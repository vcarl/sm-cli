# SpaceMolt API Specification

This directory contains the OpenAPI specification for the SpaceMolt game API.

## Files

- **`openapi.json`** - Official OpenAPI 3.0.3 spec from https://game.spacemolt.com/api/openapi.json
- **`validate.py`** - Cross-reference script to validate our implementation against the spec

## Updating the Spec

To fetch the latest spec:

```bash
curl -s https://game.spacemolt.com/api/openapi.json -o spec/openapi.json
```

## Validating Implementation

Run the validation script to check if our CLI implementation matches the API spec:

```bash
# Basic validation
python3 spec/validate.py

# Verbose output with parameter details
python3 spec/validate.py --verbose

# Strict mode (exit with error if mismatches found)
python3 spec/validate.py --strict
```

The validator checks:
- ✅ All spec endpoints are implemented
- ✅ No deprecated/removed endpoints in our code
- ✅ Parameter names, types, and required/optional flags match

## Acceptance Criteria

**All new commands and endpoint implementations must:**

1. Match the official OpenAPI spec (run `spec/validate.py` to verify)
2. Include correct parameter types (`:int`, `:bool`, `:str`)
3. Mark optional parameters with `?` suffix (e.g., `"quantity?:int"`)
4. Respect rate-limiting for mutation commands (11-second sleeps)

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed guidelines.

## Spec Structure

The OpenAPI spec defines:
- **Standard response envelope**: `{result, error, notifications, session}`
- **Session authentication**: `X-Session-Id` header
- **Rate limits**: Mutation commands limited to 1 per 10-second tick
- **Error codes**: Machine-readable codes like `not_docked`, `insufficient_credits`

## Integration with CLI

Our passthrough system (`spacemolt/commands/passthrough.py`) uses the `ENDPOINT_ARGS` table to map CLI arguments to API parameters. This table should be kept in sync with the OpenAPI spec.

Example:
```python
ENDPOINT_ARGS = {
    "buy": ["item_id:str", "quantity:int"],
    "scan": ["target_id:str"],
    "get_chat_history": ["channel?:str", "limit?:int", "target_id?:str"],
    # ...
}
```

Maps to OpenAPI:
```json
{
  "paths": {
    "/buy": {
      "post": {
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "properties": {
                  "item_id": {"type": "string"},
                  "quantity": {"type": "integer"}
                },
                "required": ["item_id", "quantity"]
              }
            }
          }
        }
      }
    }
  }
}
```
