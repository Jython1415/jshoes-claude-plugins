---
name: reflect
description: >
  End-of-session retrospective. Scans JSONL transcript via subagents using
  evidence-based checklists to identify session learnings -- user corrections,
  execution failures, approach pivots, undocumented discoveries, and repeated
  operations -- then proposes concrete improvements to docs, skills, and
  memory. Use at the end of a session or after notable missteps or discoveries.
argument-hint: "[--light] [--heavy]"
---

# Reflect

Extract lessons from the current session and turn them into durable
improvements. This skill scans the session transcript via subagents with
evidence-based checklists, identifying findings that should be persisted to
docs, skills, and memory.

## When to use this

- End of a productive session, before context is lost
- After a session with notable missteps or discoveries
- When you notice patterns that should be codified
- The user asks you to wrap up or reflect

## Arguments

- `--light`: Single-agent Haiku scanner. One Haiku subagent scans the JSONL
  with 5 boolean checklists. Use for cost-sensitive reflection.
- `--heavy`: Dual-agent Sonnet pipeline. Two Sonnet subagents scan independently,
  main agent synthesizes both outputs. Redundancy catches more findings.
- Default (no flag): Single Sonnet scanner.

## Step 1: Scan the JSONL transcript

The main agent orchestrates the scan using subagents. The subagents read the
session's JSONL transcript directly via nonce-based session identification,
filter events, and apply 5 boolean signal checklists.

### Main agent tasks

1. Generate a nonce: run `echo "REFLECT_SCAN_MARKER_{uuid}"` via Bash. This marks
   a point in the transcript for the scanner to find.

2. For `--light`: Launch 1 Haiku subagent with the scanner instructions (see below).
   For default: Launch 1 Sonnet subagent. For `--heavy`: Launch 2 Sonnet subagents
   in parallel.

3. Pass the nonce string and the full scanner instructions to each subagent.
   The subagent is self-contained -- it does NOT inherit your conversation context.
   It only sees the instructions you pass.

4. For `--heavy`: receive both subagent outputs and synthesize directly. Handle
   duplicates by noting them once, merge unique findings, and use your judgment
   when confidence scores disagree.

### Scanner subagent instructions

Pass this block verbatim to the subagent prompt:

---

**JSONL Transcript Scanner Instructions**

You are scanning a session's JSONL transcript for evidence-based findings.

**Session identification (nonce-based)**

Derive the project directory from your current working directory:

```bash
PROJECT_DIR="$HOME/.claude/projects/$(echo "$PWD" | sed 's|/|-|g; s|_|-|g')"
```

The nonce string is: `{NONCE}`. Grep all JSONL files in the project directory
for this nonce:

```bash
grep -l "{NONCE}" "$PROJECT_DIR"/*.jsonl
```

The matching file is the current session's transcript. If no match is found (nonce
not yet flushed to disk), fall back to the most-recently-modified JSONL file with
a UUID-pattern filename (12-36 character hex strings).

**JSONL filtering**

Extract relevant events. If jq is available, use:

```bash
jq -c 'select(
  .type == "user" or
  .type == "assistant" or
  (.type == "system" and .subtype == "compact_boundary")
)' "$TRANSCRIPT" > "$FILTERED"
```

If jq is not available, use Python or grep to extract the same events.

From assistant messages: keep text blocks, drop thinking blocks. Keep ALL tool_use
blocks (name + input). Keep tool results but truncate output to first 500 characters.

**Exception**: Keep FULL output for:
- AskUserQuestion tool calls (these are direct user interactions)
- Tool calls that returned errors

Drop: progress events, file-history-snapshot, pr-link, queue-operation, last-prompt,
and system events (except compact_boundary).

**Segmentation**

Find compact_boundary markers in the filtered transcript. Default: scan from the
last compact_boundary to EOF (current segment). If no compact_boundary exists:
scan the entire file. If the segment exceeds context budget: truncate from the
beginning, keeping the most recent content.

**Signal scanning (5 boolean checklists)**

Apply each checklist to the segment. Record all findings (do NOT drop low-confidence
items). For each finding, include: signal_type, description, evidence, confidence
(0.0-1.0), and suggested_persistence_target.

#### Checklist 1: User Corrections

Signals that the user redirected, corrected, or disagreed with the approach.

| Signal | How to verify in JSONL |
|--------|----------------------|
| User chose "Other" on AskUserQuestion | AskUserQuestion tool result contains user-typed text instead of a predefined option label |
| User message contains correction language | User message includes phrases like "no", "don't", "instead", "actually", "wrong", "not what I", "I said" in context of redirecting Claude's approach |
| User repeated a prior instruction | Similar directive content appears in 2+ user messages (the user had to say it again) |
| User asked to undo/revert | User message mentions "undo", "revert", "go back", "restore", "roll back" |
| User rejected a proposed plan or approach | User message explicitly declines a suggestion ("skip that", "don't do that", "let's not") |

#### Checklist 2: Execution Failures

Signals that tool calls failed, errored, or needed retries.

| Signal | How to verify in JSONL |
|--------|----------------------|
| Bash command returned non-zero exit | Tool result contains error output, stderr, or non-zero exit code |
| Same Bash command run 2+ times with modifications | Similar command strings in consecutive Bash tool_use blocks with small edits (retry pattern) |
| Any tool call returned an explicit error | Tool result contains "error" field or error-indicating content |
| Edit/Write to same file 3+ times | Same file path appears in 3+ Edit or Write tool_use inputs |
| Agent/Task subagent launched for same purpose twice | Two Agent tool calls with similar description/prompt (re-launch after failure) |

#### Checklist 3: Approach Pivots

Signals that the strategy changed significantly mid-task.

| Signal | How to verify in JSONL |
|--------|----------------------|
| Branch created then abandoned | git checkout -b or git branch command without corresponding push to that branch |
| Assistant explicitly stated changing approach | Assistant text contains pivot language: "let me try a different", "actually I should", "on second thought", "that won't work" |
| File created then deleted in same session | Write tool for a path followed by Bash rm of the same path |
| Plan was revised after initial presentation | A plan/approach was presented, then a materially different plan was presented later |

#### Checklist 4: Undocumented Discoveries

Signals that new information was learned that isn't captured in project docs.

| Signal | How to verify in JSONL |
|--------|----------------------|
| WebFetch/WebSearch produced actionable results | WebFetch or WebSearch tool was called and the result informed a decision or implementation |
| API/tool behavior discovered that wasn't documented | Assistant text describes discovering unexpected behavior ("turns out", "discovered that", "didn't expect") |
| Workaround needed for tooling limitation | A limitation was encountered and worked around (sandbox restriction, tool limitation, etc.) |
| Convention or pattern inferred from codebase exploration | Assistant identified a pattern from reading code that isn't in CLAUDE.md or docs |

#### Checklist 5: Repeated Operations

Signals that a pattern was used multiple times and could be codified.

| Signal | How to verify in JSONL |
|--------|----------------------|
| Same tool call sequence repeated 3+ times | A sequence of 2+ tool calls appears in the same order 3+ times |
| Same Bash command template used with different parameters | Similar Bash commands differing only in arguments/paths |
| Same file structure created multiple times | Write tool creates files following the same naming/structure pattern |
| Manual multi-step process that could be a script or skill | 5+ sequential tool calls achieving a single logical operation that could be automated |

**Output format**

Return ALL findings using this structure. Do NOT filter by confidence:

```
## Finding: [brief title]
- **Signal type**: [user_correction | execution_failure | approach_pivot | undocumented_discovery | repeated_operation]
- **Confidence**: [0.0-1.0]
- **Evidence**: [direct quote or reference from transcript]
- **What happened**: [1-2 sentence description]
- **Suggested target**: [docs | skills | memory | skip]
- **Why persist**: [1 sentence on why this is worth remembering]
```

If fewer than 2 findings survive the scan:

```
Clean session -- nothing to persist.
[Brief note: N user messages, M tool calls, K segments scanned]
```

---

## Step 2: Categorize findings

Receive the scanner output (or both outputs if `--heavy`). Map each finding to
a persistence target:

- **Documentation** (CLAUDE.md, DEVELOPMENT.md, etc.): Architecture decisions,
  conventions, gotchas, and module reference updates
- **Skills** (.claude/skills/): Workflow patterns, updates to existing skills,
  or new skills that codify multi-step processes
- **Memory** (MEMORY.md, topic files): Project-specific learnings, user preferences,
  tool behavior quirks, and open issue tracking updates
- **Skip**: One-time events, already-documented learnings, or transient insights

## Step 3: Propose changes

Pack all proposed changes into a **single AskUserQuestion call** with up to 4
questions -- one per proposed change. Each question is independent; the user
can answer them simultaneously.

For each question:

- **question text**: One sentence naming the insight and why it matters. No file
  paths, no literal diff text -- keep it scannable.
- **header**: 2--4 word tag (e.g., "Push rule", "Recovery note")
- **Options are the possible destinations**, not approve/skip. The recommended
  option goes first (add "(Recommended)" to its label). List remaining alternatives
  after. "File a GitHub issue" is valid when the insight needs design work before
  documentation.
- **option description**: Include the literal change (absolute file path + section
  + text to add or replace). This is where detail lives -- not the question text.

Example:

```
AskUserQuestion(questions=[
  {
    question: "Always push immediately after committing directly to main.",
    header: "Push rule",
    options: [
      {
        label: "Save to reflect SKILL.md (Recommended)",
        description: "plugins/dev-workflow/skills/reflect/SKILL.md, Step 4 -- add: 'Commit directly to main and push immediately.'"
      },
      { label: "Save to CLAUDE.md", description: "~/.claude/CLAUDE.md -- add under Workflow section." },
      { label: "Skip -- not worth persisting", description: "One-time event, not a recurring pattern." }
    ]
  },
  {
    question: "Run git show before git reset --hard to verify the squash captured the diverged commit.",
    header: "Recovery note",
    options: [
      {
        label: "Save to MEMORY.md (Recommended)",
        description: "MEMORY.md, Workflow Notes -- add: '- git show <sha> --stat before git reset --hard origin/main'"
      },
      { label: "Save to CLAUDE.md", description: "~/.claude/CLAUDE.md -- add under Safety section." },
      { label: "Skip -- not worth persisting", description: "Already obvious from context." }
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
4. **Check branching policy before committing.** Scan convention documents in
   the repo root (CLAUDE.md, CONTRIBUTING.md, README.md, DEVELOPMENT.md, and
   similar) for a "never commit to main" or "always use a feature branch" policy.
   - **Policy found**: Create a feature branch (e.g., `reflect/YYYYMMDD`), commit,
     push, and open a PR.
   - **No such policy**: Commit directly to main and push -- docs, skills, and
     memory are guidance, not runtime code. Lightweight commit paths encourage
     actually running /reflect rather than skipping it.

## Principles

- **Evidence over narrative.** Every finding must cite a specific transcript event.
  "I think we learned X" without evidence is not a finding.
- **Repo-specific over generic.** Generic advice ("use descriptive variable names")
  is useless. Only persist specific gotchas that prevent real mistakes.
- **Document the WHY, not just the WHAT.** "Don't use method X" is less useful
  than "Don't use method X because it silently drops errors in production." The
  reasoning prevents rules from being blindly overridden later.
- **Confidence is informational.** The scanner marks confidence but never drops
  findings. You decide what to surface. Low-confidence findings may still be
  worth persisting if the reasoning is sound.
- **Don't hoard.** Not everything is worth persisting. A one-time debugging
  insight for a bug that's now fixed doesn't need to live forever. Prune
  aggressively.
