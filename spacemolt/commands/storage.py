"""Base storage commands — uses the unified /storage endpoint."""
import json


def cmd_storage(api, args):
    """Handle storage subcommands: view (default), deposit, withdraw."""
    subcommand = getattr(args, "storage_subcommand", None)

    if subcommand == "deposit":
        _storage_transfer(api, args, "deposit")
    elif subcommand == "withdraw":
        _storage_transfer(api, args, "withdraw")
    else:
        _storage_view(api, args)


def _storage_view(api, args):
    """View base storage contents."""
    as_json = getattr(args, "json", False)
    target = getattr(args, "target", None) or "self"
    station = getattr(args, "station", None)

    # Use view_storage endpoint for remote station viewing
    if station:
        try:
            resp = api._post("view_storage", {"station_id": station})
        except Exception:
            print(f"Could not view storage at station '{station}'.")
            return
    else:
        body = {"action": "view"}
        if target != "self":
            body["target"] = target
        try:
            resp = api._post("storage", body)
        except Exception:
            print("Storage viewing not available.")
            print("  Hint: sm storage deposit <item> <qty>  |  sm storage withdraw <item> <qty>")
            return

    if as_json:
        print(json.dumps(resp, indent=2))
        return

    err = resp.get("error")
    if err:
        err_msg = err.get("message", err) if isinstance(err, dict) else err
        print(f"ERROR: {err_msg}")
        return

    r = resp.get("result", {})
    items = r.get("items", [])
    credits = r.get("credits", 0)

    if station:
        label = f"Storage @ {station}"
    elif target == "faction":
        label = "Faction Storage"
    else:
        label = "Base Storage"
    if not items and credits == 0:
        print(f"{label} is empty.")
        print("  Hint: sm storage deposit <item> <qty>")
        return

    print(f"{label}:")
    if credits > 0:
        print(f"  Credits: {credits:,}")

    if items:
        print(f"\n  Items ({len(items)}):")
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = item.get("item_id") or item.get("name", "?")
            qty = item.get("quantity", 0)
            print(f"    {item_id} x{qty}")

    print(f"\n  Hint: sm storage withdraw <item> <qty>  |  sm storage deposit <item> <qty>")


def _storage_transfer(api, args, action):
    """Deposit or withdraw items/credits via the unified /storage endpoint."""
    as_json = getattr(args, "json", False)
    item_id = getattr(args, "item_id", None)
    quantity = getattr(args, "quantity", None)
    credits_amt = getattr(args, "credits", None)
    target = getattr(args, "target", None) or "self"
    message = getattr(args, "message", None)

    body = {"action": action}

    if target != "self":
        body["target"] = target

    if credits_amt is not None:
        body["item_id"] = "credits"
        body["quantity"] = credits_amt
        desc = f"credits: {credits_amt}"
    elif item_id and quantity:
        body["item_id"] = item_id
        body["quantity"] = quantity
        desc = f"{item_id} x{quantity}"
    else:
        print(f"Usage: sm storage {action} <item> <qty>")
        print(f"   or: sm storage {action} --credits <amount>")
        if action == "deposit":
            print(f"   or: sm storage {action} <item> <qty> --target <player>  (gift)")
        return

    if message:
        body["message"] = message

    from spacemolt.api import APIError
    try:
        resp = api._post("storage", body)
    except APIError as e:
        print(f"ERROR: {e}")
        return

    if as_json:
        print(json.dumps(resp, indent=2))
        return

    err = resp.get("error")
    if err:
        err_msg = err.get("message", err) if isinstance(err, dict) else err
        print(f"ERROR: {err_msg}")
        return

    r = resp.get("result", {})
    msg = r.get("message")
    if msg:
        print(msg)
    else:
        verb = "Deposited" if action == "deposit" else "Withdrew"
        if target not in ("self", None):
            verb = f"{verb} (to {target})"
        print(f"{verb}: {desc}")
    print("  Hint: sm storage (view storage)")
