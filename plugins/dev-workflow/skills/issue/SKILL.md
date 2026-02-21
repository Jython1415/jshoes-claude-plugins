---
name: issue
description: |
  File a well-researched GitHub issue from a brief description.
  Use when asked to file an issue, create an issue, open an issue,
  or report a bug or feature request in a GitHub repo. Explores
  the codebase, checks for duplicates, and drafts a structured
  issue. Asks the user to clarify only when the description is
  genuinely ambiguous.
argument-hint: <description>
---

# /issue — File a GitHub issue

Turn a brief description into a well-structured, context-rich GitHub issue.

## Phases

### 1. Parse

Extract from the user's description:
- **Area**: Which part of the codebase or system is affected
- **Type**: bug, enhancement, investigation, or chore
- **Signals**: Any specific symptoms, file names, or behaviors mentioned

If the user provides multiple distinct issues in one message (e.g., bullet
points or clearly separable concerns), process each one separately through
all phases. Research can run in parallel. File all issues at the end.

### 2. Research

Delegate to a Task subagent (`subagent_type=Explore`, model=sonnet):
- Explore the relevant code area to understand current behavior
- Check for duplicate or closely related open issues (`gh issue list -S "keyword"`)
- Identify related issues that should be cross-referenced
- Note relevant architecture, conventions, or prior decisions

If a duplicate exists, stop and tell the user — don't file.
If closely related issues exist, note them for cross-referencing in the issue body.

### 3. Scope (conditional)

**Skip this phase** if the description is clear enough to file directly — most issues are.

Use `AskUserQuestion` ONLY when:
- The description is genuinely ambiguous (multiple valid interpretations)
- There's a meaningful framing choice (e.g., "is this a bug in X or a missing feature in Y?")
- The research surfaced context that changes what should be filed

Offer 2-3 options, lead with a recommendation.

### 4. Draft and file

Write the issue with this structure:

```
## Problem / Background
What's wrong or what's needed. 1-3 sentences.

## Current state
What exists today — informed by the research. Code paths, behaviors, constraints.
Only include if it adds meaningful context beyond the problem statement.

## What we'd want (for enhancements)
— OR —
## Investigation needed (for bugs/unknowns)
Concrete description of the desired outcome or the questions to answer.

## Related
- #N — brief description (only if genuinely related)
```

**Title**: Short, specific. Prefix with area when helpful (e.g., "Dashboard: ...", "API: ...").

**Filing rules:**
- Use `gh issue create --title "..." --body "..."`
- For multi-line bodies, write to a temp file and use `--body-file`
- Add footer: `---\n*Created with assistance from Claude Code*`
- No labels unless the user specifies them or the repo uses them consistently
- Show the issue URL after filing

## Guidelines

- **Research before writing**: The value of this skill is context from codebase exploration, not just formatting the user's words.
- **Don't pad**: If the user's description is already comprehensive, don't add filler sections. A short, well-written issue is better than a long one.
- **Match the repo's voice**: Look at recent issues (`gh issue list --limit 5`) for tone and structure conventions. Adapt accordingly.
- **Parallel filing**: When processing multiple issues, research can run in parallel. File all issues at the end.
- **Speed over ceremony**: The default is to file directly. Only pause to ask when it would genuinely change the issue being filed.
