"""Student accounts: saved, checked, and refused when the username isn't canonical."""

import pytest

from lerni.student.students import AccountError, Kind, StudentStore, verify_password


def test_account_saves_loads_and_checks_its_password(tmp_path):
    store = StudentStore(tmp_path)
    store.add("sam", "Sam", Kind.INDEPENDENT, "correct horse")
    sam = store.get("sam")
    assert sam.kind is Kind.INDEPENDENT and sam.display_name == "Sam"
    assert verify_password("correct horse", sam.password)
    assert not verify_password("wrong", sam.password)
    reset = store.reset_password("sam", "another pass")
    assert reset.session_version == sam.session_version + 1  # signs out every device


@pytest.mark.parametrize("username", ["Sam", "../x", "", "educator", "admin", "s", "9lives"])
def test_bad_or_reserved_usernames_are_refused(tmp_path, username):
    with pytest.raises(AccountError):
        StudentStore(tmp_path).add(username, "X", Kind.SUPERVISED, "1234")


def test_archived_username_is_never_reused(tmp_path):
    store = StudentStore(tmp_path)
    store.add("sam", "Sam", Kind.SUPERVISED, "1234")
    store.archive("sam")
    assert store.get("sam").archived
    with pytest.raises(AccountError):
        store.add("sam", "Sam again", Kind.SUPERVISED, "1234")


def test_a_stray_or_broken_file_does_not_hide_the_others(tmp_path):
    # regression: a leftover temp file or a corrupt account broke the whole Students list
    store = StudentStore(tmp_path)
    store.add("sam", "Sam", Kind.SUPERVISED, "1234")
    (store.root / ".tmp-abc.json").write_text("{")
    (store.root / "broken.json").write_text("not json")
    assert [s.username for s in store.list_students()] == ["sam"]
