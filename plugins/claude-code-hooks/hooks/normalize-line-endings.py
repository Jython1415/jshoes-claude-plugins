#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
normalize-line-endings: Automatically normalize line endings to LF (Unix-style).

Event: PreToolUse (Write, Edit)

Purpose: Ensures consistent LF line endings when writing or editing files, converting
any CRLF (Windows) or CR (old Mac) line endings to LF (Unix-style).

Behavior:
- Detects CRLF (\\r\\n) or CR (\\r) characters in content
- Converts all line endings to LF (\\n)
- Auto-approves the operation with normalized content
- Returns empty JSON if no line ending conversion needed

Triggers on:
- Write tool with content containing CRLF or CR
- Edit tool with content containing CRLF or CR

Does NOT trigger when:
- Content already uses LF line endings
- Content is empty or missing
- Tool is not Write or Edit

Benefits:
- Ensures consistent line endings across the codebase
- Prevents issues with diff tools that are sensitive to line endings
- Avoids merge conflicts caused by line ending differences
- Maintains Unix-style conventions in version control

Limitations:
- Only handles the three common line ending types (CRLF, CR, LF)
- Does not warn about the conversion (happens silently)
- May normalize intentional line endings if they were mixed-style
"""
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
    else:
        # No action needed - output empty JSON
        print(json.dumps({}))

    sys.exit(0)

except Exception:
    # On error, output empty JSON as per hook guidelines
    print(json.dumps({}))
    sys.exit(1)
