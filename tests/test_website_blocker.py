"""
8. Website blocking (WebsiteBlockerManager).

The real AI is replaced with a Mock that gives a fixed answer.
That way we test the blocking logic alone, independent of the AI.
"""
from unittest.mock import Mock

import pytest

from UserSession.BlockingWebsites.WebsiteBlockerManager import WebsiteBlockerManager


def fake_ai(answer):
    ai = Mock()
    ai.is_session_related.return_value = answer
    return ai


def test_response_contains_one_decision_per_page():
    blocker = WebsiteBlockerManager(fake_ai(False))
    page = {"tab_id": 7, "url": "https://www.youtube.com"}

    _, response = blocker.website_blocker_manager(page, "Math")

    assert response["tab_id"] == 7
    assert len(response["blocking_decisions"]) == 1
    assert response["blocking_decisions"][0]["website_url"] == "https://www.youtube.com"


def test_each_recommended_video_gets_its_own_decision():
    blocker = WebsiteBlockerManager(fake_ai(False))
    page = {"tab_id": 7, "recommended_content": [
        {"url": "https://youtube.com/a", "content_id": "a"},
        {"url": "https://youtube.com/b", "content_id": "b"},
    ]}

    _, response = blocker.website_blocker_manager(page, "Math")

    assert [d["content_id"] for d in response["blocking_decisions"]] == ["a", "b"]


def test_ai_is_asked_with_page_and_topic():
    ai = fake_ai(False)
    page = {"tab_id": 7, "url": "https://example.com"}

    WebsiteBlockerManager(ai).website_blocker_manager(page, "Math")

    ai.is_session_related.assert_called_once_with(page, "Math")


@pytest.mark.xfail(reason="Known bug: confidence_to_bool() always returns False, "
                          "so unrelated pages are never blocked", strict=True)
def test_unrelated_page_is_blocked():
    blocker = WebsiteBlockerManager(fake_ai(False))   # AI: not related to topic

    _, response = blocker.website_blocker_manager({"tab_id": 1, "url": "https://youtube.com"}, "Math")

    assert response["blocking_decisions"][0]["block"] is True
