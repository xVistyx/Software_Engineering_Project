"""9. Summary -> database format (SummaryAdapter.summary_record)."""
from dataclasses import replace

import pytest

from DataBase.SummaryAdapter import summary_record
from UserSession.StopSession.GenerateSummary import GenerateSummary


@pytest.fixture
def summary(session_data):
    backend, _ = GenerateSummary().generate_summary(session_data)
    return backend


def test_valid_summary_is_converted_for_database(summary):
    session, frontend_summary = summary_record("user-1", summary)

    assert session["user_id"] == "user-1"
    assert session["status"] == "ended"
    assert len(session["website_visits"]) == 3
    assert frontend_summary["score"] == 75


def test_time_is_grouped_per_domain(summary):
    _, frontend_summary = summary_record("user-1", summary)

    domains = {d["domain"]: d["seconds"] for d in frontend_summary["domains"]}
    assert domains["www.khanacademy.org"] == 300.0


@pytest.mark.parametrize("field, bad_value", [
    ("session_topic", "   "),           # empty topic
    ("session_id", ""),                 # empty ID
    ("actual_session_duration", -5),    # negative duration
])
def test_invalid_summary_is_rejected(summary, field, bad_value):
    with pytest.raises(ValueError):
        summary_record("user-1", replace(summary, **{field: bad_value}))
