"""1. Score calculation (GenerateSummary.generate_score)."""
import pytest

from UserSession.StopSession.GenerateSummary import GenerateSummary


@pytest.fixture
def summary():
    return GenerateSummary()


def test_score_is_productive_share_of_session_time(summary):
    # Arrange: 450 s productive out of a 600 s session
    # Act
    score = summary.generate_score(productive_time=450, total_time=600)
    # Assert
    assert score == 75


def test_score_is_zero_when_session_has_no_duration(summary):
    assert summary.generate_score(productive_time=100, total_time=0) == 0


@pytest.mark.parametrize("productive, total, expected", [
    (900, 600, 100),   # more productive time than session time -> capped at 100
    (-50, 600, 0),     # negative input -> floored at 0
])
def test_score_stays_between_0_and_100(summary, productive, total, expected):
    assert summary.generate_score(productive, total) == expected
