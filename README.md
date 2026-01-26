# Claude Code Configuration

My personal version-controlled configuration for [Claude Code CLI and Web](https://code.claude.com/docs).

## Overview

This repository serves as:

- **Project-scoped configuration**: Configuration in `.claude/` is automatically available when using this repository (both CLI and Web)
- **Hook development workspace**: Source repository for the `claude-code-hooks` plugin
- **Personal settings reference**: My custom permissions, instructions, and preferences

## Repository Structure

```
claude-code-config/
├── README.md                          # This file
├── CLAUDE.md                          # Self-management instructions for Claude
├── .claude/                           # Project-scoped configuration
│   ├── settings.json                  # Core configuration (permissions, hooks, model)
│   ├── CLAUDE.md                      # User instructions for Claude
│   ├── hooks/                         # Custom hooks (symlinked to plugin)
│   │   ├── README.md                  # Hook documentation
│   │   └── tests/                     # Comprehensive test suite (481 tests)
│   └── plugins/
│       └── installed_plugins.json     # Plugin installation list
├── plugins/
│   └── claude-code-hooks/             # Hook plugin (source of truth)
│       ├── marketplace.json           # Plugin metadata
│       └── hooks/                     # Actual hook implementations (11 scripts)
├── pyproject.toml                     # Python project metadata
└── .gitignore                         # Protects runtime data from commits
```

## How to Use This Repository

### Option 1: Project-Scoped Configuration (Recommended)

Use this repository as your working directory in Claude Code:

1. Clone this repository:
   ```bash
   git clone https://github.com/Jython1415/claude-code-config.git
   cd claude-code-config
   ```

2. Open in Claude Code:
   ```bash
   claude  # CLI
   # or open via web interface
   ```

3. Configuration in `.claude/` is automatically available (both CLI and Web)

### Option 2: Install Hooks via Plugin Marketplace

To use just the hooks globally without this entire configuration:

```bash
# Install the claude-code-hooks plugin
claude plugin install claude-code-hooks@claude-code-config

# Configure the hooks in your own ~/.claude/settings.json
```

See `plugins/claude-code-hooks/README.md` for plugin-specific documentation.

### Option 3: Manual Global Setup (Advanced CLI Users)

If you want this entire configuration as your global `~/.claude/` config:

1. **Backup existing config**:
   ```bash
   cp -R ~/.claude ~/.claude-backup-$(date +%Y%m%d-%H%M%S)
   ```

2. **Create symlinks manually**:
   ```bash
   cd /path/to/claude-code-config
   ln -sf "$(pwd)/.claude/settings.json" ~/.claude/settings.json
   ln -sf "$(pwd)/.claude/CLAUDE.md" ~/.claude/CLAUDE.md
   ln -sf "$(pwd)/.claude/hooks" ~/.claude/hooks
   mkdir -p ~/.claude/plugins
   ln -sf "$(pwd)/.claude/plugins/installed_plugins.json" ~/.claude/plugins/installed_plugins.json
   ```

3. **Restart Claude Code**:
   ```bash
   /exit
   claude
   ```

**Note**: On Windows, symlinks require Developer Mode, Administrator privileges, or WSL.

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
2. Test changes (hooks have 481 tests: `uv run pytest`)
3. Review changes: `git diff`
4. Commit: `git commit -am "feat: description of change"`
5. Push: `git push`

If using symlinked global config (Option 3), changes in this repo automatically affect `~/.claude/`.

## Hook Development

This repository serves as the development workspace for the `claude-code-hooks` plugin:

1. Edit hooks in `plugins/claude-code-hooks/hooks/`
2. Symlinks in `.claude/hooks/` automatically reflect changes
3. Run tests: `uv run pytest .claude/hooks/tests/`
4. Update version in `plugins/claude-code-hooks/marketplace.json`
5. Publish to plugin marketplace (when ready)

See `.claude/hooks/README.md` for hook development guidelines.

## License

MIT License - see [LICENSE](LICENSE)
