#!/usr/bin/env python3
"""Metrics server that tracks moving averages of unique event counts.

Listens on the same port/protocol as metrics.py, but instead of raw logs,
displays a live dashboard of event rates using a sliding window.

Usage:
    python -m spacemolt.metrics_avg [port] [window_seconds] [bucket_seconds]

Defaults: port=9100, window=60s, bucket=10s
"""

import json
import sys
import time
import threading
from collections import defaultdict
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler


class EventTracker:
    """Tracks events in time buckets and computes moving averages."""

    def __init__(self, window_seconds=60, bucket_seconds=10):
        self.window = window_seconds
        self.bucket = bucket_seconds
        self.lock = threading.Lock()
        # Each bucket is keyed by bucket_start_time (int)
        # Value: {endpoint: set(players), ...}
        self.buckets: dict[int, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )

    def _bucket_key(self, t=None):
        if t is None:
            t = time.time()
        return int(t // self.bucket) * self.bucket

    def record(self, endpoint, player):
        with self.lock:
            key = self._bucket_key()
            self.buckets[key][endpoint].add(player)

    def _prune(self, now):
        cutoff = self._bucket_key(now) - self.window
        stale = [k for k in self.buckets if k < cutoff]
        for k in stale:
            del self.buckets[k]

    def snapshot(self):
        """Return moving-average stats over the current window.

        Returns:
            {
                "window_seconds": int,
                "bucket_seconds": int,
                "n_buckets": int,        # buckets with data in window
                "total_events": int,     # total hits in window
                "unique_endpoints": int, # distinct endpoints in window
                "unique_players": int,   # distinct players in window
                "avg_events_per_bucket": float,
                "avg_unique_endpoints_per_bucket": float,
                "avg_unique_players_per_bucket": float,
                "by_endpoint": {name: {"total": int, "avg_per_bucket": float}},
                "by_player": {name: {"total": int, "avg_per_bucket": float}},
            }
        """
        now = time.time()
        with self.lock:
            self._prune(now)

            current_key = self._bucket_key(now)
            # How many bucket slots fit in the window
            n_slots = self.window // self.bucket

            # Collect per-bucket counts
            all_endpoints = set()
            all_players = set()
            total_events = 0
            endpoint_totals = defaultdict(int)
            player_totals = defaultdict(int)
            per_bucket_endpoints = []
            per_bucket_players = []
            buckets_with_data = 0

            for offset in range(n_slots):
                key = current_key - offset * self.bucket
                bucket = self.buckets.get(key)
                if bucket:
                    buckets_with_data += 1
                    bucket_endpoints = set(bucket.keys())
                    bucket_players = set()
                    for ep, players in bucket.items():
                        count = len(players)
                        endpoint_totals[ep] += count
                        total_events += count
                        all_endpoints.add(ep)
                        for p in players:
                            player_totals[p] += 1
                            bucket_players.add(p)
                            all_players.add(p)
                    per_bucket_endpoints.append(len(bucket_endpoints))
                    per_bucket_players.append(len(bucket_players))
                else:
                    per_bucket_endpoints.append(0)
                    per_bucket_players.append(0)

            denom = n_slots or 1

            by_endpoint = {
                ep: {"total": t, "avg_per_bucket": round(t / denom, 2)}
                for ep, t in sorted(endpoint_totals.items(), key=lambda x: -x[1])
            }
            by_player = {
                p: {"total": t, "avg_per_bucket": round(t / denom, 2)}
                for p, t in sorted(player_totals.items(), key=lambda x: -x[1])
            }

            return {
                "window_seconds": self.window,
                "bucket_seconds": self.bucket,
                "n_buckets": buckets_with_data,
                "total_events": total_events,
                "unique_endpoints": len(all_endpoints),
                "unique_players": len(all_players),
                "avg_events_per_bucket": round(total_events / denom, 2),
                "avg_unique_endpoints_per_bucket": round(
                    sum(per_bucket_endpoints) / denom, 2
                ),
                "avg_unique_players_per_bucket": round(
                    sum(per_bucket_players) / denom, 2
                ),
                "by_endpoint": by_endpoint,
                "by_player": by_player,
            }


# ---- Endpoint normalization ----


def _normalize_endpoint(endpoint):
    """Normalize endpoint names: strip path prefixes, canonicalize aliases."""
    if "/" in endpoint:
        endpoint = endpoint.rsplit("/", 1)[-1]
    return endpoint


# ---- Player resolution (same as metrics.py) ----

_players = {}


def _resolve_player(session_prefix):
    if session_prefix in _players:
        return _players[session_prefix]
    _players[session_prefix] = session_prefix
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


# ---- Global tracker ----

tracker = EventTracker()


# ---- HTTP handler ----


class MetricsAvgHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        session = data.get("session", "?")
        endpoint = _normalize_endpoint(data.get("endpoint", "?"))
        # Prefer client-provided username over API resolution
        username = data.get("username")
        if username:
            _players[session] = username
            player = username
        else:
            player = _resolve_player(session)

        tracker.record(endpoint, player)

        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        print(f"  [{ts}] {player:>20s}  {endpoint}", flush=True)

        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        snap = tracker.snapshot()
        body = json.dumps(snap, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


# ---- Dashboard printer ----


def dashboard_loop(interval=10):
    """Print a summary to stderr every `interval` seconds."""
    while True:
        time.sleep(interval)
        snap = tracker.snapshot()
        w = snap["window_seconds"]
        b = snap["bucket_seconds"]
        lines = [
            "",
            f"=== Moving averages ({w}s window, {b}s buckets) ===",
            f"  Events/bucket:           {snap['avg_events_per_bucket']:>8.2f}",
            f"  Unique endpoints/bucket: {snap['avg_unique_endpoints_per_bucket']:>8.2f}",
            f"  Unique players/bucket:   {snap['avg_unique_players_per_bucket']:>8.2f}",
            f"  Total in window:         {snap['total_events']:>8d} events, "
            f"{snap['unique_endpoints']} endpoints, {snap['unique_players']} players",
        ]
        if snap["by_endpoint"]:
            lines.append("  Endpoints:")
            for ep, info in snap["by_endpoint"].items():
                lines.append(f"    {ep:<30s}  {info['avg_per_bucket']:>6.2f}/bucket  ({info['total']} total)")
        if snap["by_player"]:
            lines.append("  Players:")
            for p, info in snap["by_player"].items():
                lines.append(f"    {p:<20s}  {info['avg_per_bucket']:>6.2f}/bucket  ({info['total']} total)")
        lines.append("")
        print("\n".join(lines), flush=True)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9100
    window = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    bucket = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    global tracker
    tracker = EventTracker(window_seconds=window, bucket_seconds=bucket)

    # Start dashboard printer in background
    t = threading.Thread(target=dashboard_loop, args=(bucket,), daemon=True)
    t.start()

    server = HTTPServer(("0.0.0.0", port), MetricsAvgHandler)
    print(
        f"Metrics+avg server on :{port}  "
        f"(window={window}s, bucket={bucket}s)",
        flush=True,
    )
    print(f"  GET http://localhost:{port}/  for JSON snapshot", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
