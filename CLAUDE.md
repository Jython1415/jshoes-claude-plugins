# Claude Code Configuration Repository

This repository contains version-controlled configuration for **Claude Code CLI and Web**.

## Repository Structure
- `.claude/` - Project-scoped configuration directory (works for both CLI and Web)
  - `settings.json` - Core configuration (permissions, hooks, model selection)
  - `CLAUDE.md` - User instructions for Claude
  - `hooks/` - Custom hook scripts (symlinked to plugin)
  - `plugins/` - Plugin configuration
- `plugins/claude-code-hooks/` - Hook plugin source (published to marketplace)

## How It Works

**For Claude Code Web:**
- Configuration in `.claude/` is automatically available (project scope)
- No setup required when using this repository

**For Claude Code CLI:**
- Configuration in `.claude/` is automatically available when working in this project directory
- For global configuration: Install hooks via plugin marketplace or manually symlink files

## Self-Management Instructions for Claude

When working in this repository, you are managing the user's Claude Code configuration.

### Modifying Hooks
- Hooks are Python scripts with PEP 723 inline dependency declarations
- All hooks must output valid JSON (even empty `{}` when no action needed)
- Use `uv run --script` to execute hooks
- Test hooks manually before committing: `echo '{"test":"data"}' | uv run --script .claude/hooks/hookname.py`

### Hook Development Guidelines
1. Always include PEP 723 header. Use `requires-python` for hooks with no
   dependencies. Only add `dependencies = [...]` when the hook actually
   imports third-party packages — `uv` does extra work (writing to TMPDIR)
   when `dependencies` is present, even as an empty list.
2. Use try-except to catch errors and output `{}` on failure
3. For PostToolUseFailure hooks, check both `error` and `tool_result.error` fields
4. Use `additionalContext` for guidance, not `decision` in PostToolUseFailure
5. Test locally before deploying
6. Document hook behavior in .claude/hooks/README.md
7. Use `SessionStart` for session-initialization concerns (environment
   setup, directory creation). Use `PreToolUse`/`PostToolUse` only for
   per-command validation and guidance.

### Hook Performance Assumptions
- This repo assumes `uv` is available for running Python hooks
- Python hooks via `uv run --script` are acceptable overhead as long as
  hooks are written with performance in mind (no network requests, no
  heavy computation in the hot path)
- Focus on correctness and lifecycle placement over micro-optimization

### Modifying Settings
- Edit `.claude/settings.json` directly
- Validate JSON syntax before committing
- Test permission changes carefully
- Document why permissions were added/changed in commit messages

### Plugin Versioning
Each plugin has a `version` field in `.claude-plugin/plugin.json`. Use lightweight SemVer:
- **Patch** (1.0.x): Bug fixes, documentation updates, minor guidance changes
- **Minor** (1.x.0): New hooks or skills added
- **Major** (x.0.0): Breaking changes (removed hooks, renamed skills, changed interfaces)

**Rule**: Bump the version in the same commit that ships the change. Never let `plugin.json` lag behind. CI enforces this on every PR that touches plugin files.

### Writing Skills
- Do not use `allowed-tools` in skill frontmatter
- Skills should be self-contained SKILL.md files under `plugins/<name>/skills/<skill-name>/`

### Workflow
Always create a feature branch before committing changes. Never commit directly to `main`. Use the `/solve` pattern (or create a branch manually) before making the first commit.

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
- Keep backups before major configuration changes
- Test hook changes thoroughly: `uv run pytest`

## Using This Configuration on Other Machines

**Option 1: Project-scoped (Recommended for development)**
1. Clone this repo: `git clone https://github.com/Jython1415/jshoes-claude-plugins.git`
2. Work in the repository directory: `cd jshoes-claude-plugins && claude`
3. Configuration in `.claude/` is automatically available

**Option 2: Global via plugin marketplace (Recommended for global use)**
1. Add marketplace: `claude plugin marketplace add https://github.com/Jython1415/jshoes-claude-plugins`
2. Install plugin: `claude plugin install claude-code-hooks@jshoes-claude-plugins --scope user`
3. Hooks are now active globally. Optionally copy custom permissions from `.claude/settings.json` to `~/.claude/settings.json`

## Syncing Config to Other GitHub Repositories

For Claude Code Web usage in other repositories, you can use the provided GitHub Actions workflow to automatically sync configuration.

**Setup (per repository):**
1. Copy `.github/workflow-templates/sync-claude-plugins.yml` to your target repo's `.github/workflows/`
2. If source repo is private: add a `SOURCE_REPO_TOKEN` secret with read access
3. The workflow runs weekly and creates PRs when updates are available
4. Manually trigger via Actions tab for immediate sync

**What gets synced:**
- `.claude/settings.json` - Permissions and hooks configuration
- `.claude/CLAUDE.md` - Instructions for Claude
- `.claude/hooks/*.py` - Hook scripts (symlinks resolved to actual files)

**Local customizations (preserved during sync):**
- `.claude/settings.local.json` - Override settings without affecting synced config
- `.claude/.local-config` - Create this file to opt out of automatic syncs

**Note:** This is a pull-based approach. Each target repository controls its own sync timing and can review changes via PR before merging.
