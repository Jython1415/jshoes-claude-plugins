# Changelog

## [1.3.1] - 2026-02-27

### Changed
- `hook-development` skill: documented `PostToolUse` matcher requirement — omitting `"matcher"` silently disables the hook.

## [1.3.0] - 2026-02-27

### Changed
- Renamed from `claude-code-misc` to `plugin-support` for clarity.

## [1.2.0] - 2026-02-27

### Added
- **feedback skill**: auto-discover installed plugin version from `~/.claude/plugins/installed_plugins.json` before asking the user; falls back to manual input when the file is missing or the plugin key is not found

## [1.1.2] - 2026-02-26

### Changed
- README rewritten to properly describe both skills (`/hook-development` and `/feedback`) with usage examples

## [1.1.1] - 2026-02-24

### Changed
- **hook-development skill**: added "Shell Wrapper Patterns" section documenting the ARG_MAX / `sys.argv` gotcha — pass large hook payloads (e.g. Write-tool file content) via env vars rather than positional args when spawning Python from a shell wrapper
