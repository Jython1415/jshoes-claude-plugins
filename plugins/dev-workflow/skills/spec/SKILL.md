---
name: spec
description: >-
  Write a lightweight spec for issues that need design decisions. Produces a
  temporary spec file capturing Problem, Definition of Done, Decisions, and
  Approach. Invoked automatically by /solve for complex issues, or standalone
  with an issue number. Spec files are working artifacts deleted after merge.
---

# Spec

Write a lightweight spec file for issues requiring design decisions.
Produces a durable artifact that survives conversation compaction and
guides implementation.

## Arguments

Parse issue references from arguments (numbers, #-prefixed, or URLs).
Normalize to issue numbers.

## When invoked standalone

If invoked outside /solve (no prior exploration context), run a quick
intake and exploration phase:

1. Fetch the issue with `gh`
2. Launch an Explore subagent to understand relevant code and patterns
3. Then proceed to the spec workflow below

If invoked by /solve, exploration is already done — proceed directly.

## Spec Workflow

### Step 1: Draft Definition of Done

Before exploring approaches or making design decisions, lock in what
success looks like. This prevents goal drift during brainstorming.

1. Synthesize a Definition of Done from the issue body, comments, and
   exploration findings
2. Present the draft DoD to the user via `AskUserQuestion` for
   confirmation/refinement
3. The DoD should be concrete and verifiable — "the user can..." or
   "the system does..." statements, not vague goals

Do not proceed until the DoD is confirmed.

### Step 2: Resolve Design Decisions

Invoke `/consult` (via the Skill tool) to resolve open design questions.
`/consult` handles recommendation-led, codebase-informed questions with
the user.

If the issue has no open design questions (rare for issues routed here),
skip this step.

### Step 3: Write Spec File

Write the spec to `SPEC-<issue-number>.md` at the repository root.

Template:

```markdown
# Spec: <Issue Title> (#<number>)

## Problem

<What the issue is solving — 2-3 sentences from the issue body>

## Definition of Done

<Confirmed DoD from Step 1 — bulleted list of concrete criteria>

## Decisions

<Each design decision resolved in Step 2, with the chosen option and
brief rationale. If no decisions were needed, note "No open design
questions — approach was clear from exploration.">

## Approach

<The chosen design direction, synthesizing the DoD and decisions into
a coherent plan. Component-level detail — what changes where and why.
NOT task-level implementation steps (that's /solve Phase 4's job).>
```

Commit the spec file to the current branch with message:

```
docs: add spec for #<number>
```

### Step 4: Return

Report the spec file path to the caller. If invoked by /solve, /solve
will use this as input for Phase 4 (Plan). The spec file should be
deleted in the final commit before the PR is presented.

## Guidelines

- The spec is a working artifact, not permanent documentation. Keep it
  concise — a page or less for most issues.
- Definition of Done is the anchor. If design discussion drifts, return
  to the DoD.
- Don't duplicate `/consult`'s job. Invoke `/consult` for design decisions
  rather than running your own `AskUserQuestion` for design choices.
- The spec captures WHAT and WHY at component level. Implementation
  details (task breakdown, file-by-file changes) belong in /solve Phase 4.
- If the issue is simple enough that the spec would just restate the
  issue body, say so and skip spec generation. Not every "needs design
  decisions" issue needs a full spec — sometimes one `/consult` round is
  enough and the decisions can be noted inline.

## Role in the skill collection

`/spec` is a **workflow that produces a durable artifact** (the spec file).
It uses `/consult` internally for design decisions but adds:

- **Definition of Done** — locks in success criteria before exploring
  approaches (prevents goal drift)
- **Spec file** — a working document that survives context compaction and
  guides implementation

The relationship: `/consult` is a reusable decision primitive (stateless,
artifact-free). `/spec` is a workflow that wraps `/consult` and produces a
file. This is analogous to a function vs. a program that calls it.

**When /solve routes to /spec vs /consult directly:**
- `/spec` — "Needs design decisions" issues where the complexity warrants
  a durable artifact (DoD + decisions + approach captured in a file)
- `/consult` — Well-scoped issues with implementation sub-choices, or
  post-implementation trade-offs in Phase 9 (decisions don't need a file)
