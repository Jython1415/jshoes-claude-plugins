# Changelog

## [1.0.0] - 2026-02-27

### Added
- Initial release with opt-in Stop hook implementing execution momentum enforcement via ack token handshake
- Generic default guidance message encouraging deliberate stops and /consult usage
- Project-configurable guidance via `.claude/momentum-guide.md` in project root
- Per-session ack token stored in `~/.claude/hook-state/` (supports `CLAUDE_HOOK_STATE_DIR` override)
- Loop prevention via `stop_hook_active` field check
