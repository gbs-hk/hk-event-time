from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ScrapedEvent:
    external_id: str
    name: str
    description: str
    source_name: str
    organizer: str
    location_name: str
    location_address: str
    map_url: str
    start_time_utc: datetime
    end_time_utc: datetime | None
    ticket_url: str
    discount_text: str
    discount_url: str
    source_url: str = ""
    price_text: str = ""


class BaseScraper:
    source_name: str

    def fetch(self) -> list[ScrapedEvent]:
        raise NotImplementedError
