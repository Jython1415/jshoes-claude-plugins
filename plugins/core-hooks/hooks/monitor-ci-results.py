#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
monitor-ci-results: Remind Claude to monitor CI results after push or PR creation.

Event: PostToolUse (Bash)

Purpose: After pushing commits or creating pull requests, remind Claude to monitor
CI results on GitHub so issues can be caught and addressed quickly.

Behavior:
- Detects successful `git push` commands
- Detects successful PR creation (via `gh pr create` or curl POST to /pulls)
- Checks if the repository has GitHub Actions workflows (.github/workflows/)
- Provides guidance on monitoring CI status using `gh run` or GitHub API
- Includes 2-minute cooldown to avoid repetitive reminders

Triggers on:
- `git push` (any successful push to remote)
- `gh pr create` (PR creation via gh CLI)
- `curl -X POST .../pulls` (PR creation via GitHub API)

Does NOT trigger when:
- No CI workflows detected (.github/workflows/ doesn't exist)
- Within 2-minute cooldown period since last reminder
- Command failed (error present in output)
- Non-Bash tools are used
- Non-push/PR commands

Guidance provided:
- How to check CI status with `gh run list` and `gh run watch`
- Alternative GitHub API commands when gh is unavailable
- Reminder to check PR checks page

Why this matters:
- CI failures caught early save time and prevent broken main branches
- Developers can address issues while context is still fresh
- Proactive monitoring leads to faster feedback loops
- Helps maintain code quality through automated testing

State management:
- Cooldown state stored in: `~/.claude/hook-state/monitor-ci-cooldown-<session_id>`
- Per-session-id scoping prevents cross-session contamination
- Contains Unix timestamp of last reminder
- 120-second (2-minute) cooldown period
- Safe to delete if behavior needs to be reset

Limitations:
- Only detects GitHub Actions workflows (not Travis, CircleCI, etc.)
- Workflow existence check is local (may not match remote configuration)
- Only monitors Bash tool (not direct API operations from other tools)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Cooldown period in seconds (2 minutes)
COOLDOWN_PERIOD = 120

# State file location
STATE_DIR = Path.home() / ".claude" / "hook-state"

# Patterns to detect push and PR creation
GIT_PUSH_PATTERN = r'git\s+push'
GH_PR_CREATE_PATTERN = r'gh\s+pr\s+create'
GITHUB_API_PR_CREATE_PATTERN = r'curl.*POST.*github\.com/repos/[^/]+/[^/]+/pulls'


def is_git_push(command: str) -> bool:
    """Check if command is a git push."""
    try:
        return bool(re.search(GIT_PUSH_PATTERN, command, re.IGNORECASE))
    except Exception:
        return False


def is_pr_creation(command: str) -> bool:
    """Check if command creates a PR (via gh CLI or GitHub API)."""
    try:
        # Check for gh pr create
        if re.search(GH_PR_CREATE_PATTERN, command, re.IGNORECASE):
            return True
        # Check for GitHub API PR creation
        if re.search(GITHUB_API_PR_CREATE_PATTERN, command, re.IGNORECASE):
            return True
        return False
    except Exception:
        return False


def has_github_workflows() -> bool:
    """Check if the repository has GitHub Actions workflows."""
    try:
        # Check common locations for workflow files
        workflows_dir = Path(".github/workflows")
        if workflows_dir.exists() and workflows_dir.is_dir():
            # Check if there are any YAML files
            yaml_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
            return len(yaml_files) > 0
        return False
    except Exception:
        return False


def is_gh_available() -> bool:
    """Check if gh CLI is available."""
    try:
        return shutil.which("gh") is not None
    except Exception:
        return False


def has_github_token() -> bool:
    """Check if GITHUB_TOKEN environment variable is set."""
    return bool(os.environ.get("GITHUB_TOKEN"))


def is_within_cooldown(session_id: str) -> bool:
    """Check if we're within the cooldown period since last reminder."""
    state_file = STATE_DIR / f"monitor-ci-cooldown-{session_id}"
    try:
        if not state_file.exists():
            return False

        last_reminder_time = float(state_file.read_text().strip())
        current_time = time.time()

        return (current_time - last_reminder_time) < COOLDOWN_PERIOD
    except Exception:
        # Gracefully handle corrupted state file
        return False


def record_reminder(session_id: str):
    """Record that we just provided a reminder."""
    state_file = STATE_DIR / f"monitor-ci-cooldown-{session_id}"
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_file.write_text(str(time.time()))
    except Exception as e:
        # Log but don't fail - cooldown is nice-to-have, not critical
        print(f"Warning: Could not record cooldown state: {e}", file=sys.stderr)


def format_cooldown_message() -> str:
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


def get_guidance_for_push() -> str:
    """Generate CI monitoring guidance for git push."""
    gh_available = is_gh_available()
    has_token = has_github_token()

    guidance = """**CI MONITORING REMINDER**

You just pushed commits. Consider monitoring CI results to catch issues early.

"""

    if gh_available:
        guidance += """**Check CI status with gh CLI:**
```bash
# List recent workflow runs
gh run list --limit 5

# Watch a specific run (will wait for completion)
gh run watch

# View details of the latest run
gh run view
```

"""
    elif has_token:
        guidance += """**Check CI status via GitHub API:**
```bash
# List recent workflow runs
curl -s -H "Authorization: token $(printenv GITHUB_TOKEN)" \\
  -H "Accept: application/vnd.github.v3+json" \\
  "https://api.github.com/repos/OWNER/REPO/actions/runs?per_page=5"

# Get status of a specific run
curl -s -H "Authorization: token $(printenv GITHUB_TOKEN)" \\
  -H "Accept: application/vnd.github.v3+json" \\
  "https://api.github.com/repos/OWNER/REPO/actions/runs/RUN_ID"
```

"""
    else:
        guidance += """**Check CI status:**
Visit the repository's Actions tab on GitHub to monitor workflow runs.

"""

    guidance += """**Why monitor CI:**
- Catch failures while context is fresh
- Prevent broken main branch
- Address issues before they compound

"""
    guidance += format_cooldown_message()
    return guidance


def get_guidance_for_pr() -> str:
    """Generate CI monitoring guidance for PR creation."""
    gh_available = is_gh_available()
    has_token = has_github_token()

    guidance = """**CI MONITORING REMINDER**

You just created a PR. Consider monitoring CI checks to ensure they pass.

"""

    if gh_available:
        guidance += """**Check PR status with gh CLI:**
```bash
# View PR checks status
gh pr checks

# Watch PR checks (will wait for completion)
gh pr checks --watch

# View PR details including check status
gh pr view
```

"""
    elif has_token:
        guidance += """**Check PR status via GitHub API:**
```bash
# Get PR check runs
curl -s -H "Authorization: token $(printenv GITHUB_TOKEN)" \\
  -H "Accept: application/vnd.github.v3+json" \\
  "https://api.github.com/repos/OWNER/REPO/pulls/PR_NUMBER/commits" | \\
  jq -r '.[0].sha' | xargs -I {} curl -s \\
  -H "Authorization: token $(printenv GITHUB_TOKEN)" \\
  -H "Accept: application/vnd.github.v3+json" \\
  "https://api.github.com/repos/OWNER/REPO/commits/{}/check-runs"
```

"""
    else:
        guidance += """**Check PR status:**
Visit the PR page on GitHub to monitor check status in the "Checks" tab.

"""

    guidance += """**Why monitor PR checks:**
- Address failures before requesting review
- Ensure code meets quality gates
- Faster iteration on issues

"""
    guidance += format_cooldown_message()
    return guidance


def main():
    try:
        input_data = json.load(sys.stdin)
        session_id = input_data.get("session_id", "")
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Only monitor Bash tool
        if tool_name != "Bash":
            print("{}")
            sys.exit(0)

        # Extract command from tool input
        command = tool_input.get("command", "")

        # Check for errors - don't remind if the command failed
        # PostToolUse may have errors in tool_result
        tool_result = input_data.get("tool_result", {})
        if tool_result.get("error"):
            print("{}")
            sys.exit(0)

        # Check if this is a git push
        if is_git_push(command):
            # Check if repo has CI workflows
            if not has_github_workflows():
                print("{}")
                sys.exit(0)

            # Check cooldown
            if is_within_cooldown(session_id):
                print("{}")
                sys.exit(0)

            # Record this reminder
            record_reminder(session_id)

            # Provide CI monitoring guidance
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": get_guidance_for_push()
                }
            }

            print(json.dumps(output))
            sys.exit(0)

        # Check if this is a PR creation
        if is_pr_creation(command):
            # Check if repo has CI workflows
            if not has_github_workflows():
                print("{}")
                sys.exit(0)

            # Check cooldown
            if is_within_cooldown(session_id):
                print("{}")
                sys.exit(0)

            # Record this reminder
            record_reminder(session_id)

            # Provide CI monitoring guidance
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": get_guidance_for_pr()
                }
            }

            print(json.dumps(output))
            sys.exit(0)

        # Not a triggering command
        print("{}")
        sys.exit(0)

    except Exception as e:
        # Log to stderr for debugging
        print(f"Error in monitor-ci-results hook: {e}", file=sys.stderr)
        # Always output valid JSON on error
        print("{}")
        sys.exit(1)


if __name__ == "__main__":
    main()
