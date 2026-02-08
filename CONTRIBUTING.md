# Contributing to the `sm` CLI

## Architecture

```
client/
  sm                      # Shell wrapper — just calls cli.py
  spacemolt/
    cli.py                # Argparse setup, routing, COMMAND_MAP
    commands.py           # All command handlers + ENDPOINT_ARGS passthrough table
    api.py                # HTTP client, session management, notifications
  tests/
    test_cli.py           # Unit tests (run with: python3 -m unittest client.tests.test_cli -v)
```

There are three ways to expose an API endpoint through `sm`, from least to most effort:

## 1. Passthrough (zero code)

Any endpoint not in `COMMAND_MAP` is automatically handled by `cmd_passthrough`. It converts the command name from dashes to underscores, maps positional and `key=value` arguments to the API body, and pretty-prints the JSON result.

```
sm get_map                         # no args needed
sm scan player-uuid-123            # positional arg
sm attack target_id=player-uuid    # key=value arg
```

To improve the argument mapping for a passthrough endpoint, add an entry to `ENDPOINT_ARGS` in `commands.py`:

```python
ENDPOINT_ARGS = {
    # ...
    "new_endpoint": ["first_arg", "second_arg:int", "optional_flag:bool"],
}
```

Type suffixes: `:int` converts to integer, `:bool` converts `true/1/yes` to `True`. Default is string. The parameter name is everything before the colon.

That's it — no other code changes needed.

## 2. Formatted handler (add a function + two registrations)

When you want nicer output than raw JSON, add a handler function and register it.

**Step 1: Write the handler in `commands.py`**

```python
def cmd_example(api, args):
    as_json = getattr(args, "json", False)
    resp = api._post("api_endpoint_name", {"param": args.my_param})
    if as_json:
        print(json.dumps(resp, indent=2))
        return
    if resp.get("error"):
        err = resp["error"]
        print(f"ERROR: {err.get('message', err) if isinstance(err, dict) else err}")
    else:
        r = resp.get("result", {})
        print(f"Something: {r.get('field', '?')}")
```

Key conventions:
- Check `getattr(args, "json", False)` to support `--json`.
- Handle `resp.get("error")` — errors can be strings or `{"code": ..., "message": ...}` dicts.
- Pull data from `resp.get("result", {})`.

**Step 2: Register in `cli.py`**

Add an argparse subparser:

```python
p_example = sub.add_parser("example", help="One-line description")
p_example.add_argument("my_param", help="What this param is")
```

Add to `COMMAND_MAP`:

```python
COMMAND_MAP = {
    # ...
    "example": commands.cmd_example,
}
```

**Step 3: Add a test in `tests/test_cli.py`**

```python
class TestCmdExample(unittest.TestCase):
    def test_success(self):
        api = mock_api({"result": {"field": "value"}})
        with patch("builtins.print") as mock_print:
            cmd_example(api, make_args(my_param="x", json=False))
        self.assertIn("value", mock_print.call_args[0][0])
```

## 3. Compound commands (multi-step logic)

For commands that call the API multiple times (like `sell-all`), just write the handler and register it. There's no special framework — look at `cmd_sell_all` as an example. Remember to `time.sleep(11)` between mutation calls to respect the rate limit.

## Running tests

```bash
python3 -m unittest client.tests.test_cli -v
```

Tests mock `api._post()` so they never hit the network. Use `mock_api(response_dict)` to set the return value and `make_args(key=val)` to build an argparse-like namespace.

## Conventions

- Mutation commands (mine, sell, attack, etc.) are rate-limited to 1 per 10s tick. Query commands (status, pois, etc.) are not.
- The `--json` flag should be supported by all formatted handlers so scripts can parse the output.
- Update the help epilog in `build_parser()` if you're adding a frequently-used command.
- Update the `COMMAND_MAP` count assertion in `TestCommandMapCompleteness.test_count` (currently 30) when adding new entries.
