"""Tests for accounts: registration, login and password handling."""

import pytest

from ssa.services import AuthError, AuthService


@pytest.fixture
def auth(db):
    return AuthService(db)


def test_register_then_login(auth):
    auth.register("alice", "correct horse battery")
    user = auth.login("alice", "correct horse battery")
    assert user.username == "alice"


def test_password_is_not_stored_in_plain_text(auth, db):
    auth.register("bob", "super secret pw")
    stored = db.query('SELECT * FROM "_users" WHERE username = ?', ["bob"]).iloc[0]
    assert "super secret pw" not in stored["password_hash"]
    assert len(stored["password_hash"]) == 64          # sha256 hex digest
    assert stored["salt"]                               # a per-user salt exists


def test_same_password_gets_different_hashes(auth, db):
    auth.register("user_one", "identical password")
    auth.register("user_two", "identical password")
    hashes = db.query('SELECT password_hash FROM "_users"')["password_hash"].tolist()
    assert hashes[0] != hashes[1]                       # salts differ


def test_wrong_password_is_rejected(auth):
    auth.register("carol", "the right password")
    with pytest.raises(AuthError):
        auth.login("carol", "the wrong password")


def test_unknown_user_is_rejected(auth):
    with pytest.raises(AuthError):
        auth.login("nobody", "whatever12345")


def test_duplicate_username_is_refused(auth):
    auth.register("dave", "first password")
    with pytest.raises(AuthError):
        auth.register("dave", "another password")


@pytest.mark.parametrize("username", ["ab", "has space", "way" * 20, "bad!char"])
def test_invalid_usernames_are_refused(auth, username):
    with pytest.raises(AuthError):
        auth.register(username, "a good long password")


def test_short_password_is_refused(auth):
    with pytest.raises(AuthError):
        auth.register("eve", "short")
