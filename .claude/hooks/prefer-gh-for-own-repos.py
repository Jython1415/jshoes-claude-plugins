#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Suggest using `gh` CLI when working with Jython1415's repositories.

This hook detects when Claude tries to use WebFetch or curl to access
GitHub API for repositories owned by Jython1415, and suggests using `gh`
CLI instead when it's available.

Includes cooldown mechanism to avoid duplicate suggestions when Claude
intentionally uses fetch back-to-back, but will suggest again if the
behavior reverts after a while.
"""
import json
import sys
import shutil
import os
import time
from pathlib import Path

# Owner username to match
TARGET_OWNER = "Jython1415"

# Cooldown period in seconds (60 seconds)
COOLDOWN_PERIOD = 60

# State file location
STATE_DIR = Path.home() / ".claude" / "hook-state"
STATE_FILE = STATE_DIR / "prefer-gh-cooldown"


def is_gh_available():
    """Check if gh CLI is available in PATH."""
    try:
        return shutil.which("gh") is not None
    except Exception:
        return False


def is_within_cooldown():
    """Check if we're within the cooldown period since last suggestion."""
    try:
        if not STATE_FILE.exists():
            return False

        last_suggestion_time = float(STATE_FILE.read_text().strip())
        current_time = time.time()

        return (current_time - last_suggestion_time) < COOLDOWN_PERIOD
    except Exception:
        return False


def record_suggestion():
    """Record that we just made a suggestion."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(str(time.time()))
    except Exception as e:
        # Log but don't fail - cooldown is nice-to-have, not critical
        print(f"Warning: Could not record cooldown state: {e}", file=sys.stderr)


def matches_target_owner(url):
    """Check if URL matches GitHub repos owned by target owner."""
    # Check various GitHub URL patterns
    patterns = [
        f"github.com/{TARGET_OWNER}/",
        f"api.github.com/repos/{TARGET_OWNER}/",
        f"raw.githubusercontent.com/{TARGET_OWNER}/",  # Raw file access
    ]

    for pattern in patterns:
        if pattern in url:
            return True

    return False


def main():
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Check if gh is available - if not, don't trigger
        if not is_gh_available():
            print("{}")
            sys.exit(0)

        # Check if we're within cooldown period
        if is_within_cooldown():
            print("{}")
            sys.exit(0)

        url_to_check = None
        tool_type = None

        # Handle WebFetch tool
        if tool_name == "WebFetch":
            url_to_check = tool_input.get("url", "")
            tool_type = "WebFetch"

        # Handle Bash tool with curl or similar
        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            # Check if command contains curl with GitHub API URL
            if "curl" in command:
                # Extract URL from curl command (simplified approach)
                for word in command.split():
                    if "github.com" in word or "api.github.com" in word:
                        # Remove quotes and other shell characters
                        url_to_check = word.strip('"\'')
                        tool_type = "Bash (curl)"
                        break

        # If no URL found or doesn't match target owner, exit
        if not url_to_check or not matches_target_owner(url_to_check):
            print("{}")
            sys.exit(0)

        # Record this suggestion to enable cooldown
        record_suggestion()

        # Provide guidance to use gh CLI
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"""**Consider using `gh` CLI for {TARGET_OWNER}'s repositories:**

You're accessing a GitHub repository owned by {TARGET_OWNER} using {tool_type}.
The `gh` CLI is available and provides a more direct interface.

**Common gh commands for this scenario:**

- **View issue/PR details:**
  ```bash
  gh issue view NUMBER --repo {TARGET_OWNER}/REPO
  gh pr view NUMBER --repo {TARGET_OWNER}/REPO
  ```

- **List issues/PRs:**
  ```bash
  gh issue list --repo {TARGET_OWNER}/REPO
  gh pr list --repo {TARGET_OWNER}/REPO
  ```

- **Create PR:**
  ```bash
  gh pr create --title "Title" --body "Description" --repo {TARGET_OWNER}/REPO
  ```

- **Get issue/PR JSON:**
  ```bash
  gh issue view NUMBER --json title,body,comments --repo {TARGET_OWNER}/REPO
  gh pr view NUMBER --json title,body,comments --repo {TARGET_OWNER}/REPO
  ```

**Note:** If you intentionally need to use the API (e.g., for specific fields not available in gh), you can continue with your current approach."""
            }
        }

        print(json.dumps(output))
        sys.exit(0)

    except Exception as e:
        # Log to stderr for debugging
        print(f"Error in prefer-gh-for-own-repos hook: {e}", file=sys.stderr)
        # Always output valid JSON on error
        print("{}")
        sys.exit(1)


if __name__ == "__main__":
    main()
