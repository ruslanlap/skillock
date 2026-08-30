# Contributing

## Dev setup

```bash
uv sync
uv run pytest -q
```

## Rules

- Zero runtime dependencies (stdlib only, Python >=3.11). pytest is dev-only.
- TDD: failing test first for any non-trivial change.
- Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`).
- Security-relevant changes need a test that proves the attack/leak is closed.
- New scanner rules: add to `src/skillock/scanner.py` `_RULES` with severity
  (P0 blocks install, P1 warns, P2 notes) + a test fixture line that triggers it
  and one that must NOT trigger it (no false positives on benign prose).

## Adding an agent target

Append to `AGENTS` in `src/skillock/store.py` (name → path relative to HOME)
and extend the deploy test.
