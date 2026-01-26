---
name: hook-development
description: Guidance for developing and testing hooks in claude-code-config repository
disable-model-invocation: true
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
