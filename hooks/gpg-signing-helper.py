#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""Detect GPG signing failures and guide Claude to use --no-gpg-sign."""
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
