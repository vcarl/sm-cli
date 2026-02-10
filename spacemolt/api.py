import json
import os
import threading
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

def _report_metric(session_id, endpoint):
    """Fire-and-forget POST to metrics server. Fails silently if not running."""
    global _metrics_url_v4
    if _metrics_url_v4 is None:
        _metrics_url_v4 = _resolve_metrics_host()
    def _send():
        try:
            body = json.dumps({"session": session_id, "endpoint": endpoint}).encode()
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
    def __init__(self, session_file=DEFAULT_SESSION_FILE, cred_file=DEFAULT_CRED_FILE):
        self.session_file = session_file
        self.cred_file = cred_file

    def _post(self, endpoint, body=None, use_session=True, _retried=False):
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
        _report_metric(body.get("session_id", "?"), endpoint)
        try:
            with urllib.request.urlopen(req) as resp:
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
            code, msg = self._parse_error(body_text)
            if e.code == 401 and "session" in code and not _retried:
                # Session expired — auto-relogin if credentials are available
                if os.path.exists(self.cred_file):
                    print("Session expired, re-logging in...", flush=True)
                    self.login(self.cred_file)
                    return self._post(endpoint, body, use_session, _retried=True)
                raise APIError("Session expired. Run: sm login")
            raise APIError(f"HTTP {e.code}: {msg}", status_code=e.code)

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
            else:
                code = ""
                msg = str(inner)
        except (json.JSONDecodeError, ValueError):
            code = ""
            msg = body_text
        return code, msg

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

        print(f"Logged in as {username} (session: {sid[:12]}...)")
        return result
