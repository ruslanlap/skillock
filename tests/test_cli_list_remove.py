from test_cli_add import run_add as run  # brief's run(); this one takes home=


def _install(home, benign_repo):
    r = run("add", str(benign_repo), "--skill", "polars", "--agents", "claude", "--yes", home=home)
    assert r.returncode == 0, r.stderr


def test_list_shows_entry(home, benign_repo):
    _install(home, benign_repo)
    r = run("list", home=home)
    assert "polars" in r.stdout and "claude" in r.stdout


def test_remove_cleans_everything(home, benign_repo):
    _install(home, benign_repo)
    r = run("remove", "polars", home=home)
    assert r.returncode == 0
    assert not (home / ".claude/skills/polars").exists()
    assert "polars" not in (home / ".local/share/skillock/skillock.lock").read_text()


def test_remove_unknown_fails(home):
    r = run("remove", "ghost", home=home)
    assert r.returncode == 1
