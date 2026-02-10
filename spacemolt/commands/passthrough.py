import json


__all__ = [
    "ENDPOINT_ARGS", "_parse_typed_value", "_arg_name",
    "cmd_passthrough", "cmd_commands", "cmd_raw",
    "cmd_notes", "cmd_trades", "cmd_drones", "cmd_ships_list",
    "cmd_chat_history", "cmd_faction_list", "cmd_faction_invites",
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
    "faction_list": [],
    "faction_get_invites": [],
    "set_home_base": [],
    "set_colors": ["primary_color", "secondary_color"],
    "set_status": ["status_message", "clan_tag"],
    "get_trades": [],
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
    "get_ships": [],
    "list_ships": [],
    "sell_ship": ["ship_id"],
    "switch_ship": ["ship_id"],
    # missions
    "accept_mission": ["mission_id"],
    "complete_mission": ["mission_id"],
    "abandon_mission": ["mission_id"],
    # notes
    "get_notes": [],
    "create_note": ["title", "content"],
    "write_note": ["note_id", "content"],
    "read_note": ["note_id"],
    # base building/raiding
    "build_base": ["name", "description"],
    "attack_base": ["base_id"],
    "loot_base_wreck": ["wreck_id", "item_id", "quantity:int"],
    "salvage_base_wreck": ["wreck_id"],
    # drones
    "get_drones": [],
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
    "get_chat_history": ["channel", "limit:int", "target_id"],
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


# ---------------------------------------------------------------------------
# Passthrough response formatters
# ---------------------------------------------------------------------------

def _fmt_chat_history(resp):
    r = resp.get("result", {})
    messages = r.get("messages", [])
    if not messages:
        print("No messages.")
        return
    for msg in messages:
        sender = msg.get("sender_name") or msg.get("sender") or msg.get("username", "?")
        content = msg.get("content") or msg.get("message", "")
        ts = msg.get("timestamp") or msg.get("created_at", "")
        if isinstance(ts, str) and len(ts) > 16:
            ts = ts[:16]
        ch = msg.get("channel", "")
        parts = []
        if ts:
            parts.append(f"[{ts}]")
        if ch:
            parts.append(f"[{ch}]")
        prefix = " ".join(parts)
        print(f"{prefix} {sender}: {content}")


def _fmt_notes(resp):
    r = resp.get("result", {})
    notes = r.get("notes", [])
    if not notes:
        print("No notes.")
        return
    for note in notes:
        nid = note.get("id") or note.get("note_id", "?")
        title = note.get("title", "(untitled)")
        updated = note.get("updated_at") or note.get("created_at", "")
        if isinstance(updated, str) and len(updated) > 10:
            updated = updated[:10]
        line = f"  {nid}: {title}"
        if updated:
            line += f"  ({updated})"
        print(line)


def _fmt_read_note(resp):
    r = resp.get("result", {})
    note = r.get("note", r)
    title = note.get("title", "(untitled)")
    content = note.get("content", "")
    nid = note.get("id") or note.get("note_id", "")
    print(f"# {title}")
    if nid:
        print(f"  id: {nid}")
    if content:
        print()
        print(content)


def _fmt_trades(resp):
    r = resp.get("result", {})
    trades = r.get("trades", [])
    if not trades:
        print("No pending trades.")
        return
    for t in trades:
        tid = t.get("id") or t.get("trade_id", "?")
        partner = (t.get("partner_name") or t.get("partner")
                   or t.get("target_name") or t.get("other_player", "?"))
        status = t.get("status", "?")
        print(f"Trade {tid} with {partner} [{status}]")
        for label, key in [("Offering", "items_offered"),
                           ("Requesting", "items_requested")]:
            items = t.get(key, [])
            if items:
                parts = []
                for item in items:
                    if isinstance(item, dict):
                        parts.append(f"{item.get('item_id', '?')} x{item.get('quantity', 1)}")
                    else:
                        parts.append(str(item))
                print(f"  {label}: {', '.join(parts)}")
        for label, key in [("Credits offered", "credits_offered"),
                           ("Credits requested", "credits_requested")]:
            val = t.get(key)
            if val:
                print(f"  {label}: {val}")


def _fmt_drones(resp):
    r = resp.get("result", {})
    drones = r.get("drones", [])
    if not drones:
        print("No active drones.")
        return
    for d in drones:
        did = d.get("id") or d.get("drone_id", "?")
        dtype = d.get("type") or d.get("drone_type") or d.get("name", "?")
        status = d.get("status", "?")
        target = d.get("target") or d.get("target_id", "")
        location = d.get("location") or d.get("poi_name", "")
        did_str = did[:8] if isinstance(did, str) and len(did) > 8 else str(did)
        line = f"  {dtype} ({did_str}) [{status}]"
        if target:
            line += f" -> {target}"
        if location:
            line += f" at {location}"
        print(line)


def _fmt_ships(resp):
    r = resp.get("result", {})
    ships = r.get("ships", [])
    if not ships:
        print("No ships owned.")
        return
    for s in ships:
        sid = s.get("id") or s.get("ship_id", "?")
        sclass = s.get("class_id") or s.get("ship_class") or s.get("class", "?")
        name = s.get("name", "")
        location = s.get("location") or s.get("system_name") or s.get("current_system", "")
        active = s.get("active", False) or s.get("is_active", False)
        hull = s.get("hull")
        max_hull = s.get("max_hull")
        label = name if name else sclass
        line = f"  {label}"
        if name and name != sclass:
            line += f" ({sclass})"
        sid_str = sid[:8] if isinstance(sid, str) and len(sid) > 8 else str(sid)
        line += f" id:{sid_str}"
        if active:
            line += " [ACTIVE]"
        if hull is not None and max_hull is not None:
            line += f" Hull:{hull}/{max_hull}"
        if location:
            line += f" @ {location}"
        print(line)


def _fmt_faction_list(resp):
    r = resp.get("result", {})
    factions = r.get("factions", [])
    if not factions:
        print("No factions found.")
        return
    for f in factions:
        fid = f.get("id") or f.get("faction_id", "?")
        name = f.get("name", "?")
        tag = f.get("tag", "")
        members = f.get("member_count") or f.get("members", "?")
        leader = f.get("leader_name") or f.get("leader", "")
        line = f"  [{tag}] {name}" if tag else f"  {name}"
        line += f"  (id:{fid})"
        line += f"  members:{members}"
        if leader:
            line += f"  leader:{leader}"
        print(line)


def _fmt_faction_info(resp):
    r = resp.get("result", {})
    faction = r.get("faction", r)
    name = faction.get("name", "?")
    tag = faction.get("tag", "")
    fid = faction.get("id") or faction.get("faction_id", "")
    header = f"[{tag}] {name}" if tag else name
    if fid:
        header += f" (id:{fid})"
    print(header)
    leader = faction.get("leader_name") or faction.get("leader", "")
    if leader:
        print(f"  Leader: {leader}")
    member_count = faction.get("member_count")
    if member_count is not None:
        print(f"  Members: {member_count}")
    members = faction.get("members", [])
    if members:
        print(f"\nMembers ({len(members)}):")
        for m in members:
            if isinstance(m, dict):
                mname = m.get("username") or m.get("name", "?")
                role = m.get("role", "")
                role_str = f" [{role}]" if role else ""
                print(f"  {mname}{role_str}")
            else:
                print(f"  {m}")
    for label, key in [("Allies", "allies"), ("Enemies", "enemies")]:
        items = faction.get(key, [])
        if items:
            names = []
            for a in items:
                if isinstance(a, dict):
                    names.append(a.get("name") or str(a.get("id", "?")))
                else:
                    names.append(str(a))
            print(f"\n{label}: {', '.join(names)}")


def _fmt_faction_invites(resp):
    r = resp.get("result", {})
    invites = r.get("invites", [])
    if not invites:
        print("No pending faction invites.")
        return
    for inv in invites:
        faction_name = inv.get("faction_name") or inv.get("name", "?")
        faction_id = inv.get("faction_id") or inv.get("id", "?")
        inviter = inv.get("invited_by") or inv.get("inviter", "")
        line = f"  {faction_name} (id:{faction_id})"
        if inviter:
            line += f"  invited by {inviter}"
        print(line)


_FORMATTERS = {
    "get_chat_history": _fmt_chat_history,
    "get_notes": _fmt_notes,
    "read_note": _fmt_read_note,
    "get_trades": _fmt_trades,
    "get_drones": _fmt_drones,
    "get_ships": _fmt_ships,
    "list_ships": _fmt_ships,
    "faction_list": _fmt_faction_list,
    "faction_info": _fmt_faction_info,
    "faction_get_invites": _fmt_faction_invites,
}


# ---------------------------------------------------------------------------
# Core passthrough handler
# ---------------------------------------------------------------------------

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

    # Check for missing required args (specs not covered by positional or key=value)
    if specs and not body:
        arg_names = " ".join(f"<{_arg_name(s)}>" for s in specs)
        print(f"Usage: sm {endpoint.replace('_', '-')} {arg_names}")
        return
    missing = [_arg_name(s) for s in specs if _arg_name(s) not in body]
    if missing:
        provided = " ".join(f"<{_arg_name(s)}>" for s in specs)
        print(f"Usage: sm {endpoint.replace('_', '-')} {provided}")
        print(f"Missing: {', '.join(missing)}")
        return

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
            formatter = _FORMATTERS.get(endpoint)
            if formatter:
                formatter(resp)
            else:
                result = resp.get("result", resp)
                # Try to extract a human-readable message from action results
                if isinstance(result, dict):
                    msg = result.get("message")
                    if msg:
                        print(msg)
                        for k, v in result.items():
                            if k == "message":
                                continue
                            if isinstance(v, (str, int, float, bool)):
                                print(f"  {k}: {v}")
                        return
                if isinstance(result, str):
                    print(result)
                else:
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


# ---------------------------------------------------------------------------
# Friendly command aliases (delegate to cmd_passthrough with correct endpoint)
# ---------------------------------------------------------------------------

def _make_passthrough_alias(endpoint):
    """Create a handler that delegates to cmd_passthrough for a specific endpoint."""
    def handler(api, args):
        extra = getattr(args, "extra", [])
        as_json = getattr(args, "json", False)
        cmd_passthrough(api, endpoint, extra, as_json=as_json)
    return handler


cmd_notes = _make_passthrough_alias("get_notes")
cmd_trades = _make_passthrough_alias("get_trades")
cmd_drones = _make_passthrough_alias("get_drones")
cmd_ships_list = _make_passthrough_alias("get_ships")
cmd_chat_history = _make_passthrough_alias("get_chat_history")
cmd_faction_list = _make_passthrough_alias("faction_list")
cmd_faction_invites = _make_passthrough_alias("faction_get_invites")
