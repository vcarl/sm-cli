# OpenAPI Spec Coverage Status

Last validated: 2026-02-16

## Summary

- **Live spec endpoints:** 148
- **Implemented in ENDPOINT_ARGS:** 127
- **Custom command endpoints (not in ENDPOINT_ARGS):** 21 (dock, login, mine, etc.)
- **Parameter mismatches:** 9 (6 intentional extensions, 2 complex nested, 1 dual-param)

## Recent Improvements

**Fixed (2026-02-16) — API drift sync:**
- Updated local spec from 119 to 148 endpoints (fetched from live API)
- Added 33 new endpoints to ENDPOINT_ARGS (faction features, intel, queue, facilities, items)
- Removed 4 deleted endpoints: `list_item`, `buy_listing`, `cancel_list` (replaced by market order system)
- Updated `register` to include `registration_code` (now required per spec)
- Added `refuel` params: `item_id?`, `quantity?:int`
- Added `captains_log_list` param: `index?:int`
- Added `help` params: `category?`, `command?`
- Updated `build_base` params: replaced `description` with `services` per spec
- Added `recall_drone` param: `all?:bool`
- Added `faction_create_role` params: `name?`, `priority?:int`, `invite?:bool`, `kick?:bool`
- Added `faction_edit_role` params: `role_id?`, `name?`
- Added `faction_gift` params: `faction_id?`, `item_id?`, `quantity?:int`
- Added `faction_post_mission` params: `title?`, `description?`, `type?`, `item_id?`, `quantity?:int`
- Created `spec/drift_check.py` — live drift detection tool
- Updated tests for removed endpoints
- No test regressions (pre-existing failures unchanged at 11+1)

**Previous fixes (2026-02-10):**
- Fixed 13 parameter mismatches by aligning required/optional flags with spec
- Added missing optional parameters (`offset`, `limit`, `before`, `credits`, `message`, etc.)
- Changed `buy_insurance` from `coverage_percent` to `ticks` per spec

## Endpoints Handled by Custom Commands (21)

These endpoints exist in the live spec and ARE implemented, but through dedicated command handlers in `spacemolt/commands/` rather than via ENDPOINT_ARGS passthrough:

| Spec Endpoint | CLI Command | Handler |
|---------------|-------------|---------|
| `claim` | `sm claim` | `actions.cmd_claim` |
| `createSession` | (internal) | `api.py` session flow |
| `dock` | `sm dock` | `actions.cmd_dock` |
| `get_active_missions` | `sm active-missions` | `missions.py` |
| `get_base` | `sm base` | `info.cmd_base` |
| `get_base_wrecks` | `sm wrecks` | `info.py` |
| `get_cargo` | `sm cargo` | `info.cmd_cargo` |
| `get_commands` | `sm commands` | `cli.py` |
| `get_missions` | `sm missions` | `missions.py` |
| `get_nearby` | `sm nearby` | `info.cmd_nearby` |
| `get_poi` | `sm poi` | `info.cmd_poi` |
| `get_recipes` | `sm recipes` | `recipes.py` |
| `get_ship` | `sm ship` | `info.cmd_ship` |
| `get_skills` | `sm skills` | `skills.py` |
| `get_system` | `sm system` | `info.cmd_system` |
| `get_wrecks` | `sm wrecks` | `info.py` |
| `login` | `sm login` | `actions.cmd_login` |
| `mine` | `sm mine` | `actions.cmd_mine` |
| `repair` | `sm repair` | `actions.cmd_repair` |
| `undock` | `sm undock` | `actions.cmd_undock` |
| `view_market` | `sm listings` | `info.cmd_listings` |

## Parameter Mismatches (9)

### Intentional Custom Extensions (6)
These add useful functionality beyond what the spec formally declares:
- `attack` — `weapon_idx` (select which weapon to use)
- `forum_create_thread`, `forum_list` — `category` (forum organization)
- `get_base_cost` — `base_type`
- `install_mod` — `slot_idx` (module slot selection)
- `raid_status` — `base_id`

### Complex Nested Params (2)
These endpoints accept complex nested arrays/objects not expressible as simple CLI args:
- `faction_submit_intel` — accepts `systems` array with nested POIs and resources
- `faction_submit_trade_intel` — accepts `stations` array with nested items

Use `sm raw <endpoint> '<json>'` for full nested payloads.

### Dual-Param Endpoint (1)
- `recall_drone` — we support both `drone_id` (custom) and `all` (spec)

## Custom Command Drift Flags

These custom commands may need updates to support new spec params:
- **`refuel`** (`actions.py:287`): Now supports `item_id` and `quantity` params; custom command sends neither
- **`captains_log_list`** (`actions.py:462`): Now supports `index` param; custom command sends none
- **`register`** (`actions.py:29`): Spec now requires `registration_code`; custom command doesn't send it

## Tooling

| Tool | Purpose | Usage |
|------|---------|-------|
| `spec/validate.py` | Offline: compare ENDPOINT_ARGS vs local spec | `python3 spec/validate.py [--verbose] [--strict]` |
| `spec/drift_check.py` | Live: fetch spec from API and compare | `python3 spec/drift_check.py [--json] [--strict]` |

## Action Items

- [ ] Update custom commands for new params (refuel, captains_log_list, register)
- [ ] Add `:json` type converter for complex nested params
- [ ] Handle `faction_submit_intel` / `faction_submit_trade_intel` complex payloads
- [ ] Document custom extensions in CONTRIBUTING.md
- [ ] Fix 11 pre-existing test failures (market, commands, listings, pois, formatters)
- [ ] Set up CI to run `drift_check.py --strict` periodically
