#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
"""
haiku-enforce: Override Agent tool model to Haiku via updatedInput.

Event: PreToolUse (Agent tool only)

Purpose: Enforces cost-effective subagent usage by overriding the model
parameter to "haiku" on every Agent tool call. Install/uninstall the
plugin to toggle the constraint.

Behavior:
- When tool_name is "Agent": output updatedInput with model: "haiku"
  and permissionDecision: "allow", plus additionalContext informing
  Claude of the override.
- For any other tool (shouldn't fire due to matcher, but defensive):
  output {} silently.
"""
import json
import sys


def main():
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")

        if tool_name != "Agent":
            print("{}")
            sys.exit(0)

        original_input = input_data.get("tool_input", {})
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "Haiku model enforced by haiku-enforce plugin",
                "updatedInput": {**original_input, "model": "haiku"},
                "additionalContext": (
                    "haiku-enforce: This Agent call has been overridden to use the Haiku model. "
                    "To remove this constraint, uninstall the haiku-enforce plugin."
                ),
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    except Exception as e:
        print(f"Error in haiku-enforce hook: {e}", file=sys.stderr)
        print("{}")
        sys.exit(1)


if __name__ == "__main__":
    main()
