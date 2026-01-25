# Claude Code Hooks Plugin

A comprehensive set of productivity hooks for Claude Code, providing intelligent suggestions, workflow improvements, and safety mechanisms.

## Features

### 11 Productivity Hooks

**PreToolUse Hooks (Before tool execution):**
- **normalize-line-endings** - Automatically converts CRLF/CR line endings to LF
- **gh-authorship-attribution** - Reminds about attribution for AI-assisted contributions
- **gh-web-fallback** - Suggests GitHub API alternatives when `gh` CLI unavailable
- **prefer-modern-tools** - Suggests `fd`/`rg` over `find`/`grep` when available
- **detect-cd-pattern** - Warns about global `cd` patterns, suggests absolute paths
- **prefer-gh-for-own-repos** - Suggests `gh` CLI for Jython1415 repos

**PostToolUse Hooks (After successful execution):**
- **gpg-signing-helper** - Provides guidance for GPG signing errors in sandbox
- **detect-heredoc-errors** - Suggests alternatives for heredoc temp file errors

**PostToolUseFailure Hooks (After failed execution):**
- **gh-fallback-helper** - Reactive guidance for failed `gh` commands
- **gpg-signing-helper** - GPG error handling
- **detect-heredoc-errors** - Heredoc error workarounds
- **suggest-uv-for-missing-deps** - Suggests `uv run` for Python import errors

### Graceful Failure Handling

All hooks use `run-with-fallback.sh` wrapper for safety:
- Hooks that crash don't block Claude Code
- Advisory messages instead of deadlocks
- Production-hardened for reliability

### Cooldown Mechanisms

Smart rate limiting prevents repetitive suggestions:
- Attribution reminders: 60 seconds
- Prefer-gh suggestions: 60 seconds
- Web fallback guidance: 300 seconds (5 minutes)

## Installation

### From GitHub Marketplace

```bash
# Add marketplace
claude plugin marketplace add Jython1415/claude-code-config

# Install plugin globally
claude plugin install claude-code-hooks@claude-code-config

# Or install for current project only
claude plugin install claude-code-hooks@claude-code-config --scope project
```

### Local Development

```bash
# Clone the repository
git clone https://github.com/Jython1415/claude-code-config.git
cd claude-code-config

# Test plugin locally
claude --plugin-dir ./plugins/claude-code-hooks
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

### prefer-gh-for-own-repos
**Event:** PreToolUse (WebFetch|Bash)
**Purpose:** Suggest `gh` CLI for Jython1415 repositories
**Triggers:** WebFetch/curl to github.com/Jython1415
**Cooldown:** 60 seconds
**Output:** `gh` CLI suggestions

### gh-web-fallback
**Event:** PreToolUse (Bash)
**Purpose:** Guide to GitHub API when `gh` unavailable
**Triggers:** Command contains `gh` + `gh` not available + GITHUB_TOKEN set
**Cooldown:** 300 seconds
**Output:** GitHub API usage guidance

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

https://github.com/Jython1415/claude-code-config
