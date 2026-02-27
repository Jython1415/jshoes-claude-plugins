#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
detect-heredoc-errors: Provides heredoc workarounds for sandbox mode failures.

Event: PostToolUse, PostToolUseFailure (Bash)

Purpose: Detects when heredoc syntax fails in sandbox mode and provides alternative
approaches that work within sandbox constraints.

Behavior:
- Monitors Bash tool execution for heredoc-related errors
- Detects the specific error: "can't create temp file for here document"
- Provides three alternative approaches for the most common use cases
- Outputs guidance via additionalContext
- Applies to both PostToolUse and PostToolUseFailure events

Triggers on:
- Command execution that fails with: "can't create temp file for here document"
- Any Bash tool use (Bash only, not other tools)
- Both successful operations with stderr and failures

Does NOT trigger when:
- Error message doesn't contain "can't create temp file for here document"
- Non-Bash tools (WebFetch, Read, Write, Edit, etc.)
- Command succeeds without heredoc errors

Why this matters:
- Heredoc syntax doesn't work in Claude Code's sandbox environment
- Users often encounter this error when first trying heredoc patterns
- Immediate guidance prevents repeated failed attempts
- Provides clear, actionable alternatives

Workarounds provided:
1. **For git commits**: Use multiple -m flags instead of heredoc
   - Format: `git commit -m "Title" -m "Description" -m "Footer"`
   - Works for multi-line commit messages

2. **For inline strings**: Use ANSI-C quoting syntax
   - Format: `command --arg $'Line 1\\nLine 2\\nLine 3'`
   - Works for inline multi-line strings in commands

3. **For complex content**: Use Write tool to create file first
   - Create file with Write/Edit tool, then reference it
   - Best for large content blocks or when content is already prepared

Benefits:
- Immediate guidance on first heredoc error (no trial-and-error)
- Three concrete alternatives for different use cases
- Covers the most common heredoc scenarios (git commits, inline strings, files)
- Prevents wasted tool calls on failed heredoc attempts

Limitations:
- Only detects the specific heredoc error pattern
- Does not prevent the initial failed heredoc attempt
- Pattern matching is basic (exact string match, not regex)
- Only applies to Bash tool (other tools don't use heredoc)

Related techniques:
- ANSI-C quoting: $'...' with \\n for newlines, \\t for tabs
- Multiple -m flags: Standard git commit feature, not sandbox-specific
- Write tool: Preferred approach for complex multi-line content
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
