---
name: reflect
description: >
  End-of-session retrospective. Scans JSONL transcript via a bundled filter
  script and scanner agents using evidence-based checklists to identify session
  learnings — user corrections, execution failures, approach pivots, and
  codifiable patterns — then proposes concrete improvements to docs, skills,
  and memory. Use at the end of a session or after notable missteps or discoveries.
argument-hint: "[--light] [--heavy] [--full]"
---

# Reflect

Extract lessons from the current session and turn them into durable improvements. This skill scans the session transcript via a bundled filter script and scanner agents with evidence-based checklists, identifying findings that should be persisted to docs, skills, and memory.

## Why this exists

Sessions produce learnings that prevent repeated mistakes, codify patterns, and improve future sessions. Without explicit reflection, insights are lost when context resets. The /reflect skill turns ephemeral session knowledge into durable project improvements.

## Your role

You are the editor — scanners are evidence gatherers. They extract raw findings from the transcript. You decide what matters, where it goes, and how to present it to the user. This requires understanding the project, its docs, and what's already documented.

A good finding is: specific to this repo (not generic advice), actionable (can be written into a doc or skill), and durable (will matter in future sessions, not just this one).

## When to use this

- End of a productive session, before context is lost
- After a session with notable missteps or discoveries
- When you notice patterns that should be codified
- The user asks you to wrap up or reflect

## Arguments

- `--light`: Haiku scanners. Lower cost, still effective for straightforward sessions.
- `--heavy`: Double the detail scanners (2x Sonnet). Redundancy catches more findings.
- `--full`: Scan entire transcript, not just the current segment. Useful for long sessions with important early context.
- Default (no flag): Single Sonnet scanner per chunk.

## Persistence target hierarchy

When deciding where a finding should go, promote as broadly as it's useful:

1. **Project documentation** (README, CONTRIBUTING, DEVELOPMENT, etc.) — Findings that benefit all contributors. Architecture decisions, conventions, gotchas.
2. **Plugin/agent architecture** (SKILL.md files, agent definitions, hook code) — Findings that improve the tools themselves. Workflow improvements, skill refinements.
3. **CLAUDE.md / AGENTS.md** — Findings that affect how Claude operates in this repo. Workflow rules, safety constraints, behavioral guidelines.
4. **MEMORY.md / topic files** — Project-specific quirks, user preferences, tool behavior discoveries. The most narrow scope.

**Skip**: One-time fixes, already-documented items, transient debugging insights for bugs that are now fixed.

## Step 1: Filter and scan

1. Generate a nonce:
   ```bash
   echo "REFLECT_SCAN_MARKER_$(uuidgen)"
   ```

2. Run the bundled filter script:
   ```bash
   uv run --script ${CLAUDE_SKILL_DIR}/scripts/reflect-filter.py --nonce $NONCE --mode $MODE [--full]
   ```
   Where `$MODE` is `light`, `default`, or `heavy` based on the flag passed.

3. Parse the manifest output. It lists scanner jobs (file paths + scan types) and a cleanup command.

4. Launch scanner agents per the manifest:
   - For each scanner job line, launch an Agent with `subagent_type: "dev-workflow:reflect-scanner"`
   - The scanner agent definition already includes all checklists — do NOT repeat them in the prompt
   - The prompt should contain ONLY the assignment: file path and scan type
   - For `--light`: pass Haiku model for scanners
   - For default/`--heavy`: pass Sonnet model for scanners
   - Launch all scanners in parallel where possible

   **Example scanner launch for a detail scan:**
   ```
   Agent(
     subagent_type: "dev-workflow:reflect-scanner",
     description: "Scan transcript chunk 0",
     prompt: "Your assignment: Read the file at /absolute/path/to/.reflect-scan-abc12345-detail-0.jsonl and perform a DETAIL scan."
   )
   ```

   **Example for a high-level scan:**
   ```
   Agent(
     subagent_type: "dev-workflow:reflect-scanner",
     description: "High-level transcript scan",
     prompt: "Your assignment: Read the file at /absolute/path/to/.reflect-scan-abc12345-summary.jsonl and perform a HIGH-LEVEL scan."
   )
   ```

   IMPORTANT: Always use absolute file paths in scanner prompts so scanners can find the files regardless of working directory.

5. After all scanners complete, run the cleanup command from the manifest to remove intermediate files.

## Step 3: Synthesize

Receive all scanner outputs. Merge findings:
- If two scanners report the same finding, keep it once with higher confidence
- If findings conflict, use your judgment
- Drop findings that are already documented in the project's CLAUDE.md, MEMORY.md, or other docs
- Drop findings that are generic advice rather than repo-specific insights

## Step 4: Propose

Present findings to the user via AskUserQuestion. Pack up to **4 findings per call**. Each question is independent; the user can answer them simultaneously.

For each question:
- **question text**: One sentence naming the insight and why it matters. No file paths or diffs — keep it scannable.
- **header**: 2-4 word tag (e.g., "Push rule", "Recovery note")
- **Options are persistence destinations**, not approve/skip. The recommended destination goes first (add "(Recommended)" to its label). Remaining alternatives follow. "File a GitHub issue" is valid when the insight needs design work.
- **option description**: Include the literal change (absolute file path + section + text to add/replace). This is where detail lives.

Include this example:

```
AskUserQuestion(questions=[
  {
    question: "Always push immediately after committing directly to main.",
    header: "Push rule",
    options: [
      {
        label: "Save to CLAUDE.md (Recommended)",
        description: "CLAUDE.md, Workflow section — add: 'After committing directly to main, push immediately.'"
      },
      { label: "Save to MEMORY.md", description: "MEMORY.md, Workflow Notes — add the same." },
      { label: "Skip — not worth persisting", description: "One-time event, not a recurring pattern." }
    ]
  }
])
```

Gather all answers before applying changes in Step 4.

## Step 5: Apply

Make the approved changes:

1. Edit documentation files
2. Update or create skill files
3. Update memory files
4. **Check branching policy before committing.** Scan convention documents in the repo root (CLAUDE.md, CONTRIBUTING.md, README.md, DEVELOPMENT.md) for a "never commit to main" or "always use a feature branch" policy.
   - **Policy found**: Create a feature branch (e.g., `reflect/YYYYMMDD`), commit, push, and open a PR.
   - **No such policy**: Commit directly to main and push.

## Principles

- **Evidence over narrative.** Every finding must cite a specific transcript event. "I think we learned X" without evidence is not a finding.
- **Repo-specific over generic.** Generic advice ("use descriptive variable names") is useless. Only persist specific gotchas that prevent real mistakes.
- **Document the WHY, not just the WHAT.** "Don't use method X" is less useful than "Don't use method X because it silently drops errors in production." The reasoning prevents rules from being blindly overridden later.
- **Confidence is informational.** The scanner marks confidence but never drops findings. You decide what to surface. Low-confidence findings may still be worth persisting if the reasoning is sound.
- **Don't hoard.** Not everything is worth persisting. A one-time debugging insight for a bug that's now fixed doesn't need to live forever. Prune aggressively.
