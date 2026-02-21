"""Facility commands — hierarchical subcommands for the unified /facility endpoint."""
import json


def cmd_facility_router(api, args):
    """Route facility subcommands to the appropriate handler."""
    sub = getattr(args, "facility_cmd", None)
    as_json = getattr(args, "json", False)

    dispatch = {
        "list": _cmd_list,
        "types": _cmd_types,
        "type": _cmd_type_detail,
        "build": _cmd_build,
        "upgrade": _cmd_upgrade,
        "upgrades": _cmd_upgrades,
        "toggle": _cmd_toggle,
        "faction-build": _cmd_faction_build,
        "faction-list": _cmd_faction_list,
        "transfer": _cmd_transfer,
        "quarters": _cmd_quarters,
        "decorate": _cmd_decorate,
        "quarters-build": _cmd_quarters_build,
        "help": _cmd_help,
    }

    handler = dispatch.get(sub, _cmd_list)
    handler(api, args, as_json)


def _call(api, body, as_json):
    """Post to facility endpoint; return parsed response or None on error."""
    resp = api._post("facility", body)
    if as_json:
        print(json.dumps(resp, indent=2))
        return None
    err = resp.get("error")
    if err:
        msg = err.get("message", err) if isinstance(err, dict) else err
        print(f"ERROR: {msg}")
        return None
    return resp.get("result", resp)


def _cmd_list(api, args, as_json):
    body = {"action": "list"}
    r = _call(api, body, as_json)
    if r is None:
        return
    _fmt_facility_list(r)


def _cmd_types(api, args, as_json):
    body = {"action": "types"}
    cat = getattr(args, "category", None)
    name = getattr(args, "name", None)
    page = getattr(args, "page", None)
    if cat:
        body["category"] = cat
    if name:
        body["name"] = name
    if page:
        body["page"] = page
    r = _call(api, body, as_json)
    if r is None:
        return
    _fmt_facility_types(r)


def _cmd_type_detail(api, args, as_json):
    body = {"action": "types", "facility_type": args.facility_type}
    r = _call(api, body, as_json)
    if r is None:
        return
    _fmt_facility_type_detail(r)


def _cmd_build(api, args, as_json):
    body = {"action": "build", "facility_type": args.facility_type}
    r = _call(api, body, as_json)
    if r is None:
        return
    _fmt_facility_build(r)


def _cmd_upgrade(api, args, as_json):
    body = {"action": "upgrade", "facility_id": args.facility_id}
    r = _call(api, body, as_json)
    if r is None:
        return
    _fmt_facility_build(r)  # upgrade response is similar to build


def _cmd_upgrades(api, args, as_json):
    body = {"action": "upgrades"}
    fid = getattr(args, "facility_id", None)
    if fid:
        body["facility_id"] = fid
    r = _call(api, body, as_json)
    if r is None:
        return
    _fmt_facility_upgrades(r)


def _cmd_toggle(api, args, as_json):
    body = {"action": "toggle", "facility_id": args.facility_id}
    r = _call(api, body, as_json)
    if r is None:
        return
    msg = r.get("message", "Toggled facility.")
    print(msg)
    print(f"\n  Hint: sm facility  (check status)")


def _cmd_faction_build(api, args, as_json):
    body = {"action": "faction_build", "facility_type": args.facility_type}
    r = _call(api, body, as_json)
    if r is None:
        return
    _fmt_facility_build(r)


def _cmd_faction_list(api, args, as_json):
    body = {"action": "faction_list"}
    r = _call(api, body, as_json)
    if r is None:
        return
    # API returns faction_facilities; normalize for shared formatter
    if "faction_facilities" in r:
        storage = r.get("faction_storage", {})
        if storage:
            credits = storage.get("credits", 0)
            items = storage.get("item_types", 0)
            print(f"Faction Treasury: {credits:,} cr  |  Storage: {items} item type(s)\n")
        normalized = dict(r)
        normalized["facilities"] = r["faction_facilities"]
        _fmt_facility_list(normalized)
    else:
        _fmt_facility_list(r)


def _cmd_transfer(api, args, as_json):
    body = {"action": "transfer", "facility_id": args.facility_id,
            "direction": args.direction}
    player_id = getattr(args, "player_id", None)
    if player_id:
        body["player_id"] = player_id
    r = _call(api, body, as_json)
    if r is None:
        return
    msg = r.get("message", "Transfer complete.")
    print(msg)
    print(f"\n  Hint: sm facility  |  sm facility faction-list")


def _cmd_quarters(api, args, as_json):
    body = {"action": "personal_visit"}
    username = getattr(args, "username", None)
    if username:
        body["player_id"] = username
    r = _call(api, body, as_json)
    if r is None:
        return
    _fmt_facility_quarters(r)


def _cmd_decorate(api, args, as_json):
    body = {"action": "personal_decorate", "name": args.description}
    access = getattr(args, "access", None)
    if access:
        body["category"] = access  # access level sent as category
    r = _call(api, body, as_json)
    if r is None:
        return
    msg = r.get("message", "Quarters updated.")
    print(msg)


def _cmd_quarters_build(api, args, as_json):
    body = {"action": "personal_build"}
    r = _call(api, body, as_json)
    if r is None:
        return
    _fmt_facility_build(r)


def _cmd_help(api, args, as_json):
    body = {"action": "help"}
    r = _call(api, body, as_json)
    if r is None:
        return
    _fmt_facility_help(r)


# ── Formatters ──────────────────────────────────────────────────────────────

def _fmt_facility_list(r):
    facilities = r.get("facilities", [])
    if not facilities:
        print("No facilities found.")
        print("  Hint: sm facility types  |  sm facility build <type>")
        return

    print(f"Facilities ({len(facilities)}):\n")
    # Column headers
    print(f"  {'Name':<24} {'Type':<20} {'Lvl':>3}  {'Status':<12} {'ID'}")
    print(f"  {'─'*24} {'─'*20} {'─'*3}  {'─'*12} {'─'*12}")
    for f in facilities:
        name = f.get("name") or f.get("facility_type") or f.get("type", "?")
        ftype = f.get("facility_type") or f.get("type", "?")
        level = f.get("level", 1)
        fid = f.get("facility_id", "?")
        # Truncate ID for display
        fid_short = fid[:12] if len(str(fid)) > 12 else fid
        # Determine status
        if f.get("under_construction"):
            status = "building"
        elif f.get("enabled") is False:
            status = "disabled"
        else:
            status = "active"
        print(f"  {name:<24} {ftype:<20} {level:>3}  {status:<12} {fid_short}")

    print(f"\n  Hint: sm facility upgrades  |  sm facility toggle <id>")


def _fmt_facility_types(r):
    # If categories dict is present, show summary
    categories = r.get("categories", {})
    types = r.get("types", r.get("facility_types", []))

    if categories and not types:
        print("Facility Categories:\n")
        for cat, desc in categories.items():
            label = desc if isinstance(desc, str) else cat
            print(f"  {cat:<20} {label}")
        print(f"\n  Hint: sm facility types --category <cat>")
        return

    if not types:
        print("No facility types found.")
        return

    print(f"Facility Types ({len(types)}):\n")
    print(f"  {'Name':<24} {'Type ID':<24} {'Lvl':>3}  {'Cost':>10}  {'Category'}")
    print(f"  {'─'*24} {'─'*24} {'─'*3}  {'─'*10}  {'─'*14}")
    for t in types:
        name = t.get("name", "?")
        tid = t.get("type_id") or t.get("id") or t.get("facility_type", "?")
        level = t.get("level", 1)
        cost = t.get("build_cost", 0)
        cat = t.get("category", "")
        cost_str = f"{cost:,}" if isinstance(cost, (int, float)) else str(cost)
        print(f"  {name:<24} {tid:<24} {level:>3}  {cost_str:>10}  {cat}")

    print(f"\n  Hint: sm facility type <type_id>  |  sm facility build <type_id>")


def _fmt_facility_type_detail(r):
    # May be a single type or a list with one entry
    t = r
    if isinstance(r.get("types"), list) and r["types"]:
        t = r["types"][0]
    elif isinstance(r.get("facility_types"), list) and r["facility_types"]:
        t = r["facility_types"][0]

    name = t.get("name", "?")
    desc = t.get("description", "")
    tid = t.get("type_id") or t.get("id") or t.get("facility_type", "?")
    cost = t.get("build_cost", 0)
    build_time = t.get("build_time")
    labor = t.get("labor_cost")
    upgrades_to = t.get("upgrades_to")
    materials = t.get("build_materials", [])

    print(f"{name}")
    print(f"  Type: {tid}")
    if desc:
        print(f"  {desc}")
    cost_str = f"{cost:,}" if isinstance(cost, (int, float)) else str(cost)
    print(f"  Build cost: {cost_str} credits")
    if build_time:
        print(f"  Build time: {build_time}")
    if labor:
        print(f"  Labor cost: {labor}")
    if materials:
        print(f"  Materials:")
        for m in materials:
            if isinstance(m, dict):
                mid = m.get("item_id", "?")
                qty = m.get("quantity", 1)
                print(f"    {mid} x{qty}")
            else:
                print(f"    {m}")
    if upgrades_to:
        print(f"  Upgrades to: {upgrades_to}")
    print(f"\n  Hint: sm facility build {tid}")


def _fmt_facility_build(r):
    name = r.get("facility_name") or r.get("name", "facility")
    base = r.get("base_id") or r.get("base", "")
    fid = r.get("facility_id", "")
    rent = r.get("rent")
    xp = r.get("xp_gained") or r.get("xp", 0)
    under_construction = r.get("under_construction", False)

    print(f"Built {name}" + (f" at {base}" if base else ""))
    if fid:
        print(f"  Facility ID: {fid}")
    if rent:
        print(f"  Rent: {rent:,} credits/tick" if isinstance(rent, (int, float)) else f"  Rent: {rent}")
    if xp:
        print(f"  XP gained: {xp:,}" if isinstance(xp, (int, float)) else f"  XP gained: {xp}")
    if under_construction:
        print(f"  Status: Under construction")
    msg = r.get("message")
    if msg:
        print(f"  {msg}")
    print(f"\n  Hint: sm facility  |  sm facility upgrades")


def _fmt_facility_upgrades(r):
    upgrades = r.get("upgrades", [])
    if not upgrades:
        print("No upgrades available.")
        return

    print(f"Available Upgrades ({len(upgrades)}):\n")
    for u in upgrades:
        cur_name = u.get("current_name") or u.get("name", "?")
        cur_level = u.get("current_level") or u.get("level", "?")
        up_name = u.get("upgrade_name") or u.get("upgrades_to", "?")
        up_level = u.get("upgrade_level", "")
        cost = u.get("cost") or u.get("upgrade_cost", 0)
        fid = u.get("facility_id", "")
        cost_str = f"{cost:,}" if isinstance(cost, (int, float)) else str(cost)
        line = f"  {cur_name} (lvl {cur_level}) → {up_name}"
        if up_level:
            line += f" (lvl {up_level})"
        line += f"  —  {cost_str} credits"
        if fid:
            line += f"  [{fid[:12]}]"
        print(line)

    print(f"\n  Hint: sm facility upgrade <facility_id>")


def _fmt_facility_quarters(r):
    owner = r.get("owner") or r.get("player_id", "")
    desc = r.get("description") or r.get("name", "")
    access = r.get("access") or r.get("category", "")

    header = f"{owner}'s Quarters" if owner else "Quarters"
    print(header)
    if access:
        print(f"  Access: {access}")
    if desc:
        print(f"\n  {desc}")
        print(f"\n  Hint: sm facility decorate \"new description\"  |  sm facility")
    else:
        print("  (no description set)")
        print("  Hint: sm facility decorate \"your description here\"")


def _fmt_facility_help(r):
    actions = r.get("actions", [])
    msg = r.get("message", "")
    if msg:
        print(msg)
    if actions:
        print("Facility Actions:\n")
        for a in actions:
            if isinstance(a, dict):
                name = a.get("action") or a.get("name", "?")
                desc = a.get("description", "")
                print(f"  {name:<20} {desc}")
            else:
                print(f"  {a}")
    if not actions and not msg:
        print("Use 'sm facility --help' for CLI usage.")
