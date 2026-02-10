# Tech Debt — spacemolt-client

Tracked issues from code review. Grouped by severity/category.

---

## Bugs

### 1. `missions.py:72` — Misleading f-string literal
```python
print(f"No active missions. ({0}/{max_m} slots used)")
```
`{0}` in an f-string evaluates the integer literal `0`. Functionally correct (it IS 0 when `not missions`), but reads like a `.format()` positional placeholder accidentally put inside an f-string. Should be a plain string: `(0/{max_m} slots used)`.

### 2. `passthrough.py:395-404` — All args treated as required
```python
if specs and not body:
    ...
    return
missing = [_arg_name(s) for s in specs if _arg_name(s) not in body]
if missing:
    ...
    return
```
Every spec is treated as required — there's no way to define optional parameters. Any endpoint with optional args will show "Missing:" errors if they're not all provided.

### 3. `api.py:91` — Retry passes mutated body
After session expiry re-login, `self._post(endpoint, body, ...)` is called with the same `body` dict, but that dict already had the *old* `session_id` injected. The retry then overwrites it with the new session ID, so it works — but only because of mutation side effects. Fragile if anything changes the flow. Fix: copy body before injecting session_id, or pop the old one before retry.

---

## Code quality

### 4. `actions.py:228` — Identity check for sleep gating
```python
if item is not items[-1]:
    time.sleep(11)
```
Uses `is not` (identity) instead of index comparison. Works in practice since API response dicts are distinct objects, but an index-based check (`for i, item in enumerate(items)`) would be more robust. Also sleeps even after failed sells (the `except` catches errors but execution continues to the sleep).

### 5. Duplicated utility code across metrics modules
`_normalize_endpoint()` and `_resolve_player()` are copy-pasted between `metrics.py` and `metrics_avg.py`. Should be extracted to a shared module.

### 6. `cli.py:307-339` — Repeated error handling pattern
The same `try/handler()/except APIError` block appears 3 times. Could be extracted to a helper like `_run_handler(fn, *args)`.

### 7. `actions.py:6` — Redundant ternary
```python
cred_file = args.cred_file if args.cred_file else None
```
`args.cred_file` is already `None` when not set. Simplify to `cred_file = args.cred_file`.

---

## Robustness / defensiveness

### 8. No type validation on API responses before arithmetic
Several sort keys negate values from the API (`-s.get("level", 0)`) which will `TypeError` if the API returns a string. Affects: `skills.py:7`, `info.py:92` sort on distance, recipe sorting.

### 9. `info.py:427` — `result.items()` assumes dict
```python
for k, v in result.items():
```
If `result` is a list or None (malformed response), this crashes with `AttributeError`.

### 10. `metrics.py:47` / `metrics_avg.py:188` — No Content-Length bound
```python
length = int(self.headers.get("Content-Length", 0))
body = self.rfile.read(length).decode()
```
A huge Content-Length value causes unbounded memory allocation. Should cap at a reasonable max (e.g. 1MB). Low severity since these are local dev tools, not public-facing.

---

## Test infrastructure / Documentation

### 13. `test_integration.sh` — No login failure handling
Login result isn't checked; if it fails, all subsequent tests run against an unauthenticated session and produce misleading results. Should `set -e` or check the exit code after login.

### 14. `README.md` suggests pytest but project uses unittest
```
python3 -m pytest tests/ -v
```
Should be `python3 -m unittest tests.test_cli -v`. No mention of `test_integration.sh`.

### 15. `CONTRIBUTING.md` rate-limit guidance is ambiguous
Says "10s tick" in one place and `time.sleep(11)` in another. Should clarify the relationship (the 11s sleep is intentionally > the 10s server tick to avoid rate-limit errors).
