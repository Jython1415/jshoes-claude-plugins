# Changelog

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
