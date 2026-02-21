#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///

"""SessionStart hook: reset per-session attribution state for gh-authorship-attribution."""

import json
import sys
from pathlib import Path

STATE_FILE = Path.home() / ".claude" / "hook-state" / "gh-authorship-session-shown"


def main():
    # Consume stdin (required for hooks)
    sys.stdin.read()

    if STATE_FILE.exists():
        STATE_FILE.unlink()

    print("{}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("{}")
