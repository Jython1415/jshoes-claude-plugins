#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
gpg-signing-helper: Detect GPG signing failures and guide Claude to use --no-gpg-sign.

Event: PostToolUse, PostToolUseFailure (Bash)

Purpose: Detects GPG signing errors when git commit attempts GPG signing in sandbox mode
and guides Claude to use the --no-gpg-sign flag for commits within sandbox environments.

Behavior:
- Monitors Bash command execution for GPG-related errors
- Detects common GPG signing failure messages
- Provides immediate guidance when GPG signing fails
- Explains why GPG is unavailable in sandbox mode
- Suggests the --no-gpg-sign flag as the solution

Triggers on:
- "gpg failed to sign the data"
- "gpg: can't connect to the agent"
- "No agent running"

Does NOT trigger when:
- No GPG errors in command output
- Non-Bash tools are used
- GPG signing succeeds
- Errors are unrelated to GPG

Guidance provided:
- Explains that GPG signing is unavailable in sandbox mode
- Shows how to use `git commit --no-gpg-sign -m "message"`
- Clarifies that all git commits in sandbox require the --no-gpg-sign flag

Why this matters:
- GPG agent is unavailable in isolated sandbox environments
- Attempting to sign commits without --no-gpg-sign wastes time
- Immediate guidance helps Claude retry commits correctly
- Improves workflow efficiency for users working in sandbox mode

Limitations:
- Only detects common GPG error messages (may not catch all variations)
- Assumes --no-gpg-sign is the appropriate solution
- Only monitors Bash tool (not git commands from other tools)
"""
import json
import sys

try:
    input_data = json.load(sys.stdin)

    # Get error from either location:
    # - PostToolUseFailure: top-level "error" field
    # - PostToolUse: "tool_result.error" field
    error_output = input_data.get("error", "")
    if not error_output:
        tool_result = input_data.get("tool_result", {})
        error_output = tool_result.get("error", "")

    # Check if the Bash command failed
    if error_output:

        # Detect GPG signing failure
        if "gpg failed to sign the data" in error_output or \
           "gpg: can't connect to the agent" in error_output or \
           "No agent running" in error_output:

            # Output educational message to Claude via additionalContext
            # Note: decision="block" doesn't work for PostToolUseFailure
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUseFailure",
                    "additionalContext": (
                        f"GPG SIGNING ERROR DETECTED: {error_output}\n\n"
                        "GPG signing is not available in sandbox mode. "
                        "Use the --no-gpg-sign flag for your commit:\n\n"
                        "git commit --no-gpg-sign -m \"your message\"\n\n"
                        "IMPORTANT: All git commits in sandbox require --no-gpg-sign."
                    )
                }
            }
            print(json.dumps(output))
            sys.exit(0)

    # No error detected - output empty JSON
    print("{}")
    sys.exit(0)

except Exception:
    print("{}")
    sys.exit(1)
