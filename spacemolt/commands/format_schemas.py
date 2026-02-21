"""
Declarative format schemas for SpaceMolt CLI response formatting.

Instead of hand-writing a formatter function per endpoint, define a schema dict
that describes what to print.  The generic ``render_schema()`` function walks
the schema and produces human-friendly output.

Schema keys
-----------
message : str
    A template string printed first.  Supports field expressions (see below).
icon : str
    Prepended to message (e.g. "✓").
fields : list[tuple[str, str]]
    Each entry is (Label, template).  Printed as ``  Label: <resolved>``.
    Entries where the resolved value is empty/None are skipped.
static : list[str]
    Literal lines printed as-is (e.g. "  Module returned to cargo").
list : dict
    Render a list from the result.  Keys:
        key       – result field containing the list
        empty     – message when list is empty
        header    – optional header template (``{_count}`` = list length)
        each      – per-item template
hints : list[str]
    Printed as ``\\n  Hint: <hint1>  |  <hint2>``.

Field expression syntax (inside ``{…}``)
-----------------------------------------
{field}          – simple lookup in result dict
{a|b}            – fallback chain: try ``a``, then ``b``
{field:,}        – thousands separator (int/float)
{field:id}       – truncate string to 8 chars
{field:.2f}      – float formatting
{field.nested}   – dot-path access into nested dicts
{_count}         – magic var: length of the current list being iterated
"""

import re

# ---------------------------------------------------------------------------
# Field expression resolver
# ---------------------------------------------------------------------------

_EXPR_RE = re.compile(r"\{([^}]+)\}")


def _dot_get(data, path):
    """Resolve a dot-separated path like 'foo.bar.baz' against nested dicts."""
    obj = data
    for part in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(part)
        else:
            return None
    return obj


def _resolve_expr(expr, data):
    """Resolve a single field expression (the part inside {…})."""
    # Split format spec: {field:,} -> field_part="field", fmt=","
    if ":" in expr:
        field_part, fmt = expr.rsplit(":", 1)
    else:
        field_part, fmt = expr, None

    # Fallback chain: {a|b|c}
    candidates = field_part.split("|")
    value = None
    for candidate in candidates:
        candidate = candidate.strip()
        if candidate == "_count":
            value = data.get("_count")
            break
        value = _dot_get(data, candidate)
        if value is not None and value != "":
            break

    if value is None:
        return ""

    # Apply format spec
    if fmt == ",":
        try:
            return f"{int(value):,}"
        except (ValueError, TypeError):
            return str(value)
    elif fmt == "id":
        s = str(value)
        return s[:8] if len(s) > 8 else s
    elif fmt:
        try:
            return format(value, fmt)
        except (ValueError, TypeError):
            return str(value)

    return str(value)


def _resolve(template, data):
    """Interpolate all {…} expressions in a template string."""
    def replacer(m):
        return _resolve_expr(m.group(1), data)
    return _EXPR_RE.sub(replacer, template)


# ---------------------------------------------------------------------------
# Schema renderer
# ---------------------------------------------------------------------------

def render_schema(schema, resp):
    """Render a response dict according to a declarative format schema."""
    r = resp.get("result", resp)
    if isinstance(r, str):
        print(r)
        return

    # Icon + message
    msg_tpl = schema.get("message")
    if msg_tpl:
        icon = schema.get("icon", "")
        prefix = f"{icon} " if icon else ""
        print(f"{prefix}{_resolve(msg_tpl, r)}")

    # Static lines
    for line in schema.get("static", []):
        print(line)

    # Fields
    for label, tpl in schema.get("fields", []):
        val = _resolve(tpl, r)
        if val:
            print(f"  {label}: {val}")

    # List rendering
    list_spec = schema.get("list")
    if list_spec:
        items = r.get(list_spec["key"], [])
        if not items:
            empty = list_spec.get("empty")
            if empty:
                print(empty)
        else:
            header = list_spec.get("header")
            if header:
                print(_resolve(header, {**r, "_count": len(items)}))
            each = list_spec.get("each")
            if each:
                for item in items:
                    if isinstance(item, dict):
                        print(_resolve(each, {**item, "_count": len(items)}))
                    else:
                        print(f"  {item}")

    # Hints
    hints = schema.get("hints")
    if hints:
        print(f"\n  Hint: {'  |  '.join(hints)}")


# ---------------------------------------------------------------------------
# FORMAT_SCHEMAS — declarative schemas for endpoints
# ---------------------------------------------------------------------------

FORMAT_SCHEMAS = {
    # -----------------------------------------------------------------------
    # Phase 1: Simple confirmation + fields + hints (~25 trivial formatters)
    # -----------------------------------------------------------------------

    "jump": {
        "message": "Jumped to {target_system|system}",
        "fields": [
            ("Fuel used", "{fuel_cost|fuel_used}"),
            ("Location", "{arrived_at|location}"),
        ],
        "hints": ["sm system", "sm pois", "sm nearby"],
    },
    "deposit_items": {
        "message": "Deposited {item_id} x{quantity} to storage",
        "hints": ["sm storage", "sm cargo"],
    },
    "withdraw_items": {
        "message": "Withdrawn {item_id} x{quantity} from storage",
        "hints": ["sm storage", "sm cargo"],
    },
    "deposit_credits": {
        "message": "Deposited {amount:,} cr to storage",
        "hints": ["sm storage", "sm status"],
    },
    "withdraw_credits": {
        "message": "Withdrawn {amount:,} cr from storage",
        "hints": ["sm storage", "sm status"],
    },
    "jettison": {
        "message": "Jettisoned {item_id} x{quantity}",
        "fields": [
            ("Remaining in cargo", "{remaining_quantity}"),
        ],
        "hints": ["sm cargo", "sm nearby (to see if anyone picks it up)"],
    },
    "buy_ship": {
        "icon": "✓",
        "message": "Purchased {ship_class|class_id}",
        "fields": [
            ("Cost", "{cost:,} cr"),
            ("Ship ID", "{ship_id|id:id}"),
        ],
        "hints": ["sm switch-ship <ship_id>", "sm ships"],
    },
    "switch_ship": {
        "message": "Switched to {ship_class|class_id}",
        "fields": [
            ("Ship ID", "{ship_id|id:id}"),
        ],
        "hints": ["sm ship", "sm status"],
    },
    "sell_ship": {
        "icon": "✓",
        "message": "Sold {ship_class|class_id}",
        "fields": [
            ("Value", "{value|price:,} cr"),
        ],
        "hints": ["sm ships", "sm status"],
    },
    "install_mod": {
        "icon": "✓",
        "message": "Installed {module_id}",
        "fields": [
            ("Slot", "{slot_idx|slot}"),
        ],
        "hints": ["sm ship", "sm listings"],
    },
    "uninstall_mod": {
        "icon": "✓",
        "message": "Uninstalled {module_id}",
        "static": ["  Module returned to cargo"],
        "hints": ["sm ship", "sm cargo"],
    },
    "trade_offer": {
        "message": "{message}",
        "fields": [
            ("Trade ID", "{trade_id:id}"),
        ],
        "hints": ["sm trades", "sm trade-cancel <trade_id>"],
    },
    "trade_decline": {
        "message": "Trade declined",
        "hints": ["sm trades"],
    },
    "trade_cancel": {
        "message": "Trade cancelled",
        "hints": ["sm trades"],
    },
    "modify_order": {
        "icon": "✓",
        "message": "Order modified",
        "fields": [
            ("Order ID", "{order_id|id:id}"),
            ("New price", "{new_price} cr"),
        ],
        "hints": ["sm market"],
    },
    "join_faction": {
        "icon": "✓",
        "message": "Joined faction: {faction_name|name}",
        "hints": ["sm faction-info", "sm chat faction <message>"],
    },
    "leave_faction": {
        "message": "Left faction: {faction_name|name}",
        "hints": ["sm faction-list"],
    },
    "create_faction": {
        "icon": "✓",
        "message": "Created faction: [{tag}] {name}",
        "fields": [
            ("Faction ID", "{faction_id|id}"),
        ],
        "hints": ["sm faction-info", "sm faction-invite <player_id>"],
    },
    "faction_invite": {
        "icon": "✓",
        "message": "Invited {player_name|player_id} to faction",
        "hints": ["sm faction-info"],
    },
    "faction_kick": {
        "message": "Kicked {player_name|player_id} from faction",
        "hints": ["sm faction-info"],
    },
    "set_home_base": {
        "icon": "✓",
        "message": "Home base set: {base_name|base_id}",
        "hints": ["sm base", "sm status"],
    },
    "accept_mission": {
        "icon": "✓",
        "message": "Mission accepted: {title|mission_name}",
        "fields": [
            ("Mission ID", "{mission_id|id:id}"),
        ],
        "hints": ["sm missions", "sm active-missions"],
    },
    "abandon_mission": {
        "message": "Abandoned mission: {title|mission_name}",
        "hints": ["sm missions"],
    },
    "buy_insurance": {
        "icon": "✓",
        "message": "Insurance purchased: {coverage_percent|coverage}% coverage for {ticks|duration} ticks",
        "fields": [
            ("Cost", "{cost|premium:,} cr"),
        ],
        "hints": ["sm insurance", "sm status"],
    },
    "claim_insurance": {
        "icon": "✓",
        "message": "Insurance claimed",
        "fields": [
            ("Payout", "{payout:,} cr"),
        ],
        "hints": ["sm status", "sm buy-ship <class>"],
    },
    "forum_reply": {
        "icon": "✓",
        "message": "Reply posted",
        "fields": [
            ("Thread", "{thread_title|title}"),
            ("Reply ID", "{reply_id|id:id}"),
        ],
        "hints": ["sm forum-get-thread <thread_id>"],
    },
    "forum_create_thread": {
        "icon": "✓",
        "message": "Thread created: {title}",
        "fields": [
            ("Category", "{category}"),
            ("Thread ID", "{thread_id|id:id}"),
        ],
        "hints": ["sm forum-list", "sm forum-get-thread <thread_id>"],
    },
    "forum_upvote": {
        "icon": "✓",
        "message": "Upvoted (now {upvotes|total_upvotes} upvotes)",
        "hints": ["sm forum-list"],
    },
    "forum_delete_thread": {
        "icon": "✓",
        "message": "Thread deleted",
        "hints": ["sm forum-list"],
    },
    "forum_delete_reply": {
        "icon": "✓",
        "message": "Reply deleted",
        "hints": ["sm forum-get-thread <thread_id>"],
    },
    "set_anonymous": {
        "message": "Anonymous mode {anonymous}",
        "hints": ["sm status", "sm nearby"],
    },
    "set_colors": {
        "icon": "✓",
        "message": "Ship colors set",
        "fields": [
            ("Primary", "{primary_color}"),
            ("Secondary", "{secondary_color}"),
        ],
        "hints": ["sm ship"],
    },
    "set_status": {
        "icon": "✓",
        "message": "Status updated",
        "fields": [
            ("Message", "{status_message}"),
            ("Clan tag", "{clan_tag}"),
        ],
        "hints": ["sm status"],
    },
    "tow_wreck": {
        "icon": "✓",
        "message": "Towing wreck {wreck_id}",
        "hints": ["sm release-tow", "sm sell-wreck"],
    },
    "release_tow": {
        "icon": "✓",
        "message": "Released towed wreck",
        "hints": ["sm wrecks"],
    },
    "scrap_wreck": {
        "icon": "✓",
        "message": "Scrapped wreck",
        "hints": ["sm wrecks", "sm cargo"],
    },
    "sell_wreck": {
        "icon": "✓",
        "message": "Sold wreck",
        "hints": ["sm wrecks", "sm status"],
    },
    "reload": {
        "icon": "✓",
        "message": "Reloaded {weapon_name} with {ammo_name}",
        "fields": [
            ("Ammo", "{current_ammo}/{magazine_size}"),
            ("Weapon ID", "{weapon_id}"),
            ("Previous ammo", "{previous_ammo}"),
            ("Rounds discarded", "{rounds_discarded}"),
        ],
        "hints": ["sm ship", "sm cargo"],
    },
    "logout": {
        "icon": "✓",
        "message": "Logged out",
        "hints": ["sm login"],
    },
    "cloak": {
        "message": "{message}",
        "fields": [
            ("Enabled", "{enabled}"),
            ("Cloak strength", "{cloak_strength}"),
        ],
        "hints": ["sm nearby", "sm status"],
    },

    # -----------------------------------------------------------------------
    # Phase 2: List-displaying formatters (~14 medium)
    # -----------------------------------------------------------------------

    "view_storage": {
        "fields": [
            ("Credits", "{credits:,}"),
        ],
        "list": {
            "key": "items",
            "empty": "Storage is empty.",
            "header": "  Items ({_count}):",
            "each": "    {item_id} x{quantity}",
        },
        "hints": ["sm storage deposit <item> <qty>", "sm storage deposit --credits <amount>"],
    },
    "view_orders": {
        "list": {
            "key": "orders",
            "empty": "No active market orders.",
            "header": "Your Market Orders ({_count}):",
            "each": "  [{type}] {item_id} x{quantity} @ {price_each|price}cr ea - ID: {order_id|id}",
        },
        "hints": ["sm market buy <item> <qty> <price>", "sm market sell <item> <qty> <price>"],
    },
    "get_notes": {
        "list": {
            "key": "notes",
            "empty": "No notes.",
            "each": "  {id|note_id}: {title}  ({updated_at|created_at})",
        },
    },
    "faction_list": {
        "list": {
            "key": "factions",
            "empty": "No factions found.",
            "each": "  [{tag}] {name}  (id:{id|faction_id})  members:{member_count|members}",
        },
    },
    "faction_get_invites": {
        "list": {
            "key": "invites",
            "empty": "No pending faction invites.",
            "each": "  {faction_name|name} (id:{faction_id|id})  invited by {invited_by|inviter}",
        },
    },
    "salvage_wreck": {
        "message": "Salvaged wreck",
        "list": {
            "key": "items",
            "header": "\n  Recovered:",
            "each": "    - {item_id} x{quantity}",
        },
        "hints": ["sm cargo", "sm wrecks"],
    },
    "loot_wreck": {
        "message": "Looted {item_id} x{quantity} from wreck",
        "hints": ["sm wrecks", "sm salvage-wreck <wreck_id>"],
    },
    "complete_mission": {
        "icon": "✓",
        "message": "Mission completed: {title|mission_name}",
        "fields": [
            ("Reward", "{reward_credits|credits:,} cr"),
        ],
        "list": {
            "key": "reward_items",
            "header": "  Items:",
            "each": "    {item_id} x{quantity}",
        },
        "hints": ["sm missions", "sm status"],
    },
    "send_gift": {
        "icon": "✓",
        "message": "Gift sent to {recipient}",
        "fields": [
            ("Credits", "{credits:,} cr"),
        ],
        "list": {
            "key": "items",
            "header": "  Items:",
            "each": "    {item_id} x{quantity}",
        },
        "hints": ["sm cargo", "sm status"],
    },
    "cancel_order": {
        "icon": "✓",
        "message": "Order cancelled",
        "fields": [
            ("Order ID", "{order_id|id:id}"),
            ("Refunded", "{refunded_credits:,} cr"),
        ],
        "list": {
            "key": "returned_items",
            "header": "  Returned to cargo:",
            "each": "    {item_id} x{quantity}",
        },
        "hints": ["sm market"],
    },
    "trade_accept": {
        "icon": "✓",
        "message": "{message}",
        "fields": [
            ("Trade ID", "{trade_id:id}"),
            ("Your credits", "{your_credits} cr"),
        ],
        "hints": ["sm cargo", "sm status"],
    },
    "create_buy_order": {
        "icon": "✓",
        "message": "Buy order created: {item_id} x{quantity} @ {price_each|price} cr",
        "fields": [
            ("Listing fee", "{listing_fee|fee} cr"),
            ("Order ID", "{order_id|id:id}"),
        ],
        "hints": ["sm market"],
    },
    "create_sell_order": {
        "icon": "✓",
        "message": "Sell order created: {item_id} x{quantity} @ {price_each|price} cr",
        "fields": [
            ("Listing fee", "{listing_fee|fee} cr"),
            ("Order ID", "{order_id|id:id}"),
        ],
        "hints": ["sm market"],
    },
    # "craft" — handled by custom formatter in passthrough.py (_FORMATTERS)
    "estimate_purchase": {
        "message": "Purchase estimate for {item_id} x{quantity}:",
        "fields": [
            ("Total cost", "{total_cost:,} cr"),
            ("Average price", "{average_price:.2f} cr per unit"),
            ("Available", "{available} units"),
        ],
        "hints": ["sm buy <item_id> <quantity>"],
    },
    "get_version": {
        "message": "SpaceMolt version: {version}",
        "fields": [
            ("Build", "{build}"),
            ("API version", "{api_version}"),
        ],
    },
    "get_map": {
        "list": {
            "key": "systems",
            "empty": "No map data available.",
            "header": "Galaxy Map ({_count} systems):",
            "each": "  {name|system_id} ({id|system_id})",
        },
    },

    # -----------------------------------------------------------------------
    # Phase 4: New endpoints from drift sync (no formatters yet)
    # -----------------------------------------------------------------------

    "decline_mission": {
        "message": "Mission declined",
        "hints": ["sm missions"],
    },
    "use_item": {
        "icon": "✓",
        "message": "Used {item_id} x{quantity}",
        "hints": ["sm cargo"],
    },
    "view_faction_storage": {
        "fields": [
            ("Credits", "{credits:,}"),
        ],
        "list": {
            "key": "items",
            "empty": "Faction storage is empty.",
            "header": "  Items ({_count}):",
            "each": "    {item_id} x{quantity}",
        },
        "hints": ["sm faction-info"],
    },
    "faction_deposit_credits": {
        "message": "Deposited {amount:,} cr to faction storage",
        "hints": ["sm view-faction-storage", "sm status"],
    },
    "faction_withdraw_credits": {
        "message": "Withdrawn {amount:,} cr from faction storage",
        "hints": ["sm view-faction-storage", "sm status"],
    },
    "faction_deposit_items": {
        "message": "Deposited {item_id} x{quantity} to faction storage",
        "hints": ["sm view-faction-storage", "sm cargo"],
    },
    "faction_withdraw_items": {
        "message": "Withdrawn {item_id} x{quantity} from faction storage",
        "hints": ["sm view-faction-storage", "sm cargo"],
    },
    "faction_gift": {
        "icon": "✓",
        "message": "Gift sent to faction {faction_id}",
        "hints": ["sm faction-info"],
    },
    "faction_create_buy_order": {
        "icon": "✓",
        "message": "Faction buy order created: {item_id} x{quantity} @ {price_each} cr",
        "hints": ["sm faction-info"],
    },
    "faction_create_sell_order": {
        "icon": "✓",
        "message": "Faction sell order created: {item_id} x{quantity} @ {price_each} cr",
        "hints": ["sm faction-info"],
    },
    "faction_edit": {
        "icon": "✓",
        "message": "Faction updated",
        "hints": ["sm faction-info"],
    },
    "faction_create_role": {
        "icon": "✓",
        "message": "Role created: {name}",
        "hints": ["sm faction-info"],
    },
    "faction_edit_role": {
        "icon": "✓",
        "message": "Role updated",
        "hints": ["sm faction-info"],
    },
    "faction_delete_role": {
        "icon": "✓",
        "message": "Role deleted",
        "hints": ["sm faction-info"],
    },
    "faction_cancel_mission": {
        "message": "Faction mission cancelled",
        "hints": ["sm faction-list-missions"],
    },
    "faction_list_missions": {
        "list": {
            "key": "missions",
            "empty": "No faction missions.",
            "each": "  {title} [{type}] - {status}",
        },
    },
    "faction_post_mission": {
        "icon": "✓",
        "message": "Faction mission posted: {title}",
        "hints": ["sm faction-list-missions"],
    },
    "faction_intel_status": {
        "message": "Intel status: {status}",
        "fields": [
            ("Reports", "{report_count|reports}"),
            ("Last updated", "{last_updated}"),
        ],
    },
    "faction_submit_intel": {
        "icon": "✓",
        "message": "Intel submitted",
        "hints": ["sm faction-intel-status", "sm faction-query-intel <system>"],
    },
    "faction_query_intel": {
        "message": "Intel for {system_name}:",
        "hints": ["sm faction-submit-intel", "sm faction-intel-status"],
    },
    "faction_trade_intel_status": {
        "message": "Trade intel status: {status}",
        "hints": ["sm faction-submit-trade-intel", "sm faction-query-trade-intel <base_id>"],
    },
    "faction_submit_trade_intel": {
        "icon": "✓",
        "message": "Trade intel submitted",
        "hints": ["sm faction-trade-intel-status", "sm faction-query-trade-intel <base_id>"],
    },
    "faction_query_trade_intel": {
        "message": "Trade intel for base {base_id}:",
        "hints": ["sm faction-submit-trade-intel", "sm faction-trade-intel-status"],
    },
    "faction_rooms": {
        "list": {
            "key": "rooms",
            "empty": "No faction rooms.",
            "each": "  {name} (id:{room_id|id}) [{access}]",
        },
        "hints": ["sm faction-visit-room <room_id>", "sm faction-write-room"],
    },
    "faction_visit_room": {
        "message": "Visiting room: {name}",
        "fields": [
            ("Description", "{description}"),
        ],
        "hints": ["sm faction-rooms", "sm faction-write-room"],
    },
    "faction_write_room": {
        "icon": "✓",
        "message": "Room updated",
        "hints": ["sm faction-rooms"],
    },
    "faction_delete_room": {
        "icon": "✓",
        "message": "Room deleted",
        "hints": ["sm faction-rooms"],
    },
    "faction_promote": {
        "icon": "✓",
        "message": "Promoted {player_id} to {role_id}",
        "hints": ["sm faction-info"],
    },
    "faction_declare_war": {
        "message": "Declared war on {target_faction_id}",
        "hints": ["sm faction-info"],
    },
    "faction_propose_peace": {
        "message": "Peace proposed to {target_faction_id}",
        "hints": ["sm faction-info"],
    },
    "faction_accept_peace": {
        "icon": "✓",
        "message": "Peace accepted with {target_faction_id}",
        "hints": ["sm faction-info"],
    },
    "faction_set_ally": {
        "icon": "✓",
        "message": "Set {target_faction_id} as ally",
        "hints": ["sm faction-info"],
    },
    "faction_set_enemy": {
        "message": "Set {target_faction_id} as enemy",
        "hints": ["sm faction-info"],
    },
    "faction_decline_invite": {
        "message": "Declined invite from {faction_id}",
        "hints": ["sm faction-list"],
    },
    "battle": {
        "message": "{message}",
        "fields": [
            ("Action", "{action}"),
            ("Battle ID", "{battle_id}"),
            ("Stance", "{stance}"),
            ("Target", "{target_id}"),
        ],
        "hints": ["sm battle-status", "sm battle stance fire", "sm battle retreat"],
    },
    "self_destruct": {
        "message": "Self-destruct initiated",
        "hints": ["sm insurance claim", "sm ships"],
    },
    "register": {
        "icon": "✓",
        "message": "Registered as {username}",
        "fields": [
            ("Empire", "{empire}"),
        ],
        "hints": ["sm login"],
    },
    "create_note": {
        "icon": "✓",
        "message": "Note created",
        "fields": [
            ("ID", "{id|note_id}"),
            ("Title", "{title}"),
        ],
        "hints": ["sm notes"],
    },
    "write_note": {
        "icon": "✓",
        "message": "Note updated",
        "hints": ["sm notes"],
    },
    "refuel": {
        "icon": "✓",
        "message": "Refueled",
        "fields": [
            ("Fuel", "{fuel}"),
            ("Cost", "{cost:,} cr"),
        ],
        "hints": ["sm status"],
    },
}
