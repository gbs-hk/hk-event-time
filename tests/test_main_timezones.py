import unittest
from datetime import datetime

from app.main import parse_request_datetime_to_utc, utc_naive_to_hk_iso


class MainTimezoneTests(unittest.TestCase):
    def test_parse_request_datetime_to_utc_respects_offset(self):
        parsed = parse_request_datetime_to_utc("2026-04-01T00:00:00+08:00")
        self.assertEqual(parsed, datetime(2026, 3, 31, 16, 0, 0))

    def test_utc_naive_to_hk_iso_adds_hk_offset(self):
        rendered = utc_naive_to_hk_iso(datetime(2026, 3, 31, 16, 0, 0))
        self.assertEqual(rendered, "2026-04-01T00:00:00+08:00")


if __name__ == "__main__":
    unittest.main()
