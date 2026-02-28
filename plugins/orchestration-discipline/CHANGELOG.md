# Changelog

## [1.0.1] - 2026-02-27

### Fixed
- `delegation-guard` PostToolUse hook: added missing `"matcher": ".*"` field. Without a matcher, the hook was registered in the registry but never triggered for any tool call.

## [1.0.0] - 2026-02-27

### Added
- `stop-momentum`: Prevents premature session stops via ack-token handshake. (Previously a standalone plugin.)
- `delegation-guard`: Fires advisory when consecutive non-Task tool calls exceed threshold. (Previously a standalone plugin.)
