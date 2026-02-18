import json
import sys


def cmd_missions_combined(api, args):
    """Show both active missions and available missions (combined view)."""
    as_json = getattr(args, "json", False)

    # Fetch both active and available missions
    active_resp = api._post("get_active_missions")
    available_resp = api._post("get_missions")

    if as_json:
        # Return combined JSON
        print(json.dumps({
            "active": active_resp,
            "available": available_resp
        }, indent=2))
        return

    # Format active missions
    active_r = active_resp.get("result", {})
    active_missions = active_r.get("missions") or active_r.get("active_missions") or []
    max_m = active_r.get("max_missions", 5)

    print(f"Active missions ({len(active_missions)}/{max_m}):")
    if active_missions:
        for m in active_missions:
            title = m.get("title") or m.get("name", "?")
            mid = m.get("id") or m.get("mission_id", "")
            status = m.get("status", "")

            line = f"  {title}"
            if status:
                line += f"  [{status}]"
            print(line)

            desc = m.get("description", "")
            if desc:
                # Truncate for combined view
                if len(desc) > 60:
                    desc = desc[:57] + "..."
                print(f"    {desc}")

            objectives = m.get("objectives") or []
            for obj in objectives[:2]:  # Show max 2 objectives in compact view
                if isinstance(obj, dict):
                    obj_desc = obj.get("description") or obj.get("name", "")
                    obj_cur = obj.get("current", 0)
                    obj_tgt = obj.get("required") or obj.get("target", "?")
                    if obj_desc:
                        print(f"    - {obj_desc}: {obj_cur}/{obj_tgt}")

            if mid:
                print(f"    id: {mid}")
            print()
    else:
        print("  (none)\n")

    # Format available missions
    avail_r = available_resp.get("result", {})
    available_missions = avail_r.get("missions") or []

    print("Available missions:")
    if available_missions:
        for m in available_missions[:5]:  # Show first 5 in combined view
            title = m.get("title") or m.get("name", "?")
            mid = m.get("id") or m.get("mission_id", "")
            mtype = m.get("type", "")
            diff = m.get("difficulty", "")
            reward_cr = m.get("reward_credits") or m.get("credits")

            meta = []
            if mtype:
                meta.append(mtype)
            if diff:
                meta.append(f"diff: {diff}")
            if reward_cr:
                meta.append(f"{reward_cr} cr")

            line = f"  {title}"
            if meta:
                line += f"  [{', '.join(meta)}]"
            print(line)

            if mid:
                print(f"    id: {mid}")

        if len(available_missions) > 5:
            print(f"\n  ... and {len(available_missions) - 5} more")
            print("  Use 'sm missions available' to see all available missions")
    else:
        print("  (none - not docked at a base)")


def cmd_missions_available(api, args):
    """Show available missions at current base only."""
    as_json = getattr(args, "json", False)
    resp = api._post("get_missions")
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    r = resp.get("result", {})
    missions = r.get("missions") or []
    if not missions:
        print("No missions available. (Must be docked at a base)")
        return

    for m in missions:
        title = m.get("title") or m.get("name", "?")
        mid = m.get("id") or m.get("mission_id", "")
        mtype = m.get("type", "")
        diff = m.get("difficulty", "")
        print(f"\n{title}")
        meta = []
        if mtype:
            meta.append(mtype)
        if diff:
            meta.append(f"difficulty: {diff}")
        if meta:
            print(f"  [{', '.join(meta)}]")

        desc = m.get("description", "")
        if desc:
            print(f"  {desc}")

        reward_cr = m.get("reward_credits") or m.get("credits")
        reward_items = m.get("reward_items") or []
        rewards = []
        if reward_cr:
            rewards.append(f"{reward_cr} cr")
        for ri in reward_items:
            if isinstance(ri, dict):
                rewards.append(f"{ri.get('item_id', '?')} x{ri.get('quantity', 1)}")
            else:
                rewards.append(str(ri))
        if rewards:
            print(f"  Rewards: {', '.join(rewards)}")

        loc = m.get("location") or m.get("destination")
        dist = m.get("distance")
        if loc:
            loc_str = f"  Location: {loc}"
            if dist is not None:
                loc_str += f" ({dist} jumps)"
            print(loc_str)

        if mid:
            print(f"  id: {mid}")


def cmd_missions(api, args):
    """
    Backwards-compatible wrapper: shows available missions only (old behavior).

    For the new combined view, use cmd_missions_combined via hierarchical routing.
    """
    cmd_missions_available(api, args)


def cmd_active_missions(api, args):
    """Show your currently accepted missions."""
    as_json = getattr(args, "json", False)
    resp = api._post("get_active_missions")
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    r = resp.get("result", {})
    missions = r.get("missions") or r.get("active_missions") or []
    max_m = r.get("max_missions", 5)

    if not missions:
        print(f"No active missions. ({0}/{max_m} slots used)")
        return

    print(f"Active missions ({len(missions)}/{max_m}):\n")
    for m in missions:
        title = m.get("title") or m.get("name", "?")
        mid = m.get("id") or m.get("mission_id", "")
        status = m.get("status", "")
        progress = m.get("progress")
        deadline = m.get("deadline_tick") or m.get("deadline")

        line = title
        if status:
            line += f"  [{status}]"
        print(line)

        desc = m.get("description", "")
        if desc:
            print(f"  {desc}")
        objectives = m.get("objectives") or []
        for obj in objectives:
            if isinstance(obj, dict):
                obj_desc = obj.get("description") or obj.get("name", "")
                obj_cur = obj.get("current", 0)
                obj_tgt = obj.get("required") or obj.get("target", "?")
                if obj_desc:
                    print(f"  - {obj_desc}: {obj_cur}/{obj_tgt}")
            else:
                print(f"  - {obj}")

        if progress is not None:
            if isinstance(progress, dict):
                pct = progress.get("percent_complete")
                if pct is not None:
                    print(f"  Progress: {pct}% complete")
                else:
                    current = progress.get("current", 0)
                    target = progress.get("target", "?")
                    print(f"  Progress: {current}/{target}")
            else:
                print(f"  Progress: {progress}")

        if deadline is not None:
            print(f"  Deadline: tick {deadline}")

        rewards = m.get("rewards") or {}
        reward_parts = []
        if isinstance(rewards, dict):
            cr = rewards.get("credits")
            if cr:
                reward_parts.append(f"{cr} cr")
            items = rewards.get("items", {})
            if isinstance(items, dict):
                for item_id, qty in items.items():
                    reward_parts.append(f"{item_id} x{qty}")
            else:
                for ri in items:
                    if isinstance(ri, dict):
                        reward_parts.append(f"{ri.get('item_id', '?')} x{ri.get('quantity', 1)}")
                    else:
                        reward_parts.append(str(ri))
        elif isinstance(rewards, list):
            for ri in rewards:
                reward_parts.append(str(ri))
        if reward_parts:
            print(f"  Rewards: {', '.join(reward_parts)}")

        if mid:
            print(f"  id: {mid}")
        print()


def cmd_query_missions(api, args):
    """Mission explorer: list available, show active, or search."""
    as_json = getattr(args, "json", False)
    active = getattr(args, "active", False)
    search_query = getattr(args, "search", None)
    limit = getattr(args, "limit", 10)
    page = getattr(args, "page", 1)

    if active:
        # Delegate to active missions view
        cmd_active_missions(api, args)
        return

    resp = api._post("get_missions")
    if as_json:
        print(json.dumps(resp, indent=2))
        return

    r = resp.get("result", {})
    missions = r.get("missions") or []

    if not missions:
        print("No missions available. (Must be docked at a base)")
        return

    if search_query:
        q = search_query.lower()
        missions = [m for m in missions if q in " ".join([
            m.get("title", ""),
            m.get("description", ""),
            m.get("type", ""),
            m.get("id", ""),
        ]).lower()]
        if not missions:
            print(f"No missions matching '{search_query}'.")
            return
        print(f"Found {len(missions)} mission(s) matching '{search_query}':\n")

    # Sort all missions by type, difficulty, reward
    missions.sort(key=lambda m: (
        m.get("type", "Other"),
        m.get("difficulty", 0) if isinstance(m.get("difficulty"), (int, float)) else 0,
        -(m.get("reward_credits", 0) or 0),
    ))

    from spacemolt.commands import paginate, print_page_footer
    page_missions, total, total_pages, page = paginate(missions, limit, page)

    prev_type = None
    for m in page_missions:
        mtype = m.get("type", "Other")
        if mtype != prev_type:
            print(f"\n{'═' * 50}")
            print(f"  {mtype.upper()}")
            print(f"{'═' * 50}")
            prev_type = mtype

        title = m.get("title") or m.get("name", "?")
        mid = m.get("id", "")
        diff = m.get("difficulty", "")
        reward_cr = m.get("reward_credits") or m.get("credits", 0)
        dist = m.get("distance")

        diff_str = f"  [diff: {diff}]" if diff else ""
        reward_str = f"  {reward_cr} cr" if reward_cr else ""
        dist_str = f"  ({dist} jumps)" if dist is not None else ""

        print(f"    {title}{diff_str}{reward_str}{dist_str}")

        desc = m.get("description", "")
        if desc:
            # Truncate long descriptions
            if len(desc) > 80:
                desc = desc[:77] + "..."
            print(f"      {desc}")

        reward_items = m.get("reward_items") or []
        if reward_items:
            parts = []
            for ri in reward_items:
                if isinstance(ri, dict):
                    parts.append(f"{ri.get('item_id', '?')} x{ri.get('quantity', 1)}")
                else:
                    parts.append(str(ri))
            print(f"      + items: {', '.join(parts)}")

        if mid:
            print(f"      id: {mid}")

    print_page_footer(total, total_pages, page, limit)


# ---------------------------------------------------------------------------
# Hierarchical command router
# ---------------------------------------------------------------------------

def cmd_missions_router(api, args):
    """Route missions subcommands to appropriate handlers."""
    subcmd = getattr(args, "missions_cmd", None)

    if not subcmd:
        # No subcommand: show combined view (active + available)
        cmd_missions_combined(api, args)
    elif subcmd == "active":
        cmd_active_missions(api, args)
    elif subcmd == "available":
        cmd_missions_available(api, args)
    elif subcmd == "query":
        cmd_query_missions(api, args)
    elif subcmd == "accept":
        _passthrough_mission_action(api, "accept_mission", args)
    elif subcmd == "complete":
        _passthrough_mission_action(api, "complete_mission", args)
    elif subcmd == "abandon":
        _passthrough_mission_action(api, "abandon_mission", args)
    else:
        print(f"Unknown missions subcommand: {subcmd}", file=sys.stderr)
        sys.exit(1)


def _passthrough_mission_action(api, endpoint, args):
    """Helper to call passthrough for mission actions (accept, complete, abandon)."""
    from spacemolt.commands.passthrough import cmd_passthrough
    mission_id = getattr(args, "mission_id", None)
    extra_args = [mission_id] if mission_id else []
    as_json = getattr(args, "json", False)
    cmd_passthrough(api, endpoint, extra_args, as_json=as_json)
