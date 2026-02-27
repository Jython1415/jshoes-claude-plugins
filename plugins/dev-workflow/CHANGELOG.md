# Changelog

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
