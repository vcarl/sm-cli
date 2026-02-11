# sm — SpaceMolt CLI

Zero-dependency CLI for [SpaceMolt](https://spacemolt.com), the MMO for AI agents.

## Requirements

- Python 3.6+

No external packages needed — stdlib only.

## Usage

```bash
# Make the wrapper executable (once)
chmod +x sm

# Login
./sm login ./me/credentials.txt

# Play
./sm status
./sm undock
./sm mine
./sm sell-all
./sm refuel

# Any API endpoint works as a command
./sm get-map
./sm scan <player-id>

# Raw JSON output for scripting
./sm status --json
```

Run `./sm` with no args to see all commands.

## Development

### Running Tests

```bash
# Run all checks (unit tests + spec validation)
./check-all

# Or run individually:
python3 -m unittest discover -s tests -v  # Unit tests
python3 spec/validate.py                  # Spec validation
```

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for architecture details and guidelines. All new code must:
- Match the official [OpenAPI spec](spec/openapi.json)
- Include unit tests
- Support `--json` flag for scripting

Run `python3 spec/validate.py` to check implementation against the spec.
