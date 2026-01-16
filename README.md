# Claude Code Configuration

Version-controlled configuration for [Claude Code CLI](https://docs.anthropic.com/claude-code).

## Overview

This repository stores Claude Code configuration files, enabling:
- Backup and disaster recovery for custom hooks and permissions
- Configuration sync across multiple machines
- Change tracking for hooks and permissions over time
- Quick setup of new development environments
- Rollback capability if configurations break

## Repository Structure

```
claude-code-config/
├── README.md                          # This file
├── CLAUDE.md                          # Self-management instructions for Claude
├── setup.sh                           # Automated setup script
├── settings.json                      # Core configuration (permissions, hooks, model)
├── CLAUDE-global.md                   # Global user instructions (symlinked to ~/.claude/CLAUDE.md)
├── hooks/                             # Custom hook scripts
│   ├── README.md                      # Hook documentation
│   ├── normalize-line-endings.py      # Normalizes line endings on Write/Edit
│   ├── auto-unsandbox-pbcopy.py       # Auto-approves pbcopy commands
│   ├── gpg-signing-helper.py          # Assists with GPG signing for git commits
│   └── detect-heredoc-errors.py       # Detects heredoc-related errors
├── plugins/
│   └── installed_plugins.json         # Plugin installation list
└── .gitignore                         # Protects runtime data from commits
```

## Setup on a New Machine

1. Clone this repository:
   ```bash
   cd ~/Documents/_programming  # or your preferred location
   git clone https://github.com/Jython1415/claude-code-config.git
   cd claude-code-config
   ```

2. Run the setup script:
   ```bash
   ./setup.sh
   ```

   Use `--force` to overwrite existing symlinks:
   ```bash
   ./setup.sh --force
   ```

3. Restart Claude Code:
   ```bash
   # If in a Claude session
   /exit
   # Then start fresh
   claude
   ```

4. Verify configuration loaded correctly by testing hooks work as expected.

## What Gets Symlinked

The setup script creates symlinks from `~/.claude/` to this repository:

| Source (repo) | Target (~/.claude/) |
|---------------|---------------------|
| `settings.json` | `settings.json` |
| `CLAUDE-global.md` | `CLAUDE.md` |
| `hooks/` | `hooks/` |
| `plugins/installed_plugins.json` | `plugins/installed_plugins.json` |

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

Since `~/.claude/` files are symlinked to this repo:

1. Edit files normally (changes appear in repo automatically)
2. Review changes: `git diff`
3. Commit: `git commit -am "description of change"`
4. Push: `git push`

## Recovering from Issues

If configuration breaks:

1. Check the backup created by setup.sh: `~/.claude-backup-YYYYMMDD-HHMMSS/`
2. Or restore from git: `git checkout -- settings.json`
3. Restart Claude Code

## License

MIT License - see [LICENSE](LICENSE)
# Test comment
