import json
import time


def cmd_status(api, args):
    as_json = getattr(args, "json", False)
    resp = api._post("get_status")
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    r = resp.get("result", {})
    p = r.get("player", {})
    s = r.get("ship", {})

    sys_name = p.get("current_system", "?")
    poi_name = p.get("current_poi", "")
    base_id = p.get("docked_at_base", "")

    location = sys_name
    if poi_name:
        location += f" / {poi_name}"
    if base_id:
        location += f" [docked: {base_id}]"

    print(f"Credits: {p.get('credits', '?')}")
    print(f"Location: {location}")

    # Player context
    faction_id = p.get("faction_id")
    if faction_id:
        rank = p.get("faction_rank", "")
        faction_str = f"Faction: {faction_id}"
        if rank:
            faction_str += f" ({rank})"
        print(faction_str)
    xp = p.get("experience")
    if xp is not None:
        print(f"XP: {xp}")
    home = p.get("home_base")
    if home:
        print(f"Home Base: {home}")

    # Ship vitals
    ship_name = s.get("name", "")
    ship_class = s.get("class_id", "?")
    ship_label = f"{ship_name} ({ship_class})" if ship_name and ship_name != ship_class else ship_class
    print(f"Ship: {ship_label}")
    print(f"Hull: {s.get('hull', '?')}/{s.get('max_hull', '?')} | Shield: {s.get('shield', '?')}/{s.get('max_shield', '?')} | Fuel: {s.get('fuel', '?')}/{s.get('max_fuel', '?')}")
    print(f"Cargo: {s.get('cargo_used', '?')}/{s.get('cargo_capacity', '?')}")

    # Situational flags
    flags = []
    if p.get("is_cloaked"):
        flags.append("CLOAKED")
    if p.get("towing_wreck_id"):
        flags.append(f"TOWING:{p['towing_wreck_id']}")
    if p.get("anonymous"):
        flags.append("ANONYMOUS")
    disruption = s.get("disruption_ticks_remaining")
    if disruption:
        flags.append(f"DISRUPTED:{disruption}t")
    if flags:
        print(f"Flags: [{'] ['.join(flags)}]")

    # Modules summary
    modules = r.get("modules", [])
    if modules:
        mod_names = []
        for m in modules:
            if isinstance(m, dict):
                mod_names.append(m.get("name") or m.get("module_id") or m.get("type", "?"))
            else:
                mod_names.append(str(m))
        print(f"Modules: {', '.join(mod_names)}")


def cmd_ship(api, args):
    as_json = getattr(args, "json", False)
    resp = api._post("get_ship")
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    r = resp.get("result", {})
    s = r.get("ship", r)
    cls = r.get("class", {})

    # Header with ship ID
    ship_id = s.get("id", "")
    ship_name = s.get("name") or cls.get("name") or s.get("class_id", "?")
    class_id = s.get("class_id") or cls.get("id", "")
    header = f"Ship: {ship_name}"
    if class_id and class_id != ship_name:
        header += f" ({class_id})"
    if ship_id:
        sid = ship_id[:12]
        header += f"  id:{sid}"
    print(header)

    # Stats
    print(f"Hull: {s.get('hull', '?')}/{s.get('max_hull', '?')} | Shield: {s.get('shield', '?')}/{s.get('max_shield', '?')} | Armor: {s.get('armor', '?')}")
    shield_recharge = s.get("shield_recharge")
    speed = s.get("speed")
    extras = []
    if shield_recharge is not None:
        extras.append(f"Shield Recharge: {shield_recharge}/tick")
    if speed is not None:
        extras.append(f"Speed: {speed}")
    if extras:
        print(f"{'  |  '.join(extras)}")
    print(f"Fuel: {s.get('fuel', '?')}/{s.get('max_fuel', '?')}")
    print(f"Cargo: {r.get('cargo_used', s.get('cargo_used', '?'))}/{r.get('cargo_max', s.get('cargo_capacity', '?'))}")
    print(f"CPU: {s.get('cpu_used', '?')}/{s.get('cpu_capacity', '?')} | Power: {s.get('power_used', '?')}/{s.get('power_capacity', '?')}")

    # Slot usage
    weapon_slots = s.get("weapon_slots") or cls.get("weapon_slots")
    defense_slots = s.get("defense_slots") or cls.get("defense_slots")
    utility_slots = s.get("utility_slots") or cls.get("utility_slots")
    if weapon_slots is not None or defense_slots is not None or utility_slots is not None:
        modules_list = r.get("modules") or s.get("modules") or []
        rich_modules = [m for m in modules_list if isinstance(m, dict)]
        used_w = sum(1 for m in rich_modules if (m.get("type") or "").lower() == "weapon")
        used_d = sum(1 for m in rich_modules if (m.get("type") or "").lower() == "defense")
        used_u = sum(1 for m in rich_modules if (m.get("type") or "").lower() in ("utility", "mining"))
        slot_parts = []
        if weapon_slots is not None:
            slot_parts.append(f"Weapon: {used_w}/{weapon_slots}")
        if defense_slots is not None:
            slot_parts.append(f"Defense: {used_d}/{defense_slots}")
        if utility_slots is not None:
            slot_parts.append(f"Utility: {used_u}/{utility_slots}")
        print(f"Slots: {' | '.join(slot_parts)}")

    # Special ability
    special = cls.get("special") or s.get("special")
    if special:
        print(f"Special: {special}")

    # Modules
    modules = r.get("modules") or s.get("modules") or []
    rich_modules = [m for m in modules if isinstance(m, dict)]
    if rich_modules:
        print(f"\nModules ({len(rich_modules)}):")
        for m in rich_modules:
            name = m.get("name") or m.get("module_id") or m.get("id", "?")
            mtype = m.get("type") or m.get("type_id", "")
            mid = m.get("id", "")
            type_id = m.get("type_id", "")
            quality = m.get("quality_grade") or ""
            wear = m.get("wear_status") or ""

            line = f"  {name}"
            if mtype:
                line += f" [{mtype}]"
            meta = []
            if quality and quality != "Standard":
                meta.append(quality)
            if wear and wear != "Pristine":
                meta.append(wear)
            if meta:
                line += f" ({', '.join(meta)})"
            print(line)

            # Stats line
            stats = []
            cpu = m.get("cpu_usage")
            power = m.get("power_usage")
            if cpu is not None:
                stats.append(f"cpu:{cpu}")
            if power is not None:
                stats.append(f"power:{power}")
            # All optional stat fields from the schema
            stat_keys = [
                "damage", "damage_type", "range", "reach", "cooldown",
                "current_ammo", "magazine_size", "ammo_type",
                "loaded_ammo_name",
                "mining_power", "mining_range",
                "harvest_power", "harvest_range",
                "scanner_power",
                "shield_bonus", "armor_bonus", "hull_bonus",
                "speed_bonus", "cargo_bonus",
                "fuel_efficiency",
                "cloak_strength",
                "drone_bandwidth", "drone_capacity",
            ]
            for key in stat_keys:
                val = m.get(key)
                if val is not None:
                    stats.append(f"{key.replace('_', ' ')}:{val}")
            special_mod = m.get("special")
            if special_mod:
                stats.append(f"special:{special_mod}")
            id_str = f"id:{mid[:12]}" if mid else ""
            if type_id:
                id_str = f"type:{type_id}  {id_str}"
            if stats or id_str:
                detail = "    "
                if stats:
                    detail += "  ".join(stats)
                if id_str:
                    if stats:
                        detail += "  "
                    detail += id_str
                print(detail)
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
                name = item.get("item_id", "?")
                qty = item.get("quantity", 1)
                print(f"  {name} x{qty}")
            else:
                print(f"  {item}")



def cmd_pois(api, args):
    resp = api._post("get_system")
    result = resp.get("result", {})
    system = result.get("system", {})
    pois = system.get("pois", [])

    current_poi = result.get("poi")
    if current_poi:
        name = current_poi.get("name") or current_poi.get("type") or "unnamed"
        ptype = current_poi.get("type", "?")
        print(f"{name} [{ptype}] (current)")
        print(f"  id: {current_poi.get('id', '?')}")

    if not pois:
        if not current_poi:
            print("No POIs found in current system")
        return

    for p in pois:
        name = p.get("name") or p.get("type") or "unnamed"
        ptype = p.get("type", "?")
        parts = [f"{name} [{ptype}]"]
        if p.get("has_base"):
            base_name = p.get("base_name") or p.get("base_id") or "base"
            parts.append(f"(base: {base_name})")
        online = p.get("online")
        if online:
            parts.append(f"({online} online)")
        print(" ".join(parts))
        print(f"  id: {p.get('id', '?')}")


def cmd_system(api, args):
    resp = api._post("get_system")
    r = resp.get("result", {})
    sys_info = r.get("system", r)

    print(f"System: {sys_info.get('name', '?')}")
    print(f"Security: {sys_info.get('security_status', '?')}")
    print()

    pois = sys_info.get("pois", [])
    print(f"POIs ({len(pois)}):")
    for p in pois:
        name = p.get("name") or p.get("type") or "?"
        ptype = p.get("type", "?")
        line = f"  {name} [{ptype}] id:{p.get('id', '?')}"
        if p.get("has_base"):
            base_name = p.get("base_name", "unknown")
            line += f"  base:{base_name}"
        online = p.get("online")
        if online:
            line += f"  ({online} online)"
        print(line)
    print()

    conns = sys_info.get("connections", [])
    print(f"Connections ({len(conns)}):")
    for c in conns:
        if isinstance(c, str):
            print(f"  \u2192 {c}")
        else:
            name = c.get("name", "?")
            cid = c.get("system_id", "?")
            dist = c.get("distance")
            line = f"  \u2192 {name} (id:{cid})"
            if dist is not None:
                line += f"  {dist} GU"
            print(line)


def cmd_poi(api, args):
    as_json = getattr(args, "json", False)
    resp = api._post("get_poi")
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    r = resp.get("result", {})
    p = r.get("poi", r)

    print(f"POI: {p.get('name', '?')} [{p.get('type', '?')}]")
    pid = p.get("id", "")
    if pid:
        print(f"  id: {pid}")
    desc = p.get("description")
    if desc:
        print(f"  {desc}")
    pos = p.get("position")
    if pos:
        print(f"  Position: ({pos.get('x', '?')}, {pos.get('y', '?')})")

    # Police presence
    police_drones = r.get("police_drones")
    police_warning = r.get("police_warning")
    if police_drones is not None or police_warning:
        print()
        if police_drones is not None:
            print(f"Police drones: {police_drones}")
        if police_warning:
            print(f"Warning: {police_warning}")

    # Resources (prefer result-level, fall back to poi-level)
    resources = r.get("resources") or p.get("resources", [])
    if resources:
        print("\nResources:")
        for res in resources:
            if isinstance(res, dict):
                name = res.get("name") or res.get("resource_id", "?")
                richness = res.get("richness", "")
                remaining = res.get("remaining_display") or res.get("remaining")
                line = f"  {name}"
                if richness:
                    line += f" ({richness})"
                if remaining is not None:
                    line += f"  remaining: {remaining}"
                print(line)
            else:
                print(f"  {res}")

    # Base
    base = r.get("base") or p.get("base") or p.get("base_id")
    if base:
        if isinstance(base, dict):
            print(f"\nBase: {base.get('name', '?')} [{base.get('type', '?')}]")
            print(f"  id: {base.get('id', '?')}")
            if base.get("empire"):
                print(f"  Empire: {base['empire']}")
            if base.get("faction_id"):
                print(f"  Faction: {base['faction_id']}")
            if base.get("owner_id"):
                print(f"  Owner: {base['owner_id']}")
            print(f"  Defense: {base.get('defense_level', '?')}  Public: {'yes' if base.get('public_access') else 'no'}")
            if base.get("has_drones"):
                print(f"  Has drones: yes")
            if base.get("description"):
                print(f"  {base['description']}")
            services = base.get("services", {})
            if services:
                active = [s for s, v in services.items() if v]
                if active:
                    print(f"  Services: {', '.join(sorted(active))}")
            facilities = base.get("facilities", [])
            if facilities:
                print(f"  Facilities: {', '.join(facilities)}")
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
    bid = b.get("id", "")
    if bid:
        print(f"  id: {bid}")
    owner_id = b.get("owner_id")
    if owner_id:
        print(f"  Owner: {owner_id}")

    services = b.get("services", {})
    if isinstance(services, dict):
        active = sorted(k for k, v in services.items() if v)
    else:
        active = list(services)
    if active:
        print(f"\nServices: {', '.join(active)}")

    # Service-specific command hints
    svc = services if isinstance(services, dict) else {}

    if svc.get("market"):
        print("\nMarket:")
        print("  sm listings                          Browse order book")
        print("  sm listings <item_id>                Detailed orders for an item")
        print("  sm market buy <item> <qty> <price>   Place a buy order")
        print("  sm market sell <item> <qty> <price>  Place a sell order")
        print("  sm market                            View your active orders")
        print("  sm market cancel <order_id>          Cancel an order")
        print("  sm analyze-market                    Price trends & trade insights")

    if svc.get("storage"):
        print("\nStorage:")
        print("  sm storage deposit <item_id> <qty>   Deposit items")
        print("  sm storage withdraw <item_id> <qty>  Withdraw items")
        print("  sm storage deposit --credits <amt>   Deposit credits")
        print("  sm storage withdraw --credits <amt>  Withdraw credits")
        print("  sm send-gift <player> [item] [qty] [credits] [msg]")

    if svc.get("missions"):
        print("\nMissions:")
        print("  sm missions                          Browse & track missions")
        print("  sm missions available                Available missions here")
        print("  sm missions accept <id>              Accept a mission")

    if svc.get("repair"):
        print("\nRepair: sm repair")
    if svc.get("refuel"):
        print("Refuel: sm refuel")
    if svc.get("shipyard"):
        print("Shipyard: sm ships  |  sm buy-ship <id>  |  sm sell-ship <id>")
    if svc.get("crafting"):
        print("Crafting: sm recipes  |  sm recipes craft <recipe_id> [count]")
    if svc.get("insurance"):
        print("Insurance: sm insurance-buy  |  sm insurance-claim")

    print("\nFacilities:")
    print("  sm facility help                     Full facility documentation")
    print("  sm facility types                    Browse buildable facility types")
    print("  sm facility list                     Your facilities at this base")
    print("  sm facility build <type>             Build a new facility")
    print("  sm facility upgrades <facility_id>   Available upgrades")
    print("  sm facility upgrade <facility_id>    Upgrade a facility")


def cmd_cargo(api, args):
    resp = api._post("get_cargo")
    r = resp.get("result", {})
    items = r.get("cargo", [])
    print(f"{r.get('used', 0)}/{r.get('capacity', '?')} used")
    if not items:
        print("No cargo items.")
    else:
        for item in items:
            name = item.get("item_id", "?")
            qty = item.get("quantity", 1)
            print(f"  {name} x{qty}")
    print("\n  Hint: sm sell <item> <qty>  |  sm listings  |  sm storage deposit <item> <qty>")


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
    players = r.get("nearby", [])
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

        timeout = getattr(args, "timeout", None)
        start_time = time.time() if timeout else None

        try:
            for i, p in enumerate(players):
                pid = p.get("player_id", "")
                if not pid:
                    continue

                # Check timeout before processing
                if timeout and start_time:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        print(f"  Timeout reached ({timeout}s). Scanned {i}/{len(players)} players.", flush=True)
                        break

                # Show progress
                print(f"  Scanning player {i+1}/{len(players)}...", flush=True)

                if i > 0:
                    time.sleep(11)
                try:
                    scan_resp = api._post("scan", {"target_id": pid})
                    sr = scan_resp.get("result", {})
                    scan_data = sr
                    scan_results[pid] = scan_data
                except Exception as e:
                    scan_results[pid] = {"success": False, "error": str(e)}
        except KeyboardInterrupt:
            print(f"\n  Scan interrupted. Scanned {len(scan_results)}/{len(players)} players.", flush=True)

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

    # --- Police presence ---
    police_drones = poi_r.get("police_drones")
    police_warning = poi_r.get("police_warning")
    if police_drones is not None or police_warning:
        police_parts = []
        if police_drones is not None:
            police_parts.append(f"\U0001f6e1\ufe0f {police_drones} police drones")
        if police_warning:
            police_parts.append(f"\u26a0\ufe0f {police_warning}")
        print("  " + "  ".join(police_parts))

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
    player_count = r.get("count", len(players))
    pirate_count = r.get("pirate_count", len(pirates))
    print(f"\U0001f468\u200d\U0001f468\u200d\U0001f467\u200d\U0001f467 {player_count} / \U0001f3f4\u200d\u2620\ufe0f {pirate_count}")
    print()

    # --- Player/pirate table ---
    rows = []
    for p in players:
        name = p.get("username") or "anonymous"
        pid = p.get("player_id", "")
        ship = p.get("ship_class", "?")
        clan = p.get("clan_tag", "")
        faction = p.get("faction_tag", "")
        in_combat = p.get("in_combat", False)
        anon = p.get("anonymous", False)
        status_msg = p.get("status_message", "")
        pri_color = p.get("primary_color", "")
        sec_color = p.get("secondary_color", "")

        scan_data = scan_results.get(pid)
        level, _ = _threat_level(p, scan_data)
        emoji = _threat_emoji(level)
        role = _ship_role(ship)

        ship_col = f"{role}({ship})"
        tags = ""
        if clan:
            tags += f"[{clan}]"
        if faction:
            tags += f"{{{faction}}}"
        if tags:
            tags += " "
        display_name = "\u2753" if anon else name
        name_col = f"{tags}`{display_name}`(user:{pid})"
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
        example_id = first.get("player_id", "<id>")
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


def _fmt_view_market_item(resp):
    """Format detailed view_market response for a specific item."""
    r = resp.get("result", resp)
    items = r.get("items", [])
    if not items:
        print("No market data available for this item.")
        return

    for item_data in items:
        item_id = item_data.get("item_id", "?")
        item_name = item_data.get("item_name", item_id)
        best_buy = item_data.get("best_buy")
        best_sell = item_data.get("best_sell")
        spread = item_data.get("spread")

        print(f"{item_name} ({item_id})")

        # Asks (sell orders - what's available to buy)
        sell_orders = item_data.get("sell_orders", [])
        if sell_orders:
            print(f"\n  Asks:")
            for order in sell_orders[:10]:  # Show top 10
                price = order.get("price_each", "?")
                qty = order.get("quantity", "?")
                source = order.get("source", "")
                seller_type = "NPC" if source == "station" else "Player"
                print(f"    {qty:>6} @ {price:>5} cr  [{seller_type}]")
        else:
            print("\n  No asks (cannot buy this item here)")

        # Bids (buy orders - what people want to buy)
        buy_orders = item_data.get("buy_orders", [])
        if buy_orders:
            print(f"\n  Bids:")
            for order in buy_orders[:10]:  # Show top 10
                price = order.get("price_each", "?")
                qty = order.get("quantity", "?")
                source = order.get("source", "")
                buyer_type = "NPC" if source == "station" else "Player"
                print(f"    {qty:>6} @ {price:>5} cr  [{buyer_type}]")
        else:
            print("\n  No bids (no one buying this item here)")

        # Summary
        if best_buy and best_sell:
            print(f"\n  Best bid: {best_buy} cr  |  Best ask: {best_sell} cr  |  Spread: {spread} cr")
        elif best_sell:
            print(f"\n  Best ask: {best_sell} cr")
        elif best_buy:
            print(f"\n  Best bid: {best_buy} cr")

        print(f"\n  Hint: sm buy {item_id} <qty>  |  sm sell {item_id} <qty>")


def cmd_listings(api, args):
    """Show market listings (uses view_market endpoint)."""
    as_json = getattr(args, "json", False)
    item_id = getattr(args, "item_id", None)

    # If item_id provided, show detailed view for that item
    if item_id:
        resp = api._post("view_market", {"item_id": item_id})
        if as_json:
            print(json.dumps(resp, indent=2))
            return
        _fmt_view_market_item(resp)
        return

    # Otherwise show overview of all items
    # NOTE: get_listings is deprecated, using view_market instead
    resp = api._post("view_market")
    if as_json:
        print(json.dumps(resp, indent=2))
        return

    r = resp.get("result", {})
    items = r.get("items", [])

    if not items:
        print("No market activity at this base.")
        print("\n  Create orders: sm market buy <item> <qty> <price>")
        print("                 sm market sell <item> <qty> <price>")
        return

    PAGE_SIZE = 20
    page = getattr(args, "page", 1) or 1
    total_pages = (len(items) + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    page_items = items[start:start + PAGE_SIZE]

    print("Market Listings:")
    print(f"{'Item ID':<25} {'Best Bid':>10} {'Best Ask':>10} {'Spread':>10} {'Bid Qty':>10} {'Bid Value':>12} {'Ask Qty':>10} {'Ask Value':>12}")
    print("-" * 117)

    for item_data in page_items:
        item_id = item_data.get("item_id", "?")
        best_buy = item_data.get("best_buy", 0)
        best_sell = item_data.get("best_sell", 0)

        # Get order data for market depth calculation
        buy_orders = item_data.get("buy_orders", [])
        sell_orders = item_data.get("sell_orders", [])

        # Calculate market depth (total quantity and total value)
        buy_qty_total = 0
        buy_value_total = 0
        sell_qty_total = 0
        sell_value_total = 0

        if buy_orders:
            for o in buy_orders:
                if isinstance(o, dict):
                    qty = o.get("quantity", 0)
                    price = o.get("price_each", 0)
                    buy_qty_total += qty
                    buy_value_total += qty * price
        else:
            buy_qty_total = item_data.get("buy_quantity", 0) or 0

        if sell_orders:
            for o in sell_orders:
                if isinstance(o, dict):
                    qty = o.get("quantity", 0)
                    price = o.get("price_each", 0)
                    sell_qty_total += qty
                    sell_value_total += qty * price
        else:
            sell_qty_total = item_data.get("sell_quantity", 0) or 0

        # Use server-provided spread, fall back to simple difference
        spread = ""
        spread_val = item_data.get("spread")
        if spread_val is not None:
            spread = f"{spread_val:+d}"
        elif best_buy and best_sell:
            spread = f"{best_sell - best_buy:+d}"

        buy_str = f"{best_buy}cr" if best_buy else "-"
        sell_str = f"{best_sell}cr" if best_sell else "-"
        buy_qty_str = f"{buy_qty_total:,}" if buy_qty_total else "-"
        buy_val_str = f"{buy_value_total:,}cr" if buy_value_total else "-"
        sell_qty_str = f"{sell_qty_total:,}" if sell_qty_total else "-"
        sell_val_str = f"{sell_value_total:,}cr" if sell_value_total else "-"

        print(f"{item_id:<25} {buy_str:>10} {sell_str:>10} {spread:>10} {buy_qty_str:>10} {buy_val_str:>12} {sell_qty_str:>10} {sell_val_str:>12}")

    print(f"\n  Page {page}/{total_pages}")
    if page < total_pages:
        print(f"  Next page: sm listings --page {page + 1}")

    print("\n  Bid = standing offer to buy (\"I'll pay 100cr, come to me\")")
    print("  Ask = standing offer to sell (\"I have steel at 150cr, come get it\")")
    print(f"\n  Hint: sm listings <item_id>  (detailed orders for an item)")
    print("        sm market buy <item_id> <qty> <price>  |  sm market sell <item_id> <qty> <price>")
