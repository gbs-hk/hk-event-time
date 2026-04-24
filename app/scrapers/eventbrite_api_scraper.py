from __future__ import annotations

from datetime import UTC, datetime, timedelta

import requests

from ..config import Config
from .base import BaseScraper, ScrapedEvent
from .html_event_scraper import build_map_url, normalize_text, sanitize_url, stable_external_id


class EventbriteApiScraper(BaseScraper):
    source_name = "Eventbrite Hong Kong"
    search_url = "https://www.eventbriteapi.com/v3/events/search/"

    def fetch(self) -> list[ScrapedEvent]:
        if not Config.EVENTBRITE_API_TOKEN:
            return []

        now = datetime.now(UTC)
        params = {
            "q": "Hong Kong",
            "location.address": "Hong Kong",
            "start_date.range_start": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "start_date.range_end": (now + timedelta(days=120)).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "expand": "venue,organizer,ticket_availability",
            "page_size": "50",
            "sort_by": "date",
        }
        headers = {
            "Authorization": f"Bearer {Config.EVENTBRITE_API_TOKEN}",
            "Accept": "application/json",
            "User-Agent": Config.SCRAPE_USER_AGENT,
        }

        try:
            response = requests.get(self.search_url, params=params, headers=headers, timeout=Config.SCRAPE_TIMEOUT_SECONDS)
            response.raise_for_status()
        except Exception:
            return []

        payload = response.json()
        events: list[ScrapedEvent] = []
        for item in payload.get("events", []):
            event = self._to_scraped_event(item)
            if event:
                events.append(event)
        return events

    def _to_scraped_event(self, item: dict) -> ScrapedEvent | None:
        name = normalize_text(((item.get("name") or {}).get("text")) or "")
        start_local = ((item.get("start") or {}).get("utc")) or ""
        if not name or not start_local:
            return None

        try:
            start_dt = datetime.fromisoformat(start_local.replace("Z", "+00:00")).astimezone(UTC).replace(tzinfo=None)
        except ValueError:
            return None

        end_dt = None
        end_local = ((item.get("end") or {}).get("utc")) or ""
        if end_local:
            try:
                end_dt = datetime.fromisoformat(end_local.replace("Z", "+00:00")).astimezone(UTC).replace(tzinfo=None)
            except ValueError:
                end_dt = None

        venue = item.get("primary_venue") or item.get("venue") or {}
        location_name = normalize_text(venue.get("name") or "")
        address = venue.get("address") or {}
        location_address = normalize_text(
            ", ".join(part for part in [address.get("localized_address_display"), address.get("localized_area_display")] if part)
        )
        organizer = normalize_text(((item.get("organizer") or {}).get("name")) or "")
        description = normalize_text(((item.get("description") or {}).get("text")) or "")[:500]
        source_url = sanitize_url(item.get("url") or "")

        external_id = stable_external_id("eventbrite-hk-api", source_url, name, start_dt)
        return ScrapedEvent(
            external_id=external_id,
            name=name,
            description=description,
            source_name=self.source_name,
            organizer=organizer,
            location_name=location_name,
            location_address=location_address,
            map_url=build_map_url(location_name, location_address),
            start_time_utc=start_dt,
            end_time_utc=end_dt,
            ticket_url=source_url,
            discount_text="",
            discount_url="",
            source_url=source_url,
            price_text="",
        )
