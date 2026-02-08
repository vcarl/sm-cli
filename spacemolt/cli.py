#!/usr/bin/env python3
import argparse
import sys
import os

# Allow importing spacemolt package when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spacemolt.api import SpaceMoltAPI, APIError
from spacemolt import commands


def build_parser():
    parser = argparse.ArgumentParser(
        prog="sm",
        description="sm — SpaceMolt CLI (zero-token game actions)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Info (no rate limit):
  sm status                 Credits, location, ship, fuel
  sm pois                   POIs in current system
  sm system                 System overview + connections
  sm log                    Recent captain's log
  sm cargo                  Cargo contents
  sm skills                 Trained skills
  sm nearby                 Nearby players
  sm notifications          Pending notifications

Actions (1 per 10s tick):
  sm log-add "text"         Add captain's log entry
  sm sell-all               Sell all cargo (auto-waits between items)
  sm travel <poi-id>        Travel to POI
  sm dock / sm undock       Dock or undock
  sm mine                   Mine once
  sm refuel / sm repair     Refuel or repair
  sm chat <ch> "msg"        Chat (system/local/faction/private)

Advanced:
  sm raw <endpoint> [json]  Raw API call""",
    )

    sub = parser.add_subparsers(dest="command")

    # login
    p_login = sub.add_parser("login", help="Login and save session")
    p_login.add_argument("cred_file", nargs="?", default=None, help="Path to credentials file (default: ./me/credentials.txt)")

    # status
    sub.add_parser("status", help="Credits, location, ship, fuel")

    # pois
    sub.add_parser("pois", help="POIs in current system")

    # system
    sub.add_parser("system", help="System overview + connections")

    # log
    sub.add_parser("log", help="Recent captain's log")

    # log-add
    p_log_add = sub.add_parser("log-add", help="Add captain's log entry")
    p_log_add.add_argument("text", help="Log entry text")

    # cargo
    sub.add_parser("cargo", help="Cargo contents")

    # sell-all
    sub.add_parser("sell-all", help="Sell all cargo (auto-waits between items)")

    # skills
    sub.add_parser("skills", help="Trained skills")

    # nearby
    sub.add_parser("nearby", help="Nearby players")

    # notifications
    sub.add_parser("notifications", help="Pending notifications")

    # travel
    p_travel = sub.add_parser("travel", help="Travel to POI")
    p_travel.add_argument("poi_id", help="POI UUID to travel to")

    # dock
    sub.add_parser("dock", help="Dock at base")

    # undock
    sub.add_parser("undock", help="Undock from base")

    # mine
    sub.add_parser("mine", help="Mine once")

    # refuel
    sub.add_parser("refuel", help="Refuel ship")

    # repair
    sub.add_parser("repair", help="Repair ship")

    # chat
    p_chat = sub.add_parser("chat", help="Send chat message")
    p_chat.add_argument("channel", help="Chat channel (system/local/faction/private)")
    p_chat.add_argument("message", help="Message to send")

    # raw
    p_raw = sub.add_parser("raw", help="Raw API call")
    p_raw.add_argument("endpoint", help="API endpoint name")
    p_raw.add_argument("json_body", nargs="?", default=None, help="JSON body (optional)")

    return parser


COMMAND_MAP = {
    "login": commands.cmd_login,
    "status": commands.cmd_status,
    "pois": commands.cmd_pois,
    "system": commands.cmd_system,
    "log": commands.cmd_log,
    "log-add": commands.cmd_log_add,
    "cargo": commands.cmd_cargo,
    "sell-all": commands.cmd_sell_all,
    "skills": commands.cmd_skills,
    "nearby": commands.cmd_nearby,
    "notifications": commands.cmd_notifications,
    "travel": commands.cmd_travel,
    "dock": commands.cmd_dock,
    "undock": commands.cmd_undock,
    "mine": commands.cmd_mine,
    "refuel": commands.cmd_refuel,
    "repair": commands.cmd_repair,
    "chat": commands.cmd_chat,
    "raw": commands.cmd_raw,
}


def main():
    parser = build_parser()

    # Handle "sm log add ..." by rewriting to "sm log-add ..."
    argv = sys.argv[1:]
    if len(argv) >= 2 and argv[0] == "log" and argv[1] == "add":
        argv = ["log-add"] + argv[2:]

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return

    api = SpaceMoltAPI()

    handler = COMMAND_MAP.get(args.command)
    if not handler:
        print(f"ERROR: Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)

    try:
        handler(api, args)
    except APIError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
