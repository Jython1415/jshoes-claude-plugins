#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""
ensure-tmpdir: Ensures TMPDIR directory exists at session start.

Event: SessionStart

Purpose: Ensures the directory pointed to by TMPDIR exists at the beginning
of each session. This is a silent side-effect hook — it never emits guidance.

Why: Claude Code sandbox sets TMPDIR to a path like /tmp/claude but does not
guarantee that directory exists. macOS periodically clears /tmp, so the
directory can disappear between sessions. Commands that write to $TMPDIR fail
with confusing errors if the directory is missing. This hook proactively
creates the directory at session start so tools can always rely on TMPDIR
being valid throughout the session.
"""
import json
import os
import sys
from pathlib import Path


def main():
    json.load(sys.stdin)  # Consume input; SessionStart fields are not needed

    tmpdir = os.environ.get("TMPDIR")
    if tmpdir and not os.path.isdir(tmpdir):
        os.makedirs(tmpdir, mode=0o700, exist_ok=True)

    # Reset per-session attribution flag so each new session starts fresh
    session_shown_file = Path.home() / ".claude" / "hook-state" / "gh-authorship-session-shown"
    if session_shown_file.exists():
        session_shown_file.unlink()

    print("{}")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(json.dumps({}))
        sys.exit(1)
