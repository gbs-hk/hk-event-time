from __future__ import annotations

from datetime import datetime, timedelta

from .base import BaseScraper, ScrapedEvent


class SampleHongKongScraper(BaseScraper):
    """
    Seed/demo scraper so the app is usable before real sources are plugged in.
    Replace this with source-specific scrapers for Time Out HK, ticketing platforms,
    clubs, venue websites, and RSS/event APIs.
    """

    source_name = "sample"

    def fetch(self) -> list[ScrapedEvent]:
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        return [
            ScrapedEvent(
                external_id="sample-lan-kwai-fong-dj-night",
                name="Lan Kwai Fong DJ Night",
                description="Live DJ sets with happy hour specials in Central.",
                source_name=self.source_name,
                organizer="LKF Collective",
                location_name="Lan Kwai Fong",
                location_address="Central, Hong Kong",
                map_url="https://maps.google.com/?q=Lan+Kwai+Fong+Hong+Kong",
                start_time_utc=now + timedelta(days=2, hours=12),
                end_time_utc=now + timedelta(days=2, hours=16),
                ticket_url="https://example.com/tickets/dj-night",
                discount_text="20% early bird until midnight",
                discount_url="https://example.com/discounts/dj-night",
            ),
            ScrapedEvent(
                external_id="sample-hk-marathon-training",
                name="Victoria Harbour Run Club",
                description="Community sports training session with pacing groups.",
                source_name=self.source_name,
                organizer="HK Run Club",
                location_name="Tsim Sha Tsui Promenade",
                location_address="Kowloon, Hong Kong",
                map_url="https://maps.google.com/?q=Tsim+Sha+Tsui+Promenade",
                start_time_utc=now + timedelta(days=3, hours=4),
                end_time_utc=now + timedelta(days=3, hours=6),
                ticket_url="https://example.com/register/run-club",
                discount_text="",
                discount_url="",
            ),
        ]
