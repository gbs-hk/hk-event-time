from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import time
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.categories import CATEGORY_DEFINITIONS, category_by_slug
from app.categorize import categorize_event
from app.models import Category, Event, Source
from app.sources import eventbrite_hk, hktb, klook_hk, meetup_hk, ticketflap, timeout_hk
from app.sources.common import safe_parse_datetime
from app.sources.types import RawEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceAdapter:
    name: str
    base_url: str
    rate_limit_ms: int
    parser_version: str
    fetcher: Callable[[], list[RawEvent]]


SOURCE_ADAPTERS: tuple[SourceAdapter, ...] = (
    SourceAdapter("Time Out Hong Kong", timeout_hk.SOURCE_URL, 900, "1.0", timeout_hk.fetch_events),
    SourceAdapter("Hong Kong Tourism Board", hktb.SOURCE_URL, 900, "1.0", hktb.fetch_events),
    SourceAdapter("Eventbrite Hong Kong", eventbrite_hk.SOURCE_URL, 1200, "1.0", eventbrite_hk.fetch_events),
    SourceAdapter("Meetup Hong Kong", meetup_hk.SOURCE_URL, 1200, "1.0", meetup_hk.fetch_events),
    SourceAdapter("Ticketflap", ticketflap.SOURCE_URL, 1000, "1.0", ticketflap.fetch_events),
    SourceAdapter("Klook Hong Kong", klook_hk.SOURCE_URL, 1000, "1.0", klook_hk.fetch_events)
)

DISCOUNT_MARKERS: tuple[str, ...] = (
    "%",
    "off",
    "discount",
    "promo",
    "early-bird",
    "early bird",
    "deal"
)


def ensure_categories(db: Session) -> dict[str, Category]:
    existing = {category.slug: category for category in db.scalars(select(Category)).all()}
    for config in CATEGORY_DEFINITIONS:
        if config.slug in existing:
            continue
        category = Category(name=config.name, slug=config.slug, color=config.color, icon=config.icon)
        db.add(category)
        db.flush()
        existing[config.slug] = category
    return existing


def ensure_sources(db: Session) -> dict[str, Source]:
    existing = {source.name: source for source in db.scalars(select(Source)).all()}
    for adapter in SOURCE_ADAPTERS:
        if adapter.name in existing:
            source = existing[adapter.name]
            source.base_url = adapter.base_url
            source.rate_limit_ms = adapter.rate_limit_ms
            source.parser_version = adapter.parser_version
            source.is_active = True
            continue

        source = Source(
            name=adapter.name,
            base_url=adapter.base_url,
            rate_limit_ms=adapter.rate_limit_ms,
            parser_version=adapter.parser_version,
            is_active=True
        )
        db.add(source)
        db.flush()
        existing[source.name] = source
    return existing


def normalize_datetime(raw: str | None) -> datetime:
    dt = safe_parse_datetime(raw)
    if dt is None:
        # fallback gives upcoming events a deterministic date for parsing failures
        return datetime.now(timezone.utc) + timedelta(days=3)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def build_external_id(source_name: str, event: RawEvent, start_dt: datetime) -> str:
    identity = "||".join(
        [
            source_name,
            (event.title or "").strip().lower(),
            start_dt.isoformat(),
            (event.ticket_url or "").strip().lower(),
            (event.location or "").strip().lower()
        ]
    )
    return hashlib.sha1(identity.encode("utf-8")).hexdigest()


def upsert_event(
    db: Session,
    source: Source,
    category: Category | None,
    event: RawEvent,
    start_dt: datetime,
    end_dt: datetime | None
) -> Event:
    external_id = event.external_id or build_external_id(source.name, event, start_dt)
    existing = db.scalar(
        select(Event).where(Event.source_id == source.id, Event.external_id == external_id)
    )
    if existing:
        existing.name = event.title
        existing.start_datetime = start_dt
        existing.end_datetime = end_dt
        existing.location = event.location
        existing.organizer = event.organizer
        existing.description = event.description
        existing.ticket_url = event.ticket_url
        existing.discount_text = event.discount_text or infer_discount_text(event.description)
        existing.discount_url = event.discount_url
        existing.tags = event.tags or []
        existing.category_id = category.id if category else None
        existing.last_seen_at = datetime.now(timezone.utc)
        return existing

    created = Event(
        name=event.title,
        start_datetime=start_dt,
        end_datetime=end_dt,
        location=event.location,
        organizer=event.organizer,
        description=event.description,
        ticket_url=event.ticket_url,
        discount_text=event.discount_text or infer_discount_text(event.description),
        discount_url=event.discount_url,
        tags=event.tags or [],
        external_id=external_id,
        source_id=source.id,
        category_id=category.id if category else None,
        last_seen_at=datetime.now(timezone.utc)
    )
    db.add(created)
    return created


def infer_discount_text(description: str | None) -> str | None:
    if not description:
        return None
    description_lower = description.lower()
    if not any(marker in description_lower for marker in DISCOUNT_MARKERS):
        return None
    snippet = description.strip()
    if len(snippet) > 200:
        snippet = f"{snippet[:197]}..."
    return snippet


def scrape_all_sources(db: Session) -> dict[str, int]:
    category_map = ensure_categories(db)
    ensure_sources(db)
    source_map = {source.name: source for source in db.scalars(select(Source).where(Source.is_active.is_(True))).all()}

    category_index = category_by_slug()
    inserted_or_updated = 0
    source_errors = 0

    for adapter in SOURCE_ADAPTERS:
        source = source_map.get(adapter.name)
        if source is None:
            continue

        try:
            raw_events = adapter.fetcher()
        except Exception:
            logger.exception("scrape failed for source=%s", adapter.name)
            source_errors += 1
            continue

        for raw_event in raw_events:
            if not raw_event.title:
                continue

            start_dt = normalize_datetime(raw_event.start_raw)
            end_dt = normalize_datetime(raw_event.end_raw) if raw_event.end_raw else None
            slug = categorize_event(raw_event.title, raw_event.description, source.name, source.base_url)
            if slug not in category_index:
                slug = "culture"
            category = category_map.get(slug)

            upsert_event(db, source, category, raw_event, start_dt, end_dt)
            inserted_or_updated += 1

        db.commit()
        time.sleep(source.rate_limit_ms / 1000)

    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    db.query(Event).filter(Event.start_datetime < cutoff).delete()
    db.commit()

    return {"processed": inserted_or_updated, "source_errors": source_errors}


def get_events(
    db: Session,
    start: datetime | None = None,
    end: datetime | None = None,
    category_slugs: list[str] | None = None,
    limit: int = 500
) -> list[Event]:
    query = select(Event).options(joinedload(Event.source), joinedload(Event.category))
    if start:
        query = query.where(Event.start_datetime >= start)
    if end:
        query = query.where(Event.start_datetime <= end)
    if category_slugs:
        query = query.join(Event.category).where(Category.slug.in_(category_slugs))

    query = query.order_by(Event.start_datetime.asc()).limit(min(max(limit, 1), 1000))
    return list(db.scalars(query).unique().all())
