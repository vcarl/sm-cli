import json
import time


# Mapping of endpoint names to their expected positional arg specs.
# Use "name:int" or "name:bool" for typed args; default is string.
ENDPOINT_ARGS = {
    "jump": ["target_system"],
    "buy": ["item_id", "quantity:int"],
    "scan": ["target_id"],
    "attack": ["target_id"],
    "travel": ["target_poi"],
    "chat": ["channel", "content", "target_id"],
    "craft": ["recipe_id"],
    "forum_reply": ["thread_id", "content"],
    "forum_get_thread": ["thread_id"],
    "forum_create_thread": ["title", "content"],
    "sell": ["item_id", "quantity:int"],
    "loot_wreck": ["wreck_id", "item_id", "quantity:int"],
    "salvage_wreck": ["wreck_id"],
    "install_mod": ["module_id"],
    "uninstall_mod": ["module_id"],
    "buy_ship": ["ship_class"],
    "find_route": ["target_system"],
    "search_systems": ["query"],
    "captains_log_add": ["entry"],
    "captains_log_get": ["index:int"],
    "set_anonymous": ["anonymous:bool"],
    "list_item": ["item_id", "quantity:int", "price_each:int"],
    "buy_listing": ["listing_id"],
    "cancel_list": ["listing_id"],
    "faction_invite": ["player_id"],
    "faction_kick": ["player_id"],
    "faction_promote": ["player_id", "role_id"],
    "faction_declare_war": ["target_faction_id", "reason"],
    "faction_propose_peace": ["target_faction_id", "terms"],
    "faction_accept_peace": ["target_faction_id"],
    "faction_set_ally": ["target_faction_id"],
    "faction_set_enemy": ["target_faction_id"],
    "faction_info": ["faction_id"],
    "join_faction": ["faction_id"],
    "faction_decline_invite": ["faction_id"],
    "create_faction": ["name", "tag"],
    "set_home_base": ["base_id"],
    "set_colors": ["primary_color", "secondary_color"],
    "set_status": ["status_message", "clan_tag"],
    "trade_offer": ["target_id"],
    "trade_accept": ["trade_id"],
    "trade_decline": ["trade_id"],
    "trade_cancel": ["trade_id"],
    "buy_insurance": ["ticks:int"],
    "forum_upvote": ["thread_id", "reply_id"],
    "forum_delete_thread": ["thread_id"],
    "forum_delete_reply": ["reply_id"],
    "forum_list": ["page:int"],
}


def _parse_typed_value(spec, value):
    """Convert a string value according to its type spec (e.g. 'quantity:int')."""
    if ":" in spec:
        _, type_name = spec.rsplit(":", 1)
    else:
        type_name = "str"

    if type_name == "int":
        return int(value)
    elif type_name == "bool":
        return value.lower() in ("true", "1", "yes")
    return value


def _arg_name(spec):
    """Extract the parameter name from a spec like 'quantity:int'."""
    return spec.split(":")[0]


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
            body[key] = _parse_typed_value(matching_spec, val)
        else:
            positional.append(arg)

    # Map positional args to parameter names
    for i, val in enumerate(positional):
        if i < len(specs):
            spec = specs[i]
            body[_arg_name(spec)] = _parse_typed_value(spec, val)
        else:
            # Extra positional with no spec — skip with warning
            print(f"Warning: extra argument ignored: {val}")

    resp = api._post(endpoint, body)
    if as_json:
        print(json.dumps(resp, indent=2))
    else:
        err = resp.get("error")
        if err:
            if isinstance(err, dict):
                print(f"ERROR: {err.get('message', err)}")
            else:
                print(f"ERROR: {err}")
        else:
            result = resp.get("result", resp)
            print(json.dumps(result, indent=2))


def cmd_commands(api, args):
    """List all available API endpoints grouped by category."""
    as_json = getattr(args, "json", False)
    resp = api._post("get_commands")
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    commands = resp.get("result", {}).get("commands", [])
    if not commands:
        # Fallback: dump raw
        print(json.dumps(resp.get("result", resp), indent=2))
        return

    # Group by category
    by_cat = {}
    for cmd in commands:
        cat = cmd.get("category", "other")
        by_cat.setdefault(cat, []).append(cmd)

    for cat in sorted(by_cat):
        print(f"\n{cat.upper()}")
        for cmd in sorted(by_cat[cat], key=lambda c: c.get("name", "")):
            name = cmd.get("name", "?")
            desc = cmd.get("description", "")
            if len(desc) > 70:
                desc = desc[:67] + "..."
            print(f"  {name:30s} {desc}")


def cmd_login(api, args):
    cred_file = args.cred_file if args.cred_file else None
    api.login(cred_file)


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


def cmd_sell(api, args):
    result = api._post("sell", {"item_id": args.item_id, "quantity": args.quantity})
    err = result.get("error")
    if err:
        print(f"ERROR: {err}")
    else:
        r = result.get("result", {})
        earned = r.get("credits_earned") or r.get("earned", "?")
        print(f"Sold {args.item_id} x{args.quantity} (+{earned} cr)")


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


def cmd_chat(api, args):
    body = {"channel": args.channel, "content": args.message}
    target = getattr(args, "target", None)
    if args.channel == "private":
        if not target:
            print("ERROR: private messages require a target player ID: sm chat private \"msg\" <player_id>")
            return
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


# --- Formatted handlers for commonly-used commands ---

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


def cmd_recipes(api, args):
    as_json = getattr(args, "json", False)
    resp = api._post("get_recipes")
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    r = resp.get("result", {})
    recipes = r.get("recipes", [])
    if not recipes:
        print("No recipes available.")
        return

    for rec in recipes:
        name = rec.get("name") or rec.get("recipe_id", "?")
        rid = rec.get("id") or rec.get("recipe_id", "")
        print(f"\n{name}" + (f" (id:{rid})" if rid and rid != name else ""))

        inputs = rec.get("inputs") or rec.get("materials", [])
        if inputs:
            parts = []
            for inp in inputs:
                if isinstance(inp, dict):
                    iname = inp.get("item_id") or inp.get("name", "?")
                    iqty = inp.get("quantity", 1)
                    parts.append(f"{iname} x{iqty}")
                else:
                    parts.append(str(inp))
            print(f"  Needs: {', '.join(parts)}")

        outputs = rec.get("outputs") or rec.get("output", [])
        if outputs:
            if isinstance(outputs, list):
                parts = []
                for out in outputs:
                    if isinstance(out, dict):
                        oname = out.get("item_id") or out.get("name", "?")
                        oqty = out.get("quantity", 1)
                        parts.append(f"{oname} x{oqty}")
                    else:
                        parts.append(str(out))
                print(f"  Makes: {', '.join(parts)}")
            elif isinstance(outputs, dict):
                oname = outputs.get("item_id") or outputs.get("name", "?")
                oqty = outputs.get("quantity", 1)
                print(f"  Makes: {oname} x{oqty}")

        reqs = rec.get("requirements") or rec.get("skills_required", [])
        if reqs:
            parts = []
            for req in reqs:
                if isinstance(req, dict):
                    sname = req.get("skill") or req.get("skill_id", "?")
                    slvl = req.get("level", "?")
                    parts.append(f"{sname} L{slvl}")
                else:
                    parts.append(str(req))
            print(f"  Requires: {', '.join(parts)}")


# --- Recipe query / progression diagram ---

def _normalize_recipes(raw_recipes):
    """Turn the API recipes response (dict-keyed or list) into a list."""
    if isinstance(raw_recipes, dict):
        return list(raw_recipes.values())
    return list(raw_recipes)


def _build_recipe_indexes(recipe_list):
    """Build lookup dicts: output_item→recipe, recipe_id→recipe."""
    by_output = {}  # item_id → recipe
    by_id = {}      # recipe_id → recipe
    for r in recipe_list:
        rid = r.get("id") or r.get("recipe_id", "")
        if rid:
            by_id[rid] = r
        for o in r.get("outputs", []):
            by_output[o.get("item_id", "")] = r
    return by_output, by_id


def _recipe_skill_tier(recipe):
    """Return a sortable (max_level, skill_string) tuple for ordering."""
    skills = recipe.get("required_skills", {})
    if not skills:
        return (0, "")
    max_lvl = max(skills.values())
    label = ", ".join(f"{s} {l}" for s, l in sorted(skills.items()))
    return (max_lvl, label)


def _recipe_one_line(recipe):
    """Format a recipe as: inputs → outputs (with quantities)."""
    inputs = recipe.get("inputs", [])
    outputs = recipe.get("outputs", [])
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
        # Raw material or cycle — leaf node
        return (depth, item_id, qty, None, [])
    seen = seen | {item_id}  # copy to allow sibling branches
    children = []
    for inp in recipe.get("inputs", []):
        inp_id = inp.get("item_id", "?")
        inp_qty = inp.get("quantity", 1) * qty
        children.append(
            _trace_ingredient_tree(inp_id, inp_qty, by_output, depth + 1, seen)
        )
    return (depth, item_id, qty, recipe, children)


def _render_tree(node, prefix="", is_last=True, lines=None):
    """Render a trace tree into lines with box-drawing connectors."""
    if lines is None:
        lines = []
    depth, item_id, qty, recipe, children = node

    connector = "└── " if is_last else "├── "
    if depth == 0:
        # Root node — no connector
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
        lines.append(f"{prefix}{connector}{label}")

    child_prefix = prefix + ("    " if is_last else "│   ")
    for i, child in enumerate(children):
        _render_tree(child, child_prefix, i == len(children) - 1, lines)
    return lines


def _collect_raw_totals(node, totals=None):
    """Walk tree and sum up raw material quantities at the leaves."""
    if totals is None:
        totals = {}
    _, item_id, qty, recipe, children = node
    if recipe is None:
        # Leaf = raw material
        totals[item_id] = totals.get(item_id, 0) + qty
    else:
        for child in children:
            _collect_raw_totals(child, totals)
    return totals


def cmd_query_recipes(api, args):
    """Show recipe progression, search, or trace full ingredient trees."""
    as_json = getattr(args, "json", False)
    resp = api._post("get_recipes")
    if as_json:
        print(json.dumps(resp, indent=2))
        return

    raw = resp.get("result", {}).get("recipes", resp.get("result", {}))
    recipe_list = _normalize_recipes(raw)
    if not recipe_list:
        print("No recipes available.")
        return

    by_output, by_id = _build_recipe_indexes(recipe_list)

    trace_target = getattr(args, "trace", None)
    search_query = getattr(args, "search", None)

    if trace_target:
        _do_trace(trace_target, by_output, recipe_list)
    elif search_query:
        _do_search(search_query, recipe_list)
    else:
        _do_progression(recipe_list, by_output)


def _do_progression(recipe_list, by_output):
    """Show recipes grouped by skill tier, with flow arrows."""
    from collections import defaultdict

    # Group by skill tier
    tiers = defaultdict(list)
    for r in recipe_list:
        _, label = _recipe_skill_tier(r)
        tier_key = label or "No requirements"
        tiers[tier_key].append(r)

    # Sort tiers by max level
    def tier_sort_key(item):
        key, recipes = item
        if key == "No requirements":
            return (0, "")
        return _recipe_skill_tier(recipes[0])

    for tier_key, recipes in sorted(tiers.items(), key=tier_sort_key):
        print(f"\n{'═' * 60}")
        print(f"  {tier_key}" if tier_key != "No requirements" else "  No skill requirements")
        print(f"{'═' * 60}")

        # Sub-group by category
        by_cat = defaultdict(list)
        for r in recipes:
            by_cat[r.get("category", "Other")].append(r)

        for cat in sorted(by_cat):
            print(f"\n  [{cat}]")
            for r in sorted(by_cat[cat], key=lambda x: x.get("name", "")):
                name = r.get("name", "?")
                rid = r.get("id", "")
                flow = _recipe_one_line(r)
                crafted_inputs = [
                    i["item_id"] for i in r.get("inputs", [])
                    if i.get("item_id") in by_output
                ]
                chain_marker = " ◆" if crafted_inputs else ""
                print(f"    {name}{chain_marker}")
                print(f"      {flow}")
                if rid:
                    print(f"      id: {rid}")

    # Legend
    print(f"\n{'─' * 60}")
    print("  ◆ = has crafted ingredients (use --trace to expand)")


def _do_search(query, recipe_list):
    """Filter recipes by name, id, or item_id."""
    q = query.lower()
    matches = []
    for r in recipe_list:
        searchable = " ".join([
            r.get("name", ""),
            r.get("id", ""),
            r.get("category", ""),
            " ".join(i.get("item_id", "") for i in r.get("inputs", [])),
            " ".join(o.get("item_id", "") for o in r.get("outputs", [])),
        ]).lower()
        if q in searchable:
            matches.append(r)

    if not matches:
        print(f"No recipes matching '{query}'.")
        return

    print(f"Found {len(matches)} recipe(s) matching '{query}':\n")
    for r in sorted(matches, key=lambda x: x.get("name", "")):
        name = r.get("name", "?")
        rid = r.get("id", "")
        skills = r.get("required_skills", {})
        skill_str = ""
        if skills:
            skill_str = "  [" + ", ".join(f"{s} {l}" for s, l in sorted(skills.items())) + "]"
        print(f"  {name}{skill_str}")
        print(f"    {_recipe_one_line(r)}")
        if rid:
            print(f"    id: {rid}")
        print()


def _do_trace(query, by_output, recipe_list):
    """Trace the full ingredient tree for an item or recipe."""
    if not query:
        print("Usage: sm query-recipes --trace <item_id or recipe_id>")
        return

    # Try as item_id first, then as recipe_id
    target_item = None
    target_qty = 1
    if query in by_output:
        target_item = query
    else:
        # Check if it's a recipe_id — use its first output
        for r in recipe_list:
            if r.get("id") == query:
                outputs = r.get("outputs", [])
                if outputs:
                    target_item = outputs[0].get("item_id")
                    target_qty = outputs[0].get("quantity", 1)
                break

    if not target_item:
        # Fuzzy search
        q = query.lower()
        candidates = [
            item_id for item_id in by_output
            if q in item_id.lower()
        ]
        if len(candidates) == 1:
            target_item = candidates[0]
        elif candidates:
            print(f"Ambiguous — did you mean one of these?")
            for c in sorted(candidates):
                print(f"  {c}")
            return
        else:
            print(f"No recipe produces '{query}'. Try: sm query-recipes --search {query}")
            return

    tree = _trace_ingredient_tree(target_item, target_qty, by_output)
    lines = _render_tree(tree)

    print(f"Ingredient tree for {target_item}:\n")
    for line in lines:
        print(line)

    # Raw material totals
    totals = _collect_raw_totals(tree)
    if totals:
        print(f"\n{'─' * 40}")
        print("Raw materials needed:")
        for item_id, qty in sorted(totals.items(), key=lambda x: -x[1]):
            print(f"  {qty}x {item_id}")
