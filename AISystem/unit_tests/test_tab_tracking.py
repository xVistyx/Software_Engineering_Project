
import unittest
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from UserSession.WebsiteManagement.MetaDataManager import WebsiteMetadataEvaluator


class TestTabTracking(unittest.TestCase):

    def test_tab_tracking_resumes_when_browser_regains_focus(self):
        """
        Regression test: When the user leaves Chrome and returns,
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
        evaluator.handle_event(
            {**tab, "reason": "tab_activated", "state": "active"},
            topic
        )

        self.assertTrue(evaluator.session.timer.is_active(tab_id))

        # Step 2: User switches away from Chrome.
        evaluator.handle_event(
            {
                "reason": "window_focus_changed",
                "state": "unfocused"
            },
            topic
        )

        # Timer should have stopped.
        self.assertFalse(evaluator.session.timer.is_active(tab_id))

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
        self.assertTrue(
            evaluator.session.timer.is_active(tab_id),
            "Tab timer should resume when Chrome regains focus on the active tab"
        )


if __name__ == "__main__":
    unittest.main()
