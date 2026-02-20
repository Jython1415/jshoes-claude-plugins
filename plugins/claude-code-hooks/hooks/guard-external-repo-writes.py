#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
guard-external-repo-writes: Block gh CLI write operations to repos the user doesn't own.

Event: PreToolUse (Bash)

Purpose: Prevents Claude from creating issues, comments, or other write operations
in external repositories without explicit user approval. Only the user's own repos
are allowed.

Behavior:
- Detects `gh issue create`, `gh issue comment`, `gh issue close`, `gh pr comment`,
  `gh pr create`, `gh pr close`, `gh pr review`, etc. with `--repo` flags
- Extracts the repo owner from the `--repo` argument
- Compares against the authenticated GitHub user (cached for 24 hours)
- BLOCKs the command if the repo owner doesn't match the user

Triggers on:
- `gh issue create --repo external/repo`
- `gh issue comment --repo external/repo`
- `gh pr comment --repo external/repo`
- Any `gh` write subcommand with `--repo` pointing to a non-owned repo

Does NOT trigger when:
- No `--repo` flag (operating on local repo, presumed to be user's)
- The `--repo` owner matches the authenticated GitHub user
- Read-only operations (gh issue view, gh pr list, etc.)
- Non-gh commands

State management:
- Cached GitHub username in: `~/.claude/hook-state/gh-username-cache`
- Format: `<timestamp>:<username>`
- 24-hour TTL; re-fetched via `gh api user` when expired
- Safe to delete if behavior needs to be reset
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

# Cache for the authenticated GitHub username
STATE_DIR = Path.home() / ".claude" / "hook-state"
USERNAME_CACHE = STATE_DIR / "gh-username-cache"
CACHE_TTL = 86400  # 24 hours

# Write subcommands that modify external repos
WRITE_ACTIONS = {
    "issue": {"create", "close", "comment", "edit", "delete", "reopen", "transfer"},
    "pr": {"create", "close", "comment", "edit", "merge", "review", "ready"},
}

# Regex: gh <entity> <action> ... --repo <owner/repo>
GH_CMD_PATTERN = re.compile(
    r"gh\s+(issue|pr)\s+(\w+)", re.IGNORECASE
)
REPO_FLAG_PATTERN = re.compile(
    r"--repo\s+(\S+)", re.IGNORECASE
)
# Also match -R shorthand
REPO_SHORT_PATTERN = re.compile(
    r"-R\s+(\S+)", re.IGNORECASE
)


def get_cached_username() -> str | None:
    """Read cached GitHub username if still valid."""
    try:
        if not USERNAME_CACHE.exists():
            return None
        content = USERNAME_CACHE.read_text().strip()
        ts_str, username = content.split(":", 1)
        if (time.time() - float(ts_str)) > CACHE_TTL:
            return None
        return username
    except Exception:
        return None


def fetch_and_cache_username() -> str | None:
    """Fetch authenticated GitHub username via gh CLI and cache it."""
    try:
        result = subprocess.run(
            ["gh", "api", "user", "-q", ".login"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None
        username = result.stdout.strip()
        if not username:
            return None
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        USERNAME_CACHE.write_text(f"{time.time()}:{username}")
        return username
    except Exception:
        return None


def get_github_username() -> str | None:
    """Get the authenticated GitHub username (cached or fresh)."""
    username = get_cached_username()
    if username:
        return username
    return fetch_and_cache_username()


def extract_repo_owner(command: str) -> str | None:
    """Extract the repo owner from --repo or -R flag."""
    for pattern in (REPO_FLAG_PATTERN, REPO_SHORT_PATTERN):
        match = pattern.search(command)
        if match:
            repo = match.group(1)
            if "/" in repo:
                return repo.split("/")[0]
    return None


def main():
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        if tool_name != "Bash":
            print("{}")
            sys.exit(0)

        command = tool_input.get("command", "")

        # Check if this is a gh write command
        cmd_match = GH_CMD_PATTERN.search(command)
        if not cmd_match:
            print("{}")
            sys.exit(0)

        entity = cmd_match.group(1).lower()  # "issue" or "pr"
        action = cmd_match.group(2).lower()  # "create", "comment", etc.

        # Only care about write actions
        if entity not in WRITE_ACTIONS or action not in WRITE_ACTIONS[entity]:
            print("{}")
            sys.exit(0)

        # Extract repo owner from --repo flag
        repo_owner = extract_repo_owner(command)
        if repo_owner is None:
            # No --repo flag = operating on local repo, allow
            print("{}")
            sys.exit(0)

        # Get the authenticated user
        username = get_github_username()
        if username is None:
            # Can't determine user — warn but don't block
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": (
                        "**WARNING**: Could not determine your GitHub username "
                        "to verify repo ownership. Verify that `--repo` points "
                        "to your own repository before proceeding."
                    ),
                }
            }
            print(json.dumps(output))
            sys.exit(0)

        # Compare owner to authenticated user (case-insensitive)
        if repo_owner.lower() == username.lower():
            print("{}")
            sys.exit(0)

        # BLOCK: writing to external repo
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "decision": "block",
                "additionalContext": (
                    f"**BLOCKED: Write to external repository**\n\n"
                    f"This command targets `{repo_owner}/...` but you are "
                    f"authenticated as `{username}`. Writing to repositories "
                    f"you don't own requires explicit user approval.\n\n"
                    f"**Policy**: Only create issues, comments, and PRs in "
                    f"your own repos without prior approval.\n\n"
                    f"If the user explicitly asked you to do this, ask them "
                    f"to run the command themselves or confirm the action."
                ),
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    except Exception as e:
        print(f"Error in guard-external-repo-writes hook: {e}", file=sys.stderr)
        print("{}")
        sys.exit(1)


if __name__ == "__main__":
    main()
