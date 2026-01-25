#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
detect-cd-pattern: Detect global cd patterns and suggest using absolute paths or subshell isolation.

Event: PreToolUse (Bash)

Purpose: Detects when global `cd` patterns are used and suggests using absolute paths or subshell patterns instead.

Behavior:
- Warns on global cd patterns: `cd dir && cmd`, `cd dir; cmd`, standalone `cd dir`
- Allows (silent) subshell pattern: `(cd dir && cmd)` - this is the correct pattern per CLAUDE-global.md
- Provides guidance on using absolute paths (best) or subshell pattern (acceptable)
- Explains why global cd changes are problematic

Triggers on:
- `cd dir && cmd` - global directory change
- `cd dir; cmd` - global directory change with semicolon
- Standalone `cd dir` at command start or after separators

Does NOT trigger on:
- `(cd dir && cmd)` - subshell pattern (correct usage)
- Commands without cd

Benefits:
- Prevents global working directory changes that affect the session
- Encourages explicit absolute paths for clarity
- Promotes subshell isolation when cd is necessary
- Better for debugging and command history

Recommended patterns:
- Best: `pytest /foo/bar/tests` (absolute path)
- OK: `(cd /foo/bar && pytest tests)` (subshell isolation)
- Bad: `cd /foo/bar && pytest tests` (global change)

Limitations:
- Command pattern detection is regex-based; unusual command structures may not be detected
- Only monitors Bash tool (not other command execution methods)
"""
import json
import sys
import re

def main():
    input_data = json.load(sys.stdin)

    # Only process Bash tool PreToolUse
    if input_data.get("tool_name") != "Bash":
        print("{}")
        sys.exit(0)

    # Get the command that will be run
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Patterns to detect WRONG cd usage (non-subshell):
    # Only warn about:
    # 1. cd dir && cmd - sequential pattern (global directory change)
    # 2. cd dir; cmd - semicolon pattern (global directory change)
    # 3. standalone cd dir
    #
    # DO NOT warn about:
    # - (cd dir && cmd) - subshell pattern (this is CORRECT per CLAUDE-global.md)
    # - Any command wrapped entirely in parentheses (subshell isolation)

    # Check if entire command is wrapped in parentheses (subshell)
    # This is a simple heuristic: starts with ( and ends with matching )
    stripped = command.strip()
    if stripped.startswith('(') and stripped.endswith(')'):
        # Command is in a subshell - cd is isolated, so it's OK
        print("{}")
        sys.exit(0)

    # Also check for (cd ...) pattern anywhere in the command
    if re.search(r'\(\s*cd\s+', command):
        print("{}")
        sys.exit(0)

    # Now check for non-subshell cd patterns (the BAD ones)
    cd_patterns = [
        r'(?:^|;|\||&&)\s*cd(?:\s+|$|(?=;|\||&&))',  # cd at start or after separator (with args, standalone, or before separator)
    ]

    has_cd = any(re.search(pattern, command) for pattern in cd_patterns)

    if not has_cd:
        print("{}")
        sys.exit(0)

    # Extract the directory being changed to (for better guidance)
    cd_match = re.search(r'cd\s+([^\s;&|)]+)', command)
    target_dir = cd_match.group(1) if cd_match else "<directory>"

    # Provide guidance via additionalContext
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": f"""GLOBAL CD DETECTED: The command uses `cd` which changes the working directory globally.

**Best Practice**: Use absolute paths or subshell pattern instead.

**Why avoid global cd?**
- Changes working directory for the entire session
- Can cause confusion and errors in subsequent commands
- Makes command history harder to follow

**Recommended Approaches**:

1. **Use absolute paths** (best):
   ✅ `pytest /foo/bar/tests`
   ✅ `npm build --prefix /path/to/src`
   ✅ `git -C /path/to/project status`

2. **Use subshell pattern** (if cd is necessary):
   ✅ `(cd {target_dir} && <command>)`

   The subshell `()` ensures the directory change is isolated and doesn't affect the session.

**Your command**:
❌ Current: `cd {target_dir} && ...`
✅ Better:  Use absolute paths with the command
✅ OK:     `(cd {target_dir} && ...)` (subshell keeps change isolated)"""
        }
    }

    print(json.dumps(output))
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        # On error, output empty JSON as per hook guidelines
        print(json.dumps({}))
        sys.exit(1)
