#!/usr/bin/env bash
# Integration smoke tests for the sm CLI.
# Usage: ./tests/test_integration.sh [credentials.txt]
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

echo "Logging in..."
$SM login "$CRED"
echo ""

echo "=== Basic Commands ==="
check_grep "status"     "Credits:"         $SM status
check_grep "ship"       "Hull:"            $SM ship
check_grep "cargo"      "[0-9]+/[0-9]+"    $SM cargo
check_grep "system"     "System:"          $SM system
check_grep "pois"       "id:"              $SM pois
check      "poi"                           $SM poi
check      "log"                           $SM log
check      "nearby"                        $SM nearby
check_grep "wait"       "Ready"            $SM wait --timeout 5
check_grep "commands"   "COMBAT"           $SM commands
echo ""

echo "=== Hierarchical Commands (Skills, Missions, Recipes) ==="
check      "skills (default)"              $SM skills
check      "skills list"                   $SM skills list
check_grep "skills query"   "Page"         $SM skills query --limit 5
check      "missions (combined)"           $SM missions || true
check      "missions active"               $SM missions active || true
check      "missions available"            $SM missions available || true
check_grep "recipes (default)" "Page"      $SM recipes
check      "recipes list"                  $SM recipes list --limit 5
check_grep "recipes query"  "Page"         $SM recipes query --limit 5
echo ""

echo "=== Phase 4: Insurance Commands ==="
check      "insurance (status)"            $SM insurance || true
check      "insurance --help"              $SM insurance --help
check      "insurance buy --help"          $SM insurance buy --help
check      "insurance claim --help"        $SM insurance claim --help
echo ""

echo "=== Phase 4: Storage Commands ==="
check      "storage (view)"                $SM storage || true
check      "storage --help"                $SM storage --help
check      "storage deposit --help"        $SM storage deposit --help
check      "storage withdraw --help"       $SM storage withdraw --help
echo ""

echo "=== Phase 4: Market Commands ==="
check      "market (orders)"               $SM market || true
check      "market --help"                 $SM market --help
check      "market buy --help"             $SM market buy --help
check      "market sell --help"            $SM market sell --help
check      "market cancel --help"          $SM market cancel --help
echo ""

echo "=== New Endpoints (Phase 3) ==="
check      "get-version"                   $SM get-version || true
check      "get-map"                       $SM get-map || true
check      "view-orders"                   $SM view-orders || true
check      "view-storage"                  $SM view-storage || true
echo ""

echo "=== JSON Output Modes ==="
check_grep "status --json"    '"result"'   $SM status --json
check_grep "ship --json"      '"result"'   $SM ship --json
check_grep "skills --json"    '"result"'   $SM skills --json
check_grep "missions --json"  '"result"'   $SM missions --json || true
check_grep "raw get_status"   '"result"'   $SM raw get_status --json
echo ""

echo "=== Backwards Compatibility ==="
check      "query-missions (old)"          $SM query-missions --limit 3 || true
check      "active-missions (old)"         $SM active-missions || true
check      "query-skills (old)"            $SM query-skills --limit 3
check      "query-recipes (old)"           $SM query-recipes --limit 3
echo ""

echo "=== Fuzzy Matching ==="
check_grep "typo 'misions'"   "Did you mean" $SM misions 2>&1 || true
check_grep "typo 'skils'"     "Did you mean" $SM skils 2>&1 || true
echo ""

echo "=== Social & Communication ==="
check      "notes"                         $SM notes || true
check      "trades"                        $SM trades || true
check      "drones"                        $SM drones || true
check      "ships"                         $SM ships || true
check      "notifications"                 $SM notifications || true
check      "chat-history"                  $SM chat-history general --limit 5 || true
echo ""

echo "=== Faction System ==="
check      "faction-list"                  $SM faction-list --limit 5 || true
check      "faction-invites"               $SM faction-invites || true
echo ""

echo "=== Market & Trading ==="
check      "listings"                      $SM listings || true
check      "base"                          $SM base || true
echo ""

echo "=== Passthrough System ==="
check      "passthrough get_status"        $SM passthrough get_status
check_grep "help for passthrough"  "get_status" $SM passthrough --help || $SM commands
echo ""

echo ""
echo "============================================"
echo "$pass passed, $fail failed"
echo "============================================"
[ "$fail" -eq 0 ]
