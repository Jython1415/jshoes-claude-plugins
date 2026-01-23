#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""Auto-approve pbcopy commands and disable sandbox for them."""
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
