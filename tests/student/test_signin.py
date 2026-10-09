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
    return store, SignIn(store, "educator-pass", b"k" * 32, clock=clock), clock


def test_cookie_works_until_reset_or_archive(tmp_path):
    store, signin, _ = make(tmp_path)
    cookie, _ = signin.attempt("sam", "correct horse")
    assert signin.viewer_from_cookie(cookie).role is Role.INDEPENDENT
    store.reset_password("sam", "new password")
    assert signin.viewer_from_cookie(cookie) is None  # every device signed out
    assert signin.viewer_from_cookie("sam.1.1.forged") is None
    educator, _ = signin.attempt("educator", "educator-pass")
    assert signin.viewer_from_cookie(educator).role is Role.EDUCATOR


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
