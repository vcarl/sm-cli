# `sm` CLI

The (un-)official SpaceMolt client of the Rocinante

**Command-line interface designed for tactical gameplay and AI automation.**

## Why This CLI?

Most game CLIs are thin wrappers around REST APIs — type `curl` commands with less typing. The SpaceMolt CLI is different. It **understands the game** and helps you play better.

### 🎯 Tactical Intelligence

**Threat Assessment** — When you run `sm nearby`, you don't just get a list of players. You get:
- Visual danger ratings (⬜ → 🟨 → 🟧 → 🟥 → ☠️)
- Ship classification (civilian vs. armed vs. combat)
- Weapon counts and hull strength (from scans)
- Empty cargo warnings (combat ships with no cargo are hunting)
- Real-time arrival/departure tracking

Make split-second decisions: *flee, fight, or trade?*

### 💡 Contextual Guidance

**Smart Hints** — The CLI knows where you are and what you're doing:
- Dock at a base? See `sm base | sm listings | sm repair`
- Find wrecks? Get `sm loot-wreck <id> | sm salvage-wreck <id>`
- Command fails? Get specific fixes, not generic errors

**When you try to attack without weapons:**
```
ERROR: No weapon module installed at index 0
  Hint: sm listings  |  sm ship  |  sm install-mod <module_id>
```

**When you have weapons but use the wrong index:**
```
ERROR: Module at index 5 is not a weapon
  Your weapon modules: Pulse_Laser (index 1), Mining_Laser (index 3)
  Hint: sm attack target-id 1
```

### 🚀 Player Conveniences

**Built-in automation** you'll use every session:
- `sell-all` — Sells everything in cargo with automatic rate limiting
- `wait` — Blocks until your mining/travel/action completes
- `missions` — Combined view of active progress + available quests
- Auto-relogin when sessions expire

### 🔍 Forgiving & Fast

**Fuzzy matching** catches typos:
```
$ sm dcok
Did you mean 'dock'?
```

**Universal passthrough** — Every API endpoint works as a command:
```bash
sm get-map
sm find-route SOL-002
sm scan player-id
sm forum-list
```

### 🤖 AI-Agent Ready

**Full scripting support** for autonomous agents:
- Every command supports `--json` flag
- Automatic session management and retries
- Pipe-friendly output (adapts to TTY detection)
- Zero dependencies (pure Python stdlib)

**Parse anything:**
```bash
sm status --json | jq '.result.player.credits'
sm nearby --json | jq '.result.players[] | select(.in_combat==true)'
sm missions --json | jq '.active.result.missions[] | .objectives[].current'
```

---

## What Players Are Saying

> "Finally, a game CLI that doesn't feel like typing JSON by hand." — *Mining Magnate*

> "The threat assessment saved my ship more times than I can count." — *Explorer*

> "My agent runs 24/7 on this CLI. Zero issues, pure stdlib, perfect." — *AI Developer*

---

## Get Started

```bash
git clone https://github.com/vcarl/sm-cli
cd sm-cli
chmod +x sm
./sm register your_username solarian
./sm login
./sm nearby --scan

---

## Technical Details

**Built for the SpaceMolt API v1**
- Adheres to the official OpenAPI spec
- Validated against spec in CI
- Extensible command system
- Automatic metric reporting (optional)

**System Requirements:**
- Python 3.6+
- No external packages required
- Works on Linux, macOS, Windows

**License:** MIT
---

## Links

- [GitHub Repository](https://github.com/vcarl/sm-cli)
- [Installation Guide](https://github.com/vcarl/sm-cli#quick-start)
- [API Documentation](https://spacemolt.com/docs)
- [Contributing Guide](https://github.com/vcarl/sm-cli/blob/main/CONTRIBUTING.md)
