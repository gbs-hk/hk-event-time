from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from .categories import CATEGORY_DEFINITIONS, infer_category
from .config import Config
from .database import SessionLocal
from .models import Event
from .scrapers.base import ScrapedEvent
from .scrapers.html_event_scraper import is_low_quality_title, make_semantic_key
from .scrapers.sources import build_scrapers


def upsert_event(scraped: ScrapedEvent, category: str) -> Event:

    with SessionLocal() as session:
        existing = session.scalar(select(Event).where(Event.external_id == scraped.external_id))

        if existing:
            target = existing
        else:
            target = Event(external_id=scraped.external_id)
            session.add(target)

        target.name = scraped.name
        target.category = category
        target.description = scraped.description
        target.source_name = scraped.source_name
        target.organizer = scraped.organizer
        target.location_name = scraped.location_name
        target.location_address = scraped.location_address
        target.map_url = scraped.map_url
        target.start_time_utc = scraped.start_time_utc
        target.end_time_utc = scraped.end_time_utc
        target.ticket_url = scraped.ticket_url
        target.discount_text = scraped.discount_text
        target.discount_url = scraped.discount_url
        target.scraped_at_utc = datetime.utcnow()

        session.commit()
        session.refresh(target)
        return target


def run_scrape() -> dict[str, int]:
    report = run_scrape_detailed()
    return {
        "processed": report["processed"],
        "failed_sources": report["failed_sources"],
        "empty_sources": report["empty_sources"],
        "sources_total": report["sources_total"],
    }


def run_scrape_detailed() -> dict[str, Any]:
    inserted_or_updated = 0
    failed_sources = 0
    empty_sources = 0
    sources_total = 0
    sources: list[dict[str, Any]] = []

    for scraper in build_scrapers():
        sources_total += 1
        source_name = getattr(scraper, "source_name", f"source-{sources_total}")
        source_info: dict[str, Any] = {
            "source_name": source_name,
            "fetched": 0,
            "processed": 0,
            "skipped_past": 0,
            "skipped_duplicate": 0,
            "skipped_category": 0,
            "skipped_quality": 0,
            "status": "ok",
        }

        try:
            events = scraper.fetch()
        except Exception as exc:
            failed_sources += 1
            source_info["status"] = "failed"
            source_info["error"] = str(exc)
            sources.append(source_info)
            continue

        source_info["fetched"] = len(events)
        if not events:
            empty_sources += 1
            source_info["status"] = "empty"
            sources.append(source_info)
            continue

        seen_semantic: set[tuple] = set()
        for scraped in events:
            if scraped.start_time_utc < datetime.utcnow() - timedelta(days=1):
                source_info["skipped_past"] += 1
                continue
            semantic_key = make_semantic_key(scraped)
            if semantic_key in seen_semantic:
                source_info["skipped_duplicate"] += 1
                continue
            seen_semantic.add(semantic_key)
            category = infer_category(scraped.name, scraped.description, scraped.source_name)
            if not should_keep_category(category):
                source_info["skipped_category"] += 1
                continue
            quality = evaluate_event(scraped)
            if quality["rejected"]:
                source_info["skipped_quality"] += 1
                continue

            upsert_event(scraped, category=category)
            inserted_or_updated += 1
            source_info["processed"] += 1

        if source_info["processed"] == 0 and source_info["fetched"] > 0:
            empty_sources += 1
            source_info["status"] = "empty_after_filters"

        sources.append(source_info)

    return {
        "processed": inserted_or_updated,
        "failed_sources": failed_sources,
        "empty_sources": empty_sources,
        "sources_total": sources_total,
        "sources": sources,
    }


def query_events(
    start_utc: datetime,
    end_utc: datetime,
    categories: list[str] | None = None,
) -> list[Event]:
    with SessionLocal() as session:
        stmt = select(Event).where(Event.start_time_utc >= start_utc, Event.start_time_utc <= end_utc)
        if categories:
            stmt = stmt.where(Event.category.in_(categories))
        stmt = stmt.order_by(Event.start_time_utc.asc())
        return list(session.scalars(stmt).all())


def get_color_map() -> dict[str, str]:
    return {slug: cfg.color for slug, cfg in CATEGORY_DEFINITIONS.items()}


def should_keep_category(category: str) -> bool:
    focused = set(Config.SCRAPE_FOCUS_CATEGORIES)
    if not focused:
        return True
    return category in focused


def evaluate_event(event: ScrapedEvent) -> dict[str, Any]:
    reasons: list[str] = []
    score = 0

    if is_low_quality_title(event.name):
        reasons.append("generic_title")
    else:
        score += 25

    if event.description and len(event.description.strip()) >= 40:
        score += 15
    if event.location_name:
        score += 10
    if event.ticket_url:
        score += 10
    if event.map_url:
        score += 5
    if event.organizer:
        score += 5
    if event.discount_text or event.discount_url:
        score += 5

    trusted_markers = (
        "discover hong kong",
        "timeout",
        "time out",
        "urbtix",
        "eventbrite",
        "lan-kwai-fong",
        "luma",
    )
    if any(marker in event.source_name.lower() for marker in trusted_markers):
        score += 10

    if score < 35:
        reasons.append("low_information")

    return {
        "score": score,
        "rejected": bool(reasons),
        "reasons": reasons,
    }


def source_event_counts_upcoming() -> list[dict[str, Any]]:
    cutoff = datetime.utcnow() - timedelta(days=1)
    with SessionLocal() as session:
        rows = session.execute(
            select(Event.source_name, func.count(Event.id))
            .where(Event.start_time_utc >= cutoff)
            .group_by(Event.source_name)
            .order_by(func.count(Event.id).desc())
        ).all()

    return [
        {
            "source_name": source_name,
            "upcoming_events": int(count),
        }
        for source_name, count in rows
    ]
