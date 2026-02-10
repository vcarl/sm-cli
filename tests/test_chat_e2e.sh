#!/usr/bin/env bash
# End-to-end chat tests using two accounts.
# Usage: ./tests/test_chat_e2e.sh [credentials.txt] [copilot-credentials.txt]
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
SM="$DIR/sm"
CRED_A="${1:-$DIR/credentials.txt}"
CRED_B="${2:-$DIR/copilot-credentials.txt}"

pass=0 fail=0

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

check_not_grep() {
  local name="$1" pattern="$2"; shift 2
  if output=$("$@" 2>&1) && ! echo "$output" | grep -qE "$pattern"; then
    echo "  ok  $name"
    pass=$((pass + 1))
  else
    echo "FAIL  $name (should NOT match /$pattern/)"
    echo "      $output" | head -3
    fail=$((fail + 1))
  fi
}

# --- Login both accounts and extract player IDs ---
echo "Logging in account A..."
$SM login "$CRED_A"
ID_A=$($SM raw get_status --json | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['player']['id'])")
echo "  Player A: $ID_A"

echo "Logging in account B..."
$SM login "$CRED_B"
ID_B=$($SM raw get_status --json | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['player']['id'])")
echo "  Player B: $ID_B"
echo ""

# --- Local chat ---
echo "=== Local chat ==="
$SM login "$CRED_A" > /dev/null
STAMP_LOCAL="e2e-local-$(date +%s)"
check_grep "send local"       "Sent" $SM chat local "$STAMP_LOCAL"

# Verify sender sees it in history
check_grep "sender sees local" "$STAMP_LOCAL" $SM chat-history local 5

# Other account in same system should also see it
$SM login "$CRED_B" > /dev/null
check_grep "receiver sees local" "$STAMP_LOCAL" $SM chat-history local 5
echo ""

# --- System chat ---
echo "=== System chat ==="
$SM login "$CRED_A" > /dev/null
STAMP_SYS="e2e-system-$(date +%s)"
check_grep "send system"       "Sent" $SM chat system "$STAMP_SYS"
check_grep "sender sees system" "$STAMP_SYS" $SM chat-history system 5

$SM login "$CRED_B" > /dev/null
check_grep "receiver sees system" "$STAMP_SYS" $SM chat-history system 5
echo ""

# --- Private chat (exercises the fixed arg order) ---
echo "=== Private chat ==="
$SM login "$CRED_A" > /dev/null
STAMP_PM="e2e-pm-$(date +%s)"
check_grep "send private A->B" "Sent" $SM chat private "$ID_B" "hello from A: $STAMP_PM"

# Sender should see it in their private history
check_grep "sender sees pm" "$STAMP_PM" $SM chat-history private 5 "$ID_B"

# Recipient should see it
$SM login "$CRED_B" > /dev/null
check_grep "receiver sees pm" "$STAMP_PM" $SM chat-history private 5 "$ID_A"

# Reply back
STAMP_REPLY="e2e-reply-$(date +%s)"
check_grep "send private B->A" "Sent" $SM chat private "$ID_A" "reply from B: $STAMP_REPLY"

$SM login "$CRED_A" > /dev/null
check_grep "A sees reply" "$STAMP_REPLY" $SM chat-history private 5 "$ID_B"
echo ""

# --- Private messages don't leak to other channels ---
echo "=== Isolation ==="
$SM login "$CRED_B" > /dev/null
check_not_grep "pm not in local"  "$STAMP_PM" $SM chat-history local 5
check_not_grep "pm not in system" "$STAMP_PM" $SM chat-history system 5
echo ""

# --- Missing target error ---
echo "=== Error handling ==="
check_grep "private without target" "ERROR|usage" $SM chat private "lonely message" 2>&1 || true
echo ""

# --- Results ---
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
