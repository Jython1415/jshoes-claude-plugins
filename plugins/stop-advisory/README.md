# stop-advisory

A Claude Code plugin that provides optional advisory guidance before session stops via an ack-token handshake.

## What it does

**Event:** Stop

Intercepts session stop events and optionally enforces deliberate acknowledgment before allowing Claude to stop. If guidance is configured, the hook blocks stops and requires an ack token. If no guidance is configured, the hook is a no-op (allows all stops silently).

## How it works

1. When a Stop event fires, the hook checks whether `stop_hook_active` is set (loop guard).
2. The hook loads advisory guidance from configured sources (environment variable or file).
3. **If no guidance is configured:** hook returns silently (no-op, allows stop).
4. **If guidance is configured:**
   - If no valid ack token is present in the last assistant message, the hook blocks the stop and provides guidance along with a newly generated token (e.g. `ACK-X7K2`).
   - Claude must include that exact token string in its next response to proceed.
   - On the next Stop event, the hook finds the token in the message, allows the stop, and deletes the session state file.

## Configuring guidance

The hook supports two configuration sources in priority order:

### 1. Environment variable (highest priority)

Set `STOP_HOOK_GUIDANCE` to your advisory text directly:

```bash
export STOP_HOOK_GUIDANCE="STOP ADVISORY: Before stopping, verify:
- Have you completed what the user asked?
- If you have a finding to share, /consult instead of stopping.
- If this is a genuine end, you may stop deliberately."
```

The environment variable value is used as raw text — it is not treated as a file path.

### 2. File configuration (fallback)

Create `.claude/stop-guidance.md` in your project root:

```bash
mkdir -p .claude
cat > .claude/stop-guidance.md << 'EOF'
STOP ADVISORY: Before stopping, verify:
- Have you completed what the user asked?
- If you have a finding to share, /consult instead of stopping.
- If this is a genuine end, you may stop deliberately.
EOF
```

### 3. No guidance configured

If neither `STOP_HOOK_GUIDANCE` is set nor `.claude/stop-guidance.md` exists, the hook is disabled — all stops are allowed silently.

## Suggested guidance template

Use this as a starting point for your project:

```
STOP ADVISORY: Before stopping, consider:
- Have you completed what the user actually asked for, or just a sub-task within a larger request?
- If you have a question, status update, or finding to share, prefer /consult over stopping — it gives the user a structured way to respond without treating this as a session boundary.
- If this is a genuine session end (user's request fully fulfilled, or an explicit checkpoint they asked for), you may stop deliberately.
```

## Installation

```bash
# Add the marketplace (if not already added)
claude plugin marketplace add Jython1415/jshoes-claude-plugins

# Install the plugin globally
claude plugin install stop-advisory@jshoes-claude-plugins --scope user

# Or install for the current project only
claude plugin install stop-advisory@jshoes-claude-plugins --scope project
```

## State management

Per-session ack tokens are stored in `~/.claude/hook-state/stop-ack-{session_id}`. These files are automatically created when a stop is blocked and deleted when a valid ack is received.

To redirect state storage (e.g., for testing), set the `CLAUDE_HOOK_STATE_DIR` environment variable:

```bash
export CLAUDE_HOOK_STATE_DIR=/path/to/custom/state/dir
```

## History

This hook was originally named `stop-momentum` and included a hardcoded default guidance message. In version 2.0.0, it was renamed to `stop-advisory` and refactored to:
- Remove hardcoded guidance
- Support external configuration via environment variable and file
- Become a no-op when unconfigured (opt-in enforcement)
- Reframe as a general-purpose advisory tool rather than an opinionated momentum enforcer

## Requirements

- Claude Code CLI
- Python 3.9+
- `uv` (for running the hook scripts)

## License

MIT

## Author

**Jython1415**
https://github.com/Jython1415
