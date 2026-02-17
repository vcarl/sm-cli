#!/usr/bin/env python3
"""
Generate FORMAT_SCHEMAS entries from the OpenAPI spec.

Currently a stub — the OpenAPI spec lacks response schemas (all endpoints
return a generic APIResponse with untyped `result`).  When response schemas
land, this script will:

1. Load spec/openapi.json
2. For each endpoint with a response schema, generate a FORMAT_SCHEMAS entry
3. Output Python source (or JSON) for review/commit
4. Support a manual overrides file (hints, labels, field ordering)

Usage:
    python3 spec/gen_schemas.py [--output spacemolt/commands/format_schemas_gen.py]
"""

import json
import sys
from pathlib import Path

SPEC_PATH = Path(__file__).parent / "openapi.json"


def load_spec():
    with open(SPEC_PATH) as f:
        return json.load(f)


def generate_skeleton(spec):
    """Generate skeleton schema entries from endpoint descriptions."""
    schemas = {}
    paths = spec.get("paths", {})
    for path, methods in paths.items():
        for method, details in methods.items():
            if method not in ("post", "put", "patch"):
                continue
            op_id = details.get("operationId", "")
            if not op_id:
                continue
            summary = details.get("summary", "")
            # Stub entry — just a message from the summary
            schemas[op_id] = {
                "message": summary or f"{op_id} completed",
            }
    return schemas


def main():
    spec = load_spec()
    skeletons = generate_skeleton(spec)

    print(f"# Generated {len(skeletons)} skeleton schema entries from {SPEC_PATH.name}")
    print(f"# These are stubs — add fields, lists, and hints manually or")
    print(f"# re-run when response schemas are added to the spec.\n")
    print("FORMAT_SCHEMAS_GEN = {")
    for op_id, schema in sorted(skeletons.items()):
        print(f"    {op_id!r}: {{")
        for k, v in schema.items():
            print(f"        {k!r}: {v!r},")
        print("    },")
    print("}")


if __name__ == "__main__":
    main()
