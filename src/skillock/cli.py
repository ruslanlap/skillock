import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from skillock import __version__
from skillock.errors import SkillockError
from skillock import git, scanner, store


def home_dir() -> Path:
    return Path(os.environ.get("SKILLOCK_HOME") or Path.home())


def _repo_url(spec: str) -> tuple[str, str | None]:
    repo, _, tag = spec.partition("@")
    url = repo if "://" in repo or repo.startswith(".") or repo.startswith("/") \
        else f"https://github.com/{repo}"
    return url, tag or None


def _print_findings(findings):
    for f in findings:
        print(f"  {f.severity} {f.file}:{f.line} {f.rule} — {f.issue} | {f.match}")


def _agents_from_links(links: list[str], home: Path) -> list[str]:
    out = []
    for l in links:
        link_path = Path(l)
        # Find which agent this link belongs to by checking relative to home
        try:
            rel = link_path.relative_to(home)
            # The first part should be the agent directory (e.g., .claude, .codex)
            agent_dir = rel.parts[0]
            # Map back to agent key
            for agent_key, agent_path in store.AGENTS.items():
                if agent_path.split("/")[-2:] == rel.parts[:2]:
                    out.append(agent_key)
                    break
            else:
                out.append(agent_dir)
        except ValueError:
            # Link is not under home, fallback to last known agent
            pass
    return out


def cmd_add(args) -> int:
    url, tag = _repo_url(args.repo)
    sha, pinned = git.resolve(url, tag)
    tmp = home_dir() / ".local/share/skillock/tmp"
    if tmp.exists():
        import shutil
        shutil.rmtree(tmp)
    git.clone_at(url, sha, tmp)
    try:
        skills = scanner.detect_skills(tmp)
        names = [s.name for s in skills]
        if not skills:
            raise SkillockError("no skills detected in repository")
        if args.skill and args.skill not in names:
            raise SkillockError(f"skill '{args.skill}' not found. Detected: {', '.join(names)}")
        if not args.skill:
            raise SkillockError(f"multiple/zero skills detected: {', '.join(names)} — pass --skill")
        skill = next(s for s in skills if s.name == (args.skill or names[0]))
        findings = scanner.scan_tree(skill)
        p0 = [f for f in findings if f.severity == "P0"]
        p1 = [f for f in findings if f.severity == "P1"]
        p2 = [f for f in findings if f.severity == "P2"]
        if p0:
            print("BLOCKED — P0 findings:")
            _print_findings(p0)
            return 1
        if p1 and not args.yes:
            print("P1 findings:")
            _print_findings(p1)
            try:
                if not input("proceed? [y/N] ").strip().lower().startswith("y"):
                    return 1
            except EOFError:
                return 1
        if p2:
            _print_findings(p2)
            print(f"installed with {len(p2)} note(s)")
        links = store.deploy(skill, home_dir(), url, args.agents.split(","))
        entry = {
            "name": skill.name,
            "repo": url,
            "ref": tag or (sha if pinned == "commit" else git.tags(url)[0]),
            "pinned": pinned,
            "sha": sha,
            "installed": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "agents": _agents_from_links(links, home_dir()),
            "files": store.hash_tree(store.store_dir_for(home_dir(), url, skill.name)),
            "findings": [f"{f.severity} {f.rule}" for f in p1 + p2],
        }
        entries = [e for e in store.read_lock(store.lock_path(home_dir())) if e["name"] != skill.name]
        entries.append(entry)
        store.write_lock(store.lock_path(home_dir()), entries)
        print(f"locked {skill.name} @ {entry['ref']} → {', '.join(links)}")
        return 0
    finally:
        # Clean up tmp clone after deploy
        import shutil
        if tmp.exists():
            shutil.rmtree(tmp)


def main(argv=None):
    p = argparse.ArgumentParser(prog="skillock")
    p.add_argument("--version", action="version", version=f"skillock {__version__}")
    sub = p.add_subparsers(dest="cmd")
    a = sub.add_parser("add")
    a.add_argument("repo")
    a.add_argument("--skill")
    a.add_argument("--agents", default="claude,codex,agents,cursor")
    a.add_argument("--yes", action="store_true")
    a.set_defaults(fn=cmd_add)
    args = p.parse_args(argv)
    if getattr(args, "fn", None) is None:
        p.print_help()
        return 0
    try:
        return args.fn(args)
    except SkillockError as e:
        print(f"error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())