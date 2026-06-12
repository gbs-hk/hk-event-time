"""Lu.ma (luma) Hong Kong event scraper.

Lu.ma embeds upcoming event data inside a ``__NEXT_DATA__`` JSON blob that
is server-side rendered into every city/place page, so no API key or headless
browser is needed — a plain HTTP GET is sufficient.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import requests

from ..config import Config
from .base import BaseScraper, ScrapedEvent
from .html_event_scraper import (
    build_map_url,
    dedupe_events,
    extract_discount_text,
    normalize_text,
    parse_datetime_to_utc,
    stable_external_id,
)

# City/place pages that embed HK events.  Only the place slug is needed —
# Luma's SSR includes the first page of events without any auth.
_LUMA_HK_PAGES = [
    "https://lu.ma/hong-kong",
]

_NEXT_DATA_RE = re.compile(
    r'<script\s+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
    re.DOTALL,
)


class LumaScraper(BaseScraper):
    """Scrapes Hong Kong events from lu.ma city pages."""

    source_name = "luma-hk"

    def fetch(self) -> list[ScrapedEvent]:
        events: list[ScrapedEvent] = []
        headers = {
            "User-Agent": Config.SCRAPE_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        for url in _LUMA_HK_PAGES:
            try:
                resp = requests.get(url, headers=headers, timeout=Config.SCRAPE_TIMEOUT_SECONDS, allow_redirects=True)
                resp.raise_for_status()
                events.extend(self._parse_page(resp.text))
            except Exception:
                continue
        return dedupe_events(events)

    def _parse_page(self, html: str) -> list[ScrapedEvent]:
        match = _NEXT_DATA_RE.search(html)
        if not match:
            return []
        try:
            nd = json.loads(match.group(1))
        except json.JSONDecodeError:
            return []

        raw_events = (
            nd.get("props", {})
            .get("pageProps", {})
            .get("initialData", {})
            .get("data", {})
            .get("events", [])
        )
        events: list[ScrapedEvent] = []
        for entry in raw_events:
            ev = self._parse_entry(entry)
            if ev:
                events.append(ev)
        return events

    def _parse_entry(self, entry: dict) -> ScrapedEvent | None:
        event = entry.get("event") or entry
        name = normalize_text(event.get("name") or "")
        if not name or len(name) < 4:
            return None

        start_dt = parse_datetime_to_utc(event.get("start_at") or "")
        if not start_dt:
            return None
        end_dt = parse_datetime_to_utc(event.get("end_at") or "") if event.get("end_at") else None

        geo = event.get("geo_address_info") or {}
        location_name = normalize_text(geo.get("address") or geo.get("city_state") or "")
        location_address = normalize_text(geo.get("full_address") or "")
        if not location_name:
            location_name = location_address

        url_slug = event.get("url") or ""
        ticket_url = f"https://lu.ma/{url_slug}" if url_slug else ""

        # Luma hosts (first one) can serve as organizer
        hosts = entry.get("hosts") or []
        organizer = ""
        if hosts and isinstance(hosts[0], dict):
            organizer = normalize_text(hosts[0].get("name") or "")

        description = normalize_text(event.get("description") or "")
        discount_text = extract_discount_text(f"{name} {description}")
        external_id = stable_external_id(
            self.source_name, ticket_url or name, name, start_dt
        )

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
            ticket_url=ticket_url,
            discount_text=discount_text,
            discount_url=ticket_url if discount_text else "",
        )
