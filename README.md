# Claude Code Configuration

A Claude Code plugin repository with hooks, skills, and workflow tools. See [Claude Code docs](https://code.claude.com/docs).

## Overview

This repository serves as:

- **Project-scoped configuration**: Configuration in `.claude/` is automatically available when using this repository
- **Hook development workspace**: Source repository for the `core-hooks` plugin

## How to Use This Repository

### Option 1: Project-Scoped Configuration (Recommended)

Use this repository as your working directory in Claude Code:

1. Clone this repository:
   ```bash
   git clone https://github.com/Jython1415/jshoes-claude-plugins.git
   cd jshoes-claude-plugins
   ```

2. Open in Claude Code:
   ```bash
   claude  # CLI
   ```

3. Configuration in `.claude/` is automatically available 

### Option 2: Global Installation via Plugin Marketplace (Recommended for Global Use)

Install hooks globally to use them in all your projects:

1. **Add this repository as a plugin marketplace**:
   ```bash
   claude plugin marketplace add https://github.com/Jython1415/jshoes-claude-plugins
   ```

2. **Install the core-hooks plugin**:
   ```bash
   claude plugin install core-hooks@jshoes-claude-plugins --scope user
   ```

3. **Hooks are now active globally**. You can optionally copy custom permissions from `.claude/settings.json` to your `~/.claude/settings.json` if desired.

See `plugins/core-hooks/README.md` for plugin-specific documentation.

## What's Included

### Custom Hooks (13 total)

See `plugins/core-hooks/README.md` for detailed documentation.

| Hook | Event | Purpose |
|------|-------|---------|
| `ensure-tmpdir.py` | SessionStart | Creates TMPDIR directory if missing at session start |
| `normalize-line-endings.py` | PreToolUse (Write/Edit) | Converts CRLF/CR to LF |
| `gh-authorship-attribution.py` | PreToolUse (Bash) | Ensures proper attribution for AI-assisted commits |
| `prefer-modern-tools.py` | PreToolUse (Bash) | Suggests fd/rg instead of find/grep |
| `detect-cd-pattern.py` | PreToolUse (Bash) | Warns on global cd, allows subshell pattern |
| `block-heredoc-in-bash.py` | PreToolUse (Bash) | Blocks heredoc syntax that silently fails in sandbox mode |
| `guard-external-repo-writes.py` | PreToolUse (Bash) | Blocks gh CLI write ops to external repos |
| `markdown-commit-reminder.py` | PreToolUse (Bash) | Warns about temporary markdown files in commits |
| `gh-fallback-helper.py` | PostToolUseFailure (Bash) | GitHub API guidance when gh CLI fails |
| `gpg-signing-helper.py` | PostToolUse/PostToolUseFailure (Bash) | GPG signing guidance |
| `detect-heredoc-errors.py` | PostToolUse/PostToolUseFailure (Bash) | Heredoc workarounds |
| `suggest-uv-for-missing-deps.py` | PostToolUseFailure (Bash) | Suggests uv run with PEP 723 |
| `monitor-ci-results.py` | PostToolUse (Bash) | Reminds to check CI after push/PR creation |

### Custom Permissions

Extensive pre-approved permissions in `.claude/settings.json`:
- Web search and fetch for trusted domains
- Git operations (status, log, diff, commit, etc.)
- GitHub CLI operations (gh)
- Common shell commands (ls, grep, find, etc.)
- Python/Node/Rust tooling (pytest, npm, cargo, etc.)

### Custom Instructions

`CLAUDE.md` (project root) contains self-management instructions for Claude, including:
- Preference for `uv run` over `python`
- Instructions for temporary Python scripts
- Parallel tool execution patterns
- Subagent orchestration guidelines
- Testing philosophy for hooks

## What's NOT Tracked (Runtime Data)

The following are intentionally excluded via `.gitignore`:
- `history.jsonl` - Conversation history (privacy)
- `debug/` - Debug logs
- `projects/` - Project metadata
- `shell-snapshots/` - Session state
- `file-history/` - Edit history
- `todos/`, `plans/` - Personal task lists
- `cache/`, `session-env/` - Temporary state
- `local/`, `skills/` - Regenerable binaries
- `hook-logs/` - Hook execution logs
- `stats-cache.json` - Usage statistics

## Making Configuration Changes

1. Edit plugin files in `plugins/`
2. Test changes: `uv run pytest`
3. Review changes: `git diff`
4. Commit: `git commit -am "feat: description of change"`
5. Push: `git push`

**Note**: If you've installed the plugin globally (Option 2), you'll need to update the plugin to get the latest changes:
```bash
claude plugin update core-hooks@jshoes-claude-plugins
```

## Hook Development

This repository serves as the development workspace for the `core-hooks` plugin:

1. Edit hooks in `plugins/core-hooks/hooks/`
2. Run tests: `uv run pytest plugins/core-hooks/tests/`
3. Bump version in `plugins/core-hooks/.claude-plugin/plugin.json` (same commit)
4. Publish to plugin marketplace (when ready)

See `plugins/core-hooks/README.md` for hook documentation and `plugins/plugin-support/skills/hook-development/` for the authoring guide.

## License

MIT License - see [LICENSE](LICENSE)
