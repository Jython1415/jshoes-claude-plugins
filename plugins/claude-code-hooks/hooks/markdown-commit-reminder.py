#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
markdown-commit-reminder: Remind about markdown file inclusion criteria before commits.

Event: PreToolUse (Bash)

Purpose: Reminds Claude about when markdown files should or should not be committed,
helping prevent temporary review documents from being accidentally committed.

Behavior:
- Detects git commands that include markdown (.md) files
- Provides guidance via additionalContext about inclusion criteria
- Checks for temporary file patterns (REPORT, FINDINGS, REVIEW, etc.)
- Includes 5-minute cooldown to avoid repetitive reminders

Triggers on:
- `git add *.md` or `git add file.md` - staging markdown files
- `git add .` or `git add -A` - staging all (may include markdown)
- `git commit` with staged markdown files mentioned
- Git commands with paths ending in .md

Does NOT trigger when:
- Within 5-minute cooldown period since last reminder
- Command doesn't involve markdown files
- Non-Bash tools
- Read-only git commands (status, log, diff)

Markdown file inclusion criteria (guidance provided):

DO commit markdown files:
- Permanent documentation (design docs, architecture guides)
- CLAUDE.md or README.md files
- Repositories where committing MD files is the norm
- User-requested documentation

DON'T commit markdown files:
- Temporary files for user review in current session
- Short-lived documentation or reports
- Temporary reports, findings, or analysis documents
- Session-specific outputs meant for immediate consumption

Suspicious patterns detected:
- *_REPORT.md, *_FINDINGS.md, *_REVIEW.md
- *_ANALYSIS.md, *_SUMMARY.md, *_NOTES.md
- TEMP_*.md, temp_*.md
- Files in /tmp/ or temporary directories

State management:
- Cooldown state stored in: `~/.claude/hook-state/markdown-commit-cooldown`
- Contains Unix timestamp of last reminder
- 300-second (5-minute) cooldown period
- Safe to delete if behavior needs to be reset

Benefits:
- Prevents accidental commit of temporary review documents
- Educates about markdown inclusion best practices
- Non-blocking (guidance only, no decision override)
- Works for both direct file staging and bulk staging

Limitations:
- Cannot determine actual intent without user input
- Pattern detection is heuristic-based
- Cannot see which files are already staged (only command text)
- Only monitors Bash tool (not direct git operations from other tools)
"""
import json
import sys
import re
import time
from pathlib import Path

# Cooldown period in seconds (5 minutes)
COOLDOWN_PERIOD = 300

# State file location
STATE_DIR = Path.home() / ".claude" / "hook-state"
STATE_FILE = STATE_DIR / "markdown-commit-cooldown"

# Patterns to detect markdown file involvement in git commands
MD_FILE_PATTERN = r'\.md(?:\s|$|"|\')'
MD_GLOB_PATTERN = r'\*\.md'

# Patterns for bulk add that might include markdown
BULK_ADD_PATTERNS = [
    r'git\s+add\s+\.',          # git add .
    r'git\s+add\s+-A',          # git add -A
    r'git\s+add\s+--all',       # git add --all
    r'git\s+add\s+-u',          # git add -u (only tracked)
]

# Patterns that suggest temporary/review documents
SUSPICIOUS_MD_PATTERNS = [
    r'_REPORT\.md',
    r'_FINDINGS\.md',
    r'_REVIEW\.md',
    r'_ANALYSIS\.md',
    r'_SUMMARY\.md',
    r'_NOTES\.md',
    r'TEMP_.*\.md',
    r'temp_.*\.md',
    r'/tmp/.*\.md',
    r'_temp.*\.md',
    r'_draft.*\.md',
    r'_scratch.*\.md',
]


def is_git_add_or_commit(command: str) -> bool:
    """Check if command is a git add or commit."""
    try:
        return bool(re.search(r'git\s+(add|commit)', command, re.IGNORECASE))
    except Exception:
        return False


def involves_markdown_files(command: str) -> bool:
    """Check if git command involves markdown files."""
    try:
        # Direct .md file reference
        if re.search(MD_FILE_PATTERN, command, re.IGNORECASE):
            return True

        # Glob pattern for .md files
        if re.search(MD_GLOB_PATTERN, command):
            return True

        # Bulk add commands (might include markdown)
        for pattern in BULK_ADD_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return True

        return False
    except Exception:
        return False


def has_suspicious_patterns(command: str) -> list[str]:
    """Check for patterns that suggest temporary/review documents."""
    suspicious = []
    try:
        for pattern in SUSPICIOUS_MD_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                # Extract the matched portion for reporting
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    suspicious.append(match.group(0))
        return suspicious
    except Exception:
        return []


def is_within_cooldown() -> bool:
    """Check if we're within the cooldown period since last reminder."""
    try:
        if not STATE_FILE.exists():
            return False

        last_reminder_time = float(STATE_FILE.read_text().strip())
        current_time = time.time()

        return (current_time - last_reminder_time) < COOLDOWN_PERIOD
    except Exception:
        # Gracefully handle corrupted state file
        return False


def record_reminder():
    """Record that we just showed a reminder."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(str(time.time()))
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


def build_guidance(suspicious_patterns: list[str], is_bulk_add: bool) -> str:
    """Build the guidance message based on detected patterns."""
    guidance = """**MARKDOWN FILE COMMIT REMINDER**

"""

    # Add specific warning if suspicious patterns found
    if suspicious_patterns:
        guidance += f"""**Potentially temporary file detected**: `{'`, `'.join(suspicious_patterns)}`

This looks like a temporary document. Consider if it should be committed.

"""

    # Add note about bulk add
    if is_bulk_add and not suspicious_patterns:
        guidance += """**Bulk staging detected** - This may include markdown files.

"""

    guidance += """**DO commit markdown files when:**
- Permanent documentation (design docs, architecture guides)
- CLAUDE.md, README.md, or similar project docs
- User explicitly requested the documentation
- Repository where markdown docs are the norm

**DON'T commit markdown files when:**
- Temporary files for user review in current session
- Reports, findings, or analysis meant for immediate review
- Session-specific outputs (e.g., security reviews, code analysis)
- Draft or scratch documents

**If uncertain**: Ask the user before committing markdown files.

"""

    guidance += format_cooldown_message()

    return guidance


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

        # Only check git add/commit commands
        if not is_git_add_or_commit(command):
            print("{}")
            sys.exit(0)

        # Check if markdown files are involved
        if not involves_markdown_files(command):
            print("{}")
            sys.exit(0)

        # Check cooldown
        if is_within_cooldown():
            print("{}")
            sys.exit(0)

        # Detect suspicious patterns
        suspicious = has_suspicious_patterns(command)

        # Check if this is a bulk add
        is_bulk = any(
            re.search(pattern, command, re.IGNORECASE)
            for pattern in BULK_ADD_PATTERNS
        )

        # Record this reminder
        record_reminder()

        # Provide guidance
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": build_guidance(suspicious, is_bulk)
            }
        }

        print(json.dumps(output))
        sys.exit(0)

    except Exception as e:
        # Log to stderr for debugging
        print(f"Error in markdown-commit-reminder hook: {e}", file=sys.stderr)
        # Always output valid JSON on error
        print("{}")
        sys.exit(1)


if __name__ == "__main__":
    main()
