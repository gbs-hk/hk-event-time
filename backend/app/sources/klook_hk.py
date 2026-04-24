import requests

from app.config import settings
from app.sources.common import extract_basic_cards, fetch_html
from app.sources.types import RawEvent

SOURCE_URL = "https://www.klook.com/en-HK/city/2-hong-kong-things-to-do/"


def _fetch_klook_html() -> str:
    """Fetch Klook HTML; use curl_cffi on 403 (TLS/browser impersonation)."""
    try:
        return fetch_html(SOURCE_URL)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 403:
            from curl_cffi import requests as curl_requests
            resp = curl_requests.get(
                SOURCE_URL,
                timeout=settings.request_timeout_seconds,
                impersonate="chrome124",
            )
            resp.raise_for_status()
            return resp.text
        raise


def fetch_events() -> list[RawEvent]:
    html = _fetch_klook_html()
    cards = extract_basic_cards(SOURCE_URL, html)
    events: list[RawEvent] = []
    for card in cards:
        title = card["title"]
        if not title:
            continue
        events.append(
            RawEvent(
                title=title,
                start_raw=card["start_raw"],
                location=card["location"],
                description=card["description"],
                ticket_url=card["ticket_url"],
                tags=["klook"],
                discount_text="Check Klook for limited-time offers",
                discount_url=card["ticket_url"]
            )
        )
    return events
