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

    # register
    p_register = sub.add_parser("register", help="Register a new user account")
    p_register.add_argument("username", help="Your unique username (3-24 chars)")
    p_register.add_argument("empire", choices=["solarian", "voidborn", "crimson", "nebula", "outerrim"],
                           help="Your starting empire (solarian=mining/trade, voidborn=stealth/shields, crimson=combat, nebula=exploration, outerrim=crafting/cargo)")

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
    p_sell_all = sub.add_parser("sell-all", help="Sell all cargo (auto-waits between items)")
    p_sell_all.add_argument("--max-items", type=int, metavar="N", help="Max number of items to sell (default: no limit)")

    # buy
    p_buy = sub.add_parser("buy", help="Buy item from NPC market")
    p_buy.add_argument("item_id", help="Item ID to buy (e.g. ore_iron)")
    p_buy.add_argument("quantity", nargs="?", type=int, default=1, help="Quantity to buy (default: 1)")

    # NOTE: Old flat "skills" parser removed - replaced with hierarchical version below

    # nearby
    p_nearby = sub.add_parser("nearby", help="Nearby players + threat assessment")
    p_nearby.add_argument("--scan", action="store_true", help="Scan each player (rate-limited, ~11s per player)")
    p_nearby.add_argument("--timeout", type=int, metavar="SECONDS", help="Max time for --scan operation (default: no limit)")

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

    # wait
    p_wait = sub.add_parser("wait", help="Block until current action completes")
    p_wait.add_argument("--timeout", type=int, default=60, help="Max seconds to wait (default: 60)")

    # refuel
    sub.add_parser("refuel", help="Refuel ship")

    # repair
    sub.add_parser("repair", help="Repair ship")

    # wrecks
    sub.add_parser("wrecks", help="Wrecks at current location")

    # listings
    sub.add_parser("listings", help="Market listings at current base")

    # NOTE: Old flat "recipes" parser removed - replaced with hierarchical version below

    # query-recipes
    p_qr = sub.add_parser("query-recipes", help="Recipe progression, search, and ingredient trees")
    p_qr.add_argument("--trace", metavar="ITEM",
                       help="Trace full ingredient tree for an item or recipe")
    p_qr.add_argument("--search", metavar="QUERY",
                       help="Search recipes by name, item, or category")
    p_qr.add_argument("--limit", type=int, default=10, metavar="N",
                       help="Max items per page (default: 10)")
    p_qr.add_argument("--page", type=int, default=1, metavar="N",
                       help="Page number (default: 1)")

    # NOTE: Old flat "missions" parser removed - replaced with hierarchical version below

    # active-missions
    sub.add_parser("active-missions", help="Your active missions with progress")

    # query-missions
    p_qm = sub.add_parser("query-missions", help="Mission explorer: group by type, search, active")
    p_qm.add_argument("--search", metavar="QUERY",
                       help="Search missions by name, type, or description")
    p_qm.add_argument("--active", action="store_true",
                       help="Show active missions instead of available ones")
    p_qm.add_argument("--limit", type=int, default=10, metavar="N",
                       help="Max items per page (default: 10)")
    p_qm.add_argument("--page", type=int, default=1, metavar="N",
                       help="Page number (default: 1)")

    # query-skills
    p_qs = sub.add_parser("query-skills", help="Compact skill list by category")
    p_qs.add_argument("--search", metavar="QUERY",
                       help="Search skills by name, category, or bonus")
    p_qs.add_argument("--my", action="store_true",
                       help="Show only your trained skills with progress bars")
    p_qs.add_argument("--limit", type=int, default=10, metavar="N",
                       help="Max items per page (default: 10)")
    p_qs.add_argument("--page", type=int, default=1, metavar="N",
                       help="Page number (default: 1)")

    # skill (deep inspect)
    p_si = sub.add_parser("skill", help="Deep inspect a skill: prereqs, bonuses, XP table, unlocks")
    p_si.add_argument("skill_id", help="Skill ID or name (fuzzy matched)")

    # commands
    sub.add_parser("commands", help="List all API endpoints")

    # chat
    p_chat = sub.add_parser("chat", help="Send chat message")
    p_chat.add_argument("channel", help="Chat channel (system/local/faction/private)")
    p_chat.add_argument("target_or_message", help="Player ID (for private) or message (for other channels)")
    p_chat.add_argument("message", nargs="?", default=None, help="Message to send (required for private channel)")

    # raw
    p_raw = sub.add_parser("raw", help="Raw API call (always outputs JSON)")
    p_raw.add_argument("endpoint", help="API endpoint name (e.g. get_map, get_system)")
    p_raw.add_argument("json_body", nargs="?", default=None,
                       help='Optional JSON body, e.g. \'{"target_system":"sol"}\'')

    # ========================================================================
    # HIERARCHICAL COMMAND GROUPS (new syntax alongside old flat commands)
    # ========================================================================

    # missions group (with backwards-compatible subcommand routing)
    # Note: This creates a NEW "missions" parser that overrides the old one above.
    # The router will handle showing the combined view by default.
    p_missions_hier = sub.add_parser("missions", help="Mission management (shows active + available by default)")
    missions_sub = p_missions_hier.add_subparsers(dest="missions_cmd")

    missions_sub.add_parser("active", help="Your active missions")
    missions_sub.add_parser("available", help="Available missions at base")

    p_mq = missions_sub.add_parser("query", help="Search missions")
    p_mq.add_argument("--search", metavar="QUERY", help="Search missions by name, type, or description")
    p_mq.add_argument("--active", action="store_true", help="Show active missions instead of available ones")
    p_mq.add_argument("--limit", type=int, default=10, metavar="N", help="Max items per page (default: 10)")
    p_mq.add_argument("--page", type=int, default=1, metavar="N", help="Page number (default: 1)")

    p_ma = missions_sub.add_parser("accept", help="Accept mission")
    p_ma.add_argument("mission_id", help="Mission ID")

    p_mc = missions_sub.add_parser("complete", help="Complete mission")
    p_mc.add_argument("mission_id", help="Mission ID")

    p_mab = missions_sub.add_parser("abandon", help="Abandon mission")
    p_mab.add_argument("mission_id", help="Mission ID")

    # skills group
    p_skills_hier = sub.add_parser("skills", help="Skill management (shows trained skills by default)")
    skills_sub = p_skills_hier.add_subparsers(dest="skills_cmd")

    skills_sub.add_parser("list", help="List trained skills (default)")

    p_sq = skills_sub.add_parser("query", help="Search all skills")
    p_sq.add_argument("--search", metavar="QUERY", help="Search skills by name, category, or bonus")
    p_sq.add_argument("--my", action="store_true", help="Show only your trained skills with progress bars")
    p_sq.add_argument("--limit", type=int, default=10, metavar="N", help="Max items per page (default: 10)")
    p_sq.add_argument("--page", type=int, default=1, metavar="N", help="Page number (default: 1)")

    p_si = skills_sub.add_parser("inspect", help="Deep inspect a skill")
    p_si.add_argument("skill_id_inspect", metavar="skill_id", help="Skill ID or name (fuzzy matched)")

    # recipes group
    p_recipes_hier = sub.add_parser("recipes", help="Recipe management (shows recipe list by default)")
    recipes_sub = p_recipes_hier.add_subparsers(dest="recipes_cmd")

    p_rl = recipes_sub.add_parser("list", help="List recipes (default)")
    p_rl.add_argument("--limit", type=int, default=10, metavar="N", help="Max items per page (default: 10)")
    p_rl.add_argument("--page", type=int, default=1, metavar="N", help="Page number (default: 1)")

    p_rq = recipes_sub.add_parser("query", help="Recipe progression, search, and ingredient trees")
    p_rq.add_argument("--trace", metavar="ITEM", dest="trace_query", help="Trace full ingredient tree for an item or recipe")
    p_rq.add_argument("--search", metavar="QUERY", dest="search_query", help="Search recipes by name, item, or category")
    p_rq.add_argument("--limit", type=int, default=10, metavar="N", help="Max items per page (default: 10)")
    p_rq.add_argument("--page", type=int, default=1, metavar="N", help="Page number (default: 1)")

    p_rc = recipes_sub.add_parser("craft", help="Craft a recipe")
    p_rc.add_argument("recipe_id", help="Recipe ID")
    p_rc.add_argument("count", nargs="?", type=int, help="Quantity to craft (optional)")

    # insurance group
    p_insurance = sub.add_parser("insurance", help="Insurance management (shows coverage status by default)")
    insurance_sub = p_insurance.add_subparsers(dest="insurance_subcommand")

    p_ib = insurance_sub.add_parser("buy", help="Purchase insurance coverage")
    p_ib.add_argument("ticks", type=int, help="Number of ticks to insure for")

    insurance_sub.add_parser("claim", help="Claim insurance payout after ship destruction")

    # storage group
    p_storage = sub.add_parser("storage", help="Base storage management (shows contents by default)")
    storage_sub = p_storage.add_subparsers(dest="storage_subcommand")

    p_sd = storage_sub.add_parser("deposit", help="Deposit items or credits into storage")
    p_sd.add_argument("item_id", nargs="?", help="Item ID to deposit")
    p_sd.add_argument("quantity", nargs="?", type=int, help="Quantity to deposit")
    p_sd.add_argument("--credits", type=int, metavar="AMOUNT", help="Deposit credits instead of items")

    p_sw = storage_sub.add_parser("withdraw", help="Withdraw items or credits from storage")
    p_sw.add_argument("item_id", nargs="?", help="Item ID to withdraw")
    p_sw.add_argument("quantity", nargs="?", type=int, help="Quantity to withdraw")
    p_sw.add_argument("--credits", type=int, metavar="AMOUNT", help="Withdraw credits instead of items")

    # market group
    p_market = sub.add_parser("market", help="Market orders management (shows your orders by default)")
    market_sub = p_market.add_subparsers(dest="market_subcommand")

    p_mb = market_sub.add_parser("buy", help="Create a buy order")
    p_mb.add_argument("item_id", help="Item ID")
    p_mb.add_argument("quantity", type=int, help="Quantity to buy")
    p_mb.add_argument("price", type=int, help="Price per item (in credits)")

    p_ms = market_sub.add_parser("sell", help="Create a sell order")
    p_ms.add_argument("item_id", help="Item ID")
    p_ms.add_argument("quantity", type=int, help="Quantity to sell")
    p_ms.add_argument("price", type=int, help="Price per item (in credits)")

    p_mc = market_sub.add_parser("cancel", help="Cancel a market order")
    p_mc.add_argument("order_id", help="Order ID to cancel")

    # Friendly aliases for common queries
    for alias, help_text in [("notes", "List your notes"),
                              ("trades", "List pending trades"),
                              ("drones", "List active drones"),
                              ("ships", "List owned ships"),
                              ("faction-list", "List all factions"),
                              ("faction-invites", "Pending faction invites")]:
        p = sub.add_parser(alias, help=help_text)
        p.add_argument("extra", nargs="*")
    p_ch_hist = sub.add_parser("chat-history", help="Chat message history")
    p_ch_hist.add_argument("extra", nargs="*", help="[channel] [limit] [target_id]")

    return parser


COMMAND_MAP = {
    "register": commands.cmd_register,
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
    "skills": commands.cmd_skills_router,  # NEW: hierarchical router
    "nearby": commands.cmd_nearby,
    "notifications": commands.cmd_notifications,
    "travel": commands.cmd_travel,
    "jump": commands.cmd_jump,
    "dock": commands.cmd_dock,
    "undock": commands.cmd_undock,
    "mine": commands.cmd_mine,
    "wait": commands.cmd_wait,
    "refuel": commands.cmd_refuel,
    "repair": commands.cmd_repair,
    "wrecks": commands.cmd_wrecks,
    "listings": commands.cmd_listings,
    "recipes": commands.cmd_recipes_router,  # NEW: hierarchical router
    "query-recipes": commands.cmd_query_recipes,  # Keep for backwards compatibility
    "missions": commands.cmd_missions_router,     # NEW: hierarchical router
    "active-missions": commands.cmd_active_missions,  # Keep for backwards compatibility
    "query-missions": commands.cmd_query_missions,     # Keep for backwards compatibility
    "query-skills": commands.cmd_query_skills,  # Keep for backwards compatibility
    "skill": commands.cmd_skill,  # Keep for backwards compatibility
    "commands": commands.cmd_commands,
    "chat": commands.cmd_chat,
    "raw": commands.cmd_raw,
    "chat-history": commands.cmd_chat_history,
    "notes": commands.cmd_notes,
    "trades": commands.cmd_trades,
    "drones": commands.cmd_drones,
    "ships": commands.cmd_ships,
    "faction-list": commands.cmd_faction_list,
    "faction-invites": commands.cmd_faction_invites,
    # Phase 4: Hierarchical commands
    "insurance": commands.cmd_insurance,
    "storage": commands.cmd_storage,
    "market": commands.cmd_market,
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

        # Validate endpoint exists before attempting passthrough
        from spacemolt.commands.passthrough import ENDPOINT_ARGS
        if endpoint not in ENDPOINT_ARGS:
            from spacemolt.suggestions import suggest_command
            suggestion = suggest_command(first_arg)
            print(f"ERROR: Unknown command '{first_arg}'", file=sys.stderr)
            if suggestion:
                print(suggestion, file=sys.stderr)
            print("\nRun 'sm commands' to see all available commands.", file=sys.stderr)
            sys.exit(1)

        extra_args = argv[1:]
        api.set_command_context(first_arg, extra_args or None)
        commands.cmd_passthrough(api, endpoint, extra_args, as_json=json_flag)
        return

    # Known command — let argparse handle it
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return

    # Inject --json into args for formatted handlers
    args.json = json_flag

    # Build command args list for metrics
    cmd_args = [v for k, v in sorted(vars(args).items())
                if k not in ("command", "json") and v is not None
                and v is not False and v != []]
    # Flatten to strings
    cmd_args = [str(a) for a in cmd_args]
    api.set_command_context(args.command, cmd_args or None)

    handler = COMMAND_MAP.get(args.command)
    if handler:
        try:
            handler(api, args)
            # Show contextual help after successful command execution
            from spacemolt.context_help import show_contextual_help
            show_contextual_help(args.command, args)
        except APIError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Auto-registered passthrough endpoint
        endpoint = args.command.replace("-", "_")
        extra_args = getattr(args, "extra", [])
        api.set_command_context(args.command, extra_args or None)
        commands.cmd_passthrough(api, endpoint, extra_args, as_json=json_flag)


if __name__ == "__main__":
    main()
