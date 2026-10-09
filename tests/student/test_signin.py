"""Sign-in: cookies are re-checked against the account, and wrong passwords slow down."""

from lerni.student.signin import Role, SignIn
from lerni.student.students import Kind, StudentStore


class Clock:
    def __init__(self):
        self.now = 1_000_000.0

    def __call__(self):
        return self.now


def make(tmp_path):
    store = StudentStore(tmp_path)
    store.add("sam", "Sam", Kind.INDEPENDENT, "correct horse")
    clock = Clock()
    return store, SignIn(store, b"k" * 32, clock=clock), clock


def test_cookie_works_until_reset_or_archive(tmp_path):
    store, signin, _ = make(tmp_path)
    cookie, _ = signin.attempt("sam", "correct horse")
    assert signin.viewer_from_cookie(cookie).role is Role.INDEPENDENT
    store.reset_password("sam", "new password")
    assert signin.viewer_from_cookie(cookie) is None  # every device signed out
    assert signin.viewer_from_cookie("sam.1.1.forged") is None
    store.add("alba", "Alba", Kind.INDEPENDENT, "long enough", educator=True)
    educator, _ = signin.attempt("alba", "long enough")
    assert signin.viewer_from_cookie(educator).educator


def test_wrong_passwords_wait_without_touching_signed_in_sessions(tmp_path):
    _, signin, clock = make(tmp_path)
    cookie, _ = signin.attempt("sam", "correct horse")
    for _ in range(3):
        assert signin.attempt("sam", "nope")[0] is None
    refused, message = signin.attempt("sam", "correct horse")  # inside the wait
    assert refused is None and "wait" in message.lower()
    assert signin.viewer_from_cookie(cookie) is not None  # existing session unaffected
    clock.now += 2
    assert signin.attempt("sam", "correct horse")[0] is not None


def test_parallel_wrong_passwords_still_wait(tmp_path, monkeypatch):
    # regression: attempts sent at once all slipped past the wait before any was recorded
    import threading
    import time

    import lerni.student.signin as signin_module

    store, signin, _ = make(tmp_path)
    checked = []
    real = signin_module.verify_password

    def slow_verify(password, stored):
        checked.append(1)
        time.sleep(0.05)
        return real(password, stored)

    monkeypatch.setattr(signin_module, "verify_password", slow_verify)
    threads = [threading.Thread(target=signin.attempt, args=("sam", "nope")) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(checked) == 3  # the rest were refused without checking


def test_unknown_usernames_look_like_known_ones(tmp_path):
    # regression: only real accounts ever got the wait message, revealing who exists
    _, signin, _ = make(tmp_path)
    for _ in range(3):
        signin.attempt("nobody-here", "nope")
    assert "wait" in signin.attempt("nobody-here", "nope")[1].lower()


def test_an_empty_secret_file_is_refused(tmp_path):
    # regression: an empty secret.key signed cookies with an empty key
    import pytest

    from lerni.student.signin import load_secret

    (tmp_path / "secret.key").write_text("")
    with pytest.raises(RuntimeError):
        load_secret(tmp_path)
