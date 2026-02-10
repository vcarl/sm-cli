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
    print(f"CPU: {s.get('cpu_used', '?')}/{s.get('cpu', '?')} | Power: {s.get('power_used', '?')}/{s.get('power', '?')}")

    modules = s.get("modules") or s.get("installed_modules", [])
    if modules:
        print(f"\nModules ({len(modules)}):")
        for m in modules:
            if isinstance(m, dict):
                name = m.get("name") or m.get("module_id") or m.get("id", "?")
                mid = m.get("id") or m.get("module_id", "")
                slot = m.get("slot", "")
                line = f"  {name}"
                if slot:
                    line += f" [{slot}]"
                if mid and mid != name:
                    line += f" (id:{mid})"
                print(line)
            else:
                print(f"  {m}")


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

    Returns (level, reasons) where level is 0-5 and reasons is a list of strings.
    """
    level = 0
    reasons = []

    ship = (nearby_info.get("ship_class") or "").lower()
    in_combat = nearby_info.get("in_combat", False)

    # Ship class analysis
    if any(tag in ship for tag in ("combat", "fighter", "assault", "pirate",
                                    "raider", "destroyer", "interceptor",
                                    "dreadnought", "war", "battlecruiser")):
        level += 3
        reasons.append(f"combat ship ({ship})")
    elif any(tag in ship for tag in ("corvette", "frigate", "gunship", "cruiser")):
        level += 2
        reasons.append(f"armed ship ({ship})")
    elif any(tag in ship for tag in ("mining", "hauler", "transport", "starter",
                                      "shuttle", "explorer", "prospector")):
        level += 0
        reasons.append(f"civilian ship ({ship})")
    elif ship:
        level += 1
        reasons.append(f"unknown class ({ship})")

    if in_combat:
        level += 1
        reasons.append("currently in combat")

    # Scan data enrichment
    if scan_info and scan_info.get("success"):
        revealed = scan_info.get("revealed_info") or {}

        # Weapons
        weapons = revealed.get("weapons") or revealed.get("weapon_count", 0)
        if isinstance(weapons, list):
            weapons = len(weapons)
        if weapons and weapons > 0:
            level += min(weapons, 2)
            reasons.append(f"{weapons} weapon(s)")

        # Hull/shield strength
        hull = revealed.get("hull") or revealed.get("max_hull", 0)
        shield = revealed.get("shield") or revealed.get("max_shield", 0)
        if hull and hull > 200:
            level += 1
            reasons.append(f"heavy hull ({hull})")
        if shield and shield > 100:
            level += 1
            reasons.append(f"strong shields ({shield})")

        # Cargo (low cargo on a combat ship = hunting)
        cargo_used = revealed.get("cargo_used", None)
        cargo_cap = revealed.get("cargo_capacity", None)
        if cargo_used is not None and cargo_cap and cargo_cap > 0:
            if cargo_used / cargo_cap < 0.1 and level >= 2:
                level += 1
                reasons.append("empty cargo (likely hunting)")

    return level, reasons


def _threat_label(level):
    if level >= 5:
        return "EXTREME"
    labels = {0: "NONE", 1: "LOW", 2: "MODERATE", 3: "HIGH", 4: "DANGEROUS"}
    return labels.get(level, "UNKNOWN")


def _threat_bar(level):
    filled = min(level, 5)
    empty = 5 - filled
    return "[" + "#" * filled + "." * empty + "]"


def cmd_nearby(api, args):
    scan = getattr(args, "scan", False)
    as_json = getattr(args, "json", False)
    resp = api._post("get_nearby")
    r = resp.get("result", {})
    players = r.get("nearby") or r.get("players", [])
    pirates = r.get("pirates", [])

    if not players and not pirates:
        print("No one nearby.")
        return

    if as_json and not scan:
        print(json.dumps(r, indent=2))
        return

    # Scan each player if requested
    scan_results = {}
    has_scanner = None
    if scan and players:
        # Check if we have a scanner module equipped
        try:
            ship_resp = api._post("get_ship")
            modules = ship_resp.get("result", {}).get("modules", [])
            has_scanner = any(
                "scan" in (m.get("type") or m.get("type_id") or m.get("name") or "").lower()
                for m in modules if isinstance(m, dict)
            )
        except Exception:
            has_scanner = None  # unknown

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
                # Handle nested Result key
                scan_data = sr.get("Result", sr)
                scan_results[pid] = scan_data
            except Exception as e:
                scan_results[pid] = {"success": False, "error": str(e)}

    # Display results
    total_players = len(players)
    pirate_count = r.get("pirate_count", len(pirates))
    poi_id = r.get("poi_id", "")
    if poi_id:
        print(f"Location: {poi_id}")
    print(f"Players: {total_players}  |  Pirates: {pirate_count}")
    print()

    for p in players:
        name = p.get("username") or p.get("name") or "anonymous"
        pid = p.get("player_id") or p.get("id", "")
        ship = p.get("ship_class", "?")
        clan = p.get("clan_tag", "")
        in_combat = p.get("in_combat", False)

        scan_data = scan_results.get(pid)
        level, reasons = _threat_level(p, scan_data)
        label = _threat_label(level)
        bar = _threat_bar(level)

        # Header line
        header = f"  {name}"
        if clan:
            header += f" <{clan}>"
        header += f"  [{ship}]"
        if in_combat:
            header += "  *IN COMBAT*"
        print(header)

        # Threat line
        rating = f" ({level})" if level >= 5 else ""
        print(f"    Threat: {bar} {label}{rating}")
        if reasons:
            print(f"    Basis:  {', '.join(reasons)}")

        # Scan details if available
        if scan_data:
            success = scan_data.get("success", False)
            if success:
                revealed = scan_data.get("revealed_info") or {}
                details = []
                for key in ("hull", "max_hull", "shield", "max_shield",
                            "weapons", "cargo_used", "cargo_capacity"):
                    val = revealed.get(key)
                    if val is not None:
                        details.append(f"{key}={val}")
                if details:
                    print(f"    Scan:   {', '.join(details)}")
            else:
                error = scan_data.get("error")
                if error:
                    reason = str(error)
                elif has_scanner is False:
                    reason = "no scanner module equipped"
                else:
                    reason = "target may have countermeasures"
                print(f"    Scan:   FAILED ({reason})")

        # Player ID
        if pid:
            print(f"    ID:     {pid}")
        print()

    # NPC pirates
    if pirates:
        print("NPC Pirates:")
        for p in pirates:
            name = p.get("name") or p.get("type", "pirate")
            plevel = p.get("level", "?")
            print(f"  {name} (level {plevel})")

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
