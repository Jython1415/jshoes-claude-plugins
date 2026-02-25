# Changelog

## [1.1.1] - 2026-02-24

### Changed
- **hook-development skill**: added "Shell Wrapper Patterns" section documenting the ARG_MAX / `sys.argv` gotcha — pass large hook payloads (e.g. Write-tool file content) via env vars rather than positional args when spawning Python from a shell wrapper
