import unittest
from datetime import datetime

from app.scrapers.base import ScrapedEvent
from app.scrapers.html_event_scraper import (
    MultiStrategyEventScraper,
    dedupe_events,
    extract_price_text,
    is_low_quality_title,
    iter_jsonld_event_objects,
    normalize_text,
    parse_datetime_to_utc,
    sanitize_url,
)


class ScraperParsingTests(unittest.TestCase):
    def test_iter_jsonld_events_supports_graph(self):
        raw = '{"@graph": [{"@type": "Event", "name": "A", "startDate": "2026-05-01T20:00:00+08:00"}]}'
        items = list(iter_jsonld_event_objects(raw))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "A")

    def test_parse_datetime_defaults_to_hk_tz(self):
        parsed = parse_datetime_to_utc("2026-05-01 20:00")
        self.assertIsNotNone(parsed)
        # 20:00 HKT => 12:00 UTC
        self.assertEqual(parsed.hour, 12)

    def test_normalize_text_unescapes_html_entities(self):
        self.assertEqual(normalize_text("Fish &amp; Chips"), "Fish & Chips")

    def test_low_quality_title_filter(self):
        self.assertTrue(is_low_quality_title("All Events"))
        self.assertTrue(is_low_quality_title("Best Nightclubs in Hong Kong"))
        self.assertTrue(is_low_quality_title("Events in Hong Kong"))
        self.assertFalse(is_low_quality_title("Friday Harbour Run Club"))

    def test_sanitize_url_blocks_javascript(self):
        self.assertEqual(sanitize_url("javascript:;"), "")

    def test_extract_price_text(self):
        self.assertEqual(extract_price_text("Tickets from HK$280 including one drink"), "HK$280")
        self.assertEqual(extract_price_text("Free entry before 11pm"), "Free")

    def test_parse_datetime_supports_month_day_without_year(self):
        parsed = parse_datetime_to_utc("May 1 20:00")
        self.assertIsNotNone(parsed)

    def test_dedupe_semantic_events(self):
        base = ScrapedEvent(
            external_id="a",
            name="Friday Social Ride",
            description="",
            source_name="x",
            organizer="",
            location_name="Central",
            location_address="",
            map_url="",
            start_time_utc=datetime(2026, 2, 14, 12, 0, 0),
            end_time_utc=None,
            ticket_url="",
            discount_text="",
            discount_url="",
        )
        richer = ScrapedEvent(
            external_id="b",
            name="Friday Social Ride",
            description="Cycling and dinner",
            source_name="x",
            organizer="",
            location_name="Central",
            location_address="",
            map_url="https://maps.google.com/?q=Central",
            start_time_utc=datetime(2026, 2, 14, 12, 0, 0),
            end_time_utc=None,
            ticket_url="https://example.com",
            discount_text="",
            discount_url="",
        )
        rows = dedupe_events([base, richer])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].external_id, "b")

    def test_extract_detail_page_event_from_generic_html(self):
        scraper = MultiStrategyEventScraper(source_name="demo", urls=["https://example.com"])
        html = """
        <html>
            <body>
                <main>
                    <h1>Harbourfront Sunset Session</h1>
                    <p>Live DJs, cocktails, and skyline views.</p>
                    <div class="venue">Central Harbourfront</div>
                    <time datetime="2026-05-01T20:00:00+08:00">1 May 2026 8pm</time>
                </main>
            </body>
        </html>
        """
        event = scraper._extract_detail_page_event("https://example.com/events/harbourfront", html)
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.name, "Harbourfront Sunset Session")
        self.assertEqual(event.location_name, "Central Harbourfront")
        self.assertEqual(event.ticket_url, "https://example.com/events/harbourfront")


if __name__ == "__main__":
    unittest.main()
