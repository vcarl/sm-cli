#!/usr/bin/env python3
import argparse
import sys
import os

# Allow importing spacemolt package when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

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

    # claim
    p_claim = sub.add_parser("claim", help="Link player to website account")
    p_claim.add_argument("registration_code", help="Registration code from https://spacemolt.com/dashboard")

    # status
    p_status = sub.add_parser("status", help="Credits, location, ship, fuel")
    p_status.add_argument("--nearby", action="store_true", help="Include nearby ships and wrecks")

    # ship
    sub.add_parser("ship", help="Detailed ship info + modules")

    # pois
    p_pois = sub.add_parser("pois", help="POIs in current system")
    p_pois.add_argument("--system", default=None, help="System ID to view POIs in a different system")

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

    # buy
    # NOTE: Old flat "skills" parser removed - replaced with hierarchical version below

    # nearby
    p_nearby = sub.add_parser("nearby", help="Nearby players + threat assessment")

    # notifications
    sub.add_parser("notifications", help="Pending notifications")

    # travel
    p_travel = sub.add_parser("travel", help="Travel to POI")
    p_travel.add_argument("poi_id", help="POI UUID to travel to")

    # jump
    p_jump = sub.add_parser("jump", help="Jump to adjacent system")
    p_jump.add_argument("target_system", help="System ID to jump to")

    # dock — required before storage/repair/other docked actions
    sub.add_parser("dock", help="Dock at current station (required before storage, repair, etc.)")

    # undock
    sub.add_parser("undock", help="Undock from current station")

    # mine
    sub.add_parser("mine", help="Mine once")

    # refuel
    p_refuel = sub.add_parser("refuel", help="Refuel ship (docked=station credits; item_id=burn fuel cell from cargo anywhere)")
    p_refuel.add_argument("item_id", nargs="?", default=None, help="Fuel cell item ID (e.g. fuel_cell) — works in space!")
    p_refuel.add_argument("quantity", nargs="?", type=int, default=None, help="Number of fuel cells to burn")

    # repair
    sub.add_parser("repair", help="Repair ship")

    # wrecks
    sub.add_parser("wrecks", help="Wrecks at current location")

    # listings
    p_listings = sub.add_parser("listings", help="Market listings at current base")
    p_listings.add_argument("item_id", nargs="?", default=None, help="Optional: view detailed orders for a specific item")
    p_listings.add_argument("--page", "-p", type=int, default=1, help="Page number (default: 1)")

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

    # player skills (fixed: was incorrectly redirected to catalog)
    sub.add_parser("skills", help="Your skill levels and XP progress")
    p_skill_dep = sub.add_parser("skill", help="(deprecated) Use: sm catalog skills --id <skill_id>")
    p_skill_dep.add_argument("skill_id", nargs="?", help="Skill ID (ignored)")
    sub.add_parser("query-skills", help="(deprecated) Use: sm catalog skills")

    # commands / help
    p_commands = sub.add_parser("commands", help="Show this help message")
    p_commands.add_argument("--filter", dest="filter_categories", default=None,
                            metavar="CATEGORIES",
                            help="Show only commands in these categories (comma-separated slugs)")
    p_commands.add_argument("--state", dest="state_filter", default=None,
                            metavar="STATE",
                            help="Show only commands valid in this game state (docked, space, combat)")
    p_commands.add_argument("--json", dest="json_output", action="store_true",
                            help="Output as JSON array")
    p_help = sub.add_parser("help", help="Show this help message")
    p_help.add_argument("--filter", dest="filter_categories", default=None,
                        metavar="CATEGORIES",
                        help="Show only commands in these categories (comma-separated slugs)")
    p_help.add_argument("--state", dest="state_filter", default=None,
                        metavar="STATE",
                        help="Show only commands valid in this game state (docked, space, combat)")
    p_help.add_argument("--json", dest="json_output", action="store_true",
                        help="Output as JSON array")

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
    p_missions_hier.add_argument("--json", action="store_true", help="Output raw JSON")
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

    p_md = missions_sub.add_parser("decline", help="Decline a mission (see dialog)")
    p_md.add_argument("mission_id", help="Mission template ID to decline")

    p_mab = missions_sub.add_parser("abandon", help="Abandon mission")
    p_mab.add_argument("mission_id", help="Mission ID")

    # deprecated recipe commands (redirect to catalog)
    sub.add_parser("recipes", help="(deprecated) Use: sm catalog recipes")

    # insurance group
    p_insurance = sub.add_parser("insurance", help="Insurance management (shows coverage status by default)")
    insurance_sub = p_insurance.add_subparsers(dest="insurance_subcommand")

    p_ib = insurance_sub.add_parser("buy", help="Purchase insurance coverage")
    p_ib.add_argument("ticks", type=int, help="Number of ticks of insurance coverage")

    insurance_sub.add_parser("quote", help="Get insurance pricing and risk factors")
    insurance_sub.add_parser("claim", help="Claim insurance payout after ship destruction")

    # storage group
    p_storage = sub.add_parser("storage", help="Base storage management (shows contents by default)")
    p_storage.add_argument("--target", default="self", help="Target: self (default), faction, or player name")
    p_storage.add_argument("--station", default=None, help="Station ID to view remotely (without docking)")
    storage_sub = p_storage.add_subparsers(dest="storage_subcommand")

    p_sd = storage_sub.add_parser("deposit", help="Deposit items or credits into storage")
    p_sd.add_argument("item_id", nargs="?", help="Item ID to deposit")
    p_sd.add_argument("quantity", nargs="?", type=int, help="Quantity to deposit")
    p_sd.add_argument("--credits", type=int, metavar="AMOUNT", help="Deposit credits instead of items")
    p_sd.add_argument("--target", default="self", help="Target: self (default), faction, or player name")
    p_sd.add_argument("--message", help="Optional message (for gifting to a player)")

    p_sw = storage_sub.add_parser("withdraw", help="Withdraw items or credits from storage")
    p_sw.add_argument("item_id", nargs="?", help="Item ID to withdraw")
    p_sw.add_argument("quantity", nargs="?", type=int, help="Quantity to withdraw")
    p_sw.add_argument("--credits", type=int, metavar="AMOUNT", help="Withdraw credits instead of items")
    p_sw.add_argument("--target", default="self", help="Target: self (default) or faction")

    # facility group
    p_facility = sub.add_parser("facility", help="Facility management (shows facilities at current base by default)")
    p_facility.add_argument("--json", action="store_true", help="Output raw JSON")
    facility_sub = p_facility.add_subparsers(dest="facility_cmd")

    facility_sub.add_parser("list", help="List facilities at current base (default)")

    p_ft = facility_sub.add_parser("types", help="Browse buildable facility types")
    p_ft.add_argument("--category", metavar="CAT", help="Filter by category")
    p_ft.add_argument("--name", metavar="TEXT", help="Filter by name")
    p_ft.add_argument("--page", type=int, metavar="N", help="Page number")

    p_ftd = facility_sub.add_parser("type", help="Detail view for one facility type")
    p_ftd.add_argument("facility_type", help="Facility type ID")

    p_fb = facility_sub.add_parser("build", help="Build a personal/production facility")
    p_fb.add_argument("facility_type", help="Facility type ID to build")

    p_fu = facility_sub.add_parser("upgrade", help="Upgrade a facility")
    p_fu.add_argument("facility_id", help="Facility ID to upgrade")

    p_fus = facility_sub.add_parser("upgrades", help="Show available upgrades")
    p_fus.add_argument("facility_id", nargs="?", help="Optional facility ID to filter")

    p_ftog = facility_sub.add_parser("toggle", help="Enable/disable a facility")
    p_ftog.add_argument("facility_id", help="Facility ID to toggle")

    p_ffb = facility_sub.add_parser("faction-build", help="Build a faction facility")
    p_ffb.add_argument("facility_type", help="Facility type ID to build")

    facility_sub.add_parser("faction-list", help="List faction facilities")

    p_ftr = facility_sub.add_parser("transfer", help="Transfer facility ownership")
    p_ftr.add_argument("facility_id", help="Facility ID to transfer")
    p_ftr.add_argument("direction", choices=["to_faction", "to_player"], help="Transfer direction")
    p_ftr.add_argument("player_id", nargs="?", help="Player ID (required for to_player)")

    p_fq = facility_sub.add_parser("quarters", help="Visit your or someone's quarters")
    p_fq.add_argument("username", nargs="?", help="Username to visit (default: yourself)")

    p_fd = facility_sub.add_parser("decorate", help="Write quarters description")
    p_fd.add_argument("description", help="Description text for your quarters")
    p_fd.add_argument("--access", choices=["private", "public"], help="Access level")

    facility_sub.add_parser("quarters-build", help="Build personal quarters")

    facility_sub.add_parser("help", help="Show facility actions from API")

    # market group
    p_market = sub.add_parser("market", help="Market orders management (shows your orders by default)")
    p_market.add_argument("--station", default=None, help="Station ID to view orders at remotely")
    market_sub = p_market.add_subparsers(dest="market_subcommand")

    p_mb = market_sub.add_parser("buy", help="Create a buy order")
    p_mb.add_argument("item_id", help="Item ID")
    p_mb.add_argument("quantity", type=int, help="Quantity to buy")
    p_mb.add_argument("price", type=int, help="Price per item (in credits)")
    p_mb.add_argument("--deliver-to", choices=["cargo", "storage"], default=None, help="Deliver filled items to cargo (default) or storage")

    p_ms = market_sub.add_parser("sell", help="Create a sell order")
    p_ms.add_argument("item_id", help="Item ID")
    p_ms.add_argument("quantity", type=int, help="Quantity to sell")
    p_ms.add_argument("price", type=int, help="Price per item (in credits)")

    p_mc = market_sub.add_parser("cancel", help="Cancel a market order")
    p_mc.add_argument("order_id", help="Order ID to cancel")

    # catalog
    p_catalog = sub.add_parser("catalog", help="Browse game reference data (ships, items, skills, recipes)")
    catalog_sub = p_catalog.add_subparsers(dest="catalog_type")

    # catalog ships/items/skills — simple browse with filters
    for cat_name in ["ships", "items", "skills"]:
        p_cat = catalog_sub.add_parser(cat_name, help=f"Browse {cat_name}")
        p_cat.add_argument("--search", help="Search by name/description")
        p_cat.add_argument("--category", help="Filter by category")
        p_cat.add_argument("--id", help="Look up a specific entry by ID")
        p_cat.add_argument("--page", type=int, help="Page number (default: 1)")
        p_cat.add_argument("--page-size", type=int, help="Results per page (default: 20, max: 50)")

    # catalog recipes — browse + trace subcommand
    p_cat_recipes = catalog_sub.add_parser("recipes", help="Browse recipes and trace ingredient trees")
    p_cat_recipes.add_argument("--search", help="Search by name/description")
    p_cat_recipes.add_argument("--category", help="Filter by category")
    p_cat_recipes.add_argument("--id", help="Look up a specific entry by ID")
    p_cat_recipes.add_argument("--page", type=int, help="Page number (default: 1)")
    p_cat_recipes.add_argument("--page-size", type=int, help="Results per page (default: 20, max: 50)")
    recipes_cat_sub = p_cat_recipes.add_subparsers(dest="recipes_subcmd")
    p_trace = recipes_cat_sub.add_parser("trace", help="Trace full ingredient tree for an item or recipe")
    p_trace.add_argument("trace_item", help="Item ID or recipe ID to trace")

    # Friendly aliases for common queries
    for alias, help_text in [("notes", "List your notes"),
                              ("trades", "List pending trades"),
                              ("ships", "List owned ships"),
                              ("faction-list", "List all factions"),
                              ("faction-invites", "Pending faction invites"),
                              ("forum", "Browse and post to the forum"),
                              ("battle-status", "View current battle state")]:
        p = sub.add_parser(alias, help=help_text)
        p.add_argument("extra", nargs="*")
    p_ch_hist = sub.add_parser("chat-history", help="Chat message history")
    p_ch_hist.add_argument("extra", nargs="*", help="[channel] [limit] [target_id]")

    # shipyard group
    p_shipyard = sub.add_parser("shipyard", help="Shipyard: browse, commission, buy/sell ships (shows listings by default)")
    p_shipyard.add_argument("--json", action="store_true", help="Output raw JSON")
    shipyard_sub = p_shipyard.add_subparsers(dest="shipyard_cmd")

    p_sy_browse = shipyard_sub.add_parser("browse", help="Browse player-listed ships at current base")
    p_sy_browse.add_argument("--class", dest="ship_class", metavar="CLASS", help="Filter by ship class")
    p_sy_browse.add_argument("--max-price", type=int, metavar="N", help="Maximum price filter")
    p_sy_browse.add_argument("--base", metavar="ID", help="Base ID to browse at")

    p_sy_showroom = shipyard_sub.add_parser("showroom", help="Pre-built ships in stock")
    p_sy_showroom.add_argument("--category", metavar="CAT", help="Filter by category")
    p_sy_showroom.add_argument("--scale", type=int, metavar="N", help="Filter by scale")

    p_sy_quote = shipyard_sub.add_parser("quote", help="Get commission pricing")
    p_sy_quote.add_argument("ship_class", help="Ship class to get quote for")

    p_sy_commission = shipyard_sub.add_parser("commission", help="Place a build order")
    p_sy_commission.add_argument("ship_class", help="Ship class to commission")
    p_sy_commission.add_argument("--provide-materials", action="store_true", help="Supply your own materials for reduced cost")

    p_sy_status = shipyard_sub.add_parser("status", help="View your active commissions")
    p_sy_status.add_argument("--base", metavar="ID", help="Base ID to check")

    p_sy_supply = shipyard_sub.add_parser("supply", help="Supply materials to a commission")
    p_sy_supply.add_argument("commission_id", help="Commission ID")
    p_sy_supply.add_argument("item_id", help="Item ID to supply")
    p_sy_supply.add_argument("quantity", type=int, help="Quantity to supply")

    p_sy_cancel = shipyard_sub.add_parser("cancel", help="Cancel a commission (50%% refund)")
    p_sy_cancel.add_argument("commission_id", help="Commission ID to cancel")

    p_sy_claim = shipyard_sub.add_parser("claim", help="Pick up a finished ship")
    p_sy_claim.add_argument("commission_id", help="Commission ID to claim")

    p_sy_list = shipyard_sub.add_parser("list", help="List your ship for sale (1%% fee)")
    p_sy_list.add_argument("ship_id", help="Ship ID to list")
    p_sy_list.add_argument("price", type=int, help="Asking price in credits")

    p_sy_buy = shipyard_sub.add_parser("buy", help="Buy a listed ship")
    p_sy_buy.add_argument("listing_id", help="Listing ID to buy")

    p_sy_unlist = shipyard_sub.add_parser("unlist", help="Cancel your ship listing")
    p_sy_unlist.add_argument("listing_id", help="Listing ID to cancel")

    # complain
    p_complain = sub.add_parser("complain", help="Log a complaint about sm client usability")
    p_complain.add_argument("complaint_text", help="What's bugging you? (quote your complaint)")

    # schema
    p_schema = sub.add_parser("schema", help="Show API schema for a command")
    p_schema.add_argument("schema_command", nargs="?", help="Command/endpoint name (e.g. buy, travel)")
    p_schema.add_argument("--list", action="store_true", dest="schema_list", help="List all endpoints")

    return parser


def _deprecated_skills():
    print("Skills commands have moved to the catalog:")
    print("  sm catalog skills                    Browse all skill definitions")
    print("  sm catalog skills --search <query>   Search skills by name/category")
    print("  sm catalog skills --id <skill_id>    Look up a specific skill")


def _deprecated_recipes():
    print("Recipe browsing has moved to the catalog:")
    print("  sm catalog recipes                       Browse all recipes")
    print("  sm catalog recipes --search <query>       Search recipes")
    print("  sm catalog recipes trace <item>           Trace full ingredient tree")
    print("  sm craft <recipe_id> [count]              Craft a recipe")


COMMAND_MAP = {
    "register": commands.cmd_register,
    "login": commands.cmd_login,
    "claim": commands.cmd_claim,
    "status": commands.cmd_status,
    "ship": commands.cmd_ship,
    "pois": commands.cmd_pois,
    "system": commands.cmd_system,
    "poi": commands.cmd_poi,
    "base": commands.cmd_base,
    "log": commands.cmd_log,
    "log-add": commands.cmd_log_add,
    "cargo": commands.cmd_cargo,
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
    "recipes": lambda api, args: _deprecated_recipes(),
    "query-recipes": lambda api, args: _deprecated_recipes(),
    "missions": commands.cmd_missions_router,     # NEW: hierarchical router
    "active-missions": commands.cmd_active_missions,  # Keep for backwards compatibility
    "query-missions": commands.cmd_query_missions,     # Keep for backwards compatibility
    "skills": commands.cmd_skills,
    "skill": lambda api, args: _deprecated_skills(),
    "query-skills": lambda api, args: _deprecated_skills(),
    "commands": commands.cmd_commands,
    "help": commands.cmd_commands,
    "chat": commands.cmd_chat,
    "raw": commands.cmd_raw,
    "chat-history": commands.cmd_chat_history,
    "notes": commands.cmd_notes,
    "trades": commands.cmd_trades,
    "ships": commands.cmd_ships,
    "faction-list": commands.cmd_faction_list,
    "faction-invites": commands.cmd_faction_invites,
    "forum": commands.cmd_forum,
    "battle-status": commands.cmd_battle_status,
    "catalog": commands.cmd_catalog,
    # Phase 4: Hierarchical commands
    "insurance": commands.cmd_insurance,
    "storage": commands.cmd_storage,
    "market": commands.cmd_market,
    "facility": commands.cmd_facility_router,
    "shipyard": commands.cmd_shipyard_router,
    "complain": commands.cmd_complain,
    "schema": lambda api, args: commands.cmd_schema_list(api, args) if getattr(args, "schema_list", False) else commands.cmd_schema(api, args),
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
        from spacemolt.commands.passthrough import _print_help, _all_categories
        _print_help(_all_categories())
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
        from spacemolt.commands.passthrough import _print_help, _all_categories
        _print_help(_all_categories())
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
