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
EVENT_CONTAINER_HINTS = (
    "event",
    "events",
    "calendar",
    "listing",
    "programme",
    "program",
    "schedule",
    "upcoming",
    "whatson",
    "what-s-on",
)
DISCOUNT_MARKERS = ("discount", "early bird", "promo", "coupon", "save", "off", "%")
LOW_QUALITY_TITLES = {
    "play",
    "all events",
    "events",
    "events in hong kong",
    "hong kong events",
    "things to do",
    "what's on",
    "whats on",
    "read more",
    "staff recommendation",
}
LOW_QUALITY_TITLE_PATTERNS = (
    r"^best\s+",
    r"^events?\s+in\s+hong\s+kong$",
    r"^hong\s+kong\s+events?$",
    r"^events?\s*[|:-]\s+",
    r"^(?:early|mid|late)\s+[a-z]{3,9}$",
    r"^(?:this|next)\s+(?:week|weekend|month)$",
    r"\bwhere to go\b",
    r"\bguide\b",
    r"\bthings to do\b",
    r"\barchive\b",
)
CARD_DATE_PATTERNS = (
    r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}(?:\s+\d{1,2}(?::\d{2})?(?:\s?[APMapm]{2})?)?",
    r"\b[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}(?:\s+\d{1,2}(?::\d{2})?(?:\s?[APMapm]{2})?)?",
    r"\b\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?",
    r"\b(?:Mon|Tue|Tues|Wed|Thu|Thur|Fri|Sat|Sun)(?:day)?\s*,?\s+\d{1,2}\s+[A-Za-z]{3,9}(?:\s+\d{4})?(?:\s+\d{1,2}(?::\d{2})?(?:\s?[APMapm]{2})?)?",
    r"\b\d{1,2}\s*[-/]\s*\d{1,2}\s+[A-Za-z]{3,9}(?:\s+\d{4})?(?:\s+\d{1,2}(?::\d{2})?(?:\s?[APMapm]{2})?)?",
    r"\b[A-Za-z]{3,9}\s+\d{1,2}(?:\s*[-/]\s*\d{1,2})?(?:,?\s+\d{4})?(?:\s+\d{1,2}(?::\d{2})?(?:\s?[APMapm]{2})?)?",
)
DATE_ATTRIBUTE_NAMES = (
    "datetime",
    "date",
    "data-date",
    "data-start",
    "data-start-date",
    "data-start-time",
    "data-event-date",
    "content",
)
MONTH_SLUGS = {
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
}


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
            source_url=page_url,
            price_text=extract_price_text(f"{name} {description}"),
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
                detail_event = self._extract_detail_page_event(detail_url, detail_html)
                if detail_event:
                    events.append(detail_event)

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
            if is_listing_like_event_url(absolute):
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
            has_event_marker = any(marker in context for marker in EVENT_LINK_MARKERS + EVENT_CONTAINER_HINTS)
            has_date = self._parse_card_start(node) is not None
            has_link = node.find("a", href=True) is not None
            if not has_event_marker and not (has_date and has_link):
                continue

            event = self._card_to_event(page_url, node)
            if event:
                events.append(event)

        return events

    def _extract_detail_page_event(self, page_url: str, html: str) -> ScrapedEvent | None:
        soup = BeautifulSoup(html, "html.parser")
        root = soup.find("main") or soup.find("article") or soup.body
        if not isinstance(root, Tag):
            return None

        title_tag = root.find(["h1", "h2"]) or soup.find("meta", property="og:title")
        title = ""
        if isinstance(title_tag, Tag):
            title = normalize_text(title_tag.get_text(" ", strip=True) or title_tag.get("content") or "")
        if len(title) < 4 or is_low_quality_title(title):
            return None

        start_time = self._parse_card_start(root)
        if not start_time:
            return None

        paragraphs = [normalize_text(tag.get_text(" ", strip=True)) for tag in root.find_all(["p", "li"], limit=8)]
        description = " ".join(text for text in paragraphs if text)[:500]
        if not description:
            meta_description = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
            if isinstance(meta_description, Tag):
                description = normalize_text(meta_description.get("content") or "")[:500]
        location_name = extract_location_from_node(root)
        page_text = root.get_text(" ", strip=True)
        price_text = extract_price_text(page_text)
        discount_text = extract_discount_text(page_text)
        ticket_url = extract_preferred_ticket_url(root, page_url)

        external_id = stable_external_id(self.source_name, page_url, title, start_time)
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
            ticket_url=ticket_url,
            discount_text=discount_text,
            discount_url=ticket_url if discount_text and ticket_url else "",
            source_url=page_url,
            price_text=price_text,
        )

    def _card_to_event(self, page_url: str, node: Tag) -> ScrapedEvent | None:
        title_tag, title = find_title_candidate(node)
        if title_tag is None:
            return None

        event_url = ""
        link_tag = title_tag if title_tag.name == "a" and title_tag.get("href") else title_tag.find("a", href=True)
        if link_tag is None:
            link_tag = find_best_anchor_for_title(node, title)
        if link_tag is None:
            link_tag = node.find("a", href=True)
        if link_tag:
            event_url = sanitize_url(urljoin(page_url, link_tag["href"].strip()))

        start_time = self._parse_card_start(node)
        if not start_time:
            return None

        description_tag = node.find("p")
        description = normalize_text(description_tag.get_text(" ", strip=True) if description_tag else "")
        price_text = extract_price_text(node.get_text(" ", strip=True))

        location_name = ""
        for cls in ("location", "venue", "place", "address"):
            loc = node.find(attrs={"class": re.compile(cls, re.I)})
            if loc:
                location_name = clean_location_text(loc.get_text(" ", strip=True))
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
            source_url=event_url or page_url,
            price_text=price_text,
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

        for tag in node.find_all(True):
            for attr_name in DATE_ATTRIBUTE_NAMES:
                raw = tag.get(attr_name)
                if raw and isinstance(raw, str):
                    candidates.append(raw)

        node_text = node.get_text(" ", strip=True)
        for pattern in CARD_DATE_PATTERNS:
            match = re.search(pattern, node_text)
            if match:
                candidates.append(match.group(0))

        for raw in candidates:
            parsed = parse_datetime_to_utc(raw)
            if parsed:
                return parsed
        return None


class ConfiguredSourceScraper(MultiStrategyEventScraper):
    def __init__(self, definition):
        super().__init__(source_name=definition.key, urls=definition.urls, max_detail_pages=definition.max_detail_pages)
        self.definition = definition

    def _discover_event_links(self, page_url: str, html: str) -> list[str]:
        links = super()._discover_event_links(page_url, html)
        markers = self.definition.detail_markers
        if not markers:
            filtered = links
        else:
            filtered = [link for link in links if any(marker in link.lower() for marker in markers)]
        required = self.definition.required_url_substrings
        if required:
            filtered = [link for link in filtered if any(token in link.lower() for token in required)]
        if filtered:
            return filtered
        if required:
            required_fallback = [link for link in links if any(token in link.lower() for token in required)]
            if required_fallback:
                return required_fallback
        return filtered or links

    def _extract_generic_cards(self, page_url: str, html: str) -> list[ScrapedEvent]:
        soup = BeautifulSoup(html, "html.parser")
        selector = self.definition.card_selector
        nodes = soup.select(selector)[:400] if selector else soup.find_all(["article", "li", "section", "div"], limit=400)
        events: list[ScrapedEvent] = []

        for node in nodes:
            if not isinstance(node, Tag):
                continue
            event = self._card_to_event(page_url, node)
            if event:
                if self.definition.category_hint and not event.description:
                    event.description = f"{self.definition.category_hint.title()} listing from {self.definition.label}"
                events.append(event)
        return events

    def _extract_detail_page_event(self, page_url: str, html: str) -> ScrapedEvent | None:
        event = super()._extract_detail_page_event(page_url, html)
        if not event:
            return None

        soup = BeautifulSoup(html, "html.parser")
        root = soup.find("main") or soup.find("article") or soup.body
        if isinstance(root, Tag):
            location_name = event.location_name
            if not location_name:
                for selector in self.definition.location_selectors:
                    tag = root.select_one(selector)
                    if tag:
                        location_name = clean_location_text(tag.get_text(" ", strip=True))
                        break
            if not location_name:
                location_name = extract_location_from_node(root)

            event.location_name = location_name
            event.map_url = build_map_url(location_name, "")

            if self.definition.category_hint and not event.description:
                event.description = f"{self.definition.category_hint.title()} listing from {self.definition.label}"

        event.source_name = self.definition.label
        return event

    def _card_to_event(self, page_url: str, node: Tag) -> ScrapedEvent | None:
        title_tag, title = find_title_candidate(node, self.definition.title_selector)
        if title_tag is None:
            return super()._card_to_event(page_url, node)

        link_tag = title_tag if title_tag.name == "a" and title_tag.get("href") else title_tag.find("a", href=True)
        if link_tag is None:
            link_tag = find_best_anchor_for_title(node, title)
        if link_tag is None:
            link_tag = node.find("a", href=True)
        event_url = sanitize_url(urljoin(page_url, link_tag["href"].strip())) if link_tag and link_tag.get("href") else ""
        if self.definition.required_url_substrings and event_url:
            if not any(token in event_url.lower() for token in self.definition.required_url_substrings):
                return None

        start_time = self._parse_card_start(node)
        if not start_time:
            extra_candidates = []
            for selector in self.definition.date_selectors:
                for tag in node.select(selector):
                    text = tag.get("datetime") or tag.get_text(" ", strip=True)
                    if text:
                        extra_candidates.append(text)
            for raw in extra_candidates:
                parsed = parse_datetime_to_utc(raw)
                if parsed:
                    start_time = parsed
                    break
        if not start_time:
            return None

        description = normalize_text(node.get_text(" ", strip=True))
        location_name = ""
        for selector in self.definition.location_selectors:
            tag = node.select_one(selector)
            if tag:
                location_name = clean_location_text(tag.get_text(" ", strip=True))
                break

        discount_text = extract_discount_text(description)
        price_text = extract_price_text(description)
        external_id = stable_external_id(self.source_name, event_url or page_url, title, start_time)
        return ScrapedEvent(
            external_id=external_id,
            name=title,
            description=description[:500],
            source_name=self.definition.label,
            organizer="",
            location_name=location_name,
            location_address="",
            map_url=build_map_url(location_name, ""),
            start_time_utc=start_time,
            end_time_utc=None,
            ticket_url=event_url,
            discount_text=discount_text,
            discount_url=event_url if discount_text else "",
            source_url=event_url or page_url,
            price_text=price_text,
        )


def parse_datetime_to_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = dt_parser.parse(value, fuzzy=True)
    except Exception:
        return None

    has_explicit_year = bool(re.search(r"\b\d{4}\b", value))
    cleaned_value = re.sub(r"\b(to|until)\b.*$", "", value, flags=re.I).strip()
    if cleaned_value != value:
        try:
            parsed = dt_parser.parse(cleaned_value, fuzzy=True)
        except Exception:
            pass
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
        return clean_location_text(raw_location), ""

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

    return clean_location_text(name), clean_location_text(address_str)


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


def extract_price_text(text: str) -> str:
    match = re.search(r"\b(?:hk\$|\$)\s?\d[\d,]*(?:\.\d{2})?\b", text, flags=re.I)
    if match:
        return match.group(0).upper().replace("HK$", "HK$")
    range_match = re.search(r"\b(?:from|starting at)\s+(hk\$|\$)\s?\d[\d,]*(?:\.\d{2})?\b", text, flags=re.I)
    if range_match:
        return range_match.group(0).replace("starting at", "Starting at").replace("from", "From")
    if re.search(r"\bfree entry\b|\bfree\b", text, flags=re.I):
        return "Free"
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


def extract_location_from_node(node: Tag) -> str:
    for selector in (
        ".location",
        ".venue",
        ".place",
        ".address",
        "[class*=location]",
        "[class*=venue]",
        "[class*=place]",
    ):
        tag = node.select_one(selector)
        if tag:
            text = clean_location_text(tag.get_text(" ", strip=True))
            if text:
                return text

    text = node.get_text(" ", strip=True)
    match = re.search(
        r"\b(?:at|venue|location)\s*[:\-]?\s*([A-Z][A-Za-z0-9&'().,\-/ ]{3,80})",
        text,
        flags=re.I,
    )
    if match:
        location = clean_location_text(match.group(1))
        return re.split(r"\b(?:tickets?|price|free|register|more info)\b", location, maxsplit=1, flags=re.I)[0].strip(" ,:-")
    return ""


def clean_location_text(value: str) -> str:
    text = normalize_text(value)
    if not text:
        return ""

    text = re.sub(r"\b\d+(?:\.\d+)?\s*km\b", "", text, flags=re.I).strip(" ,:-")
    if not text:
        return ""
    if len(text) > 60:
        return ""
    if text[0].islower():
        return ""
    return text


def extract_preferred_ticket_url(node: Tag, page_url: str) -> str:
    page_domain = urlparse(page_url).netloc
    preferred_markers = ("official", "ticket", "tickets", "book", "booking", "register", "signup", "buy")

    fallback = page_url
    for anchor in node.find_all("a", href=True):
        href = sanitize_url(urljoin(page_url, anchor["href"].strip()))
        if not href:
            continue
        if fallback == page_url:
            fallback = href

        anchor_text = normalize_text(anchor.get_text(" ", strip=True)).lower()
        anchor_domain = urlparse(href).netloc
        if any(marker in anchor_text for marker in preferred_markers):
            if anchor_domain and anchor_domain != page_domain:
                return href
            if href != page_url:
                fallback = href

    return fallback


def find_title_candidate(node: Tag, preferred_selector: str | None = None) -> tuple[Tag | None, str]:
    heading_candidates: list[Tag] = []
    anchor_candidates: list[Tag] = []

    if preferred_selector:
        for tag in node.select(preferred_selector):
            if not isinstance(tag, Tag):
                continue
            if tag.name in {"h1", "h2", "h3", "h4"} or any(cls in {"entry-title", "card__title"} for cls in tag.get("class", [])):
                heading_candidates.append(tag)
            else:
                anchor_candidates.append(tag)

    for tag in node.find_all(["h1", "h2", "h3", "h4"], limit=8):
        if isinstance(tag, Tag):
            heading_candidates.append(tag)
    for tag in node.find_all("a", href=True, limit=12):
        if isinstance(tag, Tag):
            anchor_candidates.append(tag)

    seen: set[int] = set()
    for tag in heading_candidates + anchor_candidates:
        if id(tag) in seen:
            continue
        seen.add(id(tag))
        if tag.name == "a" and is_non_event_taxonomy_url(tag.get("href") or ""):
            continue

        text = normalize_text(tag.get_text(" ", strip=True))
        if len(text) < 4 or is_low_quality_title(text):
            continue
        if looks_like_date_bucket(text) or looks_like_date_title(text):
            continue
        return tag, text

    return None, ""


def find_best_anchor_for_title(node: Tag, title: str) -> Tag | None:
    normalized_title = normalize_text(title).lower()
    if not normalized_title:
        return None

    best_match: Tag | None = None
    for anchor in node.find_all("a", href=True):
        if is_non_event_taxonomy_url(anchor.get("href") or ""):
            continue
        anchor_text = normalize_text(anchor.get_text(" ", strip=True)).lower()
        if not anchor_text or looks_like_date_bucket(anchor_text) or looks_like_date_title(anchor_text):
            continue
        if anchor_text == normalized_title or normalized_title in anchor_text or anchor_text in normalized_title:
            best_match = anchor
            break
    return best_match


def is_non_event_taxonomy_url(url: str) -> bool:
    lowered = url.lower()
    return any(marker in lowered for marker in ("/event-category/", "/events/location/", "/tag/", "/category/"))


def is_listing_like_event_url(url: str) -> bool:
    parsed = urlparse(url)
    path = (parsed.path or "").lower().rstrip("/")
    if parsed.fragment and path in {"", "/events"} | {f"/events/{month}" for month in MONTH_SLUGS}:
        return True
    if path in {"", "/events"}:
        return True
    if path.startswith("/events/page/") or path.startswith("/events/location/"):
        return True
    if path.startswith("/event-category/") or path.startswith("/category/") or path.startswith("/tag/"):
        return True
    if not path.startswith("/events/"):
        return False

    tail = path[len("/events/") :].strip("/")
    if not tail:
        return True
    if tail in {"this-week", "this-month", "next-month"}:
        return True
    return tail in MONTH_SLUGS


def looks_like_date_bucket(text: str) -> bool:
    normalized = normalize_text(text).lower()
    return bool(re.fullmatch(r"(?:early|mid|late)(?:\s*[~/\-]\s*(?:early|mid|late))?\s+[a-z]{3,9}", normalized))


def looks_like_date_title(text: str) -> bool:
    normalized = normalize_text(text)
    compact = re.sub(r"\s+", " ", normalized).strip()
    if not compact:
        return False

    patterns = (
        r"^(?:mon|tue|tues|wed|thu|thur|fri|sat|sun)(?:day)?,?\s+[A-Za-z]{3,9}\s+\d{1,2}(?:,?\s+\d{4})?(?:,?\s+\d{1,2}:\d{2}\s*(?:am|pm))?$",
        r"^(?:mon|tue|tues|wed|thu|thur|fri|sat|sun)(?:day)?,?\s+\d{1,2}\s+[A-Za-z]{3,9}(?:\s+\d{4})?(?:,?\s+\d{1,2}:\d{2}\s*(?:am|pm))?$",
        r"^[A-Za-z]{3,9}\s+\d{1,2}(?:,?\s+\d{4})?$",
        r"^[A-Za-z]{3,9}\s+\d{1,2}\s*[-~/]\s*[A-Za-z]{3,9}\s+\d{1,2}(?:\s+\d{4})?$",
        r"^\d{1,2}\s+[A-Za-z]{3,9}\s*[-~/]\s*\d{1,2}\s+[A-Za-z]{3,9}(?:\s+\d{4})?$",
        r"^[A-Za-z]{3,9}\s+\d{4}$",
    )
    return any(re.fullmatch(pattern, compact, flags=re.I) for pattern in patterns)
