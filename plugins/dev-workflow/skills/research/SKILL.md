---
name: research
description: >
  Systematic context-building through parallel research agents. Use before
  design decisions, implementation, or anytime you need to ground your
  understanding of a problem space. Launches parallel Haiku research agents,
  synthesizes findings, identifies gaps, and repeats until the design space
  is clear enough for /consult.
---

# Research

Systematic context-building through parallel research agents. Use before
design decisions, implementation, or anytime you need to ground your
understanding of a problem space.

## Purpose

You are building a grounded map of the problem space. The goal is to reduce
unknowns, verify assumptions, and understand constraints before making
decisions. This is NOT a query→answer tool — it's about systematically
exploring what you don't know.

Research feeds directly into `/consult` for design decisions. The output is
not a report; it's context in the main agent's window for high-signal decision
questions.

## When to use

- Before implementing a complex feature (understand the design space first)
- When you encounter unfamiliar APIs, tools, or platform behaviors
- When assumptions need empirical verification
- When the user says "let's research this first" or similar
- As part of `/solve` when the issue requires exploration before planning

## Research directions (light scaffolding)

Suggest categories to **consider** (not a checklist — pick what's relevant to
the current problem):

- **Codebase state**: What exists today? How does the current code handle this?
  What patterns are established? What subsystems interact with this area?

- **External documentation**: What do official docs say? Are there known
  limitations or gotchas? What does the community say about similar problems?

- **Empirical verification**: Can we test assumptions directly? (e.g., launch a
  worktree agent and observe its environment, run a script, check behavior)

- **Prior art**: How have others solved this? Are there published examples,
  community patterns, or reference implementations?

- **Constraints & gotchas**: What platform limitations, sandbox restrictions,
  or tool behaviors could affect the design? What edge cases should we be aware
  of?

- **Adjacent context**: What related systems, skills, or workflows does this
  interact with? What dependencies or integration points exist?

For each round, pick 3-5 directions that would most reduce uncertainty. Prefer
breadth in early rounds (cover the full problem space), depth in later rounds
(drill into specific gaps).

## Protocol

### 1. Identify unknowns

From the current context, ask yourself:

- What don't you know?
- What assumptions are you making?
- What could go wrong if those assumptions are wrong?
- Which unknowns, if resolved, would most change the direction?

Articulate your current mental model explicitly. Explain what's clear and what
gaps remain.

### 2. Launch parallel research agents

For each research direction you've identified, launch a Haiku subagent with a
**focused prompt**. Each agent should:

- Have a **specific question or investigation scope** (not "research everything")
- Know **where to look**: codebase paths, online docs, empirical tests
- Know **what to find**: which questions to answer, which facts to confirm
- Be **independent** of other agents (no cross-agent dependencies)

Launch all agents in parallel. Each should return structured findings: confirmed
facts, likely behaviors, unknowns.

### 3. Synthesize and present

After agents return, merge findings into a coherent summary. Print to the user:

- **Confirmed facts** — things we now know for certain (backed by evidence)
- **Open questions** — things we still don't know (name them explicitly)
- **Assumptions to verify** — things we believe but haven't confirmed yet
- **Key constraints** — limitations that shape the design space

This synthesis is the user's window into what you learned. Print it between
rounds so they can see the evolving knowledge map and redirect if the research
is off-track.

### 4. Decide: another round or ready?

Apply this heuristic:

- **Stop when**: Unknowns are bounded (we know what we don't know), key
  assumptions are verified, and you can articulate the design space clearly
  enough to write concrete decision questions for `/consult`.

- **Continue when**: Critical unknowns remain, assumptions are unverified, or
  the design space is still ambiguous.

- **If unsure**: Do one more round. The cost of over-researching is lower than
  the cost of building on false assumptions.

### 5. Repeat from step 1

With refined questions targeting remaining gaps. Continue until you hit the
stop condition.

## Agent prompt guidelines

Each research agent gets a focused, specific prompt. Template structure:

```
You are researching [specific question/area].

Context: [1-2 sentences on why this matters]

Investigate:
- [Specific question 1]
- [Specific question 2]
- [Specific question 3]

Where to look:
- [Codebase paths or file patterns]
- [Documentation or reference URLs]
- [Empirical tests you could run]

Return a structured summary with three sections:
1. Confirmed facts (backed by evidence from your investigation)
2. Open questions (things we still don't know)
3. Constraints or gotchas (practical limitations that affect design)

Focus on precision over breadth. If you're uncertain about something, say so.
```

Mark as RESEARCH ONLY (no code changes) unless the investigation requires
writing test code or temporary scripts.

## Transition to /consult

When research is complete, you should have enough context to:

- Enumerate the viable design options
- Articulate trade-offs for each option
- Identify which decisions need user input vs. can be made autonomously
- Write high-signal, codebase-specific questions

At this point, invoke `/consult` with curated questions. The synthesis from
your research round should be the context for those decisions.

## Guidelines

### Breadth before depth

Early rounds should cover the full problem space. Later rounds drill into
specific gaps.

Example: Round 1 asks "What tools does the codebase use? What APIs are
available? What constraints exist?" Round 2 asks "For API X, what are the edge
cases? What do users commonly get wrong?"

### Empirical over theoretical

If you can test an assumption directly (launch an agent, run a command), do it
instead of speculating.

Example: Don't assume "the sandbox blocks file writes." Ask an agent to test it
empirically and report what works and what fails.

### Print your synthesis

The user should see the evolving knowledge map between rounds. This:

- Builds trust (they see the work happening)
- Lets them redirect if the research is off-track
- Creates a record of what you learned

### Don't over-research

Research is a means to an end. If you have enough context to make good
decisions, stop and move on. Continuing indefinitely is procrastination.

### Parallel by default

Independent research directions should always be launched as parallel agents,
not sequential. This saves token budget and wall-clock time.

## Example workflow

**Problem**: We need to add a hook that runs on tool failures, but we're not
sure what hook events are available or how to access error data.

**Round 1 - Identify unknowns**:

- What hook events exist for failures? (PostToolUseFailure? Error events?)
- How is error data passed to hooks? (top-level field? nested in tool_result?)
- Are there examples of hooks handling errors?
- What constraints apply to error handling? (Can we block? Can we modify?)

**Round 2 - Launch parallel agents**:

- Agent 1: Search hook docs for error-related events and fields
- Agent 2: Search codebase for existing error-handling hooks
- Agent 3: Check GitHub issues for PostToolUseFailure discussions
- Agent 4: Run empirical test: trigger a tool failure and observe the JSON

**Round 3 - Synthesize**:

Confirmed: PostToolUseFailure exists, errors in top-level "error" field,
`additionalContext` works, `decision: "block"` is parsed but not acted upon.

Open questions: Are there other hook events? Can we modify tool input on error?

Constraints: Can't block after failure (conceptually wrong). Limited guidance
mechanisms (additionalContext only).

**Ready for /consult?** Yes. We now know the design space. Questions to ask:

1. Should we use PostToolUseFailure or PreToolUse (to prevent failures)?
2. Do we need additionalContext guidance, or should we escalate (via reminders,
   system messages)?

This moves to `/consult` for decision-making with the user.
