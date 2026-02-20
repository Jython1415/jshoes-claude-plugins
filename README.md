# Claude Code Configuration

My personal version-controlled configuration for [Claude Code CLI and Web](https://code.claude.com/docs).

## Overview

This repository serves as:

- **Project-scoped configuration**: Configuration in `.claude/` is automatically available when using this repository (both CLI and Web)
- **Hook development workspace**: Source repository for the `claude-code-hooks` plugin
- **Personal settings reference**: My custom permissions, instructions, and preferences

## Repository Structure

```
jshoes-claude-plugins/
├── README.md                          # This file
├── CLAUDE.md                          # Self-management instructions for Claude
├── .claude/                           # Project-scoped configuration
│   ├── settings.json                  # Core configuration (permissions, hooks, model)
│   ├── CLAUDE.md                      # User instructions for Claude
│   ├── hooks/                         # Custom hooks (symlinked to plugin)
│   │   ├── README.md                  # Hook documentation
│   │   └── tests/                     # Comprehensive test suite
│   └── plugins/
│       └── installed_plugins.json     # Plugin installation list
├── plugins/
│   └── claude-code-hooks/             # Hook plugin (source of truth)
│       ├── .claude-plugin/plugin.json # Plugin metadata and version
│       └── hooks/                     # Hook implementations
├── pyproject.toml                     # Python project metadata
└── .gitignore                         # Protects runtime data from commits
```

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
   # or open via web interface
   ```

3. Configuration in `.claude/` is automatically available (both CLI and Web)

### Option 2: Global Installation via Plugin Marketplace (Recommended for Global Use)

Install hooks globally to use them in all your projects:

1. **Add this repository as a plugin marketplace**:
   ```bash
   claude plugin marketplace add https://github.com/Jython1415/jshoes-claude-plugins
   ```

2. **Install the claude-code-hooks plugin**:
   ```bash
   claude plugin install claude-code-hooks@jshoes-claude-plugins --scope user
   ```

3. **Hooks are now active globally**. You can optionally copy custom permissions from `.claude/settings.json` to your `~/.claude/settings.json` if desired.

See `plugins/claude-code-hooks/README.md` for plugin-specific documentation.

## What's Included

### Custom Hooks (11 total)

See `.claude/hooks/README.md` for detailed documentation.

| Hook | Event | Purpose |
|------|-------|---------|
| `normalize-line-endings.py` | PreToolUse (Write/Edit) | Converts CRLF/CR to LF |
| `gh-authorship-attribution.py` | PreToolUse (Bash) | Ensures proper attribution for AI-assisted commits |
| `prefer-modern-tools.py` | PreToolUse (Bash) | Suggests fd/rg instead of find/grep |
| `detect-cd-pattern.py` | PreToolUse (Bash) | Warns on global cd, allows subshell pattern |
| `prefer-gh-for-own-repos.py` | PreToolUse (WebFetch/Bash) | Suggests gh CLI for my repositories |
| `gh-web-fallback.py` | PreToolUse (Bash) | Guides to GitHub API when gh unavailable (Web) |
| `gh-fallback-helper.py` | PostToolUseFailure (Bash) | GitHub API guidance when gh CLI fails |
| `gpg-signing-helper.py` | PostToolUse/PostToolUseFailure (Bash) | GPG signing guidance |
| `detect-heredoc-errors.py` | PostToolUse/PostToolUseFailure (Bash) | Heredoc workarounds |
| `suggest-uv-for-missing-deps.py` | PostToolUseFailure (Bash) | Suggests uv run with PEP 723 |

### Custom Permissions

Extensive pre-approved permissions in `.claude/settings.json`:
- Web search and fetch for trusted domains
- Git operations (status, log, diff, commit, etc.)
- GitHub CLI operations (gh)
- Common shell commands (ls, grep, find, etc.)
- Python/Node/Rust tooling (pytest, npm, cargo, etc.)

### Custom Instructions

`.claude/CLAUDE.md` contains:
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

1. Edit files in `.claude/` directory
2. Test changes: `uv run pytest`
3. Review changes: `git diff`
4. Commit: `git commit -am "feat: description of change"`
5. Push: `git push`

**Note**: If you've installed the plugin globally (Option 2), you'll need to update the plugin to get the latest changes:
```bash
claude plugin update claude-code-hooks@jshoes-claude-plugins
```

## Hook Development

This repository serves as the development workspace for the `claude-code-hooks` plugin:

1. Edit hooks in `plugins/claude-code-hooks/hooks/`
2. Symlinks in `.claude/hooks/` automatically reflect changes
3. Run tests: `uv run pytest .claude/hooks/tests/`
4. Bump version in `plugins/claude-code-hooks/.claude-plugin/plugin.json` (same commit)
5. Publish to plugin marketplace (when ready)

See `.claude/hooks/README.md` for hook development guidelines.

## License

MIT License - see [LICENSE](LICENSE)
