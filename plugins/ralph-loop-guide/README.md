# Ralph Loop Guide Plugin

A reference skill covering best practices for writing effective prompts for autonomous coding loops (ralph loops).

## Skills

### /ralph-loop-guide

Best practices reference for structuring `PROMPT.md` files and configuring ralph loops. Use when helping users write a new loop prompt, configure completion criteria, design quality gates, or debug convergence issues.

Covers:
- What a ralph loop is and how it works
- Anatomy of an effective prompt (required and recommended elements)
- Completion signals: `<promise>` tag convention, alternatives, max iteration limits
- State management: which files to use, append-only progress logs, keeping plans disposable
- Backpressure and quality gates: upstream steering and downstream automated checks
- Subagent strategy within loops
- Language that affects agent behavior (specific phrasing recommendations)
- Prompt templates: minimal, standard development, two-prompt (plan/build), and TDD
- Common pitfalls and fixes (context degradation, rebuild loops, non-convergence, plan rot)
- Prompt tuning process
- Ecosystem reference: tools, orchestrators, and community resources

This skill is tooling-agnostic — principles apply regardless of which ralph-loop implementation is in use.

## Installation

### From GitHub Marketplace

```bash
# Add marketplace
claude plugin marketplace add Jython1415/jshoes-claude-plugins

# Install plugin globally
claude plugin install ralph-loop-guide@jshoes-claude-plugins
```

## Requirements

- Claude Code CLI

## Author

**Jython1415**
https://github.com/Jython1415

## Repository

https://github.com/Jython1415/jshoes-claude-plugins
