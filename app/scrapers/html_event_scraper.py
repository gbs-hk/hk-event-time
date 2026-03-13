from __future__ import annotations

import html
import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus, urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup, Tag
from dateutil import parser as dt_parser

from ..config import Config
from .base import BaseScraper, ScrapedEvent

HK_TZ = ZoneInfo("Asia/Hong_Kong")
EVENT_LINK_MARKERS = (
    "event",
    "events",
    "festival",
    "concert",
    "show",
    "night",
    "party",
    "whatson",
    "what-s-on",
    "calendar",
    "meetup",
)
DISCOUNT_MARKERS = ("discount", "early bird", "promo", "coupon", "save", "off", "%")
LOW_QUALITY_TITLES = {
    "play",
    "all events",
    "events",
    "things to do",
    "what's on",
    "whats on",
}
LOW_QUALITY_TITLE_PATTERNS = (
    r"^best\s+",
    r"\bwhere to go\b",
    r"\bguide\b",
    r"\bthings to do\b",
)


class JsonLdEventScraper(BaseScraper):
    """Scrapes pages containing JSON-LD Event data."""

    def __init__(self, source_name: str, urls: list[str]):
        self.source_name = source_name
        self.urls = urls

    def fetch(self) -> list[ScrapedEvent]:
        events: list[ScrapedEvent] = []
        for url in self.urls:
            html = self._fetch_html(url)
            if not html:
                continue
            events.extend(self._extract_from_html(url, html))
        return dedupe_events(events)

    def _fetch_html(self, url: str) -> str:
        try:
            response = requests.get(
                url,
                timeout=Config.SCRAPE_TIMEOUT_SECONDS,
                headers={"User-Agent": Config.SCRAPE_USER_AGENT},
            )
            response.raise_for_status()
            return response.text
        except Exception:
            return ""

    def _extract_from_html(self, page_url: str, html: str) -> list[ScrapedEvent]:
        soup = BeautifulSoup(html, "html.parser")
        blocks = soup.find_all("script", attrs={"type": "application/ld+json"})
        events: list[ScrapedEvent] = []

        for block in blocks:
            raw = (block.string or block.get_text() or "").strip()
            if not raw:
                continue

            for event_obj in iter_jsonld_event_objects(raw):
                event = self._from_json_ld(event_obj, page_url)
                if event:
                    events.append(event)

        return events

    def _from_json_ld(self, item: dict, page_url: str) -> ScrapedEvent | None:
        name = normalize_text(item.get("name") or "")
        start = item.get("startDate")
        if not name or not start:
            return None

        if is_low_quality_title(name):
            return None

        start_dt = parse_datetime_to_utc(start)
        if not start_dt:
            return None

        end_dt = parse_datetime_to_utc(item.get("endDate")) if item.get("endDate") else None

        location_name, location_address = extract_location(item.get("location"))
        ticket_url = extract_ticket_url(item.get("offers"))
        description = normalize_text(item.get("description") or "")

        external_id = stable_external_id(self.source_name, page_url, name, start_dt)
        discount_text = extract_discount_text(f"{name} {description}")
        return ScrapedEvent(
            external_id=external_id,
            name=name,
            description=description,
            source_name=self.source_name,
            organizer=extract_organizer(item.get("organizer")),
            location_name=location_name,
            location_address=location_address,
            map_url=build_map_url(location_name, location_address),
            start_time_utc=start_dt,
            end_time_utc=end_dt,
            ticket_url=ticket_url,
            discount_text=discount_text,
            discount_url=ticket_url if discount_text else "",
        )


class MultiStrategyEventScraper(JsonLdEventScraper):
    """
    Attempts multiple extraction strategies per source:
    1. JSON-LD Event schema
    2. Generic listing-card extraction
    3. Event-like detail links + JSON-LD extraction
    """

    def __init__(self, source_name: str, urls: list[str], max_detail_pages: int | None = None):
        super().__init__(source_name, urls)
        self.max_detail_pages = max_detail_pages or Config.SCRAPE_MAX_DETAIL_PAGES_PER_SOURCE

    def fetch(self) -> list[ScrapedEvent]:
        events: list[ScrapedEvent] = []

        for url in self.urls:
            html = self._fetch_html(url)
            if not html:
                continue

            # Strategy 1: direct JSON-LD on listing page
            events.extend(self._extract_from_html(url, html))

            # Strategy 2: generic listing card parsing for non-schema pages
            events.extend(self._extract_generic_cards(url, html))

            # Strategy 3: follow event-like detail links and parse JSON-LD there
            detail_links = self._discover_event_links(url, html)
            for detail_url in detail_links[: self.max_detail_pages]:
                detail_html = self._fetch_html(detail_url)
                if not detail_html:
                    continue
                events.extend(self._extract_from_html(detail_url, detail_html))

        return dedupe_events(events)

    def _discover_event_links(self, page_url: str, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        page_domain = urlparse(page_url).netloc

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            text = anchor.get_text(" ", strip=True).lower()
            absolute = urljoin(page_url, href)
            parsed = urlparse(absolute)

            if parsed.scheme not in {"http", "https"}:
                continue
            if parsed.netloc != page_domain:
                continue

            token_bag = f"{parsed.path.lower()} {text}"
            if any(marker in token_bag for marker in EVENT_LINK_MARKERS):
                links.append(absolute)

        # Preserve order while deduping
        seen = set()
        unique_links = []
        for link in links:
            if link not in seen:
                unique_links.append(link)
                seen.add(link)
        return unique_links

    def _extract_generic_cards(self, page_url: str, html: str) -> list[ScrapedEvent]:
        soup = BeautifulSoup(html, "html.parser")
        candidates = soup.find_all(["article", "li", "section", "div"], limit=400)
        events: list[ScrapedEvent] = []

        for node in candidates:
            if not isinstance(node, Tag):
                continue

            context = " ".join(
                [
                    " ".join(node.get("class", [])),
                    node.get("id", ""),
                    node.get_text(" ", strip=True)[:200].lower(),
                ]
            ).lower()
            if not any(marker in context for marker in EVENT_LINK_MARKERS):
                continue

            event = self._card_to_event(page_url, node)
            if event:
                events.append(event)

        return events

    def _card_to_event(self, page_url: str, node: Tag) -> ScrapedEvent | None:
        title_tag = node.find(["h1", "h2", "h3", "h4", "a"])
        if not title_tag:
            return None

        title = normalize_text(title_tag.get_text(" ", strip=True))
        if len(title) < 4:
            return None
        if is_low_quality_title(title):
            return None

        event_url = ""
        link_tag = node.find("a", href=True)
        if link_tag:
            event_url = sanitize_url(urljoin(page_url, link_tag["href"].strip()))

        start_time = self._parse_card_start(node)
        if not start_time:
            return None

        description_tag = node.find("p")
        description = normalize_text(description_tag.get_text(" ", strip=True) if description_tag else "")

        location_name = ""
        for cls in ("location", "venue", "place", "address"):
            loc = node.find(attrs={"class": re.compile(cls, re.I)})
            if loc:
                location_name = normalize_text(loc.get_text(" ", strip=True))
                break

        external_id = stable_external_id(self.source_name, event_url or page_url, title, start_time)
        combined_text = f"{title} {description}"
        discount_text = extract_discount_text(combined_text)
        return ScrapedEvent(
            external_id=external_id,
            name=title,
            description=description,
            source_name=self.source_name,
            organizer="",
            location_name=location_name,
            location_address="",
            map_url=build_map_url(location_name, ""),
            start_time_utc=start_time,
            end_time_utc=None,
            ticket_url=event_url,
            discount_text=discount_text,
            discount_url=event_url if discount_text else "",
        )

    @staticmethod
    def _parse_card_start(node: Tag) -> datetime | None:
        candidates: list[str] = []

        for time_tag in node.find_all("time"):
            if time_tag.get("datetime"):
                candidates.append(time_tag["datetime"])
            text = time_tag.get_text(" ", strip=True)
            if text:
                candidates.append(text)

        node_text = node.get_text(" ", strip=True)
        regexes = (
            r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}(?:\s+\d{1,2}:\d{2}(?:\s?[APMapm]{2})?)?",
            r"\b[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}(?:\s+\d{1,2}:\d{2}(?:\s?[APMapm]{2})?)?",
            r"\b\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?",
        )
        for pattern in regexes:
            match = re.search(pattern, node_text)
            if match:
                candidates.append(match.group(0))

        for raw in candidates:
            parsed = parse_datetime_to_utc(raw)
            if parsed:
                return parsed
        return None


def parse_datetime_to_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = dt_parser.parse(value, fuzzy=True)
    except Exception:
        return None

    has_explicit_year = bool(re.search(r"\b\d{4}\b", value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=HK_TZ)

    # If the source omits year and the parsed date is already stale,
    # roll it forward to the next year so recurring nightlife dates
    # don't disappear after month rollover.
    now_hk = datetime.now(HK_TZ)
    if not has_explicit_year and parsed < now_hk:
        parsed = parsed.replace(year=parsed.year + 1)

    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def iter_jsonld_event_objects(raw_json: str):
    try:
        data = json.loads(raw_json)
    except Exception:
        return

    stack = [data]
    while stack:
        current = stack.pop()
        if isinstance(current, list):
            stack.extend(current)
            continue
        if not isinstance(current, dict):
            continue

        item_type = current.get("@type")
        if isinstance(item_type, str) and item_type.lower() == "event":
            yield current
        elif isinstance(item_type, list) and any(str(t).lower() == "event" for t in item_type):
            yield current

        for nested_key in ("@graph", "itemListElement", "mainEntity", "events"):
            nested = current.get(nested_key)
            if nested is not None:
                stack.append(nested)


def extract_location(raw_location) -> tuple[str, str]:
    if isinstance(raw_location, str):
        return normalize_text(raw_location), ""

    if not isinstance(raw_location, dict):
        return "", ""

    name = normalize_text(raw_location.get("name") or "")
    address = raw_location.get("address") or {}
    if isinstance(address, str):
        address_str = normalize_text(address)
    elif isinstance(address, dict):
        parts = [
            normalize_text(address.get("streetAddress") or ""),
            normalize_text(address.get("addressLocality") or ""),
            normalize_text(address.get("addressRegion") or ""),
        ]
        address_str = ", ".join(p for p in parts if p)
    else:
        address_str = ""

    return name, address_str


def extract_organizer(raw_organizer) -> str:
    if isinstance(raw_organizer, str):
        return normalize_text(raw_organizer)
    if isinstance(raw_organizer, dict):
        return normalize_text(raw_organizer.get("name") or "")
    return ""


def extract_ticket_url(raw_offers) -> str:
    offers = raw_offers
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if isinstance(offers, dict):
        return sanitize_url(offers.get("url") or offers.get("@id") or "")
    return ""


def extract_discount_text(text: str) -> str:
    lowered = text.lower()
    if any(marker in lowered for marker in DISCOUNT_MARKERS):
        return "Possible discount mentioned on source page"
    return ""


def build_map_url(location_name: str, location_address: str) -> str:
    query = " ".join(part for part in [location_name, location_address] if part).strip()
    if not query:
        return ""
    if len(query) > 120:
        return ""
    return f"https://maps.google.com/?q={quote_plus(query)}"


def stable_external_id(source_name: str, page_url: str, name: str, start_dt_utc: datetime) -> str:
    digest = hashlib.sha256(f"{source_name}|{page_url}|{name}|{start_dt_utc.isoformat()}".encode("utf-8")).hexdigest()[:32]
    return f"{source_name}-{digest}"


def dedupe_events(events: list[ScrapedEvent]) -> list[ScrapedEvent]:
    deduped: dict[str, ScrapedEvent] = {}
    semantic_seen: dict[tuple[str, str, datetime], ScrapedEvent] = {}

    for event in events:
        if is_low_quality_title(event.name):
            continue
        deduped[event.external_id] = event
        semantic_key = make_semantic_key(event)
        if semantic_key not in semantic_seen:
            semantic_seen[semantic_key] = event
            continue

        # Keep richer version if same event appears in both list/detail pages.
        existing = semantic_seen[semantic_key]
        if richness_score(event) > richness_score(existing):
            semantic_seen[semantic_key] = event

    semantic_ids = {event.external_id for event in semantic_seen.values()}
    return [event for event in deduped.values() if event.external_id in semantic_ids]


def normalize_text(value: str) -> str:
    text = html.unescape(value or "")
    return " ".join(text.split()).strip()


def sanitize_url(value: str) -> str:
    url = (value or "").strip()
    if not url:
        return ""
    lowered = url.lower()
    if lowered.startswith("javascript:") or lowered.startswith("mailto:"):
        return ""
    return url


def is_low_quality_title(title: str) -> bool:
    normalized = normalize_text(title).lower()
    if not normalized:
        return True
    if normalized in LOW_QUALITY_TITLES:
        return True
    if re.fullmatch(r"(all\s+)?events?", normalized):
        return True
    if any(re.search(pattern, normalized) for pattern in LOW_QUALITY_TITLE_PATTERNS):
        return True
    return len(normalized) < 4


def make_semantic_key(event: ScrapedEvent) -> tuple[str, str, datetime]:
    normalized_name = re.sub(r"[^a-z0-9]+", " ", event.name.lower()).strip()
    normalized_location = re.sub(r"[^a-z0-9]+", " ", event.location_name.lower()).strip()
    start_bucket = event.start_time_utc.replace(minute=0, second=0, microsecond=0)
    return normalized_name, normalized_location, start_bucket


def richness_score(event: ScrapedEvent) -> int:
    return sum(
        1
        for field in [
            event.description,
            event.location_name,
            event.location_address,
            event.map_url,
            event.ticket_url,
            event.discount_text,
            event.organizer,
        ]
        if field
    )
