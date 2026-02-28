# core-hooks Plugin

A comprehensive set of productivity hooks for Claude Code, providing intelligent suggestions, workflow improvements, and safety mechanisms.

## Features

### 15 Productivity Hooks

**SessionStart Hooks (At session initialization):**
- **ensure-tmpdir** - Ensures the TMPDIR directory exists at session start

**PreToolUse Hooks (Before tool execution):**
- **normalize-line-endings** - Automatically converts CRLF/CR line endings to LF
- **gh-authorship-attribution** - Reminds about attribution for AI-assisted contributions
- **prefer-modern-tools** - Suggests `fd`/`rg` over `find`/`grep` when available
- **detect-cd-pattern** - Warns about global `cd` patterns, suggests absolute paths
- **block-heredoc-in-bash** - Blocks heredoc syntax that silently fails in sandbox mode
- **guard-external-repo-writes** - Blocks `gh` CLI write operations to repositories the user does not own
- **markdown-commit-reminder** - Warns when staging markdown files that may be temporary session documents

**PostToolUse Hooks (After successful execution):**
- **gpg-signing-helper** - Provides guidance for GPG signing errors in sandbox
- **detect-heredoc-errors** - Suggests alternatives for heredoc temp file errors
- **monitor-ci-results** - Reminds to check CI status after a push or PR creation

**PostToolUseFailure Hooks (After failed execution):**
- **gh-fallback-helper** - Reactive guidance for failed `gh` commands
- **gpg-signing-helper** - GPG error handling
- **detect-heredoc-errors** - Heredoc error workarounds
- **suggest-uv-for-missing-deps** - Suggests `uv run` for Python import errors

**PermissionRequest Hooks (When a permission dialog appears):**
- **log-event** - Observer-only; logs the event (tool name, input, permission suggestions) to JSONL

**Notification Hooks (When Claude Code sends a notification):**
- **log-event** - Observer-only; logs the event (message, title, notification type) to JSONL

### Graceful Failure Handling

All hooks use `run-with-fallback.sh` wrapper for safety:
- Hooks that crash don't block Claude Code
- Advisory messages instead of deadlocks
- Production-hardened for reliability

### Hook Event Logging

Opt-in sidecar logging captures the full input and output of every hook invocation — including `PermissionRequest` and `Notification` events — for observability and post-session analysis.

**Enable by setting `JSHOES_HOOK_LOG_DIR`.** Two recommended approaches:

**Option 1: `~/.claude/settings.json` (recommended — persists across all projects on this machine)**

Add the `env` field at user scope (`~/.claude/settings.json`):

```json
{
  "env": {
    "JSHOES_HOOK_LOG_DIR": "~/.claude/hook-logs"
  }
}
```

This activates logging globally for this machine without touching the plugin or any project config.

**Option 2: Shell profile (`~/.zshrc` / `~/.bashrc`)**

```bash
export JSHOES_HOOK_LOG_DIR=~/.claude/hook-logs
```

When set, each Claude Code session appends JSONL entries to `$JSHOES_HOOK_LOG_DIR/{session_id}.jsonl`. The `session_id` matches CC's own session records in `~/.claude/projects/` so logs can be joined for post-session analysis. Each entry contains:

```json
{
  "ts": "2026-02-24T10:00:00Z",
  "hook": "normalize-line-endings.py",
  "input": { "session_id": "...", "tool_name": "Write", ... },
  "output": {}
}
```

Logging is **disabled by default** (env var unset = no files written). Logging errors are silently swallowed — logging never blocks hook execution.

This complements project-level observer hooks, which can see event metadata but not individual plugin hook decisions.

### Cooldown Mechanisms

Smart rate limiting prevents repetitive suggestions:
- Attribution reminders: 60 seconds

## Installation

### From GitHub Marketplace

```bash
# Add marketplace
claude plugin marketplace add Jython1415/jshoes-claude-plugins

# Install plugin globally
claude plugin install core-hooks@jshoes-claude-plugins

# Or install for current project only
claude plugin install core-hooks@jshoes-claude-plugins --scope project
```

### Local Development

```bash
# Clone the repository
git clone https://github.com/Jython1415/jshoes-claude-plugins.git
cd jshoes-claude-plugins

# Test plugin locally
claude --plugin-dir ./plugins/core-hooks
```

## Hook Details

### normalize-line-endings
**Event:** PreToolUse (Write|Edit)
**Purpose:** Normalize line endings to LF
**Triggers:** Content contains `\r\n` or `\r`
**Output:** Updated content with normalized line endings

### gh-authorship-attribution
**Event:** PreToolUse (Bash)
**Purpose:** Remind about AI contribution attribution
**Triggers:** `git commit`, GitHub API calls, `gh pr/issue create`
**Cooldown:** 60 seconds
**Output:** Attribution guidance for commits and PRs

### prefer-modern-tools
**Event:** PreToolUse (Bash)
**Purpose:** Suggest modern alternatives
**Triggers:** `find` command when `fd` available, `grep` when `rg` available
**Output:** Tool suggestion with usage examples

### detect-cd-pattern
**Event:** PreToolUse (Bash)
**Purpose:** Warn about global `cd` patterns
**Triggers:** `cd dir && cmd` or `cd dir; cmd` (but NOT `(cd dir && cmd)`)
**Output:** Suggestion to use absolute paths instead

### block-heredoc-in-bash
**Event:** PreToolUse (Bash)
**Purpose:** Block heredoc syntax before it silently corrupts data in sandbox mode
**Triggers:** Any `<<EOF`, `<<'EOF'`, `<<"EOF"`, `<<-EOF`, or variant (regex: `<<-?\s*['"]?\w`)
**Output:** BLOCKS the command; provides three alternatives (multiple `-m` flags, `--body-file`, Write tool)

### gh-fallback-helper
**Event:** PostToolUseFailure (Bash)
**Purpose:** Reactive guidance for failed `gh` commands
**Triggers:** Command with `gh` + error "not found" + GITHUB_TOKEN set
**Output:** GitHub API patterns

### gpg-signing-helper
**Event:** PostToolUse/PostToolUseFailure (Bash)
**Purpose:** Guide on GPG errors in sandbox
**Triggers:** Error contains "gpg failed", "can't connect to agent", "No agent"
**Output:** `--no-gpg-sign` guidance

### detect-heredoc-errors
**Event:** PostToolUse/PostToolUseFailure (Bash)
**Purpose:** Provide heredoc workarounds
**Triggers:** Error "can't create temp file for here document"
**Timeout:** 10 seconds
**Output:** 3 alternative approaches

### suggest-uv-for-missing-deps
**Event:** PostToolUseFailure (Bash)
**Purpose:** Suggest `uv run` for Python import errors
**Triggers:** ModuleNotFoundError/ImportError + direct Python execution
**Output:** Dependency installation guidance

### guard-external-repo-writes
**Event:** PreToolUse (Bash)
**Purpose:** Block `gh` CLI write operations targeting repositories the user does not own
**Triggers:** `gh issue create/comment/close`, `gh pr create/comment/review`, etc. with `--repo` or `-R` pointing to a non-owned repo
**Cache:** Authenticated GitHub username cached for 24 hours via `gh api user`
**Output:** BLOCKS the command; instructs the user to run it themselves or confirm

### markdown-commit-reminder
**Event:** PreToolUse (Bash)
**Purpose:** Remind about markdown file inclusion criteria before commits
**Triggers:** `git add *.md`, `git add .`, `git commit` with `.md` files mentioned
**Cooldown:** 300 seconds (5 minutes), per session
**Output:** Guidance on when to commit vs. skip temporary markdown documents; heightened warning for files matching suspicious patterns (`_REPORT.md`, `_FINDINGS.md`, `TEMP_*.md`, etc.)

### monitor-ci-results
**Event:** PostToolUse (Bash)
**Purpose:** Remind to check CI after pushing or creating a PR
**Triggers:** Successful `git push`, `gh pr create`, or GitHub API PR creation — only when `.github/workflows/` contains YAML files
**Cooldown:** 120 seconds (2 minutes), per session
**Output:** `gh run list`/`gh pr checks` commands; GitHub API equivalents when `gh` is unavailable

### log-event
**Events:** PermissionRequest, Notification
**Purpose:** Observer-only hook that logs permission prompts and notifications to JSONL
**Triggers:** All permission requests (any tool) and all notification types
**Output:** `{}` — no decision; logging is handled by `run-with-fallback.sh` when `JSHOES_HOOK_LOG_DIR` is set
**Captured fields:**
- PermissionRequest: `tool_name`, `tool_input`, `permission_suggestions`
- Notification: `message`, `title`, `notification_type`

## Requirements

- Claude Code CLI
- Python 3.11+ (for hooks)
- Optional: `fd`, `rg`, `gh` CLI tools (for enhanced functionality)

## License

MIT

## Author

**Jython1415**
https://github.com/Jython1415

## Repository

https://github.com/Jython1415/jshoes-claude-plugins
