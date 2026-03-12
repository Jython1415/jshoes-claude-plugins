# Changelog

## [2.0.0] - 2026-03-12

### Changed
- **BREAKING**: Renamed plugin from `stop-momentum` to `stop-advisory`
- **BREAKING**: Renamed hook script from `stop-momentum.py` to `stop-advisory.py`
- **BREAKING**: Config file renamed from `.claude/momentum-guide.md` to `.claude/stop-guidance.md`
- Removed hardcoded default guidance — hook is now a no-op when unconfigured
- Added `STOP_HOOK_GUIDANCE` environment variable as alternative configuration source (takes priority over file)
- Reframed as general-purpose stop interceptor with optional advisory guidance rather than opinionated momentum enforcer

## [1.0.0] - 2026-03-01

### Added
- Initial standalone release (split from `orchestration-discipline` v1.2.1)
- Stop hook with ack-token handshake for deliberate session stops
- Custom guidance support via `.claude/momentum-guide.md`
- Per-session state storage with CLAUDE_HOOK_STATE_DIR override support
