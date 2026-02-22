#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
prefer-gh-for-own-repos: Suggest using `gh` CLI when working with Jython1415's repositories.

Event: PreToolUse (WebFetch, Bash)

Purpose: Suggests using `gh` CLI when Claude tries to access GitHub repositories owned by Jython1415 via WebFetch or curl.

Behavior:
- Detects when WebFetch or Bash (curl) is used to access GitHub URLs for Jython1415's repositories
- Checks if `gh` CLI is available using system PATH lookup (cross-platform)
- If `gh` is available, provides guidance to use it instead
- Includes 60-second cooldown mechanism to avoid duplicate suggestions when Claude intentionally uses fetch back-to-back
- After cooldown expires, suggestions resume if behavior reverts to fetch/curl

Triggers on:
- WebFetch with URLs containing `github.com/Jython1415/`, `api.github.com/repos/Jython1415/`, or `raw.githubusercontent.com/Jython1415/`
- Bash commands with curl accessing the above URLs

Does NOT trigger when:
- `gh` CLI is not available (falls back to API access)
- Within 60-second cooldown period since last suggestion
- Accessing repositories owned by other users
- Using non-GitHub URLs

Benefits:
- `gh` CLI provides a more direct interface for GitHub operations
- Better integration with GitHub authentication
- Simpler syntax for common operations
- Acknowledges that API access might be intentional for specific use cases

Example suggestions:
- View issue: `gh issue view 10 --repo Jython1415/repo`
- List PRs: `gh pr list --repo Jython1415/repo`
- Get JSON: `gh issue view 10 --json title,body,comments --repo Jython1415/repo`

State management:
- Cooldown state stored in: `~/.claude/hook-state/prefer-gh-cooldown-<session_id>`
- Per-session-id scoping prevents cross-session contamination
- Contains Unix timestamp of last suggestion
- Safe to delete if behavior needs to be reset
- Prevents duplicate suggestions when Claude uses fetch multiple times consecutively
- Allows suggestions to resume after 60 seconds if behavior reverts

Limitations:
- Only detects WebFetch and curl commands (not wget or other HTTP clients)
- Curl command parsing is best-effort; complex commands with multiple URLs may not be detected correctly
- Owner matching is case-sensitive ("Jython1415" only, not "jython1415")
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


def is_gh_available():
    """Check if gh CLI is available in PATH."""
    try:
        return shutil.which("gh") is not None
    except Exception:
        return False


def is_within_cooldown(session_id: str) -> bool:
    """Check if we're within the cooldown period since last suggestion."""
    state_file = STATE_DIR / f"prefer-gh-cooldown-{session_id}"
    try:
        if not state_file.exists():
            return False

        last_suggestion_time = float(state_file.read_text().strip())
        current_time = time.time()

        return (current_time - last_suggestion_time) < COOLDOWN_PERIOD
    except Exception:
        return False


def record_suggestion(session_id: str):
    """Record that we just made a suggestion."""
    state_file = STATE_DIR / f"prefer-gh-cooldown-{session_id}"
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_file.write_text(str(time.time()))
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
        session_id = input_data.get("session_id", "")
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Check if gh is available - if not, don't trigger
        if not is_gh_available():
            print("{}")
            sys.exit(0)

        # Check if we're within cooldown period
        if is_within_cooldown(session_id):
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
        record_suggestion(session_id)

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
