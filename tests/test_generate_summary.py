"""2. Session summary (GenerateSummary.generate_summary)."""
from UserSession.StopSession.GenerateSummary import GenerateSummary


def test_backend_summary_has_correct_numbers(session_data):
    backend, _ = GenerateSummary().generate_summary(session_data)

    assert backend.session_id == "session-123"
    assert backend.actual_session_duration == 600      # 10 minutes
    assert backend.set_session_duration == 1500        # planned 25 minutes
    assert backend.productive_time == 450              # only related tabs count
    assert backend.session_score == 75
    assert backend.most_used_tab == "Khan Academy"
    assert backend.most_often_blocked == "youtube.com"  # "www." is stripped


def test_frontend_summary_has_expected_format(session_data):
    _, frontend = GenerateSummary().generate_summary(session_data)

    assert frontend == {
        "action": "end_session",
        "content": {
            "score": 75,
            "sessionTimeSeconds": 600,
            "productiveTimeSeconds": 450,
            "distractionsBlocked": 2,
            "tabsOpened": 3,
        },
    }


def test_summary_of_session_without_tabs_does_not_crash(session_data):
    session_data["website_metadata"] = []

    backend, _ = GenerateSummary().generate_summary(session_data)

    assert backend.productive_time == 0
    assert backend.most_used_tab == "None"
    assert backend.most_often_blocked == "None"
