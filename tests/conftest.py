"""
Shared test data (pytest "fixtures").

A fixture builds fresh test data for every test that asks for it,
so no test can change the data another test uses (tests stay independent).
"""
from datetime import datetime, timedelta

import pytest


START = datetime(2026, 10, 27, 10, 0, 0)


@pytest.fixture
def session_data():
    """A finished 10-minute session (planned: 25 min) with three tabs."""
    return {
        "session_info": {
            "id": "session-123",
            "topic": "Math",
            "start_time": START.isoformat(),
            "predicted_end_time": (START + timedelta(minutes=25)).isoformat(),
            "actual_end_time": (START + timedelta(minutes=10)).isoformat(),
            "time": 1500,
            "tab_count": 3,
            "blocked_tabs": 2,
        },
        "website_metadata": [
            {"tab_id": 1, "title": "Khan Academy", "url": "https://www.khanacademy.org/math",
             "time_spent": 300.0, "is_related": True, "block": False},
            {"tab_id": 2, "title": "Wolfram Alpha", "url": "https://www.wolframalpha.com",
             "time_spent": 150.0, "is_related": True, "block": False},
            {"tab_id": 3, "title": "YouTube", "url": "https://www.youtube.com/watch?v=x",
             "time_spent": 60.0, "is_related": False, "block": True},
        ],
    }
