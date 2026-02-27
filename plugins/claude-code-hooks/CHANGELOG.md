# Changelog

## [1.6.1] - 2026-02-26

### Changed
- Documentation updates: README rewritten to reflect actual hook count (15), add missing hook details, and document `JSHOES_HOOK_LOG_DIR` env var

## [1.6.0] - 2026-02-24

### Added
- **Hook event logging**: opt-in sidecar JSONL logging via `JSHOES_HOOK_LOG_DIR`. When set, `run-with-fallback.sh` captures the full input and output of every hook invocation and appends a `{ts, hook, input, output}` entry to `$JSHOES_HOOK_LOG_DIR/{session_id}.jsonl`. Complements project-level observer hooks, which cannot capture individual plugin hook decisions. Logging errors are silently swallowed and never block hook execution. (Closes [#78](https://github.com/Jython1415/jshoes-claude-plugins/issues/78))

## [1.5.4] - 2026-02-26

### Changed
- Relocated test suite from `.claude/hooks/tests/` to `plugins/claude-code-hooks/tests/`

## [1.5.3] - 2026-02-26

### Changed
- `gh-authorship-attribution`: enforce attribution reminder on the first commit of each session regardless of cooldown state

## [1.5.2] - 2026-02-26

### Fixed
- `block-heredoc-in-bash`: switched from `additionalContext` to `permissionDecision: deny` so the block is actually enforced

## [1.5.1] - 2026-02-26

### Fixed
- `gh-authorship-attribution`, `prefer-gh-for-own-repos`, `gh-web-fallback`, `markdown-commit-reminder`: scoped cooldown state files to per-session-id to prevent cross-session contamination (was previously global)

## [1.5.0] - 2026-02-26

### Added
- `block-heredoc-in-bash`: new PreToolUse hook that blocks heredoc syntax (`<<EOF` and variants) in Bash commands, which silently corrupts data in Claude Code sandbox mode
