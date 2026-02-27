# Dev Workflow Plugin

A set of development workflow skills for GitHub-based repositories. Covers the full lifecycle from issue triage through implementation, code review, and session retrospective.

## Skills

### /session

Runs a complete dev session end-to-end by chaining `/triage`, `/solve`, and `/reflect`. Use at the start of a working session to go from a blank slate to a merged PR with lessons captured.

**Arguments:** `[--light]`

- `--light` - Cost-optimized mode; propagates to `/solve` and `/code-review`, using Sonnet instead of Opus for review

**Phases:**
1. Triage open issues and propose a prioritized queue
2. Solve the selected item (one PR per session by default)
3. Reflect and persist session learnings

### /triage

Analyzes repo state, open issues, and recent activity to propose a prioritized session queue. Use at the start of a session when you are not sure what to work on.

**What it does:**
- Checks recent commits, open PRs, and CI status
- Fetches and reads all open issues
- Looks for handoff notes and prior session context
- Classifies issues as bundleable or independent
- Proposes a prioritized queue with complexity estimates and rationale

### /solve

Turns one or more GitHub issues into a reviewed pull request. Use when asked to implement an issue, fix a bug, or build a feature tracked in an issue.

**Arguments:** `<issue> [<issue> ...] [--light]`

- Issue references: numbers (`42`), prefixed (`#42`), or full URLs
- `--light` - Use single-agent Sonnet review instead of the full multi-agent Opus pipeline

**Phases:** Intake → Explore → Scope (with `/consult` if needed) → Plan → Implement → Verify → Review → Confirm CI → Pre-merge check-in → Present

### /code-review

Multi-agent code review for pull requests. Use after creating or updating a PR, or when asked to check code quality before merging.

**Arguments:** `[--light] [--comment]`

- `--light` - Cost-optimized single-agent review using Sonnet; same quality bar as the full pipeline
- `--comment` - Post inline GitHub comments for each finding (works in both modes)

**Full mode:** 4 parallel agents check convention compliance (2 Sonnet agents) and bugs (2 Opus agents), with a validation pass per finding.

**Light mode:** 1 Sonnet agent performs a structured three-pass review (category sweep, validate candidates, coverage check).

### /consult

Collaborative decision-making with the user. Presents curated, high-leverage questions that demonstrate deep codebase understanding. Use any time you need the user's input on design decisions.

**When to use:**
- Design decisions with multiple valid approaches
- Trade-offs where user priorities change the answer
- Before significant work where understanding needs confirming

**What it does:** Curates questions ruthlessly (only high-leverage decisions), leads with a recommendation for each, surfaces weaknesses in the recommendation, and groups related questions (up to 4 per `AskUserQuestion` call).

### /reflect

End-of-session retrospective. Reviews what happened, extracts lessons, and proposes concrete improvements to docs, skills, and memory. Use at the end of a session, after a notable misstep or discovery, or when winding down.

**What it does:**
- Reviews the session for missteps, discoveries, repeated patterns, and user corrections
- Categorizes improvements into documentation, skills, or memory
- Packs proposed changes into a single `AskUserQuestion` call (up to 4 questions)
- Applies approved changes and commits directly to main

### /issue

Files a well-researched GitHub issue from a brief description. Use when asked to file, create, or report an issue or bug in a GitHub repo.

**Arguments:** `<description>`

**What it does:**
- Explores the relevant code area
- Checks for duplicate or related issues
- Drafts a structured issue with Problem, Current state, and Desired outcome sections
- Files via `gh issue create` (or body file for multi-line bodies)

## Installation

### From GitHub Marketplace

```bash
# Add marketplace
claude plugin marketplace add Jython1415/jshoes-claude-plugins

# Install plugin globally
claude plugin install dev-workflow@jshoes-claude-plugins
```

## Requirements

- Claude Code CLI
- `gh` CLI (authenticated) for all GitHub operations

## Author

**Jython1415**
https://github.com/Jython1415

## Repository

https://github.com/Jython1415/jshoes-claude-plugins
