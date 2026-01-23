# Claude Code Configuration Repository

This repository contains version-controlled configuration for **Claude Code CLI and Web**.

## Repository Structure
- `.claude/` - Configuration directory (works for both CLI and Web)
  - `settings.json` - Core configuration (permissions, hooks, model selection)
  - `CLAUDE.md` - Global user instructions
  - `hooks/` - Custom hook scripts
  - `plugins/` - Plugin configuration
- `setup.sh` - Setup script for CLI (creates symlinks from ~/.claude/ to .claude/)

## How It Works

**For Claude Code Web:**
- Configuration in `.claude/` is automatically available (project scope)
- No additional setup required when using this repository

**For Claude Code CLI:**
- Run `./setup.sh` to create symlinks from `~/.claude/` to `.claude/`
- Allows version-controlled configuration on your local machine

## Self-Management Instructions for Claude

When working in this repository, you are managing the user's Claude Code configuration.

### Modifying Hooks
- Hooks are Python scripts with PEP 723 inline dependency declarations
- All hooks must output valid JSON (even empty `{}` when no action needed)
- Use `uv run --script` to execute hooks
- Test hooks manually before committing: `echo '{"test":"data"}' | uv run --script .claude/hooks/hookname.py`

### Hook Development Guidelines
1. Always include PEP 723 header with dependencies
2. Use try-except to catch errors and output `{}` on failure
3. For PostToolUseFailure hooks, check both `error` and `tool_result.error` fields
4. Use `additionalContext` for guidance, not `decision` in PostToolUseFailure
5. Test locally before deploying
6. Document hook behavior in .claude/hooks/README.md

### Modifying Settings
- Edit `.claude/settings.json` directly
- Validate JSON syntax before committing
- Test permission changes carefully
- Document why permissions were added/changed in commit messages

### Commit Messages
Follow conventional commit format:
```
feat(hooks): add new heredoc detection hook
fix(settings): correct WebFetch permission for docs.python.org
docs(hooks): document GPG signing helper behavior
```

### Testing Changes
After making changes:
1. Restart Claude Code session (`/exit` then `claude --continue`). The user has to do this.
2. Verify configuration loads correctly
3. Test affected features (hooks, permissions)
4. Check `~/.claude/debug/latest` for errors

### Safety Guidelines
- Never commit sensitive data (tokens, history, personal info)
- Always use .gitignore to protect runtime data
- Test symlinks after modifications
- Keep backups before major changes

## Syncing to Other Machines
1. Clone this repo: `git clone https://github.com/Jython1415/claude-code-config.git`
2. Run setup script: `cd claude-code-config && ./setup.sh`
3. Restart Claude Code: `/exit` then `claude`
4. Verify configuration loaded correctly
