---
name: consult
description: >
  Collaborative decision-making with the user. Presents curated,
  high-leverage questions that demonstrate deep codebase understanding
  and surface the trickiest parts of a proposed approach. Use anytime
  you need the user's input on decisions.
---

# Consult

Structure your interaction with the user to maximize their impact on
the outcome. The user's time and attention are the scarcest resources
in this collaboration. Every question you ask must earn its place.

## When to use this

- Design decisions with multiple valid approaches
- Trade-offs where you need the user's priorities
- Confirming your understanding before significant work
- Any moment where the user's input would change the outcome

Do NOT use this for:
- Questions you could answer by reading the code
- Confirmation of obvious or trivial choices
- Rubber-stamping work you've already decided on

## Before you ask anything

You must have already explored the relevant code, documentation, and
context. If you haven't, stop and do that first. The quality of your
questions is the primary signal of whether you understand the problem.
Generic questions -- ones that could apply to any project -- reveal that
you haven't done the work.

## Principles

### 1. Curate ruthlessly

Not every decision needs user input. Filter for **high-leverage
decisions** -- ones where:

- The user's domain knowledge or preferences would change the answer
- Multiple approaches are genuinely viable and the trade-offs are real
- Getting it wrong would be costly to undo

If you can make a confident choice yourself, make it and move on. Mention
it in passing ("I went with X because Y") rather than asking.

### 2. Lead with a recommendation

For each question, state which option you'd pick and why. This:
- Shows you've thought it through
- Gives the user something concrete to react to
- Lets them say "yes" quickly when they agree

But don't be precious about it. The recommendation is a starting point,
not a conclusion.

### 3. Falsify your own recommendation

After presenting your recommendation, actively surface its weaknesses:

- "The main risk with this approach is..."
- "This works well for X, but if Y matters more to you..."
- "The trade-off is that we'd lose..."

This is not about hedging. It's about giving the user the information
they need to push back effectively. If you only present the strengths,
you're selling, not consulting.

### 4. Options demonstrate understanding

Every option you present must be **tailored to this specific codebase**.
The user should be able to tell from your options alone that you
understand their project, its conventions, and its constraints.

Bad (generic): "Should we use a database or a file?"
Good (specific): "The project already uses append-only JSONL for logging.
We could follow that pattern here, or use SQLite if we need querying --
but that adds a dependency the project doesn't currently have."

### 5. Group related decisions

Use AskUserQuestion with up to 4 questions per call. Group decisions
that:
- Are about the same feature or subsystem
- Have dependencies (answering one constrains the others)
- Can be reasoned about together

Progress from **high-level architectural decisions** down to
**implementation details**. Don't ask about details until the big
picture is settled.

### 6. Highlight where the human matters most

Frame each question around WHY you need the user's input specifically:

- Preference-driven: "This comes down to whether you value X or Y more"
- Domain knowledge: "You know the usage patterns better than I can infer"
- Risk tolerance: "This is a trade-off between safety and flexibility"

The user should understand not just WHAT you're asking, but WHY their
answer matters and can't be determined from the code alone.

## Format

Use AskUserQuestion with structured options:

- **2-4 options** per question, each with a concise label and description
- **Mark your recommendation** with "(Recommended)" in the label
- **Descriptions** should cover trade-offs specific to this codebase
- **"Other"** is always available automatically -- don't add it

Keep descriptions tight. One sentence on what the option does, one on
the trade-off. The user doesn't need an essay.

## After the user responds

Acknowledge their choice briefly and adapt your plan. If they chose
something you didn't recommend, adjust without resistance -- they have
context you don't. If their choice invalidates downstream decisions
you were going to ask about, update those before presenting them.
