# stop-momentum

A Claude Code plugin that prevents premature session stops via an ack-token handshake.

## What it does

**Event:** Stop

Intercepts every session stop event and requires deliberate acknowledgment before allowing Claude to stop. This prevents Claude from stopping at sub-task boundaries within a larger request.

## How it works

1. When a Stop event fires, the hook checks whether `stop_hook_active` is set (loop guard).
2. If no valid ack token is present in the last assistant message, the hook blocks the stop and provides guidance along with a newly generated token (e.g. `ACK-X7K2`).
3. Claude must include that exact token string in its next response to proceed.
4. On the next Stop event, the hook finds the token in the message, allows the stop, and deletes the session state file.

## Custom guidance

By default, the hook shows a generic momentum check message. To override with project-specific guidance, create `.claude/momentum-guide.md` in your project root. When this file exists, its contents replace the default guidance block entirely. The ack token instruction is always appended after the guidance.

## Installation

```bash
# Add the marketplace (if not already added)
claude plugin marketplace add Jython1415/jshoes-claude-plugins

# Install the plugin globally
claude plugin install stop-momentum@jshoes-claude-plugins --scope user

# Or install for the current project only
claude plugin install stop-momentum@jshoes-claude-plugins --scope project
```

## State management

Per-session ack tokens are stored in `~/.claude/hook-state/stop-ack-{session_id}`. These files are automatically created when a stop is blocked and deleted when a valid ack is received.

To redirect state storage (e.g., for testing), set the `CLAUDE_HOOK_STATE_DIR` environment variable:

```bash
export CLAUDE_HOOK_STATE_DIR=/path/to/custom/state/dir
```

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
