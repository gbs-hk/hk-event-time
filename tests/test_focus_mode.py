import unittest

from app.services import should_keep_category


class FocusModeTests(unittest.TestCase):
    def test_keeps_party(self):
        self.assertTrue(should_keep_category("party"))

    def test_keeps_music(self):
        self.assertTrue(should_keep_category("music"))

    def test_drops_non_focus_category(self):
        self.assertFalse(should_keep_category("sports"))


if __name__ == "__main__":
    unittest.main()
