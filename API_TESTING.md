# API Compatibility Testing

Tools for analyzing and validating SpaceMolt CLI against OpenAPI specifications.

## Tools

### 1. `analyze_api_usage.py` - Extract API Usage from Code

Analyzes the entire codebase to extract:
- All API endpoints called
- Request body structures
- Response fields accessed by the code

**Usage:**

```bash
# Text report (human-readable)
python3 analyze_api_usage.py --format text

# JSON output (for programmatic use)
python3 analyze_api_usage.py --format json > api_usage_analysis.json
```

**Output includes:**
- 📊 Summary statistics
- 🔗 All endpoints with request body structures
- 📋 All response fields accessed across the codebase

### 2. `compare_with_openapi.py` - Validate Against OpenAPI Spec

Compares the extracted API usage against an OpenAPI specification.

**Usage:**

```bash
# Compare against OpenAPI spec
python3 compare_with_openapi.py path/to/openapi.json

# Use custom usage analysis file
python3 compare_with_openapi.py spec.yaml --usage my_analysis.json

# JSON output for CI/CD
python3 compare_with_openapi.py spec.json --format json
```

**What it detects:**
- ✅ Endpoints used by client that match the spec
- ⚠️ Endpoints used by client but NOT in spec (potential issues)
- 💡 Endpoints in spec but never used by client (dead code?)
- 🔍 Request body field mismatches
- 📝 Response field usage vs spec definitions

## Workflow

### Initial Analysis

```bash
# 1. Analyze the codebase
python3 analyze_api_usage.py --format json > api_usage_analysis.json

# 2. Review what endpoints are being used
python3 analyze_api_usage.py --format text | less

# 3. Compare against OpenAPI spec (when you have one)
python3 compare_with_openapi.py openapi_spec.json
```

### Acceptance Testing

When you receive an OpenAPI spec to validate:

```bash
# Generate compatibility report
python3 compare_with_openapi.py new_spec.yaml > compatibility_report.txt

# Or get JSON for automated testing
python3 compare_with_openapi.py new_spec.yaml --format json > results.json
```

### CI/CD Integration

```bash
#!/bin/bash
# acceptance_test.sh

# Analyze current API usage
python3 analyze_api_usage.py --format json > api_usage.json

# Compare against spec
python3 compare_with_openapi.py spec/openapi.yaml --format json > results.json

# Check for critical issues
missing=$(jq '.summary.missing_from_spec' results.json)
if [ "$missing" -gt 0 ]; then
    echo "❌ Client uses $missing endpoints not in spec!"
    jq '.endpoint_comparison.missing_from_spec' results.json
    exit 1
fi

echo "✅ API compatibility check passed"
```

## How It Works

### AST-Based Code Analysis

The analyzer uses Python's `ast` module to:
1. Parse all `.py` files in the `spacemolt/` directory
2. Find all calls to `self._post(endpoint, body)`
3. Extract endpoint names (string literals)
4. Extract request body structures (dict literals)
5. Track variable assignments to find response field accesses (`.get()` chains)

**Example detection:**

```python
# This code:
resp = self._post("get_status")
player = resp.get("result", {}).get("player", {})
credits = player.get("credits", 0)

# Is detected as:
# Endpoint: "get_status"
# Response fields: result, result.player, result.player.credits
```

### OpenAPI Schema Parsing

The comparison tool:
1. Loads OpenAPI spec (JSON or YAML)
2. Extracts all `/paths` and their request/response schemas
3. Resolves `$ref` references to components
4. Builds a flat map of endpoint → structure
5. Compares against extracted usage patterns

## Limitations

**Request Bodies:**
- Only detects static dict literals
- Dynamic body construction (loops, conditionals) shows as `<variable: name>`
- Function-built bodies show as `<funcname()>` or `<function call>`

**Response Fields:**
- Only tracks `.get()` access patterns
- Direct dict access (`resp["field"]`) not tracked
- Some defensive coding patterns might be missed

**Endpoints:**
- Variable endpoint names show as `<variable: name>`
- F-string endpoints show as `<f-string>`
- Most endpoints are static literals (captured correctly)

## Example Output

### API Usage Analysis

```
================================================================================
API USAGE ANALYSIS
================================================================================

📊 Summary:
   • Total API calls found: 62
   • Unique endpoints: 39
   • Files analyzed: 14

🔗 get_status
   Calls: 5
   Files: api.py, actions.py, info.py
   Request body: (none)
   Example: api.py:400 in _get_cached_status()

🔗 travel
   Calls: 1
   Files: actions.py
   Request body:
      • target_poi: Attribute
   Example: actions.py:211 in cmd_travel()
```

### Compatibility Report

```
================================================================================
API COMPATIBILITY REPORT
================================================================================

📊 Summary:
   • Client uses 37 endpoints
   • OpenAPI spec defines 40 endpoints
   • Matched: 35
   • Client uses but not in spec: 2
   • Spec defines but client never uses: 5

⚠️  Endpoints used by client but NOT in OpenAPI spec:
   • custom_endpoint
   • deprecated_action

💡 Endpoints in spec but never used by client:
   • admin_panel
   • metrics_dump
   • debug_info
```

## Maintenance

These tools should be run:
- **Before major releases** - Validate API compatibility
- **When spec changes** - Check for breaking changes
- **During code review** - Verify new endpoints are documented
- **In CI/CD** - Automated compatibility checks
