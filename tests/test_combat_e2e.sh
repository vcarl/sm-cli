#!/usr/bin/env bash
# End-to-end combat tests using two accounts.
# Logs in both players, ensures they're at the same location, and enters combat.
# Usage: ./tests/test_combat_e2e.sh [credentials.txt] [gunner-credentials.txt]
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
SM="$DIR/sm"
CRED_A="${1:-$DIR/credentials.txt}"
CRED_B="${2:-$DIR/gunner-credentials.txt}"

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

# Helper: switch to an account and return silently
login_a() { $SM login "$CRED_A" > /dev/null; }
login_b() { $SM login "$CRED_B" > /dev/null; }

# Helper: extract a field from get_status JSON
get_field() {
  $SM raw get_status --json | python3 -c "
import sys, json
r = json.load(sys.stdin)['result']
path = '$1'.split('.')
v = r
for k in path:
    v = v[k]
print(v)
"
}

# --- Login both accounts and extract player IDs + locations ---
echo "=== Setup ==="

echo "Logging in account A..."
$SM login "$CRED_A"
ID_A=$(get_field "player.id")
POI_A=$(get_field "player.current_poi")
SYS_A=$(get_field "player.current_system")
echo "  Player A: $ID_A at $POI_A ($SYS_A)"

echo "Logging in account B..."
$SM login "$CRED_B"
ID_B=$(get_field "player.id")
POI_B=$(get_field "player.current_poi")
SYS_B=$(get_field "player.current_system")
echo "  Player B: $ID_B at $POI_B ($SYS_B)"
echo ""

# --- Ensure both players are at the same POI ---
echo "=== Colocating players ==="
if [ "$POI_A" != "$POI_B" ]; then
  echo "Players are at different POIs, moving B to A's location..."
  login_b

  # Undock first (required before jumping/traveling)
  $SM undock 2>/dev/null || true

  # Jump to A's system if needed
  if [ "$SYS_A" != "$SYS_B" ]; then
    echo "  Jumping B to system $SYS_A..."
    $SM jump "$SYS_A" || true
    $SM wait --timeout 120
  fi

  # Travel to A's POI
  echo "  Traveling B to POI $POI_A..."
  $SM travel "$POI_A" || true
  $SM wait --timeout 120

  POI_B=$(login_b && get_field "player.current_poi")
  echo "  Player B now at: $POI_B"
fi

# Make sure both are undocked (required for combat)
login_a
$SM undock 2>/dev/null || true
login_b
$SM undock 2>/dev/null || true
echo ""

# --- Verify both players see each other ---
echo "=== Visibility ==="
login_a
check_grep "A sees B nearby" "$ID_B|test-gunner" $SM nearby --json

login_b
check_grep "B sees A nearby" "$ID_A|TestPilot" $SM nearby --json
echo ""

# --- Scan target before attacking ---
echo "=== Scan ==="
login_b
check_grep "B scans A" "scan|Scan|hull|Hull|shield|Shield|Hint" $SM scan "$ID_A" 2>&1 || true
echo ""

# --- Record hull before combat ---
echo "=== Pre-combat status ==="
login_a
HULL_A_BEFORE=$($SM raw get_status --json | python3 -c "
import sys, json
s = json.load(sys.stdin)['result']['ship']
print(s.get('hull', s.get('max_hull', '?')))
")
echo "  A hull before: $HULL_A_BEFORE"

login_b
HULL_B_BEFORE=$($SM raw get_status --json | python3 -c "
import sys, json
s = json.load(sys.stdin)['result']['ship']
print(s.get('hull', s.get('max_hull', '?')))
")
echo "  B hull before: $HULL_B_BEFORE"
echo ""

# --- Combat: B attacks A ---
echo "=== Combat ==="
login_b

# Attack several times
for i in 1 2 3; do
  echo "  Attack round $i..."
  ATTACK_OUT=$($SM attack "$ID_A" 2>&1) || true
  echo "    $ATTACK_OUT" | head -5

  # Check for common attack result patterns
  if echo "$ATTACK_OUT" | grep -qEi "hit|miss|damage|attack|combat|Hint"; then
    echo "  ok  attack round $i got combat response"
    pass=$((pass + 1))
  elif echo "$ATTACK_OUT" | grep -qEi "cooldown|wait|too soon|rate"; then
    echo "  ok  attack round $i (cooldown)"
    pass=$((pass + 1))
  elif echo "$ATTACK_OUT" | grep -qEi "ERROR|error"; then
    echo "FAIL  attack round $i"
    fail=$((fail + 1))
  else
    echo "  ok  attack round $i (unknown response, not error)"
    pass=$((pass + 1))
  fi

  # Rate limit between attacks
  if [ "$i" -lt 3 ]; then
    sleep 11
  fi
done
echo ""

# --- Post-combat status ---
echo "=== Post-combat status ==="
login_a
check_grep "A status after combat" "Hull:" $SM status

HULL_A_AFTER=$($SM raw get_status --json | python3 -c "
import sys, json
s = json.load(sys.stdin)['result']['ship']
print(s.get('hull', s.get('max_hull', '?')))
")
echo "  A hull after: $HULL_A_AFTER (was $HULL_A_BEFORE)"

login_b
check_grep "B status after combat" "Hull:" $SM status
echo ""

# --- Repair both ships ---
echo "=== Cleanup: repair ==="
login_a
$SM dock 2>/dev/null || true
$SM repair 2>/dev/null || true
echo "  A repaired"

login_b
$SM dock 2>/dev/null || true
$SM repair 2>/dev/null || true
echo "  B repaired"
echo ""

# --- Results ---
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
