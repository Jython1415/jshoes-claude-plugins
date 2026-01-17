#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Direct Claude to use modern alternatives when available:
- fd instead of find
- rg (ripgrep) instead of grep

This hook checks for these commands in Bash tool use and provides
guidance to use faster, more user-friendly alternatives.
"""
import json
import sys
import subprocess
import os

# Cache for tool availability (checked once per hook execution)
_tool_cache = {}

def is_tool_available(tool_name):
    """Check if a tool is available in PATH."""
    if tool_name not in _tool_cache:
        try:
            result = subprocess.run(
                ["which", tool_name],
                capture_output=True,
                timeout=1
            )
            _tool_cache[tool_name] = result.returncode == 0
        except Exception:
            _tool_cache[tool_name] = False
    return _tool_cache[tool_name]

def main():
    try:
        input_data = json.load(sys.stdin)

        # Only process Bash tool calls
        if input_data.get("tool_name") != "Bash":
            print("{}")
            sys.exit(0)

        tool_input = input_data.get("tool_input", {})
        command = tool_input.get("command", "")

        # Skip if command is empty
        if not command:
            print("{}")
            sys.exit(0)

        suggestions = []

        # Check for find command usage
        if " find " in f" {command} " or command.startswith("find "):
            if is_tool_available("fd"):
                suggestions.append("""
**Consider using `fd` instead of `find`:**
- `fd` is faster and has simpler syntax
- Example: `find . -name "*.py"` → `fd "*.py"` or `fd -e py`
- `fd` respects .gitignore by default (use -H -I to include hidden/ignored files)
- For complex patterns, `fd` syntax is more intuitive
""")

        # Check for grep command usage (but not ripgrep)
        if (" grep " in f" {command} " or command.startswith("grep ")) and "rg " not in command:
            if is_tool_available("rg"):
                suggestions.append("""
**Consider using `rg` (ripgrep) instead of `grep`:**
- `rg` is significantly faster, especially on large codebases
- Example: `grep -r "pattern" .` → `rg "pattern"`
- `rg` respects .gitignore by default
- Better default output formatting with colors and context
- For literal strings: `rg -F "exact string"`
""")

        # If we have suggestions, provide them via additionalContext
        if suggestions:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": "\n".join(suggestions).strip()
                }
            }
            print(json.dumps(output))
        else:
            print("{}")

        sys.exit(0)

    except Exception:
        # Always output valid JSON on error
        print("{}")
        sys.exit(1)

if __name__ == "__main__":
    main()
