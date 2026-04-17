import unittest
from datetime import datetime

from app.scrapers.base import ScrapedEvent
from app.services import evaluate_event


class QualityTests(unittest.TestCase):
    def test_rejects_generic_event_title(self):
        event = ScrapedEvent(
            external_id="x",
            name="Events in Hong Kong",
            description="A generic landing page",
            source_name="discover-hk",
            organizer="",
            location_name="Central",
            location_address="",
            map_url="",
            start_time_utc=datetime(2026, 5, 1, 12, 0, 0),
            end_time_utc=None,
            ticket_url="https://example.com",
            discount_text="",
            discount_url="",
        )
        result = evaluate_event(event)
        self.assertTrue(result["rejected"])
        self.assertIn("generic_title", result["reasons"])

    def test_accepts_richer_event(self):
        event = ScrapedEvent(
            external_id="x",
            name="Central Rooftop House Night",
            description="House DJs, guest list, skyline venue, and direct ticketing page for Friday night.",
            source_name="lan-kwai-fong",
            organizer="LKF",
            location_name="Central",
            location_address="Hong Kong",
            map_url="https://maps.google.com/?q=Central",
            start_time_utc=datetime(2026, 5, 1, 12, 0, 0),
            end_time_utc=None,
            ticket_url="https://example.com",
            discount_text="Early bird",
            discount_url="https://example.com",
            source_url="https://example.com",
            price_text="HK$180",
        )
        result = evaluate_event(event)
        self.assertFalse(result["rejected"])
        self.assertGreaterEqual(result["score"], 55)


if __name__ == "__main__":
    unittest.main()
