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
import sys

try:
    input_data = json.load(sys.stdin)

    # Only process Bash tool calls
    if input_data.get("tool_name") != "Bash":
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Check if command uses pbcopy
    if "pbcopy" in command:
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
