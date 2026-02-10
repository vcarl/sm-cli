import json
import time


def cmd_login(api, args):
    cred_file = args.cred_file if args.cred_file else None
    as_json = getattr(args, "json", False)
    resp = api.login(cred_file)
    if not resp:
        return
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    r = resp.get("result", {})
    _print_login_summary(r)


def _print_login_summary(r):
    """Print a compact status summary from the login response."""
    player = r.get("player", {})
    ship = r.get("ship", {})
    system = r.get("system", {})
    poi = r.get("poi", {})
    unread = r.get("unread_chat", {})
    release = r.get("release_info", {})
    log_entries = r.get("captains_log", [])
    trades = r.get("pending_trades")

    # Location
    sys_name = system.get("name") or player.get("current_system", "?")
    poi_name = poi.get("name") or player.get("current_poi", "?")
    police = system.get("police_level")
    loc_line = f"{sys_name} > {poi_name}"
    if player.get("docked_at_base"):
        loc_line += " (docked)"
    if police is not None:
        loc_line += f"  [police: {police}]"
    print(loc_line)

    # Credits & empire
    print(f"{player.get('credits', '?')} cr  |  {player.get('empire', '?')} empire")

    # Ship
    ship_name = ship.get("name") or ship.get("class_id", "?")
    parts = [
        ship_name,
        f"Hull: {ship.get('hull', '?')}/{ship.get('max_hull', '?')}",
        f"Shield: {ship.get('shield', '?')}/{ship.get('max_shield', '?')}",
        f"Fuel: {ship.get('fuel', '?')}/{ship.get('max_fuel', '?')}",
        f"Cargo: {ship.get('cargo_used', '?')}/{ship.get('cargo_capacity', '?')}",
    ]
    print("  ".join(parts))

    # Unread chat
    if unread:
        counts = [f"{ch}:{ct}" for ch, ct in unread.items() if ct]
        if counts:
            print(f"Unread: {' '.join(counts)}")

    # Pending trades
    if trades:
        print(f"Pending trades: {len(trades)}")

    # Captain's log (most recent)
    if log_entries:
        latest = log_entries[0]
        text = latest.get("entry", "")
        first_line = text.split("\n", 1)[0]
        if len(first_line) > 100:
            first_line = first_line[:97] + "..."
        ts = latest.get("created_at", "")[:10]
        print(f"Last log ({ts}): {first_line}")

    # Release info
    if release:
        ver = release.get("version", "?")
        notes = release.get("notes", [])
        note_str = notes[0] if notes else ""
        if len(note_str) > 80:
            note_str = note_str[:77] + "..."
        print(f"v{ver}: {note_str}")


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


def cmd_jump(api, args):
    as_json = getattr(args, "json", False)
    resp = api._post("jump", {"target_system": args.target_system})
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    if resp.get("error"):
        err = resp["error"]
        print(f"ERROR: {err.get('message', err) if isinstance(err, dict) else err}")
    else:
        r = resp.get("result", {})
        dest = r.get("destination") or r.get("system_name") or r.get("target_system", "?")
        fuel = r.get("fuel_cost") or r.get("fuel_used")
        eta = r.get("ticks") or r.get("eta") or r.get("jump_time", "?")
        line = f"Jumping to {dest}... ETA: {eta} ticks"
        if fuel is not None:
            line += f" (fuel: {fuel})"
        print(line)


def cmd_dock(api, args):
    resp = api._post("dock")
    if resp.get("error"):
        print(f"ERROR: {resp['error']}")
    else:
        r = resp.get("result", {})
        base_id = r.get("base_id") or r.get("base", {}).get("id", "")
        base_name = r.get("base_name") or r.get("base", {}).get("name", "")
        msg = "Docked"
        if base_name:
            msg += f" at {base_name}"
        if base_id:
            msg += f" ({base_id})"
        print(f"{msg}.")


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


def cmd_sell(api, args):
    result = api._post("sell", {"item_id": args.item_id, "quantity": args.quantity})
    err = result.get("error")
    if err:
        print(f"ERROR: {err}")
    else:
        r = result.get("result", {})
        earned = _extract_earned(r)
        if earned is not None:
            print(f"Sold {args.item_id} x{args.quantity} (+{earned} cr)")
        else:
            print(f"Sold {args.item_id} x{args.quantity}")


def _extract_earned(result_dict):
    """Extract credits earned from a sell response, returning int or None."""
    for key in ("credits_earned", "earned", "total_price", "price", "amount"):
        val = result_dict.get(key)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                pass
    return None


def cmd_sell_all(api, args):
    cargo_resp = api._post("get_cargo")
    items = cargo_resp.get("result", {}).get("cargo", [])
    items = [i for i in items if i.get("quantity", 0) > 0]

    if not items:
        print("Nothing to sell (cargo empty or unreadable).")
        return

    total = 0
    sold_count = 0
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
                earned = _extract_earned(r)
                sold_count += 1
                if earned is not None:
                    print(f"  {item_id} x{qty}: sold (+{earned} cr)")
                    total += earned
                else:
                    print(f"  {item_id} x{qty}: sold")
        except Exception as e:
            print(f"  {item_id} x{qty}: FAILED ({e})")
        if item is not items[-1]:
            time.sleep(11)

    if total > 0:
        print(f"Done. Total earned: {total} cr")
    else:
        print(f"Done. Sold {sold_count} item(s).")


def cmd_buy(api, args):
    as_json = getattr(args, "json", False)
    body = {"item_id": args.item_id, "quantity": args.quantity}
    resp = api._post("buy", body)
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    if resp.get("error"):
        err = resp["error"]
        print(f"ERROR: {err.get('message', err) if isinstance(err, dict) else err}")
    else:
        r = resp.get("result", {})
        cost = r.get("total_cost") or r.get("credits_spent") or r.get("cost", "?")
        print(f"Bought {args.item_id} x{args.quantity} (-{cost} cr)")


def cmd_chat(api, args):
    first = getattr(args, "target_or_message", "")
    second = getattr(args, "message", None)
    if args.channel == "private":
        if not second:
            print("ERROR: private messages require a target player ID: sm chat private <player_id> \"msg\"")
            return
        target = first
        message = second
    else:
        # Non-private: first arg is the message, second is ignored
        message = first
    body = {"channel": args.channel, "content": message}
    if args.channel == "private":
        body["target_id"] = target
    resp = api._post("chat", body)
    if resp.get("error"):
        print(f"ERROR: {resp['error']}")
    else:
        r = resp.get("result", {})
        # Result may use capitalized keys (Notification.Channel)
        notif = r.get("Notification", r)
        channel = notif.get("Channel") or notif.get("channel") or args.channel
        print(f"Sent to {channel}.")


def cmd_wait(api, args):
    """Block until the player is no longer in transit or performing an action."""
    timeout = getattr(args, "timeout", 60)
    elapsed = 0
    interval = 3
    while elapsed < timeout:
        resp = api._post("get_status")
        r = resp.get("result", {})
        p = r.get("player", {})
        s = r.get("ship", {})
        # Check common transit/action indicators
        in_transit = (
            p.get("in_transit", False)
            or p.get("is_traveling", False)
            or s.get("in_transit", False)
            or p.get("current_action") not in (None, "", "idle")
        )
        if not in_transit:
            print("Ready.")
            return
        action = p.get("current_action") or "in transit"
        eta = p.get("eta") or p.get("ticks_remaining") or s.get("eta")
        msg = f"Waiting... ({action}"
        if eta:
            msg += f", ETA: {eta} ticks"
        msg += ")"
        print(msg, flush=True)
        time.sleep(interval)
        elapsed += interval
    print(f"Timed out after {timeout}s.")


def cmd_log(api, args):
    resp = api._post("captains_log_list")
    entries = resp.get("result", {}).get("entries", [])
    entries = entries[:5]
    brief = getattr(args, "brief", False)
    for i, e in enumerate(entries):
        text = e.get("entry") or str(e)
        if brief:
            first_line = text.split("\n", 1)[0]
            if len(first_line) > 120:
                first_line = first_line[:117] + "..."
            print(f"#{i}: {first_line}")
        else:
            if i > 0:
                print("---")
            print(f"#{i}: {text}")


def cmd_log_add(api, args):
    resp = api._post("captains_log_add", {"entry": args.text})
    if resp.get("error"):
        print(f"ERROR: {resp['error']}")
    else:
        print("Log entry added.")
