import json
import os
import urllib.request
import urllib.error

API_BASE = "https://game.spacemolt.com/api/v1"
DEFAULT_SESSION_FILE = "/tmp/sm-session"
DEFAULT_CRED_FILE = "./me/credentials.txt"


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
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode())
                self._print_notifications(result)
                return result
        except urllib.error.HTTPError as e:
            body_text = e.read().decode()
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
        data = n.get("data", {})

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
                sender = data.get("sender", "?")
                channel = data.get("channel", "?")
                content = data.get("content", "")
                msg = f"<{sender}@{channel}> {content}"
            elif data:
                msg = f"{msg_type}: {json.dumps(data)}"
            else:
                msg = msg_type or str(n)
        return f"  [{ntype}] {msg}"

    @staticmethod
    def _print_notifications(resp):
        notifs = resp.get("notifications")
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

        # Login
        login_body = {"username": username, "password": password, "session_id": sid}
        headers = {"Content-Type": "application/json", "X-Session-Id": sid}
        data = json.dumps(login_body).encode()
        req = urllib.request.Request(
            f"{API_BASE}/login",
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body_text = e.read().decode()
            _, msg = self._parse_error(body_text)
            raise APIError(f"Login failed: {msg}")

        err = result.get("error")
        if err:
            raise APIError(f"Login failed: {err}")

        with open(self.session_file, "w") as f:
            f.write(sid)

        print(f"Logged in as {username} (session: {sid[:12]}...)")
