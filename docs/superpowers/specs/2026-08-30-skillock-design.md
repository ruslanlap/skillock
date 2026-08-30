# skillock — Design Spec

**Status:** Approved (in chat, 2026-08-30) · **Path:** Architectural · **Target:** public repo, 2000⭐

## Problem

Agent skills (SKILL.md folders) are distributed as unversioned copy-in snapshots from GitHub. Real incidents already exist: a polars skill with adversarial instructions shipped in K-Dense-AI/claude-scientific-skills; an LLM-hallucinated npm package name spread across 200+ repos via copy-pasted skills. Existing tools don't help: `npx skills add` pulls from `main` with no pinning and no scanning; skm-cli symlinks but doesn't scan; Microsoft APM has lockfile but no content scanning. arXiv 2607.01136: "existing skill package managers still lack systematic mechanisms for dependency management or warning users about vulnerable dependencies."

## Product

**skillock** — security-first package manager for AI agent skills.

One-liner: *npm for skills, where audit is built into install.*

Three differentiators:
1. **Scan-before-install** — P0 patterns (curl|bash, data exfil, sudo, secrets) block the install; P1 warns.
2. **Update-diff** — before updating, show exactly which lines changed in SKILL.md and scripts since your pinned version.
3. **Integrity lockfile** — SHA-256 of every installed file + `audit` command that detects tampering after install.

## MVP commands (v0.1)

```
skillock add owner/repo[@tag] [--skill name] [--agents claude,codex]
skillock list
skillock update [skill]
skillock remove [skill]
skillock audit
```

`add` flow: resolve ref (tag → fallback default branch HEAD) → clone (shallow, --filter=blob:none) → detect skills (root SKILL.md → ./skills/* → walk, stop at first SKILL.md) → **scan** (vendored rules from ruslanlap/skill-vet) → P0: abort with findings; P1: prompt (TTY) / `--yes` flag (CI) → hash every file → copy to store → symlink into agent dirs.

`update` flow: fetch → resolve new tag → rescan → diff vs lockfile (unified diff of changed SKILL.md/scripts) → same P0/P1 gate → re-hash.

`audit` flow: rescan installed skills + verify every file hash from lockfile. Exit 1 on P0 or hash mismatch.

## Non-goals (v0.1)

- No manifest/skills.yaml install file (add-driven only)
- No central registry, no web UI
- No dependency resolution between skills
- No Windows support (symlinks + POSIX paths)
- No progress bars/TUI

## Architecture

| Component | Decision |
|---|---|
| Language | Python ≥3.10, **zero runtime deps** (argparse, tomllib/tomli-w for lock, subprocess git) |
| Scanner | Vendored from ruslanlap/skill-vet (own code, MIT) — rules as data, one scan function |
| Store | `~/.local/share/skillock/store/<owner>__<repo>[@<tag>]/<skill>/` |
| Lockfile | `~/.local/share/skillock/skillock.lock` (TOML: skill → ref, sha, files{path→sha256}, findings) |
| Cross-agent | Default targets: `~/.claude/skills`, `~/.codex/skills`, `~/.agents/skills`, `~/.cursor/skills`; `--agents` filters; only dirs that exist get links |
| Config | None. No config file for v0.1 |
| CI | GitHub Action `skillock/audit-action` — separate tiny repo, later phase |

Name collisions checked: GitHub `ruslanlap/skillock` free, PyPI `skillock` free (2026-08-30). Unrelated same-name repos exist (0⭐). PyPI publish as `skillock`, command `skillock`.

## Rule set (vendored from skill-vet)

P0 (block): destructive-rm, sudo-execution, curl-pipe-shell, eval-injection, pickle-deserialize, os-system-call, subprocess-shell-true, sensitive-file-read, api-key-leak.
P1 (warn): network-call-no-auth, write-sensitive-paths, implicit-file-access, child-process-exec, sql-injection-risk, silent-data-exfil.
P2 (note, never blocks): stdin-read, file-delete-glob, import-hazard, hardcoded-ip.

## Testing

pytest with three fixture classes:
- `benign/` — plain markdown skill → installs clean
- `malicious/` — SKILL.md + script with P0 patterns (one fixture per rule) → install aborts
- `tampered/` — file modified after install → `audit` exits 1

Integration test drives the real CLI as subprocess against local git fixtures (git init'd fixture repos, no network).

## Launch plan (star growth)

1. Killer demo: scan real-world skills (K-Dense polars adversarial, hallucinated-npx case) — "skillock catches what npx skills lets through" → GIF in README
2. PyPI via trusted publishing; `uvx skillock` try-without-install line
3. GitHub Action for repo CI skill-scanning
4. Funnel: cross-links from standing PRs ComposioHQ/awesome-claude-skills #1766, VoltAgent #982
5. Launch: Show HN, r/ClaudeAI, r/LocalLLaMA, X thread (English)

## Sprint (10 days, intensive)

| Days | Deliverable |
|---|---|
| 1–2 | skeleton: resolver, store, `add` end-to-end |
| 3–4 | scanner integration + P0 blocking |
| 5 | lockfile + hash verify + update-diff |
| 6 | cross-agent matrix + `--agents` |
| 7 | tests (3 fixture classes) + README + demo GIF |
| 8 | PyPI publish |
| 9–10 | launch posts |

## Success criteria

- `uvx skillock add` works on real repo (e.g. obra/superpowers) and blocks a planted malicious fixture
- `audit` detects tampered file
- 2000⭐ within ~3 months post-launch (stretch), 500⭐ first two weeks (baseline)
