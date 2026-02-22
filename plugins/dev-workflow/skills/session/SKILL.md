---
name: session
description: >
  Full dev session lifecycle: triage open issues, solve the top
  priority item, then reflect on lessons learned. Chains /triage,
  /solve, and /reflect into a single workflow. Use at the start of
  a working session to run the full dev lifecycle end-to-end.
argument-hint: "[--light]"
---

# Session

Run a complete dev session from start to finish. This skill chains
three phases, each backed by a dedicated skill.

## Arguments

- `--light`: Run the session in cost-efficient mode. Propagates to
  `/solve`, which passes it to `/code-review`. Code review uses a single
  Sonnet agent instead of the full multi-agent Opus pipeline. Use for
  routine sessions where the PRs are likely to be small or low-risk.

## Phase 1: Triage

Delegate triage to a single subagent (Task tool). Triage is pure
research — it doesn't need the main context. Send one agent to do all
the repo state, issue, and context gathering, then present the
synthesized results to the user.

The triage agent should assess:

- Repo state (recent commits, open PRs, CI status)
- Open issues (priorities, themes, dependencies)
- Recent context (handoff notes, session history)
- A prioritized session queue of work items to tackle

After the triage agent returns, present the results in two steps:

1. **Print the triage summary to the main response** — a prioritized list
   or table with full context per item (complexity, what it unblocks, any
   notable dependencies). This is where markdown renders properly and the
   user can scroll at their leisure.

2. **Call AskUserQuestion with a short, self-contained question** — one
   option per queue item. Each option label should be the issue number +
   one-line description; the option description should add one sentence of
   essential context. The user can scroll up to the full summary if they
   need more detail. Keep the question field itself brief.

## Phase 2: Solve

The user selects one or more items from the triage queue. Each queue
item (a single issue or a bundle of related issues) maps to one
`/solve` invocation and one PR.

By default, solve the **top item** from the approved queue. A single
solve cycle (intake → implement → review → merge) consumes most of the
available context, so one item per session is the normal case. If the
user explicitly asks to continue with more items, repeat Phase 2 for
the next queue item after merging the current PR.

Use the issue number from the user's triage selection. Do not reuse
issue numbers from prior context or previous sessions.

If `--light` was passed to `/session`, invoke `/solve --light <issue>`.

`/solve` runs the full issue-to-PR workflow:

- Intake, explore, scope (with `/consult` for design decisions)
- Plan, implement, verify
- Code review and CI confirmation
- Present the PR

## Phase 2b: Merge

After each PR is approved by the user, merge it and clean up:

1. Merge via `gh pr merge` (use the project's preferred merge strategy)
2. Update the local default branch
3. Delete the feature branch locally and remotely

## Phase 3: Reflect

After the PR is presented (or if the session is winding down for
any reason), invoke `/reflect` to:

- Review the session for missteps, discoveries, and patterns
- Propose improvements to docs, skills, and memory
- Apply approved changes and commit

## Guidelines

- **Each phase is a checkpoint.** Wait for user input between phases.
  Don't auto-advance from triage to solve without approval. The
  solve→reflect transition is the exception: after merging the final PR,
  proceed directly to `/reflect` without checking in.
- **Phases can be skipped.** If the user already knows what to work on,
  skip triage. If there's nothing to reflect on, skip reflect. The
  skill is a framework, not a straitjacket.
- **Multiple solve cycles are possible but not the default.** A single
  solve cycle typically consumes most of the context. If the user asks
  to continue after merging, repeat Phase 2 for the next queue item.
  Don't auto-advance -- let the user decide.
- **Reflect even on short sessions.** A quick fix that surfaced a
  gotcha is still worth capturing. The value of /reflect isn't
  proportional to session length.
