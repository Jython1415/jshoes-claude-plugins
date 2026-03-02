# plugin-support Plugin

Comprehensive guide to authoring, testing, and maintaining Claude Code hooks.

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

Or read directly: `plugins/plugin-support/skills/hook-development/SKILL.md`

## Installation

### From GitHub Marketplace

```bash
# Add marketplace
claude plugin marketplace add Jython1415/jshoes-claude-plugins

# Install plugin globally
claude plugin install plugin-support@jshoes-claude-plugins
```

## Requirements

- Claude Code CLI

## Author

**Jython1415**
https://github.com/Jython1415

## Repository

https://github.com/Jython1415/jshoes-claude-plugins
