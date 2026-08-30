from pathlib import Path
from skillock.store import (read_lock, write_lock, sha256_file, hash_tree,
                            deploy, undeploy, lock_path, store_root, AGENTS)


ENTRY = {"name": "polars", "repo": "https://github.com/x/y", "ref": "v0.1.0",
         "pinned": "tag", "sha": "a" * 40, "installed": "2026-08-30T00:00:00Z",
         "agents": ["claude"], "files": {"SKILL.md": "b" * 64},
         "findings": ["P1 network-call-no-auth"]}


def test_lock_roundtrip(tmp_path):
    p = tmp_path / "skillock.lock"
    write_lock(p, [ENTRY])
    (out,) = read_lock(p)
    assert out["name"] == "polars" and out["files"]["SKILL.md"] == "b" * 64
    assert out["findings"] == ["P1 network-call-no-auth"]


def test_lock_roundtrip_escapes_newlines(tmp_path):
    # trust boundary: raw \n in a TOML basic string corrupts the lockfile
    nasty = 'line1\nline"quote"\\end'
    p = tmp_path / "skillock.lock"
    write_lock(p, [{**ENTRY, "findings": [nasty]}])
    (out,) = read_lock(p)
    assert out["findings"] == [nasty]


def test_lock_read_missing_returns_empty(tmp_path):
    assert read_lock(tmp_path / "nope.lock") == []


def test_hash_tree(tmp_path):
    (tmp_path / "SKILL.md").write_text("hi")
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "a.py").write_text("x = 1")
    h = hash_tree(tmp_path)
    assert set(h) == {"SKILL.md", "d/a.py"}
    assert h["SKILL.md"] == sha256_file(tmp_path / "SKILL.md")


def test_deploy_symlinks_into_existing_agents(tmp_path, home):
    src = tmp_path / "skill"; src.mkdir()
    (src / "SKILL.md").write_text("---\nname: s\n---\n")
    links = deploy(src, home, "https://github.com/x/y", ["claude", "codex", "cursor"])
    # cursor dir doesn't exist in fixture home → skipped
    assert (home / ".claude/skills/s").is_symlink()
    assert (home / ".codex/skills/s").is_symlink()
    assert not (home / ".cursor/skills/s").exists()
    assert len(links) == 2


def test_deploy_refuses_non_skillock_path(tmp_path, home):
    # data-loss boundary: a real user dir at the agent target must never be rmtree'd
    from skillock.errors import SkillockError
    src = tmp_path / "skill"; src.mkdir()
    (src / "SKILL.md").write_text("---\nname: s\n---\n")
    target = home / ".claude" / "skills" / "s"
    target.mkdir()
    (target / "my-notes.md").write_text("user data")
    try:
        deploy(src, home, "https://github.com/x/y", ["claude"])
    except SkillockError as e:
        assert "refusing to replace non-skillock path" in str(e)
    else:
        raise AssertionError("expected SkillockError")
    assert (target / "my-notes.md").read_text() == "user data"
    assert not target.is_symlink()


def test_undeploy_removes_only_ours(tmp_path, home):
    src = tmp_path / "skill"; src.mkdir()
    (src / "SKILL.md").write_text("---\nname: s\n---\n")
    deploy(src, home, "https://github.com/x/y", ["claude"])
    stranger = home / ".claude/skills/stranger"
    stranger.mkdir()
    undeploy({**ENTRY, "name": "s", "agents": ["claude"]}, home)
    assert not (home / ".claude/skills/s").exists()
    assert stranger.exists()
    assert not (store_root(home) / "x__y" / "s").exists()
