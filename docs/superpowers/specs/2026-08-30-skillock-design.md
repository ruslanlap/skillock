# skillock — Design Spec

**Status:** Approved (in chat, 2026-08-30) · **Path:** Architectural · **Target:** public repo, 2000⭐

## Principles (Constitution)

1. **Security before convenience.** No file reaches an agent directory unscanned. If in doubt, block and explain.
2. **Zero runtime dependencies.** stdlib only; anything needing a package either doesn't ship or gets vendored as data.
3. **Boring, readable code.** No plugin system, no async, no config DSL. One flat package, plain functions.
4. **Fail loud.** Every failure exits non-zero with an actionable message. No silent fallbacks.
5. **POSIX only (v0.1).** Linux/macOS; symlink-based deploy.

## Problem

Agent skills (SKILL.md folders) are distributed as unversioned copy-in snapshots from GitHub. Real incidents: a polars skill with adversarial instructions shipped in K-Dense-AI/claude-scientific-skills; an LLM-hallucinated npm package name spread across 200+ repos. `npx skills add` pulls from `main` with no pinning and no scanning; skm-cli symlinks but doesn't scan; Microsoft APM has lockfile but no content scanning. arXiv 2607.01136: "existing skill package managers still lack systematic mechanisms for dependency management or warning users about vulnerable dependencies."

## Product

**skillock** — security-first package manager for AI agent skills.

One-liner: *npm for skills, where audit is built into install.*

Three differentiators:
1. **Scan-before-install** — P0 patterns block the install; P1 warns.
2. **Update-diff** — before updating, show exactly which lines changed since your pinned version.
3. **Integrity lockfile** — SHA-256 of every installed file + `audit` detecting tampering after install.

## Requirements (EARS)

**Scan scope:** every regular file in the skill directory (SKILL.md, scripts, references, assets), excluding `.git/`. Binary files are hashed, not scanned.

- **WHEN** the user runs `skillock add owner/repo[@tag]`, **THEN** the system SHALL resolve the ref, clone (shallow, `--filter=blob:none`), detect skills, scan every text file, and deploy only if no P0 finding exists.
- **WHEN** a P0 finding is found, **THEN** `add` SHALL abort before any file is written to the store or agent dirs, print each finding (rule, file, line, match), and exit 1.
- **WHEN** a P1 finding is found and stdin is a TTY, **THEN** the system SHALL prompt for confirmation; **WHEN** not a TTY or `--yes` is passed, **THEN** it SHALL proceed and record findings in the lockfile.
- **WHEN** only P2 findings exist, **THEN** the system SHALL install and print them as notes (never blocks, never prompts).
- **WHEN** the repo has no tags, **THEN** the system SHALL pin the default-branch HEAD commit SHA and mark the entry `pinned = "commit"`.
- **WHEN** the user passes a tag that does not exist, **THEN** the system SHALL fail with the list of the 10 most recent tags, exit 1.
- **WHEN** the repo contains multiple skills and `--skill` is not passed, **THEN** the system SHALL list detected skills and abort with instructions to pass `--skill` (no implicit bulk install in v0.1).
- **WHEN** the user runs `skillock list`, **THEN** the system SHALL print each installed skill: name, source repo, pinned ref, scan verdict (clean / N findings), linked agent dirs.
- **WHEN** the user runs `skillock remove <skill>`, **THEN** the system SHALL delete its symlinks from agent dirs, delete the store copy, drop the lockfile entry, and leave unrelated files untouched.
- **WHEN** the user runs `skillock update [skill]`, **THEN** the system SHALL resolve the newest tag, rescan, show a unified diff of ALL changed text files (not only SKILL.md), apply the same P0/P1 gate as `add`, and refuse to deploy on P0.
- **WHEN** an update produces no tag newer than the pinned ref, **THEN** the system SHALL print "already up to date" and exit 0.
- **WHEN** the user runs `skillock audit`, **THEN** the system SHALL re-scan all installed skills AND verify every lockfile SHA-256 against the store; exit 1 on any P0 finding or hash mismatch.
- **WHEN** an agent skill file is modified after install, **THEN** `audit` SHALL report it as TAMPERED with the affected path.
- **WHEN** an agent dir (`~/.claude/skills` etc.) does not exist, **THEN** the system SHALL skip it silently; `--agents` filters the default set; unknown agent name → error listing valid names.

## MVP commands (v0.1)

```
skillock add owner/repo[@tag] [--skill name] [--agents claude,codex] [--yes]
skillock list
skillock update [skill]
skillock remove <skill>
skillock audit
```

`add` flow: resolve ref → clone → detect skills (root SKILL.md → `./skills/*` → walk, stop at first SKILL.md per subtree) → scan → gate → hash every file → copy to store → symlink into agent dirs → append lockfile entry.

## Non-goals (v0.1)

- No manifest/skills.yaml install file (add-driven only)
- No central registry, no web UI
- No dependency resolution between skills
- No Windows support
- No bulk install of all skills (explicit `--skill` only)

## Architecture

| Component | Decision |
|---|---|
| Language | Python **≥3.11**, zero runtime deps: `argparse`, `tomllib` (read), hand-rolled flat-TOML writer (~20 lines) for the lock, `subprocess` git, `hashlib`, `difflib` |
| Scanner | Vendored from ruslanlap/skill-vet (own code, MIT) — rules as data, one scan function |
| Store | `~/.local/share/skillock/store/<owner>__<repo>/<skill>/` |
| Lockfile | `~/.local/share/skillock/skillock.lock` (TOML: skill → ref, pinned, files{path→sha256}, findings) |
| Cross-agent | `~/.claude/skills`, `~/.codex/skills`, `~/.agents/skills`, `~/.cursor/skills` |
| CI | GitHub Action — separate tiny repo, later phase |

Name checked: GitHub `ruslanlap/skillock` free, PyPI `skillock` free (2026-08-30). Unrelated same-name repos exist (0⭐).

## Rule set (vendored from skill-vet)

P0 (block): destructive-rm, sudo-execution, curl-pipe-shell, eval-injection, pickle-deserialize, os-system-call, subprocess-shell-true, sensitive-file-read, api-key-leak.
P1 (warn + confirm): network-call-no-auth, write-sensitive-paths, implicit-file-access, child-process-exec, sql-injection-risk, silent-data-exfil.
P2 (note, never blocks): stdin-read, file-delete-glob, import-hazard, hardcoded-ip.

## Testing

pytest, three fixture classes + local git fixture repos (no network):
- `benign/` — plain markdown skill → installs clean
- `malicious/` — one fixture per P0 rule → install aborts; one P1 fixture → prompts/records
- `tampered/` — file modified after install → `audit` exits 1, reports TAMPERED
- ref-resolution: tagged repo, untagged repo (HEAD pin), missing tag (error + tag list)

Every EARS requirement above maps to ≥1 test.

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
| 7 | tests (fixtures per EARS req) + README + demo GIF |
| 8 | PyPI publish |
| 9–10 | launch posts |

## Success criteria

- `uvx skillock add` works on a real repo (e.g. obra/superpowers) and blocks a planted malicious fixture
- `audit` detects a tampered file
- 500⭐ first two weeks (baseline); 2000⭐ within ~3 months (stretch)
