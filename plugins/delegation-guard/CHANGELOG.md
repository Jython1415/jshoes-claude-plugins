# Changelog

## [1.0.0] - 2026-02-27

### Added
- Initial release: PostToolUse hook with offset-tracked transcript parsing
- Injects delegation advisory when consecutive non-Task streak reaches 2
- Session-scoped state files with `CLAUDE_HOOK_STATE_DIR` override for testing
- Extended `EXEMPT_TOOLS` to include orchestration primitives: `AskUserQuestion`, `TaskCreate`, `TaskUpdate`, `TaskGet`, `TaskList`, `EnterPlanMode`, `ExitPlanMode`

### Changed
- Rewrote advisory message to reflect orchestration-not-implementation philosophy
- Fixed partial-line-at-EOF offset issue in `parse_new_transcript_lines`: offset now advances only to the last complete newline, preventing partial lines from being permanently lost
- Fixed documentation drift: threshold is 2 (docs incorrectly said 3), added `advisory_fired` to state schema, corrected fire-once behavior description
