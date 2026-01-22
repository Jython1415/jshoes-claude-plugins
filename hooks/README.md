# Claude Code Hooks

Custom hooks for enhancing Claude Code CLI behavior.

## Hook Overview

| Hook | Event | Purpose |
|------|-------|---------|
| `normalize-line-endings.py` | PreToolUse (Write/Edit) | Converts CRLF/CR to LF |
| `prefer-modern-tools.py` | PreToolUse (Bash) | Suggests fd/rg instead of find/grep |
| `detect-cd-pattern.py` | PreToolUse (Bash) | Warns on global cd, allows subshell pattern |
| `auto-unsandbox-pbcopy.py` | PreToolUse (Bash) | Auto-approves and unsandboxes pbcopy |
| `prefer-gh-for-own-repos.py` | PreToolUse (WebFetch/Bash) | Suggests gh CLI for Jython1415's repositories |
| `gh-fallback-helper.py` | PostToolUseFailure (Bash) | Guides Claude to use GitHub API when gh CLI unavailable |
| `gpg-signing-helper.py` | PostToolUse/PostToolUseFailure (Bash) | Guides Claude on GPG signing issues |
| `detect-heredoc-errors.py` | PostToolUse/PostToolUseFailure (Bash) | Provides heredoc workarounds |

## Hook Details

### normalize-line-endings.py

**Event**: PreToolUse (Write, Edit)

**Purpose**: Automatically normalizes line endings to LF (Unix-style) when writing or editing files.

**Behavior**:
- Detects CRLF (`\r\n`) or CR (`\r`) in content
- Converts to LF (`\n`)
- Auto-approves the operation with normalized content

### prefer-modern-tools.py

**Event**: PreToolUse (Bash)

**Purpose**: Directs Claude to use modern, faster alternatives for common commands when available.

**Behavior**:
- Detects usage of `find` command → suggests `fd` if available
- Detects usage of `grep` command → suggests `rg` (ripgrep) if available
- Checks tool availability dynamically using `which`
- Provides context-aware guidance with example syntax

**Benefits**:
- `fd`: Faster file search, simpler syntax, respects .gitignore by default
- `rg`: Significantly faster grep, respects .gitignore, better output formatting

### detect-cd-pattern.py

**Event**: PreToolUse (Bash)

**Purpose**: Detects when global `cd` patterns are used and suggests using absolute paths or subshell patterns instead.

**Behavior**:
- **Warns** on global cd patterns: `cd dir && cmd`, `cd dir; cmd`, standalone `cd dir`
- **Allows** (silent) subshell pattern: `(cd dir && cmd)` - this is the correct pattern per CLAUDE-global.md
- Provides guidance on using absolute paths (best) or subshell pattern (acceptable)
- Explains why global cd changes are problematic

**Triggers on**:
- `cd dir && cmd` - global directory change
- `cd dir; cmd` - global directory change with semicolon
- Standalone `cd dir` at command start or after separators

**Does NOT trigger on**:
- `(cd dir && cmd)` - subshell pattern (correct usage)
- Commands without cd

**Benefits**:
- Prevents global working directory changes that affect the session
- Encourages explicit absolute paths for clarity
- Promotes subshell isolation when cd is necessary
- Better for debugging and command history

**Recommended patterns**:
- ✅ Best: `pytest /foo/bar/tests` (absolute path)
- ✅ OK: `(cd /foo/bar && pytest tests)` (subshell isolation)
- ❌ Bad: `cd /foo/bar && pytest tests` (global change)

### auto-unsandbox-pbcopy.py

**Event**: PreToolUse (Bash)

**Purpose**: Automatically approves `pbcopy` commands and disables sandbox for them (pbcopy requires unsandboxed mode).

**Behavior**:
- Detects commands containing `pbcopy`
- Auto-approves the permission
- Sets `dangerouslyDisableSandbox: true`

### prefer-gh-for-own-repos.py

**Event**: PreToolUse (WebFetch, Bash)

**Purpose**: Suggests using `gh` CLI when Claude tries to access GitHub repositories owned by Jython1415 via WebFetch or curl.

**Behavior**:
- Detects when WebFetch or Bash (curl) is used to access GitHub URLs for Jython1415's repositories
- Checks if `gh` CLI is available using `which gh`
- If `gh` is available, provides guidance to use it instead
- Includes 60-second cooldown mechanism to avoid duplicate suggestions when Claude intentionally uses fetch back-to-back
- After cooldown expires, suggestions resume if behavior reverts to fetch/curl

**Triggers on**:
- WebFetch with URLs containing `github.com/Jython1415/` or `api.github.com/repos/Jython1415/`
- Bash commands with curl accessing the above URLs

**Does NOT trigger when**:
- `gh` CLI is not available (falls back to API access)
- Within 60-second cooldown period since last suggestion
- Accessing repositories owned by other users
- Using non-GitHub URLs

**Benefits**:
- `gh` CLI provides a more direct interface for GitHub operations
- Better integration with GitHub authentication
- Simpler syntax for common operations
- Acknowledges that API access might be intentional for specific use cases

**Example suggestions**:
- View issue: `gh issue view 10 --repo Jython1415/repo`
- List PRs: `gh pr list --repo Jython1415/repo`
- Get JSON: `gh issue view 10 --json title,body,comments --repo Jython1415/repo`

**Cooldown mechanism**:
- State stored in `~/.claude/hook-state/prefer-gh-cooldown`
- Prevents duplicate suggestions when Claude uses fetch multiple times consecutively
- Allows suggestions to resume after 60 seconds if behavior reverts

### gh-fallback-helper.py

**Event**: PostToolUseFailure (Bash)

**Purpose**: Detects when `gh` CLI is unavailable but `GITHUB_TOKEN` environment variable exists, and provides guidance on using the GitHub REST API with curl instead.

**Triggers on**:
- Command contains `gh`
- Error contains "command not found" or "not found"
- `GITHUB_TOKEN` is available in environment

**Guidance provided**:
- How to use GitHub REST API with curl
- Common API patterns (list issues, create PR, update PR, search)
- Token authentication format
- JSON parsing tips with jq/python
- Specific conversion example for the failed gh command

**Example patterns**:
- List issues: `curl -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/OWNER/REPO/issues"`
- Create PR: `curl -X POST -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/OWNER/REPO/pulls" -d '{"title":"...","head":"branch","base":"main"}'`

### gpg-signing-helper.py

**Event**: PostToolUse, PostToolUseFailure (Bash)

**Purpose**: Detects GPG signing failures and provides guidance to use `--no-gpg-sign`.

**Triggers on**:
- "gpg failed to sign the data"
- "gpg: can't connect to the agent"
- "No agent running"

**Guidance**: Advises Claude to use `git commit --no-gpg-sign -m "message"` in sandbox mode.

### detect-heredoc-errors.py

**Event**: PostToolUse, PostToolUseFailure (Bash)

**Purpose**: Detects heredoc failures in sandbox mode and provides workarounds.

**Triggers on**: "can't create temp file for here document"

**Workarounds provided**:
1. Multiple `-m` flags for git commits
2. ANSI-C quoting (`$'...'`) for inline strings
3. Write tool to create files first

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

## Adding New Hooks

1. Create Python script with PEP 723 header
2. Implement JSON input/output handling
3. Create test file in `hooks/tests/test_<hookname>.py`
4. Write comprehensive tests and verify they pass
5. Add to `settings.json` hooks configuration
6. Document in this README
7. Restart Claude Code session
