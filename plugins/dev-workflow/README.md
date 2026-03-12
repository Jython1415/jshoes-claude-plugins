# Dev Workflow Plugin

A set of development workflow skills for GitHub-based repositories. Covers the full lifecycle from issue triage through implementation, code review, and session retrospective.

## Skills

### /session

Runs a complete dev session end-to-end by chaining `/triage`, `/solve`, and `/reflect`. Use at the start of a working session to go from a blank slate to a merged PR with lessons captured.

**Arguments:** `[--light] [--heavy]`

- `--light` - Haiku-first checklist pipeline; propagates to `/solve` and `/code-review`.
- `--heavy` - Full multi-agent Opus pipeline; propagates to `/solve` and `/code-review`. Default uses a single Sonnet agent.

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

**Arguments:** `<issue> [<issue> ...] [--light] [--heavy]`

- Issue references: numbers (`42`), prefixed (`#42`), or full URLs
- `--light` - Use the Haiku-first checklist review instead of the default single-Sonnet agent
- `--heavy` - Use the full multi-agent Opus review instead of the default single-Sonnet agent

**Phases:** Intake → Explore → Scope (with `/consult` if needed) → Plan → Implement → Verify → Review → Confirm CI → Impact analysis → Pre-merge check-in → Present

### /code-review

Multi-agent code review for pull requests. Use after creating or updating a PR, or when asked to check code quality before merging.

**Arguments:** `[--light] [--heavy] [--comment]`

- `--light` - Two-stage Haiku+Sonnet pipeline; mechanical checklist only (no reasoning-based bug detection)
- `--heavy` - Full multi-agent Opus pipeline; use for high-stakes PRs where maximum coverage matters
- `--comment` - Post inline GitHub comments for each finding (works in all modes)

**Light mode (`--light`):** Haiku runs an explicit mechanical checklist (hardcoded credentials, SQL injection patterns, bare exception handlers, debug prints, TODO comments, naming conventions) and returns structured JSON. Sonnet filters false positives and synthesizes the final output.

**Default mode:** 1 Sonnet agent performs a structured three-pass review (category sweep, validate candidates, coverage check).

**Heavy mode (`--heavy`):** 4 parallel agents check convention compliance (2 Sonnet agents) and bugs (2 Opus agents), with a validation pass per finding.

### /research

Systematic context-building through parallel research agents. Use before design decisions, implementation, or anytime you need to ground your understanding of a problem space.

**When to use:**
- Before implementing a complex feature
- When you encounter unfamiliar APIs, tools, or platform behaviors
- When assumptions need empirical verification
- As part of /solve when the issue requires exploration before planning

**What it does:** Identifies unknowns from the current context, launches parallel research agents to investigate specific directions (codebase state, external documentation, empirical verification, prior art, constraints, adjacent systems), synthesizes findings between rounds, and continues until the design space is clear enough for /consult. Prints the evolving knowledge map so the user can see progress and redirect as needed.

**Research directions** (light scaffolding, pick what's relevant):
- Codebase state: existing code, patterns, related subsystems
- External documentation: official docs, limitations, community patterns
- Empirical verification: direct testing of assumptions
- Prior art: how others solved similar problems
- Constraints & gotchas: platform limitations, edge cases
- Adjacent context: related systems, dependencies, integration points

### /spec

Write lightweight specs on complex issues. Produces a temporary spec file that survives conversation compaction and guides planning. Use when an issue requires significant design decisions before implementation.

**When to use:**
- During `/solve` for issues classified as "Needs design decisions"
- Standalone when you need to document design trade-offs
- Before major refactors or architectural changes
- When multiple implementation approaches are viable

**What it does:** Generates a structured temporary spec file with Problem statement, Definition of Done, key Decisions, and Approach. The spec is saved to the working directory, used by `/solve` Phase 4 for planning, and deleted in Phase 5 as a working artifact (not permanent documentation).

**Spec sections:**
- Problem: clear statement of what needs solving
- Definition of Done: acceptance criteria and success metrics
- Decisions: key design trade-offs and choices made
- Approach: implementation strategy and phases

### /consult

Collaborative decision-making with the user. Presents curated, high-leverage questions that demonstrate deep codebase understanding. Use any time you need the user's input on design decisions.

**When to use:**
- Design decisions with multiple valid approaches
- Trade-offs where user priorities change the answer
- Before significant work where understanding needs confirming
- After /research has mapped the design space

**What it does:** Curates questions ruthlessly (only high-leverage decisions), leads with a recommendation for each, surfaces weaknesses in the recommendation, and groups related questions (up to 4 per `AskUserQuestion` call).

### /reflect

End-of-session retrospective. Reviews what happened, extracts lessons, and proposes concrete improvements to docs, skills, and memory. Use at the end of a session, after a notable misstep or discovery, or when winding down.

**Arguments:** `[--light] [--heavy]`

- `--light` - Haiku scanner for cost-sensitive retrospectives; single focused pass
- `--heavy` - Two parallel Sonnet scanners for redundancy and thoroughness. Default uses a single Sonnet scanner.

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

## Architecture

### Design Philosophy

Skills are **concern-oriented** — each solves one problem — with **conditional routing**, not pipeline-oriented. This keeps skills reusable: `/consult` can be invoked standalone, by `/solve` for scoping decisions, or by `/spec` for design questions. Similarly, `/research` is optionally invoked by `/solve` Phase 2 when the issue involves unfamiliar APIs, external systems, or explicit investigation needs.

### Skill Dependency Graph

```
/session → /triage → /solve → /reflect
                       ↓
              /spec ←→ /consult
                       ↓
                   /code-review
```

- `/session` coordinates the full dev lifecycle: triage, solve, reflect
- `/solve` assesses issue complexity and routes to `/spec` (for design-heavy issues) or direct implementation
- `/spec` wraps `/consult` to produce durable spec artifacts; `/consult` provides reusable decision-making
- `/solve` optionally invokes `/research` in Phase 2 for unfamiliar territory
- `/code-review` is the final approval gate (standalone or called by `/solve` Phase 8)

### Routing Model

`/solve` classifies the issue on intake and conditionally invokes the right skill:
- **Well-scoped issues** (clear acceptance criteria, determined approach) → skip directly to implementation
- **Issues needing design decisions** (multiple approaches, significant trade-offs) → route through `/spec` + `/consult`
- **Unfamiliar territory** (unknown APIs, external systems) → invoke `/research` in Phase 2
- **Complex scoping** (unclear boundaries, ambiguous requirements) → invoke `/consult` to refine the problem

This is different from pipeline models (like ed3d-plan-and-execute) where every issue flows through design → plan → execute sequentially. The conditional routing keeps the common path fast.

## Agents

### worktree-implementor

An isolated worktree execution agent designed for Haiku-tier models implementing code changes with built-in commit discipline.

**What it is:** A standalone agent that creates a git worktree and enforces a commit-before-exit discipline for code changes.

**What it does:**
- Creates an isolated worktree based on the current HEAD
- Implements code changes within the worktree
- Enforces structured commit discipline (must commit or explicitly abandon changes before exiting)
- Generates exit reporting with implementation summary, commit hashes, and outcomes

**How to invoke it:**
```
Agent(subagent_type: "dev-workflow:worktree-implementor", prompt: "...")
```

**Key features:**
- Structured exit reporting: returns implementation summary, all commit SHAs, and success/failure status
- Procedural, Haiku-ready instructions: step-by-step procedures avoid open-ended judgment
- Sandbox-aware git protocol: handles authentication, GPG signing constraints, and git worktree lifecycle
- Isolation baked in: worktree creation is mandatory, not optional — every invocation gets a fresh, isolated work context

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
