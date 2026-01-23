#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Ensure proper authorship attribution when Claude writes to GitHub on behalf of the user.

This hook detects when Claude is creating commits, PRs, issues, or comments via git
or GitHub API and provides guidance to include explicit attribution indicating that
the content was authored with AI assistance.

Promotes transparency and proper attribution for AI-assisted contributions.
"""
import json
import sys
import re
import time
from pathlib import Path

# Cooldown period in seconds (10 minutes)
# Longer than other hooks because attribution guidance is important but not urgent
COOLDOWN_PERIOD = 600

# State file location
STATE_DIR = Path.home() / ".claude" / "hook-state"
STATE_FILE = STATE_DIR / "gh-authorship-cooldown"

# Patterns to detect operations that need attribution
GIT_COMMIT_PATTERN = r'git\s+commit'
GITHUB_API_CREATE_PATTERN = r'curl.*(?:POST|PATCH).*github\.com/repos/.*(?:pulls|issues|comments)'
GH_CLI_PATTERN = r'gh\s+(pr|issue)\s+(create|edit|comment)'


def is_git_commit(command):
    """Check if command is a git commit."""
    try:
        return bool(re.search(GIT_COMMIT_PATTERN, command, re.IGNORECASE))
    except Exception:
        return False


def is_github_api_write(command):
    """Check if command is a GitHub API call that creates/updates content."""
    try:
        # Check each condition separately for more flexible matching
        has_curl = 'curl' in command.lower()
        has_post_or_patch = bool(re.search(r'-X\s+(POST|PATCH)', command, re.IGNORECASE))
        has_github_api = 'github.com/repos' in command.lower()
        has_write_endpoint = bool(re.search(r'/(pulls|issues|comments)', command, re.IGNORECASE))

        return has_curl and has_post_or_patch and has_github_api and has_write_endpoint
    except Exception:
        return False


def is_gh_cli_write(command):
    """Check if command is a gh CLI call that creates/updates content."""
    try:
        return bool(re.search(GH_CLI_PATTERN, command, re.IGNORECASE))
    except Exception:
        return False


def has_attribution_in_commit(command):
    """Check if git commit already includes attribution."""
    try:
        # Look for common attribution patterns in commit messages
        # Co-authored-by, AI-assisted, Claude, etc.
        attribution_patterns = [
            r'Co-authored-by:\s*Claude',
            r'AI-assisted',
            r'claude\.ai/code',
            r'Generated with Claude',
            r'With assistance from Claude'
        ]
        return any(re.search(pattern, command, re.IGNORECASE) for pattern in attribution_patterns)
    except Exception:
        return False


def has_attribution_in_api_body(command):
    """Check if GitHub API request body includes attribution."""
    try:
        # Look for attribution in the JSON body or gh CLI --body argument
        attribution_patterns = [
            r'"body"[^}]*(?:Co-authored-by|AI-assisted|claude\.ai/code|Claude)',
            r'"description"[^}]*(?:Co-authored-by|AI-assisted|claude\.ai/code|Claude)',
            r'--body\s+"[^"]*(?:Co-authored-by|AI-assisted|claude\.ai/code|Claude)',
        ]
        return any(re.search(pattern, command, re.IGNORECASE) for pattern in attribution_patterns)
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
        # Gracefully handle corrupted state file
        return False


def record_suggestion():
    """Record that we just made a suggestion."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(str(time.time()))
    except Exception as e:
        # Log but don't fail - cooldown is nice-to-have, not critical
        print(f"Warning: Could not record cooldown state: {e}", file=sys.stderr)


def main():
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Only monitor Bash tool
        if tool_name != "Bash":
            print("{}")
            sys.exit(0)

        # Extract command from tool input
        command = tool_input.get("command", "")

        # Check if this is a git commit
        if is_git_commit(command):
            # Check if attribution is already present
            if has_attribution_in_commit(command):
                print("{}")
                sys.exit(0)

            # Check cooldown
            if is_within_cooldown():
                print("{}")
                sys.exit(0)

            # Record this suggestion
            record_suggestion()

            # Provide guidance for git commit attribution
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": """**AUTHORSHIP ATTRIBUTION REMINDER**

Consider adding attribution when committing AI-authored code.

**Add Co-authored-by trailer**:
```bash
git commit -m "$(cat <<'EOF'
Your commit message

Co-authored-by: Claude (Anthropic AI) <claude@anthropic.com>
https://claude.ai/code/session_ID
EOF
)"
```

**Or add an AI assistance note**:
```bash
git commit -m "Your message" -m "AI-assisted with Claude Code"
```

This promotes transparency about AI-assisted contributions. Use your judgment based on who authored the code.

*This reminder appears once per 10 minutes.*"""
                }
            }

            print(json.dumps(output))
            sys.exit(0)

        # Check if this is a GitHub API write operation
        if is_github_api_write(command):
            # Check if attribution is already present in request body
            if has_attribution_in_api_body(command):
                print("{}")
                sys.exit(0)

            # Check cooldown
            if is_within_cooldown():
                print("{}")
                sys.exit(0)

            # Record this suggestion
            record_suggestion()

            # Provide guidance for GitHub API attribution
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": """**AUTHORSHIP ATTRIBUTION REMINDER**

Consider adding attribution when creating/updating GitHub content (PRs, issues, comments) with AI assistance.

**Add attribution to the body/description**:
```
"body": "Your content\\n\\n---\\n*Created with assistance from Claude Code*"
```

**Example for gh CLI**:
```bash
gh pr create --title "Title" --body "Description

---
*Created with assistance from Claude Code*"
```

This promotes transparency about AI-assisted contributions. Use your judgment based on who authored the content.

*This reminder appears once per 10 minutes.*"""
                }
            }

            print(json.dumps(output))
            sys.exit(0)

        # Check if this is a gh CLI write operation
        if is_gh_cli_write(command):
            # Check if attribution is already present in command
            if has_attribution_in_api_body(command):
                print("{}")
                sys.exit(0)

            # Check cooldown
            if is_within_cooldown():
                print("{}")
                sys.exit(0)

            # Record this suggestion
            record_suggestion()

            # Provide guidance for gh CLI attribution
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": """**AUTHORSHIP ATTRIBUTION REMINDER**

Consider adding attribution when creating/updating GitHub content (PRs, issues, comments) with AI assistance.

**Add attribution to the body/description**:
```
"body": "Your content\\n\\n---\\n*Created with assistance from Claude Code*"
```

**Example for gh CLI**:
```bash
gh pr create --title "Title" --body "Description

---
*Created with assistance from Claude Code*"
```

This promotes transparency about AI-assisted contributions. Use your judgment based on who authored the content.

*This reminder appears once per 10 minutes.*"""
                }
            }

            print(json.dumps(output))
            sys.exit(0)

        # No attribution needed for this command
        print("{}")
        sys.exit(0)

    except Exception as e:
        # Log to stderr for debugging
        print(f"Error in gh-authorship-attribution hook: {e}", file=sys.stderr)
        # Always output valid JSON on error
        print("{}")
        sys.exit(1)


if __name__ == "__main__":
    main()
