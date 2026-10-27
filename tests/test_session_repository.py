"""
10. Database (SessionRepository).

Every test gets its own empty database in a temporary folder (pytest's
tmp_path), so the real DataBase/grove.sqlite3 is never touched.
"""
import pytest

from DataBase.SessionRepository import SessionRepository
from DataBase.SummaryAdapter import summary_record
from UserSession.StopSession.GenerateSummary import GenerateSummary


@pytest.fixture
def repo(tmp_path):
    return SessionRepository(path=tmp_path / "test.sqlite3")


@pytest.fixture
def stored_session(repo, session_data):
    repo.create_user("user-1", "secret-token")
    backend, _ = GenerateSummary().generate_summary(session_data)
    session, summary = summary_record("user-1", backend)
    repo.save_session("user-1", session, summary)
    return session


def test_saved_session_can_be_read_back(repo, stored_session):
    result = repo.get("user-1", stored_session["id"])

    assert result["session"]["topic"] == "Math"
    assert result["summary"]["score"] == 75


def test_login_works_with_correct_token_only(repo):
    repo.create_user("user-1", "secret-token")

    assert repo.authenticate("secret-token") == {"user_id": "user-1", "role": "user"}
    assert repo.authenticate("wrong-token") is None


def test_user_cannot_see_another_users_sessions(repo, stored_session):
    repo.create_user("user-2", "other-token")

    assert repo.list("user-2") == []
    with pytest.raises(ValueError):
        repo.get("user-2", stored_session["id"])
