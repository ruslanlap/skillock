# skillock 🔒

**Security-first package manager for AI agent skills.**
*npm for skills — where audit is built into install.*

`npx skills add` pulls from `main` and ships whatever is there. skillock scans
every file for malicious patterns BEFORE anything reaches your agent, pins the
exact version, and verifies file integrity afterwards.

## Install

    uvx skillock add owner/repo --skill my-skill --agents claude,codex

## Commands

| Command | What it does |
|---|---|
| `add owner/repo[@tag]` | resolve → clone → **scan** → gate → deploy → lock |
| `list` | installed skills, pinned refs, scan verdicts |
| `update [skill]` | rescan + unified diff of every changed file, then upgrade |
| `remove <skill>` | delete symlinks, store copy, lock entry |
| `audit` | re-scan everything + verify SHA-256 of every installed file |

## What gets blocked (P0)

curl-pipe-shell · destructive-rm · sudo · eval/exec · pickle · os.system ·
subprocess shell=True · credential reads · hardcoded API keys

P1 warns and asks; P2 prints notes. Full rule table in [docs](docs/superpowers/specs/2026-08-30-skillock-design.md).

## Why

Real incidents: a polars skill shipped adversarial instructions
(K-Dense-AI/claude-scientific-skills); an hallucinated npm package spread to
200+ repos via copy-pasted skills. Skills are prompts your agent executes —
treat them like code.

*Zero runtime dependencies. Python ≥3.11. POSIX. MIT.*
