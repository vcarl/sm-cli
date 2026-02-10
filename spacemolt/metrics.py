#!/usr/bin/env python3
"""Tiny metrics server — logs every sm API call."""

import json
import sys
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

# session_id prefix -> player name, filled lazily
_players = {}


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


class MetricsHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        session = data.get("session", "?")
        endpoint = _normalize_endpoint(data.get("endpoint", "?"))
        # Prefer client-provided username over API resolution
        username = data.get("username")
        if username:
            _players[session] = username
            player = username
        else:
            player = _resolve_player(session)

        print(f"[{ts}] {player:>20s}  {endpoint}", flush=True)

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
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9100
    server = HTTPServer(("0.0.0.0", port), MetricsHandler)
    print(f"Metrics server listening on :{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
