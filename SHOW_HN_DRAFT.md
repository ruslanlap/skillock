Show HN: Skillock – a security-first package manager for AI agent skills (like npm for skills, with built-in audit)

Skillock is a CLI tool that helps you install, update, and audit AI agent skills (for Claude, Codex, Agents, Cursor) with supply-chain security built in.

Key features:
- Scan-before-install: every skill is scanned for dangerous patterns (P0 blocks install, P1 warns, P2 notes)
- Lockfile (TOML) with SHA-256 hashes of every file
- Cross-agent deploy (symlinks to ~/.claude/skills/, ~/.codex/agents/, etc.)
- Audit: verify integrity and re-scan for drift
- Zero runtime dependencies (Python >=3.11, stdlib only)

Why it matters:
As agent skills become more common, installing them from arbitrary GitHub repos is risky. Skillock acts as a gatekeeper, blocking malicious patterns before they reach your agent directories.

Real-world example:
Skillock blocks the "brainstorming" skill from the popular obra/superpowers collection because it reads .env files and uses exec() – 18 genuine P0 findings.

Try it now:
uvx skillock --help
uvx skillock add obra/superpowers --skill brainstorming --agents agents --yes  # blocks with 18 P0
uvx skillock add obra/superpowers --skill test-driven-development --agents agents --yes  # clean install

Links:
- GitHub: https://github.com/ruslanlap/skillock
- Docs: https://github.com/ruslanlap/skillock/tree/main/docs
- Demo: [link to asciinema or GIF when ready]

Built with Python, zero deps, MIT license.