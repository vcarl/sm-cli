import json


__all__ = [
    "ENDPOINT_ARGS", "_parse_typed_value", "_arg_name",
    "cmd_passthrough", "cmd_commands", "cmd_raw",
    "cmd_notes", "cmd_trades", "cmd_ships",
    "cmd_chat_history", "cmd_faction_list", "cmd_faction_invites",
    "cmd_forum", "cmd_battle_status", "cmd_catalog",
    "_normalize_recipes", "_build_recipe_indexes", "_recipe_skill_tier",
    "_recipe_one_line", "_trace_ingredient_tree", "_render_tree",
    "_collect_raw_totals",
]


# Mapping of endpoint names to their expected positional arg specs.
# Use "name:int" or "name:bool" for typed args; default is string.
# Suffix with "?" for optional args (e.g., "target_id?").
# Note: Some endpoints include custom parameters not in the OpenAPI spec (marked with comments).
ENDPOINT_ARGS = {
    "jump": ["target_system"],
    "buy": ["item_id", "quantity:int", "auto_list?:bool", "deliver_to?"],
    "scan": ["target_id"],
    "attack": ["target_id"],
    "travel": ["target_poi"],
    "chat": ["channel", "content", "target_id?"],  # target_id optional per spec
    "craft": ["recipe_id", "count?:int"],  # count is optional batch parameter
    "forum_reply": ["thread_id", "content"],
    "forum_get_thread": ["thread_id"],
    "forum_create_thread": ["title", "content", "category?"],  # category is custom extension
    "sell": ["item_id", "quantity:int", "auto_list?:bool"],
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
    # list_item, buy_listing, cancel_list removed — no longer in API spec
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
    "battle": ["action", "stance?", "target_id?", "side_id?:int"],
    "get_battle_status": [],
    "cloak": ["enable?:bool"],  # enable is custom extension (spec has no params)
    "self_destruct": [],
    # market orders - spec supports batch operations via "orders" array (pass as JSON string)
    "create_sell_order": ["item_id?", "quantity?:int", "price_each?:int", "orders?"],  # orders is array (JSON string)
    "create_buy_order": ["item_id?", "quantity?:int", "price_each?:int", "deliver_to?", "orders?"],  # orders is array (JSON string)
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
    # wrecks (additional)
    "tow_wreck": ["wreck_id"],
    "release_tow": [],
    "scrap_wreck": [],
    "sell_wreck": [],
    # combat (additional)
    "reload": ["ammo_item_id", "weapon_instance_id"],
    # storage — unified endpoint (replaces deposit_items, withdraw_items, etc.)
    "storage": ["action", "item_id?", "quantity?:int", "target?", "message?"],
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
    "register": ["username", "empire", "registration_code"],  # registration_code now required per spec
    # missing endpoints (quick wins for completeness)
    "get_version": [],
    "get_map": [],
    "view_orders": [],
    # view_storage replaced by unified /storage command
    "help": ["category?", "command?"],
    # Catalog (reference data browser)
    "catalog": ["type", "search?", "category?", "id?", "page?:int", "page_size?:int"],
    # New market and exploration commands
    "analyze_market": [],
    "survey_system": [],
    # Missions
    "decline_mission": ["template_id?"],
    # Items
    "use_item": ["item_id?", "quantity?:int"],
    # Facility management
    # Faction storage
    # faction storage endpoints replaced by: sm storage --target faction
    "faction_gift": ["faction_id?", "item_id?", "quantity?:int"],
    # Faction market orders
    "faction_create_buy_order": ["item_id?", "quantity?:int", "price_each?:int"],
    "faction_create_sell_order": ["item_id?", "quantity?:int", "price_each?:int"],
    # Faction management
    "faction_edit": ["description?", "charter?", "primary_color?", "secondary_color?"],
    "faction_create_role": ["name?", "priority?:int", "invite?:bool", "kick?:bool"],
    "faction_edit_role": ["role_id?", "name?"],
    "faction_delete_role": ["role_id?"],
    "faction_cancel_mission": ["template_id?"],
    "faction_list_missions": [],
    "faction_post_mission": ["title?", "description?", "type?", "item_id?", "quantity?:int"],
    # Faction intel
    "faction_intel_status": [],
    "faction_submit_intel": [],
    "faction_query_intel": ["system_name?"],
    "faction_trade_intel_status": [],
    "faction_submit_trade_intel": [],
    "faction_query_trade_intel": ["base_id?"],
    # Faction rooms
    "faction_rooms": [],
    "faction_visit_room": ["room_id"],
    "faction_write_room": ["access?", "description?", "name?", "room_id?"],
    "faction_delete_room": ["room_id"],
    # Refuel (custom cmd in actions.py; passthrough supports new params)
    "refuel": ["item_id?", "quantity?:int"],
    # Captain's log (custom cmd in actions.py; passthrough supports index param)
    "captains_log_list": ["index?:int"],
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
# Passthrough response formatters (complex formatters that stay as custom code)
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


def _fmt_trade(t):
    """Format a single trade object."""
    tid = t.get("trade_id") or t.get("id", "?")
    partner = (t.get("partner_name") or t.get("partner")
               or t.get("target_name") or t.get("other_player", "?"))
    status = t.get("status", "?")
    print(f"  Trade {tid} with {partner} [{status}]")
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
            print(f"    {label}: {', '.join(parts)}")
    for label, key in [("Credits offered", "credits_offered"),
                       ("Credits requested", "credits_requested")]:
        val = t.get(key)
        if val:
            print(f"    {label}: {val}")


def _fmt_trades(resp):
    r = resp.get("result", {})
    incoming = r.get("incoming", [])
    outgoing = r.get("outgoing", [])
    if not incoming and not outgoing:
        print("No pending trades.")
        return
    if incoming:
        print(f"Incoming ({len(incoming)}):")
        for t in incoming:
            _fmt_trade(t)
    if outgoing:
        print(f"Outgoing ({len(outgoing)}):")
        for t in outgoing:
            _fmt_trade(t)


def _fmt_ships(resp):
    r = resp.get("result", {})
    ships = r.get("ships", [])
    if not ships:
        print("No ships owned.")
        return
    count = r.get("count", len(ships))
    print(f"Ships ({count}):")
    for s in ships:
        sid = s.get("ship_id") or s.get("id", "?")
        sclass = s.get("class_id") or s.get("ship_class", "?")
        class_name = s.get("class_name") or s.get("name", "")
        location = s.get("location") or s.get("system_name") or s.get("current_system", "")
        active = s.get("is_active", False) or s.get("active", False)
        hull = s.get("hull")
        fuel = s.get("fuel")
        cargo_used = s.get("cargo_used")
        modules = s.get("modules")

        label = class_name if class_name else sclass
        line = f"  {label}"
        if class_name and sclass and class_name != sclass:
            line += f" ({sclass})"
        sid_str = sid[:12] if isinstance(sid, str) and len(sid) > 12 else str(sid)
        line += f"  id:{sid_str}"
        if active:
            line += "  [ACTIVE]"
        print(line)

        details = []
        if hull is not None:
            details.append(f"Hull:{hull}")
        if fuel is not None:
            details.append(f"Fuel:{fuel}")
        if cargo_used is not None:
            details.append(f"Cargo:{cargo_used}")
        if modules is not None:
            details.append(f"Modules:{modules}")
        if location:
            details.append(f"@ {location}")
        if details:
            print(f"    {'  '.join(details)}")

    print(f"\n  Hint: sm switch-ship <ship_id>  |  sm sell-ship <ship_id>  |  sm ship")


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
    for i, t in enumerate(threads):
        if i > 0:
            print()
        tid = t.get("id") or t.get("thread_id", "?")
        title = t.get("title", "(untitled)")
        author = t.get("author_name") or t.get("author") or t.get("username", "?")
        author_id = t.get("author_id", "")
        replies = t.get("reply_count") or t.get("replies", 0)
        upvotes = t.get("upvotes") or t.get("upvote_count", 0)
        category = t.get("category", "")
        faction_tag = t.get("author_faction_tag", "")
        cat_str = f"[{category}] " if category else ""
        author_str = author
        if faction_tag:
            author_str = f"[{faction_tag}] {author}"
        print(f"  {cat_str}{title}")
        print(f"    by {author_str}  replies:{replies}  upvotes:{upvotes}")
        print(f"    id:{tid}  author_id:{author_id}")
        content = t.get("content", "")
        if content:
            snippet = content.replace("\n", " ")
            if len(snippet) > 120:
                snippet = snippet[:117] + "..."
            print(f"    {snippet}")


def _fmt_forum_get_thread(resp):
    r = resp.get("result", {})
    thread = r.get("thread", r)
    title = thread.get("title", "(untitled)")
    author = thread.get("author_name") or thread.get("author") or thread.get("username", "?")
    author_id = thread.get("author_id", "")
    faction_tag = thread.get("author_faction_tag", "")
    content = thread.get("content", "")
    upvotes = thread.get("upvotes") or thread.get("upvote_count", 0)
    category = thread.get("category", "")
    created = thread.get("created_at") or thread.get("timestamp", "")
    if isinstance(created, str) and len(created) > 16:
        created = created[:16]
    tid = thread.get("id") or thread.get("thread_id", "")
    cat_str = f"  [{category}]" if category else ""
    author_str = author
    if faction_tag:
        author_str = f"[{faction_tag}] {author}"
    print(f"# {title}{cat_str}")
    meta = f"  by {author_str}"
    if created:
        meta += f"  {created}"
    meta += f"  upvotes:{upvotes}"
    print(meta)
    if tid or author_id:
        id_line = "  "
        if tid:
            id_line += f"id:{tid}"
        if author_id:
            id_line += f"  author_id:{author_id}"
        print(id_line)
    if content:
        print()
        print(content)
    replies = thread.get("replies", [])
    if replies:
        print(f"\n--- Replies ({len(replies)}) ---")
        for reply in replies:
            rauthor = reply.get("author_name") or reply.get("author") or reply.get("username", "?")
            rauthor_id = reply.get("author_id", "")
            rfaction_tag = reply.get("author_faction_tag", "")
            rcontent = reply.get("content", "")
            rupvotes = reply.get("upvotes") or reply.get("upvote_count", 0)
            rts = reply.get("created_at") or reply.get("timestamp", "")
            if isinstance(rts, str) and len(rts) > 16:
                rts = rts[:16]
            rid = reply.get("id") or reply.get("reply_id", "")
            rauthor_str = rauthor
            if rfaction_tag:
                rauthor_str = f"[{rfaction_tag}] {rauthor}"
            ts_str = f"  {rts}" if rts else ""
            print(f"\n  {rauthor_str}{ts_str}  upvotes:{rupvotes}")
            print(f"    id:{rid}  author_id:{rauthor_id}")
            if rcontent:
                for line in rcontent.split("\n"):
                    print(f"    {line}")


def _fmt_attack(resp):
    r = resp.get("result", {})
    msg = r.get("message")
    if msg:
        print(msg)
    else:
        print("Attack queued.")
    if r.get("pending"):
        cmd = r.get("command", "attack")
        print(f"  Action: {cmd} (pending next tick)")
    # Legacy fields (in case server ever returns immediate results)
    for k in ("target_hull", "target_shield", "hull", "shield", "damage"):
        v = r.get(k)
        if v is not None:
            print(f"  {k}: {v}")
    print("\n  Hint: sm battle-status  |  sm nearby")
    print("  Note: Combat is in beta. If something seems wrong, check the CLI source and fix it!")


def _fmt_scan(resp):
    r = resp.get("result", {})
    scan = r

    if scan.get("queued") or scan.get("pending"):
        target = scan.get("target_id") or "target"
        msg = scan.get("message", f"Scanning {target}...")
        print(msg)
        print("\n  Hint: sm nearby")
        return

    success = scan.get("success", True)
    if not success:
        reason = scan.get("error") or scan.get("message") or scan.get("reason", "")
        if reason:
            print(f"Scan failed: {reason}")
        else:
            print(f"Scan failed.")
        print("\n  Hint: sm nearby  |  sm ship")
        return

    target = scan.get("username") or scan.get("target_id", "?")
    print(f"Scan of {target}:")

    # Show known structured fields first
    for label, key in [("Ship", "ship_class"), ("Hull", "hull"),
                        ("Shield", "shield"), ("Faction", "faction_id"),
                        ("Cloaked", "cloaked")]:
        v = scan.get(key)
        if v is not None:
            print(f"  {label}: {v}")

    # Show any extra fields not already printed
    known = {"success", "revealed_info", "username", "target_id",
             "ship_class", "hull", "shield", "faction_id", "cloaked"}
    for k, v in scan.items():
        if k in known:
            continue
        label = k.replace("_", " ").title()
        if isinstance(v, list):
            print(f"  {label}: {', '.join(str(i) for i in v)}")
        elif v is not None:
            print(f"  {label}: {v}")

    revealed = scan.get("revealed_info", [])
    if revealed:
        print(f"  Revealed: {', '.join(revealed)}")

    target_id = scan.get("target_id") or target
    print(f"\n  Hint: sm attack {target_id}  |  sm trade-offer {target_id}")
    print("  Note: Combat is in beta. If something seems wrong, check the CLI source and fix it!")


def _fmt_craft(resp):
    r = resp.get("result", {})
    msg = r.get("message")
    if msg:
        print(f"✓ {msg}")
    else:
        print("✓ Crafted successfully.")
    for label, key in [("Recipe", "recipe"), ("Count", "count"),
                        ("Quality", "quality"), ("Skill level", "skill_level")]:
        val = r.get(key)
        if val is not None:
            print(f"  {label}: {val}")

    xp = r.get("xp_gained", {})
    if xp:
        parts = [f"{skill} +{amount}" for skill, amount in xp.items()]
        print(f"  XP gained: {', '.join(parts)}")

    if r.get("level_up"):
        skills = r.get("leveled_up_skills", [])
        if skills:
            print(f"  Level up: {', '.join(skills)}")
        else:
            print("  Level up!")

    from_storage = r.get("from_storage", [])
    if from_storage:
        print("\n  Used from storage:")
        for item in from_storage:
            if isinstance(item, dict):
                print(f"    - {item.get('item_id', '?')} x{item.get('quantity', 1)}")
            else:
                print(f"    - {item}")

    to_storage = r.get("to_storage", [])
    if to_storage:
        print("\n  Overflow to storage:")
        for item in to_storage:
            if isinstance(item, dict):
                print(f"    - {item.get('item_id', '?')} x{item.get('quantity', 1)}")
            else:
                print(f"    - {item}")

    print(f"\n  Hint: sm cargo  |  sm recipes  |  sm recipes query --search <resource>")


def _fmt_help(resp):
    r = resp.get("result", resp)
    help_text = r.get("help") or r.get("message") or r.get("content", "")
    if help_text:
        print(help_text)
    else:
        print(json.dumps(r, indent=2))


def _fmt_find_route(resp):
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
    r = resp.get("result", resp)
    systems = r.get("systems", [])
    query = r.get("query", "")

    if not systems:
        print(f"No systems found matching '{query}'")
        return

    print(f"Found {len(systems)} system(s) matching '{query}':")
    for sys in systems[:20]:
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


def _fmt_analyze_market(resp):
    r = resp.get("result", resp)
    msg = r.get("message")
    if msg:
        print(msg)

    skill_level = r.get("skill_level")
    station = r.get("station")
    if skill_level is not None and not msg:
        header = f"Market Analysis (trading level {skill_level})"
        if station:
            header += f" at {station}"
        print(header)

    insights = r.get("insights", [])
    if not insights:
        print("\n  No insights found. Higher trading skill reveals more opportunities.")
        return

    # Group by category
    by_cat = {}
    for insight in insights:
        if not isinstance(insight, dict):
            continue
        cat = insight.get("category", "other")
        by_cat.setdefault(cat, []).append(insight)

    for cat, items in by_cat.items():
        print(f"\n  {cat.replace('_', ' ').title()} ({len(items)}):")
        for insight in items:
            item = insight.get("item", "")
            item_id = insight.get("item_id", "")
            message = insight.get("message", "")
            if item and item_id:
                print(f"    `{item}`({item_id}): {message}")
            elif item or item_id:
                print(f"    `{item or item_id}`: {message}")
            else:
                print(f"    {message}")

    print(f"\n  Hint: sm listings <item_id>  |  sm find-route <system>")


def _fmt_survey_system(resp):
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

    print("\n  System Properties:")
    for key in ["security_level", "police_level", "faction_control", "population"]:
        val = r.get(key)
        if val is not None:
            label = key.replace("_", " ").title()
            print(f"    {label}: {val}")

    pois = r.get("points_of_interest", []) or r.get("pois", [])
    if pois:
        print(f"\n  Points of Interest ({len(pois)}):")
        for poi in pois[:20]:
            if isinstance(poi, dict):
                poi_name = poi.get("name", "?")
                poi_type = poi.get("type", "?")
                resources = poi.get("resources", [])

                line = f"    [{poi_type:12s}] {poi_name}"
                if resources:
                    res_str = ", ".join(str(r) for r in resources[:3])
                    line += f"  ({res_str})"
                print(line)

                hidden_info = poi.get("hidden_info", {})
                if hidden_info:
                    for k, v in hidden_info.items():
                        print(f"        └─ {k}: {v}")

        if len(pois) > 20:
            print(f"    ... and {len(pois) - 20} more")

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


def _fmt_battle_status(resp):
    r = resp.get("result", {})
    battle_id = r.get("battle_id", "?")
    system_id = r.get("system_id", "?")
    is_participant = r.get("is_participant", False)
    tick_duration = r.get("tick_duration")

    status_str = "PARTICIPANT" if is_participant else "OBSERVER"
    print(f"Battle {battle_id} in {system_id} [{status_str}]")
    if tick_duration:
        print(f"  Tick duration: {tick_duration}s")

    sides = r.get("sides", [])
    if sides:
        print(f"\n  Sides ({len(sides)}):")
        for i, side in enumerate(sides):
            if isinstance(side, dict):
                side_id = side.get("side_id") or side.get("id", i)
                name = side.get("name") or side.get("faction_name", f"Side {side_id}")
                count = side.get("member_count") or side.get("count", "?")
                print(f"    [{side_id}] {name} ({count} members)")
            else:
                print(f"    {side}")

    participants = r.get("participants", [])
    if participants:
        print(f"\n  Participants ({len(participants)}):")
        for p in participants[:20]:
            if isinstance(p, dict):
                name = p.get("username") or p.get("player_id", "?")
                side = p.get("side_id", "?")
                stance = p.get("stance", "")
                hull = p.get("hull")
                shield = p.get("shield")
                ship = p.get("ship_class", "")
                line = f"    {name} (side:{side})"
                if ship:
                    line += f" [{ship}]"
                if stance:
                    line += f" stance:{stance}"
                if hull is not None:
                    line += f" hull:{hull}"
                if shield is not None:
                    line += f" shield:{shield}"
                print(line)
            else:
                print(f"    {p}")
        if len(participants) > 20:
            print(f"    ... and {len(participants) - 20} more")

    print(f"\n  Hint: sm battle engage  |  sm battle stance fire  |  sm battle retreat")
    print("  Note: Combat is in beta. If something seems wrong, check the CLI source and fix it!")


def _fmt_catalog(resp):
    r = resp.get("result", {})
    cat_type = r.get("type", "?")
    items = r.get("items", [])
    total = r.get("total", len(items))
    page = r.get("page", 1)
    total_pages = r.get("total_pages", 1)
    message = r.get("message", "")

    if message:
        print(message)
        print()

    if not items:
        print(f"No {cat_type} found.")
        return

    print(f"Catalog: {cat_type} (page {page}/{total_pages}, {total} total)")
    print()

    for item in items:
        if not isinstance(item, dict):
            print(f"  {item}")
            continue

        name = item.get("name") or item.get("id", "?")
        item_id = item.get("id") or item.get("item_id") or item.get("class_id", "")
        category = item.get("category", "")
        description = item.get("description", "")

        header = f"  {name}"
        if item_id and item_id != name:
            header += f"  ({item_id})"
        if category:
            header += f"  [{category}]"
        print(header)

        if cat_type == "ships":
            for label, key in [("Class", "class_name"), ("Hull", "max_hull"),
                               ("Shield", "max_shield"), ("Cargo", "cargo_capacity"),
                               ("Fuel", "max_fuel"), ("Slots", "module_slots"),
                               ("Price", "price")]:
                val = item.get(key)
                if val is not None:
                    if key == "price":
                        print(f"    {label}: {val:,} cr")
                    else:
                        print(f"    {label}: {val}")

        elif cat_type == "items":
            for label, key in [("Type", "type"), ("Value", "base_value"),
                               ("Stack", "stack_size"), ("Weight", "weight")]:
                val = item.get(key)
                if val is not None:
                    if key == "base_value":
                        print(f"    {label}: {val:,} cr")
                    else:
                        print(f"    {label}: {val}")

        elif cat_type == "skills":
            for label, key in [("Category", "category"), ("Max Level", "max_level"),
                               ("Bonus", "bonus_per_level")]:
                val = item.get(key)
                if val is not None:
                    print(f"    {label}: {val}")

        elif cat_type == "recipes":
            ingredients = item.get("ingredients", [])
            outputs = item.get("outputs", []) or item.get("output", [])
            skill_req = item.get("required_skill") or item.get("skill_requirement")
            if skill_req:
                print(f"    Requires: {skill_req}")
            if ingredients:
                parts = []
                for ing in ingredients:
                    if isinstance(ing, dict):
                        parts.append(f"{ing.get('item_id', '?')} x{ing.get('quantity', 1)}")
                    else:
                        parts.append(str(ing))
                print(f"    In: {', '.join(parts)}")
            if outputs:
                parts = []
                for out in outputs:
                    if isinstance(out, dict):
                        parts.append(f"{out.get('item_id', '?')} x{out.get('quantity', 1)}")
                    else:
                        parts.append(str(out))
                print(f"    Out: {', '.join(parts)}")

        if description:
            desc = description.replace("\n", " ")
            if len(desc) > 100:
                desc = desc[:97] + "..."
            print(f"    {desc}")

    if total_pages > 1:
        print(f"\nPage {page}/{total_pages} ({total} total)  --  --page {page + 1} for next")

    print(f"\n  Hint: sm catalog {cat_type} --search <text>  |  sm catalog {cat_type} --id <id>")


# Complex formatters stay as custom functions; simple ones moved to FORMAT_SCHEMAS
_FORMATTERS = {
    "get_chat_history": _fmt_chat_history,
    "read_note": _fmt_read_note,
    "get_trades": _fmt_trades,
    "get_ships": _fmt_ships,
    "list_ships": _fmt_ships,
    "faction_info": _fmt_faction_info,
    "forum_list": _fmt_forum_list,
    "forum_get_thread": _fmt_forum_get_thread,
    "attack": _fmt_attack,
    "scan": _fmt_scan,
    "craft": _fmt_craft,
    "help": _fmt_help,
    "find_route": _fmt_find_route,
    "search_systems": _fmt_search_systems,
    "analyze_market": _fmt_analyze_market,
    "survey_system": _fmt_survey_system,
    "get_battle_status": _fmt_battle_status,
    "catalog": _fmt_catalog,
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
            names = ", ".join(f"{name}" for _, name in weapons)
            print(f"\n  Your weapon modules: {names}")
            print(f"  Hint: sm attack <target_id>")
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
        print("  Hint: sm refuel")

    # Cargo full errors
    elif any(w in err_lower for w in ("cargo full", "not enough space", "insufficient cargo", "no cargo space")):
        print("\n  Not enough cargo space.")
        print("  Hint: sm jettison <item_id> <quantity>  |  sm storage deposit")

    # Credits insufficient
    elif any(w in err_lower for w in ("not enough credits", "insufficient credits", "can't afford", "insufficient funds")):
        print("\n  Insufficient credits for this purchase.")
        print("  Hint: sm listings (sell to players)  |  sm missions")

    # Must be docked errors
    elif any(w in err_lower for w in ("must be docked", "need to dock", "while docked", "at a station")):
        print("\n  This action requires being docked at a base.")
        print("  Hint: sm pois  |  sm travel <poi_id>")

    # Must be undocked errors
    elif any(w in err_lower for w in ("must be undocked", "need to undock", "while undocked", "in space")):
        print("\n  This action requires being undocked.")
        print("  Hint: sm travel <poi_id>  |  sm jump <target_system>")


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
            from spacemolt.commands.format_schemas import FORMAT_SCHEMAS, render_schema
            formatter = _FORMATTERS.get(endpoint)
            if formatter:
                try:
                    formatter(resp)
                except Exception as e:
                    print(f"Formatter error: {e}", file=__import__('sys').stderr)
                    print(json.dumps(resp, indent=2))
            elif endpoint in FORMAT_SCHEMAS:
                try:
                    render_schema(FORMAT_SCHEMAS[endpoint], resp)
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
    """Print categorized command reference."""
    _print_full_help()


def _print_full_help():
    """Print all commands organized by category, including passthrough."""
    # Commands organized by category: (cli_name, description)
    # cli_name uses hyphens (how the user types it)
    # (command_with_args, description)
    # Use <arg> for required, [arg] for optional
    categories = [
        ("Getting Started", [
            ("register <username> <empire>", "Register a new account"),
            ("login [cred_file]", "Login and save session"),
            ("claim <registration_code>", "Link player to spacemolt.com account"),
            ("logout", "End current session"),
            ("help", "Show this help"),
        ]),
        ("Info & Status", [
            ("status", "Credits, location, ship, fuel"),
            ("ship", "Ship details + modules + cargo"),
            ("cargo", "Cargo contents"),
            ("pois", "POIs in current system"),
            ("system", "System overview + connections"),
            ("poi", "Current POI details + resources"),
            ("base", "Docked base details + services"),
            ("nearby", "Nearby players + threat assessment"),
            ("notifications", "Pending notifications"),
            ("wrecks", "Wrecks at current location"),
            ("log", "Captain's log"),
            ("log-add <text>", "Add captain's log entry"),
            ("get-version", "Server version info"),
            ("get-map", "Galaxy map data"),
        ]),
        ("Navigation", [
            ("travel <poi_id>", "Travel to POI in current system"),
            ("jump <target_system>", "Jump to adjacent system"),
            ("find-route <target_system>", "Find route to a system"),
            ("search-systems <query>", "Search systems by name"),
            ("survey-system", "Survey current system (astrometrics)"),
        ]),
        ("Combat", [
            ("attack <target_id>", "Attack a target"),
            ("battle <action> [stance] [target_id] [side_id]", "Battle action (engage/advance/retreat/stance/target)"),
            ("battle-status", "View current battle state"),
            ("scan <target_id>", "Scan a player's ship"),
            ("reload <ammo_item_id> <weapon_instance_id>", "Reload weapon ammo"),
            ("cloak <true|false>", "Enable or disable cloaking device"),
            ("self-destruct", "Self-destruct your ship"),
        ]),
        ("Mining & Resources", [
            ("mine", "Mine once at current location"),
            ("refuel [fuel_cell] [qty]", "Refuel at station, or burn fuel cells from cargo"),
            ("repair", "Repair ship (requires docked)"),
            ("jettison <item_id> <quantity>", "Jettison cargo into space"),
            ("tow-wreck <wreck_id>", "Tow a wreck"),
            ("release-tow", "Release towed wreck"),
            ("scrap-wreck", "Scrap wreck at location"),
            ("sell-wreck", "Sell a wreck"),
        ]),
        ("Trading (NPC)", [
            ("buy <item_id> [quantity] [--auto-list] [--deliver-to]", "Buy item from NPC market"),
            ("sell <item_id> [quantity] [--auto-list]", "Sell item to NPC market"),
            ("listings [item_id]", "Market listings at current base"),
            ("analyze-market", "Trading insights at current station (skill-gated)"),
            ("estimate-purchase <item_id> <quantity>", "Estimate cost before buying"),
        ]),
        ("Market Orders (Player)", [
            ("market", "Your market orders"),
            ("market buy <item_id> <qty> <price>", "Create a buy order"),
            ("market sell <item_id> <qty> <price>", "Create a sell order"),
            ("market cancel <order_id>", "Cancel an order"),
        ]),
        ("Player Trading", [
            ("trade-offer <target_id> [credits]", "Send trade offer to player"),
            ("trade-accept <trade_id>", "Accept a trade offer"),
            ("trade-decline <trade_id>", "Decline a trade offer"),
            ("trade-cancel <trade_id>", "Cancel your trade offer"),
            ("trades", "List pending trades"),
        ]),
        ("Ship Management", [
            ("ships", "List owned ships"),
            ("buy-ship <ship_class>", "Buy a new ship"),
            ("sell-ship <ship_id>", "Sell a ship"),
            ("switch-ship <ship_id>", "Switch active ship"),
            ("install-mod <module_id> [slot_idx]", "Install a module"),
            ("uninstall-mod <module_id>", "Uninstall a module"),
        ]),
        ("Storage", [
            ("storage", "View base storage"),
            ("storage --target faction", "View faction storage"),
            ("storage deposit <item_id> <quantity>", "Deposit items"),
            ("storage deposit --credits <amount>", "Deposit credits"),
            ("storage withdraw <item_id> <quantity>", "Withdraw items"),
            ("storage withdraw --credits <amount>", "Withdraw credits"),
            ("storage deposit <item> <qty> --target <player>", "Gift items to a player"),
            ("send-gift <recipient> [item_id] [qty]", "Send gift to another player"),
        ]),
        ("Crafting", [
            ("catalog recipes", "Browse all recipes"),
            ("catalog recipes --search <query>", "Search recipes by name/item/category"),
            ("catalog recipes trace <item>", "Trace full ingredient tree for an item"),
            ("craft <recipe_id> [count]", "Craft a recipe"),
        ]),
        ("Missions", [
            ("missions", "Mission overview (active + available)"),
            ("missions accept <mission_id>", "Accept a mission"),
            ("missions complete <mission_id>", "Complete a mission"),
            ("missions abandon <mission_id>", "Abandon a mission"),
            ("decline-mission [template_id]", "Decline an offered mission (hides it)"),
        ]),
        ("Skills", [
            ("catalog skills", "Browse all skill definitions"),
            ("catalog skills --search <query>", "Search skills by name/category"),
            ("catalog skills --id <skill_id>", "Look up a specific skill"),
        ]),
        ("Insurance", [
            ("insurance", "Insurance coverage status"),
            ("insurance buy <ticks>", "Buy insurance coverage"),
            ("insurance claim", "Claim insurance payout"),
        ]),
        ("Chat & Social", [
            ("chat <channel> <message>", "Send chat message"),
            ("chat-history [channel] [limit]", "Chat message history"),
            ("set-status [message] [clan_tag]", "Set status message / clan tag"),
            ("set-colors <primary> <secondary>", "Set ship colors"),
            ("set-anonymous <on|off>", "Toggle anonymous mode"),
        ]),
        ("Notes & Forum", [
            ("notes", "List your notes"),
            ("create-note [title] [content]", "Create a note"),
            ("write-note [note_id] [content]", "Edit a note"),
            ("read-note [note_id]", "Read a note"),
            ("forum-list [page] [category]", "List forum threads"),
            ("forum-get-thread <thread_id>", "Read a forum thread"),
            ("forum-create-thread <title> <content>", "Create a forum thread"),
            ("forum-reply <thread_id> <content>", "Reply to a thread"),
            ("forum-upvote <thread_id> [reply_id]", "Upvote thread or reply"),
        ]),
        ("Faction", [
            ("faction-info [faction_id]", "Faction details"),
            ("faction-list", "List all factions"),
            ("faction-invites", "Pending faction invites"),
            ("create-faction <name> <tag>", "Create a new faction"),
            ("join-faction <faction_id>", "Join a faction"),
            ("leave-faction", "Leave your faction"),
            ("faction-invite <player_id>", "Invite player to faction"),
            ("faction-kick <player_id>", "Kick player from faction"),
            ("faction-promote <player_id> <role_id>", "Promote player's role"),
            ("faction-edit [desc] [charter] [colors]", "Edit faction description/colors"),
            ("faction-declare-war <faction_id> [reason]", "Declare war on faction"),
            ("faction-propose-peace <faction_id> [terms]", "Propose peace"),
            ("faction-set-ally <faction_id>", "Set faction as ally"),
            ("faction-set-enemy <faction_id>", "Set faction as enemy"),
        ]),
        ("Faction Intel & Rooms", [
            ("faction-intel-status", "Your faction's intel coverage stats"),
            ("faction-submit-intel", "Report system/POI data to faction intel database"),
            ("faction-query-intel [system_name]", "Look up faction intel on a system"),
            ("faction-rooms", "List rooms in faction's Common Space"),
            ("faction-visit-room <room_id>", "Read a faction room's contents"),
            ("faction-write-room [room_id] [name]", "Create or edit a faction room (lore/descriptions)"),
        ]),
        ("Faction Economy", [
            ("storage --target faction", "View faction storage"),
            ("storage deposit <item> <qty> --target faction", "Deposit items to faction storage"),
            ("storage withdraw <item> <qty> --target faction", "Withdraw from faction storage"),
            ("storage deposit --credits <amt> --target faction", "Deposit credits to faction treasury"),
            ("storage withdraw --credits <amt> --target faction", "Withdraw credits from faction treasury"),
            ("faction-gift [faction_id] [item_id] [qty]", "Gift items from faction storage to another faction"),
            ("faction-create-buy-order [item] [qty] [price]", "Buy order using faction treasury (needs manage_treasury)"),
            ("faction-create-sell-order [item] [qty] [price]", "Sell order from faction storage (needs manage_treasury)"),
        ]),
        ("Base & Facilities", [
            ("set-home-base <base_id>", "Set your home base"),
            ("facility", "List facilities at current base"),
            ("facility types", "List buildable facility types"),
            ("facility type <type>", "Detail view for a facility type"),
            ("facility build <type>", "Build a new facility"),
            ("facility upgrade <id>", "Upgrade a facility"),
            ("facility upgrades [id]", "Show available upgrades"),
            ("facility toggle <id>", "Enable/disable a facility"),
            ("facility faction-build <type>", "Build a faction facility"),
            ("facility faction-list", "List faction facilities"),
            ("facility transfer <id> <dir>", "Transfer facility ownership"),
            ("facility quarters [user]", "Visit quarters"),
            ("facility decorate <desc>", "Set quarters description"),
            ("facility quarters-build", "Build personal quarters"),
            ("facility help", "Show facility actions from API"),
        ]),
        ("Items", [
            ("use-item [item_id] [quantity]", "Use an item from cargo"),
        ]),
        ("Catalog", [
            ("catalog ships [--search] [--category]", "Browse ship classes"),
            ("catalog items [--search] [--category]", "Browse items"),
            ("catalog skills [--search] [--category]", "Browse skills"),
            ("catalog recipes [--search] [--category]", "Browse recipes"),
            ("catalog <type> --id <id>", "Look up a specific entry"),
        ]),
        ("Advanced", [
            ("raw <endpoint> [json_body]", "Raw API call (JSON output)"),
        ]),
    ]

    print("sm — SpaceMolt CLI\n")

    name_w = 0
    for _, cmds in categories:
        for name, _ in cmds:
            name_w = max(name_w, len(f"sm {name}"))
    name_w += 2

    for cat_name, cmds in categories:
        print(f"  {cat_name}:")
        for name, desc in cmds:
            full_name = f"sm {name}"
            print(f"    {full_name:<{name_w}} {desc}")
        print()

    print("Tips:")
    print("  sm <command> --json       Raw JSON output for any command")
    print("  sm <cmd> key=value        Pass named args to any command")
    print("  sm raw <endpoint> [json]  Raw API call with JSON body")


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
cmd_ships = _make_passthrough_alias("list_ships")
cmd_chat_history = _make_passthrough_alias("get_chat_history")
cmd_faction_list = _make_passthrough_alias("faction_list")
cmd_faction_invites = _make_passthrough_alias("faction_get_invites")
cmd_forum = _make_passthrough_alias("forum_list")
cmd_battle_status = _make_passthrough_alias("get_battle_status")


# ---------------------------------------------------------------------------
# Recipe trace helpers (used by catalog recipes trace)
# ---------------------------------------------------------------------------

def _normalize_recipes(raw_recipes):
    """Turn the API recipes response (dict-keyed or list) into a list."""
    if isinstance(raw_recipes, dict):
        return list(raw_recipes.values())
    return list(raw_recipes)


def _is_natural_resource(item_id):
    """Check if an item ID looks like a natural resource (mineable/harvestable)."""
    return item_id.startswith(("ore_", "gas_", "bio_", "salvage_"))


def _leaf_source_score(item_id, all_by_output, depth=0, seen=None):
    """Score an item by its ultimate source. Higher = more preferred.

    Recursively traces through recipes to score based on the leaf materials.
    Mine/harvest (ore/gas/bio) = 2, salvage = 1, unknown = 0.
    """
    if seen is None:
        seen = set()
    if item_id in seen:
        return 0
    if item_id.startswith(("ore_", "gas_", "bio_")):
        return 2
    if item_id.startswith("salvage_"):
        return 1
    # If this item can be crafted, score based on its best recipe's inputs
    recipes = all_by_output.get(item_id, [])
    if not recipes or depth > 5:
        return 0
    seen = seen | {item_id}
    best = 0
    for r in recipes:
        inputs = r.get("inputs") or []
        if not inputs:
            continue
        score = sum(_leaf_source_score(i.get("item_id", ""), all_by_output, depth + 1, seen)
                    for i in inputs) / len(inputs)
        best = max(best, score)
    return best


def _recipe_source_score(recipe, all_by_output):
    """Score a recipe by how obtainable its inputs ultimately are. Higher = more preferred."""
    inputs = recipe.get("inputs") or []
    if not inputs:
        return 0
    return sum(_leaf_source_score(i.get("item_id", ""), all_by_output) for i in inputs) / len(inputs)


def _build_recipe_indexes(recipe_list):
    """Build lookup dicts: output_item->recipes (list), recipe_id->recipe.

    When multiple recipes produce the same item, they are sorted so recipes
    using natural resources (ore, gas, bio, salvage) come first.
    """
    from collections import defaultdict
    all_by_output = defaultdict(list)  # item_id -> [recipes]
    by_id = {}      # recipe_id -> recipe
    for r in recipe_list:
        rid = r.get("id") or r.get("recipe_id", "")
        if rid:
            by_id[rid] = r
        for o in r.get("outputs", []):
            all_by_output[o.get("item_id", "")].append(r)

    # Sort each output's recipes: prefer mine/harvest over salvage over crafted
    by_output = {}
    alt_recipes = {}  # item_id -> [alternative recipes]
    for item_id, recipes in all_by_output.items():
        recipes.sort(key=lambda r: (-_recipe_source_score(r, all_by_output),
                                     len(r.get("inputs") or [])))
        by_output[item_id] = recipes[0]
        if len(recipes) > 1:
            alt_recipes[item_id] = recipes[1:]

    return by_output, by_id, alt_recipes


def _recipe_skill_tier(recipe):
    """Return a sortable (max_level, skill_string) tuple for ordering."""
    skills = recipe.get("required_skills", {})
    if not skills:
        return (0, "")
    max_lvl = max(skills.values())
    label = ", ".join(f"{s} {l}" for s, l in sorted(skills.items()))
    return (max_lvl, label)


def _recipe_one_line(recipe):
    """Format a recipe as: inputs -> outputs (with quantities)."""
    inputs = recipe.get("inputs") or []
    outputs = recipe.get("outputs") or []
    lhs = " + ".join(
        f"{i.get('quantity', 1)}x {i.get('item_id', '?')}" for i in inputs
    )
    rhs = " + ".join(
        f"{o.get('quantity', 1)}x {o.get('item_id', '?')}" for o in outputs
    )
    return f"{lhs} -> {rhs}"


def _trace_ingredient_tree(item_id, qty, by_output, depth=0, seen=None):
    """Recursively build a tree of (depth, item_id, qty, recipe_or_None, children)."""
    if seen is None:
        seen = set()
    recipe = by_output.get(item_id)
    if recipe is None or item_id in seen:
        return (depth, item_id, qty, None, [])
    seen = seen | {item_id}
    children = []
    for inp in recipe.get("inputs", []):
        inp_id = inp.get("item_id", "?")
        inp_qty = inp.get("quantity", 1) * qty
        children.append(
            _trace_ingredient_tree(inp_id, inp_qty, by_output, depth + 1, seen)
        )
    return (depth, item_id, qty, recipe, children)


def _item_source_tag(item_id):
    """Return a short tag describing how to obtain a natural resource."""
    if item_id.startswith("ore_"):
        return "mine"
    if item_id.startswith("gas_"):
        return "harvest"
    if item_id.startswith("bio_"):
        return "harvest"
    if item_id.startswith("salvage_"):
        return "salvage"
    return None


def _render_tree(node, prefix="", is_last=True, lines=None):
    """Render a trace tree into lines with box-drawing connectors."""
    if lines is None:
        lines = []
    depth, item_id, qty, recipe, children = node

    connector = "\u2514\u2500\u2500 " if is_last else "\u251c\u2500\u2500 "
    if depth == 0:
        label = f"{qty}x {item_id}"
        if recipe:
            rid = recipe.get("id", "")
            skills = recipe.get("required_skills", {})
            skill_str = ""
            if skills:
                skill_str = "  [" + ", ".join(f"{s} {l}" for s, l in sorted(skills.items())) + "]"
            label += f"  ({rid}){skill_str}"
        lines.append(label)
    else:
        label = f"{qty}x {item_id}"
        if recipe:
            rid = recipe.get("id", "")
            label += f"  ({rid})"
        elif _item_source_tag(item_id):
            label += f"  [{_item_source_tag(item_id)}]"
        lines.append(f"{prefix}{connector}{label}")

    child_prefix = prefix + ("    " if is_last else "\u2502   ")
    for i, child in enumerate(children):
        _render_tree(child, child_prefix, i == len(children) - 1, lines)
    return lines


def _collect_raw_totals(node, totals=None):
    """Walk tree and sum up raw material quantities at the leaves."""
    if totals is None:
        totals = {}
    _, item_id, qty, recipe, children = node
    if recipe is None:
        totals[item_id] = totals.get(item_id, 0) + qty
    else:
        for child in children:
            _collect_raw_totals(child, totals)
    return totals


def _print_raw_totals(label, totals):
    """Print raw material totals grouped by source type."""
    groups = {}
    for item_id, qty in totals.items():
        tag = _item_source_tag(item_id) or "other"
        groups.setdefault(tag, []).append((item_id, qty))

    GROUP_LABELS = {
        "mine": "Mine",
        "harvest": "Harvest",
        "salvage": "Salvage",
        "other": "Other",
    }
    print(f"\n{'─' * 40}")
    print(f"{label}:\n")
    for tag in ["mine", "harvest", "salvage", "other"]:
        items = groups.get(tag)
        if not items:
            continue
        items.sort(key=lambda x: -x[1])
        print(f"  {GROUP_LABELS[tag]}:")
        for item_id, qty in items:
            print(f"    {qty}x {item_id}")
        print()



def _find_items_with_alts_in_tree(item_id, by_output, alt_recipes, seen=None):
    """Walk the primary tree and find items that have alternative recipes."""
    if seen is None:
        seen = set()
    if item_id in seen:
        return []
    seen.add(item_id)
    result = []
    recipe = by_output.get(item_id)
    if recipe is None:
        return []

    alts = alt_recipes.get(item_id, [])
    if alts:
        result.append((item_id, alts))

    for inp in recipe.get("inputs", []):
        result.extend(_find_items_with_alts_in_tree(
            inp.get("item_id", ""), by_output, alt_recipes, seen))

    return result


def _do_trace(query, by_output, recipe_list, alt_recipes=None):
    """Trace the full ingredient tree for an item or recipe."""
    if alt_recipes is None:
        alt_recipes = {}
    if not query:
        print("Usage: sm catalog recipes trace <item_id or recipe_id>")
        return

    target_item = None
    target_qty = 1
    if query in by_output:
        target_item = query
    else:
        for r in recipe_list:
            if r.get("id") == query:
                outputs = r.get("outputs", [])
                if outputs:
                    target_item = outputs[0].get("item_id")
                    target_qty = outputs[0].get("quantity", 1)
                break

    if not target_item:
        q = query.lower()
        candidates = [
            item_id for item_id in by_output
            if q in item_id.lower()
        ]
        if len(candidates) == 1:
            target_item = candidates[0]
        elif candidates:
            print("Ambiguous \u2014 did you mean one of these?")
            for c in sorted(candidates):
                print(f"  {c}")
            return
        else:
            print(f"No recipe produces '{query}'. Try: sm catalog recipes --search {query}")
            return

    # Build list of (label, tree, totals) for primary + alt paths
    paths = []

    # Primary path
    tree = _trace_ingredient_tree(target_item, target_qty, by_output)
    totals = _collect_raw_totals(tree)
    paths.append(("Primary path", tree, totals))

    # Alt paths: for each item with alternatives, show each alt recipe
    MAX_ALT_PATHS = 4
    items_with_alts = _find_items_with_alts_in_tree(target_item, by_output, alt_recipes)
    for item_id, alts in items_with_alts:
        for alt_recipe in alts:
            modified = dict(by_output)
            modified[item_id] = alt_recipe
            alt_tree = _trace_ingredient_tree(target_item, target_qty, modified)
            alt_totals = _collect_raw_totals(alt_tree)
            rid = alt_recipe.get("id", "?")
            paths.append((f"Alt: {item_id} via {rid}", alt_tree, alt_totals))
            if len(paths) >= 1 + MAX_ALT_PATHS:
                break
        if len(paths) >= 1 + MAX_ALT_PATHS:
            break

    for i, (label, path_tree, path_totals) in enumerate(paths):
        if i > 0:
            print(f"\n{'═' * 50}\n")
        lines = _render_tree(path_tree)
        print(f"{label} — ingredient tree for {target_item}:\n")
        for line in lines:
            print(line)
        if path_totals:
            _print_raw_totals("Raw materials", path_totals)


# ---------------------------------------------------------------------------
# Catalog command
# ---------------------------------------------------------------------------

def _catalog_api_call(api, cat_type, args):
    """Make a catalog API call and return the response, or None on error."""
    as_json = getattr(args, "json", False)
    body = {"type": cat_type}
    search = getattr(args, "search", None)
    category = getattr(args, "category", None)
    entry_id = getattr(args, "id", None)
    page = getattr(args, "page", None)
    page_size = getattr(args, "page_size", None)

    if search:
        body["search"] = search
    if category:
        body["category"] = category
    if entry_id:
        body["id"] = entry_id
    if page:
        body["page"] = page
    if page_size:
        body["page_size"] = page_size

    from spacemolt.api import APIError
    try:
        resp = api._post("catalog", body)
    except APIError as e:
        print(f"ERROR: {e}")
        return None

    if as_json:
        print(json.dumps(resp, indent=2))
        return None  # already handled

    err = resp.get("error")
    if err:
        err_msg = err.get('message', err) if isinstance(err, dict) else err
        print(f"ERROR: {err_msg}")
        return None

    return resp


def cmd_catalog(api, args):
    """Handle catalog commands: sm catalog <type> [options]."""
    cat_type = getattr(args, "catalog_type", None)

    if not cat_type:
        print("Usage: sm catalog <ships|items|skills|recipes> [options]")
        print()
        print("Options:")
        print("  --search <text>    Search by name/description")
        print("  --category <cat>   Filter by category")
        print("  --id <id>          Look up a specific entry")
        print("  --page <n>         Page number (default: 1)")
        print("  --page-size <n>    Results per page (default: 20, max: 50)")
        print()
        print("Recipes also supports:")
        print("  sm catalog recipes trace <item>   Trace full ingredient tree")
        return

    # For recipes, check for trace subcommand
    if cat_type == "recipes":
        trace_target = getattr(args, "trace_item", None)
        if trace_target:
            # Trace needs all recipes — fetch via get_recipes endpoint
            resp = api._post("get_recipes")
            raw = resp.get("result", {}).get("recipes", {})
            recipe_list = _normalize_recipes(raw)
            if not recipe_list:
                print("No recipes available.")
                return
            by_output, by_id, alt_recipes = _build_recipe_indexes(recipe_list)
            _do_trace(trace_target, by_output, recipe_list, alt_recipes)
            return

    resp = _catalog_api_call(api, cat_type, args)
    if resp:
        _fmt_catalog(resp)
