#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
prefer-modern-tools: Direct Claude to use modern alternatives for find and grep.

Event: PreToolUse (Bash)

Purpose: Directs Claude to use modern, faster alternatives for common commands when available,
improving performance and user experience.

Behavior:
- Detects usage of `find` command → suggests `fd` if available
- Detects usage of `grep` command → suggests `rg` (ripgrep) if available
- Checks tool availability dynamically using `which` command
- Provides context-aware guidance with example syntax
- Only triggers if the modern alternative tool is installed

Triggers on:
- Commands using `find` (e.g., `find . -name "*.py"`, `find /path -type f`)
- Commands using `grep` (e.g., `grep -r "pattern" .`, `grep -n "text"`)
- Tools are checked for availability dynamically in user's PATH

Does NOT trigger when:
- Requested tool not found in PATH (silent, no nagging)
- Command is empty or missing
- Non-Bash tools (Read, Edit, Write, etc.)
- Within `grep` detection: if command already uses `rg` (ripgrep)

Suggestions provided:
- fd: Faster file search, simpler syntax, respects .gitignore by default
- rg: Significantly faster grep, respects .gitignore, better output formatting

Benefits:
- `fd`: Faster file search with more intuitive syntax than find
  - Respects .gitignore by default (use -H -I to include hidden/ignored files)
  - Simpler pattern syntax (e.g., `fd "*.py"` instead of `find . -name "*.py"`)
  - Better performance on large directory trees
- `rg`: Significantly faster than grep, especially on large codebases
  - Respects .gitignore by default
  - Better default output formatting with colors and context
  - Supports regex patterns with better syntax
  - Works well with piping and complex commands

Limitations:
- Only suggests if tool is available (doesn't fail if tool isn't installed)
- Detection is command-based, not intelligent about context
- Won't suggest if user explicitly needs standard POSIX find/grep for compatibility
- Silent if suggested tool isn't in PATH (respects user's environment)

Examples:
- `find . -name "*.py"` → suggests `fd "*.py"` or `fd -e py`
- `grep -r "pattern" .` → suggests `rg "pattern"`
- `find /path -type f -exec` → suggests `fd` with appropriate flags
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
- Use `fd --help` for additional usage guidance
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
- Use `rg --help` for additional usage guidance
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
