from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import requests

from app.config import settings


def fetch_html(url: str) -> str:
    response = requests.get(
        url,
        timeout=settings.request_timeout_seconds,
        headers={"User-Agent": settings.request_user_agent}
    )
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
