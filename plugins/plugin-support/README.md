# plugin-support Plugin

Reference documentation and development guides for Claude Code.

## Skills

### /claude-code-reference

Authoritative reference for Claude Code settings.json schema, CLI flags, permission system, and hook configuration. Use when editing settings.json, writing permission rules, configuring hooks, or generating CLI commands.

Covers:
- All `settings.json` fields with types and descriptions
- Configuration scopes and precedence rules
- CLI commands and flags
- Permission rule syntax (Bash, Read/Edit, WebFetch, MCP, Agent patterns)
- Permission modes and evaluation order
- Hook events, configuration schema, input/output formats, and exit codes

Sourced from official documentation at code.claude.com (March 2026).

Invoke with:
```
/claude-code-reference
```

Or read directly: `plugins/plugin-support/skills/claude-code-reference/SKILL.md`

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
