#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
gpg-signing-helper: Proactive GPG signing helper that injects --no-gpg-sign.

Event: PreToolUse (Bash)

Purpose: Detects git commands that require GPG signing in sandbox mode and
proactively injects --no-gpg-sign (or rewrites to -c commit.gpgSign=false for
rebase) before execution, avoiding sandbox GPG signing failures.

Behavior:
- Monitors Bash commands for git commit/tag/merge/rebase patterns
- For commit/tag/merge: injects --no-gpg-sign after the subcommand
- For rebase: rewrites "git rebase ..." to "git -c commit.gpgSign=false rebase ..."
- Informs Claude of the change via additionalContext
- Non-git commands pass through silently

Injected Flags:
- git commit → --no-gpg-sign
- git tag → --no-gpg-sign
- git merge → --no-gpg-sign
- git rebase → -c commit.gpgSign=false

Examples:
- "git commit -m 'msg'" → "git commit --no-gpg-sign -m 'msg'"
- "git tag -s v1.0.0" → "git tag --no-gpg-sign -s v1.0.0"
- "git merge feature" → "git merge --no-gpg-sign feature"
- "git rebase -i main" → "git -c commit.gpgSign=false rebase -i main"

Handles:
- Piped commands: git commit ... | other_command
- Chained commands: git commit ... && git push
- Already-present flags (no duplication)
- Variations: "git  commit" (extra spaces), different flag orders

Why this matters:
- GPG agent is unavailable in isolated sandbox environments
- Attempting to sign commits without --no-gpg-sign fails silently
- Proactive injection prevents failures before they occur
- Improves workflow efficiency in sandbox mode
"""
import json
import re
import sys


def inject_no_gpg_sign(command: str) -> str | None:
    """
    Inject --no-gpg-sign into git commit/tag/merge commands.
    Returns modified command, or None if no modification needed.
    """
    # Match: git commit (with various flags/args)
    if re.search(r'\bgit\s+commit\b', command):
        # Skip if already has --no-gpg-sign
        if '--no-gpg-sign' in command:
            return None
        # Inject after "git commit"
        return re.sub(
            r'(\bgit\s+commit\b)',
            r'\1 --no-gpg-sign',
            command,
            count=1
        )

    # Match: git tag (with various flags/args)
    if re.search(r'\bgit\s+tag\b', command):
        # Skip if already has --no-gpg-sign
        if '--no-gpg-sign' in command:
            return None
        # Inject after "git tag"
        return re.sub(
            r'(\bgit\s+tag\b)',
            r'\1 --no-gpg-sign',
            command,
            count=1
        )

    # Match: git merge (with various flags/args)
    if re.search(r'\bgit\s+merge\b', command):
        # Skip if already has --no-gpg-sign
        if '--no-gpg-sign' in command:
            return None
        # Inject after "git merge"
        return re.sub(
            r'(\bgit\s+merge\b)',
            r'\1 --no-gpg-sign',
            command,
            count=1
        )

    # Match: git rebase
    if re.search(r'\bgit\s+rebase\b', command):
        # Skip if already has -c commit.gpgSign=false
        if '-c commit.gpgSign=false' in command or '-c' in command and 'commit.gpgSign=false' in command:
            return None
        # Rewrite: "git rebase" → "git -c commit.gpgSign=false rebase"
        return re.sub(
            r'\bgit\s+rebase\b',
            r'git -c commit.gpgSign=false rebase',
            command,
            count=1
        )

    return None


def main():
    try:
        input_data = json.load(sys.stdin)

        # Only process Bash tool calls
        tool_name = input_data.get("tool_name", "")
        if tool_name != "Bash":
            print("{}")
            sys.exit(0)

        # Extract command from tool_input
        tool_input = input_data.get("tool_input", {})
        command = tool_input.get("command", "")

        if not command:
            print("{}")
            sys.exit(0)

        # Try to inject --no-gpg-sign
        modified_command = inject_no_gpg_sign(command)

        if modified_command is None:
            # No modification needed
            print("{}")
            sys.exit(0)

        # Output updatedInput with the modified command
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "gpg-signing-helper: injected --no-gpg-sign to prevent sandbox GPG failures",
                "updatedInput": {
                    "command": modified_command
                },
                "additionalContext": (
                    f"gpg-signing-helper: Proactively injected GPG signing flag to prevent sandbox failures.\n"
                    f"Original:  {command}\n"
                    f"Modified:  {modified_command}\n\n"
                    f"GPG signing is not available in sandbox mode. The hook automatically injects the "
                    f"necessary flag (--no-gpg-sign or -c commit.gpgSign=false for rebase) to allow the "
                    f"command to proceed."
                )
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    except Exception as e:
        # Silently fail: output empty JSON on any error
        print("{}")
        sys.exit(1)


if __name__ == "__main__":
    main()
