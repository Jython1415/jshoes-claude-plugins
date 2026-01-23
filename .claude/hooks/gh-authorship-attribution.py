#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
gh-authorship-attribution: Ensure proper authorship attribution for AI-assisted GitHub contributions.

Event: PreToolUse (Bash)

Purpose: Ensures proper authorship attribution when Claude creates git commits, pull requests,
issues, or comments on behalf of the user.

Behavior:
- Detects `git commit` commands without attribution and provides guidance
- Detects GitHub API calls (POST/PATCH to pulls, issues, comments) without attribution
- Checks for existing attribution markers (Co-authored-by, AI-assisted, claude.ai/code links)
- Provides concrete examples for adding attribution
- Includes 1-minute cooldown to avoid repetitive suggestions

Triggers on:
- Git commits: `git commit -m "message"`, `git commit --amend`, etc.
- PR creation: `curl -X POST .../pulls -d '{"title":"...","body":"..."}'`
- Issue creation: `curl -X POST .../issues -d '{"title":"...","body":"..."}'`
- Comment creation: `curl -X POST .../comments -d '{"body":"..."}'`
- PR/issue updates: `curl -X PATCH .../pulls/NUMBER` or `.../issues/NUMBER`

Does NOT trigger when:
- Attribution already present (Co-authored-by, AI-assisted, claude.ai/code, etc.)
- Within 1-minute cooldown period since last suggestion
- Non-write operations (git status, git log, GET requests, etc.)
- Non-GitHub API calls

Attribution patterns recognized:
- `Co-authored-by: Claude`
- `AI-assisted`
- `claude.ai/code`
- `Generated with Claude`
- `With assistance from Claude`

Guidance provided:

For git commits:
```bash
# Option 1: Co-authored-by trailer (recommended)
git commit -m "$(cat <<'EOF'
Your commit message

Co-authored-by: Claude (Anthropic AI) <claude@anthropic.com>
https://claude.ai/code/session_ID
EOF
)"

# Option 2: AI assistance note
git commit -m "$(cat <<'EOF'
Your commit message

AI-assisted with Claude Code
https://claude.ai/code/session_ID
EOF
)"

# Option 3: Multiple -m flags
git commit -m "feat: add feature" -m "AI-assisted with Claude Code" -m "https://claude.ai/code/session_ID"
```

For GitHub API calls:
```bash
# Pull requests
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/pulls" \
  -d '{
    "title": "PR title",
    "head": "branch",
    "base": "main",
    "body": "Description\n\n---\n*Created with [Claude Code](https://claude.ai/code/session_ID)*"
  }'

# Issues
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/issues" \
  -d '{
    "title": "Issue title",
    "body": "Description\n\n---\n*AI-assisted with Claude Code*"
  }'

# Comments
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/issues/10/comments" \
  -d '{"body": "Comment\n\n*AI-assisted with Claude Code*"}'
```

Why this matters:
- Transparency about AI-assisted contributions
- Proper attribution when acting on user's behalf
- Maintains trust in collaborative development
- Complies with attribution best practices

State management:
- Cooldown state stored in: `~/.claude/hook-state/gh-authorship-cooldown`
- Contains Unix timestamp of last suggestion
- 60-second (1-minute) cooldown period
- Safe to delete if behavior needs to be reset

Benefits:
- Promotes transparency in AI-assisted development
- Educates about attribution best practices
- Prevents accidental omission of attribution
- Works for both git and GitHub API workflows

Limitations:
- Only detects curl-based GitHub API calls (not wget or other HTTP clients)
- Attribution detection is pattern-based; unusual formats may not be recognized
- Cooldown may prevent guidance on subsequent operations within 1 minute
- Only monitors Bash tool (not direct API operations from other tools)
"""
import json
import sys
import re
import time
from pathlib import Path

# Cooldown period in seconds (1 minute)
COOLDOWN_PERIOD = 60

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

*This reminder appears once per minute.*"""
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

*This reminder appears once per minute.*"""
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

*This reminder appears once per minute.*"""
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
