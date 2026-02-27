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

**Event:** PostToolUse (all tools)

Tracks consecutive non-Task tool calls in the main session and injects an advisory reminder when the streak reaches 2, encouraging delegation to subagents via the `Task` tool.

#### How it works

On each PostToolUse call, the hook uses offset-tracked transcript parsing to read only new content since the last call. It counts `tool_use` entries: Task calls reset the streak to 0; exempt tools are neutral; all other tool calls increment the streak. When the streak hits 2, a one-time advisory fires.

The advisory message:

```
Orchestration advisory: 2 consecutive tool calls without delegating.
Main session context is for synthesis and coordination only — reads, research,
planning, and implementation all belong in subagents. Use the Task tool to
delegate, then synthesize what comes back.
```

The advisory fires once per unbroken non-delegation run; it resets when a Task call occurs.

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

#### State management

Per-session state is stored in `~/.claude/hook-state/{session_id}-delegation.json`:

```json
{"offset": 12345, "streak": 2, "task_calls": 0, "advisory_fired": false}
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
