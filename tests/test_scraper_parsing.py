import unittest
from datetime import datetime

from app.scrapers.base import ScrapedEvent
from app.scrapers.eventbrite_api_scraper import EventbriteApiScraper
from app.scrapers.html_event_scraper import (
    MultiStrategyEventScraper,
    ConfiguredSourceScraper,
    clean_location_text,
    dedupe_events,
    extract_price_text,
    is_low_quality_title,
    iter_jsonld_event_objects,
    looks_like_date_bucket,
    looks_like_date_title,
    normalize_text,
    parse_datetime_to_utc,
    sanitize_url,
)
from app.scrapers.sources import SourceDefinition, hongkong_cheapo_month_urls
from app.scrapers.urbtix_open_data_scraper import UrbtixOpenDataScraper


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

    def test_date_bucket_titles_are_detected(self):
        self.assertTrue(looks_like_date_bucket("Early Jun"))
        self.assertTrue(looks_like_date_bucket("Mid ~ Late Jun"))
        self.assertTrue(is_low_quality_title("Mid May"))
        self.assertFalse(looks_like_date_bucket("Harbour Sessions"))

    def test_date_titles_are_detected(self):
        self.assertTrue(looks_like_date_title("Apr 23 ~ May 9"))
        self.assertTrue(looks_like_date_title("Sun, May 24"))
        self.assertTrue(looks_like_date_title("Tue, 31 Mar 2026, 12:00 am"))
        self.assertTrue(looks_like_date_title("Dec 11 ~ Mar 31 2026"))
        self.assertTrue(looks_like_date_title("May 2026"))
        self.assertFalse(looks_like_date_title("Mega Ice Hockey 5's 2026"))

    def test_sanitize_url_blocks_javascript(self):
        self.assertEqual(sanitize_url("javascript:;"), "")

    def test_extract_price_text(self):
        self.assertEqual(extract_price_text("Tickets from HK$280 including one drink"), "HK$280")
        self.assertEqual(extract_price_text("Free entry before 11pm"), "Free")

    def test_clean_location_text(self):
        self.assertEqual(clean_location_text("Tsim Sha Tsui 27.6 km"), "Tsim Sha Tsui")
        self.assertEqual(clean_location_text("tendees can partake in more than 35 whisky masterclasses"), "")

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

    def test_configured_scraper_avoids_cheapo_date_bucket_title(self):
        definition = SourceDefinition(
            key="hongkong-cheapo",
            label="Hong Kong Cheapo",
            urls=["https://hongkongcheapo.com/events"],
            priority=95,
            card_selector="article",
            title_selector="h2, h3, .entry-title, a",
            date_selectors=("time", ".date", ".meta-date"),
            location_selectors=(".location", ".venue"),
        )
        scraper = ConfiguredSourceScraper(definition)
        html = """
        <article class="post">
          <h2>Early Jun</h2>
          <a href="/events/harbour-party/">Harbour Party with Guest DJs</a>
          <div class="meta-date">1 Jun 2026 8:00pm</div>
          <div class="venue">Central</div>
          <p>Sunset drinks and rooftop music.</p>
        </article>
        """
        events = scraper._extract_generic_cards("https://hongkongcheapo.com/events", html)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Harbour Party with Guest DJs")
        self.assertEqual(events[0].source_url, "https://hongkongcheapo.com/events/harbour-party/")

    def test_configured_scraper_avoids_cheapo_date_overlay_title(self):
        definition = SourceDefinition(
            key="hongkong-cheapo",
            label="Hong Kong Cheapo",
            urls=["https://hongkongcheapo.com/events/may"],
            priority=95,
            card_selector="article",
            title_selector="h2, h3, .entry-title, a",
            date_selectors=("time", ".date", ".meta-date"),
            location_selectors=(".location", ".venue"),
        )
        scraper = ConfiguredSourceScraper(definition)
        html = """
        <article class="article card card--event">
          <a class="card__image" href="/events/mega-ice-hockey-5s/" title="Mega Ice Hockey 5's 2026">
            <div class="card__image__overlay">
              <div class="card--event__date-box multi">
                <div class="inner">
                  <div class="date">Apr 23</div>
                  <div class="tilde">~</div>
                  <div class="date">May 9</div>
                </div>
              </div>
            </div>
          </a>
          <div class="card__content">
            <h3 class="card__title">
              <a href="/events/mega-ice-hockey-5s/" title="Mega Ice Hockey 5's 2026">Mega Ice Hockey 5's 2026</a>
            </h3>
            <p class="card__excerpt">Ice hockey in Hong Kong? Absolutely.</p>
            <a class="location" href="/events/location/kowloon/kowloon-bay/">Kowloon Bay</a>
          </div>
        </article>
        """
        events = scraper._extract_generic_cards("https://hongkongcheapo.com/events/may", html)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Mega Ice Hockey 5's 2026")
        self.assertEqual(events[0].source_url, "https://hongkongcheapo.com/events/mega-ice-hockey-5s/")

    def test_jsonld_events_keep_source_page_url(self):
        scraper = MultiStrategyEventScraper(source_name="demo", urls=["https://example.com"])
        html = """
        <script type="application/ld+json">
        {
          "@type": "Event",
          "name": "Harbourfront Film Night",
          "startDate": "2026-05-01T20:00:00+08:00",
          "offers": {"url": "https://tickets.example.com/film-night"}
        }
        </script>
        """
        events = scraper._extract_from_html("https://example.com/events/film-night", html)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].source_url, "https://example.com/events/film-night")
        self.assertEqual(events[0].ticket_url, "https://tickets.example.com/film-night")

    def test_detail_page_prefers_official_external_link(self):
        scraper = MultiStrategyEventScraper(source_name="demo", urls=["https://example.com"])
        html = """
        <html>
          <body>
            <main>
              <h1>Harbour Cinema Night</h1>
              <p>Open-air movies with cocktails.</p>
              <time datetime="2026-05-01T20:00:00+08:00">1 May 2026 8pm</time>
              <a href="https://tickets.partner.com/harbour-cinema">Official site</a>
            </main>
          </body>
        </html>
        """
        event = scraper._extract_detail_page_event("https://example.com/events/harbour-cinema", html)
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.source_url, "https://example.com/events/harbour-cinema")
        self.assertEqual(event.ticket_url, "https://tickets.partner.com/harbour-cinema")

    def test_cheapo_month_urls_include_current_and_next_month(self):
        urls = hongkong_cheapo_month_urls(datetime(2026, 5, 15))
        self.assertEqual(
            urls,
            [
                "https://hongkongcheapo.com/events/may",
                "https://hongkongcheapo.com/events/june",
            ],
        )

    def test_eventbrite_api_mapping(self):
        scraper = EventbriteApiScraper()
        event = scraper._to_scraped_event(
            {
                "name": {"text": "Warehouse Disco"},
                "description": {"text": "Late-night disco and live visuals."},
                "start": {"utc": "2026-05-01T12:00:00Z"},
                "end": {"utc": "2026-05-01T15:00:00Z"},
                "url": "https://www.eventbrite.com/e/warehouse-disco",
                "primary_venue": {
                    "name": "Kowloon Warehouse",
                    "address": {"localized_address_display": "Kowloon Bay, Hong Kong"},
                },
                "organizer": {"name": "Night Shift"},
            }
        )
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.source_url, "https://www.eventbrite.com/e/warehouse-disco")
        self.assertEqual(event.location_name, "Kowloon Warehouse")
        self.assertEqual(event.organizer, "Night Shift")

    def test_urbtix_open_data_mapping(self):
        scraper = UrbtixOpenDataScraper()
        events = scraper._parse_batch_xml(
            """
            <BATCH>
              <EVENTS>
                <EVENT>
                  <EVENT_EG>Harbour Concert Series</EVENT_EG>
                  <REFERENCE_LINK>https://www.urbtix.hk/event-detail/99999</REFERENCE_LINK>
                  <CATEGORY>
                    <MAIN_CAT><EG>Music</EG></MAIN_CAT>
                    <SUB_CAT><EG>Classical Music</EG></SUB_CAT>
                  </CATEGORY>
                  <LOCATION>
                    <VENUE_EG>HONG KONG CULTURAL CENTRE</VENUE_EG>
                    <CITY_EG>Hong Kong, China</CITY_EG>
                    <REGION_EG>Kowloon</REGION_EG>
                  </LOCATION>
                  <PERFORMANCES>
                    <PERFORMANCE>
                      <PERFORMANCE_DATETIME>2026-05-01 19:30</PERFORMANCE_DATETIME>
                      <TITLE_EG>Harbour Concert Series</TITLE_EG>
                      <REMARK_EG>Opening Night</REMARK_EG>
                      <REFERENCE_LINK>https://www.urbtix.hk/performance-detail?eventId=99999&amp;performanceId=12345</REFERENCE_LINK>
                    </PERFORMANCE>
                  </PERFORMANCES>
                </EVENT>
              </EVENTS>
            </BATCH>
            """
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Harbour Concert Series")
        self.assertEqual(events[0].source_name, "URBTIX Open Data")
        self.assertEqual(events[0].location_name, "HONG KONG CULTURAL CENTRE")
        self.assertEqual(events[0].location_address, "Kowloon, Hong Kong, China")
        self.assertEqual(events[0].source_url, "https://www.urbtix.hk/performance-detail?eventId=99999&performanceId=12345")


if __name__ == "__main__":
    unittest.main()
