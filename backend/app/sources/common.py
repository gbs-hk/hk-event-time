"""Shared helper functions used by every scraper.

Key functions:
  fetch_html()           -- downloads a web page and returns its HTML as a string
  safe_parse_datetime()  -- tries to turn a date string into a Python datetime
  extract_basic_cards()  -- finds event "cards" on a page using common CSS selectors

Each individual scraper (klook_hk.py, timeout_hk.py, ...) imports these
helpers so it does not have to repeat the same boilerplate.
"""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import requests

from app.config import settings

# Session with browser-like defaults; reuse to preserve cookies
_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(_base_headers())
    return _session


def _base_headers() -> dict[str, str]:
    """Browser-like headers shared by all requests."""
    return {
        "User-Agent": settings.request_user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "DNT": "1",
    }


def _headers_for_url(url: str) -> dict[str, str]:
    """Per-request headers (e.g. Referer) so the request looks from that site."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return {"Referer": f"{parsed.scheme}://{parsed.netloc}/"}


def fetch_html(url: str) -> str:
    session = _get_session()
    headers = _headers_for_url(url)
    response = session.get(url, timeout=settings.request_timeout_seconds, headers=headers)
    response.raise_for_status()
    return response.text


def safe_parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return date_parser.parse(value)
    except (ValueError, TypeError, OverflowError):
        pass

    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def extract_basic_cards(base_url: str, html: str, limit: int = 30) -> list[dict[str, str | None]]:
    soup = BeautifulSoup(html, "html.parser")
    cards: list[dict[str, str | None]] = []

    selectors = [
        "article",
        ".event",
        ".event-card",
        ".card",
        ".listing-item"
    ]

    seen: set[str] = set()
    for selector in selectors:
        for node in soup.select(selector):
            link_node = node.select_one("a[href]")
            if not link_node:
                continue

            href = link_node.get("href")
            if not href:
                continue
            url = urljoin(base_url, href)
            if url in seen:
                continue
            seen.add(url)

            title = (link_node.get_text(" ", strip=True) or "").strip()
            if not title:
                header = node.select_one("h1, h2, h3, .title")
                title = (header.get_text(" ", strip=True) if header else "").strip()
            if not title:
                continue

            description_node = node.select_one("p, .description, .summary")
            time_node = node.select_one("time")
            location_node = node.select_one(".location, .venue, [data-location]")

            cards.append(
                {
                    "title": title,
                    "description": description_node.get_text(" ", strip=True) if description_node else None,
                    "start_raw": time_node.get("datetime") if time_node else None,
                    "location": location_node.get_text(" ", strip=True) if location_node else None,
                    "ticket_url": url
                }
            )

            if len(cards) >= limit:
                return cards

    return cards
