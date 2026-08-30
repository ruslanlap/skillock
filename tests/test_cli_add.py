import subprocess
import sys


def run(*args):
    return subprocess.run([sys.executable, "-m", "skillock", *args], capture_output=True, text=True)


def test_version():
    r = run("--version")
    assert r.returncode == 0
    assert "0.1.0" in r.stdout


# Task 5 tests
import os


def run_add(*args, home=None):
    env = dict(os.environ)
    if home:
        env["SKILLOCK_HOME"] = str(home)
    return subprocess.run(
        [sys.executable, "-m", "skillock", *args], capture_output=True, text=True, env=env
    )


def test_add_benign(home, benign_repo):
    r = run_add("add", str(benign_repo), "--skill", "polars", "--agents", "claude", home=home)
    assert r.returncode == 0, r.stderr
    assert (home / ".claude/skills/polars/SKILL.md").exists()
    lock = (home / ".local/share/skillock/skillock.lock").read_text()
    assert "polars" in lock and 'pinned = "commit"' in lock


def test_add_p0_blocks_and_writes_nothing(home, evil_repo):
    r = run_add("add", str(evil_repo), "--skill", "evil", "--agents", "claude", home=home)
    assert r.returncode == 1
    assert "curl-pipe-shell" in r.stdout
    assert not (home / ".claude/skills/evil").exists()
    assert not (home / ".local/share/skillock/skillock.lock").exists()


def test_add_missing_skill_flag_lists_skills(home, benign_repo):
    r = run_add("add", str(benign_repo), home=home)
    assert r.returncode == 1
    assert "polars" in r.stdout and "--skill" in r.stdout


def test_add_missing_tag_lists_tags(home, benign_repo):
    r = run_add("add", f"{benign_repo}@v9.9.9", "--skill", "polars", home=home)
    assert r.returncode == 1
    assert "v9.9.9" in r.stdout
