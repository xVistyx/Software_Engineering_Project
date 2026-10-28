"""
19. Finding a user's session manager (AuthenticateUser).

The database is replaced with a small FAKE that keeps users in a dict.
A fake is used instead of a Mock because register_user() saves a user and
then immediately looks it up again, so the test double has to remember it.
"""
from datetime import datetime
from threading import RLock

import pytest

from System.SystemManager import AuthenticateUser


class FakeUserDatabase:
    def __init__(self, *user_ids):
        self.tokens = {user_id: f"token-{user_id}" for user_id in user_ids}

    def get_users(self):
        return list(self.tokens)

    def create_user(self, user_id, token):
        self.tokens[user_id] = token


@pytest.fixture
def auth(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)   # each session manager creates a folder in the current directory
    return AuthenticateUser(system_db_manager=FakeUserDatabase("user-1", "user-2"),
                            session_folder=tmp_path, session_managers={},
                            lock=RLock(), clock=datetime.now)


def test_unknown_user_is_rejected(auth):
    with pytest.raises(ValueError):
        auth.for_user("stranger")


def test_same_user_always_gets_the_same_session_manager(auth):
    assert auth.for_user("user-1") is auth.for_user("user-1")


def test_different_users_get_separate_session_managers(auth):
    assert auth.for_user("user-1") is not auth.for_user("user-2")


def test_registering_saves_new_user_with_the_returned_token(auth):
    db = auth.system_db_manager

    result = auth.register_user()

    new_users = set(db.tokens) - {"user-1", "user-2"}
    assert len(new_users) == 1
    assert db.tokens[new_users.pop()] == result["token"]


def test_every_registration_gets_a_different_token(auth):
    assert auth.register_user()["token"] != auth.register_user()["token"]
