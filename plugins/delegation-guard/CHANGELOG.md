# Changelog

## [1.0.0] - 2026-03-01

### Added
- Initial standalone release (split from `orchestration-discipline` v1.2.1)
- PreToolUse hook with one-time hard block and escalating advisory reminders
- SubagentStart/SubagentStop reference counter for subagent detection
- Exempt tool list: Skill, AskUserQuestion, TaskCreate/Update/Get/List, EnterPlanMode, ExitPlanMode
- Per-session state storage with CLAUDE_HOOK_STATE_DIR override support
- Documentation of SubagentStop crash limitation and session lifecycle behavior
