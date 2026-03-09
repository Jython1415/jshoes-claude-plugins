# Changelog

## [3.1.0] - 2026-03-09

### Changed
- Refactored `gpg-signing-helper` from reactive PostToolUseFailure to proactive PreToolUse with `updatedInput`
- Now injects `--no-gpg-sign` (or `-c commit.gpgSign=false` for rebase) before execution instead of advising after failure
- Expanded command coverage: commit, rebase, tag, and merge

## [3.0.1] - 2026-03-08

### Fixed
- `guard-external-repo-writes`: replaced deprecated `decision: "block"` field with `permissionDecision: "deny"` (hook was advisory-only instead of blocking)

## [3.0.0] - 2026-03-01

### Changed
- Renamed plugin from `core-hooks` to `essentials` to better reflect the scope: essential hooks for all Claude Code users

## [2.0.0] - 2026-03-01

### Removed
- **prefer-modern-tools** - Hook suggested modern tools (`fd`/`rg`) as alternatives; deprecated in favor of direct tool recommendations in hook guidance
- **detect-cd-pattern** - Hook warned about global `cd` patterns; less relevant with modern absolute path tooling
- **detect-heredoc-errors** - Hook provided workarounds for heredoc temp file errors; now handled by improved sandbox documentation
- **normalize-line-endings** - Hook normalized line endings; task better suited for pre-commit hooks or editor configuration
- **gh-fallback-helper** - Hook provided fallback guidance for failed `gh` commands; consolidated into other error handlers
- **markdown-commit-reminder** - Hook warned about markdown file inclusion; now covered by improved session documentation
- **suggest-uv-for-missing-deps** - Hook suggested `uv run` for Python import errors; guidance now part of error messages
- **monitor-ci-results** - Hook reminded to check CI after push/PR; less critical with GitHub notifications

## [1.1.1] - 2026-03-01

### Fixed
- Add `CLAUDE_HOOK_STATE_DIR` env var support to markdown-commit-reminder and monitor-ci-results hooks for sandbox compatibility
- Update test files to use TMPDIR-based state directory instead of hardcoded `~/.claude/hook-state/`

## [1.1.0] - 2026-02-27

### Added
- **PermissionRequest logging**: New `PermissionRequest` hook entry routes all permission prompts through `run-with-fallback.sh` → `log-event.py`. When `JSHOES_HOOK_LOG_DIR` is set, captures `tool_name`, `tool_input`, and `permission_suggestions` to `{session_id}.jsonl`. Observer-only — no decision returned.
- **Notification logging**: New `Notification` hook entry captures all notification events (`permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog`). Same logging path as PermissionRequest. Observer-only.
- **`log-event.py`**: Minimal observer hook shared by PermissionRequest and Notification. Outputs `{}` so `run-with-fallback.sh` handles all logging.

### Changed
- **Machine-local configuration docs**: README now documents enabling `JSHOES_HOOK_LOG_DIR` via `~/.claude/settings.json` `env` field (user scope) as the recommended approach for persistent per-machine logging — no plugin changes required.

## [1.0.0] - 2026-02-27

### Changed
- Renamed from `claude-code-hooks` to `core-hooks` to better reflect that all plugins in this repository target Claude Code CLI.

## [2.0.0] - 2026-02-27

### Removed
- `prefer-gh-for-own-repos`: Hook was hardcoded to a specific GitHub owner and provided no value to other users.
- `gh-web-fallback`: Hook was designed for claude.ai/code (web) environments where `gh` CLI is unavailable. This repository now targets Claude Code CLI only.

## [1.6.1] - 2026-02-26

### Changed
- Documentation updates: README rewritten to reflect actual hook count (15), add missing hook details, and document `JSHOES_HOOK_LOG_DIR` env var

## [1.6.0] - 2026-02-24

### Added
- **Hook event logging**: opt-in sidecar JSONL logging via `JSHOES_HOOK_LOG_DIR`. When set, `run-with-fallback.sh` captures the full input and output of every hook invocation and appends a `{ts, hook, input, output}` entry to `$JSHOES_HOOK_LOG_DIR/{session_id}.jsonl`. Complements project-level observer hooks, which cannot capture individual plugin hook decisions. Logging errors are silently swallowed and never block hook execution. (Closes [#78](https://github.com/Jython1415/jshoes-claude-plugins/issues/78))

## [1.5.4] - 2026-02-22

### Changed
- Relocated test suite from `.claude/hooks/tests/` to `plugins/claude-code-hooks/tests/`

## [1.5.3] - 2026-02-21

### Changed
- `gh-authorship-attribution`: enforce attribution reminder on the first commit of each session regardless of cooldown state

## [1.5.2] - 2026-02-22

### Fixed
- `block-heredoc-in-bash`: switched from `additionalContext` to `permissionDecision: deny` so the block is actually enforced

## [1.5.1] - 2026-02-22

### Fixed
- `gh-authorship-attribution`, `prefer-gh-for-own-repos`, `gh-web-fallback`, `markdown-commit-reminder`: scoped cooldown state files to per-session-id to prevent cross-session contamination (was previously global)

## [1.5.0] - 2026-02-21

### Added
- `block-heredoc-in-bash`: new PreToolUse hook that blocks heredoc syntax (`<<EOF` and variants) in Bash commands, which silently corrupts data in Claude Code sandbox mode
