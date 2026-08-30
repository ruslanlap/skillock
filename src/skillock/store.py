from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

import tomllib

from skillock.errors import SkillockError

AGENTS: dict[str, str] = {
    "claude": ".claude/skills",
    "codex": ".codex/skills",
    "agents": ".agents/skills",
    "cursor": ".cursor/skills",
}


def data_root(home: Path) -> Path:
    return home / ".local/share/skillock"


def store_root(home: Path) -> Path:
    return data_root(home) / "store"


def lock_path(home: Path) -> Path:
    return data_root(home) / "skillock.lock"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_tree(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and ".git" not in p.parts:
            out[p.relative_to(root).as_posix()] = sha256_file(p)
    return out


def _esc(s: str) -> str:
    return (s.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")
             .replace('"', '\\"'))


# ponytail: hand-rolled flat TOML writer (~30 lines) instead of a dependency —
# ceiling: only str/list-of-str/dict-of-str values; enough for the lock format
def write_lock(path: Path, entries: list[dict]) -> None:
    lines: list[str] = []
    for e in entries:
        lines.append("[[skill]]")
        for k in ("name", "repo", "ref", "pinned", "sha", "installed"):
            lines.append(f'{k} = "{_esc(str(e[k]))}"')
        lines.append(f'agents = [{", ".join(chr(34) + _esc(a) + chr(34) for a in e["agents"])}]')
        lines.append(f'findings = [{", ".join(chr(34) + _esc(f) + chr(34) for f in e.get("findings", []))}]')
        for fp, h in e["files"].items():
            lines.append(f'[skill.files."{_esc(fp)}"]')
            lines.append(f'sha256 = "{h}"')
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


def read_lock(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = tomllib.loads(path.read_text())
    out = []
    for e in data.get("skill", []):
        e = dict(e)
        e["files"] = {fp: v["sha256"] for fp, v in e.get("files", {}).items()}
        out.append(e)
    return out


def store_dir_for(home: Path, repo: str, skill: str) -> Path:
    name = repo.rstrip("/").split("/")[-1]
    owner = repo.rstrip("/").split("/")[-2] if "/" in repo.rstrip("/") else "local"
    return store_root(home) / f"{owner}__{name}" / skill


def _skill_name(skill_dir: Path) -> str:
    # tests + lockfile key on frontmatter name, not dir name (brief's stub used dir name)
    sm = skill_dir / "SKILL.md"
    if sm.is_file():
        lines = sm.read_text().splitlines()
        if lines and lines[0].strip() == "---":
            for line in lines[1:]:
                if line.strip() == "---":
                    break
                if (m := re.match(r"^name:\s*(.+?)\s*$", line)):
                    return m.group(1)
    return skill_dir.name


def deploy(skill_dir: Path, home: Path, repo: str, agents: list[str]) -> list[str]:
    dest = store_dir_for(home, repo, _skill_name(skill_dir))
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill_dir, dest)
    links: list[str] = []
    for a in agents:
        adir = home / AGENTS[a]
        if not adir.is_dir():
            continue
        link = adir / dest.name
        if link.is_symlink() or link.exists():
            if not (link.is_symlink() and store_root(home) in link.resolve().parents):
                raise SkillockError(f"refusing to replace non-skillock path: {link}")
            link.unlink()
        link.symlink_to(dest)
        links.append(str(link))
    return links


def undeploy(entry: dict, home: Path) -> None:
    for a in entry.get("agents", []):
        link = home / AGENTS[a] / entry["name"]
        if link.is_symlink() and store_root(home) in link.resolve().parents:
            link.unlink()
    dest = store_dir_for(home, entry["repo"], entry["name"])
    if dest.exists():
        shutil.rmtree(dest)
