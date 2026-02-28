# Claude Code Configuration Repository

This repository contains version-controlled configuration for **Claude Code CLI**.

## Repository Structure
- `plugins/core-hooks/` - Hook scripts and tests (published to marketplace)
  - `hooks/` — hook source files
  - `tests/` — hook tests
- `plugins/plugin-support/` - Hook development skill, hook reference docs, and `/feedback` skill (consumer issue filing)
  - `skills/hook-development/SKILL.md` — hook authoring guide
- `plugins/orchestration-discipline/` - stop-momentum and delegation-guard hooks (execution discipline)
- `plugins/dev-workflow/` - Dev workflow skills (if present)
- Root `CLAUDE.md` - Project instructions for Claude
- **`.claude/` is gitignored** — local runtime state only; no tracked files tracked under `.claude/`

## Self-Management Instructions for Claude

When working in this repository, you are managing the user's Claude Code configuration.

### Modifying Hooks
Use the `/hook-development` skill (`plugins/plugin-support/skills/hook-development/SKILL.md`) for all hook authoring, testing, lifecycle, and performance guidance.
**Always read this skill at session start when hook changes are anticipated.** Read: `plugins/plugin-support/skills/hook-development/SKILL.md`

Quick manual test: `echo '{"tool_name":"Bash","tool_input":{"command":"test"}}' | uv run --script plugins/core-hooks/hooks/hookname.py`

### Modifying Settings
- Edit your local `.claude/settings.json` directly (not tracked in git)
- Validate JSON syntax before making changes
- Test permission changes carefully
- Document why permissions were added/changed in commit messages

### Plugin Versioning
Each plugin has a `version` field in `plugins/<name>/.claude-plugin/plugin.json`. Use lightweight SemVer:
- **Patch** (1.0.x): Bug fixes, documentation updates, minor guidance changes
- **Minor** (1.x.0): New hooks or skills added; new capabilities or modes added to existing skills (e.g., a new `--flag` that meaningfully changes behavior)
- **Major** (x.0.0): Breaking changes (removed hooks, renamed skills, changed interfaces)

**Rule**: Bump the version in the same commit that ships the change. Never let `plugin.json` lag behind. CI enforces this on every PR that touches plugin files. Also keep `.claude-plugin/marketplace.json` in sync — CI verifies that its per-plugin version fields match `plugin.json` whenever a version is bumped.

**Changelog**: Every minor or major version bump must include a `CHANGELOG.md` entry in `plugins/<name>/CHANGELOG.md`. Create the file if it doesn't exist. Format: `## [x.y.z] - YYYY-MM-DD` followed by a `### Added`/`### Changed`/`### Fixed` section.

**Consumer documentation**: When shipping a configurable feature (new env var, new opt-in behavior), include README documentation for plugin consumers in the same commit. Docs are part of the feature — not a follow-up.

**Renaming a plugin**: When renaming a plugin directory, all of these must be updated in the same PR:
1. `marketplace.json` — entry `name` and `version` fields
2. `plugins/<new-name>/.claude-plugin/plugin.json` — `name` field
3. `plugins/<new-name>/CHANGELOG.md` — add rename entry
4. `plugins/<new-name>/README.md` — install commands referencing the old name
5. Other plugins' READMEs that cross-reference the renamed plugin
6. Any SKILL.md files that list plugin names (e.g. the `/feedback` skill)
7. `pyproject.toml` — `[project].name` if it matches the old plugin name

### Writing Skills
- Do not use `allowed-tools` in skill frontmatter
- Skills should be self-contained SKILL.md files under `plugins/<name>/skills/<skill-name>/`
- When a skill has a deliberately limited scope, lead the description with explicit constraint language (e.g., "ONLY for X"). Contextual hints are not enough — ambiguous descriptions invite misuse in unintended contexts.

### Workflow
Always create a feature branch before committing changes. Never commit directly to `main`. Use the `/solve` pattern (or create a branch manually) before making the first commit.

Use squash merge when closing PRs: `gh pr merge --squash --delete-branch`. This updates local main and deletes both local and remote feature branches in one step.

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

**CI trigger scope**: `version-check.yml` only fires on `plugins/**` changes. PRs that only touch `.github/` or `CLAUDE.md` won't run it. To test a workflow change, the PR must also include a plugin file change.

### Safety Guidelines
- Never commit sensitive data (tokens, history, personal info)
- Always use .gitignore to protect runtime data
- Keep backups before major configuration changes
- Test hook changes thoroughly: `uv run pytest`

### Python and Tooling Conventions
- Use `uv run` or `uv run --script` over `python` when running Python files, unless specified otherwise
- For temporary Python scripts: write the script, `uv run` to execute it, then clean up with `rm`
  - Works in sandbox mode (unlike heredoc which creates files in `/tmp/`)
  - For temporary Python scripts, use inline dependencies (PEP 723) and run with `uv`
- When creating temporary files, DO NOT put them in `/tmp/claude/`. Put them in the project directory.
- If you create any temporary new files, scripts, or helper files for iteration, clean up these files by removing them at the end of the task.

### General Instructions
- Use emojis only when directed to do so
- If you intend to call multiple tools and there are no dependencies between the tool calls, make all of the independent tool calls in parallel. Prioritize calling tools simultaneously whenever the actions can be done in parallel rather than sequentially. Maximize use of parallel tool calls where possible to increase speed and efficiency. However, if some tool calls depend on previous calls to inform dependent values like the parameters, do NOT call these tools in parallel and instead call them sequentially.
- If a task will take more than 5–8 tool calls, then prefer to hand it off to a subagent and have it report back to you. You are the orchestrator. Use subagents in a "call stack" style.
- Take ownership over the tasks in the repositories and projects you manage, responding in ways that lessen the user's mental overhead.

## Using This Configuration

**Global via plugin marketplace (recommended):**
1. Add marketplace: `claude plugin marketplace add https://github.com/Jython1415/jshoes-claude-plugins`
2. Install plugin: `claude plugin install core-hooks@jshoes-claude-plugins --scope user`
3. Hooks are now active globally

## Testing Philosophy for Hooks

See the `/hook-development` skill (`plugins/plugin-support/skills/hook-development/`) for the full testing philosophy. The key principle: **test behavior, not content** — verify that hooks trigger correctly and produce valid JSON, not the specific wording of guidance messages.
