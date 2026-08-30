import argparse
import difflib
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from skillock import __version__, git, scanner, store
from skillock.errors import SkillockError


def home_dir() -> Path:
    return Path(os.environ.get("SKILLOCK_HOME") or Path.home())


def _rmtree(path: Path) -> None:
    # git marks object files read-only; plain rmtree fails on Windows (WinError 5)
    shutil.rmtree(path, onerror=lambda f, p, e: (os.chmod(p, 0o644), f(p)))


def _repo_url(spec: str) -> tuple[str, str | None]:
    repo, _, tag = spec.partition("@")
    url = (
        repo
        if "://" in repo
        or repo.startswith((".", "/"))
        or Path(repo).drive  # Windows path like C:\... or C:/...
        or (len(repo) > 1 and repo[1] == ":")
        else f"https://github.com/{repo}"
    )
    return url, tag or None


def _print_findings(findings):
    for f in findings:
        print(f"  {f.severity} {f.file}:{f.line} {f.rule} — {f.issue} | {f.match}")


def _agents_from_links(links: list[str], home: Path) -> list[str]:
    out = []
    for link in links:
        link_path = Path(link)
        # Find which agent this link belongs to by checking relative to home
        try:
            rel = link_path.relative_to(home)
            # The first part should be the agent directory (e.g., .claude, .codex)
            agent_dir = rel.parts[0]
            # Map back to agent key
            for agent_key, agent_path in store.AGENTS.items():
                if agent_path.split("/")[-2:] == list(rel.parts[:2]):
                    out.append(agent_key)
                    break
            else:
                out.append(agent_dir)
        except ValueError:
            # Link is not under home, fallback to last known agent
            pass
    return out


def _gate(findings, yes) -> int | None:
    """Shared security gate: returns 1 to abort, None to proceed."""
    p0 = [f for f in findings if f.severity == "P0"]
    p1 = [f for f in findings if f.severity == "P1"]
    p2 = [f for f in findings if f.severity == "P2"]
    if p0:
        print("BLOCKED — P0 findings:")
        _print_findings(p0)
        return 1
    if p1 and not yes:
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
    return None


def cmd_add(args) -> int:
    url, tag = _repo_url(args.repo)
    sha, pinned = git.resolve(url, tag)
    tmp = home_dir() / ".local/share/skillock/tmp"
    if tmp.exists():
        _rmtree(tmp)
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
        if (gate := _gate(findings, args.yes)) is not None:
            return gate
        links = store.deploy(skill, home_dir(), url, args.agents.split(","))
        entry = {
            "name": skill.name,
            "repo": url,
            "ref": tag or (sha if pinned == "commit" else git.tags(url)[0]),
            "pinned": pinned,
            "sha": sha,
            "installed": datetime.now(UTC).isoformat(timespec="seconds"),
            "agents": _agents_from_links(links, home_dir()),
            "files": store.hash_tree(store.store_dir_for(home_dir(), url, skill.name)),
            "findings": [f"{f.severity} {f.rule}" for f in findings if f.severity != "P0"],
        }
        lp = store.lock_path(home_dir())
        entries = [e for e in store.read_lock(lp) if e["name"] != skill.name]
        entries.append(entry)
        store.write_lock(store.lock_path(home_dir()), entries)
        print(f"locked {skill.name} @ {entry['ref']} -> {', '.join(links)}")
        return 0
    finally:
        # Clean up tmp clone after deploy
        if tmp.exists():
            _rmtree(tmp)


def _diff(old_dir: Path, new_dir: Path) -> str:
    out = []
    old = store.hash_tree(old_dir)
    new = store.hash_tree(new_dir)
    for f in sorted(set(old) | set(new)):
        a = (old_dir / f).read_text(errors="replace") if f in old else ""
        b = (new_dir / f).read_text(errors="replace") if f in new else ""
        if a != b:
            out.extend(
                difflib.unified_diff(
                    a.splitlines(True), b.splitlines(True), fromfile=f"a/{f}", tofile=f"b/{f}"
                )
            )
    return "".join(out)


def cmd_update(args) -> int:
    entries = store.read_lock(store.lock_path(home_dir()))
    pool = [e for e in entries if not args.skill or e["name"] == args.skill]
    if args.skill and not pool:
        raise SkillockError(f"skill '{args.skill}' is not installed")
    rc = 0
    for e in pool:
        sha, pinned = git.resolve(e["repo"], None)
        newest = git.tags(e["repo"])[0] if git.tags(e["repo"]) else sha
        if newest == e["ref"] or sha == e["sha"]:
            print(f"{e['name']}: already up to date")
            continue
        tmp = home_dir() / ".local/share/skillock/tmp"
        if tmp.exists():
            _rmtree(tmp)
        git.clone_at(e["repo"], sha, tmp)
        try:
            skills = scanner.detect_skills(tmp)
            if not any(s.name == e["name"] for s in skills):
                print(f"{e['name']}: skill no longer present in {e['repo']}, skipping")
                rc = 1
                continue
            skill = next(s for s in skills if s.name == e["name"])
            findings = scanner.scan_tree(skill)
            if _gate(findings, args.yes) is not None:
                print(f"{e['name']}: refusing update, keeping {e['ref']}")
                rc = 1
                continue
            old_dir = store.store_dir_for(home_dir(), e["repo"], e["name"])
            print(_diff(old_dir, skill))
            store.deploy(skill, home_dir(), e["repo"], e["agents"])
            e["sha"] = sha
            e["ref"], e["pinned"] = (newest, "tag") if pinned == "tag" else (sha, "commit")
            e["files"] = store.hash_tree(store.store_dir_for(home_dir(), e["repo"], e["name"]))
            e["findings"] = [f"{f.severity} {f.rule}" for f in findings if f.severity != "P0"]
            print(f"updated {e['name']} -> {e['ref']}")
        finally:
            if tmp.exists():
                _rmtree(tmp)
    store.write_lock(store.lock_path(home_dir()), entries)
    return rc


def cmd_list(args) -> int:
    entries = store.read_lock(store.lock_path(home_dir()))
    if not entries:
        print("nothing installed")
        return 0
    for e in entries:
        verdict = "clean" if not e.get("findings") else f"{len(e['findings'])} finding(s)"
        print(f"{e['name']}  {e['repo']}@{e['ref']} [{verdict}] -> {','.join(e['agents'])}")
    return 0


def cmd_remove(args) -> int:
    entries = store.read_lock(store.lock_path(home_dir()))
    entry = next((e for e in entries if e["name"] == args.skill), None)
    if entry is None:
        raise SkillockError(f"skill '{args.skill}' is not installed")
    store.undeploy(entry, home_dir())
    store.write_lock(store.lock_path(home_dir()), [e for e in entries if e["name"] != args.skill])
    print(f"removed {args.skill}")
    return 0


def cmd_audit(args) -> int:
    bad = False
    for e in store.read_lock(store.lock_path(home_dir())):
        d = store.store_dir_for(home_dir(), e["repo"], e["name"])
        findings = scanner.scan_tree(d)
        p0 = [f for f in findings if f.severity == "P0"]
        for f in p0:
            print(f"DRIFT  {e['name']} {f.file}:{f.line} {f.rule}")
        cur = store.hash_tree(d)
        expected_files = e["files"]
        for fp, h in expected_files.items():
            if cur.get(fp) != h:
                print(f"TAMPERED {e['name']}/{fp}")
                bad = True
        for fp in sorted(set(cur) - set(expected_files)):
            print(f"TAMPERED {e['name']}/{fp} (unexpected file)")
            bad = True
        if p0:
            bad = True
        if not p0 and cur == expected_files:
            print(f"{e['name']}: clean")
    return 1 if bad else 0


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
    a = sub.add_parser("list")
    a.set_defaults(fn=cmd_list)
    a = sub.add_parser("remove")
    a.add_argument("skill")
    a.set_defaults(fn=cmd_remove)
    a = sub.add_parser("update")
    a.add_argument("skill", nargs="?")
    a.add_argument("--yes", action="store_true")
    a.set_defaults(fn=cmd_update)
    a = sub.add_parser("audit")
    a.set_defaults(fn=cmd_audit)
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
