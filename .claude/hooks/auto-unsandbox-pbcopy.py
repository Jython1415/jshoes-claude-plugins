#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""Auto-approve pbcopy commands and disable sandbox for them."""
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
