# Changelog

## [1.1.1] - 2026-02-28

### Fixed
- `delegation-guard`: Add `"Agent"` alongside `"Task"` as a delegation-reset trigger. The Agent tool was renamed from Task in Claude Code v2.1.63; the hook was checking only for `"Task"`, so Agent calls incremented the streak instead of resetting it.
- `delegation-guard`: Skip hook entirely when `transcript_path` contains `"/subagents/"`. Subagents share the parent's `session_id` and state file; without this guard, subagents received confusing "delegate to a subagent" messages. The heuristic uses the fact that subagent transcripts live at `.../subagents/agent-{id}.jsonl`.

## [1.1.0] - 2026-02-28

### Changed
- `delegation-guard` rewritten as a **PreToolUse** hook (was PostToolUse). This enables
  blocking tool calls, not just advising after the fact.
- New behavior: first solo tool call (streak=0, block not yet fired) is **blocked** via
  `permissionDecision: "deny"`. The blocked call does not increment the streak — only
  executed calls count.
- After the block fires, escalating advisory messages fire at streak 2, 4, 8, 16 (powers
  of 2 ≥ 2) with increasingly urgent language. Intermediate streaks (1, 3, 5, 6, 7, ...)
  pass through silently.
- A Task call resets streak to 0 and re-arms the block, so the cycle restarts on the next
  solo call.
- State schema simplified: `{streak, block_fired}` — removed `offset`, `task_calls`, and
  `advisory_fired` (no longer needed without transcript parsing).

## [1.0.2] - 2026-02-28

### Fixed
- `delegation-guard` `compute_streak`: transcript parsing now correctly unwraps `type: "assistant"` entries and iterates `message.content[]` to find tool calls. Previously checked for top-level `type: "tool_use"` which never exists in Claude Code transcripts — the streak was always 0 and the advisory never fired.

## [1.0.1] - 2026-02-27

### Fixed
- `delegation-guard` PostToolUse hook: added missing `"matcher": ".*"` field. Without a matcher, the hook was registered in the registry but never triggered for any tool call.

## [1.0.0] - 2026-02-27

### Added
- `stop-momentum`: Prevents premature session stops via ack-token handshake. (Previously a standalone plugin.)
- `delegation-guard`: Fires advisory when consecutive non-Task tool calls exceed threshold. (Previously a standalone plugin.)
