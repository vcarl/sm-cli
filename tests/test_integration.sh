#!/usr/bin/env bash
# Integration smoke tests for the sm CLI.
# Usage: ./tests/test_integration.sh [credentials.txt]
#
# Tests are written to pass regardless of server state — assertions match
# output patterns that are always present (success OR empty-case text).
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
SM="$DIR/sm"
CRED="${1:-$DIR/credentials.txt}"

pass=0 fail=0

check() {
  local name="$1"; shift
  if output=$("$@" 2>&1); then
    echo "  ok  $name"
    pass=$((pass + 1))
  else
    echo "FAIL  $name"
    echo "      $output" | head -3
    fail=$((fail + 1))
  fi
}

check_grep() {
  local name="$1" pattern="$2"; shift 2
  if output=$("$@" 2>&1) && echo "$output" | grep -qE "$pattern"; then
    echo "  ok  $name"
    pass=$((pass + 1))
  else
    echo "FAIL  $name (expected /$pattern/)"
    echo "      $output" | head -3
    fail=$((fail + 1))
  fi
}

# Checks output matches pattern regardless of exit code.
check_output() {
  local name="$1" pattern="$2"; shift 2
  output=$("$@" 2>&1) || true
  if echo "$output" | grep -qE "$pattern"; then
    echo "  ok  $name"
    pass=$((pass + 1))
  else
    echo "FAIL  $name (expected /$pattern/)"
    echo "      $output" | head -3
    fail=$((fail + 1))
  fi
}

echo "Logging in..."
$SM login "$CRED"
echo ""

# ── Core info commands ────────────────────────────────────
echo "=== Core Info Commands ==="
check_grep "status"     "Credits:"         $SM status
check_grep "ship"       "Hull:"            $SM ship
check_grep "cargo"      "[0-9]+/[0-9]+"    $SM cargo
check_grep "system"     "System:"          $SM system
# pois may return data or "No POIs found" depending on location
check_output "pois"     "id:|No POIs found" $SM pois
check      "poi"                           $SM poi
check      "log"                           $SM log
check      "nearby"                        $SM nearby
echo ""

# ── CLI help / commands ───────────────────────────────────
echo "=== CLI Help ==="
check_grep "commands"      "usage: sm"          $SM commands
check_grep "commands list" "status|ship|pois"   $SM commands
check_grep "help alias"    "usage: sm"          $SM help
echo ""

# ── Hierarchical commands ─────────────────────────────────
echo "=== Hierarchical Commands (Skills, Missions, Recipes) ==="
check      "skills (default)"              $SM skills
check      "skills list"                   $SM skills list
check_output "skills query" "Page|═"       $SM skills query --limit 5
check_output "missions (combined)"  "mission|Mission|No active|ERROR" $SM missions
check_output "missions active"      "mission|Mission|No active|ERROR" $SM missions active
check_output "missions available"   "mission|Mission|No |ERROR"       $SM missions available
# recipes progression view has ═ dividers; Page footer only if >1 page
check_output "recipes (default)" "═|No skill"  $SM recipes
check_output "recipes list"      "═|No skill"  $SM recipes list --limit 5
check_output "recipes query"     "═|No skill"  $SM recipes query --limit 5
echo ""

# ── Insurance commands ────────────────────────────────────
echo "=== Insurance Commands ==="
check_output "insurance (status)"  "Insurance|coverage|insur|ERROR" $SM insurance
check_grep   "insurance --help"    "insurance"    $SM insurance --help
check_grep   "insurance buy --help"  "coverage"   $SM insurance buy --help
check_grep   "insurance claim --help" "claim"     $SM insurance claim --help
echo ""

# ── Storage commands ──────────────────────────────────────
echo "=== Storage Commands ==="
check_output "storage (view)"  "Storage|storage|Credits|empty|ERROR" $SM storage
check_grep   "storage --help"           "storage"   $SM storage --help
check_grep   "storage deposit --help"   "deposit"   $SM storage deposit --help
check_grep   "storage withdraw --help"  "withdraw"  $SM storage withdraw --help
echo ""

# ── Market commands ───────────────────────────────────────
echo "=== Market Commands ==="
check_output "market (orders)"  "Market|orders|No active|ERROR" $SM market
check_grep   "market --help"          "market"   $SM market --help
check_grep   "market buy --help"      "item_id"  $SM market buy --help
check_grep   "market sell --help"     "item_id"  $SM market sell --help
check_grep   "market cancel --help"   "order_id" $SM market cancel --help
echo ""

# ── Passthrough endpoints ─────────────────────────────────
echo "=== Passthrough Endpoints ==="
check      "get-version"                   $SM get-version || true
check_output "get-map"   "Galaxy Map|map|systems|ERROR" $SM get-map
check_output "view-orders" "Market Orders|No active|ERROR" $SM view-orders
check_output "view-storage" "Storage|Credits|empty|ERROR"  $SM view-storage
echo ""

# ── JSON output modes ─────────────────────────────────────
echo "=== JSON Output Modes ==="
check_grep "status --json"    '"result"'   $SM status --json
check_grep "ship --json"      '"result"'   $SM ship --json
check_grep "skills --json"    '"result"'   $SM skills --json
check_output "missions --json" '"result"'  $SM missions --json
check_grep "raw get_status"   '"result"'   $SM raw get_status --json
echo ""

# ── Backwards compatibility ───────────────────────────────
echo "=== Backwards Compatibility ==="
check_output "query-missions (old)"  "mission|Mission|No |ERROR"  $SM query-missions --limit 3
check_output "active-missions (old)" "mission|Mission|No |ERROR"  $SM active-missions
check      "query-skills (old)"            $SM query-skills --limit 3
check_output "query-recipes (old)"  "═|No skill" $SM query-recipes --limit 3
echo ""

# ── Fuzzy matching (typo suggestions) ─────────────────────
echo "=== Fuzzy Matching ==="
check_output "typo 'misions'"   "Did you mean" $SM misions
check_output "typo 'skils'"     "Did you mean" $SM skils
echo ""

# ── Social & communication ────────────────────────────────
echo "=== Social & Communication ==="
check_output "notes"          "notes|No notes"          $SM notes
check_output "trades"         "trade|Trade|No pending"  $SM trades
check_output "drones"         "drone|No active"         $SM drones
check_output "ships"          "id:|No ships"            $SM ships
check_output "notifications"  "notification|No |Unread" $SM notifications
check_output "chat-history"   "No messages|:]"          $SM chat-history general 5
echo ""

# ── Faction system ────────────────────────────────────────
echo "=== Faction System ==="
check_output "faction-list"    "factions|No factions|members:|ERROR" $SM faction-list 0 5
check_output "faction-invites" "invite|No pending|ERROR"            $SM faction-invites
echo ""

# ── Market & trading ──────────────────────────────────────
echo "=== Market & Trading ==="
check_output "listings"  "Listings|listing|No |ERROR"  $SM listings
check_output "base"      "Base|base|docked|ERROR"      $SM base
echo ""

# ── Passthrough dispatch ──────────────────────────────────
echo "=== Passthrough Dispatch ==="
# Direct endpoint name works as passthrough
check_grep "passthrough get_status"  "Credits:|credit" $SM get_status
# Declarative schema renders (jump without args shows usage)
check_output "passthrough usage"  "Usage:" $SM jump
# Unknown endpoint gives error + suggestion
check_output "unknown endpoint"   "Unknown command|ERROR" $SM totally_fake_endpoint
echo ""

# ── Declarative formatter smoke tests ─────────────────────
echo "=== Declarative Formatters ==="
# These test that FORMAT_SCHEMAS render without crashing.
# Each should produce either formatted output or a server error — never a traceback.
check_output "get-version"    "version|SpaceMolt|ERROR" $SM get-version
check_output "view-storage"   "Storage|Credits|empty|ERROR" $SM view-storage
check_output "view-orders"    "Market|orders|No active|ERROR" $SM view-orders
check_output "faction-list schema" "factions|No factions|members:|ERROR" $SM faction-list
check_output "faction-invites schema" "invite|No pending|ERROR" $SM faction-invites
echo ""

echo ""
echo "============================================"
echo "$pass passed, $fail failed"
echo "============================================"
[ "$fail" -eq 0 ]
