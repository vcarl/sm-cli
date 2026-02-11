#!/usr/bin/env python3
"""Analyze sm metrics logs (JSONL) and print a usage report.

Usage:
    python -m spacemolt.metrics_analyze [log_file]

Default log file: /tmp/sm-metrics.jsonl

Report includes:
  - Command frequency and recency
  - Per-player breakdown
  - Error patterns (failed commands, unknown commands)
  - Argument usage patterns
  - Usability observations
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime


DEFAULT_LOG_FILE = "/tmp/sm-metrics.jsonl"


def load_records(path):
    """Read JSONL log file, returning list of dicts. Skips malformed lines."""
    records = []
    try:
        with open(path) as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"  warning: skipped malformed line {lineno}", file=sys.stderr)
    except FileNotFoundError:
        print(f"No log file at {path}", file=sys.stderr)
        print("Start the metrics server first: python -m spacemolt.metrics", file=sys.stderr)
        sys.exit(1)
    return records


def analyze(records):
    """Return analysis dict from a list of log records."""
    if not records:
        return {"empty": True}

    command_counts = Counter()
    endpoint_counts = Counter()
    player_counts = Counter()
    player_commands = defaultdict(Counter)
    hourly = Counter()
    arg_patterns = defaultdict(list)
    errors = []

    first_ts = None
    last_ts = None

    for r in records:
        ts_str = r.get("ts", "")
        try:
            ts = datetime.fromisoformat(ts_str)
            if first_ts is None or ts < first_ts:
                first_ts = ts
            if last_ts is None or ts > last_ts:
                last_ts = ts
            hourly[ts.strftime("%Y-%m-%d %H:00")] += 1
        except (ValueError, TypeError):
            pass

        cmd = r.get("command", r.get("endpoint", "?"))
        endpoint = r.get("endpoint", "?")
        player = r.get("player", "?")

        command_counts[cmd] += 1
        endpoint_counts[endpoint] += 1
        player_counts[player] += 1
        player_commands[player][cmd] += 1

        cmd_args = r.get("command_args")
        if cmd_args:
            arg_patterns[cmd].append(cmd_args)

        # Detect error-like patterns
        if endpoint == "?" or cmd == "?":
            errors.append({"type": "unknown_endpoint", "record": r})

    return {
        "total_events": len(records),
        "time_range": {
            "first": first_ts.isoformat() if first_ts else None,
            "last": last_ts.isoformat() if last_ts else None,
        },
        "unique_players": len(player_counts),
        "unique_commands": len(command_counts),
        "command_counts": command_counts.most_common(),
        "endpoint_counts": endpoint_counts.most_common(20),
        "player_counts": player_counts.most_common(),
        "player_commands": {p: c.most_common(5) for p, c in player_commands.items()},
        "hourly_activity": sorted(hourly.items()),
        "arg_patterns": {cmd: len(args) for cmd, args in arg_patterns.items()},
        "arg_examples": {cmd: args[:3] for cmd, args in arg_patterns.items()},
        "errors": errors,
    }


def print_report(analysis):
    """Print a human-readable report."""
    if analysis.get("empty"):
        print("No records found in log file.")
        return

    print("=" * 60)
    print("  SM METRICS ANALYSIS REPORT")
    print("=" * 60)

    tr = analysis["time_range"]
    print(f"\nTotal events: {analysis['total_events']}")
    print(f"Time range:   {tr['first'] or '?'} to {tr['last'] or '?'}")
    print(f"Players:      {analysis['unique_players']}")
    print(f"Commands:     {analysis['unique_commands']}")

    print("\n--- Command Frequency ---")
    for cmd, count in analysis["command_counts"]:
        bar = "#" * min(count, 40)
        print(f"  {cmd:25s} {count:5d}  {bar}")

    print("\n--- Player Activity ---")
    for player, count in analysis["player_counts"]:
        print(f"  {player:25s} {count:5d} events")
        top = analysis["player_commands"].get(player, [])
        for cmd, c in top[:3]:
            print(f"    {cmd:23s} {c:5d}")

    if analysis["hourly_activity"]:
        print("\n--- Hourly Activity ---")
        for hour, count in analysis["hourly_activity"][-12:]:
            bar = "#" * min(count, 40)
            print(f"  {hour}  {count:4d}  {bar}")

    if analysis["arg_patterns"]:
        print("\n--- Argument Usage ---")
        for cmd, count in sorted(analysis["arg_patterns"].items(), key=lambda x: -x[1]):
            examples = analysis["arg_examples"].get(cmd, [])
            print(f"  {cmd:25s} {count:5d} calls with args")
            for ex in examples:
                print(f"    example: {ex}")

    if analysis["errors"]:
        print(f"\n--- Potential Issues ({len(analysis['errors'])}) ---")
        for e in analysis["errors"][:10]:
            print(f"  [{e['type']}] {json.dumps(e['record'], separators=(',', ':'))}")

    # Usability observations
    print("\n--- Usability Observations ---")
    cmds = dict(analysis["command_counts"])

    # Check for very rarely used commands (might indicate discoverability issues)
    rare = [(c, n) for c, n in analysis["command_counts"] if n == 1]
    if rare:
        print(f"  {len(rare)} commands used only once (may indicate exploration or discoverability issues):")
        for c, _ in rare[:5]:
            print(f"    - {c}")

    # Check for heavy repeated single-command usage (automation pattern)
    total = analysis["total_events"]
    for cmd, count in analysis["command_counts"][:3]:
        pct = count / total * 100 if total else 0
        if pct > 50:
            print(f"  '{cmd}' accounts for {pct:.0f}% of all calls — likely automated or in a loop")

    print("\n" + "=" * 60)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LOG_FILE
    records = load_records(path)
    analysis = analyze(records)
    print_report(analysis)


if __name__ == "__main__":
    main()
