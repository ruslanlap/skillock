# Security Policy

## Scope

skillock scans skill files for dangerous patterns before they reach your agent
directories. Security issues in skillock itself (scanner bypasses, lockfile
integrity, symlink handling) are in scope.

## Reporting

Report privately: [GitHub security advisories](https://github.com/ruslanlap/skillock/security/advisories/new).

Do NOT open public issues for exploitable findings.

## Trust model

- Scanner is heuristic (regex, docs-aware). It catches common malicious
  patterns; it is not a sandbox. A determined author can evade it.
- `audit` verifies SHA-256 of every installed file against the lockfile and
  re-scans for P0 drift.
- deploy() never deletes a path it does not own; non-skillock targets are
  refused loudly.

## Known ceilings (documented, deliberate)

- Regex-based detection: obfuscated payloads can pass (`ponytail:`-marked in code).
- Files added to the store after install are re-scanned for P0 but not
  reported as TAMPERED unless a locked file's hash changes.
- No sandboxing of skill scripts at runtime.
