#!/usr/bin/env python3
"""
Detect API drift between the live SpaceMolt OpenAPI spec, the local spec copy,
and the CLI implementation.

Checks performed:
1. Local spec staleness  -- is spec/openapi.json behind the live server?
2. New endpoints          -- live spec has endpoints missing from ENDPOINT_ARGS
3. Deleted endpoints      -- ENDPOINT_ARGS has endpoints not in the live spec
4. Parameter changes      -- added/removed params, type changes, required/optional
5. Undocumented API calls -- custom commands calling api._post() with endpoints
                             not present in the live spec

Usage:
    python3 spec/drift_check.py            # human-readable report
    python3 spec/drift_check.py --json     # machine-readable JSON output
    python3 spec/drift_check.py --strict   # exit code 1 on any drift

Requires only stdlib (no pip dependencies).
"""

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

LIVE_SPEC_URL = "https://game.spacemolt.com/api/openapi.json"
FETCH_TIMEOUT = 15  # seconds


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_live_spec():
    """Download the live OpenAPI spec. Returns (dict, raw_bytes) or raises."""
    req = urllib.request.Request(
        LIVE_SPEC_URL,
        headers={"User-Agent": "spacemolt-drift-check/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not fetch live spec from {LIVE_SPEC_URL}: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"Network error fetching {LIVE_SPEC_URL}: {exc}") from exc
    return json.loads(raw), raw


def load_local_spec(spec_path):
    """Load spec/openapi.json.  Returns (dict, raw_bytes) or (None, None)."""
    if not spec_path.exists():
        return None, None
    raw = spec_path.read_bytes()
    return json.loads(raw), raw


# ---------------------------------------------------------------------------
# Parsing OpenAPI spec -> endpoint map
# ---------------------------------------------------------------------------

def _extract_description_params(description):
    """
    Many SpaceMolt endpoints document their parameters only in the description
    as JSON examples like:  "payload": {"amount": 1000, "item_id": "ore"}

    Returns a list of param dicts extracted from those examples, or [].
    """
    params = []
    # Look for JSON payload examples in the description
    # Patterns: "payload": {...}  or  `{"type": "...", "payload": {...}}`
    payload_patterns = [
        r'"payload"\s*:\s*\{([^}]+)\}',
        r'`\{[^`]*"payload"\s*:\s*\{([^}]+)\}',
    ]
    for pattern in payload_patterns:
        match = re.search(pattern, description)
        if match:
            payload_text = match.group(1)
            # Extract "key": value pairs
            for kv in re.finditer(r'"(\w+)"\s*:\s*("(?:[^"\\]|\\.)*"|\d+(?:\.\d+)?|true|false|\[.*?\]|\{.*?\})', payload_text):
                name = kv.group(1)
                value = kv.group(2)
                # Infer type from the example value
                if value.startswith('"'):
                    ptype = "string"
                elif value in ("true", "false"):
                    ptype = "boolean"
                elif "." in value:
                    ptype = "number"
                elif re.match(r'^\d+$', value):
                    ptype = "integer"
                elif value.startswith("["):
                    ptype = "array"
                else:
                    ptype = "string"
                params.append({
                    "name": name,
                    "type": ptype,
                    "required": False,  # Can't infer required from examples
                    "description": "(extracted from description example)",
                    "from_description": True,
                })
            break  # Use first match only
    return params


def extract_spec_endpoints(spec):
    """
    Parse an OpenAPI spec dict into:
      { operation_id: { params: [...], description: str, tags: [...] } }
    """
    endpoints = {}
    for path, methods in spec.get("paths", {}).items():
        if "post" not in methods:
            continue
        post = methods["post"]
        op_id = post.get("operationId", path.strip("/"))
        description = post.get("description", "")
        tags = post.get("tags", [])

        params = []
        rb = post.get("requestBody", {})
        content = rb.get("content", {})
        json_content = content.get("application/json", {})
        schema = json_content.get("schema", {})
        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))

        for pname, pdef in properties.items():
            params.append({
                "name": pname,
                "type": pdef.get("type", "string"),
                "required": pname in required_fields,
                "description": pdef.get("description", ""),
                "from_description": False,
            })

        # If the spec lacks a formal requestBody, try extracting from description
        if not params:
            params = _extract_description_params(description)

        endpoints[op_id] = {
            "params": params,
            "description": description.split("\n")[0][:120],
            "tags": tags,
        }
    return endpoints


# ---------------------------------------------------------------------------
# Parsing ENDPOINT_ARGS from passthrough.py
# ---------------------------------------------------------------------------

def extract_impl_endpoints():
    """
    Parse ENDPOINT_ARGS from spacemolt/commands/passthrough.py.
    Returns { endpoint_name: [ "arg_spec", ... ] }
    """
    script_dir = Path(__file__).parent
    passthrough_path = script_dir.parent / "spacemolt" / "commands" / "passthrough.py"
    if not passthrough_path.exists():
        raise FileNotFoundError(f"Cannot find {passthrough_path}")

    content = passthrough_path.read_text()
    match = re.search(r'ENDPOINT_ARGS\s*=\s*\{(.+?)\n\}', content, re.DOTALL)
    if not match:
        raise ValueError("Cannot find ENDPOINT_ARGS in passthrough.py")

    endpoint_args_text = match.group(1)
    endpoints = {}
    for line in endpoint_args_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        entry_match = re.match(r'"([^"]+)":\s*\[([^\]]*)\]', line)
        if entry_match:
            endpoint_name = entry_match.group(1)
            args_text = entry_match.group(2)
            args = []
            if args_text.strip():
                for arg in re.findall(r'"([^"]+)"', args_text):
                    args.append(arg.strip())
            endpoints[endpoint_name] = args
    return endpoints


def parse_arg_spec(arg_spec):
    """Parse 'target_id?:int' -> {name, type, required}."""
    if ":" in arg_spec:
        name_part, arg_type = arg_spec.split(":", 1)
        name = name_part.rstrip("?")
        optional = name_part.endswith("?")
    else:
        name = arg_spec.rstrip("?")
        arg_type = "str"
        optional = arg_spec.endswith("?")
    return {"name": name, "type": arg_type, "required": not optional}


# ---------------------------------------------------------------------------
# Scanning custom commands for undocumented _post() calls
# ---------------------------------------------------------------------------

def extract_post_calls():
    """
    Scan spacemolt/commands/*.py and spacemolt/cli.py for api._post("...")
    calls that reference API endpoints directly.

    Returns { endpoint_name: [source_file, ...] }
    """
    script_dir = Path(__file__).parent
    base = script_dir.parent / "spacemolt"
    files_to_scan = list((base / "commands").glob("*.py"))
    cli_path = base / "cli.py"
    if cli_path.exists():
        files_to_scan.append(cli_path)

    calls = {}
    # Match api._post("endpoint_name"   (with or without extra args)
    pattern = re.compile(r'api\._post\(\s*"(\w+)"')

    for fpath in files_to_scan:
        content = fpath.read_text()
        for m in pattern.finditer(content):
            ep = m.group(1)
            relpath = str(fpath.relative_to(script_dir.parent))
            calls.setdefault(ep, []).append(relpath)

    return calls


# ---------------------------------------------------------------------------
# Comparison logic
# ---------------------------------------------------------------------------

TYPE_MAP = {
    "string": "str",
    "integer": "int",
    "boolean": "bool",
    "number": "int",
    "array": "str",   # arrays are passed as JSON strings in CLI
    "object": "str",  # objects are passed as JSON strings in CLI
}


def compare_params(spec_params, impl_arg_specs):
    """
    Compare spec params against implementation arg specs for a single endpoint.
    Returns a dict of changes (empty dict means no drift).
    """
    changes = {}

    spec_map = {p["name"]: p for p in spec_params}
    impl_map = {}
    for arg_spec in impl_arg_specs:
        parsed = parse_arg_spec(arg_spec)
        impl_map[parsed["name"]] = parsed

    spec_names = set(spec_map.keys())
    impl_names = set(impl_map.keys())

    # Skip comparison for description-extracted params (low confidence)
    all_from_desc = all(p.get("from_description") for p in spec_params) if spec_params else False

    added_in_spec = spec_names - impl_names
    removed_from_spec = impl_names - spec_names

    if added_in_spec:
        changes["params_added_in_spec"] = sorted(added_in_spec)
    if removed_from_spec:
        changes["params_only_in_impl"] = sorted(removed_from_spec)

    # Type and required/optional changes on common params
    type_changes = []
    required_changes = []
    for name in sorted(spec_names & impl_names):
        sp = spec_map[name]
        ip = impl_map[name]

        if not all_from_desc:
            expected_type = TYPE_MAP.get(sp["type"], sp["type"])
            if ip["type"] != expected_type:
                type_changes.append({
                    "param": name,
                    "spec_type": sp["type"],
                    "impl_type": ip["type"],
                })

            if ip["required"] != sp["required"]:
                required_changes.append({
                    "param": name,
                    "spec_required": sp["required"],
                    "impl_required": ip["required"],
                })

    if type_changes:
        changes["type_changes"] = type_changes
    if required_changes:
        changes["required_changes"] = required_changes

    return changes


def run_checks():
    """
    Execute all drift checks.
    Returns a report dict with all findings.
    """
    report = {
        "live_spec_url": LIVE_SPEC_URL,
        "local_spec_stale": False,
        "local_spec_missing": False,
        "new_endpoints": [],
        "deleted_endpoints": [],
        "param_changes": [],
        "undocumented_api_calls": [],
        "error": None,
        "summary": {},
    }

    # --- Fetch live spec ---
    try:
        live_spec, live_raw = fetch_live_spec()
    except RuntimeError as exc:
        report["error"] = str(exc)
        return report

    live_endpoints = extract_spec_endpoints(live_spec)

    # --- Local spec staleness ---
    script_dir = Path(__file__).parent
    local_spec_path = script_dir / "openapi.json"
    local_spec, local_raw = load_local_spec(local_spec_path)

    if local_spec is None:
        report["local_spec_missing"] = True
    else:
        # Normalize both to sorted JSON for comparison (ignore whitespace diffs)
        live_normalized = json.dumps(live_spec, sort_keys=True)
        local_normalized = json.dumps(local_spec, sort_keys=True)
        if live_normalized != local_normalized:
            report["local_spec_stale"] = True
            # Provide some detail
            local_endpoints = extract_spec_endpoints(local_spec)
            live_ep_set = set(live_endpoints.keys())
            local_ep_set = set(local_endpoints.keys())
            report["local_spec_diff"] = {
                "live_endpoint_count": len(live_ep_set),
                "local_endpoint_count": len(local_ep_set),
                "added_in_live": sorted(live_ep_set - local_ep_set),
                "removed_in_live": sorted(local_ep_set - live_ep_set),
            }

    # --- Parse implementation ---
    try:
        impl_endpoints = extract_impl_endpoints()
    except (FileNotFoundError, ValueError) as exc:
        report["error"] = str(exc)
        return report

    # --- New / deleted endpoints ---
    live_names = set(live_endpoints.keys())
    impl_names = set(impl_endpoints.keys())

    new_eps = sorted(live_names - impl_names)
    deleted_eps = sorted(impl_names - live_names)
    common_eps = live_names & impl_names

    for ep in new_eps:
        info = live_endpoints[ep]
        report["new_endpoints"].append({
            "endpoint": ep,
            "description": info["description"],
            "tags": info["tags"],
            "param_count": len(info["params"]),
            "params": [p["name"] for p in info["params"]],
        })

    for ep in deleted_eps:
        report["deleted_endpoints"].append({
            "endpoint": ep,
            "impl_params": impl_endpoints[ep],
        })

    # --- Parameter changes on common endpoints ---
    for ep in sorted(common_eps):
        changes = compare_params(live_endpoints[ep]["params"], impl_endpoints[ep])
        if changes:
            changes["endpoint"] = ep
            report["param_changes"].append(changes)

    # --- Undocumented api._post() calls ---
    post_calls = extract_post_calls()
    for ep, sources in sorted(post_calls.items()):
        if ep not in live_names:
            # Skip generic passthrough calls (endpoint is a variable)
            # and the session endpoint which is infra, not a game command
            if ep in ("session",):
                continue
            report["undocumented_api_calls"].append({
                "endpoint": ep,
                "called_from": sources,
                "in_endpoint_args": ep in impl_names,
            })

    # --- Summary ---
    report["summary"] = {
        "live_endpoints": len(live_names),
        "impl_endpoints": len(impl_names),
        "new_count": len(report["new_endpoints"]),
        "deleted_count": len(report["deleted_endpoints"]),
        "param_change_count": len(report["param_changes"]),
        "undocumented_count": len(report["undocumented_api_calls"]),
        "local_spec_stale": report["local_spec_stale"],
    }

    return report


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def print_human_report(report):
    """Print a clear, human-readable drift report."""
    print("=" * 72)
    print("  SpaceMolt API Drift Check")
    print("=" * 72)

    if report.get("error"):
        print(f"\nERROR: {report['error']}")
        return

    s = report["summary"]
    print(f"\nLive spec: {report['live_spec_url']}")
    print(f"Live endpoints: {s['live_endpoints']}  |  Implemented: {s['impl_endpoints']}")

    has_drift = False

    # Local spec staleness
    if report.get("local_spec_missing"):
        has_drift = True
        print("\n[!] LOCAL SPEC MISSING")
        print("    spec/openapi.json not found. Run:")
        print(f"    curl -o spec/openapi.json {LIVE_SPEC_URL}")

    elif report.get("local_spec_stale"):
        has_drift = True
        diff = report.get("local_spec_diff", {})
        print("\n[!] LOCAL SPEC IS STALE")
        print(f"    Live has {diff.get('live_endpoint_count', '?')} endpoints, "
              f"local has {diff.get('local_endpoint_count', '?')}")
        added = diff.get("added_in_live", [])
        removed = diff.get("removed_in_live", [])
        if added:
            print(f"    New in live: {', '.join(added[:10])}"
                  + (f" (+{len(added)-10} more)" if len(added) > 10 else ""))
        if removed:
            print(f"    Removed from live: {', '.join(removed[:10])}"
                  + (f" (+{len(removed)-10} more)" if len(removed) > 10 else ""))
        print("    Update with:")
        print(f"    curl -o spec/openapi.json {LIVE_SPEC_URL}")
    else:
        print("\n[OK] Local spec is up to date")

    # New endpoints
    new_eps = report.get("new_endpoints", [])
    if new_eps:
        has_drift = True
        print(f"\n[!] NEW ENDPOINTS ({len(new_eps)}) -- in live spec but not in ENDPOINT_ARGS:")
        for ep in new_eps:
            tags = f" [{', '.join(ep['tags'])}]" if ep["tags"] else ""
            params = f"  params: {', '.join(ep['params'])}" if ep["params"] else ""
            print(f"    + {ep['endpoint']}{tags}{params}")
            if ep["description"]:
                desc = ep["description"]
                if len(desc) > 90:
                    desc = desc[:87] + "..."
                print(f"      {desc}")
    else:
        print("\n[OK] No new endpoints in live spec")

    # Deleted endpoints
    deleted_eps = report.get("deleted_endpoints", [])
    if deleted_eps:
        has_drift = True
        print(f"\n[!] DELETED ENDPOINTS ({len(deleted_eps)}) -- in ENDPOINT_ARGS but not in live spec:")
        for ep in deleted_eps:
            params_str = f"  [{', '.join(ep['impl_params'])}]" if ep["impl_params"] else ""
            print(f"    - {ep['endpoint']}{params_str}")
    else:
        print("\n[OK] No deleted endpoints")

    # Parameter changes
    param_changes = report.get("param_changes", [])
    if param_changes:
        has_drift = True
        print(f"\n[!] PARAMETER CHANGES ({len(param_changes)}) -- differences on common endpoints:")
        for change in param_changes:
            print(f"    ~ {change['endpoint']}:")
            if "params_added_in_spec" in change:
                print(f"      New params in spec: {', '.join(change['params_added_in_spec'])}")
            if "params_only_in_impl" in change:
                print(f"      Extra params in impl: {', '.join(change['params_only_in_impl'])}")
            for tc in change.get("type_changes", []):
                print(f"      Type: {tc['param']}  spec={tc['spec_type']}  impl={tc['impl_type']}")
            for rc in change.get("required_changes", []):
                spec_req = "required" if rc["spec_required"] else "optional"
                impl_req = "required" if rc["impl_required"] else "optional"
                print(f"      Required: {rc['param']}  spec={spec_req}  impl={impl_req}")
    else:
        print("\n[OK] No parameter changes on common endpoints")

    # Undocumented API calls
    undoc = report.get("undocumented_api_calls", [])
    if undoc:
        has_drift = True
        print(f"\n[!] UNDOCUMENTED API CALLS ({len(undoc)}) -- _post() endpoints not in live spec:")
        for call in undoc:
            in_ea = " (in ENDPOINT_ARGS)" if call["in_endpoint_args"] else ""
            sources = ", ".join(call["called_from"])
            print(f"    ? {call['endpoint']}{in_ea}  -- called from: {sources}")
    else:
        print("\n[OK] All api._post() endpoints are in the live spec")

    # Final summary
    print("\n" + "-" * 72)
    total_issues = (s["new_count"] + s["deleted_count"] + s["param_change_count"]
                    + s["undocumented_count"] + (1 if s["local_spec_stale"] else 0))
    if total_issues == 0:
        print("No drift detected. Implementation matches the live spec.")
    else:
        print(f"Drift detected: {total_issues} issue(s) found.")
        print(f"  New endpoints:       {s['new_count']}")
        print(f"  Deleted endpoints:   {s['deleted_count']}")
        print(f"  Parameter changes:   {s['param_change_count']}")
        print(f"  Undocumented calls:  {s['undocumented_count']}")
        if s["local_spec_stale"]:
            print(f"  Local spec stale:    yes")

    return has_drift


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    json_output = "--json" in sys.argv
    strict = "--strict" in sys.argv

    report = run_checks()

    if json_output:
        print(json.dumps(report, indent=2))
    else:
        has_drift = print_human_report(report)

    if report.get("error"):
        sys.exit(2)

    if strict:
        s = report.get("summary", {})
        total = (s.get("new_count", 0) + s.get("deleted_count", 0)
                 + s.get("param_change_count", 0) + s.get("undocumented_count", 0)
                 + (1 if s.get("local_spec_stale") else 0))
        if total > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
