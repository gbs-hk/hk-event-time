from app.sources.common import extract_basic_cards, fetch_html
from app.sources.types import RawEvent

SOURCE_URL = "https://www.klook.com/en-HK/city/2-hong-kong-things-to-do/"


def fetch_events() -> list[RawEvent]:
    html = fetch_html(SOURCE_URL)
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
