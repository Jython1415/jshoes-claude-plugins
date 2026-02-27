# stop-momentum

An opt-in Claude Code plugin that enforces execution momentum by requiring deliberate acknowledgment before Claude stops.

## What it does

This plugin registers a Stop hook that intercepts every session stop event. Instead of letting Claude stop freely, it requires an explicit acknowledgment token to confirm the stop is intentional.

### The problem

Claude can stop prematurely — finishing a sub-task and stopping instead of continuing to the next part of a larger request. This is especially common in agentic workflows where Claude interprets natural stopping points within a task as session boundaries.

### How the ack token handshake works

1. When a Stop event fires, the hook checks whether `stop_hook_active` is set (loop guard).
2. If no valid ack token is present in the last assistant message, the hook blocks the stop and provides a guidance message along with a newly generated token (e.g. `ACK-X7K2`).
3. Claude must include that exact token string in its next response to proceed.
4. On the next Stop event, the hook finds the token in the message, allows the stop, and deletes the session state file.

This ensures Claude only stops when it has explicitly confirmed the stop is deliberate.

## Installation

```bash
# Add the marketplace (if not already added)
claude plugin marketplace add Jython1415/jshoes-claude-plugins

# Install the plugin globally
claude plugin install stop-momentum@jshoes-claude-plugins --scope user

# Or install for the current project only
claude plugin install stop-momentum@jshoes-claude-plugins --scope project
```

## Customizing the guidance message

By default, the hook shows a generic message:

```
EXECUTION MOMENTUM CHECK: Before stopping, consider:
- Have you completed what the user actually asked for, or just a sub-task within a larger request?
- If you have a question, status update, or finding to share, prefer /consult over stopping — it gives the user a structured way to respond without treating this as a session boundary.
- If this is a genuine session end (user's request fully fulfilled, or an explicit checkpoint they asked for), you may stop deliberately.
```

To override this with project-specific guidance, create `.claude/momentum-guide.md` in your project root:

```markdown
STOP CHECK: Before stopping, verify:
- All acceptance criteria from the issue are met
- Tests are passing (run `npm test` or `uv run pytest`)
- The PR description accurately reflects the changes made
- No outstanding TODO comments were added without a follow-up task
```

When this file exists, its contents replace the default guidance block entirely. The ack token instruction is always appended after the guidance regardless of which source is used.

## State management

The hook stores per-session ack tokens in:

```
~/.claude/hook-state/stop-ack-{session_id}
```

These files are automatically created when a stop is blocked and deleted when a valid ack is received. You can safely delete them manually if needed.

To redirect state storage (e.g. for testing), set the `CLAUDE_HOOK_STATE_DIR` environment variable:

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
