import json
import os


def _load_openapi():
    spec_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
        "spec",
        "openapi.json",
    )
    with open(spec_path) as f:
        return json.load(f)


def cmd_schema(api, args):
    """Show the API schema for a given command/endpoint."""
    command = getattr(args, "schema_command", None)
    if not command:
        print("Usage: sm schema <command>")
        return

    spec = _load_openapi()
    paths = spec.get("paths", {})

    # Normalize: try as-is, with leading slash, and with underscores
    candidates = [
        command,
        f"/{command}",
        command.replace("-", "_"),
        f"/{command.replace('-', '_')}",
    ]

    path_info = None
    matched_path = None
    for c in candidates:
        if c in paths:
            path_info = paths[c]
            matched_path = c
            break

    if not path_info:
        # List close matches
        available = sorted(k.lstrip("/") for k in paths)
        matches = [a for a in available if command.replace("-", "_") in a or command in a]
        print(f"No schema found for '{command}'.")
        if matches:
            print(f"Did you mean: {', '.join(matches[:5])}")
        else:
            print(f"Run 'sm schema --list' to see all endpoints.")
        return

    as_json = getattr(args, "json", False)

    if as_json:
        print(json.dumps({matched_path: path_info}, indent=2))
        return

    # Pretty-print the schema
    endpoint_name = matched_path.lstrip("/")
    for method, details in path_info.items():
        print(f"=== {method.upper()} {matched_path} ===")
        desc = details.get("description", "")
        if desc:
            print(f"\n{desc}\n")

        # Request body schema
        body = details.get("requestBody", {})
        schema = (
            body.get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        props = schema.get("properties", {})
        required = set(schema.get("required", []))

        if props:
            print("Parameters:")
            for name, info in props.items():
                req = " (required)" if name in required else ""
                ptype = info.get("type", "")
                desc = info.get("description", "")
                enum = info.get("enum")
                line = f"  {name}: {ptype}{req}"
                if enum:
                    line += f"  [{', '.join(str(e) for e in enum)}]"
                if desc:
                    line += f"\n    {desc}"
                print(line)

        # Response schema
        resp_200 = details.get("responses", {}).get("200", {})
        resp_schema = (
            resp_200.get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        result_props = _extract_result_props(resp_schema)
        if result_props:
            print("\nResult fields:")
            _print_props(result_props, indent=2)


def cmd_schema_list(api, args):
    """List all API endpoints."""
    spec = _load_openapi()
    paths = spec.get("paths", {})
    for path in sorted(paths):
        name = path.lstrip("/")
        details = paths[path]
        for method, info in details.items():
            desc = info.get("description", "")
            # First sentence only
            short = desc.split(".")[0].strip() if desc else ""
            if len(short) > 80:
                short = short[:77] + "..."
            print(f"  {name:30s} {short}")


def _extract_result_props(schema):
    """Extract result properties from an APIResponse allOf schema."""
    all_of = schema.get("allOf", [])
    for entry in all_of:
        props = entry.get("properties", {})
        if "result" in props:
            result = props["result"]
            return result.get("properties", {})
    # Direct properties
    return schema.get("properties", {}).get("result", {}).get("properties", {})


def _print_props(props, indent=2):
    prefix = " " * indent
    for name, info in props.items():
        ptype = info.get("type", "")
        desc = info.get("description", "")
        line = f"{prefix}{name}: {ptype}"
        if desc:
            line += f"  — {desc}"
        print(line)
        # Nested object
        nested = info.get("properties")
        if nested:
            _print_props(nested, indent + 2)
        # Array items
        items = info.get("items", {})
        if items.get("properties"):
            _print_props(items["properties"], indent + 2)
