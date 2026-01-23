# Claude Code Hooks

Custom hooks for enhancing Claude Code CLI behavior.

## Hook Overview

| Hook | Event | Purpose |
|------|-------|---------|
| `normalize-line-endings.py` | PreToolUse (Write/Edit) | Converts CRLF/CR to LF |
| `gh-authorship-attribution.py` | PreToolUse (Bash) | Ensures proper attribution for AI-assisted GitHub contributions |
| `prefer-modern-tools.py` | PreToolUse (Bash) | Suggests fd/rg instead of find/grep |
| `detect-cd-pattern.py` | PreToolUse (Bash) | Warns on global cd, allows subshell pattern |
| `auto-unsandbox-pbcopy.py` | PreToolUse (Bash) | Auto-approves and unsandboxes pbcopy |
| `prefer-gh-for-own-repos.py` | PreToolUse (WebFetch/Bash) | Suggests gh CLI for Jython1415's repositories |
| `gh-web-fallback.py` | PreToolUse (Bash) | Proactively guides to GitHub API when gh unavailable (Web environment) |
| `gh-fallback-helper.py` | PostToolUseFailure (Bash) | Guides Claude to use GitHub API when gh CLI unavailable |
| `gpg-signing-helper.py` | PostToolUse/PostToolUseFailure (Bash) | Guides Claude on GPG signing issues |
| `detect-heredoc-errors.py` | PostToolUse/PostToolUseFailure (Bash) | Provides heredoc workarounds |
| `suggest-uv-for-missing-deps.py` | PostToolUseFailure (Bash) | Suggests uv run with PEP 723 for import errors |

## Development Guidelines

### PEP 723 Header
All hooks use inline script dependencies:
```python
#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
```

### JSON Output Requirements
- **Always output valid JSON** (even empty `{}`)
- Use `hookSpecificOutput` wrapper
- Include `hookEventName` matching the event type

### Testing Hooks
```bash
# Test with sample input
echo '{"tool_name":"Bash","tool_input":{"command":"echo test"}}' | uv run --script hooks/hookname.py

# Check output is valid JSON
echo '{"test":"data"}' | uv run --script hooks/hookname.py | jq .
```

### Error Handling
```python
try:
    # Hook logic
    input_data = json.load(sys.stdin)
    # ... process ...
except Exception:
    print("{}")  # Always output valid JSON on error
    sys.exit(1)
```

### PostToolUseFailure Notes
- Error is in top-level `"error"` field (not `tool_result.error`)
- `decision: "block"` is parsed but NOT acted upon
- Use `additionalContext` for guidance instead

## Configuration in settings.json

Hooks are configured in `settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "uv run --script ~/.claude/hooks/normalize-line-endings.py"
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": "uv run --script ~/.claude/hooks/gpg-signing-helper.py"
        }]
      }
    ]
  }
}
```

## Testing Hooks

### Test Structure

Hook tests are located in `hooks/tests/` directory:
- Each hook has a corresponding test file: `test_<hookname>.py`
- Tests use pytest with PEP 723 inline dependencies
- Tests can be run individually or all together

### Running Tests

**Run all hook tests:**
```bash
(cd hooks/tests && uv run pytest -v)
```

**Run specific hook test:**
```bash
uv run --script hooks/tests/test_detect_cd_pattern.py
```
Or with pytest:
```bash
(cd hooks/tests && uv run pytest test_detect_cd_pattern.py -v)
```

**Run tests with specific options:**
```bash
(cd hooks/tests && uv run pytest -v -k "subshell")  # Run only tests matching "subshell"
(cd hooks/tests && uv run pytest --tb=short)        # Short traceback format
```

### Writing Hook Tests

Each test file should:
1. Use PEP 723 header with `pytest>=7.0.0` dependency
2. Include a helper function to run the hook with test input
3. Have comprehensive test cases covering:
   - Happy path (correct behavior, returns `{}`)
   - Error cases (warnings/guidance)
   - Edge cases (spacing, special characters, etc.)
   - JSON validity
   - Event name correctness

**Example test structure:**
```python
#!/usr/bin/env python3
# /// script
# dependencies = ["pytest>=7.0.0"]
# ///
import json
import subprocess
from pathlib import Path

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
    def test_case_name(self):
        output = run_hook("Bash", "some command")
        assert output == {}, "Description of expected behavior"
```

### Test Coverage for detect-cd-pattern

The `detect-cd-pattern.py` hook has 14 tests covering:
- ✅ Subshell pattern allowed: `(cd dir && cmd)` → `{}`
- ✅ Global cd patterns warned: `cd dir && cmd` → warning
- ✅ Semicolon patterns warned: `cd dir; cmd` → warning
- ✅ No cd returns empty: `pytest /path` → `{}`
- ✅ Non-Bash tools ignored: `Read` tool → `{}`
- ✅ JSON validity in all cases
- ✅ Correct event name in warnings
- ✅ Target directory included in guidance

### Test Coverage for prefer-gh-for-own-repos

The `prefer-gh-for-own-repos.py` hook has 37 tests covering:
- ✅ WebFetch detection: GitHub URLs for Jython1415 repos trigger suggestion
- ✅ Bash/curl detection: curl commands with GitHub API URLs trigger suggestion
- ✅ Owner filtering: Only Jython1415's repos trigger (case-sensitive)
- ✅ gh availability: No suggestion when gh CLI unavailable
- ✅ Cooldown mechanism: Duplicate suggestions prevented within 60 seconds
- ✅ Cooldown expiry: Suggestions resume after cooldown period
- ✅ Non-matching tools: Read, Edit, Glob don't trigger
- ✅ Edge cases: Empty URLs, missing fields, malformed URLs handled
- ✅ URL patterns: Various GitHub URL formats detected correctly
- ✅ JSON validity and event name correctness
- ✅ Suggestion content: Mentions gh commands, owner, and examples

### Test Coverage for gh-web-fallback

The `gh-web-fallback.py` hook has 36 tests covering:
- ✅ Command detection: gh commands at start, parametrized shell operators (|, ;, &&, ||)
- ✅ False positive prevention: "sigh", "high" don't trigger (gh must be standalone)
- ✅ Environment detection: Only triggers when gh unavailable AND token available
- ✅ Cooldown mechanism: Duplicate suggestions prevented within 5 minutes
- ✅ Cooldown expiry: Suggestions resume after cooldown period
- ✅ Tool filtering: Parametrized non-Bash tools (WebFetch, Read, Edit)
- ✅ Edge cases: Empty commands, missing fields, malformed JSON handled
- ✅ JSON validity and event name correctness
- ✅ Output validation: Comprehensive content validation (GitHub API, jq, docs)
- ✅ Real-world scenarios: Integration test, cooldown behavior
- ✅ Complex commands: Complex flags and chained operations

## Adding New Hooks

1. Create Python script with PEP 723 header
2. Implement JSON input/output handling
3. Create test file in `hooks/tests/test_<hookname>.py`
4. Write comprehensive tests and verify they pass
5. Add to `settings.json` hooks configuration
6. Document in this README
7. Restart Claude Code session
