---
name: triage
description: >
  Analyze repo state, open issues, and recent activity to propose a
  coherent batch of work for the session. Use at the start of a session
  to decide what to tackle.
---

# Triage

Assess the current state of the project and propose what to work on.
This is a research and synthesis task -- you are not implementing
anything, you are helping the user decide where to focus.

## Step 1: Repo state

Gather context on what's been happening recently:

1. `git log --oneline -20` -- recent commits, what landed recently
2. `git branch -a` -- any open feature branches
3. `gh pr list` -- open PRs awaiting review or merge
4. `gh run list --limit 5` -- recent CI status (if CI is configured)

Note anything that needs immediate attention (failing CI, stale PRs,
unfinished branches).

## Step 2: Open issues

Fetch all open issues:

    gh issue list --state open --limit 50 --json number,title,labels,createdAt,updatedAt

For each issue, understand:
- What it's asking for
- How long it's been open
- Whether it has labels indicating priority or category
- Any comments with additional context

If the issue list is large, fetch full details for the most promising
candidates:

    gh issue view <number> --json title,body,labels,comments

## Step 3: Recent context

Check for session continuity signals. Consult the project's documentation
(CLAUDE.md, DEVELOPMENT.md, or equivalent) to learn where prior session
context, handoff notes, or activity logs are stored. Look for:

1. Handoff notes or task lists from prior sessions
2. Memory files or session summaries with open issues tracking
3. Recent session logs or activity patterns (recurring failures,
   incomplete work)

## Step 4: Synthesize

Group issues by theme, dependency, and effort:

- **Themes**: Which issues are related and would benefit from being
  solved together? (e.g., "error handling", "performance",
  "new feature")
- **Dependencies**: Which issues unblock others? Those go first.
- **Effort**: Roughly how large is each issue? Can it fit in a single
  PR or does it need splitting?
- **Urgency**: Is anything broken or degraded right now?

## Step 5: Propose

Present 2-3 recommended batches to the user, ordered by your
recommendation. For each batch:

- Which issues it includes and why they go together
- Estimated complexity (light / moderate / heavy)
- What it unblocks or enables
- Any risks or open questions

Lead with your recommendation, explain why, and surface the trade-offs.
The user decides what to work on -- you provide the informed options.

## Guidelines

- **Delegate the research.** Use subagents for fetching issue details
  and exploring the codebase. Keep the main context for synthesis and
  presentation.
- **Don't just list issues.** The value is in the synthesis -- grouping,
  prioritization, and reasoning about what matters now.
- **Be opinionated.** The user wants your recommendation, not a menu.
  Say what you'd pick and why.
- **Note what you'd skip.** If an issue is low-priority or poorly
  defined, say so. Not everything needs to be tackled now.
