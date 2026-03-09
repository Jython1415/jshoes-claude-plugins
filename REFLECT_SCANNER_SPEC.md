# Spec: Reflect Scanner — SubagentStart Hook Injection

**Issue**: #202 — reflect scanner chunks exceed single-Read budget
**Date**: 2026-03-09
**Status**: Draft

## Problem

The `/reflect` skill chunks session transcripts and spawns Haiku scanner
agents to analyze each chunk. Scanners currently read their chunk via the
Read tool, which has a hard 25K-token limit per call. Chunks target 20K
tokens but routinely exceed this due to overlap padding and oversized lines.
When this happens, Haiku scanners degrade: they attempt multi-read pagination
(4-15 Read calls), lose context, and produce empty or incomplete findings.

The current architecture forces a tension between **chunk size** (larger =
fewer scanners, cheaper, better cross-turn context) and **Read tool limits**
(25K hard cap). This spec resolves that tension by eliminating the Read tool
from the scanner entirely.

## Solution Overview

Inject transcript chunk content directly into each scanner's context via a
**SubagentStart hook**, bypassing the Read tool entirely. Scanners become
**zero-tool analytical agents**: instructions at the top (agent definition),
transcript data in the middle (additionalContext), and a repeated scanning
prompt at the bottom (also additionalContext).

Chunk size increases from 20K to **80K tokens** — within Haiku's effective
context range (200K window, ~15-19K overhead, leaving ~100K for content +
analysis).

## Architecture

```
reflect-filter.py                    SubagentStart Hook
┌──────────────────────┐            ┌──────────────────────────┐
│ 1. Parse transcript   │            │ Fires for agent_type     │
│ 2. Segment + filter   │            │ matching "reflect-scanner"│
│ 3. Chunk at 80K token │            │                          │
│    budget             │            │ 1. flock queue file      │
│ 4. Write chunk files  │            │ 2. Pop next chunk path   │
│ 5. Write queue file   │──────────► │ 3. Read chunk (Python    │
│    (.reflect-scan-    │            │    file I/O — no CC      │
│     {nonce}-queue.txt)│            │    Read tool limit)      │
│ 6. Output manifest    │            │ 4. Wrap in structured    │
└──────────────────────┘            │    markers + trailing    │
                                    │    scanning prompt       │
Main Agent                          │ 5. Return as             │
┌──────────────────────┐            │    additionalContext     │
│ 1. Run filter script  │            └──────────────────────────┘
│ 2. Parse manifest     │                       │
│ 3. Spawn N scanners:  │                       ▼
│    Agent(             │              Scanner (Haiku)
│      type: "reflect-  │         ┌──────────────────────────┐
│       scanner",       │         │ Context at spawn:        │
│      prompt: "Scan    │         │ ┌────────────────────┐   │
│       chunk N")       │         │ │ System prompt       │   │
│ 4. Collect findings   │         │ │ (agent definition   │   │
│ 5. Synthesize         │         │ │  + 4 checklists)    │   │
└──────────────────────┘         │ ├────────────────────┤   │
                                  │ │ additionalContext   │   │
                                  │ │ - section header    │   │
                                  │ │ - 80K JSONL content │   │
                                  │ │ - trailing prompt   │   │
                                  │ ├────────────────────┤   │
                                  │ │ User message        │   │
                                  │ │ (Agent prompt:      │   │
                                  │ │  "Scan chunk N")    │   │
                                  │ └────────────────────┘   │
                                  │                          │
                                  │ Zero tools. Pure         │
                                  │ text-in, text-out.       │
                                  │ Returns findings.        │
                                  └──────────────────────────┘
```

## Detailed Changes

### 1. `reflect-filter.py`

**File**: `plugins/dev-workflow/skills/reflect/scripts/reflect-filter.py`

#### 1a. Increase chunk budget

```python
# Before
max_chunk_tokens = 20_000
overlap_pct = 0.10

# After
max_chunk_tokens = 80_000
overlap_pct = 0.05
```

**Rationale**: 80K tokens is 40% of Haiku's 200K context. With ~4K overhead
(system prompt with zero tools + environment metadata) and the scanning
prompt repeated in additionalContext (~500 tokens), the scanner has ~115K
tokens remaining for its analysis and output. The overlap drops from 10% to
5% because at 80K per chunk, 5% overlap (4K tokens) already provides
substantial cross-chunk context for detecting approach pivots that span
chunk boundaries.

#### 1b. Write queue file

After writing chunk files, write a queue file listing chunk paths in order.
For `--heavy` mode, each path appears twice (two scanners per chunk).

```python
# New: write queue file after chunk files
queue_file = os.path.join(pwd, f".reflect-scan-{nonce_prefix}-queue.txt")
with open(queue_file, "w") as f:
    for job_type, filepath, line_count in scanner_jobs:
        f.write(filepath + "\n")
```

The queue file path is included in the manifest output so the main agent
knows where it is (for documentation/debugging), but the main agent doesn't
interact with it directly — the hook does.

#### 1c. Include queue file in cleanup

The cleanup command in the manifest and the `atexit` handler already cover
the queue file. The existing glob pattern `.reflect-scan-{nonce}-*` matches
it since the queue file follows the naming convention:
`.reflect-scan-{nonce}-queue.txt`.

#### 1d. Post-creation validation (optional hardening)

After writing chunk files, verify each chunk is within budget:

```python
for chunk_idx, (start_line, end_line) in enumerate(chunks):
    chunk_lines = detail_lines[start_line:end_line]
    chunk_tokens = count_lines_tokens(chunk_lines, encoding)
    if chunk_tokens > max_chunk_tokens:
        print(
            f"WARNING: chunk {chunk_idx} is {chunk_tokens} tokens "
            f"(budget: {max_chunk_tokens})",
            file=sys.stderr,
        )
```

At 80K budget this is less critical (no hard Read limit to hit), but useful
for monitoring. A warning is sufficient — no re-splitting needed since the
scanner's context window (200K) can absorb overages.

### 2. SubagentStart Hook

**New file**: `plugins/dev-workflow/hooks/reflect-scanner-inject.py`

A Python hook script (PEP 723, no external dependencies) that fires on
SubagentStart for `reflect-scanner` agents. It reads the next chunk file
from the queue and injects the content as `additionalContext`.

#### Input

The hook receives JSON on stdin:

```json
{
  "session_id": "...",
  "hook_event_name": "SubagentStart",
  "agent_type": "reflect-scanner",
  "agent_id": "agent-...",
  "cwd": "/path/to/project",
  "transcript_path": "..."
}
```

#### Logic

1. Check `agent_type` — if not `reflect-scanner`, output `{}` and exit.
2. Find queue file: glob for `.reflect-scan-*-queue.txt` in `cwd`.
   - If no queue file found, output `{}` (scanner will report error).
3. Acquire exclusive lock (`flock`) on the queue file.
4. Read all lines, pop the first line (chunk file path).
5. Write remaining lines back, release lock.
6. Read the chunk file using Python `open()` (no Claude Code limits).
7. Construct the additionalContext string (see format below).
8. Output JSON to stdout.

#### additionalContext Format

```
## Transcript Chunk

The following is your assigned transcript chunk in JSONL format. Each line
is a JSON object representing one conversation event (user message, assistant
response, or system event). Analyze this data using the 4 checklists defined
in your instructions above.

---

{raw JSONL content — one event per line}

---

## Your Task

You have received the complete transcript chunk above. Now apply all 4
checklists to this data:

1. **User Corrections** — Where did the user redirect, correct, or disagree?
2. **Execution Failures** — Which tool calls failed, errored, or needed retries?
3. **Approach Pivots** — Where did the strategy change significantly?
4. **Codifiable Patterns** — What patterns were used repeatedly?

Report each finding using the structured format from your instructions.
If fewer than 2 findings survive, report "Clean session — nothing to persist"
with approximate message and tool call counts.
```

#### Output

```json
{
  "hookSpecificOutput": {
    "hookEventName": "SubagentStart",
    "additionalContext": "## Transcript Chunk\n\nThe following is..."
  }
}
```

If queue is empty or file not found:

```json
{}
```

#### Error Handling

- **No queue file**: Output `{}`. Scanner will detect missing data and
  report an error.
- **Empty queue**: Output `{}`. Same behavior.
- **Chunk file not found**: Output `{}` with a warning to stderr.
- **flock timeout**: Use a 10-second timeout. If lock can't be acquired,
  output `{}` and log to stderr.
- **Any exception**: Catch at top level, output `{}`, log to stderr.
  Never crash — a crashing hook blocks the subagent spawn.

#### Concurrency

Multiple scanners may spawn in parallel from a single response. The hook
uses `fcntl.flock(LOCK_EX)` for mutual exclusion on queue file access.
This ensures each scanner gets a unique chunk even under concurrent spawns.

FIFO ordering: the queue file is written in chunk order by reflect-filter.py.
Scanners pop from the front. The first scanner spawned gets chunk 0, the
second gets chunk 1, etc. If spawning order differs from queue order, scanners
still get unique chunks — just potentially in different order. This is fine
because scanners are independent.

### 3. Hook Registration

**New file**: `plugins/dev-workflow/hooks/hooks.json`

```json
{
  "hooks": {
    "SubagentStart": [
      {
        "matcher": "reflect-scanner",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --script \"${CLAUDE_PLUGIN_ROOT}/hooks/reflect-scanner-inject.py\""
          }
        ]
      }
    ]
  }
}
```

The matcher `reflect-scanner` matches the agent's `name` field from the
agent definition frontmatter. This fires only for reflect scanner spawns,
not for any other subagent type.

### 4. Scanner Agent Definition Rewrite

**File**: `plugins/dev-workflow/agents/reflect-scanner.md`

Major changes:

- **`tools: []`** — Zero tools. Pure text-in, text-out.
- **Remove all Read instructions** — No file reading, no pagination, no
  offset/limit.
- **Add context-injection awareness** — Scanner expects transcript data
  in its context (injected by SubagentStart hook).
- **Add failure detection** — If no transcript data is present, report
  error instead of silently producing nothing.
- **Keep all 4 checklists unchanged** — The scanning logic is the same;
  only the data delivery mechanism changes.

#### Updated Frontmatter

```yaml
---
name: reflect-scanner
description: >
  Scans a pre-processed Claude Code session transcript for evidence-based
  findings using 4 judgment-based checklists. Zero-tool agent — transcript
  data is pre-loaded into context via SubagentStart hook. Used by the
  /reflect skill.
tools: []
---
```

#### Updated Instructions Section

Replace the "Reading your assigned file" section with:

```markdown
## How You Receive Data

Your transcript chunk has been pre-loaded into your context as a system
reminder by the SubagentStart hook. You do NOT need to read any files.
Look for the section marked "## Transcript Chunk" in your context — that
contains the JSONL data to analyze.

**If no transcript data appears in your context**, report:

ERROR: No transcript data injected. The SubagentStart hook may have
failed. Check that the dev-workflow plugin hooks are registered and
that the queue file exists.

**Do NOT attempt to use any tools.** You have no tool access. Your entire
job is to analyze the transcript data already in your context and report
findings.
```

#### Checklists and Output Format

**No changes.** The 4 checklists (User Corrections, Execution Failures,
Approach Pivots, Codifiable Patterns) and the output format remain identical.

### 5. SKILL.md Updates

**File**: `plugins/dev-workflow/skills/reflect/SKILL.md`

#### Scanner launch instructions (Step 1, item 4)

Update the scanner launch example:

```markdown
- For each scanner job line, launch an Agent with
  `subagent_type: "dev-workflow:reflect-scanner"`
- The scanner receives its transcript chunk automatically via the
  SubagentStart hook — do NOT include file paths in the prompt
- The prompt should contain ONLY a brief assignment identifier
- For `--light`: pass Haiku model for scanners
- For default/`--heavy`: pass Sonnet model for scanners
- Launch all scanners in parallel where possible

**Example scanner launch:**

Agent(
  subagent_type: "dev-workflow:reflect-scanner",
  description: "Scan transcript chunk 0",
  prompt: "Perform a DETAIL scan on the transcript chunk in your context. You are scanner 0."
)
```

#### Remove file path references

The scanner prompt no longer includes file paths. The hook handles data
delivery. The main agent's only job is to spawn scanners and collect results.

## Token Budget Analysis

### Per-Scanner Context Breakdown (Haiku, 200K window)

| Component | Estimated Tokens | Notes |
|-----------|-----------------|-------|
| System prompt (agent def) | ~3,000 | Checklists + instructions |
| Tool definitions | ~0 | Zero tools = zero overhead |
| Environment metadata | ~1,000 | cwd, permissions, session |
| additionalContext header | ~200 | Section markers |
| Transcript chunk | ~80,000 | Target budget |
| additionalContext trailer | ~300 | Repeated scanning prompt |
| User message (Agent prompt) | ~50 | "Perform a DETAIL scan..." |
| **Total input** | **~84,550** | **42% of 200K** |
| Remaining for output | ~115,450 | Ample for findings |

### Cost Comparison

Assuming a 200K-token session transcript:

| Configuration | Chunks | Scanners | Input tokens/scanner | Total input |
|--------------|--------|----------|---------------------|-------------|
| Current (20K) | ~10 | 10 | ~25K (with overhead) | ~250K |
| Proposed (80K) | ~3 | 3 | ~85K (with overhead) | ~255K |
| Proposed heavy | ~3 | 6 | ~85K (with overhead) | ~510K |

Total token costs are comparable. The proposed design uses fewer scanners
with larger inputs — net cost is similar, but with better analytical
quality per scanner (more context = better pattern detection) and fewer
agent spawn overheads.

## Queue File Specification

### Format

Plain text file, one absolute file path per line:

```
/path/to/project/.reflect-scan-abc12345-detail-0.jsonl
/path/to/project/.reflect-scan-abc12345-detail-1.jsonl
/path/to/project/.reflect-scan-abc12345-detail-2.jsonl
```

For `--heavy` mode, paths are doubled:

```
/path/to/project/.reflect-scan-abc12345-detail-0.jsonl
/path/to/project/.reflect-scan-abc12345-detail-0.jsonl
/path/to/project/.reflect-scan-abc12345-detail-1.jsonl
/path/to/project/.reflect-scan-abc12345-detail-1.jsonl
```

### Naming Convention

```
.reflect-scan-{nonce_prefix}-queue.txt
```

Lives in `cwd` alongside chunk files. Matched by the existing cleanup
glob pattern `.reflect-scan-{nonce_prefix}-*`.

### Lifecycle

1. **Created by**: `reflect-filter.py` after writing all chunk files
2. **Consumed by**: SubagentStart hook (pop-from-front on each scanner spawn)
3. **Cleaned up by**: The manifest cleanup command (`rm -f .reflect-scan-{nonce}-*`)
   and the `atexit` crash handler

## Edge Cases

### 1. Small transcripts (< 80K tokens total)

No chunking needed. Single chunk file + single queue entry. One scanner.
Behavior identical to current implementation except data delivery is via
hook instead of Read.

### 2. Very large transcripts (> 400K tokens)

Produces 5+ chunks. Each scanner still gets ~80K tokens. Cost scales
linearly. The 200-chunk hard cap in reflect-filter.py prevents runaway
chunking (would require a 16M+ token transcript to hit).

### 3. Hook doesn't fire (plugin not installed)

Scanner receives no transcript data in context. Scanner detects this and
reports the error message defined in its agent definition. Main agent
sees the error and can surface it to the user.

### 4. Queue exhausted before all scanners spawn

If more scanners are spawned than queue entries (shouldn't happen if
reflect-filter.py and SKILL.md are in sync), later scanners get empty
`additionalContext` from the hook (empty queue = output `{}`). Scanner
reports the missing-data error.

### 5. Concurrent scanner spawns

Handled by `fcntl.flock(LOCK_EX)`. Each spawn atomically pops one entry.
No race conditions. Order may differ from queue order, but this is
acceptable — scanners are independent.

### 6. Chunk file deleted before hook reads it

Could happen if cleanup runs prematurely. Hook catches `FileNotFoundError`,
outputs `{}`, logs warning to stderr. Scanner reports missing-data error.

## Files Changed

| File | Change Type | Description |
|------|------------|-------------|
| `plugins/dev-workflow/skills/reflect/scripts/reflect-filter.py` | Modify | 80K budget, 5% overlap, write queue file, optional validation |
| `plugins/dev-workflow/hooks/reflect-scanner-inject.py` | **New** | SubagentStart hook: queue pop + chunk injection |
| `plugins/dev-workflow/hooks/hooks.json` | **New** | Hook registration for reflect-scanner |
| `plugins/dev-workflow/agents/reflect-scanner.md` | Modify | Zero-tool rewrite, remove Read, add context-injection instructions |
| `plugins/dev-workflow/skills/reflect/SKILL.md` | Modify | Update scanner launch instructions, remove file path refs |
| `plugins/dev-workflow/.claude-plugin/plugin.json` | Modify | Version bump |
| `plugins/dev-workflow/CHANGELOG.md` | Modify | New entry |

## Version

This is a minor version bump: **2.3.0 → 2.4.0**

- New hook added (new capability)
- Scanner agent redesigned (changed interface)
- Chunk budget changed (changed behavior)
- No breaking changes to the `/reflect` skill's public interface

## Testing Strategy

### 1. Hook unit test

Test `reflect-scanner-inject.py` directly:

```bash
# Create mock queue and chunk files
echo "/tmp/test-chunk-0.jsonl" > /tmp/test-queue.txt
echo '{"type":"user","message":{"content":"test"}}' > /tmp/test-chunk-0.jsonl

# Simulate SubagentStart input
echo '{"hook_event_name":"SubagentStart","agent_type":"reflect-scanner","cwd":"/tmp"}' \
  | uv run --script plugins/dev-workflow/hooks/reflect-scanner-inject.py
```

Verify: output contains `additionalContext` with chunk content wrapped
in structured markers.

### 2. Queue concurrency test

Spawn 5 concurrent hook invocations against a 5-entry queue. Verify each
gets a unique chunk path (no duplicates, no gaps).

### 3. Integration test

Run `/reflect --light` on a session with a transcript large enough to
produce 2+ chunks (>80K tokens after filtering). Verify:
- Filter script produces correct chunk count
- Queue file is created with correct entries
- Scanners receive data and produce findings
- Cleanup removes all intermediate files

### 4. Failure mode tests

- Run hook with no queue file → outputs `{}`
- Run hook with empty queue file → outputs `{}`
- Run hook with non-reflect-scanner agent_type → outputs `{}`
- Run hook with missing chunk file → outputs `{}`, logs warning

## Open Questions

None remaining. All design decisions resolved during research phase.
