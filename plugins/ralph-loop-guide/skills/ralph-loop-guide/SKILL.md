---
name: ralph-loop-guide
description: "Best practices reference for writing effective ralph-loop prompts. Use when helping users structure prompts for autonomous coding loops, configure completion criteria, design quality gates, or debug convergence issues. Covers prompt anatomy, state management, backpressure, and common pitfalls — without prescribing a specific tooling stack."
---

# Ralph Loop Prompt Guide

Reference for writing prompts that converge in autonomous coding loops. This guide covers universal principles that apply regardless of which ralph-loop tooling you use.

**This is a living document.** When you discover new patterns, failure modes, or best practices through running ralph loops, update this file. Add to the pitfalls section, refine the templates, and correct anything that doesn't hold up in practice.

## What a Ralph Loop Is

A ralph loop feeds the same prompt to a coding agent repeatedly. Each iteration gets a fresh context window but sees the cumulative state of the filesystem and git history. The agent doesn't talk to itself — it reads its own previous work from files.

```
while not done:
    agent reads PROMPT → works on files → commits → exits
    loop feeds same PROMPT again
    agent sees updated files/git, picks up where it left off
```

The prompt is the constant. The codebase is the memory.

## Anatomy of an Effective Prompt

### Required Elements

1. **Task description** — what to build, fix, or refactor
2. **Completion signal** — how the loop knows to stop
3. **Success criteria** — concrete, verifiable conditions (tests pass, linting clean, etc.)

### Strongly Recommended Elements

4. **Orientation phase** — tell the agent to study existing code/specs before acting
5. **Single-task constraint** — one logical unit of work per iteration
6. **Quality gates** — automated checks that must pass before committing
7. **State files** — where to read progress and where to write updates

### Structure

A well-structured prompt follows this general flow:

```markdown
# Phase 0: Orient
Study the specs/requirements and existing code. Understand what exists
before assuming anything is missing.

# Phase 1: Select
Pick the highest-priority incomplete task.

# Phase 2: Implement
Do the work. One task only.

# Phase 3: Validate
Run tests, linting, type checks. All must pass.

# Phase 4: Record & Commit
Update progress tracking. Commit with a descriptive message.

# Completion
When ALL tasks are done and ALL checks pass:
<promise>COMPLETE</promise>

# Guardrails
[Critical constraints and invariants — things that must never be violated]
```

The numbering scheme varies by practitioner. Some use `999+` for guardrails (higher = more critical). The key is that orientation comes first, guardrails are visually distinct, and the flow is unambiguous.

## Completion Signals

Every ralph loop needs a way to stop. Without one, it runs forever.

### The `<promise>` Tag

The most common convention across tooling:

```markdown
When all tasks are complete and all tests pass, output:
<promise>COMPLETE</promise>
```

The loop's stop hook watches for this tag. Custom promise text is supported in most implementations via a `--completion-promise` flag.

### Alternative Signals

- All items marked done in a structured task file (e.g., `prd.json`)
- A specific file created (e.g., `DONE.md`)
- Max iteration count reached (safety net, not primary signal)

### Always Set a Max Iteration Limit

Even with a completion signal, set `--max-iterations` as a circuit breaker. Recommended ranges:

| Scope | Iterations |
|-------|-----------|
| Single bug fix or small feature | 5–10 |
| Multi-task feature | 15–30 |
| Large project / overnight run | 50–100 |

## State Management

Since each iteration starts with a fresh context, the agent's memory lives in the filesystem. Common state files:

| File | Purpose | Who Writes |
|------|---------|-----------|
| `specs/*` or `requirements/*` | What to build (one file per topic) | Human |
| `IMPLEMENTATION_PLAN.md` | Prioritized task list | Agent (disposable, regenerate freely) |
| `progress.txt` | Log of completed work and learnings | Agent (append-only) |
| `AGENTS.md` | Operational notes: build commands, patterns, gotchas | Agent + Human |
| `prd.json` | Structured stories with pass/fail status | Human or Agent |

### Principles

- **Specs are the source of truth.** Plans are disposable. When trajectory diverges, regenerate the plan — don't patch it.
- **Keep operational docs lean.** AGENTS.md should be ~60 lines, not 600. Dense context is better than verbose context.
- **Append-only progress logs.** Never truncate `progress.txt`. It's the agent's long-term memory across iterations.
- **One topic per spec file.** Test: can you describe it in one sentence without "and"?

## Backpressure and Quality Gates

Backpressure is what makes ralph loops converge instead of diverge. Rather than telling the agent exactly what to do, engineer conditions where wrong outputs get automatically rejected.

### Upstream Steering (Before the Agent Acts)

- Well-written specifications
- Existing code patterns the agent discovers during orientation
- Shared utilities and types the agent must conform to
- Clear naming and directory conventions

### Downstream Gates (After the Agent Acts)

Include these explicitly in your prompt:

```markdown
Before committing, ALL of these must pass:
- `npm run typecheck` (or equivalent)
- `npm run lint`
- `npm run test`

Do NOT commit if any check fails. Fix the issue first.
```

Other gate types:
- Pre-commit hooks that enforce formatting/linting
- Build verification (`npm run build`)
- Coverage thresholds
- LLM-as-judge for subjective quality criteria

### The Key Insight

> Sit outside the loop, not in it. Engineer the environment; don't micromanage execution.

## Subagent Strategy

When your prompt instructs the agent to use subagents (parallel task workers), follow these guidelines:

- **Many subagents for reads/searches.** Exploring the codebase is embarrassingly parallel. Use as many as needed to study specs, search for patterns, and verify assumptions.
- **One subagent for builds/tests.** Sequential validation prevents conflicting changes and provides clear backpressure. If the build breaks, the agent knows exactly what caused it.
- **Use the most capable model for synthesis.** After parallel exploration, have a single capable model analyze findings, prioritize tasks, and make implementation decisions.

## Language That Matters

Specific phrasing affects agent behavior in measurable ways:

| Say This | Not This | Why |
|----------|----------|-----|
| "Study the specs" | "Read the specs" | "Study" implies deeper analysis, not just loading into context |
| "Don't assume not implemented" | (nothing) | Prevents the #1 failure: rebuilding what already exists |
| "Search codebase before implementing" | "Implement X" | Forces verification before action |
| "One task per iteration" | "Complete the project" | Prevents context overload and ensures incremental progress |
| "Capture the why in commit messages" | "Commit your changes" | Produces useful git history for future iterations |

## Prompt Templates

### Minimal Loop Prompt

For small, well-defined tasks:

```markdown
@specs/feature.md @progress.txt

Study the spec and progress file. Find the next incomplete requirement
and implement it. Run tests. Commit your changes. Update progress.txt.

Work on ONE requirement at a time.

When ALL requirements are implemented and tests pass:
<promise>COMPLETE</promise>
```

### Standard Development Loop

For multi-task features:

```markdown
# Phase 0: Orient
Study `specs/*` to understand requirements.
Read `IMPLEMENTATION_PLAN.md` for the current task list.
Review `AGENTS.md` for project-specific commands and patterns.
Search the codebase before assuming any feature is missing.

# Phase 1: Select Task
Pick the highest-priority incomplete task from the plan.

# Phase 2: Implement
Implement ONE task completely. No stubs or placeholders.
Follow existing code patterns and conventions.

# Phase 3: Validate
Run all quality checks (from AGENTS.md).
All must pass before proceeding.

# Phase 4: Record
Update IMPLEMENTATION_PLAN.md — mark completed, add learnings.
Update AGENTS.md if you discovered reusable patterns.
Append to progress.txt: what you did, files changed, gotchas.
Commit with a descriptive message that captures the "why".

# Completion
When ALL tasks in IMPLEMENTATION_PLAN.md are done and all checks pass:
<promise>COMPLETE</promise>

# Guardrails
- Complete implementations only. No TODOs, no placeholder code.
- Verify before assuming. Search the codebase first.
- Maintain single sources of truth. No migration shims or adapters.
- Fix any failing tests you encounter, even if unrelated to your task.
- Keep AGENTS.md lean and operational (commands, conventions, gotchas).
```

### Two-Prompt Mode (Plan Then Build)

Some practitioners separate planning and building into distinct prompts:

**Planning prompt** (`PROMPT_plan.md`):
```markdown
Perform gap analysis between specs/* and the existing codebase.
Generate a prioritized IMPLEMENTATION_PLAN.md.

CRITICAL: Do NOT implement anything. Planning only.

Search exhaustively. Verify functionality exists before listing it as a gap.
```

**Building prompt** (`PROMPT_build.md`):
```markdown
Read IMPLEMENTATION_PLAN.md. Pick the top task. Implement it.
Run tests. Commit. Update the plan.

When all tasks are done: <promise>COMPLETE</promise>
```

Run the planning prompt for a few iterations, review the plan, then switch to the building prompt.

### Test-Driven Loop

```markdown
Implement the requirements in @specs/feature.md using TDD.

For each requirement:
1. Write a failing test that captures the requirement
2. Implement the minimum code to pass the test
3. Run the full test suite
4. Refactor if needed (tests must still pass)
5. Commit

When ALL requirements have passing tests:
<promise>COMPLETE</promise>
```

## Common Pitfalls

### 1. Context Degradation in Long Sessions

**Problem:** Running many iterations in a single session causes context compaction, losing important early information.

**Fix:** Prefer fresh context per iteration (external bash loop) over same-session continuation. If using same-session mode, keep iteration counts low.

### 2. The Agent Rebuilds Existing Features

**Problem:** The agent doesn't search before implementing and creates duplicates.

**Fix:** Add explicit instructions:
```markdown
ALWAYS search the codebase before implementing. Do not assume
a feature is missing — it may already exist in a different location
or under a different name.
```

### 3. The Loop Never Converges

**Problem:** The agent keeps making changes but never reaches completion.

**Fixes:**
- Make completion criteria more concrete and testable
- Add stronger quality gates (if tests don't pass, the agent must fix before moving on)
- Reduce scope — smaller tasks converge faster
- Check that the completion signal syntax matches what the stop hook expects

### 4. Overly Verbose Prompts

**Problem:** Long, prose-heavy prompts degrade determinism. The agent struggles to follow too many instructions.

**Fix:** Keep prompts structured and concise. Use markdown lists and tables over paragraphs. Every line should earn its place.

### 5. No Progress Tracking

**Problem:** The agent redoes work from previous iterations because it doesn't know what's already done.

**Fix:** Always include a progress file and instruct the agent to update it. The progress file is how the agent "remembers" across fresh contexts.

### 6. Committing Broken Code

**Problem:** The agent commits before validation, and future iterations build on a broken state.

**Fix:** Make the validation step explicit and mandatory:
```markdown
Run ALL checks before committing. If ANY check fails,
fix the issue and re-run. Do NOT commit broken code.
```

### 7. Plan Rot

**Problem:** The implementation plan becomes stale or wrong, but the agent keeps following it.

**Fix:** Plans are disposable. Include instructions to update or regenerate the plan when it diverges from reality. Don't treat plans as sacred.

## Tuning Your Prompt

Ralph loops require iterative prompt refinement. The prompts you start with won't be the prompts you finish with.

### The Process

1. **Run a few iterations and watch.** Don't go AFK immediately. Observe what the agent does.
2. **Identify failure patterns.** Does it rebuild existing code? Skip tests? Commit too much at once?
3. **Add a "sign."** For each failure mode, add a specific, short instruction to the prompt. Like placing a sign near a playground slide: "SLIDE DOWN, DON'T JUMP."
4. **Re-run and verify.** Check if the sign fixed the behavior.
5. **Remove signs that aren't needed.** Unnecessary instructions add noise. Only keep what's actively preventing a known failure.

### When to Start Over

If the agent's trajectory has diverged badly:
- Regenerate `IMPLEMENTATION_PLAN.md` from scratch
- Reset to a known-good git commit
- Revise specs if they were the root cause
- Simplify the prompt if it's gotten too complex

## Ecosystem Reference

The ralph loop ecosystem includes many tools and approaches. Rather than prescribing one, here are the categories:

### Official Plugin
The `ralph-loop` Claude Code plugin provides `/ralph-loop` and `/cancel-ralph` commands for same-session loops.

### External Orchestrators
Tools like `ralph-orchestrator`, `ralphex`, `open-ralph-wiggum`, and others provide external bash-loop orchestration with features like multi-backend support, TUI monitoring, and template systems.

### Desktop / GUI Tools
Applications like `Ralph Desktop` offer visual interfaces with conversational prompt generation (brainstorm mode).

### Reference Material
- [ghuntley.com/ralph](https://ghuntley.com/ralph/) — Original technique description
- [github.com/ghuntley/how-to-ralph-wiggum](https://github.com/ghuntley/how-to-ralph-wiggum) — Reference templates
- [The Ralph Playbook](https://claytonfarr.github.io/ralph-playbook/) — Comprehensive practitioner guide
- [11 Tips for AI Coding with Ralph Wiggum](https://www.aihero.dev/tips-for-ai-coding-with-ralph-wiggum) — Community tips
- [awesome-ralph](https://github.com/snwfdhmp/awesome-ralph) — Curated tool and resource list
