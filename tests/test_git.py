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
