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
        # Look for attribution in the JSON body
        attribution_patterns = [
            r'"body"[^}]*(?:Co-authored-by|AI-assisted|claude\.ai/code|Claude)',
            r'"description"[^}]*(?:Co-authored-by|AI-assisted|claude\.ai/code|Claude)'
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
                    "additionalContext": """**AUTHORSHIP ATTRIBUTION REQUIRED**

When creating git commits on behalf of the user, you must include explicit attribution indicating AI assistance.

**Required**: Add attribution to your commit message using one of these approaches:

1. **Add Co-authored-by trailer** (recommended for collaborative work):
   ```bash
   git commit -m "$(cat <<'EOF'
   Your commit message here

   Co-authored-by: Claude (Anthropic AI) <claude@anthropic.com>
   https://claude.ai/code/session_ID
   EOF
   )"
   ```

2. **Add AI assistance note** (simpler):
   ```bash
   git commit -m "$(cat <<'EOF'
   Your commit message here

   AI-assisted with Claude Code
   https://claude.ai/code/session_ID
   EOF
   )"
   ```

3. **Include in commit message body**:
   ```bash
   git commit -m "feat: add new feature" -m "Generated with assistance from Claude Code" -m "https://claude.ai/code/session_ID"
   ```

**Why this matters**:
- Transparency about AI-assisted contributions
- Proper attribution for collaborative work
- Helps maintain trust in the development process
- Complies with attribution best practices

**This reminder will appear once per 10 minutes.**"""
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
                    "additionalContext": """**AUTHORSHIP ATTRIBUTION REQUIRED**

When creating or updating GitHub content (PRs, issues, comments) via API on behalf of the user, you must include explicit attribution in the request body.

**Required**: Add attribution to the body/description field:

**For Pull Requests**:
```bash
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \\
  -H "Accept: application/vnd.github.v3+json" \\
  "https://api.github.com/repos/OWNER/REPO/pulls" \\
  -d '{
    "title": "Your PR title",
    "head": "branch-name",
    "base": "main",
    "body": "Your PR description here\\n\\n---\\n*This pull request was created with assistance from [Claude Code](https://claude.ai/code/session_ID)*"
  }'
```

**For Issues**:
```bash
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \\
  -H "Accept: application/vnd.github.v3+json" \\
  "https://api.github.com/repos/OWNER/REPO/issues" \\
  -d '{
    "title": "Your issue title",
    "body": "Issue description\\n\\n---\\n*Created with assistance from [Claude Code](https://claude.ai/code/session_ID)*"
  }'
```

**For Comments**:
```bash
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \\
  -H "Accept: application/vnd.github.v3+json" \\
  "https://api.github.com/repos/OWNER/REPO/issues/NUMBER/comments" \\
  -d '{
    "body": "Your comment\\n\\n*AI-assisted with Claude Code*"
  }'
```

**Why this matters**:
- Transparency about AI-assisted contributions
- Proper attribution when acting on user's behalf
- Maintains trust and clarity in collaborative development

**This reminder will appear once per 10 minutes.**"""
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
