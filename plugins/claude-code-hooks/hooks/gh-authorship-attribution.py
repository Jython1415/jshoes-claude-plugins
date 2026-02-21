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
For detailed examples, see the guidance messages provided by this hook.

Why this matters:
- Transparency about AI-assisted contributions
- Proper attribution when acting on user's behalf
- Maintains trust in collaborative development
- Complies with attribution best practices

State management:
- Cooldown state stored in: `~/.claude/hook-state/gh-authorship-cooldown-{session_id}`
- Contains Unix timestamp of last suggestion, scoped per session_id
- 60-second (1-minute) cooldown period
- Safe to delete if behavior needs to be reset
- Session tracking stored in: `~/.claude/hook-state/gh-authorship-session-shown-{session_id}`
- Empty flag file keyed by session_id; files accumulate but are zero-byte
- First trigger per session always shows guidance regardless of cooldown
- Per-session scoping ensures Session A's commits don't suppress Session B's reminders

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

# State directory location
STATE_DIR = Path.home() / ".claude" / "hook-state"

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


def is_within_cooldown(session_id):
    """Check if we're within the cooldown period since last suggestion for this session."""
    try:
        cooldown_file = STATE_DIR / f"gh-authorship-cooldown-{session_id}"
        if not cooldown_file.exists():
            return False

        last_suggestion_time = float(cooldown_file.read_text().strip())
        current_time = time.time()

        return (current_time - last_suggestion_time) < COOLDOWN_PERIOD
    except Exception:
        # Gracefully handle corrupted state file
        return False


def record_suggestion(session_id):
    """Record that we just made a suggestion for this session."""
    try:
        cooldown_file = STATE_DIR / f"gh-authorship-cooldown-{session_id}"
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        cooldown_file.write_text(str(time.time()))
    except Exception as e:
        # Log but don't fail - cooldown is nice-to-have, not critical
        print(f"Warning: Could not record cooldown state: {e}", file=sys.stderr)


def is_first_trigger_this_session(session_id):
    """Check if this is the first trigger in the current session.

    Returns True if no flag file exists for this session_id.
    """
    session_file = STATE_DIR / f"gh-authorship-session-shown-{session_id}"
    return not session_file.exists()


def record_first_trigger(session_id):
    """Record that the first trigger has been shown this session."""
    session_file = STATE_DIR / f"gh-authorship-session-shown-{session_id}"
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    session_file.touch()


def format_cooldown_message():
    """Format the cooldown period message based on COOLDOWN_PERIOD constant."""
    if COOLDOWN_PERIOD < 60:
        return f"*This reminder appears every {COOLDOWN_PERIOD} seconds.*"
    elif COOLDOWN_PERIOD == 60:
        return "*This reminder appears once per minute.*"
    elif COOLDOWN_PERIOD % 60 == 0:
        minutes = COOLDOWN_PERIOD // 60
        if minutes == 1:
            return "*This reminder appears once per minute.*"
        else:
            return f"*This reminder appears every {minutes} minutes.*"
    else:
        return f"*This reminder appears every {COOLDOWN_PERIOD} seconds.*"


def main():
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        session_id = input_data.get("session_id", "")

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

            # First trigger always shows guidance; subsequent triggers use cooldown
            if is_first_trigger_this_session(session_id):
                record_first_trigger(session_id)
                record_suggestion(session_id)
            elif is_within_cooldown(session_id):
                print("{}")
                sys.exit(0)
            else:
                record_suggestion(session_id)

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

""" + format_cooldown_message() + """
"""
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

            # First trigger always shows guidance; subsequent triggers use cooldown
            if is_first_trigger_this_session(session_id):
                record_first_trigger(session_id)
                record_suggestion(session_id)
            elif is_within_cooldown(session_id):
                print("{}")
                sys.exit(0)
            else:
                record_suggestion(session_id)

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

""" + format_cooldown_message() + """
"""
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

            # First trigger always shows guidance; subsequent triggers use cooldown
            if is_first_trigger_this_session(session_id):
                record_first_trigger(session_id)
                record_suggestion(session_id)
            elif is_within_cooldown(session_id):
                print("{}")
                sys.exit(0)
            else:
                record_suggestion(session_id)

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

""" + format_cooldown_message() + """
"""
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
