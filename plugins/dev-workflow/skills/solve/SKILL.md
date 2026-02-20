---
name: solve
description: >
  Turn GitHub issues into reviewed pull requests. Explores the codebase,
  collaboratively scopes design decisions with the user, plans the
  implementation, builds it, and runs code review before presenting the PR.
argument-hint: <issue> [<issue> ...]
---

# Solve

Turn one or more GitHub issues into a reviewed pull request. Work through
these phases in order. Do not skip phases unless explicitly noted.

## Arguments

`$ARGUMENTS` contains issue references separated by spaces. Each may be a
number (`42`), prefixed (`#42`), or a full URL. Parse all references and
normalize to issue numbers.

## Phase 1: Intake

Fetch every issue:

    gh issue view <number> --json title,body,labels,comments,assignees,milestone

For each issue, extract:
- What is being requested (bug fix, feature, refactor, docs, etc.)
- Acceptance criteria or constraints mentioned
- Relevant context from comments

If multiple issues were provided, note how they relate to each other.

## Phase 2: Explore

Build a deep understanding of the codebase as it relates to the issues.
Use subagents (Task tool, subagent_type=Explore) to:

1. Read CLAUDE.md and any project documentation
2. Find code directly relevant to the issue(s) -- modules, files, patterns,
   interfaces
3. Identify conventions, test patterns, and architectural norms the solution
   must follow
4. Search for related PRs or issues that provide additional context

**Do not ask the user anything yet.** Your questions in Phase 3 must be
informed by what you learn here. Generic questions waste the user's time
and signal that you haven't done the work.

## Phase 3: Scope

Triage the issue(s) into one of three categories:

**Trivial** -- The fix is obvious, mechanical, and low-risk (typo, config
change, single-line fix). Skip directly to Phase 4 without user
interaction.

**Well-scoped** -- The issue clearly describes what to build and the
implementation path is clear from your exploration. Briefly present your
understanding and planned approach. Ask the user to confirm, then proceed
to Phase 4.

**Needs design decisions** -- There are open questions about approach,
trade-offs, or how the solution fits into the existing architecture.
Follow `/consult` principles for structured decision-making:

- Present only high-leverage decisions where the user's input changes the
  outcome
- Lead with a recommendation, but surface the weakest parts of that
  recommendation
- Options must demonstrate deep codebase understanding -- never generic
- Group related questions (up to 4) into a single AskUserQuestion call
- Progress from high-level architectural decisions down to implementation
  details

## Phase 4: Plan

Write a concrete implementation plan:

1. Create a task list (TaskCreate) covering every discrete task
2. For each task, specify which files will be created or modified and what
   changes will be made
3. Include test additions or updates where appropriate
4. Note any migration, compatibility, or ordering considerations

Present the plan to the user for approval. If the plan involves
meaningful design choices (file structure, approach, scope), apply
`/consult` principles: surface specific decisions with codebase-informed
options that demonstrate understanding. A generic "looks good?" is only
appropriate when the plan is fully mechanical with no real choices to
make.

## Phase 5: Implement

Execute the approved plan:

1. Create a feature branch from the default branch
2. Work through each task, updating progress as you go (TaskUpdate)
3. Follow the conventions and patterns discovered in Phase 2
4. Write tests where the project's norms call for them
5. Commit with clear, descriptive messages
6. Push and create a PR that:
   - Has a clear title (under 72 characters)
   - Summarizes the changes in the body
   - Includes `Closes #N` for each issue being resolved

## Phase 6: Verify

Run the project's checks locally before requesting review. This catches
lint errors, formatting issues, and test failures before the PR is
presented.

1. Check for CI workflow files in `.github/workflows/` to discover what
   checks the project runs (linting, formatting, tests, etc.)
2. If CI exists: install dependencies if needed, run each check locally
3. If no CI: run whatever validation is available (test suite, linter,
   type checker) based on the project's tooling
4. If any check fails, fix the issue, commit the fix, push to the remote
   branch, and re-run the failing check to confirm it passes
5. Repeat until all checks pass before proceeding

**Important:** Always derive the checks from the project's actual
configuration rather than hardcoding assumptions. Projects vary widely.

**Integration fixes:** When a change involves integration with external
systems (APIs, services, infrastructure), verify the integration actually
works end-to-end -- not just that the code compiles and lints. Syntactically
correct config in the wrong format is a silent failure.

## Phase 7: Review

Before presenting the PR to the user:

1. Invoke `/code-review` using the Skill tool to run a thorough review of
   the PR
2. If the review surfaces real issues, fix them and commit -- do not
   pause to report intermediate findings to the user; act on them
   autonomously
3. Re-run `/code-review` until clean -- the PR must pass review before
   being presented to the user

## Phase 8: Confirm CI

Before presenting the PR, confirm that CI passes on the PR itself (if the
project has CI configured). Local checks (Phase 6) are a fast feedback
loop, but the CI run is the source of truth.

1. Check the PR's CI status:

       gh pr checks <PR_NUMBER> --watch

   If `--watch` is unavailable, poll with `gh pr checks` until all
   checks complete.
2. If all checks pass, proceed to Phase 9.
3. If any check fails:
   a. Inspect the failure using `gh run view <run_id> --log-failed`
   b. Fix the issue, commit, and push
   c. Wait for the new CI run to complete and re-check
4. Repeat until CI is green.

If the project has no CI, skip this phase.

## Phase 9: Pre-merge Check-in

After code review and CI pass, run a quick check-in before presenting the
PR for merge. Implementation and review surface decisions and
considerations that weren't visible during planning:

1. Review the diff (`gh pr diff`) and code review feedback for anything
   that diverged from the original plan or introduced new trade-offs
2. If there are meaningful decisions or considerations that emerged,
   present them to the user via AskUserQuestion:
   - Lead with what changed vs. the plan and why
   - Surface trade-offs the user should know about before merging
   - If everything went exactly to plan with no surprises, briefly
     confirm that and skip the interactive check-in
3. If the user requests changes, implement them, re-run code review and
   CI, then return to this phase

## Phase 10: Present

Give the user:

- Link to the PR
- Concise summary of what was implemented and why
- Key decisions made during scoping and their rationale
- Review results (clean, or notes on what was flagged and addressed)
- Any known limitations or suggested follow-up work

## Guidelines

- **Delegate aggressively.** Only interactive work (AskUserQuestion,
  presenting plans for approval) needs the main context. Push exploration,
  implementation, and review to subagents (Task tool) to keep the main
  context lean. Phase 2 exploration, Phase 5 implementation of individual
  tasks, Phase 6 verification, Phase 7 review, and Phase 8 CI confirmation
  are all good candidates for delegation.
- **Explore before you ask.** Never ask the user a question you could
  answer by reading the code. Uninformed questions erode trust.
- **Options reveal understanding.** The quality of your scoping options is
  the primary signal of whether you understand the problem. Invest effort
  in curating them. If the options are generic, you have not explored
  enough.
- **Don't over-engineer.** Implement what the issues ask for. No
  unrequested features, refactoring, or "improvements."
- **Track progress.** Use TaskCreate/TaskUpdate throughout so the user has
  visibility into what you're doing and what remains.
- **Be honest about scope.** If the issue is too large for a single PR,
  say so and suggest how to split it.
