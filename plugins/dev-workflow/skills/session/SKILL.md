---
name: session
description: >
  Full dev session lifecycle: triage open issues, solve a batch, then
  reflect on lessons learned. Chains /triage, /solve, and /reflect
  into a single workflow.
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
- A recommended batch of issues to tackle

Wait for the user to approve the batch before proceeding.

## Phase 2: Solve

Invoke `/solve` with the approved issue batch. This runs the full
issue-to-PR workflow:

- Intake, explore, scope (with `/consult` for design decisions)
- Plan, implement, verify
- Code review and CI confirmation
- Present the PR

If the batch contains independent issues that would produce separate
PRs, run `/solve` for each. If issues are related and belong in one
PR, pass them all to a single `/solve` invocation.

## Phase 2b: Merge

After each PR is approved by the user, merge it and clean up:

1. Merge via `gh pr merge` (use the project's preferred merge strategy)
2. Update the local default branch
3. Delete the feature branch locally and remotely

If there are multiple PRs in the batch, merge each one after its
approval before moving to the next `/solve` invocation, so later work
builds on the merged state.

## Phase 3: Reflect

After all PRs are presented (or if the session is winding down for
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
- **Multiple solve cycles are fine.** A session might involve triaging
  once, then solving 2-3 batches before reflecting. The lifecycle is
  triage → (solve)+ → reflect, not strictly one of each.
- **Reflect even on short sessions.** A quick fix that surfaced a
  gotcha is still worth capturing. The value of /reflect isn't
  proportional to session length.
