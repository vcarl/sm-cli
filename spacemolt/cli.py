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
Tips:
  sm <command> --json       Raw JSON output for any command
  sm <cmd> key=value        Pass named args to any command
  sm raw <endpoint> [json]  Raw API call with JSON body""",
    )

    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of formatted text")

    sub = parser.add_subparsers(dest="command")

    # login
    p_login = sub.add_parser("login", help="Login and save session")
    p_login.add_argument("cred_file", nargs="?", default=None, help="Path to credentials file (default: ./me/credentials.txt)")

    # status
    sub.add_parser("status", help="Credits, location, ship, fuel")

    # ship
    sub.add_parser("ship", help="Detailed ship info + modules")

    # pois
    sub.add_parser("pois", help="POIs in current system")

    # system
    sub.add_parser("system", help="System overview + connections")

    # poi
    sub.add_parser("poi", help="Current POI details + resources")

    # base
    sub.add_parser("base", help="Docked base details + services")

    # log
    p_log = sub.add_parser("log", help="Recent captain's log")
    p_log.add_argument("--brief", action="store_true", help="Show only first line of each entry")

    # log-add
    p_log_add = sub.add_parser("log-add", help="Add captain's log entry")
    p_log_add.add_argument("text", help="Log entry text")

    # cargo
    sub.add_parser("cargo", help="Cargo contents")

    # sell
    p_sell = sub.add_parser("sell", help="Sell an item from cargo")
    p_sell.add_argument("item_id", help="Item ID to sell (e.g. ore_iron)")
    p_sell.add_argument("quantity", nargs="?", type=int, default=1, help="Quantity to sell (default: 1)")

    # sell-all
    sub.add_parser("sell-all", help="Sell all cargo (auto-waits between items)")

    # buy
    p_buy = sub.add_parser("buy", help="Buy item from NPC market")
    p_buy.add_argument("item_id", help="Item ID to buy (e.g. ore_iron)")
    p_buy.add_argument("quantity", nargs="?", type=int, default=1, help="Quantity to buy (default: 1)")

    # skills
    sub.add_parser("skills", help="Trained skills")

    # nearby
    p_nearby = sub.add_parser("nearby", help="Nearby players + threat assessment")
    p_nearby.add_argument("--scan", action="store_true", help="Scan each player (rate-limited, ~11s per player)")

    # notifications
    sub.add_parser("notifications", help="Pending notifications")

    # travel
    p_travel = sub.add_parser("travel", help="Travel to POI")
    p_travel.add_argument("poi_id", help="POI UUID to travel to")

    # jump
    p_jump = sub.add_parser("jump", help="Jump to adjacent system")
    p_jump.add_argument("target_system", help="System ID to jump to")

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

    # wrecks
    sub.add_parser("wrecks", help="Wrecks at current location")

    # listings
    sub.add_parser("listings", help="Market listings at current base")

    # recipes
    sub.add_parser("recipes", help="Crafting recipes")

    # query-recipes
    p_qr = sub.add_parser("query-recipes", help="Recipe progression, search, and ingredient trees")
    p_qr.add_argument("--trace", metavar="ITEM",
                       help="Trace full ingredient tree for an item or recipe")
    p_qr.add_argument("--search", metavar="QUERY",
                       help="Search recipes by name, item, or category")

    # missions
    sub.add_parser("missions", help="Available missions at current base")

    # active-missions
    sub.add_parser("active-missions", help="Your active missions with progress")

    # query-missions
    p_qm = sub.add_parser("query-missions", help="Mission explorer: group by type, search, active")
    p_qm.add_argument("--search", metavar="QUERY",
                       help="Search missions by name, type, or description")
    p_qm.add_argument("--active", action="store_true",
                       help="Show active missions instead of available ones")

    # query-skills
    p_qs = sub.add_parser("query-skills", help="Compact skill list by category")
    p_qs.add_argument("--search", metavar="QUERY",
                       help="Search skills by name, category, or bonus")
    p_qs.add_argument("--my", action="store_true",
                       help="Show only your trained skills with progress bars")

    # skill (deep inspect)
    p_si = sub.add_parser("skill", help="Deep inspect a skill: prereqs, bonuses, XP table, unlocks")
    p_si.add_argument("skill_id", help="Skill ID or name (fuzzy matched)")

    # commands
    sub.add_parser("commands", help="List all API endpoints")

    # chat
    p_chat = sub.add_parser("chat", help="Send chat message")
    p_chat.add_argument("channel", help="Chat channel (system/local/faction/private)")
    p_chat.add_argument("message", help="Message to send")
    p_chat.add_argument("target", nargs="?", default=None, help="Player ID for private messages (required when channel=private)")

    # raw
    p_raw = sub.add_parser("raw", help="Raw API call")
    p_raw.add_argument("endpoint", help="API endpoint name")
    p_raw.add_argument("json_body", nargs="?", default=None, help="JSON body (optional)")

    # Auto-register passthrough endpoints so they show in help
    _register_passthrough_subparsers(sub)

    return parser


def _register_passthrough_subparsers(sub):
    """Register ENDPOINT_ARGS entries as subparsers for discoverability."""
    existing = set(sub.choices.keys()) if sub.choices else set()

    for endpoint, specs in sorted(commands.ENDPOINT_ARGS.items()):
        cmd_name = endpoint.replace("_", "-")
        if cmd_name in existing:
            continue
        arg_names = [commands._arg_name(s) for s in specs]
        help_str = " ".join(f"<{a}>" for a in arg_names) if arg_names else "(no args)"
        p = sub.add_parser(cmd_name, help=help_str)
        p.add_argument("extra", nargs="*", help="Positional or key=value args")


COMMAND_MAP = {
    "login": commands.cmd_login,
    "status": commands.cmd_status,
    "ship": commands.cmd_ship,
    "pois": commands.cmd_pois,
    "system": commands.cmd_system,
    "poi": commands.cmd_poi,
    "base": commands.cmd_base,
    "log": commands.cmd_log,
    "log-add": commands.cmd_log_add,
    "cargo": commands.cmd_cargo,
    "sell": commands.cmd_sell,
    "sell-all": commands.cmd_sell_all,
    "buy": commands.cmd_buy,
    "skills": commands.cmd_skills,
    "nearby": commands.cmd_nearby,
    "notifications": commands.cmd_notifications,
    "travel": commands.cmd_travel,
    "jump": commands.cmd_jump,
    "dock": commands.cmd_dock,
    "undock": commands.cmd_undock,
    "mine": commands.cmd_mine,
    "refuel": commands.cmd_refuel,
    "repair": commands.cmd_repair,
    "wrecks": commands.cmd_wrecks,
    "listings": commands.cmd_listings,
    "recipes": commands.cmd_recipes,
    "query-recipes": commands.cmd_query_recipes,
    "missions": commands.cmd_missions,
    "active-missions": commands.cmd_active_missions,
    "query-missions": commands.cmd_query_missions,
    "query-skills": commands.cmd_query_skills,
    "skill": commands.cmd_skill_info,
    "commands": commands.cmd_commands,
    "chat": commands.cmd_chat,
    "raw": commands.cmd_raw,
}


def _known_commands():
    """Return the set of all command names registered with argparse subparsers."""
    return set(COMMAND_MAP.keys())


def main():
    parser = build_parser()

    # Handle "sm log add ..." by rewriting to "sm log-add ..."
    argv = sys.argv[1:]
    if len(argv) >= 2 and argv[0] == "log" and argv[1] == "add":
        argv = ["log-add"] + argv[2:]

    # Extract --json flag before argparse sees it (so passthrough commands work)
    json_flag = "--json" in argv
    if json_flag:
        argv = [a for a in argv if a != "--json"]

    if not argv:
        parser.print_help()
        return

    # Check if the first arg (ignoring flags) is a known command or a passthrough
    first_arg = argv[0] if argv else None
    known = _known_commands()

    api = SpaceMoltAPI()

    if first_arg and first_arg not in known and not first_arg.startswith("-"):
        # Passthrough: treat first arg as an API endpoint
        endpoint = first_arg.replace("-", "_")
        extra_args = argv[1:]
        try:
            commands.cmd_passthrough(api, endpoint, extra_args, as_json=json_flag)
        except APIError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Known command — let argparse handle it
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return

    # Inject --json into args for formatted handlers
    args.json = json_flag

    handler = COMMAND_MAP.get(args.command)
    if handler:
        try:
            handler(api, args)
        except APIError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Auto-registered passthrough endpoint
        endpoint = args.command.replace("-", "_")
        extra_args = getattr(args, "extra", [])
        try:
            commands.cmd_passthrough(api, endpoint, extra_args, as_json=json_flag)
        except APIError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
