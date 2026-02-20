# Claude Code Hooks

Custom hooks for enhancing Claude Code behavior.

## Hook Overview

| Hook | Event | Purpose |
|------|-------|---------|
| `ensure-tmpdir.py` | PreToolUse (Bash) | Creates TMPDIR if set but missing (macOS /tmp is periodically cleared) |
| `normalize-line-endings.py` | PreToolUse (Write/Edit) | Converts CRLF/CR to LF |
| `gh-authorship-attribution.py` | PreToolUse (Bash) | Ensures proper attribution for AI-assisted GitHub contributions |
| `prefer-modern-tools.py` | PreToolUse (Bash) | Suggests fd/rg instead of find/grep |
| `detect-cd-pattern.py` | PreToolUse (Bash) | Warns on global cd, allows subshell pattern |
| `prefer-gh-for-own-repos.py` | PreToolUse (WebFetch/Bash) | Suggests gh CLI for Jython1415's repositories |
| `gh-web-fallback.py` | PreToolUse (Bash) | Proactively guides to GitHub API when gh unavailable |
| `gh-fallback-helper.py` | PostToolUseFailure (Bash) | Guides Claude to use GitHub API when gh CLI unavailable |
| `gpg-signing-helper.py` | PostToolUse/PostToolUseFailure (Bash) | Guides Claude on GPG signing issues |
| `detect-heredoc-errors.py` | PostToolUse/PostToolUseFailure (Bash) | Provides heredoc workarounds |
| `suggest-uv-for-missing-deps.py` | PostToolUseFailure (Bash) | Suggests uv run with PEP 723 for import errors |
| `markdown-commit-reminder.py` | PreToolUse (Bash) | Reminds about markdown file inclusion criteria before commits |
| `monitor-ci-results.py` | PostToolUse (Bash) | Reminds to monitor CI results after push or PR creation |

## Development Guide

For hook development guidelines, invoke the skill:

```
/hook-development
```

Or read the skill directly: `.claude/skills/hook-development/SKILL.md`

## Running Tests

```bash
uv run pytest
```
