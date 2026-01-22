#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Detect heredoc sandbox errors and provide workaround guidance.
Only triggers on the specific heredoc error pattern.
"""
import json
import sys

def main():
    input_data = json.load(sys.stdin)

    # Only process Bash tool failures
    if input_data.get("tool_name") != "Bash":
        print("{}")
        sys.exit(0)

    # Get error from either location:
    # - PostToolUseFailure: top-level "error" field
    # - PostToolUse: "tool_result.error" field
    error_output = input_data.get("error", "")
    if not error_output:
        tool_result = input_data.get("tool_result", {})
        error_output = tool_result.get("error", "")

    # Check for specific heredoc error
    if "can't create temp file for here document" not in error_output:
        print("{}")
        sys.exit(0)  # Not the error we're looking for

    # Provide targeted guidance via additionalContext
    # Note: decision="block" doesn't work for PostToolUseFailure, so we use additionalContext
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUseFailure",
            "additionalContext": f"""HEREDOC ERROR DETECTED: {error_output}

**Required Workarounds for Sandbox:**

1. **For git commits:** Use multiple -m flags instead of heredoc
   ```bash
   git commit -m "Title" -m "Description" -m "Footer"
   ```

2. **For inline strings:** Use ANSI-C quoting
   ```bash
   command --arg $'Line 1\\nLine 2\\nLine 3'
   ```

3. **For complex content:** Use Write tool to create file first
   ```bash
   # First use Write tool to create the file, then reference it
   command --file /path/to/file
   ```

IMPORTANT: Heredocs don't work in sandbox mode. Use one of the above alternatives."""
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
