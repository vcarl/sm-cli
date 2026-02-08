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
  sm ship                   Detailed ship info + modules
  sm pois                   POIs in current system
  sm system                 System overview + connections
  sm poi                    Current POI details + resources
  sm base                   Docked base details + services
  sm log                    Recent captain's log
  sm cargo                  Cargo contents
  sm skills                 Trained skills
  sm nearby                 Nearby players
  sm notifications          Pending notifications
  sm listings               Market listings at current base
  sm recipes                Crafting recipes (flat list)
  sm query-recipes           Recipe progression by skill tier
  sm query-recipes --search  Search recipes by name/item
  sm query-recipes --trace   Full ingredient tree diagram
  sm wrecks                 Wrecks at current location
  sm commands               List all API endpoints

Actions (1 per 10s tick):
  sm log-add "text"         Add captain's log entry
  sm sell-all               Sell all cargo (auto-waits between items)
  sm travel <poi-id>        Travel to POI
  sm jump <system-id>       Jump to adjacent system
  sm buy <item> <qty>       Buy item from NPC market
  sm dock / sm undock       Dock or undock
  sm mine                   Mine once
  sm refuel / sm repair     Refuel or repair
  sm chat <ch> "msg" [id]   Chat (private requires player ID)

Passthrough (any API endpoint):
  sm <endpoint> [args...]   Auto-maps args to API params
  sm scan <player-id>       Example: positional arg
  sm attack target_id=<id>  Example: key=value arg

Flags:
  sm <any-command> --json   Raw JSON output for any command

Advanced:
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
    sub.add_parser("nearby", help="Nearby players")

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

    return parser


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
