"""Shipyard commands — ship browsing, commissioning, showroom, and player ship exchange."""
import json


def cmd_shipyard_router(api, args):
    """Route shipyard subcommands to the appropriate handler."""
    sub = getattr(args, "shipyard_cmd", None)
    as_json = getattr(args, "json", False)

    dispatch = {
        "browse": _cmd_browse,
        "showroom": _cmd_showroom,
        "quote": _cmd_quote,
        "commission": _cmd_commission,
        "status": _cmd_status,
        "supply": _cmd_supply,
        "cancel": _cmd_cancel,
        "claim": _cmd_claim,
        "list": _cmd_list,
        "buy": _cmd_buy,
        "unlist": _cmd_unlist,
    }

    handler = dispatch.get(sub, _cmd_browse)
    handler(api, args, as_json)


def _call(api, endpoint, body, as_json):
    """Post to a shipyard endpoint; return parsed response or None on error."""
    resp = api._post(endpoint, body)
    if as_json:
        print(json.dumps(resp, indent=2))
        return None
    err = resp.get("error")
    if err:
        msg = err.get("message", err) if isinstance(err, dict) else err
        print(f"ERROR: {msg}")
        return None
    return resp.get("result", resp)


# ── Handlers ───────────────────────────────────────────────────────────────

def _cmd_browse(api, args, as_json):
    body = {}
    ship_class = getattr(args, "ship_class", None)
    max_price = getattr(args, "max_price", None)
    base_id = getattr(args, "base", None)
    if ship_class:
        body["ship_class"] = ship_class
    if max_price is not None:
        body["max_price"] = max_price
    if base_id:
        body["base_id"] = base_id
    r = _call(api, "browse_ships", body, as_json)
    if r is None:
        return
    _fmt_browse(r)


def _cmd_showroom(api, args, as_json):
    body = {}
    category = getattr(args, "category", None)
    scale = getattr(args, "scale", None)
    if category:
        body["category"] = category
    if scale is not None:
        body["scale"] = scale
    r = _call(api, "shipyard_showroom", body, as_json)
    if r is None:
        return
    _fmt_showroom(r)


def _cmd_quote(api, args, as_json):
    body = {"ship_class": args.ship_class}
    r = _call(api, "commission_quote", body, as_json)
    if r is None:
        return
    _fmt_quote(r)


def _cmd_commission(api, args, as_json):
    body = {"ship_class": args.ship_class}
    if getattr(args, "provide_materials", False):
        body["provide_materials"] = True
    r = _call(api, "commission_ship", body, as_json)
    if r is None:
        return
    _fmt_commission(r)


def _cmd_status(api, args, as_json):
    body = {}
    base_id = getattr(args, "base", None)
    if base_id:
        body["base_id"] = base_id
    r = _call(api, "commission_status", body, as_json)
    if r is None:
        return
    _fmt_status(r)


def _cmd_supply(api, args, as_json):
    body = {
        "commission_id": args.commission_id,
        "item_id": args.item_id,
        "quantity": args.quantity,
    }
    r = _call(api, "supply_commission", body, as_json)
    if r is None:
        return
    msg = r.get("message", "Materials supplied.")
    print(msg)
    print(f"\n  Hint: sm shipyard status  (check commission progress)")


def _cmd_cancel(api, args, as_json):
    body = {"commission_id": args.commission_id}
    r = _call(api, "cancel_commission", body, as_json)
    if r is None:
        return
    msg = r.get("message", "Commission cancelled.")
    print(msg)
    refund = r.get("refund")
    if refund is not None:
        print(f"  Refund: {refund:,} credits" if isinstance(refund, (int, float)) else f"  Refund: {refund}")
    print(f"\n  Hint: sm shipyard showroom  |  sm shipyard quote <ship_class>")


def _cmd_claim(api, args, as_json):
    body = {"commission_id": args.commission_id}
    r = _call(api, "claim_commission", body, as_json)
    if r is None:
        return
    msg = r.get("message", "Ship claimed!")
    print(msg)
    ship_name = r.get("ship_name") or r.get("name")
    if ship_name:
        print(f"  Ship: {ship_name}")
    print(f"\n  Hint: sm ships  |  sm ship")


def _cmd_list(api, args, as_json):
    body = {
        "ship_id": args.ship_id,
        "price": args.price,
    }
    r = _call(api, "list_ship_for_sale", body, as_json)
    if r is None:
        return
    msg = r.get("message", "Ship listed for sale.")
    print(msg)
    listing_id = r.get("listing_id")
    if listing_id:
        print(f"  Listing ID: {listing_id}")
    fee = r.get("fee")
    if fee is not None:
        print(f"  Listing fee: {fee:,} credits" if isinstance(fee, (int, float)) else f"  Listing fee: {fee}")
    print(f"\n  Hint: sm shipyard browse  |  sm shipyard unlist <listing_id>")


def _cmd_buy(api, args, as_json):
    body = {"listing_id": args.listing_id}
    r = _call(api, "buy_listed_ship", body, as_json)
    if r is None:
        return
    msg = r.get("message", "Ship purchased!")
    print(msg)
    ship_name = r.get("ship_name") or r.get("name")
    if ship_name:
        print(f"  Ship: {ship_name}")
    print(f"\n  Hint: sm ships  |  sm ship")


def _cmd_unlist(api, args, as_json):
    body = {"listing_id": args.listing_id}
    r = _call(api, "cancel_ship_listing", body, as_json)
    if r is None:
        return
    msg = r.get("message", "Listing cancelled.")
    print(msg)
    print(f"\n  Hint: sm ships  |  sm shipyard list <ship_id> <price>")


# ── Formatters ─────────────────────────────────────────────────────────────

def _fmt_browse(r):
    listings = r.get("listings") or r.get("ships", [])
    if not listings:
        print("No ships listed for sale at this location.")
        print("  Hint: sm shipyard showroom  |  sm shipyard list <ship_id> <price>")
        return

    print(f"Ships For Sale ({len(listings)}):\n")
    print(f"  {'Ship':<24} {'Class':<16} {'Price':>12}  {'Seller':<16} {'ID'}")
    print(f"  {'─'*24} {'─'*16} {'─'*12}  {'─'*16} {'─'*12}")
    for s in listings:
        name = s.get("ship_name") or s.get("name", "?")
        sclass = s.get("ship_class") or s.get("class", "?")
        price = s.get("price", 0)
        seller = s.get("seller") or s.get("player_id", "?")
        lid = s.get("listing_id") or s.get("id", "?")
        price_str = f"{price:,}" if isinstance(price, (int, float)) else str(price)
        lid_short = str(lid)[:12]
        print(f"  {name:<24} {sclass:<16} {price_str:>12}  {seller:<16} {lid_short}")

    print(f"\n  Hint: sm shipyard buy <listing_id>")


def _fmt_showroom(r):
    ships = r.get("ships") or r.get("showroom", [])
    if not ships:
        print("Showroom is empty.")
        print("  Hint: sm shipyard quote <ship_class>")
        return

    print(f"Shipyard Showroom ({len(ships)}):\n")
    print(f"  {'Ship':<24} {'Class':<16} {'Price':>12}  {'Category'}")
    print(f"  {'─'*24} {'─'*16} {'─'*12}  {'─'*14}")
    for s in ships:
        name = s.get("name", "?")
        sclass = s.get("ship_class") or s.get("class", "?")
        price = s.get("price") or s.get("cost", 0)
        cat = s.get("category", "")
        price_str = f"{price:,}" if isinstance(price, (int, float)) else str(price)
        print(f"  {name:<24} {sclass:<16} {price_str:>12}  {cat}")

    print(f"\n  Hint: sm shipyard quote <ship_class>  |  sm shipyard commission <ship_class>")


def _fmt_quote(r):
    ship_class = r.get("ship_class") or r.get("class", "?")
    name = r.get("name") or r.get("ship_name", ship_class)

    print(f"Commission Quote: {name}")
    print(f"  Class: {ship_class}")

    # Credits-only mode
    credits_cost = r.get("credits_cost") or r.get("cost")
    if credits_cost is not None:
        cost_str = f"{credits_cost:,}" if isinstance(credits_cost, (int, float)) else str(credits_cost)
        print(f"  Full price (credits): {cost_str}")

    # Provide-materials mode
    mat_cost = r.get("materials_cost") or r.get("reduced_cost")
    if mat_cost is not None:
        cost_str = f"{mat_cost:,}" if isinstance(mat_cost, (int, float)) else str(mat_cost)
        print(f"  Price (provide materials): {cost_str}")

    materials = r.get("materials") or r.get("required_materials", [])
    if materials:
        print(f"  Required materials:")
        for m in materials:
            if isinstance(m, dict):
                mid = m.get("item_id") or m.get("id", "?")
                qty = m.get("quantity", 1)
                print(f"    {mid} x{qty}")
            else:
                print(f"    {m}")

    build_time = r.get("build_time")
    if build_time:
        print(f"  Build time: {build_time}")

    print(f"\n  Hint: sm shipyard commission {ship_class}  |  sm shipyard commission {ship_class} --provide-materials")


def _fmt_commission(r):
    msg = r.get("message", "Commission placed!")
    print(msg)
    commission_id = r.get("commission_id")
    if commission_id:
        print(f"  Commission ID: {commission_id}")
    ship_class = r.get("ship_class") or r.get("class")
    if ship_class:
        print(f"  Ship class: {ship_class}")
    cost = r.get("cost") or r.get("credits_charged")
    if cost is not None:
        print(f"  Cost: {cost:,} credits" if isinstance(cost, (int, float)) else f"  Cost: {cost}")
    build_time = r.get("build_time")
    if build_time:
        print(f"  Build time: {build_time}")
    print(f"\n  Hint: sm shipyard status  (check progress and material needs)")


def _fmt_status(r):
    commissions = r.get("commissions") or r.get("orders", [])
    if not commissions:
        print("No active commissions.")
        print("  Hint: sm shipyard showroom  |  sm shipyard quote <ship_class>")
        return

    print(f"Active Commissions ({len(commissions)}):\n")
    for c in commissions:
        cid = c.get("commission_id") or c.get("id", "?")
        ship_class = c.get("ship_class") or c.get("class", "?")
        status = c.get("status", "?")
        progress = c.get("progress")
        base = c.get("base_id") or c.get("base", "")

        line = f"  [{cid[:12] if len(str(cid)) > 12 else cid}] {ship_class} — {status}"
        if progress is not None:
            line += f" ({progress}%)"
        if base:
            line += f"  @ {base}"
        print(line)

        # Show missing materials if any
        missing = c.get("missing_materials") or c.get("materials_needed", [])
        if missing:
            for m in missing:
                if isinstance(m, dict):
                    mid = m.get("item_id") or m.get("id", "?")
                    qty = m.get("quantity", 0)
                    supplied = m.get("supplied", 0)
                    print(f"    need {mid}: {supplied}/{qty}")

    print(f"\n  Hint: sm shipyard supply <id> <item> <qty>  |  sm shipyard claim <id>")
