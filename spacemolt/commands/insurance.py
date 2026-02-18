"""Insurance system commands."""
import json


def cmd_insurance(api, args):
    """Handle insurance subcommands: status (default), buy, claim."""
    subcommand = getattr(args, "insurance_subcommand", None)
    as_json = getattr(args, "json", False)

    if subcommand == "buy":
        cmd_insurance_buy(api, args)
    elif subcommand == "claim":
        cmd_insurance_claim(api, args)
    else:
        # Default: show status
        cmd_insurance_status(api, args)


def cmd_insurance_status(api, args):
    """Show current insurance coverage status."""
    as_json = getattr(args, "json", False)

    resp = api._post("get_status")
    if as_json:
        print(json.dumps(resp, indent=2))
        return

    r = resp.get("result", {})
    insurance = r.get("insurance", {})

    if not insurance or not isinstance(insurance, dict):
        print("No active insurance coverage.")
        print("  Hint: sm insurance buy <coverage_percent> <ticks>")
        return

    ticks_remaining = insurance.get("ticks_remaining") or insurance.get("ticks", 0)
    coverage_amount = insurance.get("coverage_amount") or insurance.get("amount", 0)
    ship_value = r.get("ship_value", 0)

    print("Insurance Coverage:")
    print(f"  Ticks remaining: {ticks_remaining}")
    if coverage_amount:
        print(f"  Coverage amount: {coverage_amount:,} cr")
    if ship_value:
        coverage_pct = (coverage_amount / ship_value * 100) if ship_value > 0 else 0
        print(f"  Ship value: {ship_value:,} cr ({coverage_pct:.1f}% covered)")

    if ticks_remaining <= 0:
        print("\n  ⚠️  Insurance has expired!")
        print("  Hint: sm insurance buy <coverage_percent> <ticks>")
    elif ticks_remaining < 10:
        print(f"\n  ⚠️  Insurance expires soon!")
        print("  Hint: sm insurance buy <coverage_percent> <ticks>")


def cmd_insurance_buy(api, args):
    """Purchase insurance coverage."""
    as_json = getattr(args, "json", False)
    ticks = args.ticks
    coverage_percent = args.coverage_percent

    if ticks <= 0:
        print("Error: Ticks must be greater than 0")
        return
    if not (50 <= coverage_percent <= 100):
        print("Error: Coverage percent must be between 50 and 100")
        return

    resp = api._post("buy_insurance", {"coverage_percent": coverage_percent, "ticks": ticks})

    if as_json:
        print(json.dumps(resp, indent=2))
        return

    err = resp.get("error")
    if err:
        err_msg = err.get('message', err) if isinstance(err, dict) else err
        print(f"ERROR: {err_msg}")
        return

    r = resp.get("result", {})
    premium = r.get("premium", "?")
    coverage = r.get("coverage", "?")
    expires = r.get("expires_at", "")
    message = r.get("message", "")

    if message:
        print(message)
    else:
        print(f"Insurance purchased!")
        print(f"  Premium: {premium} cr")
        print(f"  Coverage: {coverage:,} cr" if coverage != "?" else f"  Coverage: {coverage}")
        if expires:
            print(f"  Expires: {expires}")

    print("\n  Hint: sm insurance (check status)")


def cmd_insurance_claim(api, args):
    """Claim insurance payout after ship destruction."""
    as_json = getattr(args, "json", False)

    resp = api._post("claim_insurance")

    if as_json:
        print(json.dumps(resp, indent=2))
        return

    err = resp.get("error")
    if err:
        err_msg = err.get('message', err) if isinstance(err, dict) else err
        print(f"ERROR: {err_msg}")

        # Provide helpful hints based on error
        if "no insurance" in str(err_msg).lower():
            print("\n  You don't have active insurance coverage.")
            print("  Hint: sm insurance buy <coverage_percent> <ticks>")
        elif "not destroyed" in str(err_msg).lower() or "alive" in str(err_msg).lower():
            print("\n  Your ship is still intact - no claim needed!")
        return

    r = resp.get("result", {})
    msg = r.get("message")
    if msg:
        print(msg)

    policies = r.get("policies", [])
    if policies:
        print(f"  Policies: {len(policies)}")
        for p in policies:
            if isinstance(p, dict):
                print(f"    {p.get('policy_id', '?')}: {p.get('coverage', '?')} cr coverage")

    payout = r.get("payout", "?")
    new_credits = r.get("credits", "?")

    print(f"Insurance claim successful!")
    print(f"  Payout: {payout} cr")
    if new_credits != "?":
        print(f"  New balance: {new_credits:,} cr")
    print("\n  Hint: sm buy-ship <class>  |  sm ships")
