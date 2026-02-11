# OpenAPI Spec Coverage Status

Last validated: 2026-02-10 (Updated)

## Summary

- **Spec endpoints:** 119
- **Implemented:** 88 (74% coverage)
- **Missing:** 31 endpoints (mostly naming differences)
- **Mismatches:** 20 endpoints with parameter differences (down from 33)

## Recent Improvements

**Fixed (2026-02-10):**
- ✅ Fixed 13 parameter mismatches by aligning required/optional flags with spec
- ✅ Added missing optional parameters (`offset`, `limit`, `before`, `credits`, `message`, etc.)
- ✅ Changed `buy_insurance` from `coverage_percent` to `ticks` per spec
- ✅ Added `base_id` parameter to `set_home_base`
- ✅ Added batch operation parameters (`orders`, `order_ids`) to market endpoints
- ✅ Fixed validator to parse `param?:type` format correctly
- ✅ All 196 unit tests passing

## Missing Endpoints (31)

These endpoints are in the OpenAPI spec but not yet implemented in the CLI:

### Query Endpoints (Most are naming differences)
- `captains_log_list` (we have `log`)
- `get_active_missions` (we have `active-missions`)
- `get_base` (we have `base`)
- `get_base_cost`
- `get_base_wrecks` (we have `wrecks`)
- `get_cargo` (we have `cargo`)
- `get_commands` (we have `commands`)
- `get_listings` (we have `listings`)
- `get_map`
- `get_missions` (we have `missions`)
- `get_nearby` (we have `nearby`)
- `get_poi` (we have `poi`)
- `get_recipes` (we have `recipes`)
- `get_ship` (we have `ship`)
- `get_skills` (we have `skills`)
- `get_status` (we have `status`)
- `get_system` (we have `system`)
- `get_version`
- `get_wrecks` (we have `wrecks`)
- `help`
- `raid_status`
- `view_orders`
- `view_storage`

### Mutation Endpoints
- `createSession` (we have session creation in login flow)
- `dock` (we have `dock`)
- `login` (we have `login`)
- `mine` (we have `mine`)
- `refuel` (we have `refuel`)
- `register` (not implemented - users must register via web)
- `repair` (we have `repair`)
- `undock` (we have `undock`)

**Note:** Many of these "missing" endpoints are actually implemented with different names (e.g., `status` instead of `get_status`). The passthrough system handles both naming conventions.

## Parameter Mismatches (20)

These are **intentional custom extensions** or **type limitations** in the CLI:

### Custom Extensions (Intentional)
These add useful functionality beyond the spec:
- `attack` - `weapon_idx` (select which weapon to use)
- `attack_base`, `loot_base_wreck`, `salvage_base_wreck` - base/wreck identification
- `build_base` - `name`, `description` (base metadata)
- `cloak` - `enable` (boolean toggle)
- `create_note`, `write_note`, `read_note` - note content/ID parameters
- `deploy_drone`, `order_drone`, `recall_drone` - drone management params
- `forum_create_thread`, `forum_list` - `category` (forum organization)
- `install_mod` - `slot_idx` (module slot selection)

### Type Limitations (CLI Architecture)
The CLI treats complex types as JSON strings:
- `orders` parameter (array type) → pass as JSON string
- `order_ids` parameter (array type) → pass as JSON string
- `items` parameter (object type) → pass as JSON string

**Example:** `sm market buy ore_iron 10 100`

## Compliance Status

| Category | Count | Status |
|----------|-------|--------|
| Spec-compliant params | 68 | ✅ Fully aligned |
| Custom extensions | 16 | ✅ Documented, intentional |
| Type limitations | 4 | ✅ Expected for CLI (JSON strings) |

**Overall:** 77% of implemented endpoints are fully spec-compliant. Remaining 23% have intentional enhancements or type handling differences.

## Action Items

- [x] Fix required/optional flags to match spec ✅ **DONE**
- [x] Add missing pagination parameters ✅ **DONE**
- [x] Add batch operation parameters ✅ **DONE**
- [x] Update validator to handle `param?:type` format ✅ **DONE**
- [ ] Document custom extensions in CONTRIBUTING.md
- [ ] Add commonly-used missing endpoints (`get_version`, `raid_status`, `view_orders`)
- [ ] Consider JSON parsing for array/object types (`:json` type specifier)

## Next Steps

1. **Documentation:** Add section to CONTRIBUTING.md about custom extensions
2. **Low-hanging fruit:** Add missing endpoints that are just passthrough (get_version, view_orders, etc.)
3. **Long-term:** Consider adding `:json` type converter for complex types

Run `python3 spec/validate.py --verbose` for detailed parameter comparisons.
