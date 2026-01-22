#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Detect cd usage patterns and suggest using absolute paths instead.
Promotes better practices by avoiding directory changes in Bash commands.
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

    # Patterns to detect cd usage:
    # 1. (cd dir && cmd) - subshell pattern
    # 2. cd dir && cmd - sequential pattern
    # 3. cd dir; cmd - semicolon pattern
    # 4. standalone cd dir

    # Check for cd patterns
    cd_patterns = [
        r'\(\s*cd\s+',           # (cd ...
        r'(?:^|;|\||&&)\s*cd\s+',  # cd at start or after separator
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
            "additionalContext": f"""CD PATTERN DETECTED: The command uses `cd` to change directories.

**Best Practice**: Maintain your current working directory and use absolute paths instead.

**Why avoid cd?**
- Preserves current working directory throughout the session
- Makes commands more explicit and easier to understand
- Reduces context-switching and potential errors
- Better for command history and debugging

**Recommended Approach**:
Instead of: `cd {target_dir} && <command>`
Use: `<command> /absolute/path/to/target`

**Examples**:
❌ Bad:  `cd /foo/bar && pytest tests`
✅ Good: `pytest /foo/bar/tests`

❌ Bad:  `(cd src && npm build)`
✅ Good: `npm build --prefix /path/to/src` (or run from src directory)

❌ Bad:  `cd project && git status`
✅ Good: `git -C /path/to/project status`

**Note**: Only use `cd` if the user explicitly requests it, or if the tool/command requires being run from a specific directory without an alternative."""
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
