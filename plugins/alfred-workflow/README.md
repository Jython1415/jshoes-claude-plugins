# Alfred Workflow Plugin

A reference skill for designing, creating, and modifying Alfred 5 workflows programmatically from the command line.

## Skills

### /alfred-workflow

Complete reference for building Alfred 5 workflows by writing `info.plist` files directly. Use when creating a new workflow, adding nodes to an existing workflow, debugging workflow behavior, or automating Alfred configuration.

Covers:
- Workflow directory structure and file layout
- Complete `info.plist` top-level schema
- All node types: input triggers, actions, outputs, utilities, and automation nodes
- Node version numbers (schema versions per node type)
- Data flow between nodes (`{query}` propagation)
- Connection wiring: fan-out, modifier branching, conditional routing
- Canvas layout (`uidata` positioning)
- User configuration variables
- Script types and the escaping bitmask
- Full worked example (keyword → script → clipboard)
- Validation checklist and common pitfalls

This skill was reverse-engineered from real workflows and is updated as new patterns are discovered. When you encounter undocumented behavior or incorrect schema details, update the skill file.

## Installation

### From GitHub Marketplace

```bash
# Add marketplace
claude plugin marketplace add Jython1415/jshoes-claude-plugins

# Install plugin globally
claude plugin install alfred-workflow@jshoes-claude-plugins
```

## Requirements

- Claude Code CLI
- Alfred 5 (macOS)

## Author

**Jython1415**
https://github.com/Jython1415

## Repository

https://github.com/Jython1415/jshoes-claude-plugins
