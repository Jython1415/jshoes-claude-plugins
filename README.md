# Claude Code Configuration

My personal version-controlled configuration for [Claude Code CLI and Web](https://code.claude.com/docs).

## Overview

This repository provides configuration that works seamlessly with **both** Claude Code CLI and Claude Code Web:

- **For Web users**: Configuration in `.claude/` is automatically available when using this repository
- **For CLI users**: Run `setup.sh` to create symlinks from `~/.claude/` to this repository

## Repository Structure

```
claude-code-config/
├── README.md                          # This file
├── CLAUDE.md                          # Self-management instructions for Claude
├── setup.sh                           # Automated setup script for CLI users
├── .claude/                           # Configuration directory (works for both CLI and Web)
│   ├── settings.json                  # Core configuration (permissions, hooks, model)
│   ├── CLAUDE.md                      # Global user instructions
│   ├── hooks/                         # Custom hooks (11 Python scripts)
│   │   ├── README.md                  # Hook documentation
│   │   └── tests/                     # Comprehensive test suite
│   └── plugins/
│       └── installed_plugins.json     # Plugin installation list
├── pyproject.toml                     # Python project metadata
└── .gitignore                         # Protects runtime data from commits
```

## Setup

### For Claude Code Web

No setup required! Configuration in `.claude/` is automatically available when you use this repository in Claude Code Web.

### For Claude Code CLI

1. Clone this repository:
   ```bash
   git clone https://github.com/Jython1415/claude-code-config.git
   cd claude-code-config
   ```

2. Run the setup script:
   ```bash
   ./setup.sh
   ```

3. Restart Claude Code:
   ```bash
   /exit
   claude
   ```

4. Verify configuration loaded correctly by testing that hooks work as expected.

## What Gets Symlinked (CLI Only)

For CLI users, the setup script creates symlinks from `~/.claude/` to this repository:

| Source (repo) | Target (~/.claude/) |
|---------------|---------------------|
| `.claude/settings.json` | `settings.json` |
| `.claude/CLAUDE.md` | `CLAUDE.md` |
| `.claude/hooks/` | `hooks/` |
| `.claude/plugins/installed_plugins.json` | `plugins/installed_plugins.json` |

**Note**: Web users don't need symlinks - configuration in `.claude/` is automatically available.

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

**For CLI users**: Since `~/.claude/` files are symlinked to `.claude/` in this repo:

1. Edit files in `.claude/` directory (or via the `~/.claude/` symlinks)
2. Review changes: `git diff`
3. Commit: `git commit -am "feat: description of change"`
4. Push: `git push`

**For Web users**: Edit files in `.claude/` directory directly:

1. Use Claude Code Web to modify files in `.claude/`
2. Commit and push changes through the web interface or pull to local CLI

## Recovering from Issues

**For CLI users**: If configuration breaks:

1. Check the backup created by setup.sh: `~/.claude-backup-YYYYMMDD-HHMMSS/`
2. Or restore from git: `git checkout -- .claude/settings.json`
3. Restart Claude Code

**For Web users**: Restore from git:

1. `git checkout -- .claude/settings.json` (or the specific file that broke)
2. Commit and push the fix if needed

## License

MIT License - see [LICENSE](LICENSE)

