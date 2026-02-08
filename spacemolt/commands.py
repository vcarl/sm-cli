import json
import time


def cmd_login(api, args):
    cred_file = args.cred_file if args.cred_file else None
    api.login(cred_file)


def cmd_status(api, args):
    resp = api._post("get_status")
    r = resp.get("result", {})
    p = r.get("player", {})
    s = r.get("ship", {})

    location = p.get("current_system", "?")
    if p.get("current_poi"):
        location += f" / {p['current_poi']}"
    if p.get("docked_at_base"):
        location += " (docked)"

    print(f"Credits: {p.get('credits', '?')}")
    print(f"Location: {location}")
    print(f"Ship: {s.get('class_id') or s.get('name', '?')}")
    print(f"Hull: {s.get('hull', '?')}/{s.get('max_hull', '?')} | Fuel: {s.get('fuel', '?')}/{s.get('max_fuel', '?')}")
    print(f"Cargo: {s.get('cargo_used', '?')}/{s.get('cargo_capacity', '?')}")


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
        if p.get("base_id"):
            line += " *base*"
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


def cmd_log(api, args):
    resp = api._post("captains_log_list")
    entries = resp.get("result", {}).get("entries", [])
    entries = entries[:5]
    for i, e in enumerate(entries):
        if i > 0:
            print("---")
        text = e.get("entry") or str(e)
        print(f"#{i}: {text}")


def cmd_log_add(api, args):
    resp = api._post("captains_log_add", {"entry": args.text})
    if resp.get("error"):
        print(f"ERROR: {resp['error']}")
    else:
        print("Log entry added.")


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


def cmd_sell_all(api, args):
    cargo_resp = api._post("get_cargo")
    items = cargo_resp.get("result", {}).get("cargo", [])
    items = [i for i in items if i.get("quantity", 0) > 0]

    if not items:
        print("Nothing to sell (cargo empty or unreadable).")
        return

    total = 0
    for item in items:
        item_id = item.get("item_id") or item.get("name") or item.get("id")
        qty = item.get("quantity", 1)
        try:
            result = api._post("sell", {"item_id": item_id, "quantity": qty})
            err = result.get("error")
            if err:
                print(f"  {item_id} x{qty}: FAILED ({err})")
            else:
                r = result.get("result", {})
                earned = r.get("credits_earned") or r.get("earned", "?")
                print(f"  {item_id} x{qty}: sold (+{earned} cr)")
                if earned != "?":
                    try:
                        total += int(earned)
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            print(f"  {item_id} x{qty}: FAILED ({e})")
        time.sleep(11)

    print(f"Done. Total earned: {total} cr")


def cmd_skills(api, args):
    resp = api._post("get_skills")
    skills = resp.get("result", {}).get("player_skills", [])
    skills.sort(key=lambda s: (-s.get("level", 0), -s.get("current_xp", 0)))
    if not skills:
        print("(no skills trained yet)")
    else:
        for s in skills:
            name = s.get("name", "?")
            level = s.get("level", 0)
            xp = s.get("current_xp", 0)
            next_xp = s.get("next_level_xp", "?")
            print(f"{name}: L{level} ({xp}/{next_xp} XP)")


def cmd_nearby(api, args):
    resp = api._post("get_nearby")
    r = resp.get("result", {})
    players = r.get("nearby") or r.get("players", [])
    if not players:
        print("No one nearby.")
    else:
        for p in players:
            name = p.get("username") or p.get("name") or "anonymous"
            line = name
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


def cmd_travel(api, args):
    resp = api._post("travel", {"target_poi": args.poi_id})
    if resp.get("error"):
        print(f"ERROR: {resp['error']}")
    else:
        r = resp.get("result", {})
        dest = r.get("destination") or r.get("poi_name", "destination")
        eta = r.get("ticks") or r.get("eta") or r.get("travel_time", "?")
        fuel = r.get("fuel_cost")
        line = f"Traveling to {dest}... ETA: {eta} ticks"
        if fuel is not None:
            line += f" (fuel: {fuel})"
        print(line)


def cmd_dock(api, args):
    resp = api._post("dock")
    if resp.get("error"):
        print(f"ERROR: {resp['error']}")
    else:
        print("Docked.")


def cmd_undock(api, args):
    resp = api._post("undock")
    if resp.get("error"):
        print(f"ERROR: {resp['error']}")
    else:
        print("Undocked.")


def cmd_mine(api, args):
    resp = api._post("mine")
    if resp.get("error"):
        print(f"ERROR: {resp['error']}")
        return
    r = resp.get("result", {})
    msg = r.get("message")
    if msg:
        print(msg)


def cmd_refuel(api, args):
    resp = api._post("refuel")
    if resp.get("error"):
        print(f"ERROR: {resp['error']}")
    else:
        r = resp.get("result", {})
        print(f"Refueled. Fuel: {r.get('fuel', '?')}/{r.get('max_fuel', '?')}")


def cmd_repair(api, args):
    resp = api._post("repair")
    if resp.get("error"):
        print(f"ERROR: {resp['error']}")
    else:
        r = resp.get("result", {})
        print(f"Repaired. Hull: {r.get('hull', '?')}/{r.get('max_hull', '?')}")


def cmd_chat(api, args):
    resp = api._post("chat", {"channel": args.channel, "content": args.message})
    if resp.get("error"):
        print(f"ERROR: {resp['error']}")
    else:
        r = resp.get("result", {})
        # Result may use capitalized keys (Notification.Channel)
        notif = r.get("Notification", r)
        channel = notif.get("Channel") or notif.get("channel") or args.channel
        print(f"Sent to {channel}.")


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
