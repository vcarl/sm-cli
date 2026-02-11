import json
import sys


def cmd_skills(api, args):
    """Show your trained skills (default view)."""
    resp = api._post("get_skills")
    skills = resp.get("result", {}).get("player_skills", [])
    skills.sort(key=lambda s: (-s.get("level", 0), -s.get("current_xp", 0)))

    as_json = getattr(args, "json", False)
    if as_json:
        print(json.dumps(resp, indent=2))
        return

    if not skills:
        print("(no skills trained yet)")
    else:
        for s in skills:
            name = s.get("name", "?")
            level = s.get("level", 0)
            xp = s.get("current_xp", 0)
            next_xp = s.get("next_level_xp", "?")
            print(f"{name}: L{level} ({xp}/{next_xp} XP)")


# --- Skill tree explorer ---

def _build_skill_tree(skills_dict):
    """Build lookup structures for the skill tree."""
    by_id = {}
    by_category = {}
    dependents = {}  # skill_id -> list of skills that require it

    for sid, s in skills_dict.items():
        by_id[sid] = s
        cat = s.get("category", "Other")
        by_category.setdefault(cat, []).append(s)
        for req_id in (s.get("required_skills") or {}):
            dependents.setdefault(req_id, []).append(s)

    return by_id, by_category, dependents


def _skill_tier(skill):
    """Return (max_prereq_level, prereq_count) for ordering."""
    reqs = skill.get("required_skills") or {}
    if not reqs:
        return (0, 0)
    return (max(reqs.values()), len(reqs))


def _skill_one_line(skill, player_map=None):
    """Format a skill as a compact one-liner."""
    sid = skill.get("id", "?")
    name = skill.get("name", "?")
    max_lvl = skill.get("max_level", "?")

    progress = ""
    if player_map and sid in player_map:
        ps = player_map[sid]
        lvl = ps.get("level", 0)
        xp = ps.get("current_xp", 0)
        next_xp = ps.get("next_level_xp", "?")
        progress = f"  L{lvl}/{max_lvl} ({xp}/{next_xp} XP)"
    else:
        progress = f"  (max L{max_lvl})"

    return f"{name}{progress}"


def _trace_skill_tree(skill_id, by_id, depth=0, seen=None):
    """Recursively build a prerequisite tree: what do you need to train first?"""
    if seen is None:
        seen = set()
    skill = by_id.get(skill_id)
    if skill is None or skill_id in seen:
        return (depth, skill_id, None, [])
    seen = seen | {skill_id}
    children = []
    for req_id, req_lvl in sorted((skill.get("required_skills") or {}).items()):
        child = _trace_skill_tree(req_id, by_id, depth + 1, seen)
        # Annotate the required level
        children.append((child, req_lvl))
    return (depth, skill_id, skill, children)


def _render_skill_tree(node, by_id, player_map=None, prefix="", is_last=True, lines=None):
    """Render a skill prerequisite tree with box-drawing connectors."""
    if lines is None:
        lines = []
    depth, skill_id, skill, children = node

    if skill:
        name = skill.get("name", skill_id)
        max_lvl = skill.get("max_level", "?")
        label = f"{name} (max L{max_lvl})"
        if player_map and skill_id in player_map:
            ps = player_map[skill_id]
            label += f"  [YOU: L{ps.get('level', 0)}, {ps.get('current_xp', 0)}/{ps.get('next_level_xp', '?')} XP]"
    else:
        label = f"{skill_id} (unknown)"

    if depth == 0:
        lines.append(label)
        desc = (skill or {}).get("description", "")
        if desc:
            lines.append(f"  {desc}")
        bonuses = (skill or {}).get("bonus_per_level", {})
        if bonuses:
            parts = [f"{k}: +{v}/lvl" for k, v in sorted(bonuses.items())]
            lines.append(f"  Bonuses: {', '.join(parts)}")
    else:
        connector = "\u2514\u2500\u2500 " if is_last else "\u251c\u2500\u2500 "
        lines.append(f"{prefix}{connector}{label}")

    child_prefix = prefix + ("    " if is_last else "\u2502   ")
    for i, (child_node, req_lvl) in enumerate(children):
        child_is_last = (i == len(children) - 1)
        # Show required level on the branch
        child_depth, child_sid, child_skill, _ = child_node
        req_marker = f" (need L{req_lvl})"
        # Temporarily patch the label
        if child_skill:
            orig_name = child_skill.get("name", child_sid)
            label_with_req = f"{orig_name} (max L{child_skill.get('max_level', '?')}){req_marker}"
            if player_map and child_sid in player_map:
                ps = player_map[child_sid]
                lvl = ps.get("level", 0)
                met = "\u2713" if lvl >= req_lvl else "\u2717"
                label_with_req += f"  [{met} YOU: L{lvl}]"
        else:
            label_with_req = f"{child_sid} (unknown){req_marker}"

        conn = "\u2514\u2500\u2500 " if child_is_last else "\u251c\u2500\u2500 "
        lines.append(f"{child_prefix}{conn}{label_with_req}")

        # Recurse into grandchildren
        inner_prefix = child_prefix + ("    " if child_is_last else "\u2502   ")
        _, _, _, grandchildren = child_node
        for j, (gc_node, gc_req_lvl) in enumerate(grandchildren):
            _render_skill_tree(gc_node, by_id, player_map, inner_prefix,
                              j == len(grandchildren) - 1, lines)

    return lines


def _find_unlocks(skill_id, level, by_id):
    """Find what other skills/recipes become available at a given skill level."""
    unlocks = []
    for sid, s in by_id.items():
        reqs = s.get("required_skills") or {}
        if skill_id in reqs and reqs[skill_id] <= level:
            unlocks.append(s)
    return unlocks


def _fetch_skill_data(api):
    """Fetch and index skill data. Returns (data_dict, raw_resp)."""
    resp = api._post("get_skills")
    r = resp.get("result", {})
    skills_dict = r.get("skills", {})
    player_skills = r.get("player_skills", [])

    if not skills_dict:
        return None, resp

    by_id, by_category, dependents = _build_skill_tree(skills_dict)

    player_map = {}
    for ps in player_skills:
        sid = ps.get("skill_id") or ps.get("id", "")
        if sid:
            player_map[sid] = ps

    return {
        "skills_dict": skills_dict,
        "player_map": player_map,
        "by_id": by_id,
        "by_category": by_category,
        "dependents": dependents,
    }, resp


def cmd_query_skills(api, args):
    """Compact skill list by category, with trained status inline."""
    as_json = getattr(args, "json", False)
    data, resp = _fetch_skill_data(api)
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    if data is None:
        print("No skill data available.")
        return

    search_query = getattr(args, "search", None)
    show_my = getattr(args, "my", False)
    limit = getattr(args, "limit", 10)
    page = getattr(args, "page", 1)

    if search_query:
        _do_skill_search(search_query, data["skills_dict"], data["player_map"], limit=limit, page=page)
    elif show_my:
        player_skills = resp.get("result", {}).get("player_skills", [])
        _do_my_skills(player_skills, data["by_id"], data["dependents"], limit=limit, page=page)
    else:
        _do_skill_list(data["by_category"], data["player_map"], limit=limit, page=page)


def cmd_skill(api, args):
    """Deep inspection of a single skill: prereqs, bonuses, XP table, unlocks."""
    as_json = getattr(args, "json", False)
    data, resp = _fetch_skill_data(api)
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    if data is None:
        print("No skill data available.")
        return

    _do_skill_trace(args.skill_id, data["by_id"], data["player_map"])


def _do_skill_list(by_category, player_map, limit=10, page=1):
    """Compact one-line-per-skill list grouped by category."""
    from spacemolt.commands import paginate, print_page_footer

    # Flatten into sorted list of (category, tier_key, skill)
    entries = []
    for cat in sorted(by_category):
        for s in sorted(by_category[cat], key=lambda x: _skill_tier(x)):
            entries.append((cat, s))

    page_entries, total, total_pages, page = paginate(entries, limit, page)

    prev_cat = None
    # Count trained per category across ALL skills (not just current page)
    cat_trained = {}
    cat_total = {}
    for cat in by_category:
        skills = by_category[cat]
        cat_total[cat] = len(skills)
        cat_trained[cat] = sum(1 for s in skills if s.get("id", "") in player_map)

    for cat, s in page_entries:
        if cat != prev_cat:
            print(f"\n{cat.upper()} ({cat_trained.get(cat, 0)}/{cat_total.get(cat, 0)} trained)")
            prev_cat = cat

        sid = s.get("id", "?")
        name = s.get("name", "?")
        max_lvl = s.get("max_level", "?")

        if sid in player_map:
            ps = player_map[sid]
            lvl = ps.get("level", 0)
            xp = ps.get("current_xp", 0)
            next_xp = ps.get("next_level_xp", "?")
            print(f"  {name:<28s} L{lvl}/{max_lvl}  ({xp}/{next_xp} XP)")
        else:
            reqs = s.get("required_skills") or {}
            if reqs:
                req_str = ", ".join(f"{r} L{l}" for r, l in sorted(reqs.items()))
                print(f"  {name:<28s} --/{max_lvl}  needs: {req_str}")
            else:
                print(f"  {name:<28s} --/{max_lvl}")

    print_page_footer(total, total_pages, page, limit)


def _do_skill_search(query, skills_dict, player_map, limit=10, page=1):
    """Search skills by name, description, category, or bonus."""
    from spacemolt.commands import paginate, print_page_footer

    q = query.lower()
    matches = []
    for sid, s in skills_dict.items():
        searchable = " ".join([
            s.get("name", ""),
            s.get("id", ""),
            s.get("description", ""),
            s.get("category", ""),
            " ".join(s.get("bonus_per_level", {}).keys()),
        ]).lower()
        if q in searchable:
            matches.append(s)

    if not matches:
        print(f"No skills matching '{query}'.")
        return

    matches.sort(key=lambda x: (x.get("category", ""), x.get("name", "")))
    page_matches, total, total_pages, page = paginate(matches, limit, page)

    print(f"Found {total} skill(s) matching '{query}':\n")
    for s in page_matches:
        sid = s.get("id", "?")
        name = s.get("name", "?")
        cat = s.get("category", "?")
        max_lvl = s.get("max_level", "?")
        desc = s.get("description", "")

        progress = ""
        if sid in player_map:
            ps = player_map[sid]
            progress = f"  L{ps.get('level', 0)}/{max_lvl}"
        else:
            progress = f"  (max L{max_lvl})"

        print(f"  [{cat}] {name}{progress}")
        if desc:
            print(f"    {desc}")

        reqs = s.get("required_skills") or {}
        if reqs:
            parts = [f"{r} L{l}" for r, l in sorted(reqs.items())]
            print(f"    Requires: {', '.join(parts)}")

        bonuses = s.get("bonus_per_level", {})
        if bonuses:
            parts = [f"{k}: +{v}/lvl" for k, v in sorted(bonuses.items())]
            print(f"    Bonuses: {', '.join(parts)}")

        print(f"    id: {sid}")
        print()
    print_page_footer(total, total_pages, page, limit)


def _do_skill_trace(query, by_id, player_map):
    """Trace the full prerequisite tree for a skill."""
    # Find the skill
    target = None
    if query in by_id:
        target = query
    else:
        # Fuzzy match
        q = query.lower()
        candidates = [sid for sid, s in by_id.items()
                       if q in sid.lower() or q in s.get("name", "").lower()]
        if len(candidates) == 1:
            target = candidates[0]
        elif candidates:
            print("Ambiguous \u2014 did you mean one of these?")
            for c in sorted(candidates):
                s = by_id[c]
                print(f"  {s.get('name', c)} (id: {c})")
            return
        else:
            print(f"No skill matching '{query}'. Try: sm query-skills --search {query}")
            return

    skill = by_id[target]
    tree = _trace_skill_tree(target, by_id)
    lines = _render_skill_tree(tree, by_id, player_map)

    print(f"Prerequisite tree for {skill.get('name', target)}:\n")
    for line in lines:
        print(line)

    # Show what this skill unlocks at each level
    print(f"\n{'-' * 40}")
    print("Unlocks at each level:")
    found_any = False
    for lvl in range(1, (skill.get("max_level") or 10) + 1):
        unlocks = _find_unlocks(target, lvl, by_id)
        # Filter to exactly this level (not lower)
        exact = [u for u in unlocks if (u.get("required_skills") or {}).get(target) == lvl]
        if exact:
            found_any = True
            names = [u.get("name", u.get("id", "?")) for u in exact]
            print(f"  L{lvl}: {', '.join(names)}")
    if not found_any:
        print("  (none \u2014 this is a leaf skill)")

    # XP table
    xp_levels = skill.get("xp_per_level", [])
    if xp_levels:
        print(f"\n{'-' * 40}")
        print("XP requirements:")
        for i, xp in enumerate(xp_levels):
            lvl = i + 1
            marker = ""
            if target in player_map:
                ps = player_map[target]
                if ps.get("level", 0) >= lvl:
                    marker = " \u2713"
                elif ps.get("level", 0) == lvl - 1:
                    marker = f" \u2190 ({ps.get('current_xp', 0)}/{xp} XP)"
            print(f"  L{lvl}: {xp} XP{marker}")


def _do_my_skills(player_skills, by_id, dependents, limit=10, page=1):
    """Show only trained skills with progress and next unlocks."""
    from spacemolt.commands import paginate, print_page_footer

    if not player_skills:
        print("No skills trained yet. Start mining, trading, or fighting to gain XP!")
        return

    sorted_skills = sorted(player_skills, key=lambda s: (-s.get("level", 0), -s.get("current_xp", 0)))
    page_skills, total, total_pages, page = paginate(sorted_skills, limit, page)
    print(f"Trained skills ({total}):\n")

    for ps in page_skills:
        sid = ps.get("skill_id") or ps.get("id", "?")
        name = ps.get("name", sid)
        lvl = ps.get("level", 0)
        max_lvl = ps.get("max_level") or (by_id.get(sid, {}).get("max_level", "?"))
        xp = ps.get("current_xp", 0)
        next_xp = ps.get("next_level_xp", "?")

        # Progress bar
        bar = ""
        if isinstance(next_xp, (int, float)) and next_xp > 0:
            pct = min(xp / next_xp, 1.0)
            filled = int(pct * 20)
            bar = f"  [{'█' * filled}{'░' * (20 - filled)}] {pct:.0%}"

        print(f"  {name}: L{lvl}/{max_lvl} ({xp}/{next_xp} XP){bar}")

        # What will next levels unlock?
        next_unlocks = []
        for dep in (dependents.get(sid) or []):
            dep_reqs = dep.get("required_skills", {})
            req_lvl = dep_reqs.get(sid, 0)
            if req_lvl > lvl:
                next_unlocks.append(f"{dep.get('name', '?')} @L{req_lvl}")
        if next_unlocks:
            print(f"    \u2192 next unlocks: {', '.join(next_unlocks)}")
    print_page_footer(total, total_pages, page, limit)


# ---------------------------------------------------------------------------
# Hierarchical command router
# ---------------------------------------------------------------------------

def cmd_skills_router(api, args):
    """Route skills subcommands to appropriate handlers."""
    subcmd = getattr(args, "skills_cmd", None)

    if not subcmd:
        # No subcommand: show trained skills (default view)
        cmd_skills(api, args)
    elif subcmd == "list":
        cmd_skills(api, args)
    elif subcmd == "query":
        cmd_query_skills(api, args)
    elif subcmd == "inspect":
        # Map to cmd_skill
        args.skill_id = getattr(args, "skill_id_inspect", None)
        cmd_skill(api, args)
    else:
        print(f"Unknown skills subcommand: {subcmd}", file=sys.stderr)
        sys.exit(1)
