# haiku-enforce

A Claude Code plugin that enforces the Haiku model for all subagent launches.

## What it does

**Event:** PreToolUse (Agent tool only)

Intercepts every Agent tool call and overrides the `model` parameter to `"haiku"` using `updatedInput`. This ensures all subagents run on the most cost-effective model. Install the plugin to enable the constraint; uninstall it to remove it.

## How it works

| Tool call | Action |
|-----------|--------|
| Agent | Override `model` to `"haiku"` via `updatedInput`, auto-allow via `permissionDecision: "allow"` |
| Any other tool | Silent pass-through (matcher prevents hook from firing) |

Claude is informed of the override via `additionalContext`, so it knows the subagent will run on Haiku.

## Installation

```bash
# Add the marketplace (if not already added)
claude plugin marketplace add Jython1415/jshoes-claude-plugins

# Install the plugin globally
claude plugin install haiku-enforce@jshoes-claude-plugins --scope user

# Or install for the current project only
claude plugin install haiku-enforce@jshoes-claude-plugins --scope project
```

## Uninstallation

To remove the Haiku constraint and allow full model flexibility:

```bash
claude plugin uninstall haiku-enforce@jshoes-claude-plugins
```

## Requirements

- Claude Code CLI v2.0.10+ (for `updatedInput` support)
- Python 3.9+
- `uv` (for running the hook script)

## License

MIT

## Author

**Jython1415**
https://github.com/Jython1415
