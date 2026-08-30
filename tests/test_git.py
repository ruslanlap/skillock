from conftest import make_repo
from skillock.git import tags, resolve, clone_at
from skillock.errors import SkillockError


def test_tags_newest_first(tagged_repo):
    assert tags(tagged_repo) == ["v0.2.0", "v0.1.0"]


def test_resolve_explicit_tag(tagged_repo):
    sha, pinned = resolve(tagged_repo, "v0.1.0")
    assert pinned == "tag" and len(sha) == 40


def test_resolve_default_newest_tag(tagged_repo):
    sha, pinned = resolve(tagged_repo, None)
    assert pinned == "tag"


def test_resolve_untagged_pins_head(benign_repo):
    sha, pinned = resolve(benign_repo, None)
    assert pinned == "commit" and len(sha) == 40


def test_resolve_missing_tag_raises(benign_repo):
    try:
        resolve(benign_repo, "v9.9.9")
    except SkillockError as e:
        assert "v9.9.9" in str(e)
    else:
        raise AssertionError("expected SkillockError")


def test_bare_number_tag_not_listed(tmp_path):
    # decision: accept only ^v?\d+\.\d+(\.\d+)?$ — bare v1 is ambiguous
    repo = make_repo(tmp_path, "bare1.git",
                     {"s/SKILL.md": "---\nname: s\n---\nbody\n"}, tags=["v1"])
    assert tags(repo) == []


def test_only_bare_number_tags_fall_back_to_head(tmp_path):
    repo = make_repo(tmp_path, "bare.git",
                     {"s/SKILL.md": "---\nname: s\n---\nbody\n"}, tags=["v1"])
    sha, pinned = resolve(repo, None)
    assert pinned == "commit" and len(sha) == 40


def test_two_component_tag_accepted(tmp_path):
    repo = make_repo(tmp_path, "two.git",
                     {"s/SKILL.md": "---\nname: s\n---\nbody\n"}, tags=["v1.0"])
    assert tags(repo) == ["v1.0"]


def test_three_component_tag_accepted(tmp_path):
    repo = make_repo(tmp_path, "three.git",
                     {"s/SKILL.md": "---\nname: s\n---\nbody\n"}, tags=["v6.3.0"])
    assert tags(repo) == ["v6.3.0"]


def test_non_numeric_tag_rejected(tmp_path):
    repo = make_repo(tmp_path, "rel.git",
                     {"s/SKILL.md": "---\nname: s\n---\nbody\n"}, tags=["release-2026"])
    assert tags(repo) == []
