# SM-CLI Test Suite

## Test Types

### Unit Tests (Python)
Fast, isolated tests for individual functions and components.

**Location:** `tests/test_*.py`

**Run all unit tests:**
```bash
python3 -m unittest discover -s tests -v
```

**Run specific test file:**
```bash
python3 -m unittest tests.test_cli -v
python3 -m unittest tests.test_restructuring -v
python3 -m unittest tests.test_register -v
```

**Current coverage:** 243 tests

### Integration Test (Shell)
Comprehensive end-to-end test that registers a real user and performs a full gameplay loop.

**Location:** `tests/integration-test.sh`

**Run integration test:**
```bash
./tests/integration-test.sh
```

**What it tests:**
1. **Registration & Login**
   - Register new user with unique timestamp-based username
   - Login with generated credentials
   - Session management

2. **Basic Status & Info**
   - Player status
   - Ship details
   - Cargo inventory
   - POI information
   - System overview
   - Captain's log

3. **Skills & Progression**
   - Trained skills display
   - Skill queries and searches
   - Deep skill inspection
   - Mission views (combined, active, available)

4. **Crafting & Recipes**
   - Recipe listing
   - Recipe queries and searches
   - Ingredient trees

5. **Mining & Resources**
   - Mining operations (3 cycles)
   - Resource collection
   - Cargo updates

6. **Market & Trading**
   - Market listings
   - Ship inventory
   - Trading system

7. **Social & Communication**
   - Nearby players
   - Notifications
   - Captain's log entries

8. **Faction System**
   - Faction listings
   - Invites and membership

9. **Notes System**
   - Note management

10. **JSON Output**
    - All major commands with --json flag
    - JSON validation

11. **Backwards Compatibility**
    - Old flat command syntax
    - query-missions, active-missions, query-skills, query-recipes

12. **Fuzzy Matching**
    - Typo suggestions
    - "Did you mean?" functionality

13. **Help System**
    - Main help
    - Hierarchical command help
    - Subcommand help

**Features:**
- ✅ Automatic cleanup (credentials and session)
- ✅ Colored output for readability
- ✅ Test counters (passed/failed)
- ✅ Descriptive step labels
- ✅ Error handling with graceful failures

**Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ 1. Registration & Login
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1: Register new user
✓ Register new user

Test 2: Login with new credentials
✓ Login with new credentials

...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ALL TESTS PASSED! ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### E2E Chat Test (Shell)
Tests chat functionality in different contexts.

**Location:** `tests/e2e-chat.sh`

**Run:**
```bash
./tests/e2e-chat.sh
```

## Running All Tests

**Quick validation:**
```bash
# Unit tests only (fast)
python3 -m unittest discover -s tests

# Integration test (slower, requires API)
./tests/integration-test.sh
```

**Full test suite:**
```bash
# Run everything
python3 -m unittest discover -s tests && ./tests/integration-test.sh
```

## Continuous Integration

For CI/CD pipelines:

```bash
#!/bin/bash
set -e

echo "Running unit tests..."
python3 -m unittest discover -s tests -v

echo "Running integration tests..."
./tests/integration-test.sh

echo "All tests passed!"
```

## Test Coverage

**Current Status:**
- **Unit Tests:** 243 tests ✅
- **Integration Test:** 50+ scenarios ✅
- **E2E Tests:** Chat system ✅

**Coverage Areas:**
- ✅ Command parsing
- ✅ Argument validation
- ✅ API interactions
- ✅ Error handling
- ✅ JSON output modes
- ✅ Hierarchical commands
- ✅ Fuzzy matching
- ✅ Contextual help
- ✅ Backwards compatibility
- ✅ Registration flow
- ✅ Session management
- ✅ Full gameplay loop

## Adding New Tests

### Unit Tests
1. Create `tests/test_yourfeature.py`
2. Import from `spacemolt.*`
3. Use `unittest.TestCase`
4. Run with `python3 -m unittest tests.test_yourfeature -v`

### Integration Tests
1. Add new section to `tests/integration-test.sh`
2. Use `run_test` helper function
3. Follow existing patterns
4. Test with real API calls

## Troubleshooting

**Unit tests fail:**
- Check Python syntax: `python3 -m py_compile spacemolt/**/*.py`
- Run specific test: `python3 -m unittest tests.test_cli.TestSpecificTest -v`

**Integration test fails:**
- Check API connectivity: `./sm status`
- Review credentials: Check `me/credentials-test-*.txt`
- Check session: `/tmp/sm-session-test-*`
- Run with debug: `bash -x ./tests/integration-test.sh`

**Permission errors:**
- Make scripts executable: `chmod +x tests/*.sh`

**API rate limits:**
- Integration test includes sleep delays
- Wait between test runs if needed
