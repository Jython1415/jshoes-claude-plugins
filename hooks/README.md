# Claude Code Hooks

Custom hooks for enhancing Claude Code CLI behavior.

## Hook Overview

| Hook | Event | Purpose |
|------|-------|---------|
| `normalize-line-endings.py` | PreToolUse (Write/Edit) | Converts CRLF/CR to LF |
| `prefer-modern-tools.py` | PreToolUse (Bash) | Suggests fd/rg instead of find/grep |
| `auto-unsandbox-pbcopy.py` | PreToolUse (Bash) | Auto-approves and unsandboxes pbcopy |
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

### auto-unsandbox-pbcopy.py

**Event**: PreToolUse (Bash)

**Purpose**: Automatically approves `pbcopy` commands and disables sandbox for them (pbcopy requires unsandboxed mode).

**Behavior**:
- Detects commands containing `pbcopy`
- Auto-approves the permission
- Sets `dangerouslyDisableSandbox: true`

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

## Adding New Hooks

1. Create Python script with PEP 723 header
2. Implement JSON input/output handling
3. Test manually with sample input
4. Add to `settings.json` hooks configuration
5. Document in this README
6. Restart Claude Code session
