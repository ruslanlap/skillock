"""Rule-based security scanner for agent skills (vendored from ruslanlap/skill-vet)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

FENCE_RE = re.compile(r"^\s*```")


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str  # P0 | P1 | P2
    file: str
    line: int
    match: str
    issue: str


# ponytail: flat regex rules, no AST — ceiling: obfuscated payloads pass;
# upgrade path: per-language parsers if FP/FN rate hurts
_RULES: list[tuple[str, str, str, re.Pattern]] = [
    # name, severity, issue, pattern
    # Matches rm with -r/-R and -f flags in any order/spacing, or --recursive and --force
    (
        "destructive-rm",
        "P0",
        "destructive recursive deletion",
        re.compile(
            r"\brm\b(?=.*(?:(?<!-)-[a-zA-Z]*[rR]|--recursive))(?=.*(?:(?<!-)-[a-zA-Z]*[fF]|--force))[^|\n;]*",
            re.IGNORECASE,
        ),
    ),
    ("sudo-execution", "P0", "privilege escalation attempt", re.compile(r"^\s*sudo\b", re.M)),
    (
        "curl-pipe-shell",
        "P0",
        "remote script piped into shell",
        re.compile(r"\b(curl|wget)\b[^|\n;]*\|\s*(ba|z|da|k)?sh\b"),
    ),
    ("eval-injection", "P0", "dynamic code execution", re.compile(r"\b(eval|exec)\s*\(")),
    ("pickle-deserialize", "P0", "unsafe deserialization", re.compile(r"\bpickle\.loads?\s*\(")),
    ("os-system-call", "P0", "direct shell via os.system", re.compile(r"\bos\.system\s*\(")),
    (
        "subprocess-shell-true",
        "P0",
        "subprocess with shell=True",
        re.compile(r"\bsubprocess\.\w+\([^)]*shell\s*=\s*True"),
    ),
    (
        "sensitive-file-read",
        "P0",
        "reads credentials/ssh/env",
        re.compile(r"(\.ssh/|\.env\b|id_rsa|\.aws/credentials|\.gitconfig)"),
    ),
    (
        "api-key-leak",
        "P0",
        "hardcoded API key/token",
        re.compile(r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16})"),
    ),
    (
        "network-call-no-auth",
        "P1",
        "network call without auth context",
        re.compile(r"\b(requests|urllib|httpx|fetch)\.(get|post|put|delete)\s*\("),
    ),
    ("write-sensitive-paths", "P1", "writes to system paths", re.compile(r"open\(\s*['\"]/etc/")),
    (
        "implicit-file-access",
        "P1",
        "unscoped filesystem enumeration",
        re.compile(r"\bos\.listdir\s*\(|\bglob\.glob\s*\("),
    ),
    ("child-process-exec", "P1", "node child_process exec", re.compile(r"\bchild_process\.exec")),
    ("sql-injection-risk", "P1", "f-string SQL query", re.compile(r"\.execute\(\s*f['\"]")),
    (
        "silent-data-exfil",
        "P1",
        "POST carrying local data",
        re.compile(r"\b(requests|httpx)\.post\(\s*[^)]*\b(json|data)\s*="),
    ),
    ("stdin-read", "P2", "reads stdin", re.compile(r"\binput\(|sys\.stdin\b")),
    (
        "file-delete-glob",
        "P2",
        "wildcard deletion",
        re.compile(r"\b(os\.remove|os\.unlink|shutil\.rmtree)\s*\([^)]*\*"),
    ),
    ("import-hazard", "P2", "dynamic import", re.compile(r"__import__\s*\(")),
    (
        "hardcoded-ip",
        "P2",
        "embedded raw IP address",
        re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    ),
]

MD_EXT = {".md", ".markdown"}


def _is_binary(path: Path) -> bool:
    # ponytail: NUL-sniff first 8KiB — ceiling: crafted text with late NULs; fine for v0.1
    with path.open("rb") as fh:
        return b"\0" in fh.read(8192)


def scan_file(path: Path, root: Path) -> list[Finding]:
    rel = path.relative_to(root).as_posix()
    out: list[Finding] = []
    if _is_binary(path):
        return out
    in_fence = False
    is_md = path.suffix.lower() in MD_EXT
    for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if is_md:
            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
        for name, sev, issue, pat in _RULES:
            m = pat.search(line)
            if m:
                out.append(Finding(name, sev, rel, n, m.group(0)[:80], issue))
    return out


def scan_tree(root: Path) -> list[Finding]:
    out: list[Finding] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or ".git" in p.parts:
            continue
        out.extend(scan_file(p, root))
    return out


def detect_skills(repo_dir: Path) -> list[Path]:
    if (repo_dir / "SKILL.md").is_file():
        return [repo_dir]
    if (repo_dir / "skills").is_dir():
        return sorted(p.parent for p in (repo_dir / "skills").glob("*/SKILL.md"))
    found: list[Path] = []
    for p in sorted(repo_dir.rglob("SKILL.md")):
        if ".git" in p.parts:
            continue
        if any(p.is_relative_to(f) for f in found):
            continue
        found.append(p.parent)
    return found
