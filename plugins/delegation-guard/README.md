# delegation-guard

A Claude Code plugin that encourages delegation to subagents via escalating advisory messages and a one-time hard block.

## What it does

**Event:** PreToolUse (all tools), SubagentStart, SubagentStop

Intercepts every tool call before it runs. Blocks the first solo tool call after delegation, then fires escalating advisory messages as the streak grows. Subagents are automatically exempted — while any subagent is active, the main session's guard is suppressed.

## How it works

| Streak | Action |
|--------|--------|
| 0 (block not yet fired) | **Block** — hard stop via `permissionDecision: "deny"`. The blocked call does not count toward the streak. |
| 1 | Silent — first executed call after the block |
| 2 | Advisory — mild reminder |
| 4 | Advisory — stronger |
| 8 | Advisory — urgent |
| 16 | Advisory — critical |
| Task/Agent call | Reset — streak returns to 0 and the block re-arms |

Streaks at non-power-of-2 values (3, 5, 6, 7, 9, …) pass through silently.

The block fires once per unbroken solo run. After it fires, subsequent tool calls increment the streak and receive advisory messages — but are not blocked. A Task or Agent call resets the streak to 0 and re-arms the block so the cycle can start again.

## Exempt tools

These tools neither increment nor reset the streak:

- `Skill` — invokes skills/subcommands (orchestration)
- `AskUserQuestion` — clarification request (not task work)
- `TaskCreate`, `TaskUpdate`, `TaskGet`, `TaskList` — task list management
- `EnterPlanMode`, `ExitPlanMode` — planning mode transitions

### Per-project configuration

You can extend the exempt tools list on a per-project basis by creating a `.claude/delegation-guard.json` config file:

```json
{
  "exempt_tools": ["ToolName1", "ToolName2"]
}
```

Project-specific exemptions are **merged** with the defaults (not a replacement). Example:

```json
{
  "exempt_tools": ["mcp__assistant__send_message", "mcp__custom__tool"]
}
```

This allows you to exempt project-specific tools (e.g., MCP integrations) without overriding the built-in exempt tools.

## Subagent detection

The hook registers for `SubagentStart` and `SubagentStop` events. When a subagent starts, a reference counter (`subagent_count`) increments; when it stops, it decrements (floor 0). While `subagent_count > 0`, all `PreToolUse` calls pass through silently — subagents receive no blocks or advisory messages. The hard block re-arms when the count returns to 0 (the Agent call that spawned the subagent already reset `streak=0`).

**Known trade-off:** While any subagent is active, the main session's guard is also suppressed. This is semantically acceptable — the session IS delegating during that window.

**Known limitation:** SubagentStop is not guaranteed to fire if a subagent process crashes (e.g., OOM, signal). If that happens, `subagent_count` remains elevated for the rest of the session and the guard is permanently suppressed. No recovery mechanism is implemented.

## Installation

```bash
# Add the marketplace (if not already added)
claude plugin marketplace add Jython1415/jshoes-claude-plugins

# Install the plugin globally
claude plugin install delegation-guard@jshoes-claude-plugins --scope user

# Or install for the current project only
claude plugin install delegation-guard@jshoes-claude-plugins --scope project
```

## State management

Per-session state is stored in `~/.claude/hook-state/{session_id}-delegation.json`:

```json
{"streak": 2, "block_fired": true, "subagent_count": 0}
```

To redirect state storage (e.g., for testing), set the `CLAUDE_HOOK_STATE_DIR` environment variable:

```bash
export CLAUDE_HOOK_STATE_DIR=/path/to/custom/state/dir
```

**Session lifecycle:**
- `/clear` generates a new `session_id` — state resets automatically (the old file is orphaned but harmless).
- `/compact` preserves `session_id` — state persists correctly through compaction.

## History

This hook was split from the `orchestration-discipline` plugin (v1.2.1) into a standalone plugin to simplify configuration and enable independent evolution.

## Requirements

- Claude Code CLI
- Python 3.9+
- `uv` (for running the hook scripts)

## License

MIT

## Author

**Jython1415**
https://github.com/Jython1415
