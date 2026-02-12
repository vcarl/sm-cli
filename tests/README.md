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

**Current coverage:** 343 tests

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

## Coverage Measurement

The sm-cli uses [coverage.py](https://coverage.readthedocs.io/) to measure test coverage.

### Running Tests with Coverage

**Basic coverage report:**
```bash
coverage run -m unittest discover tests -v
coverage report
```

**HTML report (detailed, with highlighting):**
```bash
coverage run -m unittest discover tests -v
coverage html
open coverage_html/index.html  # macOS
# or: xdg-open coverage_html/index.html  # Linux
```

**Coverage for specific module:**
```bash
coverage run -m unittest discover tests -v
coverage report --include="spacemolt/commands/insurance.py"
```

**Check coverage threshold:**
```bash
coverage run -m unittest discover tests -v
coverage report --fail-under=60  # Fails if below 60%
```

### Coverage Configuration

Coverage is configured in `.coveragerc`:
- **Source:** `spacemolt/` directory
- **Omits:** Tests, specs, `__pycache__`
- **HTML Output:** `coverage_html/` directory

### Coverage Targets

| Module Type | Target | Rationale |
|-------------|--------|-----------|
| **Overall** | 60%+ | Aspirational but achievable |
| **New features** | 90%+ | All new code should be well-tested |
| **Critical modules** | 95%+ | cli.py, api.py need thorough coverage |
| **Command modules** | 85%+ | User-facing commands should be reliable |
| **Formatters/display** | 70%+ | Lower priority, visual output |

**Note:** Coverage is not the only metric. Quality of tests matters more than quantity. Focus on:
- Testing both success and failure paths
- Edge cases (empty, None, invalid types)
- Error messages are helpful and accurate
- --json output format correctness

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

The project uses GitHub Actions for automated testing on every push and pull request.

**Workflow:** `.github/workflows/tests.yml`

**What it does:**
- Tests on Python 3.9, 3.10, 3.11, 3.12, 3.13
- Runs all unit tests with coverage
- Fails if coverage drops below 60%
- Uploads coverage reports to Codecov (Python 3.11 only)
- Archives HTML coverage report on failure

**Manual CI simulation:**
```bash
#!/bin/bash
set -e

echo "Running unit tests with coverage..."
coverage run -m unittest discover tests -v
coverage report --fail-under=60

echo "Running integration tests..."
./tests/integration-test.sh

echo "All tests passed!"
```

## Test Coverage

**Current Status:**
- **Unit Tests:** 343 tests ✅
- **Integration Test:** 50+ scenarios ✅
- **E2E Tests:** Chat system ✅
- **Code Coverage:** 63.91% overall

**Module Coverage:**
- insurance.py: 100% ✅
- storage.py: 100% ✅
- market.py: 100% ✅
- recipes.py: 88.28%
- cli.py: 91.63%

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

## Testing Standards & Guidelines

### Test Structure

**One test file per command module:**
- `tests/test_insurance.py` → `spacemolt/commands/insurance.py`
- `tests/test_storage.py` → `spacemolt/commands/storage.py`
- `tests/test_market.py` → `spacemolt/commands/market.py`

**Group tests by function/method:**
```python
class TestInsuranceStatus(unittest.TestCase):
    def test_no_coverage(self): ...
    def test_with_coverage(self): ...
    def test_expiry_warning(self): ...

class TestInsuranceBuy(unittest.TestCase):
    def test_valid_purchase(self): ...
    def test_invalid_ticks(self): ...
```

**Use descriptive test names:**
- Format: `test_<action>_<scenario>`
- Examples:
  - `test_no_coverage()` - Tests the no coverage state
  - `test_invalid_ticks_zero()` - Tests validation for zero ticks
  - `test_already_insured_error()` - Tests error when already insured

**Keep tests isolated:**
- No shared state between tests
- Each test should be independent
- Use setUp/tearDown only when necessary

### What to Test

**1. Success Paths:**
- Valid inputs produce expected outputs
- API called with correct parameters
- Output messages are correct

**2. Failure Paths:**
- Invalid inputs show error messages
- API errors are handled gracefully
- Helpful hints are provided

**3. Edge Cases:**
- Empty values ([], {}, None, "")
- Zero and negative numbers
- Very large values
- Malformed data types

**4. Validation:**
- Required parameters checked
- Type validation works
- Range validation works

**5. Output Modes:**
- Normal text output is readable
- --json flag produces valid JSON
- Error messages are consistent

### Mocking Guidelines

**Use the test helpers:**
```python
def make_args(**kwargs):
    """Build test arguments."""
    ns = argparse.Namespace()
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns

def mock_api(response=None):
    """Mock API that returns specific response."""
    api = MagicMock()
    api._post.return_value = response or {}
    return api
```

**Mock external dependencies:**
- ✅ Mock API calls with `mock_api()`
- ✅ Mock print output with `@patch("builtins.print")`
- ✅ Mock time.sleep for speed (when needed)
- ❌ Don't mock the code under test

**Verify API calls:**
```python
api._post.assert_called_once_with("buy_insurance", {"ticks": 50})
api._post.assert_not_called()  # When validation should fail
```

**Capture print output:**
```python
with patch("builtins.print") as mock_print:
    cmd_insurance_status(api, args)

output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
self.assertIn("Insurance Coverage:", output)
```

### Test Quality Checklist

Before submitting tests, ensure:

- [ ] Both success and error paths tested
- [ ] Edge cases covered (empty, None, zero, negative)
- [ ] Error messages verified to be helpful
- [ ] --json output tested and validated
- [ ] API calls verified with correct parameters
- [ ] Tests run in isolation (no dependencies)
- [ ] Descriptive test names used
- [ ] Test docstrings explain what's being tested

### Common Patterns

**Testing validation:**
```python
def test_invalid_quantity_zero(self):
    api = mock_api({})
    with patch("builtins.print") as mock_print:
        cmd_market_buy_order(api, make_args(
            item_id="ore_iron",
            quantity=0,
            price=50,
            json=False
        ))

    output = mock_print.call_args_list[0][0][0]
    self.assertIn("Error", output)
    api._post.assert_not_called()  # Should not reach API
```

**Testing error handling:**
```python
def test_insufficient_credits_error(self):
    api = mock_api({"error": {"message": "Insufficient credits"}})
    with patch("builtins.print") as mock_print:
        cmd_insurance_buy(api, make_args(ticks=50, json=False))

    output = mock_print.call_args_list[0][0][0]
    self.assertIn("ERROR", output)
    self.assertIn("Insufficient credits", output)
```

**Testing JSON output:**
```python
def test_json_output(self):
    response = {"result": {"order_id": "buy-123"}}
    api = mock_api(response)
    with patch("builtins.print") as mock_print:
        cmd_market_buy_order(api, make_args(
            item_id="ore_iron",
            quantity=100,
            price=50,
            json=True
        ))

    output = mock_print.call_args_list[-1][0][0]  # Last print is JSON
    parsed = json.loads(output)
    self.assertEqual(parsed["result"]["order_id"], "buy-123")
```

## Adding New Tests

### Unit Tests
1. Create `tests/test_yourfeature.py`
2. Import from `spacemolt.*`
3. Use `unittest.TestCase`
4. Follow the testing standards above
5. Run with `python3 -m unittest tests.test_yourfeature -v`
6. Check coverage: `coverage run -m unittest tests.test_yourfeature && coverage report`

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
