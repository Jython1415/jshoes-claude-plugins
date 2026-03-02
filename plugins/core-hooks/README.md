# core-hooks Plugin

A focused set of essential hooks for Claude Code, providing critical safety mechanisms and observability.

## Features

### 6 Core Hooks

**SessionStart Hooks (At session initialization):**
- **ensure-tmpdir** - Ensures the TMPDIR directory exists at session start

**PreToolUse Hooks (Before tool execution):**
- **gh-authorship-attribution** - Reminds about attribution for AI-assisted contributions
- **block-heredoc-in-bash** - Blocks heredoc syntax that silently fails in sandbox mode
- **guard-external-repo-writes** - Blocks `gh` CLI write operations to repositories the user does not own

**PostToolUse Hooks (After successful execution):**
- **gpg-signing-helper** - Provides guidance for GPG signing errors in sandbox

**PostToolUseFailure Hooks (After failed execution):**
- **gpg-signing-helper** - GPG error handling

**PermissionRequest & Notification Hooks:**
- **log-event** - Observer-only; logs permission requests and notifications to JSONL for observability

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
    "JSHOES_HOOK_LOG_DIR": "/Users/yourname/.claude/hook-logs"
  }
}
```

Use an **absolute path** — tilde (`~`) is not expanded by the shell when reading values from `settings.json`. This activates logging globally for this machine without touching the plugin or any project config.

**Option 2: Shell profile (`~/.zshrc` / `~/.bashrc`)**

```bash
export JSHOES_HOOK_LOG_DIR=~/.claude/hook-logs
```

When set, each Claude Code session appends JSONL entries to `$JSHOES_HOOK_LOG_DIR/{session_id}.jsonl`. The `session_id` matches CC's own session records in `~/.claude/projects/` so logs can be joined for post-session analysis. Each entry contains:

```json
{
  "ts": "2026-02-24T10:00:00Z",
  "hook": "gh-authorship-attribution.py",
  "input": { "session_id": "...", "tool_name": "Bash", ... },
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

### gh-authorship-attribution
**Event:** PreToolUse (Bash)
**Purpose:** Remind about AI contribution attribution
**Triggers:** `git commit`, GitHub API calls, `gh pr/issue create`
**Cooldown:** 60 seconds
**Output:** Attribution guidance for commits and PRs

### block-heredoc-in-bash
**Event:** PreToolUse (Bash)
**Purpose:** Block heredoc syntax before it silently corrupts data in sandbox mode
**Triggers:** Any `<<EOF`, `<<'EOF'`, `<<"EOF"`, `<<-EOF`, or variant (regex: `<<-?\s*['"]?\w`)
**Output:** BLOCKS the command; provides three alternatives (multiple `-m` flags, `--body-file`, Write tool)

### gpg-signing-helper
**Event:** PostToolUse/PostToolUseFailure (Bash)
**Purpose:** Guide on GPG errors in sandbox
**Triggers:** Error contains "gpg failed", "can't connect to agent", "No agent"
**Output:** `--no-gpg-sign` guidance

### guard-external-repo-writes
**Event:** PreToolUse (Bash)
**Purpose:** Block `gh` CLI write operations targeting repositories the user does not own
**Triggers:** `gh issue create/comment/close`, `gh pr create/comment/review`, etc. with `--repo` or `-R` pointing to a non-owned repo
**Cache:** Authenticated GitHub username cached for 24 hours via `gh api user`
**Output:** BLOCKS the command; instructs the user to run it themselves or confirm

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
- Optional: `gh` CLI tool (for enhanced functionality)

## License

MIT

## Author

**Jython1415**
https://github.com/Jython1415

## Repository

https://github.com/Jython1415/jshoes-claude-plugins
