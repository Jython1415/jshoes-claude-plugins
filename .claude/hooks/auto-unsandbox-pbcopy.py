#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
auto-unsandbox-pbcopy: Automatically approves pbcopy commands and disables sandbox for them.

Event: PreToolUse (Bash)

Purpose: Automatically approves pbcopy commands and disables sandbox for them, since pbcopy
requires unsandboxed mode to function.

Behavior:
- Detects commands containing `pbcopy`
- Auto-approves the command with permission decision
- Sets `dangerouslyDisableSandbox: true` to allow pbcopy to work
- Outputs permission decision with clear reasoning

Triggers on:
- Bash commands containing `pbcopy` (any part of the command)
- Examples: `echo "text" | pbcopy`, `cat file | pbcopy`, `pbcopy < file.txt`

Does NOT trigger when:
- Non-Bash tools (Read, Write, Edit, etc.)
- Commands that don't contain `pbcopy`

Benefits:
- Streamlines clipboard operations without manual sandbox approval
- Enables pbcopy-dependent workflows (e.g., copy command output to clipboard)
- Provides clear reasoning for the auto-approval

Limitations:
- Only detects `pbcopy` in command string (case-sensitive)
- No additional validation of command syntax
- Only available on macOS (pbcopy is a macOS utility)
"""
import json
import re
import sys

try:
    input_data = json.load(sys.stdin)

    # Only process Bash tool calls
    if input_data.get("tool_name") != "Bash":
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Check if command uses pbcopy in command positions (not in strings/filenames/variables)
    # Match pbcopy when it appears as a command:
    # - At command start, with optional path prefix (e.g., pbcopy or /usr/bin/pbcopy)
    # - After pipe |, &&, ||, ; (with optional whitespace)
    # This avoids matching pbcopy in quoted strings, filenames, or variable assignments
    pbcopy_pattern = r'(?:^\s*(?:/[\w/]+/)?|[|&;]\s*)pbcopy\b'
    if re.search(pbcopy_pattern, command, re.MULTILINE):
        # Auto-approve and disable sandbox
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "pbcopy auto-approved (requires unsandboxed mode)",
                "updatedInput": {
                    "command": command,
                    "dangerouslyDisableSandbox": True
                }
            }
        }
        print(json.dumps(output))
    else:
        # No action needed, output empty JSON as per hook guidelines
        print(json.dumps({}))

    sys.exit(0)

except Exception:
    # On error, output empty JSON as per hook guidelines
    print(json.dumps({}))
    sys.exit(1)
