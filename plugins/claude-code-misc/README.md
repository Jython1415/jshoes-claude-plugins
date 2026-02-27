# Claude Code Misc Plugin

Miscellaneous skills for Claude Code development and plugin consumer support.

## Skills

### /hook-development

A comprehensive guide to authoring, testing, and maintaining Claude Code hooks. Use when writing a new hook, debugging an existing hook, or learning the hook lifecycle.

Covers:
- Hook event types and JSON input/output formats
- PreToolUse blocking patterns (`permissionDecision: deny`)
- PostToolUseFailure guidance patterns (`additionalContext`)
- Cooldown and state management using session-scoped files
- Shell wrapper patterns with `run-with-fallback.sh`
- Testing approach and sandbox-safe test state directory setup

Invoke with:
```
/hook-development
```

Or read directly: `plugins/claude-code-misc/skills/hook-development/SKILL.md`

### /feedback

ONLY for plugin consumers to report issues with the `jshoes-claude-plugins` plugins. Files a structured GitHub issue in the `Jython1415/jshoes-claude-plugins` repository on behalf of the user.

Use when a user reports a bug, unexpected behavior, or missing feature in a hook or skill from this plugin set.

Invoke with:
```
/feedback
```

## Installation

### From GitHub Marketplace

```bash
# Add marketplace
claude plugin marketplace add Jython1415/jshoes-claude-plugins

# Install plugin globally
claude plugin install claude-code-misc@jshoes-claude-plugins
```

## Requirements

- Claude Code CLI

## Author

**Jython1415**
https://github.com/Jython1415

## Repository

https://github.com/Jython1415/jshoes-claude-plugins
