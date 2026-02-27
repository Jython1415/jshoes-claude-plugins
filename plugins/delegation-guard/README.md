# delegation-guard

A Claude Code plugin that tracks consecutive non-Task tool calls in the main session and injects an advisory reminder when the streak reaches 3, encouraging delegation to subagents.

## What it does

This plugin registers a PostToolUse hook that fires on every tool call. It parses the session transcript to count consecutive tool uses that are not the `Task` tool. When that count hits 3 or more, it injects an advisory into the context reminding Claude to consider delegating work to a subagent.

This matches the "3 consecutive non-spawn tool calls = delegate" rule: main-context capacity is limited. Granular work — reads, searches, analysis, implementation — belongs in subagents. The Task tool spawns a fresh-context subagent for that work.

### The advisory message

When the streak hits 3, Claude sees:

```
Delegation check: 3 consecutive tool calls without using Task.
Consider whether this work should be delegated to a subagent to preserve
main context. Use the Task tool to spawn a subagent for implementation,
research, or multi-step analysis work.
```

The streak count in the message updates as consecutive calls continue (e.g., "4 consecutive tool calls").

### How it tracks state

The hook uses offset-tracked transcript parsing. On each PostToolUse call:

1. Reads the session transcript from the last recorded byte offset (new content only)
2. Parses each new JSONL line looking for `type == "tool_use"` entries
3. Task tool calls reset the streak to 0; all other tool calls increment it
4. Saves the updated offset, streak, and Task call count to a per-session state file

This approach is efficient — only new transcript content is parsed on each call.

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
{"offset": 12345, "streak": 2, "task_calls": 0}
```

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
