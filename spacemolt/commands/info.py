import json


def _fmt_poi(r):
    """Format POI data from a get_poi response result. Returns list of lines."""
    lines = []
    p = r.get("poi", r)

    name = p.get("name", "?")
    ptype = p.get("type", "?")
    pid = p.get("id", "")
    header = f"{name} [{ptype}]"
    if pid:
        header += f"  id: {pid}"
    lines.append(header)

    desc = p.get("description")
    if desc:
        lines.append(f"  {desc}")

    # Police presence
    police_drones = r.get("police_drones")
    police_warning = r.get("police_warning")
    if police_drones is not None:
        lines.append(f"  Police drones: {police_drones}")
    if police_warning:
        lines.append(f"  Warning: {police_warning}")

    # Resources
    resources = r.get("resources") or p.get("resources", [])
    if resources:
        lines.append("  Resources:")
        for res in resources:
            if isinstance(res, dict):
                rname = res.get("name") or res.get("resource_id", "?")
                rid = res.get("resource_id") or res.get("id", "")
                richness = res.get("richness", "")
                remaining = res.get("remaining_display") or res.get("remaining")
                line = f"    {rname}"
                if rid and rid != rname:
                    line += f" [{rid}]"
                if richness:
                    line += f" ({richness})"
                if remaining is not None:
                    line += f"  remaining: {remaining}"
                lines.append(line)
            else:
                lines.append(f"    {res}")

    # Base
    base = r.get("base") or p.get("base") or p.get("base_id")
    if base:
        if isinstance(base, dict):
            btype = base.get("type") or "base"
            lines.append(f"  Base: {base.get('name', '?')} [{btype}]  id: {base.get('id', '?')}")
        else:
            lines.append(f"  Base: {base}")

    return lines


def _fmt_nearby_summary(nearby_r, poi_r):
    """Format a compact nearby summary for sm status. Returns list of lines."""
    lines = []
    poi_info = poi_r.get("poi") or poi_r
    players = nearby_r.get("nearby", [])
    pirates = nearby_r.get("pirates", [])

    # Counts
    player_count = nearby_r.get("count", len(players))
    pirate_count = nearby_r.get("pirate_count", len(pirates))
    lines.append(f"\U0001f468\u200d\U0001f468\u200d\U0001f467\u200d\U0001f467 {player_count} / \U0001f3f4\u200d\u2620\ufe0f {pirate_count}")

    # Threat table
    rows = []
    for p in players:
        name = p.get("username") or "anonymous"
        pid = p.get("player_id", "")
        ship = p.get("ship_class", "?")
        clan = p.get("clan_tag", "")
        faction = p.get("faction_tag", "")
        in_combat = p.get("in_combat", False)
        anon = p.get("anonymous", False)

        level, _ = _threat_level(p)
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
        rows.append((level, emoji, ship_col, name_col))

    for p in pirates:
        name = p.get("name") or p.get("type", "pirate")
        plevel = p.get("level", "?")
        pid = p.get("id") or p.get("pirate_id", "")
        pid_label = pid if pid else "npc"
        level, _ = _threat_level(p)
        emoji = _threat_emoji(level)
        rows.append((level, emoji, f"pirate(L{plevel}:{pid_label})", f"`{name}`"))

    if rows:
        level_w = max(len(str(r[0])) for r in rows)
        ship_w = max(len(r[2]) for r in rows)
        for level, emoji, ship_col, name_col in rows:
            lvl_str = str(level).rjust(level_w) if level > 0 else " " * level_w
            lines.append(f" {lvl_str} {emoji} {ship_col:<{ship_w}}  {name_col}")

    lines.append(f"\u2b1c safe  \U0001f7e8  \U0001f7e7  \U0001f7e5  \u2620\ufe0f dangerous")

    return lines


def _fmt_wrecks(r):
    """Format wrecks data from a get_wrecks response result. Returns list of lines."""
    lines = []
    wrecks = r.get("wrecks", [])
    if not wrecks:
        return lines

    for w in wrecks:
        wid = w.get("wreck_id") or w.get("id", "?")
        ship_class = w.get("ship_class", "unknown")
        cargo = w.get("cargo", [])
        cargo_count = len(cargo)
        modules = w.get("modules", [])
        module_count = len(modules)
        salvage_value = w.get("salvage_value", 0)
        insured = w.get("insured", False)

        flags = []
        if insured:
            flags.append("INSURED")
        flag_str = f"  [{', '.join(flags)}]" if flags else ""

        line = f"  {ship_class}{flag_str}  (id:{wid})  Cargo: {cargo_count} | Modules: {module_count}"
        if salvage_value:
            line += f" | Salvage: {salvage_value:,} cr"
        lines.append(line)
        for c in cargo:
            lines.append(f"    - {c.get('name', c.get('item_id', '?'))}: {c.get('quantity', '?')}")

    return lines


def _fmt_battle(r):
    """Format compact battle status for sm status. Returns list of lines."""
    lines = []
    battle_id = r.get("battle_id", "?")
    is_participant = r.get("is_participant", False)
    if not is_participant:
        return lines

    participants = r.get("participants", [])
    sides = r.get("sides", [])

    # Side summary
    side_parts = []
    for side in sides:
        if isinstance(side, dict):
            sid = side.get("side_id") or side.get("id", "?")
            name = side.get("name") or side.get("faction_name") or side.get("faction_tag") or f"Side {sid}"
            count = side.get("member_count") or side.get("count") or side.get("player_count", "?")
            side_parts.append(f"{name}({count})")
    if side_parts:
        lines.append(f"  {' vs '.join(side_parts)}")

    # Participant table — show all with combat-critical info
    for p in participants:
        if not isinstance(p, dict):
            continue
        name = p.get("username") or p.get("player_id", "?")
        side = p.get("side_id", "?")
        stance = p.get("stance", "")
        zone = p.get("zone", "")
        hull_pct = p.get("hull_pct")
        shield_pct = p.get("shield_pct")
        ship = p.get("ship_class", "")
        target = p.get("target_id", "")
        dmg_dealt = p.get("damage_dealt", 0)
        dmg_taken = p.get("damage_taken", 0)
        kills = p.get("kill_count", 0)

        # Hull/shield bars (5 chars wide)
        def _bar(pct):
            if pct is None:
                return "???%"
            filled = max(0, min(5, pct // 20))
            return "\u2588" * filled + "\u2591" * (5 - filled) + f" {pct}%"

        line = f"  [{side}] {name}"
        if ship:
            line += f" ({ship})"
        if stance:
            line += f" [{stance}]"
        if zone:
            line += f" @{zone}"
        lines.append(line)

        detail = f"      H:{_bar(hull_pct)} S:{_bar(shield_pct)}"
        if target:
            detail += f"  \u2192{target}"
        stats = []
        if dmg_dealt:
            stats.append(f"dealt:{dmg_dealt}")
        if dmg_taken:
            stats.append(f"taken:{dmg_taken}")
        if kills:
            stats.append(f"kills:{kills}")
        if stats:
            detail += f"  {' '.join(stats)}"
        lines.append(detail)

    return lines


def _fmt_modules_combat(modules):
    """Format modules with combat-critical info (cooldowns, ammo). Returns list of lines."""
    lines = []
    for m in modules:
        if not isinstance(m, dict):
            continue
        name = m.get("name") or m.get("module_id") or m.get("type", "?")
        mtype = (m.get("type") or "").lower()
        cooldown = m.get("cooldown")
        current_ammo = m.get("current_ammo")
        magazine_size = m.get("magazine_size")
        damage = m.get("damage")
        ammo_name = m.get("loaded_ammo_name", "")

        line = f"  {name}"
        parts = []
        if damage is not None:
            parts.append(f"dmg:{damage}")
        if cooldown is not None and cooldown > 0:
            parts.append(f"CD:{cooldown}t")
        if current_ammo is not None and magazine_size:
            parts.append(f"ammo:{current_ammo}/{magazine_size}")
            if ammo_name:
                parts.append(f"({ammo_name})")
        elif current_ammo is not None:
            parts.append(f"ammo:{current_ammo}")
        if parts:
            line += "  " + " ".join(parts)
        lines.append(line)
    return lines


def _safe_post(api, endpoint, body=None):
    """Call an API endpoint, returning None on error instead of raising."""
    try:
        return api._post(endpoint, body) if body else api._post(endpoint)
    except Exception:
        return None


def cmd_status(api, args):
    as_json = getattr(args, "json", False)
    show_nearby = getattr(args, "nearby", False)
    resp = api._post("get_status")

    r = resp.get("result", {})
    p = r.get("player", {})
    s = r.get("ship", {})

    # Determine context from status
    poi_name = p.get("current_poi", "")
    base_id = p.get("docked_at_base", "")
    disruption = s.get("disruption_ticks_remaining")

    # Detect combat: check for active battle
    # Suppress notifications on secondary calls
    orig_print = api._print_notifications
    api._print_notifications = lambda resp: None
    try:
        battle_resp = _safe_post(api, "get_battle_status")
    finally:
        api._print_notifications = orig_print

    battle_r = (battle_resp or {}).get("result", {})
    in_combat = battle_r.get("is_participant", False)

    # Context-dependent secondary calls
    api._print_notifications = lambda resp: None
    try:
        # Always fetch POI if at one
        poi_resp = _safe_post(api, "get_poi") if poi_name else None

        if in_combat:
            # Combat: nearby is useful (who else is here), wrecks less so
            nearby_resp = _safe_post(api, "get_nearby") if show_nearby else None
            wrecks_resp = None
        elif base_id:
            # Docked: no need for nearby/wrecks at a station
            nearby_resp = None
            wrecks_resp = None
        elif poi_name:
            # In space at a POI: full situational awareness
            nearby_resp = _safe_post(api, "get_nearby") if show_nearby else None
            wrecks_resp = _safe_post(api, "get_wrecks") if show_nearby else None
        else:
            # In transit (no POI): nothing to fetch
            nearby_resp = None
            wrecks_resp = None
    finally:
        api._print_notifications = orig_print

    if as_json:
        combined = {"status": resp}
        if battle_resp and in_combat:
            combined["battle"] = battle_resp
        if poi_resp:
            combined["poi"] = poi_resp
        if nearby_resp:
            combined["nearby"] = nearby_resp
        if wrecks_resp:
            combined["wrecks"] = wrecks_resp
        print(json.dumps(combined, indent=2))
        return

    sys_name = p.get("current_system", "?")

    location = sys_name
    if poi_name:
        location += f" / {poi_name}"
    if base_id:
        location += " [docked]"
    elif poi_resp:
        poi_data = poi_resp.get("result", {})
        poi_base = poi_data.get("base") or poi_data.get("poi", {}).get("base") or poi_data.get("poi", {}).get("base_id")
        if poi_base:
            location += " [undocked]"

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
    print(f"Cargo: {s.get('cargo_used', '?')}/{s.get('cargo_capacity', '?')} space")

    # Situational flags
    flags = []
    if in_combat:
        flags.append("IN COMBAT")
    if p.get("is_cloaked"):
        flags.append("CLOAKED")
    if p.get("towing_wreck_id"):
        flags.append(f"TOWING:{p['towing_wreck_id']}")
    if p.get("anonymous"):
        flags.append("ANONYMOUS")
    if disruption:
        flags.append(f"DISRUPTED:{disruption}t")
    if flags:
        print(f"Flags: [{'] ['.join(flags)}]")

    # ── Combat section ──
    if in_combat:
        # Modules with combat detail (cooldowns, ammo)
        modules = r.get("modules", [])
        if modules:
            print(f"\n\u2500\u2500 Weapons/Modules \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
            for line in _fmt_modules_combat(modules):
                print(line)

        # Active buffs
        buffs = s.get("active_buffs", [])
        if buffs:
            buff_names = []
            for b in buffs:
                if isinstance(b, dict):
                    buff_names.append(b.get("name") or b.get("id", "?"))
                else:
                    buff_names.append(str(b))
            print(f"  Buffs: {', '.join(buff_names)}")

        # Speed/damage penalties
        speed_pen = s.get("speed_penalty")
        dmg_pen = s.get("damage_penalty")
        penalties = []
        if speed_pen and speed_pen != 1:
            penalties.append(f"speed:{speed_pen}x")
        if dmg_pen and dmg_pen != 1:
            penalties.append(f"damage:{dmg_pen}x")
        if penalties:
            print(f"  Penalties: {' '.join(penalties)}")

        # Battle state
        battle_lines = _fmt_battle(battle_r)
        if battle_lines:
            print(f"\n\u2500\u2500 Battle \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
            for line in battle_lines:
                print(line)

        # Nearby (who else is at this location, not yet in the fight?)
        if nearby_resp:
            nearby_r = nearby_resp.get("result", {})
            nearby_players = nearby_r.get("nearby", [])
            nearby_pirates = nearby_r.get("pirates", [])
            if nearby_players or nearby_pirates:
                poi_r = (poi_resp or {}).get("result", {})
                print(f"\n\u2500\u2500 Nearby \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
                for line in _fmt_nearby_summary(nearby_r, poi_r):
                    print(line)
    else:
        # Non-combat: simple modules summary
        modules = r.get("modules", [])
        if modules:
            mod_names = []
            for m in modules:
                if isinstance(m, dict):
                    mod_names.append(m.get("name") or m.get("module_id") or m.get("type", "?"))
                else:
                    mod_names.append(str(m))
            print(f"Modules: {', '.join(mod_names)}")

    # ── POI (non-combat) ──
    if not in_combat and poi_resp:
        poi_r = poi_resp.get("result", {})
        poi_lines = _fmt_poi(poi_r)
        if poi_lines:
            print(f"\n\u2500\u2500 POI \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
            for line in poi_lines:
                print(line)

    # ── Nearby (non-combat, in space) ──
    if not in_combat and nearby_resp:
        nearby_r = nearby_resp.get("result", {})
        nearby_players = nearby_r.get("nearby", [])
        nearby_pirates = nearby_r.get("pirates", [])
        if nearby_players or nearby_pirates:
            poi_r = (poi_resp or {}).get("result", {})
            print(f"\n\u2500\u2500 Nearby \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
            for line in _fmt_nearby_summary(nearby_r, poi_r):
                print(line)

    # ── Wrecks (in space, non-combat) ──
    if wrecks_resp:
        wrecks_r = wrecks_resp.get("result", {})
        wreck_lines = _fmt_wrecks(wrecks_r)
        if wreck_lines:
            print(f"\n\u2500\u2500 Wrecks \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
            for line in wreck_lines:
                print(line)

    # ── Docked context ──
    if base_id and not in_combat:
        print(f"\n  Hint: sm base  |  sm listings  |  sm missions  |  sm storage  |  sm status --nearby")


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
    print(f"Cargo: {r.get('cargo_used', s.get('cargo_used', '?'))}/{r.get('cargo_max', s.get('cargo_capacity', '?'))} space")
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
        print(f"\nCargo ({s.get('cargo_used', '?')}/{s.get('cargo_capacity', '?')} space):")
        for item in cargo:
            if isinstance(item, dict):
                name = item.get("name") or item.get("item_id", "?")
                qty = item.get("quantity", 1)
                size = item.get("size")
                if size is not None:
                    total_size = size * qty
                    size_str = f"  ({total_size} space)" if qty == 1 or size == 1 else f"  ({size}x{qty} = {total_size} space)"
                else:
                    size_str = ""
                print(f"  {name} x{qty}{size_str}")
            else:
                print(f"  {item}")



def cmd_pois(api, args):
    system_id = getattr(args, "system", None)
    body = {"system_id": system_id} if system_id else {}
    resp = api._post("get_system", body)
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
    for line in _fmt_poi(r):
        print(line)

    # Extra detail not in the compact formatter: position, full base info
    p = r.get("poi", r)
    pos = p.get("position")
    if pos:
        print(f"  Position: ({pos.get('x', '?')}, {pos.get('y', '?')})")

    base = r.get("base") or p.get("base") or p.get("base_id")
    if base and isinstance(base, dict):
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

    print("\n  Note: This info is now included in 'sm status --nearby'")


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
    import json as _json
    resp = api._post("get_cargo")
    as_json = getattr(args, "json", False)
    if as_json:
        print(_json.dumps(resp, indent=2))
        return
    r = resp.get("result", {})
    items = r.get("cargo", [])
    used = r.get("used", 0)
    capacity = r.get("capacity", "?")
    print(f"{used}/{capacity} used")
    if not items:
        print("No cargo items.")
    else:
        for item in items:
            name = item.get("name") or item.get("item_id", "?")
            item_id = item.get("item_id", "?")
            qty = item.get("quantity", 1)
            size = item.get("size", 1)
            weight = qty * size
            if size > 1:
                print(f"  {name} [{item_id}] x{qty}  ({weight} cargo, {size}/unit)")
            else:
                print(f"  {name} [{item_id}] x{qty}")
    print("\n  Hint: sm market sell <item> <qty> <price>  |  sm listings  |  sm storage deposit <item> <qty>")


def _threat_level(nearby_info):
    """Estimate threat from nearby data.

    Returns (level, reasons) where level is 0-20 and reasons is a list of strings.
    Thresholds: 0 safe, 1-5 low, 6-10 medium, 11-15 high, 16+ deadly.

    Works for both player entries (ship_class, in_combat) and pirate entries
    (tier, is_boss, hull/shield stats).
    """
    level = 0
    reasons = []

    # --- Pirate-specific fields ---
    tier = nearby_info.get("tier", "")
    is_boss = nearby_info.get("is_boss", False)

    if tier or is_boss:
        # This is a pirate entry — use tier/boss/stats instead of ship_class
        tier_lower = tier.lower() if tier else ""
        if tier_lower in ("elite", "deadly"):
            level += 10
            reasons.append(f"elite pirate (tier:{tier})")
        elif tier_lower in ("hard", "dangerous"):
            level += 7
            reasons.append(f"dangerous pirate (tier:{tier})")
        elif tier_lower in ("medium", "moderate"):
            level += 4
            reasons.append(f"moderate pirate (tier:{tier})")
        elif tier_lower in ("easy", "weak", "low"):
            level += 2
            reasons.append(f"weak pirate (tier:{tier})")
        elif tier:
            level += 5
            reasons.append(f"pirate (tier:{tier})")
        else:
            level += 5
            reasons.append("pirate")

        if is_boss:
            level += 5
            reasons.append("BOSS")

        # Use direct hull/shield stats if available
        hull = nearby_info.get("max_hull") or nearby_info.get("hull", 0)
        shield = nearby_info.get("max_shield") or nearby_info.get("shield", 0)
        if hull and hull > 200:
            level += 3
            reasons.append(f"heavy hull ({hull})")
        if shield and shield > 100:
            level += 3
            reasons.append(f"strong shields ({shield})")

        status = (nearby_info.get("status") or "").lower()
        if status == "aggressive" or status == "attacking":
            level += 2
            reasons.append(f"status:{status}")

        return level, reasons

    # --- Player entry ---
    ship = (nearby_info.get("ship_class") or "").lower()
    in_combat = nearby_info.get("in_combat", False)

    # Ship class analysis (IDs like fighter_scout, freighter_small)
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


def cmd_nearby(api, args):
    """Redirects to sm status --nearby."""
    print("Use 'sm status --nearby' for nearby info.")
    args.nearby = True
    cmd_status(api, args)



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
    wreck_lines = _fmt_wrecks(r)
    if not wreck_lines:
        print("No wrecks at this location.")
        return

    print(f"Wrecks ({len(r.get('wrecks', []))}):")
    for line in wreck_lines:
        print(line)

    # Show owner info not in the compact formatter
    for w in r.get("wrecks", []):
        owner = w.get("owner_id", "")
        if owner:
            wid = w.get("wreck_id") or w.get("id", "?")
            print(f"    {wid} owner: {owner}")

    print("\n  Hint: sm loot-wreck <wreck_id> <item_id> <qty>  |  sm salvage-wreck <wreck_id>")
    print("        sm tow-wreck <wreck_id>  |  sm sell-wreck  |  sm scrap-wreck")
    print("  Note: This info is now included in 'sm status --nearby'")


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

        print(f"\n  Hint: sm market buy {item_id} <qty> <price>  |  sm market sell {item_id} <qty> <price>")


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


def cmd_skills(api, args):
    as_json = getattr(args, "json", False)
    resp = api._post("get_skills")
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    r = resp.get("result", {})
    skills = r.get("skills", {})
    if not skills:
        print("No skills trained yet.")
        return
    print("Your Skills:\n")
    for skill_id, data in sorted(skills.items()):
        level = data.get("level", 0)
        xp = data.get("xp", 0)
        next_xp = data.get("next_level_xp", 0)
        name = skill_id.replace("_", " ").title()
        if next_xp == 0:
            bar = "██████████"
            progress = "maxed"
        else:
            pct = min(xp / next_xp, 1.0)
            filled = int(pct * 10)
            bar = "█" * filled + "░" * (10 - filled)
            progress = f"{xp:,}/{next_xp:,} XP"
        print(f"  {name:<28} L{level:<3} {bar}  {progress}")
    print(f"\n  {len(skills)} skills tracked.")
    print("  Hint: sm catalog skills --search <query>  (browse all skill definitions)")
