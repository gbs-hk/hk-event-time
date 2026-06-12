import unittest

from app.categories import infer_category


class CategoryInferenceTests(unittest.TestCase):
    def test_music_category(self):
        self.assertEqual(infer_category("Sunset Concert", "Live band tonight"), "music")

    def test_sports_category(self):
        self.assertEqual(infer_category("Harbour Marathon", "Community sports event"), "sports")

    def test_default_category(self):
        self.assertEqual(infer_category("Unknown", "No matching text"), "other")

    def test_sports_beats_party_for_run_club(self):
        self.assertEqual(infer_category("Victoria Harbour Run Club", "community sports event"), "sports")


if __name__ == "__main__":
    unittest.main()
