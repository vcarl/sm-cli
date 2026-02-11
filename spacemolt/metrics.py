#!/usr/bin/env python3
"""Tiny metrics server — logs every sm API call to stdout and a JSONL file.

Log file (default /tmp/sm-metrics.jsonl) is append-only JSONL, one record per
CLI invocation.  Other processes can tail or read it for analysis.
"""

import json
import os
import sys
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

DEFAULT_LOG_FILE = "/tmp/sm-metrics.jsonl"

# session_id prefix -> player name, filled lazily
_players = {}
_log_path = DEFAULT_LOG_FILE


def _normalize_endpoint(endpoint):
    """Normalize endpoint names: strip path prefixes, canonicalize aliases."""
    # Strip path prefixes like /game/ or /api/v1/
    if "/" in endpoint:
        endpoint = endpoint.rsplit("/", 1)[-1]
    return endpoint


def _resolve_player(session_prefix):
    """Try to resolve a session prefix to a player name via the game API."""
    if session_prefix in _players:
        return _players[session_prefix]
    _players[session_prefix] = session_prefix  # fallback
    try:
        import urllib.request
        body = json.dumps({"session_id": session_prefix}).encode()
        req = urllib.request.Request(
            "https://game.spacemolt.com/api/v1/get_status",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            name = data.get("result", {}).get("player", {}).get("username")
            if name:
                _players[session_prefix] = name
    except Exception:
        pass
    return _players[session_prefix]


def _append_log(record):
    """Append a JSON record to the log file."""
    try:
        with open(_log_path, "a") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")
    except OSError:
        pass


class MetricsHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        now = datetime.now(timezone.utc)
        ts = now.strftime("%H:%M:%S")
        session = data.get("session", "?")
        endpoint = _normalize_endpoint(data.get("endpoint", "?"))
        command = data.get("command")
        command_args = data.get("command_args")

        # Prefer client-provided username over API resolution
        username = data.get("username")
        if username:
            _players[session] = username
            player = username
        else:
            player = _resolve_player(session)

        # Pretty-print to stdout
        cmd_label = f" (cmd: {command})" if command else ""
        print(f"[{ts}] {player:>20s}  {endpoint}{cmd_label}", flush=True)

        # Append structured record to log file
        record = {
            "ts": now.isoformat(),
            "player": player,
            "endpoint": endpoint,
            "session": session,
        }
        if command:
            record["command"] = command
        if command_args:
            record["command_args"] = command_args
        _append_log(record)

        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok\n")

    def log_message(self, format, *args):
        pass


def main():
    global _log_path
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9100
    if len(sys.argv) > 2:
        _log_path = sys.argv[2]
    server = HTTPServer(("0.0.0.0", port), MetricsHandler)
    print(f"Metrics server listening on :{port}", flush=True)
    print(f"Logging to {_log_path}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
