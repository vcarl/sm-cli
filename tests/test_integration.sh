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

echo "Running smoke tests..."
check_grep "status"     "Credits:"         $SM status
check_grep "ship"       "Hull:"            $SM ship
check_grep "cargo"      "[0-9]+/[0-9]+"    $SM cargo
check_grep "system"     "System:"          $SM system
check_grep "pois"       "id:"              $SM pois
check      "poi"                           $SM poi
check      "skills"                        $SM skills
check_grep "recipes"    "Page"             $SM recipes
check_grep "commands"   "COMBAT"           $SM commands
check      "nearby"                        $SM nearby
check      "log"                           $SM log
check_grep "wait"       "Ready"            $SM wait --timeout 5
check_grep "json flag"  '"result"'         $SM raw get_status --json

echo ""
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
