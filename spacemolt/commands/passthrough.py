import json


__all__ = [
    "ENDPOINT_ARGS", "_parse_typed_value", "_arg_name",
    "cmd_passthrough", "cmd_commands", "cmd_raw",
]


# Mapping of endpoint names to their expected positional arg specs.
# Use "name:int" or "name:bool" for typed args; default is string.
ENDPOINT_ARGS = {
    "jump": ["target_system"],
    "buy": ["item_id", "quantity:int"],
    "scan": ["target_id"],
    "attack": ["target_id", "weapon_idx:int"],
    "travel": ["target_poi"],
    "chat": ["channel", "content", "target_id"],
    "craft": ["recipe_id"],
    "forum_reply": ["thread_id", "content"],
    "forum_get_thread": ["thread_id"],
    "forum_create_thread": ["title", "content", "category"],
    "sell": ["item_id", "quantity:int"],
    "loot_wreck": ["wreck_id", "item_id", "quantity:int"],
    "salvage_wreck": ["wreck_id"],
    "install_mod": ["module_id", "slot_idx:int"],
    "uninstall_mod": ["module_id"],
    "buy_ship": ["ship_class"],
    "find_route": ["target_system"],
    "search_systems": ["query"],
    "captains_log_add": ["entry"],
    "captains_log_get": ["index:int"],
    "set_anonymous": ["anonymous:bool"],
    "list_item": ["item_id", "quantity:int", "price_each:int"],
    "buy_listing": ["listing_id"],
    "cancel_list": ["listing_id"],
    "faction_invite": ["player_id"],
    "faction_kick": ["player_id"],
    "faction_promote": ["player_id", "role_id"],
    "faction_declare_war": ["target_faction_id", "reason"],
    "faction_propose_peace": ["target_faction_id", "terms"],
    "faction_accept_peace": ["target_faction_id"],
    "faction_set_ally": ["target_faction_id"],
    "faction_set_enemy": ["target_faction_id"],
    "faction_info": ["faction_id"],
    "join_faction": ["faction_id"],
    "faction_decline_invite": ["faction_id"],
    "create_faction": ["name", "tag"],
    "set_home_base": [],
    "set_colors": ["primary_color", "secondary_color"],
    "set_status": ["status_message", "clan_tag"],
    "trade_offer": ["target_id"],
    "trade_accept": ["trade_id"],
    "trade_decline": ["trade_id"],
    "trade_cancel": ["trade_id"],
    "buy_insurance": ["coverage_percent:int"],
    "forum_upvote": ["thread_id", "reply_id"],
    "forum_delete_thread": ["thread_id"],
    "forum_delete_reply": ["reply_id"],
    "forum_list": ["page:int", "category"],
    # combat
    "cloak": ["enable:bool"],
    "self_destruct": [],
    # market orders
    "create_sell_order": ["item_id", "quantity:int", "price_each:int"],
    "create_buy_order": ["item_id", "quantity:int", "price_each:int"],
    "cancel_order": ["order_id"],
    "modify_order": ["order_id", "new_price:int"],
    "view_market": ["item_id"],
    "estimate_purchase": ["item_id", "quantity:int"],
    # wrecks
    "jettison": ["item_id", "quantity:int"],
    # ships
    "sell_ship": ["ship_id"],
    "switch_ship": ["ship_id"],
    # missions
    "accept_mission": ["mission_id"],
    "complete_mission": ["mission_id"],
    "abandon_mission": ["mission_id"],
    # notes
    "create_note": ["title", "content"],
    "write_note": ["note_id", "content"],
    "read_note": ["note_id"],
    # base building/raiding
    "build_base": ["name", "description"],
    "attack_base": ["base_id"],
    "loot_base_wreck": ["wreck_id", "item_id", "quantity:int"],
    "salvage_base_wreck": ["wreck_id"],
    # drones
    "deploy_drone": ["drone_item_id", "target_id"],
    "recall_drone": ["drone_id"],
    "order_drone": ["command", "target_id"],
    # storage
    "deposit_items": ["item_id", "quantity:int"],
    "withdraw_items": ["item_id", "quantity:int"],
    "deposit_credits": ["amount:int"],
    "withdraw_credits": ["amount:int"],
    "send_gift": ["recipient", "item_id", "quantity:int"],
    # chat
    "get_chat_history": ["channel", "limit:int"],
    # insurance
    "claim_insurance": [],
    # faction
    "leave_faction": [],
    # misc
    "logout": [],
}


def _parse_typed_value(spec, value):
    """Convert a string value according to its type spec (e.g. 'quantity:int')."""
    if ":" in spec:
        _, type_name = spec.rsplit(":", 1)
    else:
        type_name = "str"

    if type_name == "int":
        return int(value)
    elif type_name == "bool":
        return value.lower() in ("true", "1", "yes")
    return value


def _arg_name(spec):
    """Extract the parameter name from a spec like 'quantity:int'."""
    return spec.split(":")[0]


def cmd_passthrough(api, endpoint, extra_args, as_json=False):
    """Generic passthrough: map positional/keyword args to API body and call endpoint."""
    body = {}
    specs = ENDPOINT_ARGS.get(endpoint, [])

    # Separate key=value pairs from positional args
    positional = []
    for arg in extra_args:
        if "=" in arg and not arg.startswith("="):
            key, val = arg.split("=", 1)
            # Find the matching spec for type conversion
            matching_spec = next((s for s in specs if _arg_name(s) == key), key)
            body[key] = _parse_typed_value(matching_spec, val)
        else:
            positional.append(arg)

    # Map positional args to parameter names
    for i, val in enumerate(positional):
        if i < len(specs):
            spec = specs[i]
            body[_arg_name(spec)] = _parse_typed_value(spec, val)
        else:
            # Extra positional with no spec — skip with warning
            print(f"Warning: extra argument ignored: {val}")

    resp = api._post(endpoint, body)
    if as_json:
        print(json.dumps(resp, indent=2))
    else:
        err = resp.get("error")
        if err:
            if isinstance(err, dict):
                print(f"ERROR: {err.get('message', err)}")
            else:
                print(f"ERROR: {err}")
        else:
            result = resp.get("result", resp)
            print(json.dumps(result, indent=2))


def cmd_commands(api, args):
    """List all available API endpoints grouped by category."""
    as_json = getattr(args, "json", False)
    resp = api._post("get_commands")
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    commands = resp.get("result", {}).get("commands", [])
    if not commands:
        # Fallback: dump raw
        print(json.dumps(resp.get("result", resp), indent=2))
        return

    # Group by category
    by_cat = {}
    for cmd in commands:
        cat = cmd.get("category", "other")
        by_cat.setdefault(cat, []).append(cmd)

    for cat in sorted(by_cat):
        print(f"\n{cat.upper()}")
        for cmd in sorted(by_cat[cat], key=lambda c: c.get("name", "")):
            name = cmd.get("name", "?")
            desc = cmd.get("description", "")
            if len(desc) > 70:
                desc = desc[:67] + "..."
            print(f"  {name:30s} {desc}")


def cmd_raw(api, args):
    body = {}
    if args.json_body:
        try:
            body = json.loads(args.json_body)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON: {e}", flush=True)
            return
    resp = api._post(args.endpoint, body)
    print(json.dumps(resp, indent=2))
