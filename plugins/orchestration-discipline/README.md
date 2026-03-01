# orchestration-discipline

A Claude Code plugin that enforces execution discipline in main-session workflows. Contains two complementary hooks: `stop-momentum` prevents premature session stops, and `delegation-guard` encourages subagent delegation.

## Hooks

### stop-momentum

**Event:** Stop

Intercepts every session stop event and requires deliberate acknowledgment before allowing Claude to stop. This prevents Claude from stopping at sub-task boundaries within a larger request.

#### How it works

1. When a Stop event fires, the hook checks whether `stop_hook_active` is set (loop guard).
2. If no valid ack token is present in the last assistant message, the hook blocks the stop and provides guidance along with a newly generated token (e.g. `ACK-X7K2`).
3. Claude must include that exact token string in its next response to proceed.
4. On the next Stop event, the hook finds the token in the message, allows the stop, and deletes the session state file.

#### Custom guidance

By default, the hook shows a generic momentum check message. To override with project-specific guidance, create `.claude/momentum-guide.md` in your project root. When this file exists, its contents replace the default guidance block entirely. The ack token instruction is always appended after the guidance.

#### State management

Per-session ack tokens are stored in `~/.claude/hook-state/stop-ack-{session_id}`. These files are automatically created when a stop is blocked and deleted when a valid ack is received.

To redirect state storage (e.g. for testing), set the `CLAUDE_HOOK_STATE_DIR` environment variable:

```bash
export CLAUDE_HOOK_STATE_DIR=/path/to/custom/state/dir
```

---

### delegation-guard

**Event:** PreToolUse (all tools), SubagentStart, SubagentStop

Intercepts every tool call before it runs. Blocks the first solo tool call after delegation, then fires escalating advisory messages as the streak grows.

#### How it works

| Streak | Action |
|--------|--------|
| 0 (block not yet fired) | **Block** — hard stop via `permissionDecision: "deny"`. The blocked call does not count toward the streak. |
| 1 | Silent — first executed call after the block |
| 2 | Advisory — mild reminder |
| 4 | Advisory — stronger |
| 8 | Advisory — urgent |
| 16 | Advisory — critical |
| Task call | Reset — streak returns to 0 and the block re-arms |

Streaks at non-power-of-2 values (3, 5, 6, 7, 9, …) pass through silently.

The block fires once per unbroken solo run. After it fires, subsequent tool calls increment the streak and receive advisory messages — but are not blocked. A Task call resets the streak to 0 and re-arms the block so the cycle can start again.

#### Exempt tools (neutral — neither increment nor reset)

| Tool | Rationale |
|---|---|
| `Skill` | Invokes skills/subcommands — orchestration |
| `AskUserQuestion` | Clarification request — not task work |
| `TaskCreate` | Task list management — orchestration |
| `TaskUpdate` | Task list management — orchestration |
| `TaskGet` | Task list management — orchestration |
| `TaskList` | Task list management — orchestration |
| `EnterPlanMode` | Planning mode transition — orchestration |
| `ExitPlanMode` | Planning mode transition — orchestration |

#### Subagent detection

**Subagent detection via SubagentStart/Stop counter**: The hook registers for `SubagentStart` and `SubagentStop` events. When a subagent starts, `subagent_count` increments; when it stops, it decrements (floor 0). While `subagent_count > 0`, all `PreToolUse` calls pass through silently — subagents receive no blocks or advisory messages. The hard block re-arms when the count returns to 0 (the Agent/Task call that spawned the subagent already reset `streak=0, block_fired=False`).

**Known trade-off**: While any subagent is active, the main session's guard is also suppressed. Semantically, this is acceptable — the session IS delegating during that window.

#### State management

Per-session state is stored in `~/.claude/hook-state/{session_id}-delegation.json`:

```json
{"streak": 2, "block_fired": true, "subagent_count": 0}
```

To redirect state storage (e.g., for testing), set the `CLAUDE_HOOK_STATE_DIR` environment variable:

```bash
export CLAUDE_HOOK_STATE_DIR=/path/to/custom/state/dir
```

---

## Installation

```bash
# Add the marketplace (if not already added)
claude plugin marketplace add Jython1415/jshoes-claude-plugins

# Install the plugin globally
claude plugin install orchestration-discipline@jshoes-claude-plugins --scope user

# Or install for the current project only
claude plugin install orchestration-discipline@jshoes-claude-plugins --scope project
```

## Requirements

- Claude Code CLI
- Python 3.9+
- `uv` (for running the hook scripts)

## License

MIT

## Author

**Jython1415**
https://github.com/Jython1415
