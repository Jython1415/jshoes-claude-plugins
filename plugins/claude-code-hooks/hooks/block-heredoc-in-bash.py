#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""
block-heredoc-in-bash: Block heredoc syntax in Bash commands before it silently corrupts data in sandbox mode.

Event: PreToolUse (Bash)

Purpose: Detects heredoc syntax (`<<EOF`, `<<'EOF'`, `<<"EOF"`, `<<-EOF`, etc.) in Bash
commands and blocks them before execution. In sandbox mode, heredocs silently fail to
create temp files, resulting in data loss or corrupt commands with no clear error message.

Triggers on:
- `cat > file <<EOF` - unquoted heredoc
- `cat <<'EOF'` - single-quoted heredoc delimiter
- `cat <<"EOF"` - double-quoted heredoc delimiter
- `cat <<-EOF` - dash heredoc (strip leading tabs)
- Any heredoc delimiter variant matched by `<<-?\\s*['"\\]?\\w`

Does NOT trigger on:
- Regular Bash commands without heredoc syntax
- Non-Bash tool calls (Write, Edit, etc.)
"""
import json
import re
import sys

HEREDOC_PATTERN = re.compile(r"<<-?['\"]?[A-Za-z_]")


def main():
    input_data = json.load(sys.stdin)

    # Only process Bash tool PreToolUse
    if input_data.get("tool_name") != "Bash":
        print("{}")
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    if not HEREDOC_PATTERN.search(command):
        print("{}")
        sys.exit(0)

    # BLOCK: heredoc detected
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "decision": "block",
            "additionalContext": (
                "**BLOCKED: Heredoc syntax detected**\n\n"
                "Heredoc (`<<EOF`) silently fails in sandbox mode — the shell cannot "
                "create the required temp file, which corrupts the command without any "
                "clear error message. Use one of these alternatives instead:\n\n"
                "**1. Git commits** — use multiple `-m` flags:\n"
                "   `git commit -m \"Title\" -m \"Body paragraph\"`\n\n"
                "**2. gh CLI commands** (issue create, pr create, pr comment, etc.) — "
                "write the body to a temp file and pass `--body-file`:\n"
                "   Use the Write tool to create the file, then:\n"
                "   `gh issue create --title \"...\" --body-file /path/to/body.txt`\n\n"
                "**3. File creation or inline scripts** — use the Write tool directly "
                "to create the file, then reference it in the Bash command:\n"
                "   Write tool → `uv run /path/to/script.py`"
            ),
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(json.dumps({}))
        sys.exit(1)
