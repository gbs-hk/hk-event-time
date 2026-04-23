from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RawEvent:
    title: str
    start_raw: str | None
    end_raw: str | None = None
    location: str | None = None
    organizer: str | None = None
    description: str | None = None
    ticket_url: str | None = None
    discount_text: str | None = None
    discount_url: str | None = None
    tags: list[str] | None = None
    external_id: str | None = None
