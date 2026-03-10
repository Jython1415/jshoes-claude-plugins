# Changelog

## [1.3.1] - 2026-03-09

### Fixed

- Exempt `ToolSearch` from streak counting — it's a prerequisite tool that loads deferred tools and cannot be delegated (#215)

## [1.3.0] - 2026-03-08

### Changed
- Strengthened block and advisory message language to be more directive while acknowledging legitimate solo work
- Added periodic re-blocking at Fibonacci streak thresholds (5, 8, 13, ...) for normal tools; unblocked tools remain advisory-only

## [1.2.0] - 2026-03-08

### Added
- `unblocked_tools` category — tools that are never hard-blocked but still count toward the advisory streak
- Default unblocked tools: Read, Glob, Grep (essential for code understanding)
- Unblocked tools fire an advisory at streak=0 instead of being hard-blocked, then increment to streak=1
- Per-project configuration for `unblocked_tools` via `.claude/delegation-guard.json` (merged with defaults, same pattern as `exempt_tools`)

## [1.1.0] - 2026-03-01

### Added
- Per-project configuration via `.claude/delegation-guard.json`
- `exempt_tools` config field to add project-specific tool exemptions (merged with defaults)

## [1.0.0] - 2026-03-01

### Added
- Initial standalone release (split from `orchestration-discipline` v1.2.1)
- PreToolUse hook with one-time hard block and escalating advisory reminders
- SubagentStart/SubagentStop reference counter for subagent detection
- Exempt tool list: Skill, AskUserQuestion, TaskCreate/Update/Get/List, EnterPlanMode, ExitPlanMode
- Per-session state storage with CLAUDE_HOOK_STATE_DIR override support
- Documentation of SubagentStop crash limitation and session lifecycle behavior
