# Changelog

## [2.10.0] - 2026-03-10

### Added

- `/spec` skill for writing lightweight specs on complex issues. Produces a temporary spec file (Problem, Definition of Done, Decisions, Approach) that survives conversation compaction. Auto-invoked by `/solve` Phase 3 when an issue is classified as "Needs design decisions". Also usable standalone.
- `/solve` Phase 3 now routes "Needs design decisions" issues through `/spec` instead of directly to `/consult`
- `/solve` Phase 4 uses spec file as primary planning input when available
- `/solve` Phase 5 deletes spec file in final commit (working artifact, not permanent docs)

## [2.9.0] - 2026-03-09

### Changed

- /code-review --light: consolidate two-stage Haiku+Sonnet pipeline into single Haiku agent (#217)

## [2.8.0] - 2026-03-09

### Changed

- /solve Phase 9: mandate /consult instead of conditional AskUserQuestion for pre-merge check-in (#216)

## [2.7.0] - 2026-03-09

### Added
- `/solve` Phase 9: re-read project convention docs before presenting PR for merge. Catches pre-merge, pre-deploy, and smoke-test requirements that were discovered during exploration but not re-verified before merge.

## [2.6.0] - 2026-03-09

### Added
- `/research` skill: systematic context-building through parallel research agents. Guides the orchestrator through multi-round research with light scaffolding for direction-finding, synthesis between rounds, and heuristic stop conditions. Feeds into /consult for design decisions.

## [2.5.0] - 2026-03-09

### Added
- `worktree-implementor` agent: isolated worktree execution agent designed for Haiku-tier models. Enforces commit-before-exit protocol to prevent work loss on worktree cleanup. Includes structured exit reporting (status, commit hash, files changed, warnings) for mechanical verification by the coordinator.

## [2.4.3] - 2026-03-09

### Changed
- `/reflect` filter script: Scanner Jobs header now includes explicit count (e.g., "7 scanners to launch") for clearer orchestration
- `/reflect` SKILL.md: Updated scanner launch instructions to reference the count in the header instead of asking orchestrators to count manifest lines manually

## [2.4.2] - 2026-03-09

### Changed
- `/reflect` SKILL.md: clarified that scanner count must exactly match manifest job lines to prevent accidentally skipping chunks. Added multi-scanner example to illustrate correct 5-job launch pattern.

## [2.4.1] - 2026-03-09

### Fixed
- `/reflect` SubagentStart hook matcher: changed from `"reflect-scanner"` to `"dev-workflow:reflect-scanner"` to match the full subagent_type string the CLI queries with (hook was never firing due to mismatch)
- `/reflect` filter script: queue file (`.reflect-scan-{nonce}-queue.txt`) is now written for all cases (single-chunk and multi-chunk), not just the multi-chunk branch
- `/reflect` scanner-inject hook: agent type check changed from `"reflect-scanner"` to `"dev-workflow:reflect-scanner"` for consistency with hook matcher

## [2.4.0] - 2026-03-09

### Changed
- `/reflect` filter script: increased per-chunk token budget from 20K to 80K tokens
- `/reflect` filter script: reduced overlap from 10% to 5% (at 80K chunks, 5% overlap provides sufficient cross-chunk context)
- `/reflect` filter script: added queue file output (`.reflect-scan-{nonce}-queue.txt`) listing chunk paths for scanner consumption
- `/reflect` filter script: added post-creation validation warnings for chunks exceeding budget
- `/reflect` scanner agent: converted to zero-tool agent (no tool access). Transcript chunks now injected via SubagentStart hook instead of Read tool
- `/reflect` scanner agent: removed Read tool instructions; added context-injection awareness and error detection for missing transcript data
- `/reflect` SKILL.md: updated scanner launch instructions to remove file path references (data delivery now handled by SubagentStart hook)

### Added
- `/reflect` SubagentStart hook (`reflect-scanner-inject.py`): pops chunk paths from queue file using file locking, reads chunks via Python I/O, injects content as additionalContext into scanner agents
- `/reflect` hook registration (`hooks.json`): registers SubagentStart hook for `reflect-scanner` agent type

## [2.3.0] - 2026-03-08

### Changed
- Lowered per-chunk token budget from 80K to 20K so scanner agents can read entire chunks in a single Read call (fixes #192)
- Removed high-level scanner pass — only detail scanners remain, cutting scanner count and improving signal-to-noise ratio (closes #193)
- Simplified scanner agent instructions (no multi-read needed at 20K chunks)

## [2.2.0] - 2026-03-08

### Changed
- `/reflect` filter script: replaced byte-based chunking (`target_bytes=100_000`) with token-based chunking using `tiktoken` (`cl100k_base`, 80K tokens per chunk). Three-layer token budget defense: (1) intra-turn splitting at line boundaries for oversized turns, (2) `cap_oversized_lines()` binary-search truncation for individual lines, (3) hard-cap overlap trimming with partition start guard.
- `/reflect` filter script: chunking algorithm redesigned — computes per-turn token costs, derives even partition targets with overlap headroom, then adds token-bounded overlap. Summary view is also chunked when it exceeds the threshold.
- `/reflect` scanner agent: added `tools: Read` to YAML frontmatter to restrict scanner agents to Read-only at the system level (previously prompt-level guidance only).
- `/reflect` scanner agent: added multi-read instructions for 80K chunks (Read tool returns ~25K tokens per call, so scanners must read in multiple passes).
- `/reflect` SKILL.md: scanner agents now launched via `subagent_type` with assignment-only prompts; absolute file paths required.

## [2.1.3] - 2026-03-07

### Fixed
- `/reflect` SKILL.md: scanner agents now invoked via `subagent_type: "dev-workflow:reflect-scanner"` with assignment-only prompts instead of redundantly passing checklists. Ensures consistent scanner behavior.

## [2.1.2] - 2026-03-07

### Fixed
- Fixed atexit cleanup handler that deleted intermediate scan files before scanner agents could read them. Cleanup now only fires on abnormal exit (crashes); normal exit leaves files for scanners, with main agent running explicit cleanup after.

## [2.1.1] - 2026-03-07

### Fixed
- Removed invalid `agents` field from plugin.json that prevented the plugin from loading
- Updated SKILL.md scanner invocation to read agent instructions from file instead of referencing unsupported bundled agent

## [2.1.0] - 2026-03-07

### Changed
- `/reflect`: rewritten as bundled filter script + scanner agent architecture. Deterministic JSONL filtering, segmentation, and chunking handled by `reflect-filter.py` (bundled via `${CLAUDE_SKILL_DIR}`). Judgment-based scanning handled by bundled `reflect-scanner` agent (read-only, 4 checklists). Main agent focuses on synthesis and presentation.
- `/reflect`: checklists reframed from keyword-based to judgment-based; 5 checklists merged to 4 (Undocumented Discoveries and Repeated Operations merged into Codifiable Patterns)
- `/reflect`: added `--full` flag to scan entire transcript instead of just the current segment
- `/reflect`: SKILL.md now provides purpose/mental model context and persistence target hierarchy for the main agent
- `/reflect`: Python-only filtering (removed jq dependency)

## [2.0.0] - 2026-03-06

### Changed
- `/reflect` Step 1: replaced open-ended introspection with JSONL-transcript-scanning subagent pipeline -- scanner reads session transcript directly via nonce-based session identification, jq filtering, compact-segment awareness, and 5 evidence-based boolean signal checklists (user corrections, execution failures, approach pivots, undocumented discoveries, repeated operations)
- `/reflect`: added `--light` (1 Haiku scanner) and `--heavy` (2 parallel Sonnet scanners) modes
- `/reflect` Principles: pruned from 6 to 5; replaced "Anchor where Claude diverges" and "Keep docs concise" with "Evidence over narrative" and "Confidence is informational"

## [1.5.0] - 2026-03-06

### Changed
- `/triage` Step 4: replaced open-ended synthesis with boolean priority checklist (7 signals, 0-12 score), S/M/L effort classification with concrete criteria, and explicit dependency verification checklist
- `/triage` Step 5: added structured output template with mandatory fields per queue item (priority score, effort, what it unblocks, bundle rationale, ranking reason)
- `/triage` `--light`: changed from two-agent (Haiku gather + Sonnet synthesize) to single-agent fully-Haiku pipeline — boolean checklists make Sonnet unnecessary for scoring
- `/triage` Guidelines: added "apply the checklist mechanically" principle; added explicit skip criteria (no acceptance criteria + no clarifying comments, vague future ideas, duplicates)

## [1.4.2] - 2026-03-01

### Changed
- `/session` Phase 1: document AskUserQuestion 4-option limit and handling rule for triage queues with >4 items

## [1.4.1] - 2026-03-01

### Changed
- `/solve` Phase 3: replace binary approve/reject on the Well-scoped path with explicit routing — proceed silently when the approach is fully determined; invoke `/consult` when any implementation sub-choices exist (#147)

## [1.4.0] - 2026-02-28

### Added
- `--light` mode for `code-review`, `solve`, `session`, and `triage`: Haiku-first,
  single-agent, checklist-only pipeline. `code-review --light` runs a two-stage
  mechanical scan (Haiku extracts and flags against an explicit checklist, Sonnet
  filters false positives and synthesizes findings). `session --light` auto-selects
  the top triage item without `AskUserQuestion`. `triage --light` uses a Haiku
  subagent for data gathering and Sonnet for synthesis. Closes #117.

## [1.3.0] - 2026-02-27

### Changed
- `code-review`, `solve`, `session`: inverted flag defaults — single-Sonnet-agent review is now
  the default (no flag); `--heavy` opts into the full multi-agent Opus pipeline. `--light` slot
  is reserved for a future Haiku-first tier (#117). Closes #140.

## [1.2.4] - 2026-02-27

### Changed
- `reflect`: Step 4 now checks convention documents (CLAUDE.md, CONTRIBUTING.md,
  README.md, DEVELOPMENT.md, etc.) for a branching policy before committing.
  Creates a branch + PR when a "never commit to main" rule is found; falls back
  to direct-to-main only when no such policy exists. Closes #131.
- `issue`: Phase 2 research is now conditional. Duplicate check (`gh issue list -S`)
  always runs. The full Explore subagent only fires when the current session lacks
  sufficient context (unfamiliar area, vague description). Closes #132.

## [1.2.3] - 2026-02-26

### Changed
- Added README.md documenting all 7 skills with usage examples and argument descriptions

## [1.2.2] - 2026-02-26 (backfilled)

### Changed
- `code-review` (`--light` mode): research-informed prompt improvements; reframed as cost-optimized rather than lower-quality
- `solve`: require comprehensive issue exploration before scoping

## [1.2.1] - 2026-02-26 (backfilled)

### Changed
- `session`: print triage queue to main response before calling `AskUserQuestion`, so rendered markdown is visible to the user
- `session`: warn against reusing issue numbers from prior context

## [1.2.0] - 2026-02-26 (backfilled)

### Added
- `session`: added trigger phrase documentation
- `triage`: added trigger phrase documentation
- `solve`: added trigger phrase documentation
- `code-review`: added trigger phrase documentation
- `reflect`: added trigger phrase documentation

### Changed
- `reflect`: improved `AskUserQuestion` structure — options are now destinations, not approve/skip; recommended option goes first; literal change details moved to option descriptions

## [1.1.0] - 2026-02-26 (backfilled)

### Added
- `--light` mode for `/code-review`, `/solve`, and `/session`: cost-optimized single-Sonnet-agent review as an alternative to the full multi-agent Opus pipeline

### Changed
- `code-review`: expanded convention document search to include CONTRIBUTING.md, ARCHITECTURE.md, and DEVELOPMENT.md alongside CLAUDE.md and README.md

## [1.0.0] - 2026-02-26 (backfilled)

### Added
- Initial release with 7 skills: `/session`, `/triage`, `/solve`, `/code-review`, `/consult`, `/reflect`, `/issue`
