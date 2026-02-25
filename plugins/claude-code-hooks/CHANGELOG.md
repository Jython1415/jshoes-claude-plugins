# Changelog

## [1.6.0] - 2026-02-24

### Added
- **Hook event logging**: opt-in sidecar JSONL logging via `JSHOES_HOOK_LOG_DIR`. When set, `run-with-fallback.sh` captures the full input and output of every hook invocation and appends a `{ts, hook, input, output}` entry to `$JSHOES_HOOK_LOG_DIR/{session_id}.jsonl`. Complements project-level observer hooks, which cannot capture individual plugin hook decisions. Logging errors are silently swallowed and never block hook execution. (Closes [#78](https://github.com/Jython1415/jshoes-claude-plugins/issues/78))
