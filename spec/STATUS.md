# OpenAPI Spec Coverage Status

Last validated: 2026-02-10

## Summary

- **Spec endpoints:** 119
- **Implemented:** 88
- **Missing:** 31 endpoints
- **Mismatches:** 33 endpoints with parameter differences

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

## Parameter Mismatches (33)

These endpoints are implemented but have parameter differences with the spec. This may indicate:
- API spec changes not yet reflected in our code
- Our custom enhancements (extra parameters)
- Spec is more flexible (batching, optional parameters)

### Common Patterns

1. **Batching support in spec:** Many endpoints support batch operations in the spec but we only support single operations
   - `create_buy_order`, `create_sell_order`, `modify_order` - spec has `orders` array
   - `cancel_order` - spec has `order_ids` array

2. **Optional parameters in spec marked as required in our impl:**
   - `chat` - `target_id` should be optional
   - `forum_upvote` - `reply_id` should be optional
   - Various others

3. **Extra parameters in our impl:** We may have added convenience parameters
   - `attack` - `weapon_idx`
   - `build_base` - `name`, `description`
   - `cloak` - `enable`
   - `deploy_drone` - `target_id`, `drone_item_id`

### Action Items

- [ ] Review parameter mismatches and update `ENDPOINT_ARGS` to match spec
- [ ] Add support for batch operations where spec provides it
- [ ] Fix required/optional flags to match spec
- [ ] Consider deprecating or documenting custom parameters not in spec
- [ ] Update tests to cover spec-compliant parameter usage

## Next Steps

1. **Immediate:** Fix critical parameter mismatches (required/optional flags)
2. **Short-term:** Add missing commonly-used endpoints
3. **Long-term:** Support batch operations for market/order endpoints
4. **Documentation:** Document custom extensions vs spec compliance

Run `python3 spec/validate.py --verbose` for detailed parameter comparisons.
