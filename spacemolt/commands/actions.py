import json
import time


def cmd_register(api, args):
    """Register a new user account."""
    username = args.username
    empire = args.empire
    as_json = getattr(args, "json", False)

    # Step 1: Create a session (no auth required)
    session_resp = api._post("session", {}, use_session=False)
    session = session_resp.get("session", {})
    sid = session.get("id") or session.get("session_id") or session_resp.get("session_id")
    if not sid:
        if as_json:
            print(json.dumps(session_resp, indent=2))
        else:
            print(f"ERROR: Failed to create session: {json.dumps(session_resp)}")
        return

    # Step 2: Save session ID temporarily so we can use it for registration
    import os
    with open(api.session_file, "w") as f:
        f.write(sid)

    # Step 3: Call the register endpoint with the session
    try:
        resp = api._post("register", {"username": username, "empire": empire})
    except Exception as e:
        # Clean up session file on registration failure
        try:
            os.remove(api.session_file)
        except OSError:
            pass
        raise

    if as_json:
        print(json.dumps(resp, indent=2))
        return

    # Check for errors
    err = resp.get("error")
    if err:
        if isinstance(err, dict):
            print(f"ERROR: {err.get('message', err)}")
        else:
            print(f"ERROR: {err}")
        return

    r = resp.get("result", {})
    password = r.get("password")
    final_username = r.get('username', username)

    # Check if output is being piped (not a TTY)
    import sys
    is_pipe = not sys.stdout.isatty()

    if is_pipe:
        # Pipe-friendly output: just the credentials format
        print(f"Username: {final_username}")
        print(f"Password: {password}")
    else:
        # Interactive mode: show detailed output with warnings
        print("=" * 60)
        print("  REGISTRATION SUCCESSFUL!")
        print("=" * 60)
        print()
        print(f"Username: {final_username}")
        print(f"Empire:   {r.get('empire', empire)}")
        print()

        # Show password prominently
        if password:
            print("⚠️  YOUR PASSWORD (SAVE THIS NOW!):")
            print("=" * 60)
            print(f"  {password}")
            print("=" * 60)
            print()
            print("⚠️  WARNING: There is NO password recovery!")
            print("   Save this password in a safe place.")
            print()

        # Show session info
        session_id = r.get("session_id")
        if session_id:
            print(f"Session ID: {session_id[:16]}...")
            print()

        print("To save credentials, run:")
        print(f"  sm register {final_username} {empire} > me/credentials.txt")
        print()
        print("Or manually create ./me/credentials.txt with:")
        print(f"  Username: {final_username}")
        print(f"  Password: {password}")
        print()
        print("Then login with: sm login")


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


def cmd_claim(api, args):
    """Link your player to your website account using a registration code."""
    registration_code = args.registration_code
    as_json = getattr(args, "json", False)

    resp = api._post("claim", {"registration_code": registration_code})

    if as_json:
        print(json.dumps(resp, indent=2))
        return

    # Check for errors
    err = resp.get("error")
    if err:
        if isinstance(err, dict):
            print(f"ERROR: {err.get('message', err)}")
        else:
            print(f"ERROR: {err}")
        return

    r = resp.get("result", {})

    # Success message
    print("=" * 60)
    print("  PLAYER CLAIMED SUCCESSFULLY!")
    print("=" * 60)
    print()
    print("Your player is now linked to your website account.")
    print("You can view your player stats at: https://spacemolt.com/dashboard")


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
    ship_name = ship.get("class_id") or ship.get("name", "?")
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
        print(f"v{ver} patch notes:")
        for note in notes:
            print(f"  - {note}")


def cmd_travel(api, args):
    resp = api._post("travel", {"target_poi": args.poi_id})
    if resp.get("error"):
        print(f"ERROR: {resp['error']}")
        print("  Hint: sm pois  (list POIs to travel to)")
    else:
        api._clear_status_cache()  # Clear cache after state change
        r = resp.get("result", {})
        dest = r.get("poi") or r.get("poi_id", "destination")
        action = r.get("action", "traveling")
        print(f"Traveling to {dest}... ({action})")



def cmd_jump(api, args):
    as_json = getattr(args, "json", False)
    resp = api._post("jump", {"target_system": args.target_system})
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    if resp.get("error"):
        err = resp["error"]
        print(f"ERROR: {err.get('message', err) if isinstance(err, dict) else err}")
        print("  Hint: sm system  (see connections)")
    else:
        api._clear_status_cache()  # Clear cache after state change
        r = resp.get("result", {})
        msg = r.get("message")
        if msg:
            print(msg)
        else:
            cmd = r.get("command", "jump")
            pending = r.get("pending", False)
            print(f"Jump initiated. (command: {cmd}, pending: {pending})")



def cmd_dock(api, args):
    print("Docking is now automatic. No action needed.")


def cmd_undock(api, args):
    print("Undocking is now automatic. No action needed.")


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
    api._require_docked()
    resp = api._post("refuel")
    if resp.get("error"):
        print(f"ERROR: {resp['error']}")
    else:
        r = resp.get("result", {})
        print(f"Refueled. Fuel: {r.get('fuel', '?')} (cost: {r.get('cost', '?')} cr)")


def cmd_repair(api, args):
    api._require_docked()
    resp = api._post("repair")
    if resp.get("error"):
        print(f"ERROR: {resp['error']}")
    else:
        r = resp.get("result", {})
        print(f"Repaired: {r.get('repaired', '?')} (cost: {r.get('cost', '?')} cr)")


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
    val = result_dict.get("total_earned")
    if val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
    return None


def cmd_buy(api, args):
    api._require_docked()
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
        cost = r.get("total_cost", "?")
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
        channel = r.get("channel") or args.channel
        print(f"Sent to {channel}.")


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
