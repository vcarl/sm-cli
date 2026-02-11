# SM-CLI Command Restructuring - Implementation Summary

## What Was Implemented

### 1. Fuzzy Matching for Unknown Commands ✅

**Files Created:**
- `spacemolt/suggestions.py` - Levenshtein distance algorithm and command suggestion system

**Files Modified:**
- `spacemolt/cli.py` - Integrated fuzzy matching into passthrough validation

**Features:**
- Unknown commands trigger "Did you mean?" suggestions
- Up to 3 similar commands shown based on edit distance (threshold: 3)
- Searches both COMMAND_MAP and ENDPOINT_ARGS for all valid commands

**Examples:**
```bash
$ sm misions
ERROR: Unknown command 'misions'
Did you mean 'missions'?

$ sm atacc
ERROR: Unknown command 'atacc'
Did you mean 'attack'?
```

### 2. Hierarchical Command Structure ✅

**Files Created:**
- `spacemolt/context_help.py` - Contextual help system

**Files Modified:**
- `spacemolt/cli.py` - Added hierarchical subparsers for missions, skills, recipes
- `spacemolt/commands/missions.py` - Added router and enhanced combined view
- `spacemolt/commands/skills.py` - Added router
- `spacemolt/commands/recipes.py` - Added router and updated __all__

**New Command Structure:**

**Missions:**
```bash
sm missions              # Show active + available missions (NEW combined view)
sm missions active       # Active missions only
sm missions available    # Available missions only
sm missions query        # Search missions with pagination
sm missions accept <id>  # Accept mission
sm missions complete <id> # Complete mission
sm missions abandon <id>  # Abandon mission
```

**Skills:**
```bash
sm skills                # Show trained skills (default)
sm skills list           # Same as default
sm skills query          # Search all skills
sm skills inspect <id>   # Deep inspect skill
```

**Recipes:**
```bash
sm recipes               # List recipes (default)
sm recipes list          # Same as default
sm recipes query         # Recipe progression and search
sm recipes craft <id>    # Craft recipe
```

### 3. Enhanced Missions View ✅

**New Default Behavior:**
- `sm missions` (no subcommand) shows BOTH active and available missions in one view
- Active section shows: title, status, description (truncated), objectives (max 2)
- Available section shows: first 5 missions with type, difficulty, rewards
- Falls back gracefully when not docked or no missions

### 4. Contextual Help System ✅

**Automatic Integration:**
- Contextual help shows automatically after command execution
- Centralized in `cli.py` - commands don't need to know about it
- Only shows when:
  - Command has suggestions defined in COMMAND_SUGGESTIONS
  - Not in JSON mode (`--json` flag not set)
  - Command completed successfully (no errors)

**Example Output:**
```bash
$ sm missions
Active missions (2/5):
  [mission details...]

Available missions:
  [mission details...]

Related commands:
  sm missions accept <id>    # Accept a mission
  sm missions query          # Search missions
  sm missions complete <id>  # Complete mission
  sm missions abandon <id>   # Abandon mission
```

## Backwards Compatibility ✅

**All old commands still work:**
- `sm missions` - Still works (but now shows combined view instead of available only)
- `sm active-missions` - Still works (unchanged)
- `sm query-missions` - Still works (unchanged)
- `sm query-skills` - Still works (unchanged)
- `sm skill` - Still works (unchanged)
- `sm recipes` - Still works (but now hierarchical)
- `sm query-recipes` - Still works (unchanged)

**Both syntaxes work side-by-side:**
```bash
# Old flat syntax
sm query-missions --search "escort"
sm active-missions
sm query-skills --my

# New hierarchical syntax
sm missions query --search "escort"
sm missions active
sm skills query --my
```

## Testing

**All Existing Tests Pass:** ✅
- 196 tests passed
- 0 failures
- No regressions

**Manual Testing Scenarios:**

1. **Fuzzy Matching:**
   ```bash
   sm misions    # → suggests "missions"
   sm atacc      # → suggests "attack"
   sm jum        # → suggests "jump"
   ```

2. **Hierarchical Help:**
   ```bash
   sm missions --help
   sm skills --help
   sm recipes --help
   sm missions query --help
   ```

3. **Backwards Compatibility:**
   ```bash
   sm active-missions     # Old command works
   sm query-missions      # Old command works
   sm missions active     # New command works
   sm missions query      # New command works
   ```

## Architecture Decisions

### 1. Automatic Contextual Help
Instead of manually adding `show_related_commands()` to each command function, integrated it into the main CLI dispatch in `cli.py`. This:
- Centralizes the logic
- Commands don't need to be aware of contextual help
- Easy to enable/disable
- Consistent behavior across all commands

### 2. Router Pattern
Created router functions (`cmd_missions_router`, `cmd_skills_router`, `cmd_recipes_router`) that:
- Handle hierarchical subcommand dispatch
- Maintain backwards compatibility
- Keep existing command functions unchanged
- Allow easy extension for new subcommands

### 3. Combined Missions View
The new `sm missions` default shows both active and available missions because:
- Users typically want to see both contexts
- Reduces need to run two separate commands
- Still allows specific views via `sm missions active` or `sm missions available`
- More informative at a glance

## Files Changed

**New Files:**
- `spacemolt/suggestions.py` (84 lines)
- `spacemolt/context_help.py` (54 lines)

**Modified Files:**
- `spacemolt/cli.py` (+47 lines, -3 lines)
- `spacemolt/commands/missions.py` (+85 lines, -1 line)
- `spacemolt/commands/skills.py` (+18 lines)
- `spacemolt/commands/recipes.py` (+31 lines, -1 line)

**Total:** ~234 lines added, ~5 lines removed

## Next Steps (Optional Future Enhancements)

1. **Expand Hierarchical Groups:**
   - `sm ship` (ship, buy-ship, sell-ship, switch-ship)
   - `sm faction` (15 faction subcommands)
   - `sm market` (7 market subcommands)
   - `sm notes` (4 note subcommands)
   - `sm drones` (4 drone subcommands)
   - `sm chat` (2 chat subcommands)
   - `sm base` (4 base subcommands)
   - `sm log` (3 captain's log subcommands)

2. **Deprecation Warnings:**
   - Add optional warnings for old flat syntax
   - Guide users toward hierarchical syntax

3. **Shell Completion:**
   - Add bash/zsh completion scripts
   - Support tab completion for hierarchical commands

4. **Command Aliases:**
   - Add short aliases (e.g., `sm m` for `sm missions`)
   - User-configurable aliases

## Success Criteria

✅ Unknown commands show "Did you mean?" suggestions
✅ Hierarchical commands work (`sm missions query`, `sm skills inspect`, etc.)
✅ Default command behavior makes sense (`sm missions` shows active + available)
✅ Contextual help appears automatically for relevant commands
✅ All old commands continue to work (full backwards compatibility)
✅ All existing tests pass (196/196)
✅ No new spec validation errors
✅ Clean, maintainable code architecture
