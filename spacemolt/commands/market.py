"""Market orders commands."""
import json


def cmd_market(api, args):
    """Handle market subcommands: orders (default), buy, sell, cancel."""
    subcommand = getattr(args, "market_subcommand", None)

    if subcommand == "buy":
        cmd_market_buy_order(api, args)
    elif subcommand == "sell":
        cmd_market_sell_order(api, args)
    elif subcommand == "cancel":
        cmd_market_cancel_order(api, args)
    else:
        # Default: show orders
        cmd_market_orders(api, args)


def cmd_market_orders(api, args):
    """View your active market orders."""
    as_json = getattr(args, "json", False)

    station = getattr(args, "station", None)

    # view_orders requires docking or a station_id — derive from current location if not given
    if not station:
        try:
            status_resp = api._post("get_status")
            player = status_resp.get("result", {}).get("player", {})
            # Use docked_at_base first (most reliable when docked), fall back to home_base
            station = player.get("docked_at_base") or player.get("home_base")
        except Exception:
            pass

    try:
        body = {"station_id": station} if station else {}
        resp = api._post("view_orders", body)
    except Exception:
        print("Market orders viewing not available.")
        print("  Hint: sm market buy <item> <qty> <price>  |  sm market sell <item> <qty> <price>")
        return

    if as_json:
        print(json.dumps(resp, indent=2))
        return

    r = resp.get("result", {})
    orders = r.get("orders", [])

    if not orders:
        print("No active market orders.")
        print("  Hint: sm listings  (view market)")
        print("        sm market buy <item> <qty> <price>  |  sm market sell <item> <qty> <price>")
        return

    print(f"Your Market Orders ({len(orders)}):")

    buy_orders = [o for o in orders if isinstance(o, dict) and o.get("order_type") == "buy"]
    sell_orders = [o for o in orders if isinstance(o, dict) and o.get("order_type") == "sell"]

    if buy_orders:
        print("\n  Buy Orders:")
        for order in buy_orders:
            _print_order(order)

    if sell_orders:
        print("\n  Sell Orders:")
        for order in sell_orders:
            _print_order(order)

    print("\n  Hint: sm listings  (view market)  |  sm market cancel <order_id>")
    print("        sm market buy <item> <qty> <price>  |  sm market sell <item> <qty> <price>")


def _print_order(order):
    """Print a single order line."""
    order_id = order.get("order_id") or order.get("id", "?")
    item_id = order.get("item_id", "?")
    qty = order.get("quantity", 0)
    price = order.get("price_each", 0)
    remaining = order.get("remaining", qty)
    filled = qty - remaining
    total = remaining * price

    status = ""
    if filled > 0:
        status = f" ({filled} filled)"

    print(f"    {item_id} x{remaining}/{qty} @ {price}cr ea = {total:,}cr - ID: {order_id}{status}")


def cmd_market_buy_order(api, args):
    """Create a buy order for an item."""
    as_json = getattr(args, "json", False)
    item_id = args.item_id
    quantity = args.quantity
    price = args.price

    if quantity <= 0 or price <= 0:
        print("Error: Quantity and price must be greater than 0")
        return

    total_cost = quantity * price
    print(f"Creating buy order: {item_id} x{quantity} @ {price}cr ea (total: {total_cost:,}cr)")

    body = {
        "item_id": item_id,
        "quantity": quantity,
        "price_each": price
    }
    deliver_to = getattr(args, "deliver_to", None)
    if deliver_to:
        body["deliver_to"] = deliver_to
    resp = api._post("create_buy_order", body)

    if as_json:
        print(json.dumps(resp, indent=2))
        return

    err = resp.get("error")
    if err:
        err_msg = err.get('message', err) if isinstance(err, dict) else err
        print(f"ERROR: {err_msg}")
        return

    r = resp.get("result", {})

    # Check if action was queued (async processing)
    if r.get("queued"):
        tick = r.get("estimated_tick", "?")
        print(f"Buy order queued for processing at tick {tick}")
        print("  Check notifications or market orders to see the result")
        print("  Hint: sm notifications  |  sm market")
        return

    # Check if order was filled vs listed
    filled = r.get("quantity_filled", 0)
    listed = r.get("quantity_listed", 0)
    order_id = r.get("order_id")

    if filled > 0:
        total_spent = r.get("total_spent", filled * price)
        print(f"Buy order matched! Bought {filled}x {item_id} for {total_spent:,}cr")
        fills = r.get("fills", [])
        if fills:
            for fill in fills:
                counterparty = fill.get("counterparty", "?")
                qty = fill.get("quantity", 0)
                fill_price = fill.get("price_each", 0)
                print(f"  {qty}x @ {fill_price}cr from {counterparty}")

    if listed > 0 and order_id:
        print(f"Buy order listed: {listed}x {item_id} @ {price}cr ea - ID: {order_id}")
        print("  Hint: sm market (view orders)  |  sm market cancel <order_id>")
    elif listed > 0:
        print(f"Buy order listed: {listed}x {item_id} @ {price}cr ea")
        print("  Hint: sm market (view orders)")

    if filled == 0 and listed == 0:
        print("Order processed but no details available")
        print(f"  Hint: sm market (view orders)  |  sm cargo")


def cmd_market_sell_order(api, args):
    """Create a sell order for an item."""
    as_json = getattr(args, "json", False)
    item_id = args.item_id
    quantity = args.quantity
    price = args.price

    if quantity <= 0 or price <= 0:
        print("Error: Quantity and price must be greater than 0")
        return

    total_value = quantity * price
    print(f"Creating sell order: {item_id} x{quantity} @ {price}cr ea (total: {total_value:,}cr)")

    resp = api._post("create_sell_order", {
        "item_id": item_id,
        "quantity": quantity,
        "price_each": price
    })

    if as_json:
        print(json.dumps(resp, indent=2))
        return

    err = resp.get("error")
    if err:
        err_msg = err.get('message', err) if isinstance(err, dict) else err
        print(f"ERROR: {err_msg}")

        # Helpful hints
        if "not enough" in str(err_msg).lower() or "insufficient" in str(err_msg).lower():
            print("\n  You don't have enough of this item in your cargo.")
            print("  Hint: sm cargo  |  sm storage withdraw")
        return

    r = resp.get("result", {})

    # Check if action was queued (async processing)
    if r.get("queued"):
        tick = r.get("estimated_tick", "?")
        print(f"Sell order queued for processing at tick {tick}")
        print("  Check notifications or market orders to see the result")
        print("  Hint: sm notifications  |  sm market")
        return

    # Check if order was filled vs listed
    filled = r.get("quantity_filled", 0)
    listed = r.get("quantity_listed", 0)
    order_id = r.get("order_id")

    if filled > 0:
        total_earned = r.get("total_earned", filled * price)
        print(f"Sell order matched! Sold {filled}x {item_id} for {total_earned:,}cr")
        fills = r.get("fills", [])
        if fills:
            for fill in fills:
                counterparty = fill.get("counterparty", "?")
                qty = fill.get("quantity", 0)
                fill_price = fill.get("price_each", 0)
                print(f"  {qty}x @ {fill_price}cr to {counterparty}")

    if listed > 0 and order_id:
        print(f"Sell order listed: {listed}x {item_id} @ {price}cr ea - ID: {order_id}")
        print("  Hint: sm market (view orders)  |  sm market cancel <order_id>")
    elif listed > 0:
        print(f"Sell order listed: {listed}x {item_id} @ {price}cr ea")
        print("  Hint: sm market (view orders)")

    if filled == 0 and listed == 0:
        print("Order processed but no details available")
        print(f"  Hint: sm market (view orders)  |  sm cargo")


def cmd_market_cancel_order(api, args):
    """Cancel a market order."""
    as_json = getattr(args, "json", False)
    order_id = args.order_id

    resp = api._post("cancel_order", {"order_id": order_id})

    if as_json:
        print(json.dumps(resp, indent=2))
        return

    err = resp.get("error")
    if err:
        err_msg = err.get('message', err) if isinstance(err, dict) else err
        print(f"ERROR: {err_msg}")
        return

    print(f"Order cancelled: {order_id}")
    print("  Hint: sm market (view remaining orders)")
