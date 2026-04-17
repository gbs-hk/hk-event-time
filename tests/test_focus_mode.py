import unittest
from unittest.mock import patch

from app.config import Config
from app.services import run_scrape_detailed, should_keep_category


class FocusModeTests(unittest.TestCase):
    def setUp(self):
        self.original_focus = Config.SCRAPE_FOCUS_CATEGORIES
        self.original_include_sample = Config.SCRAPE_INCLUDE_SAMPLE

    def tearDown(self):
        Config.SCRAPE_FOCUS_CATEGORIES = self.original_focus
        Config.SCRAPE_INCLUDE_SAMPLE = self.original_include_sample

    def test_keeps_party(self):
        Config.SCRAPE_FOCUS_CATEGORIES = ("party", "music")
        self.assertTrue(should_keep_category("party"))

    def test_keeps_music(self):
        Config.SCRAPE_FOCUS_CATEGORIES = ("party", "music")
        self.assertTrue(should_keep_category("music"))

    def test_drops_non_focus_category(self):
        Config.SCRAPE_FOCUS_CATEGORIES = ("party", "music")
        self.assertFalse(should_keep_category("sports"))

    def test_keeps_everything_without_focus_filter(self):
        Config.SCRAPE_FOCUS_CATEGORIES = ()
        self.assertTrue(should_keep_category("sports"))

    @patch("app.services.seed_sample_events", return_value=2)
    @patch("app.services.build_scrapers", return_value=[])
    def test_seeds_sample_events_when_live_scrape_is_empty(self, _mock_build_scrapers, mock_seed_sample_events):
        Config.SCRAPE_INCLUDE_SAMPLE = False
        report = run_scrape_detailed()
        self.assertEqual(report["processed"], 2)
        self.assertTrue(report["used_sample_fallback"])
        mock_seed_sample_events.assert_called_once()


if __name__ == "__main__":
    unittest.main()
