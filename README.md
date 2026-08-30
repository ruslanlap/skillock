# skillock 🔒

**Security-first package manager for AI agent skills.**  
*Like npm for skills — with audit built into install.*

## Features

- 🔒 **Scan-before-install** — 19 security rules (9 P0, 6 P1, 4 P2) check every file
- 🔐 **Supply-chain integrity** — TOML lockfile with SHA-256 of every file
- 🚫 **Zero trust** — P0 rules block install; P1 prompts; P2 notes only
- 🔄 **Symlink deploy** — clean, reversible installation into agent directories
- 🏷️ **Pinned versions** — resolves tags/commits/branches to immutable SHA
- 🧩 **Multi-agent** — supports Claude, Codex, Agents, Cursor (or `--agents all`)
- 📦 **Zero runtime deps** — Python ≥3.11, stdlib only (`tomllib`, `hashlib`, `subprocess`, `pathlib`)
- 🛡️ **MIT licensed**

## Install

```bash
# one-off (no install needed)
uvx skillock add owner/repo --skill my-skill --agents claude,codex

# or install globally
uv tool install skillock
```

## Commands

| Command | Description |
|---------|-------------|
| `add owner/repo[@tag]` | resolve → clone → **scan** → gate → deploy → lock |
| `list` | installed skills, pinned refs, scan verdicts |
| `update [skill]` | rescan + unified diff of every changed file, then upgrade |
| `remove <skill>` | delete symlinks, store copy, lock entry |
| `audit` | re-scan everything + verify SHA-256 of every installed file |

## What Gets Blocked (P0 — Install Refused)

- **curl-pipe-shell** — `curl ... | sh`, `wget ... | bash`
- **destructive-rm** — `rm -rf /`, `rm -fr`, `rm -Rf`
- **sudo / privilege escalation** — `sudo`, `su`, `doas`
- **code execution** — `eval()`, `exec()`, `Function()`, `os.system()`, `subprocess(..., shell=True)`
- **pickle deserialization** — `pickle.load()`, `pickle.loads()`
- **credential reads** — `.env`, `~/.ssh/`, `AWS_SECRET`, `GH_TOKEN`, etc.
- **hardcoded secrets** — API keys, tokens, passwords in source

P1 warns and asks for confirmation; P2 prints notes only.  
Full rule table: [docs/spec](docs/superpowers/specs/2026-08-30-skillock-design.md).

## Quick Demo

```bash
# This skill reads .env and uses exec() — BLOCKED (18 P0 findings)
uvx skillock add obra/superpowers --skill brainstorming --agents agents --yes

# Clean skill — installs successfully
uvx skillock add obra/superpowers --skill test-driven-development --agents agents --yes
```

## How It Works

1. **Resolve** — GitHub repo + tag/commit/branch → pinned commit SHA
2. **Clone** — shallow clone at pinned ref
3. **Scan** — every file checked against 19 security rules (9 P0, 6 P1, 4 P2)
4. **Gate** — P0 blocks install; P1 prompts; P2 notes
5. **Deploy** — symlinks into agent directories (`~/.claude/skills/`, `~/.codex/agents/`, etc.)
6. **Lock** — TOML lockfile with SHA-256 of every file for integrity verification

Supported agents: `claude`, `codex`, `agents`, `cursor` (or `--agents all`)

## Why

Real incidents show skills are untrusted code:
- A polars skill shipped adversarial instructions ([K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills))
- A hallucinated npm package spread to 200+ repos via copy-pasted skills

Skills are prompts your agent executes — treat them like untrusted code.

## Architecture

- **Zero runtime dependencies** — Python ≥3.11, stdlib only (`tomllib`, `hashlib`, `subprocess`, `pathlib`)
- **POSIX** — Linux, macOS, WSL
- **MIT license**

## Links

- GitHub: https://github.com/ruslanlap/skillock
- PyPI: https://pypi.org/project/skillock/
- Security policy: [SECURITY.md](SECURITY.md)
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)
- Changelog: [CHANGELOG.md](CHANGELOG.md) (if exists)

## Badges

![PyPI](https://img.shields.io/pypi/v/skillock)
![Python](https://img.shields.io/pypi/pyversions/skillock)
![License](https://img.shields.io/pypi/l/skillock)
![CI](https://github.com/ruslanlap/skillock/actions/workflows/ci.yml/badge.svg)