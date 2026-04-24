from app.sources.common import extract_basic_cards, fetch_html
from app.sources.types import RawEvent

SOURCE_URL = "https://www.timeout.com/hong-kong/things-to-do"


def fetch_events() -> list[RawEvent]:
    html = fetch_html(SOURCE_URL)
    cards = extract_basic_cards(SOURCE_URL, html)
    return [
        RawEvent(
            title=card["title"] or "",
            start_raw=card["start_raw"],
            location=card["location"],
            description=card["description"],
            ticket_url=card["ticket_url"]
        )
        for card in cards
        if card["title"]
    ]
