import json
import os
import threading
import time
import urllib.request
import urllib.error

API_BASE = "https://game.spacemolt.com/api/v1"
METRICS_URL = "http://host.docker.internal:9100"
DEFAULT_SESSION_FILE = "/tmp/sm-session"
DEFAULT_CRED_FILE = "./me/credentials.txt"


def _resolve_metrics_host():
    """Resolve host.docker.internal to IPv4, falling back to the URL as-is."""
    try:
        import socket
        ip = socket.getaddrinfo("host.docker.internal", 9100, socket.AF_INET)[0][4][0]
        return f"http://{ip}:9100"
    except Exception:
        return METRICS_URL

_metrics_url_v4 = None

def _report_metric(session_id, endpoint, username=None, command=None, command_args=None):
    """Fire-and-forget POST to metrics server. Fails silently if not running."""
    global _metrics_url_v4
    if _metrics_url_v4 is None:
        _metrics_url_v4 = _resolve_metrics_host()
    def _send():
        try:
            payload = {"session": session_id, "endpoint": endpoint}
            if username:
                payload["username"] = username
            if command:
                payload["command"] = command
            if command_args:
                payload["command_args"] = command_args
            body = json.dumps(payload).encode()
            req = urllib.request.Request(_metrics_url_v4, data=body, headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=1)
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()


class APIError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class SpaceMoltAPI:
    def __init__(self, session_file=DEFAULT_SESSION_FILE, cred_file=DEFAULT_CRED_FILE, timeout=30):
        self.session_file = session_file
        self.cred_file = cred_file
        self.timeout = timeout
        self.username = None
        self._command = None
        self._command_args = None
        self._status_cache = None
        self._status_cache_time = 0

    def set_command_context(self, command, command_args=None):
        """Set the current CLI command context for metrics reporting."""
        self._command = command
        self._command_args = command_args

    def _post(self, endpoint, body=None, use_session=True, _retried=False, _retry_count=0):
        if body is None:
            body = {}
        if use_session:
            sid = self.get_session_id()
            body["session_id"] = sid

        data = json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        if use_session:
            headers["X-Session-Id"] = sid

        req = urllib.request.Request(
            f"{API_BASE}/{endpoint}",
            data=data,
            headers=headers,
            method="POST",
        )
        _report_metric(body.get("session_id", "?"), endpoint, self.username,
                       self._command, self._command_args)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode())
                self._print_notifications(result)
                return result
        except urllib.error.HTTPError as e:
            body_text = e.read().decode()
            try:
                err_resp = json.loads(body_text)
                self._print_notifications(err_resp)
            except (json.JSONDecodeError, ValueError):
                pass
            code, msg, wait_seconds = self._parse_error(body_text)

            # Handle session expiry with auto-relogin
            if e.code == 401 and "session" in code and not _retried:
                if os.path.exists(self.cred_file):
                    print("Session expired, re-logging in...", flush=True)
                    self.login(self.cred_file)
                    return self._post(endpoint, body, use_session, _retried=True)
                raise APIError("Session expired. Run: sm login")

            # Handle rate limiting with API-provided wait time
            if e.code == 429:
                if wait_seconds and wait_seconds <= 10 and _retry_count < 1:
                    print(f"Rate limited. Waiting {wait_seconds}s...", flush=True)
                    time.sleep(wait_seconds)
                    return self._post(endpoint, body, use_session, _retried, _retry_count + 1)
                elif wait_seconds:
                    raise APIError(f"Rate limited. Try again in {wait_seconds}s", status_code=429)
                else:
                    raise APIError(f"Rate limited. {msg}", status_code=429)

            # Retry on transient server errors
            if e.code in (503, 504) and _retry_count < 1:
                delay = 2
                print(f"Server error {e.code}, retrying in {delay}s...", flush=True)
                time.sleep(delay)
                return self._post(endpoint, body, use_session, _retried, _retry_count + 1)

            raise APIError(f"HTTP {e.code}: {msg}", status_code=e.code)
        except urllib.error.URLError as e:
            # Network errors (connection refused, DNS failure, timeout)
            if _retry_count < 2:
                delay = 2 ** _retry_count  # Exponential backoff: 1s, 2s
                print(f"Network error, retrying in {delay}s...", flush=True)
                time.sleep(delay)
                return self._post(endpoint, body, use_session, _retried, _retry_count + 1)
            raise APIError(f"Network error: {e.reason}")

    @staticmethod
    def _format_notification(n):
        """Format a notification for display, or return None to skip it."""
        msg_type = n.get("msg_type", "")
        data = n.get("data") or {}

        # Skip low-value ack notifications
        if msg_type == "ok":
            return None

        ntype = n.get("type", "?")
        msg = data.get("message") or n.get("message") or n.get("content")
        if not msg:
            if msg_type == "mining_yield":
                name = data.get("resource_name") or data.get("resource_id", "ore")
                qty = data.get("quantity", "?")
                msg = f"Mined {name} x{qty}"
            elif msg_type == "chat_message":
                sender = data.get("sender_name") or data.get("sender", "?")
                sender_id = data.get("sender_id", "")
                channel = data.get("channel", "?")
                content = data.get("content", "")
                sender_label = sender
                if sender_id:
                    sender_label += f"({sender_id})"
                msg = f"<{sender_label}@{channel}> {content}"
            elif msg_type in ("ship_destroyed", "death", "killed", "destroyed"):
                killer = data.get("killed_by") or data.get("attacker", "")
                system = data.get("system") or data.get("system_name", "")
                parts = ["Ship destroyed!"]
                if killer:
                    parts.append(f"Killed by {killer}")
                if system:
                    parts.append(f"in {system}")
                parts.append("\n  Tip: sm buy-insurance <ticks>  |  sm claim-insurance")
                msg = "  ".join(parts)
            elif msg_type in ("combat_start", "combat_end", "attack_hit",
                             "attack_miss", "under_attack"):
                attacker = data.get("attacker") or data.get("attacker_name", "")
                target = data.get("target") or data.get("target_name", "")
                damage = data.get("damage")
                parts = []
                if msg_type == "combat_start":
                    parts.append(f"Combat started with {target or attacker}")
                elif msg_type == "combat_end":
                    parts.append(f"Combat ended")
                elif msg_type == "under_attack":
                    parts.append(f"Under attack from {attacker}")
                elif damage is not None:
                    verb = "Hit" if msg_type == "attack_hit" else "Missed"
                    parts.append(f"{verb} {target or attacker}")
                    if msg_type == "attack_hit":
                        parts.append(f"for {damage} damage")
                else:
                    parts.append(msg_type.replace("_", " ").title())
                parts.append("\n  Hint: sm status  |  sm nearby")
                msg = "  ".join(parts)
            elif msg_type in ("trade_offer", "trade_received"):
                partner = data.get("from") or data.get("sender") or data.get("partner", "?")
                trade_id = data.get("trade_id") or data.get("id", "")
                msg = f"Trade offer from {partner}"
                if trade_id:
                    msg += f"\n  Hint: sm trades  |  sm trade-accept {trade_id}"
                else:
                    msg += "\n  Hint: sm trades"
            elif msg_type in ("poi_arrival", "poi_departure"):
                uname = data.get("username", "?")
                clan = data.get("clan_tag", "")
                clan_str = f"[{clan}] " if clan else ""
                emoji = "\U0001f6ec" if msg_type == "poi_arrival" else "\U0001f4a8"
                poi_name = data.get("poi_name", "")
                poi_str = f" at {poi_name}" if poi_name else ""
                msg = f"{emoji} {clan_str}{uname}{poi_str}"
            elif data:
                msg = f"{msg_type}: {json.dumps(data)}"
            else:
                msg = msg_type or str(n)
        return f"  [{ntype}] {msg}"

    @staticmethod
    def _print_notifications(resp):
        """Extract and print notifications from any API response.

        Notifications may appear at the top level or nested inside 'result'.
        """
        notifs = resp.get("notifications") or []
        # Also check inside result, in case the API nests them there
        result = resp.get("result")
        if isinstance(result, dict):
            nested = result.get("notifications")
            if nested:
                notifs = notifs + nested
        if not notifs:
            return
        for n in notifs:
            line = SpaceMoltAPI._format_notification(n)
            if line:
                print(line, flush=True)

    @staticmethod
    def _parse_error(body_text):
        try:
            err_json = json.loads(body_text)
            # API wraps errors as {"error": {"code": ..., "message": ...}}
            inner = err_json.get("error", err_json)
            if isinstance(inner, dict):
                code = inner.get("code", "")
                msg = inner.get("message") or str(inner)
                wait_seconds = inner.get("wait_seconds")
            else:
                code = ""
                msg = str(inner)
                wait_seconds = None
        except (json.JSONDecodeError, ValueError):
            code = ""
            msg = body_text
            wait_seconds = None
        return code, msg, wait_seconds

    def get_session_id(self):
        if not os.path.exists(self.session_file):
            raise APIError("Not logged in. Run: sm login")
        with open(self.session_file) as f:
            sid = f.read().strip()
        if not sid:
            raise APIError("Not logged in. Run: sm login")
        return sid

    def login(self, cred_file=None):
        cred_file = cred_file or self.cred_file
        if not os.path.exists(cred_file):
            raise APIError(f"No credentials at {cred_file}")

        username = None
        password = None
        with open(cred_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("Username:"):
                    username = line.split(":", 1)[1].strip()
                elif line.startswith("Password:"):
                    password = line.split(":", 1)[1].strip()

        if not username or not password:
            raise APIError(f"Can't parse credentials from {cred_file}")

        # Create session
        resp = self._post("session", {}, use_session=False)
        session = resp.get("session", {})
        sid = session.get("id") or session.get("session_id") or resp.get("session_id")
        if not sid:
            raise APIError(f"Failed to create session: {json.dumps(resp)}")

        # Login — write session file first so _post can read it
        with open(self.session_file, "w") as f:
            f.write(sid)

        try:
            result = self._post("login", {"username": username, "password": password})
        except APIError as e:
            # Clean up session file on login failure
            try:
                os.remove(self.session_file)
            except OSError:
                pass
            raise APIError(f"Login failed: {e}")

        err = result.get("error")
        if err:
            try:
                os.remove(self.session_file)
            except OSError:
                pass
            raise APIError(f"Login failed: {err}")

        self.username = username
        print(f"Logged in as {username} (session: {sid[:12]}...)")
        return result

    def _get_cached_status(self, max_age=5):
        """Get cached status response, or fetch fresh if cache is stale (>max_age seconds)."""
        now = time.time()
        if self._status_cache and (now - self._status_cache_time) < max_age:
            return self._status_cache
        # Fetch fresh status
        self._status_cache = self._post("get_status")
        self._status_cache_time = now
        return self._status_cache

    def _clear_status_cache(self):
        """Clear cached status (call after mutations that change ship state)."""
        self._status_cache = None
        self._status_cache_time = 0

    def _require_docked(self, hint="You must dock first. Hint: sm dock"):
        """Raise APIError if not currently docked at a station."""
        status = self._get_cached_status()
        result = status.get("result", {})
        # Check both old format (result.docked) and new format (result.player.docked_at_base)
        player = result.get("player", {})
        docked = result.get("docked") or result.get("is_docked") or bool(player.get("docked_at_base"))
        if not docked:
            raise APIError(hint)

    def _require_undocked(self, hint="You must undock first. Hint: sm undock"):
        """Raise APIError if currently docked at a station."""
        status = self._get_cached_status()
        result = status.get("result", {})
        # Check both old format (result.docked) and new format (result.player.docked_at_base)
        player = result.get("player", {})
        docked = result.get("docked") or result.get("is_docked") or bool(player.get("docked_at_base"))
        if docked:
            raise APIError(hint)

    def _check_cargo_space(self, required_space, hint="Not enough cargo space. Hint: sm sell-all or sm jettison"):
        """Raise APIError if cargo space is insufficient."""
        status = self._get_cached_status()
        result = status.get("result", {})
        cargo_used = result.get("cargo_used", 0)
        cargo_capacity = result.get("cargo_capacity", 0)
        available = cargo_capacity - cargo_used
        if available < required_space:
            raise APIError(f"{hint} (need {required_space}, have {available})")
