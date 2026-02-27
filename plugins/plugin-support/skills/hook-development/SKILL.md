---
name: hook-development
description: Read this skill when working on Claude Code hook development - covers hook architecture, PEP 723 patterns, JSON output, and testing philosophy
---

# Hook Development Skill

When working on Claude Code hooks, follow these guidelines.

## Hook Architecture

Claude Code hooks are Python scripts executed by the Claude Code CLI at specific lifecycle events. They are configured in `.claude/settings.json` (or `settings.local.json`) and run outside the Claude Code process.

Hooks live wherever you put them — common locations:
- `~/.claude/hooks/` — global hooks (apply to all projects)
- `.claude/hooks/` — project-local hooks (checked in or gitignored)
- A plugin directory distributed via the marketplace

When editing hooks, edit the source files directly (not symlinks or copies).

## Hook Development Process

1. Create a Python script with a PEP 723 header
2. Implement JSON input/output handling
3. Add the hook to your `.claude/settings.json` hooks configuration
4. Create a test file alongside or near the hook
5. Write comprehensive tests and verify they pass (`uv run pytest`)
6. Restart the Claude Code session to apply changes

## PEP 723 Inline Dependencies

All hooks must include a PEP 723 header:

**No third-party dependencies** — use `requires-python` only:
```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
```

**With third-party dependencies** — use `dependencies`:
```python
# /// script
# dependencies = ["requests>=2.28.0"]
# ///
```

Do not use `dependencies = []` (an empty list). `uv` does extra work
(writing to TMPDIR) when `dependencies` is present, even as an empty
list. Use `requires-python` for dependency-free hooks instead.

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

## Hook Lifecycle Placement

Choose the right event type for your hook's concern:

| Event | Use for |
|-------|---------|
| `SessionStart` | One-time session setup: creating directories, environment checks |
| `PreToolUse` | Per-command validation, blocking, or pre-execution guidance |
| `PostToolUse` | Per-command post-execution guidance or logging |
| `PostToolUseFailure` | Guidance when a tool call fails |

**Rules:**
- Use `SessionStart` for setup that should happen once per session, not on every tool call.
- Use `PreToolUse`/`PostToolUse` only for per-command concerns — they run on every matching tool call.
- Never use a `SessionStart` hook to reset shared state. Use `session_id` scoping so each session manages its own state independently.

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

Use `~/.claude/hook-state/` for state files. State files are tiny; accumulation is negligible. Support a `CLAUDE_HOOK_STATE_DIR` env var override so tests can redirect state to a temp directory.

### Tests for stateful hooks

**Never reference `~/.claude/hook-state/` directly in test helpers.** Test code that calls `unlink()` or `write_text()` on that path can fail in sandboxed environments. (Hooks themselves work fine — they run as external subprocesses.)

Instead, redirect state via a `CLAUDE_HOOK_STATE_DIR` env var. Use a module-level constant so state persists across multiple `run_hook()` calls within the same test (required for cooldown tests):

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

HOOK_PATH = Path(__file__).parent.parent / "hooks" / "hookname.py"
# ^ assumes tests/test_hookname.py → hooks/hookname.py sibling layout


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
# Run all tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_hookname.py

# Verbose output
uv run pytest -v

# Run tests matching a pattern
uv run pytest -k "subshell"
```

## Hook Path Convention in settings.json

For project-local hooks, use `$CLAUDE_PROJECT_DIR` so paths resolve correctly regardless of working directory or user:

```json
"command": "uv run --script \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/hookname.py"
```

For global hooks installed to `~/.claude/hooks/`, you can use the full path directly:

```json
"command": "uv run --script \"/Users/yourname/.claude/hooks/hookname.py\""
```

Why not `~`? Tilde expands to current user's home, which differs in Claude Code Web.
Why not relative paths? They break when working directory changes.

## Manual Testing

Test hooks before committing:

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"test"}}' | uv run --script path/to/hookname.py
```

## Shell Wrapper Patterns

When `run-with-fallback.sh` or a similar shell wrapper needs to spawn Python and pass hook data:

**Pass large payloads via env vars, not `sys.argv`.** Hook input can be large — a Write hook carrying a big file can exceed the shell's ARG_MAX (~1 MB on macOS), causing the `python3` call to silently fail and drop the log entry with no error. Use env vars instead:

```bash
HOOK_LOG_INPUT="$INPUT" HOOK_LOG_OUTPUT="$output" uv run python -c "
import os, json
raw = os.environ['HOOK_LOG_INPUT']
..."
```

Read with `os.environ['HOOK_LOG_INPUT']` on the Python side. Env vars are not subject to the same ARG_MAX constraint as positional arguments.

## Performance

- Hooks run on every matching tool call — keep them fast.
- No network requests in hook code. Latency is unacceptable in the hot path.
- No heavy computation. Parse input, check a condition, write a state file, output JSON — that's the expected pattern.
- Focus on correctness and lifecycle placement over micro-optimization.
- This skill assumes `uv` is available; `uv run --script` overhead is acceptable.

## See Also

- [Claude Code Hooks documentation](https://docs.anthropic.com/en/docs/claude-code/hooks)
