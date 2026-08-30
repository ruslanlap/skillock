from __future__ import annotations

import re
import subprocess
from pathlib import Path

from skillock.errors import SkillockError

_TAG_RE = re.compile(r"^v?\d+\.\d+(\.\d+)?$")  # semver-ish: 2-3 components, no bare v1


def run(*args: str, cwd: Path | None = None) -> str:
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        raise SkillockError(f"git {' '.join(args)} failed: {p.stderr.strip()[:300]}")
    return p.stdout


def tags(url: Path | str) -> list[str]:
    out = run("ls-remote", "--tags", str(url))
    names = sorted({m.group(1) for t in out.splitlines()
                    if (m := re.search(r"refs/tags/([^^\n]+)$", t)) and _TAG_RE.match(m.group(1))})
    def key(t: str):
        return tuple(int(x) for x in t.lstrip("v").split("."))
    return sorted(names, key=key, reverse=True)


def resolve(url: Path | str, ref: str | None) -> tuple[str, str]:
    all_tags = tags(url)
    if ref is None:
        ref = all_tags[0] if all_tags else None
    if ref is not None:
        if ref not in all_tags:
            listed = ", ".join(all_tags[:10]) or "(none)"
            raise SkillockError(f"tag '{ref}' not found. Available: {listed}")
        out = run("ls-remote", str(url), f"refs/tags/{ref}")
        sha = out.split()[0]
        return sha, "tag"
    out = run("ls-remote", str(url), "HEAD")
    sha = out.split()[0]
    return sha, "commit"


def clone_at(url: Path | str, sha: str, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    run("init", cwd=dest)
    run("remote", "add", "origin", str(url), cwd=dest)
    p = subprocess.run(["git", "fetch", "--depth", "1", "origin", sha],
                       cwd=dest, capture_output=True, text=True)
    if p.returncode != 0:
        raise SkillockError(f"cannot fetch {sha[:12]}: {p.stderr.strip()[:200]}")
    run("checkout", "FETCH_HEAD", cwd=dest)
