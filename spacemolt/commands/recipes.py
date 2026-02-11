import json


__all__ = [
    "cmd_recipes", "cmd_query_recipes", "cmd_recipes_router",
    "_normalize_recipes", "_build_recipe_indexes", "_recipe_skill_tier",
    "_recipe_one_line", "_trace_ingredient_tree", "_render_tree",
    "_collect_raw_totals",
]


def cmd_recipes(api, args):
    from spacemolt.commands import paginate, print_page_footer

    as_json = getattr(args, "json", False)
    resp = api._post("get_recipes")
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    r = resp.get("result", {})
    recipes = r.get("recipes", {})
    if not recipes:
        print("No recipes available.")
        return

    all_recipes = list(recipes.values()) if isinstance(recipes, dict) else list(recipes)
    limit = getattr(args, "limit", 10)
    page = getattr(args, "page", 1)
    page_recipes, total, total_pages, page = paginate(all_recipes, limit, page)
    for rec in page_recipes:
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

    print_page_footer(total, total_pages, page, limit)


# --- Recipe query / progression diagram ---

def _normalize_recipes(raw_recipes):
    """Turn the API recipes response (dict-keyed or list) into a list."""
    if isinstance(raw_recipes, dict):
        return list(raw_recipes.values())
    return list(raw_recipes)


def _build_recipe_indexes(recipe_list):
    """Build lookup dicts: output_item->recipe, recipe_id->recipe."""
    by_output = {}  # item_id -> recipe
    by_id = {}      # recipe_id -> recipe
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
    """Format a recipe as: inputs -> outputs (with quantities)."""
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

    connector = "\u2514\u2500\u2500 " if is_last else "\u251c\u2500\u2500 "
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

    child_prefix = prefix + ("    " if is_last else "\u2502   ")
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
    limit = getattr(args, "limit", 10)
    page = getattr(args, "page", 1)

    if trace_target:
        _do_trace(trace_target, by_output, recipe_list)
    elif search_query:
        _do_search(search_query, recipe_list, limit=limit, page=page)
    else:
        _do_progression(recipe_list, by_output, limit=limit, page=page)


def _do_progression(recipe_list, by_output, limit=10, page=1):
    """Show recipes grouped by skill tier, with flow arrows."""
    from spacemolt.commands import paginate, print_page_footer

    # Flatten into a sorted list of (tier_sort_key, tier_label, category, recipe)
    entries = []
    for r in recipe_list:
        tier_lvl, tier_label = _recipe_skill_tier(r)
        tier_key = tier_label or "No requirements"
        cat = r.get("category", "Other")
        entries.append((tier_lvl, tier_key, cat, r))

    entries.sort(key=lambda e: (e[0], e[1], e[2], e[3].get("name", "")))

    page_entries, total, total_pages, page = paginate(entries, limit, page)

    prev_tier = None
    prev_cat = None
    for tier_lvl, tier_key, cat, r in page_entries:
        if tier_key != prev_tier:
            print(f"\n{'═' * 60}")
            print(f"  {tier_key}" if tier_key != "No requirements" else "  No skill requirements")
            print(f"{'═' * 60}")
            prev_tier = tier_key
            prev_cat = None

        if cat != prev_cat:
            print(f"\n  [{cat}]")
            prev_cat = cat

        name = r.get("name", "?")
        rid = r.get("id", "")
        flow = _recipe_one_line(r)
        crafted_inputs = [
            i["item_id"] for i in r.get("inputs", [])
            if i.get("item_id") in by_output
        ]
        chain_marker = " \u25c6" if crafted_inputs else ""
        print(f"    {name}{chain_marker}")
        print(f"      {flow}")
        if rid:
            print(f"      id: {rid}")

    # Legend
    print(f"\n{'─' * 60}")
    print("  \u25c6 = has crafted ingredients (use --trace to expand)")
    print_page_footer(total, total_pages, page, limit)


def _do_search(query, recipe_list, limit=10, page=1):
    """Filter recipes by name, id, or item_id."""
    from spacemolt.commands import paginate, print_page_footer

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

    matches.sort(key=lambda x: x.get("name", ""))
    page_matches, total, total_pages, page = paginate(matches, limit, page)

    print(f"Found {total} recipe(s) matching '{query}':\n")
    for r in page_matches:
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
    print_page_footer(total, total_pages, page, limit)


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


# ---------------------------------------------------------------------------
# Hierarchical command router
# ---------------------------------------------------------------------------

def cmd_recipes_router(api, args):
    """Route recipes subcommands to appropriate handlers."""
    import sys
    from spacemolt.commands.passthrough import cmd_passthrough

    subcmd = getattr(args, "recipes_cmd", None)

    if not subcmd:
        # No subcommand: show recipes list (default view)
        cmd_recipes(api, args)
    elif subcmd == "list":
        cmd_recipes(api, args)
    elif subcmd == "query":
        # Map query subcommand args to cmd_query_recipes
        args.trace = getattr(args, "trace_query", None)
        args.search = getattr(args, "search_query", None)
        cmd_query_recipes(api, args)
    elif subcmd == "craft":
        # Passthrough to craft endpoint
        recipe_id = getattr(args, "recipe_id", None)
        count = getattr(args, "count", None)
        extra_args = [recipe_id] if recipe_id else []
        if count:
            extra_args.append(str(count))
        as_json = getattr(args, "json", False)
        cmd_passthrough(api, "craft", extra_args, as_json=as_json)
    else:
        print(f"Unknown recipes subcommand: {subcmd}", file=sys.stderr)
        sys.exit(1)
