---
name: hook-development
description: Read this skill when working on hooks in .claude/hooks/ or plugins/claude-code-hooks/hooks/ - covers development process, PEP 723 patterns, JSON output, and testing philosophy
---

# Hook Development Skill

When working on hooks in `.claude/hooks/`, follow these guidelines.

## Hook Architecture

Hooks in this repository use a **symlink architecture** for cross-platform compatibility:

- **Source of truth**: `plugins/claude-code-hooks/hooks/`
- **Symlinks**: `.claude/hooks/*.py` -> `../../plugins/claude-code-hooks/hooks/*.py`
- **Why**: Claude Code Web uses `.claude/hooks/` directly; CLI can use plugins

When editing hooks, edit the plugin source files in `plugins/claude-code-hooks/hooks/`.

## Hook Development Process

1. Create Python script with PEP 723 header in `plugins/claude-code-hooks/hooks/`
2. Implement JSON input/output handling
3. Create symlink in `.claude/hooks/` pointing to the plugin file
4. Create test file in `.claude/hooks/tests/test_<hookname>.py`
5. Write comprehensive tests and verify they pass (`uv run pytest`)
6. Add to `.claude/settings.json` hooks configuration
7. Document in `.claude/hooks/README.md`
8. User restarts Claude Code session to apply

## PEP 723 Inline Dependencies

All hooks must include a PEP 723 header for inline script dependencies:

```python
#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
```

Add dependencies as needed:
```python
# /// script
# dependencies = ["requests>=2.28.0"]
# ///
```

Run hooks with `uv run --script hookname.py`.

## JSON Output Requirements

- **Always output valid JSON** (even empty `{}` on success or error)
- Use `hookSpecificOutput` wrapper for guidance
- Include `hookEventName` matching the event type

### Output Structure

**No action needed:**
```json
{}
```

**Provide guidance:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "Your guidance message here"
  }
}
```

### Blocking Tool Calls (PreToolUse only)

To actually block a command in a `PreToolUse` hook, use `permissionDecision: "deny"`:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Reason shown to Claude — explain why and what to do instead"
  }
}
```

**Common mistakes that do NOT block:**
- `hookSpecificOutput.decision: "block"` — not a recognized field in any position
- Top-level `decision: "block"` — the old deprecated format; avoid in new hooks
- Using `additionalContext` instead of `permissionDecisionReason` — `additionalContext` is injected before execution and is irrelevant on a deny

**Verify against docs:** When modifying blocking/decision fields, fetch the actual docs at `https://docs.anthropic.com/en/docs/claude-code/hooks` rather than trusting issue descriptions or AI-generated summaries. The hook API has deprecated fields that look plausible but do nothing.

### Error Handling Pattern

```python
try:
    input_data = json.load(sys.stdin)
    # ... process ...
except Exception:
    print("{}")  # Always output valid JSON on error
    sys.exit(1)
```

## Hook Event Types

| Event | Purpose | Key Fields |
|-------|---------|------------|
| `PreToolUse` | Before tool execution | `tool_name`, `tool_input` |
| `PostToolUse` | After successful execution | `tool_name`, `tool_input`, `tool_result` |
| `PostToolUseFailure` | After failed execution | `tool_name`, `tool_input`, `error` |

### PostToolUseFailure Notes

- Error is in top-level `"error"` field (not `tool_result.error`)
- `decision: "block"` is parsed but NOT acted upon by the system
- Use `additionalContext` for guidance instead of `decision`

## State Management

Many hooks need to rate-limit guidance to avoid repetition. Use per-session-id state files — **not global files** — for all advisory reminder hooks.

### Why per-session-id

Each Claude session is an isolated instance. `additionalContext` injected into Session A has zero effect on Session B. A global cooldown from Session A incorrectly silences Session B (which never received the guidance). Per-session-id files ensure each session gets its own cooldown.

### Per-session-id time-based cooldown (most hooks)

```python
COOLDOWN_PERIOD = 60  # seconds

def is_within_cooldown(session_id: str) -> bool:
    state_file = STATE_DIR / f"my-hook-cooldown-{session_id}"
    try:
        if not state_file.exists():
            return False
        return (time.time() - float(state_file.read_text().strip())) < COOLDOWN_PERIOD
    except Exception:
        return False

def record_suggestion(session_id: str):
    state_file = STATE_DIR / f"my-hook-cooldown-{session_id}"
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_file.write_text(str(time.time()))
    except Exception as e:
        print(f"Warning: {e}", file=sys.stderr)
```

In `main()`: `session_id = input_data.get("session_id", "")`

**Critical distinction**: Per-session-id files isolate cooldowns **between** sessions but do NOT eliminate the time-based cooldown **within** a session. A 300s cooldown scoped to `session_id` still re-fires every 300s in a long session. The guidance text should say "appears once per 5 minutes within a session" — not "once per session."

### True once-per-session (flag file)

If you want "show exactly once per session regardless of session length":

```python
def has_shown_this_session(session_id: str) -> bool:
    flag_file = STATE_DIR / f"my-hook-shown-{session_id}"
    return flag_file.exists()

def mark_shown(session_id: str):
    flag_file = STATE_DIR / f"my-hook-shown-{session_id}"
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    flag_file.touch()
```

Use empty flag files (existence = shown), no timestamp. Guidance text: "appears once per session."

### State directory

Use `~/.claude/hook-state/` (global) for hooks installed via the marketplace. State files are tiny; accumulation is negligible.

### Tests for stateful hooks

**Never reference `~/.claude/hook-state/` directly in test helpers.** Test code runs inside
a sandboxed Bash tool call; `unlink()` and `write_text()` on that path will fail with
`PermissionError`. (The hooks themselves work fine — they run as external subprocesses outside
the sandbox.)

Instead, redirect state to a writable temp dir via the `CLAUDE_HOOK_STATE_DIR` env var, which
both hooks support. Use a module-level constant so state persists across multiple `run_hook()`
calls within the same test (required for cooldown tests):

```python
import os
TEST_STATE_DIR = Path(os.environ.get("TMPDIR", "/tmp")) / "claude-hook-test-state"

def run_hook(command: str, session_id: str = "test-session-abc123", clear_state: bool = True) -> dict:
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": session_id,
    }
    if clear_state:
        state_file = TEST_STATE_DIR / f"my-hook-cooldown-{session_id}"
        if state_file.exists():
            state_file.unlink()
    TEST_STATE_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CLAUDE_HOOK_STATE_DIR"] = str(TEST_STATE_DIR)
    result = subprocess.run(
        ["uv", "run", "--script", str(HOOK_PATH)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(result.stdout)
```

Tests that write state directly (e.g., to simulate an expired cooldown) must also use
`TEST_STATE_DIR`, not `Path.home() / ".claude" / "hook-state"`.

## Testing Philosophy

**Test behavior, not content.** Guidance messages should be improvable without breaking tests.

### DO

- Verify that guidance is presented when expected
- Test trigger conditions (what activates the hook)
- Validate JSON output structure
- Check that hook activates/deactivates correctly

### DON'T

- Validate specific strings or phrases in guidance text
- Check for particular examples in output
- Assert on exact wording or formatting
- Test content that may evolve over time

### Test Categories

1. **Trigger Tests**: Verify hook activates on correct inputs
2. **Non-Trigger Tests**: Verify hook stays silent on incorrect inputs
3. **Structure Tests**: Validate JSON format and required fields
4. **Edge Case Tests**: Handle malformed input, missing fields, etc.

### Example Test Structure

```python
"""Unit tests for hookname.py hook"""
import json
import subprocess
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).parent.parent / "hookname.py"


def run_hook(tool_name: str, command: str) -> dict:
    """Helper to run hook and return parsed output"""
    input_data = {
        "tool_name": tool_name,
        "tool_input": {"command": command}
    }
    result = subprocess.run(
        ["uv", "run", "--script", str(HOOK_PATH)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )
    return json.loads(result.stdout)


class TestMyHook:
    def test_triggers_on_expected_input(self):
        output = run_hook("Bash", "some command")
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]

    def test_silent_on_unrelated_input(self):
        output = run_hook("Bash", "unrelated command")
        assert output == {}
```

## Running Tests

```bash
# Run all hook tests (481 tests)
uv run pytest

# Run specific hook test
uv run pytest .claude/hooks/tests/test_hookname.py

# Verbose output
uv run pytest -v

# Run tests matching pattern
uv run pytest -k "subshell"
```

## Hook Path Convention in settings.json

**Always use `$CLAUDE_PROJECT_DIR` for hook paths:**

```json
"command": "uv run --script \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/hookname.py"
```

Why not `~`? Tilde expands to current user's home, which differs in Claude Code Web.
Why not relative paths? They break when working directory changes.

## Manual Testing

Test hooks before committing:

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"test"}}' | uv run --script .claude/hooks/hookname.py
```

## See Also

- `.claude/hooks/README.md` - Comprehensive hook documentation and coverage details
- `.claude/hooks/tests/` - Test examples and patterns
- `plugins/claude-code-hooks/` - Plugin source (marketplace distribution)
- Root `CLAUDE.md` - Repository management instructions
