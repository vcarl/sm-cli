#!/bin/bash
# Comprehensive integration test for sm-cli
# Registers a new user and performs a full gameplay loop in the spawn system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
print_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶ $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

run_test() {
    TESTS_RUN=$((TESTS_RUN + 1))
    local description="$1"
    shift

    echo -e "\n${YELLOW}Test $TESTS_RUN: $description${NC}"

    if "$@"; then
        print_success "$description"
        return 0
    else
        print_error "$description"
        return 1
    fi
}

# Cleanup function
cleanup() {
    if [ -f "$CRED_FILE" ]; then
        rm -f "$CRED_FILE"
        print_info "Cleaned up credentials file"
    fi
    if [ -f "$SESSION_FILE" ]; then
        rm -f "$SESSION_FILE"
        print_info "Cleaned up session file"
    fi
}

trap cleanup EXIT

# Setup
DIR="$(cd "$(dirname "$0")/.." && pwd)"
SM="$DIR/sm"
TIMESTAMP=$(date +%s)
USERNAME="IntegrationTest-$TIMESTAMP"
EMPIRE="solarian"  # Good for mining/trading in spawn system
CRED_FILE="$DIR/me/credentials-test-$TIMESTAMP.txt"
SESSION_FILE="/tmp/sm-session-test-$TIMESTAMP"
mkdir -p "$DIR/me"

print_step "SM-CLI Integration Test"
print_info "Username: $USERNAME"
print_info "Empire: $EMPIRE"
print_info "Credentials: $CRED_FILE"
echo

# ============================================================================
# REGISTRATION & LOGIN
# ============================================================================

print_step "1. Registration & Login"

run_test "Register new user" \
    bash -c "$SM register '$USERNAME' '$EMPIRE' > '$CRED_FILE'"

if [ ! -f "$CRED_FILE" ]; then
    print_error "Credentials file was not created"
    exit 1
fi

print_info "Credentials saved to $CRED_FILE"
cat "$CRED_FILE"

run_test "Login with new credentials" \
    $SM login "$CRED_FILE"

# ============================================================================
# BASIC STATUS & INFO COMMANDS
# ============================================================================

print_step "2. Basic Status & Information"

run_test "Check player status" \
    $SM status

run_test "Check ship details" \
    $SM ship

run_test "Check cargo" \
    $SM cargo

run_test "Check current POI" \
    $SM poi

run_test "Check system info" \
    $SM system

run_test "List POIs in system" \
    $SM pois

run_test "Check captain's log" \
    $SM log

# ============================================================================
# SKILLS & PROGRESSION
# ============================================================================

print_step "3. Skills & Progression"

run_test "Check trained skills" \
    $SM skills

run_test "Query all skills" \
    $SM skills query --limit 5

run_test "Inspect a specific skill" \
    $SM skills inspect mining || true  # May not exist yet

run_test "Check missions (combined view)" \
    $SM missions

run_test "Check active missions" \
    $SM missions active

run_test "Check available missions" \
    $SM missions available

# ============================================================================
# CRAFTING & RECIPES
# ============================================================================

print_step "4. Crafting & Recipes"

run_test "List recipes" \
    $SM recipes --limit 5

run_test "Query recipes" \
    $SM recipes query --limit 5

run_test "Search recipes" \
    $SM recipes query --search ore || true

# ============================================================================
# MINING & RESOURCE GATHERING
# ============================================================================

print_step "5. Mining & Resource Gathering"

print_info "Starting mining operations..."

# Mine a few times
for i in {1..3}; do
    run_test "Mine (attempt $i)" \
        $SM mine

    print_info "Waiting for mining cooldown..."
    sleep 2
done

run_test "Check cargo after mining" \
    $SM cargo

# ============================================================================
# MARKET & TRADING
# ============================================================================

print_step "6. Market & Trading"

run_test "Check market listings" \
    $SM listings || print_info "No listings available (not docked)"

run_test "Check ships available" \
    $SM ships || true

# ============================================================================
# SOCIAL & COMMUNICATION
# ============================================================================

print_step "7. Social & Communication"

run_test "Check nearby players" \
    $SM nearby || true

run_test "Check notifications" \
    $SM notifications

run_test "Add captain's log entry" \
    $SM log-add "Integration test run at $(date)"

run_test "Check log with new entry" \
    $SM log --brief

# ============================================================================
# FACTION SYSTEM
# ============================================================================

print_step "8. Faction System"

run_test "List factions" \
    $SM faction-list --limit 5 || $SM passthrough faction_list limit=5

run_test "Check faction invites" \
    $SM faction-invites || true

# ============================================================================
# NOTES SYSTEM
# ============================================================================

print_step "9. Notes System"

run_test "List notes" \
    $SM notes || true

# ============================================================================
# JSON OUTPUT MODES
# ============================================================================

print_step "10. JSON Output Modes"

run_test "Status as JSON" \
    bash -c "$SM status --json | python3 -m json.tool > /dev/null"

run_test "Ship as JSON" \
    bash -c "$SM ship --json | python3 -m json.tool > /dev/null"

run_test "Missions as JSON" \
    bash -c "$SM missions --json | python3 -m json.tool > /dev/null"

run_test "Skills as JSON" \
    bash -c "$SM skills --json | python3 -m json.tool > /dev/null"

# ============================================================================
# BACKWARDS COMPATIBILITY
# ============================================================================

print_step "11. Backwards Compatibility (Old Command Syntax)"

run_test "Old query-missions syntax" \
    $SM query-missions --limit 3

run_test "Old active-missions syntax" \
    $SM active-missions

run_test "Old query-skills syntax" \
    $SM query-skills --limit 3

run_test "Old query-recipes syntax" \
    $SM query-recipes --limit 3

# ============================================================================
# FUZZY MATCHING
# ============================================================================

print_step "12. Fuzzy Matching"

print_info "Testing typo suggestions..."

run_test "Typo 'misions' suggests 'missions'" \
    bash -c "$SM misions 2>&1 | grep -q \"Did you mean 'missions'\""

run_test "Typo 'atacc' suggests 'attack'" \
    bash -c "$SM atacc 2>&1 | grep -q \"Did you mean 'attack'\""

run_test "Typo 'jum' suggests similar commands" \
    bash -c "$SM jum 2>&1 | grep -q 'Did you mean'"

# ============================================================================
# HELP SYSTEM
# ============================================================================

print_step "13. Help System"

run_test "Main help" \
    $SM --help > /dev/null

run_test "Missions hierarchical help" \
    $SM missions --help > /dev/null

run_test "Skills hierarchical help" \
    $SM skills --help > /dev/null

run_test "Recipes hierarchical help" \
    $SM recipes --help > /dev/null

run_test "Register command help" \
    $SM register --help > /dev/null

# ============================================================================
# FINAL SUMMARY
# ============================================================================

echo
print_step "Integration Test Summary"
echo
echo "Total Tests: $TESTS_RUN"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
else
    echo -e "Failed: $TESTS_FAILED"
fi
echo

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ALL TESTS PASSED! ✓${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}  SOME TESTS FAILED ✗${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 1
fi
