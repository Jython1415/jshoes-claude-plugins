#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""Normalize CRLF/CR line endings to LF in Write/Edit operations."""
import json
import sys

try:
    input_data = json.load(sys.stdin)
    tool_input = input_data.get("tool_input", {})
    content = tool_input.get("content", "")

    # Normalize: CRLF -> LF, then CR -> LF
    if '\r' in content:
        normalized = content.replace('\r\n', '\n').replace('\r', '\n')

        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "Normalized line endings",
                "updatedInput": {"content": normalized}
            }
        }
        print(json.dumps(output))

    sys.exit(0)

except Exception:
    sys.exit(1)
