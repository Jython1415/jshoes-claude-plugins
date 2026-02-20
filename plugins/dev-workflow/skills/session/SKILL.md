---
name: session
description: >
  Full dev session lifecycle: triage open issues, solve the top
  priority item, then reflect on lessons learned. Chains /triage,
  /solve, and /reflect into a single workflow.
---

# Session

Run a complete dev session from start to finish. This skill chains
three phases, each backed by a dedicated skill.

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

Wait for the user to approve the queue before proceeding.

## Phase 2: Solve

The user selects one or more items from the triage queue. Each queue
item (a single issue or a bundle of related issues) maps to one
`/solve` invocation and one PR.

By default, solve the **top item** from the approved queue. A single
solve cycle (intake → implement → review → merge) consumes most of the
available context, so one item per session is the normal case. If the
user explicitly asks to continue with more items, repeat Phase 2 for
the next queue item after merging the current PR.

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
  Don't auto-advance from triage to solve without approval.
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
