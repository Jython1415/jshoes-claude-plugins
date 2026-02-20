#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
ensure-tmpdir: Ensures TMPDIR directory exists before Bash tool execution.

Event: PreToolUse (Bash)

Purpose: Ensures the directory pointed to by TMPDIR exists before running a
Bash command. This is a silent side-effect hook — it never emits guidance.

Why: Claude Code sandbox sets TMPDIR to a path like /tmp/claude but does not
guarantee that directory exists. macOS periodically clears /tmp, so the
directory can disappear between sessions. Commands that write to $TMPDIR fail
with confusing errors if the directory is missing. This hook proactively
creates the directory so tools can always rely on TMPDIR being valid.
"""
import json
import os
import sys


def main():
    input_data = json.load(sys.stdin)

    # Only process Bash tool PreToolUse events
    if input_data.get("tool_name") != "Bash":
        print("{}")
        sys.exit(0)

    tmpdir = os.environ.get("TMPDIR")
    if tmpdir and not os.path.isdir(tmpdir):
        os.makedirs(tmpdir, exist_ok=True)

    print("{}")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(json.dumps({}))
        sys.exit(1)
