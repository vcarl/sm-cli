import json


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


def cmd_nearby(api, args):
    resp = api._post("get_nearby")
    r = resp.get("result", {})
    players = r.get("nearby") or r.get("players", [])
    if not players:
        print("No one nearby.")
    else:
        for p in players:
            name = p.get("username") or p.get("name") or "anonymous"
            pid = p.get("id") or p.get("player_id", "")
            line = name
            if pid:
                line += f" (id:{pid})"
            if p.get("ship_class"):
                line += f" [{p['ship_class']}]"
            if p.get("clan_tag"):
                line += f" <{p['clan_tag']}>"
            print(line)


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
