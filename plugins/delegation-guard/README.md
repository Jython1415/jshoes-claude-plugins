# delegation-guard

A Claude Code plugin that tracks consecutive non-Task tool calls in the main session and injects an advisory reminder when the streak reaches 2, encouraging delegation to subagents.

## What it does

This plugin registers a PostToolUse hook that fires on every tool call. It parses the session transcript to count consecutive tool uses that are not the `Task` tool. When that count hits 2 or more, it injects an advisory into the context reminding Claude to orchestrate rather than implement.

This matches the "main session should orchestrate, not implement" principle: main-context capacity is limited. Granular work — reads, searches, analysis, implementation — belongs in subagents. The Task tool spawns a fresh-context subagent for that work.

### The advisory message

When the streak hits 2, Claude sees:

```
Orchestration advisory: 2 consecutive tool calls without delegating.
Main session should orchestrate, not implement — use it for quick reads,
planning, and launching agents. Delegate implementation, analysis, and
multi-step work to a subagent via the Task tool.
```

The advisory fires once when the streak reaches the threshold; it is suppressed until a Task call resets the counter.

### How it tracks state

The hook uses offset-tracked transcript parsing. On each PostToolUse call:

1. Reads the session transcript from the last recorded byte offset (new content only, up to the last complete newline)
2. Parses each new JSONL line looking for `type == "tool_use"` entries
3. Task tool calls reset the streak to 0; exempt tools are neutral (neither increment nor reset); all other tool calls increment the streak
4. Saves the updated offset, streak, Task call count, and advisory_fired flag to a per-session state file

This approach is efficient — only new transcript content is parsed on each call.

### Exempt tools

The following tools are neutral — they do not increment or reset the streak, because they are orchestration primitives, not implementation work:

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

Per-session state is stored in:

```
~/.claude/hook-state/{session_id}-delegation.json
```

The state file contains:

```json
{"offset": 12345, "streak": 2, "task_calls": 0, "advisory_fired": false}
```

| Field | Type | Description |
|---|---|---|
| `offset` | int | Byte offset into the transcript file (next read starts here) |
| `streak` | int | Count of consecutive non-Task, non-exempt tool calls |
| `task_calls` | int | Cumulative count of Task tool calls this session |
| `advisory_fired` | bool | Whether the advisory has already fired for the current unbroken streak |

To redirect state storage (e.g., for testing), set the `CLAUDE_HOOK_STATE_DIR` environment variable:

```bash
export CLAUDE_HOOK_STATE_DIR=/path/to/custom/state/dir
```

## Requirements

- Claude Code CLI
- Python 3.9+
- `uv` (for running the hook script)

## License

MIT

## Author

**Jython1415**
https://github.com/Jython1415
