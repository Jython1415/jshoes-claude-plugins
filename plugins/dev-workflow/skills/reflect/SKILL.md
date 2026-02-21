---
name: reflect
description: >
  End-of-session retrospective. Reviews what happened, extracts lessons,
  and proposes concrete improvements to docs, skills, and memory to
  make future sessions better. Run before context is lost.
---

# Reflect

Extract lessons from the current session and turn them into durable
improvements. This skill exists because context disappears between
sessions -- if a learning isn't persisted, it's lost.

## When to use this

- End of a productive session, before context compaction
- After a session with notable missteps or discoveries
- When you notice patterns that should be codified
- The user asks you to wrap up or reflect

## Step 1: Review the session

Scan the current conversation for:

- **Missteps**: Where did you go wrong? What caused it? Could better
  docs, skills, or memory have prevented it?
- **Discoveries**: What did you learn about the codebase, tools, APIs,
  or workflows that wasn't documented?
- **Patterns**: What did you do repeatedly that could be codified into
  a convention, skill, or checklist?
- **User corrections**: Where did the user redirect you? These are the
  highest-signal improvements -- the user spent their time correcting
  something that should be self-correcting.
- **Tool/workflow friction**: Where did tooling slow you down or cause
  confusion? Are there gotchas worth recording?

Be honest. The value of this skill is proportional to your willingness
to identify what went wrong, not just what went well.

## Step 2: Categorize improvements

Sort findings into where they should be persisted:

### Documentation (CLAUDE.md, DEVELOPMENT.md, etc.)
- Architecture decisions and their rationale (especially WHERE Claude
  tends to diverge from the correct approach)
- Conventions that were discovered or clarified during the session
- Gotchas and footguns that cost time
- Module reference updates (new files, changed interfaces)

### Skills (.claude/skills/)
- Workflow patterns that were used successfully and should be repeatable
- Existing skills that need updates based on how they performed
- New skills that would codify a multi-step process you did manually

### Memory (MEMORY.md, topic files)
- Project-specific learnings and gotchas
- User preferences discovered during the session
- Tool behavior quirks
- Open issues tracking updates

### Nothing
Some findings don't need to be persisted. Don't force it. If a learning
is obvious, transient, or already documented, skip it.

## Step 3: Propose changes

Pack all proposed changes into a **single AskUserQuestion call** with up
to 4 questions — one question per proposed change. Each question is its
own independent panel; the user can answer them simultaneously rather
than sequentially.

For each question:

- **Show the exact change** in the question text: absolute file path,
  section heading, and the literal text to add or replace (not a
  paraphrase -- the user needs to see the actual content to approve
  efficiently)
- **Options are the possible destinations**, not approve/skip. The
  recommended option goes first (add "(Recommended)" to its label) —
  that may be a specific file, a GitHub issue, or "Skip — not worth
  persisting" if that's genuinely the right call. List remaining
  alternatives after. "File a GitHub issue" is a valid option when the
  insight needs design work before it can be documented
- **Include the motivation** (session event) and impact in the question
  or option descriptions

Example call structure for two insights:

```
AskUserQuestion(questions=[
  {
    question: "Save the 'always push after direct main commit' rule?\n\nFile: plugins/.../SKILL.md, Step 4\nAdd: 'Commit directly to main and push'",
    header: "Push rule",
    options: [
      { label: "Save to reflect SKILL.md (Recommended)", description: "..." },
      { label: "Save to CLAUDE.md", description: "..." },
      { label: "Skip — not worth persisting", description: "..." }
    ]
  },
  {
    question: "Save the recovery steps for a diverged local main?\n\nFile: MEMORY.md, Workflow Notes\nAdd: '- git show <sha> before git reset --hard'",
    header: "Recovery note",
    options: [
      { label: "Save to MEMORY.md (Recommended)", description: "..." },
      { label: "Save to CLAUDE.md", description: "..." },
      { label: "Skip — not worth persisting", description: "..." }
    ]
  }
])
```

Gather all answers before applying any changes in Step 4.

## Step 4: Apply

Make the approved changes:

1. Edit documentation files
2. Update or create skill files
3. Update memory files
4. Commit directly to main and push -- docs, skills, and memory are guidance,
   not runtime code. Keeping the commit path lightweight encourages
   actually running /reflect rather than skipping it.

## Principles

- **Repo-specific over generic.** Generic advice ("use descriptive
  variable names") is useless. Specific gotchas ("the API returns
  null for deleted records, not 404 -- check for null before accessing
  .data") prevent real mistakes. Only persist the latter.
- **Document the WHY, not just the WHAT.** "Don't use method X" is
  less useful than "Don't use method X because it silently drops
  errors in production." The reasoning prevents the rule from being
  blindly overridden later.
- **Anchor where Claude diverges.** The highest-value documentation
  captures places where the model predictably makes the wrong choice.
  If you went down a wrong path, document why the right path is right
  and why the wrong path looks tempting.
- **Keep docs concise.** Root CLAUDE.md should stay short and reference
  detailed files. MEMORY.md has a 200-line effective limit. Use
  progressive disclosure -- detailed notes go in topic files, summaries
  go in the index.
- **User corrections are gold.** If the user had to redirect you, that
  correction must be persisted. It's the clearest signal of a gap in
  your guidance.
- **Don't hoard.** Not everything is worth persisting. A one-time
  debugging insight for a bug that's now fixed doesn't need to live
  forever. Prune aggressively.
