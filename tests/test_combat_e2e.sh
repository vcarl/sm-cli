#!/usr/bin/env bash
# End-to-end combat tests using two accounts.
# Logs in both players, ensures they're at the same location, and enters combat.
# Usage: ./tests/test_combat_e2e.sh [credentials.txt] [copilot-credentials.txt]
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
SM="$DIR/sm"
CRED_A="${1:-$DIR/credentials.txt}"
CRED_B="${2:-$DIR/copilot-credentials.txt}"
SESSION_FILE="/tmp/sm-session"

# Switch accounts by swapping saved session IDs (no API call)
use_a() { cp "$SESSION_A" "$SESSION_FILE"; }
use_b() { cp "$SESSION_B" "$SESSION_FILE"; }

# --- Login both accounts once, save session IDs ---
echo "=== Setup ==="
SESSION_A=$(mktemp)
SESSION_B=$(mktemp)
trap "rm -f '$SESSION_A' '$SESSION_B'" EXIT

echo "--- Login A ---"
$SM login "$CRED_A"
cp "$SESSION_FILE" "$SESSION_A"

echo ""
echo "--- Login B ---"
$SM login "$CRED_B"
cp "$SESSION_FILE" "$SESSION_B"
echo ""

# --- Make sure both are undocked ---
echo "=== Undocking ==="
use_a
$SM undock 2>/dev/null || true
use_b
$SM undock 2>/dev/null || true
echo ""

# --- Check who's nearby from each side ---
echo "=== Nearby (from A) ==="
use_a
$SM nearby
echo ""

echo "=== Nearby (from B) ==="
use_b
NEARBY_JSON=$($SM nearby --json 2>/dev/null || true)
$SM nearby
echo ""

# Extract A's player_id from B's nearby list
TARGET_ID=$(echo "$NEARBY_JSON" | python3 -c "
import sys, json
try:
    r = json.loads(sys.stdin.read())
    players = r.get('result',r).get('nearby', r.get('result',r).get('players', []))
    for p in players:
        pid = p.get('player_id') or p.get('id','')
        if pid:
            print(pid)
            break
except: pass
" 2>/dev/null)

if [ -z "$TARGET_ID" ]; then
  echo "ERROR: Could not find a target player nearby. Are both accounts at the same POI?"
  exit 1
fi
echo "Target ID: $TARGET_ID"
echo ""

# --- Scan target before attacking ---
echo "=== B scans A ==="
use_b
$SM scan "$TARGET_ID" || true
echo ""

# --- Pre-combat status ---
echo "=== Pre-combat status ==="
echo "--- A ---"
use_a
$SM status
echo ""
echo "--- B ---"
use_b
$SM status
echo ""

# --- Combat: B attacks A ---
echo "=== Combat: B attacks A ==="
use_b

for i in 1 2 3; do
  echo "--- Attack round $i ---"
  $SM attack "$TARGET_ID" || true

  if [ "$i" -lt 3 ]; then
    sleep 11
  fi
done
echo ""

# --- Post-combat status ---
echo "=== Post-combat status ==="
echo "--- A ---"
use_a
$SM status
echo ""
echo "--- B ---"
use_b
$SM status
echo ""

# --- Repair both ships ---
echo "=== Cleanup: repair ==="
use_a
$SM dock 2>/dev/null || true
$SM repair 2>/dev/null || true

use_b
$SM dock 2>/dev/null || true
$SM repair 2>/dev/null || true
echo "Done."
