import json


__all__ = [
    "ENDPOINT_ARGS", "_parse_typed_value", "_arg_name",
    "cmd_passthrough", "cmd_commands", "cmd_raw",
    "cmd_notes", "cmd_trades", "cmd_drones", "cmd_ships",
    "cmd_chat_history", "cmd_faction_list", "cmd_faction_invites",
]


# Mapping of endpoint names to their expected positional arg specs.
# Use "name:int" or "name:bool" for typed args; default is string.
# Suffix with "?" for optional args (e.g., "target_id?").
# Note: Some endpoints include custom parameters not in the OpenAPI spec (marked with comments).
ENDPOINT_ARGS = {
    "jump": ["target_system"],
    "buy": ["item_id", "quantity:int"],
    "scan": ["target_id"],
    "attack": ["target_id", "weapon_idx?:int"],  # weapon_idx is custom extension
    "travel": ["target_poi"],
    "chat": ["channel", "content", "target_id?"],  # target_id optional per spec
    "craft": ["recipe_id", "count?:int"],  # count is optional batch parameter
    "forum_reply": ["thread_id", "content"],
    "forum_get_thread": ["thread_id"],
    "forum_create_thread": ["title", "content", "category?"],  # category is custom extension
    "sell": ["item_id", "quantity:int"],
    "loot_wreck": ["wreck_id", "item_id", "quantity:int"],
    "salvage_wreck": ["wreck_id"],
    "install_mod": ["module_id", "slot_idx?:int"],  # slot_idx is custom extension
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
    "faction_declare_war": ["target_faction_id", "reason?"],  # reason is optional
    "faction_propose_peace": ["target_faction_id", "terms?"],  # terms is optional
    "faction_accept_peace": ["target_faction_id"],
    "faction_set_ally": ["target_faction_id"],
    "faction_set_enemy": ["target_faction_id"],
    "faction_info": ["faction_id?"],  # faction_id is optional (defaults to your faction)
    "join_faction": ["faction_id"],
    "faction_decline_invite": ["faction_id"],
    "create_faction": ["name", "tag"],
    "faction_list": ["offset?:int", "limit?:int"],  # pagination params per spec
    "faction_get_invites": [],
    "set_home_base": ["base_id"],  # base_id is required per spec
    "set_colors": ["primary_color", "secondary_color"],
    "get_status": [],
    "set_status": ["status_message?", "clan_tag?"],  # both optional per spec
    "get_trades": [],
    "trade_offer": ["target_id", "credits?:int", "items?"],  # items is object (JSON string), credits optional
    "trade_accept": ["trade_id"],
    "trade_decline": ["trade_id"],
    "trade_cancel": ["trade_id"],
    "buy_insurance": ["ticks:int"],  # changed from coverage_percent to match spec
    "forum_upvote": ["thread_id", "reply_id?"],  # reply_id is optional
    "forum_delete_thread": ["thread_id"],
    "forum_delete_reply": ["reply_id"],
    "forum_list": ["page?:int", "category?"],  # page is optional, category is custom extension
    # combat
    "cloak": ["enable?:bool"],  # enable is custom extension (spec has no params)
    "self_destruct": [],
    # market orders - spec supports batch operations via "orders" array (pass as JSON string)
    "create_sell_order": ["item_id?", "quantity?:int", "price_each?:int", "orders?"],  # orders is array (JSON string)
    "create_buy_order": ["item_id?", "quantity?:int", "price_each?:int", "orders?"],  # orders is array (JSON string)
    "cancel_order": ["order_id?", "order_ids?"],  # order_ids is array (JSON string)
    "modify_order": ["order_id?", "new_price?:int", "orders?"],  # orders is array (JSON string)
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
    # notes - custom extensions (spec has no params for these)
    "get_notes": [],
    "create_note": ["title?", "content?"],  # custom extensions
    "write_note": ["note_id?", "content?"],  # custom extensions
    "read_note": ["note_id?"],  # custom extension
    # base building/raiding - custom extensions (spec has no params)
    "build_base": ["name?", "description?"],  # custom extensions
    "attack_base": ["base_id?"],  # custom extension
    "loot_base_wreck": ["wreck_id?", "item_id?", "quantity?:int"],  # custom extensions
    "salvage_base_wreck": ["wreck_id?"],  # custom extension
    # drones - custom extensions (spec has no params)
    "get_drones": [],
    "deploy_drone": ["drone_item_id?", "target_id?"],  # custom extensions
    "recall_drone": ["drone_id?"],  # custom extension
    "order_drone": ["command?", "target_id?"],  # custom extensions
    # storage
    "deposit_items": ["item_id", "quantity:int"],
    "withdraw_items": ["item_id", "quantity:int"],
    "deposit_credits": ["amount:int"],
    "withdraw_credits": ["amount:int"],
    "send_gift": ["recipient", "item_id?", "quantity?:int", "credits?:int", "message?"],  # item/qty/credits/message all optional
    # chat
    "get_chat_history": ["channel", "limit?:int", "target_id?", "before?"],  # limit/target/before all optional
    # insurance
    "claim_insurance": [],
    # faction
    "leave_faction": [],
    # misc
    "logout": [],
    # registration
    "register": ["username", "empire"],
    # missing endpoints (quick wins for completeness)
    "get_version": [],
    "get_map": [],
    "view_orders": [],
    "view_storage": [],
    "get_base_cost": ["base_type?"],  # base_type optional
    "raid_status": ["base_id?"],  # base_id optional
    "help": [],
    # New market and exploration commands
    "analyze_market": ["item_id?", "page?:int"],  # both optional
    "survey_system": [],  # no params
}


def _parse_typed_value(spec, value):
    """Convert a string value according to its type spec (e.g. 'quantity:int')."""
    if ":" in spec:
        _, type_name = spec.rsplit(":", 1)
    else:
        type_name = "str"

    if type_name == "int":
        try:
            return int(value)
        except (ValueError, TypeError) as e:
            param_name = _arg_name(spec)
            raise ValueError(f"Invalid integer value for '{param_name}': {value!r}")
    elif type_name == "bool":
        if value is None or not isinstance(value, str):
            param_name = _arg_name(spec)
            raise ValueError(f"Invalid boolean value for '{param_name}': {value!r}")
        return value.lower() in ("true", "1", "yes")
    return value


def _is_optional(spec):
    """Check if a spec is optional (trailing '?', e.g. 'target_id?')."""
    return spec.rstrip(":").endswith("?") or spec.split(":")[0].endswith("?")


def _arg_name(spec):
    """Extract the parameter name from a spec like 'quantity:int' or 'target_id?'."""
    return spec.split(":")[0].rstrip("?")


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


def _fmt_forum_list(resp):
    r = resp.get("result", {})
    threads = r.get("threads", [])
    if not threads:
        print("No forum threads.")
        return
    page = r.get("page", 1)
    total_pages = r.get("total_pages") or r.get("pages")
    if total_pages is not None:
        print(f"Forum threads (page {page}/{total_pages}):")
    else:
        print("Forum threads:")
    for t in threads:
        tid = t.get("id") or t.get("thread_id", "?")
        title = t.get("title", "(untitled)")
        author = t.get("author_name") or t.get("author") or t.get("username", "?")
        replies = t.get("reply_count") or t.get("replies", 0)
        upvotes = t.get("upvotes") or t.get("upvote_count", 0)
        category = t.get("category", "")
        tid_str = tid[:8] if isinstance(tid, str) and len(tid) > 8 else str(tid)
        cat_str = f"[{category}] " if category else ""
        print(f"  {cat_str}{title}")
        print(f"    by {author}  replies:{replies}  upvotes:{upvotes}  id:{tid_str}")


def _fmt_forum_get_thread(resp):
    r = resp.get("result", {})
    thread = r.get("thread", r)
    title = thread.get("title", "(untitled)")
    author = thread.get("author_name") or thread.get("author") or thread.get("username", "?")
    content = thread.get("content", "")
    upvotes = thread.get("upvotes") or thread.get("upvote_count", 0)
    category = thread.get("category", "")
    created = thread.get("created_at") or thread.get("timestamp", "")
    if isinstance(created, str) and len(created) > 16:
        created = created[:16]
    tid = thread.get("id") or thread.get("thread_id", "")
    cat_str = f"  [{category}]" if category else ""
    print(f"# {title}{cat_str}")
    meta = f"  by {author}"
    if created:
        meta += f"  {created}"
    meta += f"  upvotes:{upvotes}"
    if tid:
        tid_str = tid[:8] if isinstance(tid, str) and len(tid) > 8 else str(tid)
        meta += f"  id:{tid_str}"
    print(meta)
    if content:
        print()
        print(content)
    replies = thread.get("replies", [])
    if replies:
        print(f"\n--- Replies ({len(replies)}) ---")
        for reply in replies:
            rauthor = reply.get("author_name") or reply.get("author") or reply.get("username", "?")
            rcontent = reply.get("content", "")
            rupvotes = reply.get("upvotes") or reply.get("upvote_count", 0)
            rts = reply.get("created_at") or reply.get("timestamp", "")
            if isinstance(rts, str) and len(rts) > 16:
                rts = rts[:16]
            rid = reply.get("id") or reply.get("reply_id", "")
            rid_str = rid[:8] if isinstance(rid, str) and len(rid) > 8 else str(rid)
            ts_str = f"  {rts}" if rts else ""
            print(f"\n  {rauthor}{ts_str}  upvotes:{rupvotes}  id:{rid_str}")
            if rcontent:
                for line in rcontent.split("\n"):
                    print(f"    {line}")


def _fmt_attack(resp):
    r = resp.get("result", {})
    msg = r.get("message")
    if msg:
        print(msg)
    else:
        hit = r.get("hit", r.get("success", False))
        damage = r.get("damage", 0)
        target = r.get("target") or r.get("target_name", "target")
        if hit:
            print(f"Hit {target} for {damage} damage!")
        else:
            print(f"Missed {target}.")
    # Show extra result fields
    for k in ("target_hull", "target_shield", "hull", "shield"):
        v = r.get(k)
        if v is not None:
            print(f"  {k}: {v}")
    print("\n  Hint: sm status  |  sm nearby")


def _fmt_scan(resp):
    r = resp.get("result", {})
    scan = r.get("Result", r)
    success = scan.get("success", True)
    if not success:
        reason = scan.get("error") or scan.get("message") or scan.get("reason", "")
        if reason:
            print(f"Scan failed: {reason}")
        else:
            print(f"Scan failed.")
        print("\n  Hint: sm nearby  |  sm ship")
        return
    target = scan.get("target") or scan.get("target_name") or scan.get("target_id", "?")
    print(f"Scan of {target}:")
    revealed = scan.get("revealed_info") or scan
    for k, v in revealed.items():
        if k in ("success", "target", "target_name", "target_id", "revealed_info"):
            continue
        if isinstance(v, list):
            print(f"  {k}: {', '.join(str(i) for i in v)}")
        else:
            print(f"  {k}: {v}")
    target_id = scan.get("target_id") or target
    print(f"\n  Hint: sm attack {target_id}  |  sm trade-offer {target_id}")


def _fmt_version(resp):
    """Format get_version response."""
    r = resp.get("result", resp)
    # Handle plain string results
    if isinstance(r, str):
        print(r)
        return
    version = r.get("version", "unknown")
    build = r.get("build", "")
    api_version = r.get("api_version", "")
    print(f"SpaceMolt version: {version}")
    if build:
        print(f"  Build: {build}")
    if api_version:
        print(f"  API version: {api_version}")


def _fmt_map(resp):
    """Format get_map response."""
    r = resp.get("result", resp)
    # Handle plain string results
    if isinstance(r, str):
        print(r)
        return
    systems = r.get("systems", [])
    if not systems:
        print("No map data available.")
        return
    print(f"Galaxy Map ({len(systems)} systems):")
    for sys in systems[:20]:  # Limit to first 20
        if not isinstance(sys, dict):
            continue
        name = sys.get("name") or sys.get("system_id", "?")
        sid = sys.get("id") or sys.get("system_id", "")
        coords = sys.get("coordinates", {})
        x = coords.get("x", "?")
        y = coords.get("y", "?")
        print(f"  {name} ({sid}) @ ({x}, {y})")
    if len(systems) > 20:
        print(f"  ... and {len(systems) - 20} more systems")


def _fmt_view_orders(resp):
    """Format view_orders response (market orders)."""
    r = resp.get("result", resp)
    # Handle plain string results
    if isinstance(r, str):
        print(r)
        return
    orders = r.get("orders", [])
    if not orders:
        print("No active market orders.")
        print("  Hint: sm market buy <item> <qty> <price>  |  sm market sell <item> <qty> <price>")
        return
    print(f"Your Market Orders ({len(orders)}):")
    for order in orders:
        if not isinstance(order, dict):
            continue
        order_id = order.get("order_id") or order.get("id", "?")
        order_type = order.get("type", "?")
        item_id = order.get("item_id", "?")
        qty = order.get("quantity", 0)
        price = order.get("price_each") or order.get("price", 0)
        filled = order.get("filled", 0)
        remaining = qty - filled
        total = qty * price
        print(f"  [{order_type}] {item_id} x{remaining}/{qty} @ {price}cr ea (total: {total}cr) - ID: {order_id}")


def _fmt_view_storage(resp):
    """Format view_storage response (base storage contents)."""
    r = resp.get("result", resp)
    # Handle plain string results
    if isinstance(r, str):
        print(r)
        return
    items = r.get("items", [])
    credits = r.get("credits", 0)
    if not items and credits == 0:
        print("Storage is empty.")
        print("  Hint: sm storage deposit <item> <qty>  |  sm storage deposit --credits <amount>")
        return
    print("Base Storage:")
    if credits > 0:
        print(f"  Credits: {credits:,}")
    if items:
        print(f"  Items ({len(items)}):")
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = item.get("item_id", "?")
            qty = item.get("quantity", 0)
            print(f"    {item_id} x{qty}")


def _fmt_raid_status(resp):
    """Format raid_status response."""
    r = resp.get("result", resp)
    # Handle plain string results
    if isinstance(r, str):
        print(r)
        return
    status = r.get("status", "unknown")
    progress = r.get("progress", 0)
    defenders = r.get("defenders", [])
    base_id = r.get("base_id", "")
    print(f"Raid Status: {status}")
    if base_id:
        print(f"  Base: {base_id}")
    if progress:
        bar_length = 20
        filled = int((progress / 100) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"  Progress: [{bar}] {progress}%")
    if defenders:
        print(f"  Defenders ({len(defenders)}):")
        for defender in defenders[:10]:  # Limit to 10
            if isinstance(defender, dict):
                dname = defender.get("name") or defender.get("player_id", "?")
                print(f"    - {dname}")


def _fmt_help(resp):
    """Format help response."""
    r = resp.get("result", resp)
    help_text = r.get("help") or r.get("message") or r.get("content", "")
    if help_text:
        print(help_text)
    else:
        print(json.dumps(r, indent=2))


def _fmt_find_route(resp):
    """Format find_route response."""
    r = resp.get("result", resp)
    route = r.get("route", [])
    distance = r.get("distance") or r.get("jumps")
    target = r.get("target_system") or r.get("destination", "?")

    if not route:
        print(f"No route found to {target}")
        return

    print(f"Route to {target} ({len(route)} jumps):")
    for i, system in enumerate(route):
        if isinstance(system, dict):
            sys_name = system.get("name") or system.get("system_id", "?")
            sys_id = system.get("id") or system.get("system_id", "")
        else:
            sys_name = str(system)
            sys_id = ""

        prefix = "  └─" if i == len(route) - 1 else "  ├─"
        line = f"{prefix} {sys_name}"
        if sys_id and sys_id != sys_name:
            line += f" ({sys_id})"
        print(line)

    if distance:
        print(f"\nTotal distance: {distance} jumps")
    print("\n  Hint: sm jump <system_id>")


def _fmt_search_systems(resp):
    """Format search_systems response."""
    r = resp.get("result", resp)
    systems = r.get("systems", [])
    query = r.get("query", "")

    if not systems:
        print(f"No systems found matching '{query}'")
        return

    print(f"Found {len(systems)} system(s) matching '{query}':")
    for sys in systems[:20]:  # Limit to 20
        if isinstance(sys, dict):
            name = sys.get("name", "?")
            sys_id = sys.get("id") or sys.get("system_id", "")
            coords = sys.get("coordinates", {})
            x = coords.get("x") if isinstance(coords, dict) else "?"
            y = coords.get("y") if isinstance(coords, dict) else "?"
            police = sys.get("police_level")

            line = f"  {name}"
            if sys_id:
                line += f" ({sys_id})"
            line += f" @ ({x}, {y})"
            if police is not None:
                line += f"  [police: {police}]"
            print(line)
        else:
            print(f"  {sys}")

    if len(systems) > 20:
        print(f"\n... and {len(systems) - 20} more")
    print("\n  Hint: sm find-route <system_id>  |  sm jump <system_id>")


def _fmt_estimate_purchase(resp):
    """Format estimate_purchase response."""
    r = resp.get("result", resp)
    item_id = r.get("item_id", "?")
    quantity = r.get("quantity", 0)
    total_cost = r.get("total_cost", 0)
    avg_price = r.get("average_price", 0)
    available = r.get("available", 0)

    print(f"Purchase estimate for {item_id} x{quantity}:")
    print(f"  Total cost: {total_cost:,} cr")
    if avg_price:
        print(f"  Average price: {avg_price:.2f} cr per unit")
    if available is not None:
        print(f"  Available: {available} units")
        if available < quantity:
            print(f"  ⚠️  Warning: Only {available} units available (need {quantity})")

    print(f"\n  Hint: sm buy {item_id} {quantity}")


def _fmt_craft(resp):
    """Format craft response."""
    r = resp.get("result", resp)
    recipe_id = r.get("recipe_id", "?")
    item_id = r.get("item_id") or r.get("output_item", "?")
    quantity = r.get("quantity", 1)
    success = r.get("success", True)

    if success:
        print(f"✓ Crafted {item_id} x{quantity}")
    else:
        print(f"✗ Failed to craft {recipe_id}")
        reason = r.get("reason") or r.get("error", "")
        if reason:
            print(f"  Reason: {reason}")

    # Show what was consumed
    consumed = r.get("consumed", [])
    if consumed:
        print("\n  Consumed:")
        for item in consumed:
            if isinstance(item, dict):
                iid = item.get("item_id", "?")
                qty = item.get("quantity", 1)
                print(f"    - {iid} x{qty}")

    print("\n  Hint: sm cargo  |  sm recipes")


def _fmt_jettison(resp):
    """Format jettison response."""
    r = resp.get("result", resp)
    item_id = r.get("item_id", "?")
    quantity = r.get("quantity", 0)

    print(f"Jettisoned {item_id} x{quantity}")
    remaining = r.get("remaining_quantity")
    if remaining is not None:
        print(f"  Remaining in cargo: {remaining}")

    print("\n  Hint: sm cargo  |  sm nearby (to see if anyone picks it up)")


def _fmt_buy_ship(resp):
    """Format buy_ship response."""
    r = resp.get("result", resp)
    ship_class = r.get("ship_class") or r.get("class_id", "?")
    cost = r.get("cost", 0)
    ship_id = r.get("ship_id") or r.get("id", "")

    print(f"✓ Purchased {ship_class}")
    print(f"  Cost: {cost:,} cr")
    if ship_id:
        sid_short = ship_id[:8] if len(ship_id) > 8 else ship_id
        print(f"  Ship ID: {sid_short}")

    print("\n  Hint: sm switch-ship <ship_id>  |  sm ships")


def _fmt_switch_ship(resp):
    """Format switch_ship response."""
    r = resp.get("result", resp)
    ship_class = r.get("ship_class") or r.get("class_id", "?")
    ship_id = r.get("ship_id") or r.get("id", "")

    print(f"Switched to {ship_class}")
    if ship_id:
        sid_short = ship_id[:8] if len(ship_id) > 8 else ship_id
        print(f"  Ship ID: {sid_short}")

    print("\n  Hint: sm ship  |  sm status")


def _fmt_install_mod(resp):
    """Format install_mod response."""
    r = resp.get("result", resp)
    module_id = r.get("module_id", "?")
    slot_idx = r.get("slot_idx") or r.get("slot", "?")

    print(f"✓ Installed {module_id}")
    print(f"  Slot: {slot_idx}")

    # Show any bonuses
    bonuses = r.get("bonuses", {})
    if bonuses:
        print("\n  Bonuses:")
        for key, val in bonuses.items():
            print(f"    {key}: +{val}")

    print("\n  Hint: sm ship  |  sm listings")


def _fmt_uninstall_mod(resp):
    """Format uninstall_mod response."""
    r = resp.get("result", resp)
    module_id = r.get("module_id", "?")

    print(f"✓ Uninstalled {module_id}")
    print(f"  Module returned to cargo")

    print("\n  Hint: sm ship  |  sm cargo")


def _fmt_loot_wreck(resp):
    """Format loot_wreck response."""
    r = resp.get("result", resp)
    item_id = r.get("item_id", "?")
    quantity = r.get("quantity", 0)
    wreck_id = r.get("wreck_id", "")

    print(f"Looted {item_id} x{quantity} from wreck")

    remaining = r.get("remaining_items", [])
    if remaining:
        print(f"\n  Wreck still contains {len(remaining)} item types")

    print("\n  Hint: sm wrecks  |  sm salvage-wreck <wreck_id>")


def _fmt_salvage_wreck(resp):
    """Format salvage_wreck response."""
    r = resp.get("result", resp)
    wreck_id = r.get("wreck_id", "")
    items = r.get("items", [])

    print(f"Salvaged wreck")
    if items:
        print(f"\n  Recovered:")
        for item in items:
            if isinstance(item, dict):
                iid = item.get("item_id", "?")
                qty = item.get("quantity", 1)
                print(f"    - {iid} x{qty}")

    print("\n  Hint: sm cargo  |  sm wrecks")


def _fmt_jump(resp):
    """Format jump response."""
    r = resp.get("result", resp)
    target = r.get("target_system") or r.get("system", "?")
    fuel_cost = r.get("fuel_cost") or r.get("fuel_used")

    print(f"Jumped to {target}")
    if fuel_cost:
        print(f"  Fuel used: {fuel_cost}")

    # Show arrival info
    arrived_at = r.get("arrived_at") or r.get("location")
    if arrived_at:
        print(f"  Location: {arrived_at}")

    print("\n  Hint: sm system  |  sm pois  |  sm nearby")


def _fmt_trade_offer(resp):
    """Format trade_offer response."""
    r = resp.get("result", resp)
    trade_id = r.get("trade_id") or r.get("id", "")
    target = r.get("target") or r.get("target_name", "?")

    print(f"Trade offer sent to {target}")
    if trade_id:
        tid_short = trade_id[:8] if len(trade_id) > 8 else trade_id
        print(f"  Trade ID: {tid_short}")

    print("\n  Hint: sm trades  |  sm trade-cancel <trade_id>")


def _fmt_trade_accept(resp):
    """Format trade_accept response."""
    r = resp.get("result", resp)
    print("✓ Trade accepted")

    # Show what was exchanged
    received_items = r.get("received_items", [])
    received_credits = r.get("received_credits", 0)
    gave_items = r.get("gave_items", [])
    gave_credits = r.get("gave_credits", 0)

    if received_items or received_credits:
        print("\n  Received:")
        if received_credits:
            print(f"    {received_credits:,} cr")
        for item in received_items:
            if isinstance(item, dict):
                print(f"    {item.get('item_id', '?')} x{item.get('quantity', 1)}")

    if gave_items or gave_credits:
        print("\n  Gave:")
        if gave_credits:
            print(f"    {gave_credits:,} cr")
        for item in gave_items:
            if isinstance(item, dict):
                print(f"    {item.get('item_id', '?')} x{item.get('quantity', 1)}")

    print("\n  Hint: sm cargo  |  sm status")


def _fmt_trade_decline(resp):
    """Format trade_decline response."""
    print("Trade declined")
    print("\n  Hint: sm trades")


def _fmt_trade_cancel(resp):
    """Format trade_cancel response."""
    print("Trade cancelled")
    print("\n  Hint: sm trades")


def _fmt_create_buy_order(resp):
    """Format create_buy_order response."""
    r = resp.get("result", resp)
    item_id = r.get("item_id", "?")
    quantity = r.get("quantity", 0)
    price = r.get("price_each") or r.get("price", 0)
    order_id = r.get("order_id") or r.get("id", "")
    fee = r.get("listing_fee") or r.get("fee", 0)

    print(f"✓ Buy order created: {item_id} x{quantity} @ {price} cr")
    if fee:
        print(f"  Listing fee: {fee} cr")
    if order_id:
        oid_short = order_id[:8] if len(order_id) > 8 else order_id
        print(f"  Order ID: {oid_short}")

    escrowed = quantity * price + fee
    print(f"  Escrowed: {escrowed:,} cr")

    print("\n  Hint: sm market  |  sm listings " + item_id)


def _fmt_create_sell_order(resp):
    """Format create_sell_order response."""
    r = resp.get("result", resp)
    item_id = r.get("item_id", "?")
    quantity = r.get("quantity", 0)
    price = r.get("price_each") or r.get("price", 0)
    order_id = r.get("order_id") or r.get("id", "")
    fee = r.get("listing_fee") or r.get("fee", 0)

    print(f"✓ Sell order created: {item_id} x{quantity} @ {price} cr")
    if fee:
        print(f"  Listing fee: {fee} cr")
    if order_id:
        oid_short = order_id[:8] if len(order_id) > 8 else order_id
        print(f"  Order ID: {oid_short}")

    potential = quantity * price
    print(f"  Potential revenue: {potential:,} cr")

    print("\n  Hint: sm market  |  sm listings " + item_id)


def _fmt_cancel_order(resp):
    """Format cancel_order response."""
    r = resp.get("result", resp)
    order_id = r.get("order_id") or r.get("id", "")

    print("✓ Order cancelled")
    if order_id:
        oid_short = order_id[:8] if len(order_id) > 8 else order_id
        print(f"  Order ID: {oid_short}")

    # Show what was returned
    refunded_credits = r.get("refunded_credits", 0)
    returned_items = r.get("returned_items", [])

    if refunded_credits:
        print(f"  Refunded: {refunded_credits:,} cr")
    if returned_items:
        print("  Returned to cargo:")
        for item in returned_items:
            if isinstance(item, dict):
                print(f"    {item.get('item_id', '?')} x{item.get('quantity', 1)}")

    print("\n  Hint: sm market")


def _fmt_modify_order(resp):
    """Format modify_order response."""
    r = resp.get("result", resp)
    order_id = r.get("order_id") or r.get("id", "")
    new_price = r.get("new_price", "?")

    print("✓ Order modified")
    if order_id:
        oid_short = order_id[:8] if len(order_id) > 8 else order_id
        print(f"  Order ID: {oid_short}")
    print(f"  New price: {new_price} cr")

    print("\n  Hint: sm market")


def _fmt_deposit_items(resp):
    """Format deposit_items response."""
    r = resp.get("result", resp)
    item_id = r.get("item_id", "?")
    quantity = r.get("quantity", 0)

    print(f"Deposited {item_id} x{quantity} to storage")
    print("\n  Hint: sm storage  |  sm cargo")


def _fmt_withdraw_items(resp):
    """Format withdraw_items response."""
    r = resp.get("result", resp)
    item_id = r.get("item_id", "?")
    quantity = r.get("quantity", 0)

    print(f"Withdrawn {item_id} x{quantity} from storage")
    print("\n  Hint: sm storage  |  sm cargo")


def _fmt_deposit_credits(resp):
    """Format deposit_credits response."""
    r = resp.get("result", resp)
    amount = r.get("amount", 0)

    print(f"Deposited {amount:,} cr to storage")
    print("\n  Hint: sm storage  |  sm status")


def _fmt_withdraw_credits(resp):
    """Format withdraw_credits response."""
    r = resp.get("result", resp)
    amount = r.get("amount", 0)

    print(f"Withdrawn {amount:,} cr from storage")
    print("\n  Hint: sm storage  |  sm status")


def _fmt_send_gift(resp):
    """Format send_gift response."""
    r = resp.get("result", resp)
    recipient = r.get("recipient", "?")

    print(f"✓ Gift sent to {recipient}")

    items = r.get("items", [])
    credits = r.get("credits", 0)

    if credits:
        print(f"  Credits: {credits:,} cr")
    if items:
        print("  Items:")
        for item in items:
            if isinstance(item, dict):
                print(f"    {item.get('item_id', '?')} x{item.get('quantity', 1)}")

    print("\n  Hint: sm cargo  |  sm status")


def _fmt_join_faction(resp):
    """Format join_faction response."""
    r = resp.get("result", resp)
    faction_name = r.get("faction_name") or r.get("name", "?")

    print(f"✓ Joined faction: {faction_name}")
    print("\n  Hint: sm faction-info  |  sm chat faction <message>")


def _fmt_leave_faction(resp):
    """Format leave_faction response."""
    r = resp.get("result", resp)
    faction_name = r.get("faction_name") or r.get("name", "?")

    print(f"Left faction: {faction_name}")
    print("\n  Hint: sm faction-list")


def _fmt_create_faction(resp):
    """Format create_faction response."""
    r = resp.get("result", resp)
    faction_name = r.get("name", "?")
    faction_tag = r.get("tag", "")
    faction_id = r.get("faction_id") or r.get("id", "")

    print(f"✓ Created faction: [{faction_tag}] {faction_name}")
    if faction_id:
        print(f"  Faction ID: {faction_id}")

    print("\n  Hint: sm faction-info  |  sm faction-invite <player_id>")


def _fmt_faction_invite(resp):
    """Format faction_invite response."""
    r = resp.get("result", resp)
    player = r.get("player_name") or r.get("player_id", "?")

    print(f"✓ Invited {player} to faction")
    print("\n  Hint: sm faction-info")


def _fmt_faction_kick(resp):
    """Format faction_kick response."""
    r = resp.get("result", resp)
    player = r.get("player_name") or r.get("player_id", "?")

    print(f"Kicked {player} from faction")
    print("\n  Hint: sm faction-info")


def _fmt_cloak(resp):
    """Format cloak response."""
    r = resp.get("result", resp)
    enabled = r.get("cloaked") or r.get("enabled", False)

    if enabled:
        print("✓ Cloaking device activated")
        print("  You are now hidden from casual scans")
    else:
        print("Cloaking device deactivated")

    fuel_drain = r.get("fuel_drain") or r.get("fuel_per_tick")
    if fuel_drain:
        print(f"  Fuel drain: {fuel_drain} per tick")

    print("\n  Hint: sm nearby  |  sm status")


def _fmt_set_home_base(resp):
    """Format set_home_base response."""
    r = resp.get("result", resp)
    base = r.get("base_name") or r.get("base_id", "?")

    print(f"✓ Home base set: {base}")
    print("\n  Hint: sm base  |  sm status")


def _fmt_accept_mission(resp):
    """Format accept_mission response."""
    r = resp.get("result", resp)
    mission_title = r.get("title") or r.get("mission_name", "?")
    mission_id = r.get("mission_id") or r.get("id", "")

    print(f"✓ Mission accepted: {mission_title}")
    if mission_id:
        mid_short = mission_id[:8] if len(mission_id) > 8 else mission_id
        print(f"  Mission ID: {mid_short}")

    print("\n  Hint: sm missions  |  sm active-missions")


def _fmt_complete_mission(resp):
    """Format complete_mission response."""
    r = resp.get("result", resp)
    mission_title = r.get("title") or r.get("mission_name", "?")
    reward_credits = r.get("reward_credits") or r.get("credits", 0)
    reward_items = r.get("reward_items", [])

    print(f"✓ Mission completed: {mission_title}")

    if reward_credits:
        print(f"  Reward: {reward_credits:,} cr")

    if reward_items:
        print("  Items:")
        for item in reward_items:
            if isinstance(item, dict):
                print(f"    {item.get('item_id', '?')} x{item.get('quantity', 1)}")

    print("\n  Hint: sm missions  |  sm status")


def _fmt_abandon_mission(resp):
    """Format abandon_mission response."""
    r = resp.get("result", resp)
    mission_title = r.get("title") or r.get("mission_name", "?")

    print(f"Abandoned mission: {mission_title}")
    print("\n  Hint: sm missions")


def _fmt_buy_insurance(resp):
    """Format buy_insurance response."""
    r = resp.get("result", resp)
    cost = r.get("cost") or r.get("premium", 0)
    coverage = r.get("coverage_percent") or r.get("coverage", "?")
    ticks = r.get("ticks") or r.get("duration", "?")

    print(f"✓ Insurance purchased: {coverage}% coverage for {ticks} ticks")
    print(f"  Cost: {cost:,} cr")

    print("\n  Hint: sm insurance  |  sm status")


def _fmt_claim_insurance(resp):
    """Format claim_insurance response."""
    r = resp.get("result", resp)
    payout = r.get("payout", 0)

    print(f"✓ Insurance claimed")
    print(f"  Payout: {payout:,} cr")

    print("\n  Hint: sm status  |  sm shipyard")


def _fmt_sell_ship(resp):
    """Format sell_ship response."""
    r = resp.get("result", resp)
    ship_class = r.get("ship_class") or r.get("class_id", "?")
    value = r.get("value") or r.get("price", 0)

    print(f"✓ Sold {ship_class}")
    print(f"  Value: {value:,} cr")

    print("\n  Hint: sm ships  |  sm status")


def _fmt_forum_reply(resp):
    """Format forum_reply response."""
    r = resp.get("result", resp)
    thread_title = r.get("thread_title") or r.get("title", "")
    reply_id = r.get("reply_id") or r.get("id", "")

    print("✓ Reply posted" + (f" to: {thread_title}" if thread_title else ""))
    if reply_id:
        rid_short = reply_id[:8] if len(reply_id) > 8 else reply_id
        print(f"  Reply ID: {rid_short}")

    print("\n  Hint: sm forum-get-thread <thread_id>")


def _fmt_forum_create_thread(resp):
    """Format forum_create_thread response."""
    r = resp.get("result", resp)
    title = r.get("title", "?")
    thread_id = r.get("thread_id") or r.get("id", "")
    category = r.get("category", "")

    cat_str = f" [{category}]" if category else ""
    print(f"✓ Thread created{cat_str}: {title}")
    if thread_id:
        tid_short = thread_id[:8] if len(thread_id) > 8 else thread_id
        print(f"  Thread ID: {tid_short}")

    print("\n  Hint: sm forum-list  |  sm forum-get-thread " + (thread_id or "<thread_id>"))


def _fmt_forum_upvote(resp):
    """Format forum_upvote response."""
    r = resp.get("result", resp)
    upvotes = r.get("upvotes") or r.get("total_upvotes", "?")

    print(f"✓ Upvoted (now {upvotes} upvotes)")
    print("\n  Hint: sm forum-list")


def _fmt_forum_delete_thread(resp):
    """Format forum_delete_thread response."""
    print("✓ Thread deleted")
    print("\n  Hint: sm forum-list")


def _fmt_forum_delete_reply(resp):
    """Format forum_delete_reply response."""
    print("✓ Reply deleted")
    print("\n  Hint: sm forum-get-thread <thread_id>")


def _fmt_set_anonymous(resp):
    """Format set_anonymous response."""
    r = resp.get("result", resp)
    anonymous = r.get("anonymous", False)

    if anonymous:
        print("✓ Anonymous mode enabled")
        print("  Your identity is hidden from casual observers")
    else:
        print("Anonymous mode disabled")
        print("  Your identity is visible")

    print("\n  Hint: sm status  |  sm nearby")


def _fmt_set_colors(resp):
    """Format set_colors response."""
    r = resp.get("result", resp)
    primary = r.get("primary_color", "?")
    secondary = r.get("secondary_color", "?")

    print(f"✓ Ship colors set")
    print(f"  Primary: {primary}")
    print(f"  Secondary: {secondary}")

    print("\n  Hint: sm ship")


def _fmt_set_status(resp):
    """Format set_status response."""
    r = resp.get("result", resp)
    status = r.get("status_message", "")
    clan_tag = r.get("clan_tag", "")

    print("✓ Status updated")
    if status:
        print(f"  Message: {status}")
    if clan_tag:
        print(f"  Clan tag: {clan_tag}")

    print("\n  Hint: sm status")


def _fmt_build_base(resp):
    """Format build_base response."""
    r = resp.get("result", resp)
    base_name = r.get("name") or r.get("base_name", "?")
    base_id = r.get("base_id") or r.get("id", "")
    cost = r.get("cost", 0)

    print(f"✓ Base constructed: {base_name}")
    if base_id:
        bid_short = base_id[:8] if len(base_id) > 8 else base_id
        print(f"  Base ID: {bid_short}")
    if cost:
        print(f"  Cost: {cost:,} cr")

    print("\n  Hint: sm base  |  sm set-home-base <base_id>")


def _fmt_attack_base(resp):
    """Format attack_base response."""
    r = resp.get("result", resp)
    base_name = r.get("base_name") or r.get("target", "?")
    damage = r.get("damage", 0)
    base_hull = r.get("base_hull")

    print(f"Attacked {base_name}")
    if damage:
        print(f"  Damage dealt: {damage}")
    if base_hull is not None:
        print(f"  Base hull remaining: {base_hull}")

    print("\n  Hint: sm raid-status <base_id>  |  sm nearby")


def _fmt_deploy_drone(resp):
    """Format deploy_drone response."""
    r = resp.get("result", resp)
    drone_type = r.get("drone_type") or r.get("type", "?")
    drone_id = r.get("drone_id") or r.get("id", "")

    print(f"✓ Deployed {drone_type}")
    if drone_id:
        did_short = drone_id[:8] if len(drone_id) > 8 else drone_id
        print(f"  Drone ID: {did_short}")

    print("\n  Hint: sm drones  |  sm order-drone <command> <target>")


def _fmt_recall_drone(resp):
    """Format recall_drone response."""
    r = resp.get("result", resp)
    drone_type = r.get("drone_type") or r.get("type", "?")

    print(f"✓ Recalled {drone_type}")
    print("\n  Hint: sm drones")


def _fmt_order_drone(resp):
    """Format order_drone response."""
    r = resp.get("result", resp)
    command = r.get("command", "?")
    target = r.get("target") or r.get("target_id", "")

    print(f"✓ Drone order: {command}" + (f" -> {target}" if target else ""))
    print("\n  Hint: sm drones")


def _fmt_logout(resp):
    """Format logout response."""
    print("✓ Logged out")
    print("\n  Hint: sm login")


def _fmt_analyze_market(resp):
    """Format analyze_market response."""
    r = resp.get("result", resp)
    item_id = r.get("item_id", "?")
    item_name = r.get("item_name", item_id)
    systems = r.get("systems", [])
    skill_level = r.get("skill_level") or r.get("market_analysis_level")
    range_systems = r.get("range") or r.get("systems_scanned")

    print(f"Market Analysis: {item_name} ({item_id})")

    if skill_level is not None:
        print(f"  Market Analysis Skill: Level {skill_level}")
    if range_systems is not None:
        print(f"  Systems scanned: {range_systems}")

    if not systems:
        print("\n  No market data found in range")
        print("\n  Hint: Increase market_analysis skill to scan more systems")
        return

    # Group by best opportunities
    print(f"\n  Found markets in {len(systems)} systems:")

    # Sort by best price spread (buy low, sell high)
    systems_with_spread = []
    for sys_data in systems:
        if not isinstance(sys_data, dict):
            continue
        sys_name = sys_data.get("system_name") or sys_data.get("system_id", "?")
        sys_id = sys_data.get("system_id", "")
        best_buy = sys_data.get("best_buy_price")
        best_sell = sys_data.get("best_sell_price")
        distance = sys_data.get("distance") or sys_data.get("jumps", "?")

        if best_buy is not None or best_sell is not None:
            spread = (best_sell or 0) - (best_buy or 0)
            systems_with_spread.append((sys_name, sys_id, best_buy, best_sell, spread, distance))

    # Sort by spread descending
    systems_with_spread.sort(key=lambda x: x[4], reverse=True)

    # Display top opportunities
    for sys_name, sys_id, best_buy, best_sell, spread, distance in systems_with_spread[:15]:
        buy_str = f"{best_buy} cr" if best_buy else "---"
        sell_str = f"{best_sell} cr" if best_sell else "---"
        spread_str = f"+{spread}" if spread > 0 else str(spread) if spread else "---"
        dist_str = f"{distance}j" if distance != "?" else "?"

        line = f"    {sys_name:20s}  Buy:{buy_str:>8s}  Sell:{sell_str:>8s}  Spread:{spread_str:>6s}  ({dist_str})"
        print(line)

    if len(systems_with_spread) > 15:
        print(f"\n  ... and {len(systems_with_spread) - 15} more systems")

    # Show best trade route
    if len(systems_with_spread) >= 2:
        # Find best buy location
        best_buy_sys = min(systems_with_spread, key=lambda x: x[2] if x[2] else float('inf'))
        # Find best sell location
        best_sell_sys = max(systems_with_spread, key=lambda x: x[3] if x[3] else 0)

        if best_buy_sys[2] and best_sell_sys[3] and best_buy_sys != best_sell_sys:
            profit = best_sell_sys[3] - best_buy_sys[2]
            print(f"\n  💡 Best trade route:")
            print(f"    Buy at {best_buy_sys[0]} ({best_buy_sys[2]} cr) → Sell at {best_sell_sys[0]} ({best_sell_sys[3]} cr)")
            print(f"    Profit: {profit} cr per unit")

    print(f"\n  Hint: sm find-route <system>  |  sm listings {item_id}")


def _fmt_survey_system(resp):
    """Format survey_system response."""
    r = resp.get("result", resp)
    system_name = r.get("system_name") or r.get("system", "?")
    system_id = r.get("system_id", "")
    skill_level = r.get("astrometrics_level") or r.get("skill_level")
    scanner_bonus = r.get("scanner_bonus") or r.get("module_bonus")

    print(f"System Survey: {system_name}" + (f" ({system_id})" if system_id else ""))

    if skill_level is not None:
        print(f"  Astrometrics Skill: Level {skill_level}")
    if scanner_bonus is not None:
        print(f"  Scanner Bonus: +{scanner_bonus}%")

    # Basic system info
    print("\n  System Properties:")
    for key in ["security_level", "police_level", "faction_control", "population"]:
        val = r.get(key)
        if val is not None:
            label = key.replace("_", " ").title()
            print(f"    {label}: {val}")

    # Points of Interest
    pois = r.get("points_of_interest", []) or r.get("pois", [])
    if pois:
        print(f"\n  Points of Interest ({len(pois)}):")
        for poi in pois[:20]:
            if isinstance(poi, dict):
                poi_name = poi.get("name", "?")
                poi_type = poi.get("type", "?")
                poi_id = poi.get("id") or poi.get("poi_id", "")
                resources = poi.get("resources", [])

                line = f"    [{poi_type:12s}] {poi_name}"
                if resources:
                    res_str = ", ".join(str(r) for r in resources[:3])
                    line += f"  ({res_str})"
                print(line)

                # Show hidden/detailed info if revealed by skill
                hidden_info = poi.get("hidden_info", {})
                if hidden_info:
                    for k, v in hidden_info.items():
                        print(f"        └─ {k}: {v}")

        if len(pois) > 20:
            print(f"    ... and {len(pois) - 20} more")

    # Resources
    resources = r.get("system_resources", []) or r.get("resources", [])
    if resources:
        print(f"\n  System Resources:")
        for res in resources:
            if isinstance(res, dict):
                res_name = res.get("name") or res.get("resource_id", "?")
                abundance = res.get("abundance", "?")
                quality = res.get("quality")
                print(f"    {res_name:20s}  Abundance: {abundance}" + (f"  Quality: {quality}" if quality else ""))
            else:
                print(f"    {res}")

    # Connections/routes
    connections = r.get("connections", []) or r.get("adjacent_systems", [])
    if connections:
        print(f"\n  Connected Systems ({len(connections)}):")
        for conn in connections[:10]:
            if isinstance(conn, dict):
                conn_name = conn.get("name") or conn.get("system_id", "?")
                distance = conn.get("distance") or conn.get("fuel_cost")
                print(f"    {conn_name}" + (f" ({distance} fuel)" if distance else ""))
            else:
                print(f"    {conn}")

    # Hidden discoveries (only shown with high astrometrics)
    discoveries = r.get("discoveries", []) or r.get("hidden_features", [])
    if discoveries:
        print(f"\n  ✨ Discoveries:")
        for disc in discoveries:
            if isinstance(disc, dict):
                disc_name = disc.get("name", "?")
                disc_type = disc.get("type", "")
                reward = disc.get("reward")
                print(f"    {disc_name}" + (f" [{disc_type}]" if disc_type else "") + (f" - Reward: {reward}" if reward else ""))
            else:
                print(f"    {disc}")

    print(f"\n  Hint: sm pois  |  sm system  |  sm travel <poi_id>")


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
    "forum_list": _fmt_forum_list,
    "forum_get_thread": _fmt_forum_get_thread,
    "attack": _fmt_attack,
    "scan": _fmt_scan,
    # New formatters
    "get_version": _fmt_version,
    "get_map": _fmt_map,
    "view_orders": _fmt_view_orders,
    "view_storage": _fmt_view_storage,
    "raid_status": _fmt_raid_status,
    "help": _fmt_help,
    "find_route": _fmt_find_route,
    "search_systems": _fmt_search_systems,
    "estimate_purchase": _fmt_estimate_purchase,
    "craft": _fmt_craft,
    "jettison": _fmt_jettison,
    "buy_ship": _fmt_buy_ship,
    "switch_ship": _fmt_switch_ship,
    "install_mod": _fmt_install_mod,
    "uninstall_mod": _fmt_uninstall_mod,
    "loot_wreck": _fmt_loot_wreck,
    "salvage_wreck": _fmt_salvage_wreck,
    "jump": _fmt_jump,
    # Trade commands
    "trade_offer": _fmt_trade_offer,
    "trade_accept": _fmt_trade_accept,
    "trade_decline": _fmt_trade_decline,
    "trade_cancel": _fmt_trade_cancel,
    # Market orders
    "create_buy_order": _fmt_create_buy_order,
    "create_sell_order": _fmt_create_sell_order,
    "cancel_order": _fmt_cancel_order,
    "modify_order": _fmt_modify_order,
    # Storage
    "deposit_items": _fmt_deposit_items,
    "withdraw_items": _fmt_withdraw_items,
    "deposit_credits": _fmt_deposit_credits,
    "withdraw_credits": _fmt_withdraw_credits,
    "send_gift": _fmt_send_gift,
    # Faction
    "join_faction": _fmt_join_faction,
    "leave_faction": _fmt_leave_faction,
    "create_faction": _fmt_create_faction,
    "faction_invite": _fmt_faction_invite,
    "faction_kick": _fmt_faction_kick,
    # Ship/combat
    "cloak": _fmt_cloak,
    "set_home_base": _fmt_set_home_base,
    # Missions
    "accept_mission": _fmt_accept_mission,
    "complete_mission": _fmt_complete_mission,
    "abandon_mission": _fmt_abandon_mission,
    # Insurance
    "buy_insurance": _fmt_buy_insurance,
    "claim_insurance": _fmt_claim_insurance,
    # Ships
    "sell_ship": _fmt_sell_ship,
    # Forum
    "forum_reply": _fmt_forum_reply,
    "forum_create_thread": _fmt_forum_create_thread,
    "forum_upvote": _fmt_forum_upvote,
    "forum_delete_thread": _fmt_forum_delete_thread,
    "forum_delete_reply": _fmt_forum_delete_reply,
    # Player settings
    "set_anonymous": _fmt_set_anonymous,
    "set_colors": _fmt_set_colors,
    "set_status": _fmt_set_status,
    # Base building
    "build_base": _fmt_build_base,
    "attack_base": _fmt_attack_base,
    # Drones
    "deploy_drone": _fmt_deploy_drone,
    "recall_drone": _fmt_recall_drone,
    "order_drone": _fmt_order_drone,
    # Misc
    "logout": _fmt_logout,
    # New market and exploration commands
    "analyze_market": _fmt_analyze_market,
    "survey_system": _fmt_survey_system,
}


def _print_error_hints(endpoint, err_msg, api=None):
    """Print contextual hints for common endpoint errors."""
    err_lower = err_msg.lower()

    # Scanner module missing
    if endpoint == "scan" and any(w in err_lower for w in ("module", "scanner", "equip", "install")):
        print("\n  You need a scanner module installed to scan ships.")
        print("  Hint: sm listings  |  sm ship  |  sm install-mod <module_id>")

    # Weapon module issues
    elif endpoint == "attack" and ("not a weapon" in err_lower or "no weapon" in err_lower
                                    or ("module" in err_lower and "weapon" in err_lower)):
        # Try to find actual weapon modules and suggest the right index
        weapons = _find_weapon_modules(api)
        if weapons:
            indices = ", ".join(str(idx) for idx, _ in weapons)
            names = ", ".join(f"{name} (index {idx})" for idx, name in weapons)
            print(f"\n  Your weapon modules: {names}")
            first_idx = weapons[0][0]
            print(f"  Hint: sm attack <target_id> {first_idx}")
        else:
            print("\n  You have no weapon modules installed.")
            print("  Hint: sm listings  |  sm install-mod <module_id>")
    elif endpoint == "attack" and any(w in err_lower for w in ("equip", "install")):
        print("\n  You need a weapon module installed to attack.")
        print("  Hint: sm listings  |  sm ship  |  sm install-mod <module_id>")

    # Mining errors
    elif endpoint == "mine" and any(w in err_lower for w in ("no resource", "not mineable", "no ore", "nothing to mine")):
        print("\n  No mineable resources at current location.")
        print("  Hint: sm pois (find asteroid belts or mining sites)")

    # Docking errors
    elif endpoint == "dock" and any(w in err_lower for w in ("no base", "no station", "not dockable", "can't dock")):
        print("\n  No dockable base or station at current location.")
        print("  Hint: sm pois (find bases)  |  sm travel <poi_id>")

    # Fuel errors
    elif any(w in err_lower for w in ("not enough fuel", "insufficient fuel", "out of fuel", "no fuel")):
        print("\n  Insufficient fuel for this operation.")
        print("  Hint: sm dock  |  sm refuel")

    # Cargo full errors
    elif any(w in err_lower for w in ("cargo full", "not enough space", "insufficient cargo", "no cargo space")):
        print("\n  Not enough cargo space.")
        print("  Hint: sm sell-all  |  sm jettison <item_id> <quantity>  |  sm storage deposit")

    # Credits insufficient
    elif any(w in err_lower for w in ("not enough credits", "insufficient credits", "can't afford", "insufficient funds")):
        print("\n  Insufficient credits for this purchase.")
        print("  Hint: sm sell-all  |  sm listings (sell to players)  |  sm missions")

    # Must be docked errors
    elif any(w in err_lower for w in ("must be docked", "need to dock", "while docked", "at a station")):
        print("\n  This action requires being docked at a base.")
        print("  Hint: sm pois  |  sm travel <poi_id>  |  sm dock")

    # Must be undocked errors
    elif any(w in err_lower for w in ("must be undocked", "need to undock", "while undocked", "in space")):
        print("\n  This action requires being undocked.")
        print("  Hint: sm undock")


def _find_weapon_modules(api):
    """Return list of (index, name) for installed weapon modules."""
    if api is None:
        return []
    try:
        resp = api._post("get_ship")
        modules = resp.get("result", {}).get("modules", [])
        weapons = []
        for i, m in enumerate(modules):
            if not isinstance(m, dict):
                continue
            mtype = (m.get("type") or m.get("type_id") or "").lower()
            mname = m.get("name") or m.get("module_id") or f"module_{i}"
            if any(w in mtype for w in ("weapon", "laser", "cannon", "missile",
                                         "turret", "gun", "blaster", "railgun")):
                weapons.append((i, mname))
        return weapons
    except Exception:
        return []


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
            try:
                body[key] = _parse_typed_value(matching_spec, val)
            except ValueError as e:
                print(f"Error: {e}")
                return
        else:
            positional.append(arg)

    # Map positional args to parameter names
    for i, val in enumerate(positional):
        if i < len(specs):
            spec = specs[i]
            try:
                body[_arg_name(spec)] = _parse_typed_value(spec, val)
            except ValueError as e:
                print(f"Error: {e}")
                return
        else:
            # Extra positional with no spec — skip with warning
            print(f"Warning: extra argument ignored: {val}")

    # Check for missing required args (specs not covered by positional or key=value)
    required_specs = [s for s in specs if not _is_optional(s)]
    # Only show usage if we have required params but got no body
    if required_specs and not body:
        arg_names = " ".join(
            f"[{_arg_name(s)}]" if _is_optional(s) else f"<{_arg_name(s)}>"
            for s in specs)
        print(f"Usage: sm {endpoint.replace('_', '-')} {arg_names}")
        return
    missing = [_arg_name(s) for s in required_specs if _arg_name(s) not in body]
    if missing:
        provided = " ".join(
            f"[{_arg_name(s)}]" if _is_optional(s) else f"<{_arg_name(s)}>"
            for s in specs)
        print(f"Usage: sm {endpoint.replace('_', '-')} {provided}")
        print(f"Missing: {', '.join(missing)}")
        return

    from spacemolt.api import APIError
    try:
        resp = api._post(endpoint, body)
    except APIError as e:
        print(f"ERROR: {e}")
        _print_error_hints(endpoint, str(e), api)
        return

    if as_json:
        print(json.dumps(resp, indent=2))
    else:
        err = resp.get("error")
        if err:
            err_msg = err.get('message', err) if isinstance(err, dict) else err
            print(f"ERROR: {err_msg}")
            _print_error_hints(endpoint, str(err_msg), api)
        else:
            formatter = _FORMATTERS.get(endpoint)
            if formatter:
                try:
                    formatter(resp)
                except Exception as e:
                    print(f"Formatter error: {e}", file=__import__('sys').stderr)
                    print(json.dumps(resp, indent=2))
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
                    # Fall back to JSON with a note
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
cmd_ships = _make_passthrough_alias("get_ships")
cmd_chat_history = _make_passthrough_alias("get_chat_history")
cmd_faction_list = _make_passthrough_alias("faction_list")
cmd_faction_invites = _make_passthrough_alias("faction_get_invites")
