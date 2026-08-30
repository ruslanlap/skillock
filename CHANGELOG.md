# Changelog

All notable changes to this project will be documented in this file.

## [0.1.3] - 2026-08-30

### Added
- Initial public release of `skillock`.
- Core commands: `add`, `list`, `update`, `remove`, `audit`.
- Scan-before-install workflow with 19 security rules (9 P0, 6 P1, 4 P2).
- SHA-256 lockfile integrity tracking for installed skill files.
- Symlink-based deploy support for Claude, Codex, Agents, and Cursor.

### Changed
- Skills are pinned to immutable refs after resolving tag, branch, or commit input.
- `audit` re-validates installed files with both hash checks and scanner re-runs.

### Security
- P0 findings block installation by default.
- Credential reads, hardcoded secrets, curl-pipe-shell, destructive `rm`, and code-execution patterns are explicitly detected.
