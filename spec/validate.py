#!/usr/bin/env python3
"""
Cross-reference the OpenAPI spec against our CLI implementation.

This script:
1. Parses spec/openapi.json to extract all available endpoints
2. Reads spacemolt/commands/passthrough.py to find ENDPOINT_ARGS
3. Compares and reports:
   - Endpoints in spec but not implemented
   - Endpoints implemented but not in spec (deprecated/custom)
   - Parameter mismatches (name, type, required/optional)

Usage:
    python3 spec/validate.py [--verbose] [--strict]

Options:
    --verbose   Show detailed parameter comparisons
    --strict    Exit with error code if any mismatches found
"""

import json
import os
import re
import sys
from pathlib import Path


def load_openapi_spec(spec_path):
    """Load and parse the OpenAPI JSON spec."""
    with open(spec_path) as f:
        return json.load(f)


def extract_endpoints_from_spec(spec):
    """
    Extract endpoint definitions from OpenAPI spec.

    Returns: dict mapping endpoint_name -> {params: [...], description: str, rate_limited: bool}
    """
    endpoints = {}

    for path, methods in spec.get("paths", {}).items():
        # SpaceMolt uses POST for everything
        if "post" not in methods:
            continue

        post_def = methods["post"]
        operation_id = post_def.get("operationId", path.strip("/"))
        description = post_def.get("description", "")

        # Check if rate-limited (mutation command)
        rate_limited = "rate limited" in description.lower() or "mutation command" in description.lower()

        # Extract parameters from requestBody schema
        params = []
        request_body = post_def.get("requestBody", {})
        content = request_body.get("content", {})
        json_content = content.get("application/json", {})
        schema = json_content.get("schema", {})
        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))

        for param_name, param_def in properties.items():
            param_type = param_def.get("type", "string")
            param_desc = param_def.get("description", "")
            is_required = param_name in required_fields

            params.append({
                "name": param_name,
                "type": param_type,
                "required": is_required,
                "description": param_desc,
            })

        endpoints[operation_id] = {
            "params": params,
            "description": description.split("\n")[0][:100],  # First line, truncated
            "rate_limited": rate_limited,
        }

    return endpoints


def extract_endpoints_from_implementation():
    """
    Parse spacemolt/commands/passthrough.py to extract ENDPOINT_ARGS.

    Returns: dict mapping endpoint_name -> list of param specs
    """
    script_dir = Path(__file__).parent
    passthrough_path = script_dir.parent / "spacemolt" / "commands" / "passthrough.py"

    if not passthrough_path.exists():
        print(f"ERROR: Cannot find {passthrough_path}", file=sys.stderr)
        sys.exit(1)

    with open(passthrough_path) as f:
        content = f.read()

    # Extract ENDPOINT_ARGS dictionary
    # This is a bit hacky but works for the current structure
    match = re.search(r'ENDPOINT_ARGS\s*=\s*\{(.+?)\n\}', content, re.DOTALL)
    if not match:
        print("ERROR: Cannot find ENDPOINT_ARGS in passthrough.py", file=sys.stderr)
        sys.exit(1)

    endpoint_args_text = match.group(1)

    # Parse endpoint entries: "endpoint_name": ["arg1:type", "arg2?:type", ...],
    endpoints = {}
    for line in endpoint_args_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Match: "endpoint": [...],
        entry_match = re.match(r'"([^"]+)":\s*\[([^\]]*)\]', line)
        if entry_match:
            endpoint_name = entry_match.group(1)
            args_text = entry_match.group(2)

            # Parse args like "arg:int", "optional?:str"
            args = []
            if args_text.strip():
                for arg in re.findall(r'"([^"]+)"', args_text):
                    args.append(arg.strip())

            endpoints[endpoint_name] = args

    return endpoints


def parse_arg_spec(arg_spec):
    """
    Parse an arg spec like "target_system:str", "quantity?:int", or "target_id?".

    Returns: {name: str, type: str, required: bool}
    """
    # Check for optional marker (handles both "param?" and "param?:type")
    optional = arg_spec.endswith("?") or (":not" in arg_spec and arg_spec.split(":")[0].endswith("?"))

    # Handle "param?:type" format
    if ":" in arg_spec:
        name_part, arg_type = arg_spec.split(":", 1)
        name = name_part.rstrip("?")
        optional = name_part.endswith("?")
    else:
        # Handle "param?" or "param" format
        name = arg_spec.rstrip("?")
        arg_type = "str"
        optional = arg_spec.endswith("?")

    return {
        "name": name,
        "type": arg_type,
        "required": not optional,
    }


def compare_endpoints(spec_endpoints, impl_endpoints, verbose=False):
    """
    Compare spec endpoints against implementation.

    Returns: (missing, extra, mismatches)
    """
    spec_names = set(spec_endpoints.keys())
    impl_names = set(impl_endpoints.keys())

    missing = spec_names - impl_names  # In spec but not implemented
    extra = impl_names - spec_names    # Implemented but not in spec
    common = spec_names & impl_names

    mismatches = []

    for endpoint in sorted(common):
        spec_def = spec_endpoints[endpoint]
        impl_args = impl_endpoints[endpoint]

        spec_params = {p["name"]: p for p in spec_def["params"]}
        impl_params = {parse_arg_spec(a)["name"]: parse_arg_spec(a) for a in impl_args}

        spec_param_names = set(spec_params.keys())
        impl_param_names = set(impl_params.keys())

        # Check for parameter differences
        missing_params = spec_param_names - impl_param_names
        extra_params = impl_param_names - spec_param_names

        # Check for type/required mismatches
        type_mismatches = []
        for param_name in spec_param_names & impl_param_names:
            spec_p = spec_params[param_name]
            impl_p = impl_params[param_name]

            # Type mapping: OpenAPI -> our types
            type_map = {
                "string": "str",
                "integer": "int",
                "boolean": "bool",
                "number": "int",  # Could be float, but we use int
            }
            expected_type = type_map.get(spec_p["type"], spec_p["type"])

            if impl_p["type"] != expected_type:
                type_mismatches.append(f"{param_name}: {impl_p['type']} (ours) vs {expected_type} (spec)")

            if impl_p["required"] != spec_p["required"]:
                req_str = "required" if spec_p["required"] else "optional"
                impl_req_str = "required" if impl_p["required"] else "optional"
                type_mismatches.append(f"{param_name}: {impl_req_str} (ours) vs {req_str} (spec)")

        if missing_params or extra_params or type_mismatches:
            mismatches.append({
                "endpoint": endpoint,
                "missing_params": missing_params,
                "extra_params": extra_params,
                "type_mismatches": type_mismatches,
            })

    return missing, extra, mismatches


def main():
    verbose = "--verbose" in sys.argv
    strict = "--strict" in sys.argv

    script_dir = Path(__file__).parent
    spec_path = script_dir / "openapi.json"

    if not spec_path.exists():
        print(f"ERROR: OpenAPI spec not found at {spec_path}", file=sys.stderr)
        sys.exit(1)

    print("Loading OpenAPI spec...")
    spec = load_openapi_spec(spec_path)
    spec_endpoints = extract_endpoints_from_spec(spec)

    print(f"Found {len(spec_endpoints)} endpoints in spec")

    print("\nParsing implementation (ENDPOINT_ARGS)...")
    impl_endpoints = extract_endpoints_from_implementation()

    print(f"Found {len(impl_endpoints)} endpoints in implementation")

    print("\n" + "="*80)
    print("CROSS-REFERENCE REPORT")
    print("="*80)

    missing, extra, mismatches = compare_endpoints(spec_endpoints, impl_endpoints, verbose)

    has_issues = False

    # Missing endpoints (in spec but not implemented)
    if missing:
        has_issues = True
        print(f"\n❌ MISSING: {len(missing)} endpoints in spec but NOT implemented:")
        for endpoint in sorted(missing):
            spec_def = spec_endpoints[endpoint]
            rate_note = " [RATE-LIMITED]" if spec_def["rate_limited"] else ""
            print(f"  - {endpoint}{rate_note}")
            if verbose:
                print(f"    {spec_def['description']}")
                for param in spec_def["params"]:
                    req = "required" if param["required"] else "optional"
                    print(f"      {param['name']} ({param['type']}, {req})")
    else:
        print("\n✅ All spec endpoints are implemented")

    # Extra endpoints (implemented but not in spec)
    if extra:
        has_issues = True
        print(f"\n⚠️  EXTRA: {len(extra)} endpoints implemented but NOT in spec (custom/deprecated?):")
        for endpoint in sorted(extra):
            print(f"  - {endpoint}")
            if verbose:
                print(f"    Args: {impl_endpoints[endpoint]}")
    else:
        print("\n✅ No extra/custom endpoints beyond spec")

    # Mismatches (parameter differences)
    if mismatches:
        has_issues = True
        print(f"\n⚠️  MISMATCHES: {len(mismatches)} endpoints with parameter differences:")
        for mismatch in mismatches:
            print(f"  - {mismatch['endpoint']}:")
            if mismatch["missing_params"]:
                print(f"    Missing params: {', '.join(mismatch['missing_params'])}")
            if mismatch["extra_params"]:
                print(f"    Extra params: {', '.join(mismatch['extra_params'])}")
            if mismatch["type_mismatches"]:
                print(f"    Type/required mismatches:")
                for tm in mismatch["type_mismatches"]:
                    print(f"      {tm}")
    else:
        print("\n✅ All implemented endpoints match spec parameters")

    print("\n" + "="*80)

    if has_issues:
        print("\n⚠️  Issues found. Review and update implementation or spec.")
        if strict:
            sys.exit(1)
    else:
        print("\n✅ All checks passed! Implementation matches spec.")

    print(f"\nSummary:")
    print(f"  Spec endpoints: {len(spec_endpoints)}")
    print(f"  Implemented: {len(impl_endpoints)}")
    print(f"  Missing: {len(missing)}")
    print(f"  Extra: {len(extra)}")
    print(f"  Mismatches: {len(mismatches)}")


if __name__ == "__main__":
    main()
