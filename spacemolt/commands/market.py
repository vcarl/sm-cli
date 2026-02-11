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

    # Try view_orders endpoint first
    try:
        resp = api._post("view_orders")
    except Exception:
        # Fallback: might not be implemented
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
        print("  Hint: sm market buy <item> <qty> <price>  |  sm market sell <item> <qty> <price>")
        return

    print(f"Your Market Orders ({len(orders)}):")

    buy_orders = [o for o in orders if isinstance(o, dict) and o.get("type") == "buy"]
    sell_orders = [o for o in orders if isinstance(o, dict) and o.get("type") == "sell"]

    if buy_orders:
        print("\n  Buy Orders:")
        for order in buy_orders:
            _print_order(order)

    if sell_orders:
        print("\n  Sell Orders:")
        for order in sell_orders:
            _print_order(order)

    print("\n  Hint: sm market cancel <order_id>")


def _print_order(order):
    """Print a single order line."""
    order_id = order.get("order_id") or order.get("id", "?")
    item_id = order.get("item_id", "?")
    qty = order.get("quantity", 0)
    price = order.get("price_each") or order.get("price", 0)
    filled = order.get("filled", 0)
    remaining = qty - filled
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

    resp = api._post("create_buy_order", {
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
        return

    r = resp.get("result", {})
    order_id = r.get("order_id") or r.get("id", "?")

    print(f"Buy order created! ID: {order_id}")
    print(f"  Item: {item_id} x{quantity}")
    print(f"  Price: {price}cr each (total: {total_cost:,}cr)")
    print("\n  Hint: sm market (view orders)  |  sm market cancel <order_id>")


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
    order_id = r.get("order_id") or r.get("id", "?")

    print(f"Sell order created! ID: {order_id}")
    print(f"  Item: {item_id} x{quantity}")
    print(f"  Price: {price}cr each (total: {total_value:,}cr)")
    print("\n  Hint: sm market (view orders)  |  sm market cancel <order_id>")


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
