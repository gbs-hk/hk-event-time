from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    color: str
    icon: str


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    base_url: str


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    start_datetime: datetime
    end_datetime: datetime | None
    location: str | None
    organizer: str | None
    description: str | None
    ticket_url: str | None
    discount_text: str | None
    discount_url: str | None
    tags: list[str]
    last_seen_at: datetime
    category: CategoryOut | None
    source: SourceOut
