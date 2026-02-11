import json
import time


def cmd_status(api, args):
    resp = api._post("get_status")
    r = resp.get("result", {})
    p = r.get("player", {})
    s = r.get("ship", {})

    sys_name = p.get("current_system_name") or p.get("current_system", "?")
    sys_id = p.get("current_system_id") or p.get("current_system", "")
    poi_name = p.get("current_poi_name") or p.get("current_poi", "")
    poi_id = p.get("current_poi_id") or p.get("current_poi", "")
    base_id = p.get("docked_at_base") or p.get("docked_base_id", "")

    location = sys_name
    if sys_id and sys_id != sys_name:
        location += f" ({sys_id})"
    if poi_name:
        location += f" / {poi_name}"
        if poi_id and poi_id != poi_name:
            location += f" ({poi_id})"
    if base_id:
        location += f" [docked: {base_id}]"

    print(f"Credits: {p.get('credits', '?')}")
    print(f"Location: {location}")
    print(f"Ship: {s.get('class_id') or s.get('name', '?')}")
    print(f"Hull: {s.get('hull', '?')}/{s.get('max_hull', '?')} | Fuel: {s.get('fuel', '?')}/{s.get('max_fuel', '?')}")
    print(f"Cargo: {s.get('cargo_used', '?')}/{s.get('cargo_capacity', '?')}")


def cmd_ship(api, args):
    as_json = getattr(args, "json", False)
    resp = api._post("get_ship")
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    r = resp.get("result", {})
    s = r.get("ship", r)

    print(f"Ship: {s.get('class_id') or s.get('name', '?')}")
    print(f"Hull: {s.get('hull', '?')}/{s.get('max_hull', '?')} | Shield: {s.get('shield', '?')}/{s.get('max_shield', '?')}")
    print(f"Fuel: {s.get('fuel', '?')}/{s.get('max_fuel', '?')}")
    print(f"Cargo: {s.get('cargo_used', '?')}/{s.get('cargo_capacity', '?')}")
    print(f"CPU: {s.get('cpu_used', '?')}/{s.get('cpu_capacity') or s.get('cpu', '?')} | Power: {s.get('power_used', '?')}/{s.get('power_capacity') or s.get('power', '?')}")

    # Prefer the rich module list at result.modules over ship.modules (which may be just IDs)
    modules = r.get("modules") or s.get("modules") or s.get("installed_modules", [])
    # Filter to only rich dicts if we got a mix
    rich_modules = [m for m in modules if isinstance(m, dict)]
    if rich_modules:
        print(f"\nModules ({len(rich_modules)}):")
        for m in rich_modules:
            name = m.get("name") or m.get("module_id") or m.get("id", "?")
            mtype = m.get("type") or m.get("type_id", "")
            quality = m.get("quality_grade") or ""
            wear = m.get("wear_status") or ""
            line = f"  {name}"
            if mtype:
                line += f" [{mtype}]"
            parts = []
            if quality:
                parts.append(quality)
            if wear and wear != "Pristine":
                parts.append(wear)
            if parts:
                line += f" ({', '.join(parts)})"
            print(line)
    elif modules:
        print(f"\nModules ({len(modules)}):")
        for m in modules:
            print(f"  {m}")

    # Cargo / inventory
    cargo = s.get("cargo") or r.get("cargo", [])
    if cargo:
        print(f"\nCargo ({s.get('cargo_used', '?')}/{s.get('cargo_capacity', '?')}):")
        for item in cargo:
            if isinstance(item, dict):
                name = item.get("item_id") or item.get("name", "?")
                qty = item.get("quantity", 1)
                print(f"  {name} x{qty}")
            else:
                print(f"  {item}")


def cmd_pois(api, args):
    resp = api._post("get_system")
    pois = resp.get("result", {}).get("pois", [])
    pois.sort(key=lambda p: p.get("distance", 0))
    for p in pois:
        name = p.get("name") or p.get("type") or "unnamed"
        ptype = p.get("type", "?")
        line = f"{name} [{ptype}]"
        if p.get("distance") is not None:
            line += f" ({p['distance']} AU)"
        base_id = p.get("base_id")
        if base_id:
            line += f" *base:{base_id}*"
        line += f"\n  id: {p.get('id', '?')}"
        print(line)


def cmd_system(api, args):
    resp = api._post("get_system")
    r = resp.get("result", {})
    sys_info = r.get("system", r)

    print(f"System: {sys_info.get('name') or sys_info.get('system_name', '?')}")
    print(f"Security: {r.get('security_status') or sys_info.get('police_level', '?')}")
    print()

    pois = r.get("pois", [])
    print(f"POIs ({len(pois)}):")
    for p in pois:
        name = p.get("name") or p.get("type") or "?"
        ptype = p.get("type", "?")
        print(f"  {name} [{ptype}] id:{p.get('id', '?')}")
    print()

    conns = sys_info.get("connections", [])
    print(f"Connections ({len(conns)}):")
    for c in conns:
        if isinstance(c, str):
            print(f"  \u2192 {c}")
        else:
            name = c.get("name") or c.get("system_name") or c.get("id", "?")
            cid = c.get("id") or c.get("system_id", "?")
            print(f"  \u2192 {name} (id:{cid})")


def cmd_poi(api, args):
    as_json = getattr(args, "json", False)
    resp = api._post("get_poi")
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    r = resp.get("result", {})
    p = r.get("poi", r)

    print(f"POI: {p.get('name', '?')} [{p.get('type', '?')}]")
    pid = p.get("id") or p.get("poi_id", "")
    if pid:
        print(f"  id: {pid}")

    resources = p.get("resources", [])
    if resources:
        print("\nResources:")
        for res in resources:
            if isinstance(res, dict):
                name = res.get("name") or res.get("resource_id", "?")
                richness = res.get("richness") or res.get("abundance", "")
                line = f"  {name}"
                if richness:
                    line += f" ({richness})"
                print(line)
            else:
                print(f"  {res}")

    base = p.get("base") or p.get("base_id")
    if base:
        if isinstance(base, dict):
            print(f"\nBase: {base.get('name', '?')} (id:{base.get('id', '?')})")
        else:
            print(f"\nBase: {base}")


def cmd_base(api, args):
    as_json = getattr(args, "json", False)
    resp = api._post("get_base")
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    if resp.get("error"):
        err = resp["error"]
        print(f"ERROR: {err.get('message', err) if isinstance(err, dict) else err}")
        return
    r = resp.get("result", {})
    b = r.get("base", r)

    print(f"Base: {b.get('name', '?')}")
    bid = b.get("id") or b.get("base_id", "")
    if bid:
        print(f"  id: {bid}")
    owner = b.get("owner") or b.get("owner_name")
    if owner:
        print(f"  Owner: {owner}")

    services = b.get("services", [])
    if services:
        print(f"\nServices: {', '.join(services)}")

    market = b.get("has_market") or b.get("market")
    if market:
        print("Market: available (use 'sm listings' to browse)")

    # Show storage hints when base has storage service
    svc_lower = [s.lower() for s in services]
    if any("storage" in s for s in svc_lower):
        print("\nStorage commands:")
        print("  sm deposit-items <item_id> <quantity>")
        print("  sm withdraw-items <item_id> <quantity>")
        print("  sm deposit-credits <amount>")
        print("  sm withdraw-credits <amount>")
        print("  sm send-gift <recipient> [item_id] [quantity] [credits] [message]")


def cmd_cargo(api, args):
    resp = api._post("get_cargo")
    r = resp.get("result", {})
    items = r.get("cargo", [])
    print(f"{r.get('used', 0)}/{r.get('capacity', '?')} used")
    if not items:
        print("No cargo items.")
    else:
        for item in items:
            name = item.get("item_id") or item.get("name") or item.get("id")
            qty = item.get("quantity", 1)
            print(f"  {name} x{qty}")


COMBAT_SHIP_CLASSES = {
    "fighter", "heavy_fighter", "interceptor", "assault", "destroyer",
    "battlecruiser", "dreadnought", "pirate", "raider",
    "combat_frigate", "war_barge",
}

ARMED_SHIP_CLASSES = {
    "corvette", "frigate", "gunship", "cruiser",
}


def _threat_level(nearby_info, scan_info=None):
    """Estimate threat from nearby data + optional scan results.

    Returns (level, reasons) where level is 0-20 and reasons is a list of strings.
    Thresholds: 0 safe, 1-5 low, 6-10 medium, 11-15 high, 16+ deadly.
    """
    level = 0
    reasons = []

    ship = (nearby_info.get("ship_class") or "").lower()
    in_combat = nearby_info.get("in_combat", False)

    # Ship class analysis
    if any(tag in ship for tag in ("combat", "fighter", "assault", "pirate",
                                    "raider", "destroyer", "interceptor",
                                    "dreadnought", "war", "battlecruiser")):
        level += 8
        reasons.append(f"combat ship ({ship})")
    elif any(tag in ship for tag in ("corvette", "frigate", "gunship", "cruiser")):
        level += 5
        reasons.append(f"armed ship ({ship})")
    elif any(tag in ship for tag in ("mining", "hauler", "transport", "starter",
                                      "shuttle", "explorer", "prospector")):
        level += 0
        reasons.append(f"civilian ship ({ship})")
    elif ship:
        level += 2
        reasons.append(f"unknown class ({ship})")

    if in_combat:
        level += 3
        reasons.append("currently in combat")

    # Scan data enrichment
    if scan_info and scan_info.get("success"):
        revealed = scan_info.get("revealed_info") or {}

        # Weapons
        weapons = revealed.get("weapons") or revealed.get("weapon_count", 0)
        if isinstance(weapons, list):
            weapons = len(weapons)
        if weapons and weapons > 0:
            level += min(weapons * 2, 6)
            reasons.append(f"{weapons} weapon(s)")

        # Hull/shield strength
        hull = revealed.get("hull") or revealed.get("max_hull", 0)
        shield = revealed.get("shield") or revealed.get("max_shield", 0)
        if hull and hull > 200:
            level += 3
            reasons.append(f"heavy hull ({hull})")
        if shield and shield > 100:
            level += 3
            reasons.append(f"strong shields ({shield})")

        # Cargo (low cargo on a combat ship = hunting)
        cargo_used = revealed.get("cargo_used", None)
        cargo_cap = revealed.get("cargo_capacity", None)
        if cargo_used is not None and cargo_cap and cargo_cap > 0:
            if cargo_used / cargo_cap < 0.1 and level >= 5:
                level += 3
                reasons.append("empty cargo (likely hunting)")

    return level, reasons


CIVILIAN_SHIPS = {
    "mining", "hauler", "transport", "starter", "shuttle", "explorer",
    "prospector", "freighter", "cargo", "mule", "barge",
}


def _ship_role(ship_class):
    """Classify a ship as civilian or military."""
    sc = (ship_class or "").lower()
    if any(tag in sc for tag in CIVILIAN_SHIPS):
        return "civilian"
    return "military"


def _threat_emoji(level):
    if level <= 0:
        return "\u2b1c"       # white square
    elif level <= 5:
        return "\U0001f7e8"   # yellow square
    elif level <= 10:
        return "\U0001f7e7"   # orange square
    elif level <= 15:
        return "\U0001f7e5"   # red square
    else:
        return "\u2620\ufe0f" # skull and crossbones


def _extract_notifications(resp):
    """Pull notifications out of an API response without printing them."""
    notifs = list(resp.get("notifications") or [])
    result = resp.get("result")
    if isinstance(result, dict):
        nested = result.get("notifications")
        if nested:
            notifs = notifs + list(nested)
    return notifs


def cmd_nearby(api, args):
    scan = getattr(args, "scan", False)
    as_json = getattr(args, "json", False)

    # Suppress auto-printing of notifications so we can parse them
    orig_print = api._print_notifications
    api._print_notifications = lambda resp: None
    try:
        resp = api._post("get_nearby")
        poi_resp = api._post("get_poi")
    finally:
        api._print_notifications = orig_print

    notifs = _extract_notifications(resp)
    notifs += _extract_notifications(poi_resp)
    r = resp.get("result", {})
    poi_r = poi_resp.get("result", {})
    poi_info = poi_r.get("poi") or poi_r
    players = r.get("nearby") or r.get("players", [])
    pirates = r.get("pirates", [])

    # Scan each player if requested
    scan_results = {}
    has_scanner = None
    if scan and players:
        try:
            ship_resp = api._post("get_ship")
            modules = ship_resp.get("result", {}).get("modules", [])
            has_scanner = any(
                "scan" in (m.get("type") or m.get("type_id") or m.get("name") or "").lower()
                for m in modules if isinstance(m, dict)
            )
        except Exception:
            has_scanner = None

        for i, p in enumerate(players):
            pid = p.get("player_id") or p.get("id", "")
            if not pid:
                continue
            if i > 0:
                print(f"  scanning... (waiting for rate limit)", flush=True)
                time.sleep(11)
            try:
                scan_resp = api._post("scan", {"target_id": pid})
                sr = scan_resp.get("result", {})
                scan_data = sr.get("Result", sr)
                scan_results[pid] = scan_data
            except Exception as e:
                scan_results[pid] = {"success": False, "error": str(e)}

    if as_json and not scan:
        print(json.dumps(r, indent=2))
        return

    # --- Header: POI ---
    poi_name = poi_info.get("name") or r.get("poi_name") or r.get("poi_id", "?")
    poi_id = poi_info.get("id") or r.get("poi_id", "")
    poi_type = poi_info.get("type", "")
    sys_id = poi_info.get("system_id", "")
    pos = poi_info.get("position") or {}
    header = f"`{poi_name}`(poi:{poi_id}) [{poi_type}]"
    if sys_id:
        header += f" in {sys_id}"
    if pos:
        header += f" @({pos.get('x', '?')},{pos.get('y', '?')})"
    print(header)

    desc = poi_info.get("description", "")
    if desc:
        print(f"  {desc}")

    base_info = poi_r.get("base") or poi_info.get("base")
    if base_info and isinstance(base_info, dict):
        bname = base_info.get("name", "?")
        bid = base_info.get("id", "?")
        print(f"  \U0001f3ed base: `{bname}`({bid})")

    # --- Resources ---
    resources = poi_r.get("resources") or poi_info.get("resources", [])
    if resources:
        parts = []
        for res in resources:
            if isinstance(res, dict):
                name = res.get("name") or res.get("resource_id", "?")
                richness = res.get("richness", "")
                remaining = res.get("remaining_display") or res.get("remaining", "")
                part = f"{name}({richness})"
                if remaining and remaining != "unlimited" and remaining != -1:
                    part += f"[{remaining}]"
                parts.append(part)
        print("  " + "  ".join(parts))

    print()

    # --- Counts ---
    player_count = len(players)
    pirate_count = r.get("pirate_count", len(pirates))
    print(f"\U0001f468\u200d\U0001f468\u200d\U0001f467\u200d\U0001f467 {player_count} / \U0001f3f4\u200d\u2620\ufe0f {pirate_count}")
    print()

    # --- Player/pirate table ---
    rows = []
    for p in players:
        name = p.get("username") or p.get("name") or "anonymous"
        pid = p.get("player_id") or p.get("id", "")
        ship = p.get("ship_class", "?")
        clan = p.get("clan_tag", "")
        in_combat = p.get("in_combat", False)
        anon = p.get("anonymous", False)
        status_msg = p.get("status_message", "")
        pri_color = p.get("primary_color", "")
        sec_color = p.get("secondary_color", "")

        scan_data = scan_results.get(pid)
        level, _ = _threat_level(p, scan_data)
        emoji = _threat_emoji(level)
        role = _ship_role(ship)

        ship_col = f"{role}({ship}:{pid})"
        clan_str = f"[{clan}] " if clan else ""
        display_name = "\u2753" if anon else name
        name_col = f"{clan_str}`{display_name}`(user:{pid})"
        if in_combat:
            name_col += " \u2694\ufe0f"
        # Annotations after the main columns
        notes = []
        if status_msg:
            notes.append(f"\u2709 {status_msg}")
        if pri_color and pri_color != "#FFFFFF":
            notes.append(f"\U0001f3a8{pri_color}")
        if anon:
            notes.append("anon")
        note_str = "  " + " | ".join(notes) if notes else ""
        rows.append((level, emoji, ship_col, name_col, note_str))

    for p in pirates:
        name = p.get("name") or p.get("type", "pirate")
        plevel = p.get("level", "?")
        pid = p.get("id") or p.get("pirate_id", "")
        pid_label = pid if pid else "npc"
        level, _ = _threat_level(p)
        emoji = _threat_emoji(level)
        rows.append((level, emoji, f"pirate(L{plevel}:{pid_label})", f"`{name}`", ""))

    if rows:
        # Column widths
        level_w = max(len(str(r[0])) for r in rows)
        ship_w = max(len(r[2]) for r in rows)

        for level, emoji, ship_col, name_col, note_str in rows:
            lvl_str = str(level).rjust(level_w) if level > 0 else " " * level_w
            print(f" {lvl_str} {emoji} {ship_col:<{ship_w}}  {name_col}{note_str}")
    else:
        print("  No one nearby.")

    # --- Legend ---
    print(f"\n\u2b1c safe  \U0001f7e8  \U0001f7e7  \U0001f7e5  \u2620\ufe0f dangerous")

    # --- Command hints ---
    if players:
        first = players[0]
        example_id = first.get("player_id") or first.get("id", "<id>")
        print(f"\n  Hint: sm scan {example_id}  |  sm attack {example_id}  |  sm trade-offer {example_id}")

    # --- Arrival/departure log ---
    movements = []
    for n in notifs:
        msg_type = n.get("msg_type", "")
        data = n.get("data") or {}
        if msg_type == "poi_arrival":
            uname = data.get("username", "?")
            clan = data.get("clan_tag", "")
            clan_str = f"[{clan}] " if clan else ""
            movements.append(f"  \U0001f6ec {clan_str}`{uname}`")
        elif msg_type == "poi_departure":
            uname = data.get("username", "?")
            clan = data.get("clan_tag", "")
            clan_str = f"[{clan}] " if clan else ""
            movements.append(f"  \U0001f4a8 {clan_str}`{uname}`")

    if movements:
        print()
        for m in movements:
            print(m)

    if as_json:
        combined = {"nearby": r, "scans": scan_results}
        print(json.dumps(combined, indent=2))


def cmd_notifications(api, args):
    # _post prints notifications automatically; just trigger a call
    resp = api._post("get_status")
    if not resp.get("notifications"):
        print("No notifications.")


def cmd_wrecks(api, args):
    as_json = getattr(args, "json", False)
    resp = api._post("get_wrecks")
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    r = resp.get("result", {})
    wrecks = r.get("wrecks", [])
    if not wrecks:
        print("No wrecks at this location.")
        return

    for w in wrecks:
        wid = w.get("id") or w.get("wreck_id", "?")
        owner = w.get("owner") or w.get("ship_class") or "unknown"
        print(f"Wreck: {owner} (id:{wid})")
        cargo = w.get("cargo") or w.get("items", [])
        if cargo:
            for item in cargo:
                if isinstance(item, dict):
                    name = item.get("item_id") or item.get("name", "?")
                    qty = item.get("quantity", 1)
                    print(f"  {name} x{qty}")
                else:
                    print(f"  {item}")
        modules = w.get("modules", [])
        if modules:
            for m in modules:
                if isinstance(m, dict):
                    print(f"  [mod] {m.get('name') or m.get('module_id', '?')}")
                else:
                    print(f"  [mod] {m}")

    print("\n  Hint: sm loot-wreck <wreck_id> <item_id> <qty>  |  sm salvage-wreck <wreck_id>")


def cmd_listings(api, args):
    as_json = getattr(args, "json", False)
    resp = api._post("get_listings")
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    r = resp.get("result", {})
    listings = r.get("listings", [])
    if not listings:
        print("No market listings at this base.")
        print("\n  Create one: sm list-item <item_id> <qty> <price>")
        print("              sm create-sell-order <item_id> <qty> <price>")
        print("              sm create-buy-order <item_id> <qty> <price>")
        return

    # Table header
    print(f"{'Item':<25} {'Qty':>5} {'Price':>10} {'Seller':<20} {'ID'}")
    print("-" * 80)
    for l in listings:
        item = l.get("item_id") or l.get("item_name", "?")
        qty = l.get("quantity", "?")
        price = l.get("price_each") or l.get("price", "?")
        seller = l.get("seller_name") or l.get("seller", "?")
        lid = l.get("id") or l.get("listing_id", "?")
        print(f"{item:<25} {qty:>5} {price:>10} {seller:<20} {lid}")

    print(f"\n  Hint: sm buy-listing <listing_id>")
    print("        sm view-market [item_id]  |  sm estimate-purchase <item_id> <qty>")
    print("  Sell:  sm list-item <item_id> <qty> <price>  |  sm create-sell-order <item_id> <qty> <price>")
    print("  Buy:   sm create-buy-order <item_id> <qty> <price>  |  sm cancel-order <order_id>")
