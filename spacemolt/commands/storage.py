"""Base storage commands."""
import json


def cmd_storage(api, args):
    """Handle storage subcommands: view (default), deposit, withdraw."""
    subcommand = getattr(args, "storage_subcommand", None)

    if subcommand == "deposit":
        cmd_storage_deposit(api, args)
    elif subcommand == "withdraw":
        cmd_storage_withdraw(api, args)
    else:
        # Default: show storage contents
        cmd_storage_view(api, args)


def cmd_storage_view(api, args):
    """View base storage contents."""
    as_json = getattr(args, "json", False)

    # Try view_storage endpoint first, fallback to passthrough
    try:
        resp = api._post("view_storage")
    except Exception:
        # Endpoint might not exist, show helpful message
        print("Storage viewing not available.")
        print("  Hint: sm storage deposit <item> <qty>  |  sm storage withdraw <item> <qty>")
        return

    if as_json:
        print(json.dumps(resp, indent=2))
        return

    r = resp.get("result", {})
    items = r.get("items", [])
    credits = r.get("credits", 0)

    if not items and credits == 0:
        print("Storage is empty.")
        print("  Hint: sm storage deposit <item> <qty>")
        return

    print("Base Storage:")
    if credits > 0:
        print(f"  Credits: {credits:,}")

    if items:
        # Group by item type if possible
        print(f"\n  Items ({len(items)}):")
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = item.get("item_id") or item.get("name", "?")
            qty = item.get("quantity", 0)
            print(f"    {item_id} x{qty}")

    print("\n  Hint: sm storage withdraw <item> <qty>  |  sm storage deposit <item> <qty>")


def cmd_storage_deposit(api, args):
    """Deposit items or credits into base storage."""
    as_json = getattr(args, "json", False)
    item_id = getattr(args, "item_id", None)
    quantity = getattr(args, "quantity", None)
    credits = getattr(args, "credits", None)

    # Determine if depositing items or credits
    if credits is not None:
        endpoint = "deposit_credits"
        body = {"amount": credits}
        action = f"credits: {credits}"
    elif item_id and quantity:
        endpoint = "deposit_items"
        body = {"item_id": item_id, "quantity": quantity}
        action = f"{item_id} x{quantity}"
    else:
        print("Usage: sm storage deposit <item> <qty>")
        print("   or: sm storage deposit --credits <amount>")
        return

    # Require docked
    try:
        api._require_docked()
    except Exception as e:
        print(f"Error: {e}")
        return

    resp = api._post(endpoint, body)

    if as_json:
        print(json.dumps(resp, indent=2))
        return

    err = resp.get("error")
    if err:
        err_msg = err.get('message', err) if isinstance(err, dict) else err
        print(f"ERROR: {err_msg}")
        return

    print(f"Deposited: {action}")
    print("  Hint: sm storage (view storage)")


def cmd_storage_withdraw(api, args):
    """Withdraw items or credits from base storage."""
    as_json = getattr(args, "json", False)
    item_id = getattr(args, "item_id", None)
    quantity = getattr(args, "quantity", None)
    credits = getattr(args, "credits", None)

    # Determine if withdrawing items or credits
    if credits is not None:
        endpoint = "withdraw_credits"
        body = {"amount": credits}
        action = f"credits: {credits}"
    elif item_id and quantity:
        endpoint = "withdraw_items"
        body = {"item_id": item_id, "quantity": quantity}
        action = f"{item_id} x{quantity}"
    else:
        print("Usage: sm storage withdraw <item> <qty>")
        print("   or: sm storage withdraw --credits <amount>")
        return

    # Require docked
    try:
        api._require_docked()
    except Exception as e:
        print(f"Error: {e}")
        return

    resp = api._post(endpoint, body)

    if as_json:
        print(json.dumps(resp, indent=2))
        return

    err = resp.get("error")
    if err:
        err_msg = err.get('message', err) if isinstance(err, dict) else err
        print(f"ERROR: {err_msg}")
        return

    print(f"Withdrew: {action}")
    print("  Hint: sm storage (view storage)  |  sm cargo")
