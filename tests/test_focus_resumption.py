
"""Regression test: tab timing should resume when Chrome regains focus."""

from UserSession.MetadataProcessing.MetaDataManager import WebsiteMetadataEvaluator


def test_tab_tracking_resumes_when_browser_regains_focus():
    """
    When the user leaves Chrome and then returns,
    the previously active tab should resume tracking time.
    """

    # ARRANGE
    evaluator = WebsiteMetadataEvaluator()
    topic = "Math"
    tab_id = 42

    tab = {
        "tab_id": tab_id,
        "url": "https://example.com"
    }

    # Step 1: User activates a tab.
    evaluator.handle_event({**tab, "reason": "tab_activated", "state": "active"},topic)

    assert evaluator.session.timer.is_active(tab_id)

    # Step 2: User switches away from Chrome.
    evaluator.handle_event(
        {
            "reason": "window_focus_changed",
            "state": "unfocused"
        },
        topic
    )

    # Timer should have stopped.
    assert not evaluator.session.timer.is_active(tab_id)

    # Step 3: User returns to Chrome on the same tab.
    evaluator.handle_event(
        {
            **tab,
            "reason": "window_focus_changed",
            "state": "active"
        },
        topic
    )

    # ASSERT: Timer should restart, but currently does not.
    assert evaluator.session.timer.is_active(tab_id), (
        "Tab timer should resume when Chrome regains focus "
        "on the active tab"
    )
