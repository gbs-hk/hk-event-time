"""Eventbrite Hong Kong event scraper.

Uses the Eventbrite public API (requires EVENTBRITE_API_KEY env var) or,
as a fallback, extracts the JSON blob that Eventbrite embeds in its HTML
pages (window.__SERVER_DATA__) — no credentials required for the fallback.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

from ..config import Config
from .base import BaseScraper, ScrapedEvent
from .html_event_scraper import (
    build_map_url,
    dedupe_events,
    extract_discount_text,
    normalize_text,
    parse_datetime_to_utc,
    sanitize_url,
    stable_external_id,
)

HK_TZ = ZoneInfo("Asia/Hong_Kong")

# Eventbrite "place_id" for Hong Kong. Stable identifier used in their public
# discovery endpoints and always returns publicly-visible events.
_EB_PLACE_ID = "101193363"

# Public discovery endpoint — no token required.
_EB_DISCOVERY_URL = (
    "https://www.eventbrite.com/api/v3/destination/events/"
    f"?place_id={_EB_PLACE_ID}"
    "&expand=event_sales_status,primary_venue,saves,ticket_availability,"
    "primary_organizer,image"
    "&page_size=50"
    "&page=1"
    "&dates=current_future"
    "&sort_by=best"
    "&online_events_only=false"
    "&include_adult_events=true"
)

# Eventbrite official REST API v3 (requires private token).
_EB_API_URL = (
    "https://www.eventbriteapi.com/v3/events/search/"
    "?location.address=Hong+Kong"
    "&expand=venue,organizer,ticket_availability"
    "&date_modified.range_start={start_utc}"
    "&order_by=start_asc"
    "&page_size=100"
)

# Listing pages to scrape for embedded JSON when no API key is available.
_EB_LISTING_PAGES = [
    "https://www.eventbrite.com/d/hk--hong-kong/events/",
    "https://www.eventbrite.com/d/hk--hong-kong/music/",
    "https://www.eventbrite.com/d/hk--hong-kong/nightlife/",
    "https://www.eventbrite.com/d/hk--hong-kong/sports-and-fitness/",
    "https://www.eventbrite.com/d/hk--hong-kong/food-and-drink/",
]


class EventbriteScraper(BaseScraper):
    """Scrapes Hong Kong events from Eventbrite."""

    source_name = "eventbrite-hk"

    def __init__(self) -> None:
        import os
        self._api_key = os.getenv("EVENTBRITE_API_KEY", "").strip()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def fetch(self) -> list[ScrapedEvent]:
        if self._api_key:
            events = self._fetch_via_official_api()
            if events:
                return dedupe_events(events)

        # Try the public discovery endpoint first (no auth).
        events = self._fetch_via_discovery_api()
        if events:
            return dedupe_events(events)

        # Last resort: scrape embedded JSON from listing pages.
        events = self._fetch_via_html_pages()
        return dedupe_events(events)

    # ------------------------------------------------------------------
    # Strategy 1: Official REST API (needs token)
    # ------------------------------------------------------------------

    def _fetch_via_official_api(self) -> list[ScrapedEvent]:
        start_utc = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        url = _EB_API_URL.format(start_utc=start_utc)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }
        events: list[ScrapedEvent] = []
        while url:
            try:
                resp = requests.get(url, headers=headers, timeout=Config.SCRAPE_TIMEOUT_SECONDS)
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                break

            for eb_event in data.get("events", []):
                event = self._parse_api_event(eb_event)
                if event:
                    events.append(event)

            pagination = data.get("pagination", {})
            if pagination.get("has_more_items"):
                url = pagination.get("continuation")
                if not url:
                    break
            else:
                break
        return events

    def _parse_api_event(self, eb: dict) -> ScrapedEvent | None:
        name = normalize_text((eb.get("name") or {}).get("text") or "")
        if not name or len(name) < 4:
            return None

        start_raw = (eb.get("start") or {}).get("utc") or ""
        start_dt = parse_datetime_to_utc(start_raw)
        if not start_dt:
            return None

        end_raw = (eb.get("end") or {}).get("utc") or ""
        end_dt = parse_datetime_to_utc(end_raw) if end_raw else None

        venue = eb.get("venue") or {}
        location_name = normalize_text(venue.get("name") or "")
        address_obj = venue.get("address") or {}
        location_address = normalize_text(
            address_obj.get("localized_address_display") or
            address_obj.get("address_1") or ""
        )

        organizer = normalize_text((eb.get("organizer") or {}).get("name") or "")
        description = normalize_text((eb.get("description") or {}).get("text") or "")
        ticket_url = sanitize_url(eb.get("url") or "")
        discount_text = extract_discount_text(f"{name} {description}")
        external_id = stable_external_id(self.source_name, ticket_url or name, name, start_dt)

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

    # ------------------------------------------------------------------
    # Strategy 2: Public discovery API (no auth)
    # ------------------------------------------------------------------

    def _fetch_via_discovery_api(self) -> list[ScrapedEvent]:
        headers = {
            "User-Agent": Config.SCRAPE_USER_AGENT,
            "Accept": "application/json",
            "Referer": "https://www.eventbrite.com/",
        }
        try:
            resp = requests.get(
                _EB_DISCOVERY_URL,
                headers=headers,
                timeout=Config.SCRAPE_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        events: list[ScrapedEvent] = []
        for eb in data.get("events", []):
            event = self._parse_discovery_event(eb)
            if event:
                events.append(event)
        return events

    def _parse_discovery_event(self, eb: dict) -> ScrapedEvent | None:
        name = normalize_text(eb.get("name") or "")
        if not name or len(name) < 4:
            return None

        start_raw = eb.get("start_date") or eb.get("start_time") or ""
        if not start_raw:
            # Sometimes it's nested
            start_raw = (eb.get("primary_venue") or {}).get("start_date") or ""
        start_dt = parse_datetime_to_utc(start_raw)
        if not start_dt:
            return None

        venue = eb.get("primary_venue") or {}
        location_name = normalize_text(venue.get("name") or "")
        address_obj = venue.get("address") or {}
        location_address = normalize_text(
            address_obj.get("localized_address_display") or
            address_obj.get("address_1") or ""
        )

        organizer = normalize_text((eb.get("primary_organizer") or {}).get("name") or "")
        description = normalize_text(eb.get("summary") or "")
        ticket_url = sanitize_url(eb.get("url") or "")
        discount_text = extract_discount_text(f"{name} {description}")
        external_id = stable_external_id(self.source_name, ticket_url or name, name, start_dt)

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
            end_time_utc=None,
            ticket_url=ticket_url,
            discount_text=discount_text,
            discount_url=ticket_url if discount_text else "",
        )

    # ------------------------------------------------------------------
    # Strategy 3: Scrape embedded JSON from HTML listing pages
    # ------------------------------------------------------------------

    def _fetch_via_html_pages(self) -> list[ScrapedEvent]:
        headers = {
            "User-Agent": Config.SCRAPE_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        events: list[ScrapedEvent] = []
        for url in _EB_LISTING_PAGES:
            try:
                resp = requests.get(url, headers=headers, timeout=Config.SCRAPE_TIMEOUT_SECONDS)
                resp.raise_for_status()
                events.extend(self._parse_html_page(resp.text))
            except Exception:
                continue
        return events

    # Pattern that Eventbrite embeds in script tags: window.__SERVER_DATA__ = {...}
    _SERVER_DATA_RE = re.compile(
        r"window\.__SERVER_DATA__\s*=\s*(\{.+?\});\s*(?:window\.|</script>)", re.DOTALL
    )
    # Also look for JSON-LD Event blocks
    _JSONLD_RE = re.compile(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )

    def _parse_html_page(self, html: str) -> list[ScrapedEvent]:
        events: list[ScrapedEvent] = []

        # Try window.__SERVER_DATA__ blob
        match = self._SERVER_DATA_RE.search(html)
        if match:
            try:
                server_data = json.loads(match.group(1))
                search_data = (
                    server_data.get("search_data") or
                    server_data.get("searchData") or {}
                )
                eb_events = (
                    search_data.get("events", {}).get("results") or
                    search_data.get("events") or
                    server_data.get("events") or
                    []
                )
                for eb in (eb_events if isinstance(eb_events, list) else []):
                    event = self._parse_discovery_event(eb)
                    if event:
                        events.append(event)
            except (json.JSONDecodeError, AttributeError):
                pass

        # Try JSON-LD blocks
        for raw in self._JSONLD_RE.findall(html):
            try:
                data = json.loads(raw.strip())
            except json.JSONDecodeError:
                continue

            items = data if isinstance(data, list) else [data]
            for item in items:
                eb_type = item.get("@type", "")
                if isinstance(eb_type, str) and eb_type.lower() == "event":
                    event = self._parse_jsonld_event(item)
                    if event:
                        events.append(event)

        return events

    def _parse_jsonld_event(self, item: dict) -> ScrapedEvent | None:
        name = normalize_text(item.get("name") or "")
        if not name or len(name) < 4:
            return None

        start_dt = parse_datetime_to_utc(item.get("startDate"))
        if not start_dt:
            return None

        end_dt = parse_datetime_to_utc(item.get("endDate")) if item.get("endDate") else None

        location = item.get("location") or {}
        location_name = normalize_text(location.get("name") or "")
        address = location.get("address") or {}
        if isinstance(address, dict):
            location_address = normalize_text(
                address.get("streetAddress") or
                address.get("addressLocality") or ""
            )
        else:
            location_address = normalize_text(str(address))

        organizer = item.get("organizer") or {}
        organizer_name = normalize_text(
            organizer.get("name") if isinstance(organizer, dict) else str(organizer)
        )

        offers = item.get("offers") or {}
        ticket_url = sanitize_url(
            (offers.get("url") if isinstance(offers, dict) else "") or
            item.get("url") or ""
        )

        description = normalize_text(item.get("description") or "")
        discount_text = extract_discount_text(f"{name} {description}")
        external_id = stable_external_id(self.source_name, ticket_url or name, name, start_dt)

        return ScrapedEvent(
            external_id=external_id,
            name=name,
            description=description,
            source_name=self.source_name,
            organizer=organizer_name,
            location_name=location_name,
            location_address=location_address,
            map_url=build_map_url(location_name, location_address),
            start_time_utc=start_dt,
            end_time_utc=end_dt,
            ticket_url=ticket_url,
            discount_text=discount_text,
            discount_url=ticket_url if discount_text else "",
        )
