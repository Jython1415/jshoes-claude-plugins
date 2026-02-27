---
name: feedback
description: |
  ONLY for filing issues and suggestions against jshoes-claude-plugins
  (https://github.com/Jython1415/jshoes-claude-plugins). Do NOT use for
  filing issues in any other repository. Use when a consumer of the
  jshoes-claude-plugins hooks or skills wants to report a bug, request a
  feature, or suggest an optimization back to this plugin ecosystem.
argument-hint: "<description>"
---

# /feedback — Report an issue to jshoes-claude-plugins

Turn a description into a well-structured GitHub issue filed against
[`Jython1415/jshoes-claude-plugins`](https://github.com/Jython1415/jshoes-claude-plugins).

## Issue types

| Type | When to use |
|------|-------------|
| **Bug** | A hook fires incorrectly, a skill gives wrong guidance, or something breaks unexpectedly |
| **Feature request** | A new hook, skill, or capability you'd find valuable |
| **Optimization** | An existing hook or skill that could be smarter, faster, or more useful |

## Phases

### 1. Classify and gather context

Determine from the user's description (ask if unclear):
- **Type**: Bug / Feature request / Optimization
- **Component**: Which plugin and which specific hook or skill
  - Plugin names: `claude-code-hooks`, `dev-workflow`, `claude-code-misc`
  - Hook filename (e.g., `detect-cd-pattern.py`) or skill name (e.g., `/solve`)
- **Plugin version**: Auto-discover before asking the user.
  1. Read `~/.claude/plugins/installed_plugins.json`
  2. Find the key `<plugin-name>@jshoes-claude-plugins` (e.g., `"claude-code-hooks@jshoes-claude-plugins"`)
  3. If multiple entries exist for that key, prefer the one whose `projectPath` matches the
     current working directory; if none match, prefer `scope: "user"`
  4. Extract the `version` field from the matching entry
  5. If the file is missing, the plugin key is not found, or no entry matches the selection
     criteria above, ask the user to provide the version
- **Claude Code version**: Ask the user to run `claude --version` if not provided

Then gather type-specific details:

**Bug:**
- What happened (actual behavior)
- What was expected
- Steps to reproduce — include the exact tool used (Bash command, file write, etc.)
- Any hook output or error messages visible in the conversation, or from `~/.claude/debug/latest`

**Feature request:**
- The problem or workflow gap it addresses
- What the ideal behavior would look like
- Which plugin area it belongs to (hook type, skill area, etc.)
- Any workarounds currently in use

**Optimization:**
- Current behavior and what specifically could be better
- A real example that prompted the idea
- The expected improvement (fewer false positives, better guidance text, etc.)

### 2. Check for duplicates

Search before filing:

    gh issue list -R Jython1415/jshoes-claude-plugins -S "<keyword>" --state all

If a duplicate exists, report the URL and stop — don't file. If a related issue
exists, note it for cross-referencing in the body.

### 3. Draft and file

**Bug template:**

```
## Problem
<What went wrong — 1-2 sentences>

## Environment
- Plugin: <plugin name and version, e.g. "claude-code-hooks 1.5.4">
- Hook/skill: <hook filename or /skill-name>
- Claude Code version: <output of `claude --version`>

## Steps to reproduce
1. <first step>
2. <what triggered the behavior>

## Expected behavior
<what should have happened>

## Actual behavior
<what actually happened>

## Additional context
<Hook output, error messages, or debug log excerpts — omit if nothing relevant>
```

**Feature request template:**

```
## Use case
<The problem or workflow gap this would address — 1-3 sentences>

## Proposed behavior
<What the hook or skill should do>

## Plugin / component
<Where this would live: plugin name, hook lifecycle event, or skill name>

## Additional context
<Workarounds currently used, related issues, prior art — omit if nothing relevant>
```

**Optimization template:**

```
## Current behavior
<What happens today>

## Desired improvement
<What could be better and why>

## Real-world example
<The specific situation that prompted this idea>

## Component
<Plugin name and specific hook or skill>
```

**Filing rules:**
- Repo: `Jython1415/jshoes-claude-plugins`
- Write the issue body to a temp file in the current project directory, then use
  `gh issue create -R Jython1415/jshoes-claude-plugins --title "..." --body-file <tmpfile>`
- Title format: `<Component>: <short description>` (e.g., `detect-cd-pattern: false positive on subshell cd`)
- Add a footer as the last two lines of the body:
  ```
  ---
  *Filed with /feedback — jshoes-claude-plugins*
  ```
- Show the issue URL after filing

## Guidelines

- **Gather before drafting**: Don't write the issue until you have all the type-specific
  details. Missing reproduction steps or version numbers make reports much harder to act on.
- **Don't pad**: Omit sections that don't add context. A short, complete issue is better
  than a long one with filler.
- **Check duplicates first**: Always search before filing.
- **One issue per problem**: If the user describes multiple distinct problems, file them
  separately and cross-link if related.
