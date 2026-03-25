# Changelog

## [1.0.1] - 2026-03-25

### Fixed
- `updatedInput` now preserves all original tool input fields alongside the model override. Previously only `{"model": "haiku"}` was returned, stripping prompt, description, and other fields, which crashed the Agent tool.

## [1.0.0] - 2026-03-05

### Added
- Initial release
- PreToolUse hook that enforces Haiku model on all Agent tool calls via `updatedInput`
- Auto-allow with `permissionDecision: "allow"` to avoid permission prompts
- `additionalContext` to inform Claude of the model override
