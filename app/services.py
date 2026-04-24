from __future__ import annotations

import copy
import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError, as_completed
from datetime import UTC, datetime, timedelta
from queue import Empty, Queue
from typing import Any

from sqlalchemy import func, select

from .categories import CATEGORY_DEFINITIONS, infer_category
from .config import Config
from .database import Base, SessionLocal, engine, ensure_schema
from .models import Event, ScrapeRun
from .scrapers.base import ScrapedEvent
from .scrapers.html_event_scraper import (
    is_listing_like_event_url,
    is_low_quality_title,
    looks_like_date_bucket,
    looks_like_date_title,
    make_semantic_key,
    normalize_text,
)
from .scrapers.sample_scraper import SampleHongKongScraper
from .scrapers.sources import build_scrapers, selected_sources

EVENT_QUERY_CACHE: dict[tuple, tuple[datetime, list[Event]]] = {}

SCRAPE_QUEUE: Queue[dict[str, Any]] = Queue()
SCRAPE_STATE_LOCK = threading.Lock()
SCRAPE_JOBS: dict[str, dict[str, Any]] = {}
LAST_COMPLETED_REPORT: dict[str, Any] | None = None
WORKER_STARTED = False
TRUSTED_SOURCE_ALIASES = {
    "urbtix-open-data": {"urbtix-open-data", "urbtix open data"},
    "discover-hk": {"discover-hk", "discover hong kong"},
    "hongkong-cheapo": {"hongkong-cheapo", "hong kong cheapo"},
    "timeout-hk": {"timeout-hk", "time out hong kong"},
    "hkcec": {"hkcec", "hong kong convention and exhibition centre"},
    "lan-kwai-fong": {"lan-kwai-fong", "lan kwai fong"},
}


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def upsert_event(scraped: ScrapedEvent, category: str, quality_score: int) -> Event:
    ensure_schema()
    with SessionLocal() as session:
        existing = session.scalar(select(Event).where(Event.external_id == scraped.external_id))
        if not existing and scraped.source_url:
            existing = session.scalar(
                select(Event)
                .where(Event.source_url == scraped.source_url)
                .where(func.lower(Event.source_name) == normalize_source_name(scraped.source_name))
                .order_by(Event.scraped_at_utc.desc())
            )

        if existing:
            target = existing
        else:
            target = Event(external_id=scraped.external_id)
            session.add(target)

        target.external_id = scraped.external_id
        target.name = scraped.name
        target.category = category
        target.description = scraped.description
        target.source_name = scraped.source_name
        target.source_url = scraped.source_url
        target.organizer = scraped.organizer
        target.location_name = scraped.location_name
        target.location_address = scraped.location_address
        target.map_url = scraped.map_url
        target.start_time_utc = scraped.start_time_utc
        target.end_time_utc = scraped.end_time_utc
        target.ticket_url = scraped.ticket_url
        target.price_text = scraped.price_text
        target.discount_text = scraped.discount_text
        target.discount_url = scraped.discount_url
        target.quality_score = quality_score
        target.scraped_at_utc = utcnow_naive()

        session.commit()
        session.refresh(target)
        clear_event_cache()
        return target


def run_scrape() -> dict[str, int]:
    report = run_scrape_detailed(triggered_by="manual")
    return {
        "processed": report["processed"],
        "failed_sources": report["failed_sources"],
        "empty_sources": report["empty_sources"],
        "sources_total": report["sources_total"],
        "used_sample_fallback": report["used_sample_fallback"],
    }


def run_scrape_detailed(
    triggered_by: str = "manual",
    progress_callback: Any | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    started_at = utcnow_naive()
    inserted_or_updated = 0
    failed_sources = 0
    empty_sources = 0
    rejected_events = 0
    source_reports: list[dict[str, Any]] = []
    used_sample_fallback = False
    scrapers = build_scrapers()
    sources_total = len(scrapers)
    max_workers = max(1, min(Config.SCRAPE_MAX_PARALLEL_SOURCES, sources_total or 1))
    completed_sources = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(fetch_with_retry, scraper): (index, scraper)
            for index, scraper in enumerate(scrapers, start=1)
        }

        for future in as_completed(future_map):
            index, scraper = future_map[future]
            source_name = getattr(scraper, "source_name", f"source-{index}")
            completed_sources += 1
            if progress_callback:
                progress_callback(
                    {
                        "current": completed_sources,
                        "total": sources_total,
                        "message": f"Checked {completed_sources} of {sources_total}: {source_name}",
                        "source_name": source_name,
                    }
                )

            source_info = {
                "source_index": index,
                "source_name": source_name,
                "fetched": 0,
                "processed": 0,
                "skipped_past": 0,
                "skipped_duplicate": 0,
                "skipped_category": 0,
                "rejected_quality": 0,
                "status": "ok",
                "kept": [],
                "rejected": [],
            }

            try:
                raw_events = future.result()
            except Exception as exc:
                failed_sources += 1
                source_info["status"] = "failed"
                source_info["error"] = str(exc)
                source_reports.append(source_info)
                continue

            source_info["fetched"] = len(raw_events)
            if not raw_events:
                empty_sources += 1
                source_info["status"] = "empty"
                source_reports.append(source_info)
                continue

            seen_semantic: set[tuple] = set()
            for scraped in raw_events:
                evaluation = evaluate_event(scraped)
                if evaluation["rejected"]:
                    rejected_events += 1
                    source_info["rejected_quality"] += 1
                    source_info["rejected"].append(event_debug_payload(scraped, evaluation))
                    continue

                if scraped.start_time_utc < utcnow_naive() - timedelta(days=1):
                    source_info["skipped_past"] += 1
                    source_info["rejected"].append(event_debug_payload(scraped, {"score": 0, "reasons": ["past_event"], "rejected": True}))
                    rejected_events += 1
                    continue

                semantic_key = make_semantic_key(scraped)
                if semantic_key in seen_semantic:
                    source_info["skipped_duplicate"] += 1
                    source_info["rejected"].append(event_debug_payload(scraped, {"score": evaluation["score"], "reasons": ["duplicate_in_source"], "rejected": True}))
                    rejected_events += 1
                    continue
                seen_semantic.add(semantic_key)

                category = infer_category(scraped.name, scraped.description, scraped.source_name)
                if not should_keep_category(category):
                    source_info["skipped_category"] += 1
                    source_info["rejected"].append(event_debug_payload(scraped, {"score": evaluation["score"], "reasons": ["category_filtered"], "rejected": True, "category": category}))
                    rejected_events += 1
                    continue

                quality_score = evaluation["score"]
                upsert_event(scraped, category=category, quality_score=quality_score)
                inserted_or_updated += 1
                source_info["processed"] += 1
                source_info["kept"].append(event_debug_payload(scraped, {"score": quality_score, "reasons": evaluation["reasons"], "category": category, "rejected": False}))

            if source_info["processed"] == 0 and source_info["fetched"] > 0:
                empty_sources += 1
                source_info["status"] = "empty_after_filters"

            source_reports.append(source_info)

    source_reports.sort(key=lambda item: item.get("source_index", 0))
    for source_info in source_reports:
        source_info.pop("source_index", None)

    if inserted_or_updated == 0 and not Config.SCRAPE_INCLUDE_SAMPLE:
        sample_count = seed_sample_events()
        if sample_count > 0:
            inserted_or_updated = sample_count
            used_sample_fallback = True
            source_reports.append(
                {
                    "source_name": "sample",
                    "fetched": sample_count,
                    "processed": sample_count,
                    "skipped_past": 0,
                    "skipped_duplicate": 0,
                    "skipped_category": 0,
                    "rejected_quality": 0,
                    "status": "fallback_seeded",
                    "kept": [],
                    "rejected": [],
                }
            )

    purged_invalid = purge_invalid_events()

    report = {
        "processed": inserted_or_updated,
        "failed_sources": failed_sources,
        "empty_sources": empty_sources,
        "sources_total": sources_total,
        "rejected_events": rejected_events,
        "purged_invalid": purged_invalid,
        "sources": source_reports,
        "used_sample_fallback": used_sample_fallback,
        "triggered_by": triggered_by,
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": utcnow_naive().isoformat(),
        "selected_sources": [source.key for source in selected_sources()],
    }
    persist_scrape_run(report, job_id=job_id)
    set_last_completed_report(report)
    return report


def fetch_with_retry(scraper) -> list[ScrapedEvent]:
    attempts = max(1, Config.SCRAPE_RETRY_COUNT + 1)
    last_error: Exception | None = None

    for _attempt in range(1, attempts + 1):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(scraper.fetch)
            try:
                return future.result(timeout=Config.SCRAPE_SOURCE_TIMEOUT_SECONDS)
            except FutureTimeoutError as exc:
                last_error = TimeoutError(f"source timeout after {Config.SCRAPE_SOURCE_TIMEOUT_SECONDS}s")
                future.cancel()
            except Exception as exc:  # noqa: PERF203
                last_error = exc
        if last_error is None:
            break

    if last_error is not None:
        raise last_error
    return []


def evaluate_event(scraped: ScrapedEvent) -> dict[str, Any]:
    score = 0
    reasons: list[str] = []

    if not scraped.name or len(scraped.name.strip()) < 5:
        reasons.append("missing_title")
    else:
        score += 20

    if scraped.description and len(scraped.description) >= 40:
        score += 10
    else:
        reasons.append("thin_description")
        if scraped.description and len(scraped.description) >= 16:
            score += 4

    if scraped.location_name:
        score += 10
    else:
        reasons.append("missing_location")

    if scraped.ticket_url or scraped.source_url:
        score += 10
    else:
        reasons.append("missing_link")

    if scraped.price_text:
        score += 5
    if scraped.organizer:
        score += 5
    if scraped.discount_text:
        score += 3

    if scraped.start_time_utc:
        score += 15
    else:
        reasons.append("missing_start")

    if scraped.end_time_utc:
        score += 4

    lowered = f"{scraped.name} {scraped.description}".lower()
    if "archive" in lowered or "past events" in lowered:
        reasons.append("archive_page")
        score -= 40
    if "events in hong kong" in lowered or scraped.name.lower().strip() in {"events in hong kong", "hong kong events"}:
        reasons.append("generic_title")
        score -= 40

    normalized_source = normalize_source_name(scraped.source_name)
    if any(normalized_source in aliases for aliases in TRUSTED_SOURCE_ALIASES.values()):
        score += 15
    if scraped.source_url and scraped.ticket_url and scraped.source_url != scraped.ticket_url:
        score += 4
    if scraped.location_name and scraped.price_text:
        score += 3
    if len(scraped.name.split()) >= 3:
        score += 4

    rejected = score < Config.SCRAPE_MIN_QUALITY_SCORE or bool(
        {"missing_title", "missing_start", "generic_title", "archive_page"} & set(reasons)
    )
    return {"score": max(score, 0), "reasons": reasons, "rejected": rejected}


def normalize_source_name(source_name: str) -> str:
    return " ".join((source_name or "").strip().lower().replace("-", " ").split())


def event_debug_payload(scraped: ScrapedEvent, evaluation: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": scraped.name,
        "source_name": scraped.source_name,
        "start_time_utc": scraped.start_time_utc.isoformat() if scraped.start_time_utc else None,
        "location_name": scraped.location_name,
        "source_url": scraped.source_url or scraped.ticket_url,
        "price_text": scraped.price_text,
        "quality_score": evaluation.get("score", 0),
        "category": evaluation.get("category", ""),
        "reasons": evaluation.get("reasons", []),
    }


def query_events(
    start_utc: datetime,
    end_utc: datetime,
    categories: list[str] | None = None,
    filters: dict[str, Any] | None = None,
) -> list[Event]:
    category_key = tuple(sorted(categories or []))
    filter_key = tuple(sorted((filters or {}).items()))
    cache_key = (start_utc.isoformat(), end_utc.isoformat(), category_key, filter_key)
    cached = EVENT_QUERY_CACHE.get(cache_key)
    if cached and utcnow_naive() - cached[0] < timedelta(seconds=Config.CACHE_TTL_SECONDS):
        return cached[1]

    with SessionLocal() as session:
        stmt = select(Event).where(Event.start_time_utc >= start_utc, Event.start_time_utc <= end_utc)
        if categories:
            stmt = stmt.where(Event.category.in_(categories))
        if filters:
            if filters.get("free"):
                stmt = stmt.where(func.lower(Event.price_text).like("%free%"))
            if filters.get("district"):
                district = f"%{filters['district'].lower()}%"
                stmt = stmt.where(
                    func.lower(Event.location_name).like(district) | func.lower(Event.location_address).like(district)
                )
            if filters.get("category_slug"):
                stmt = stmt.where(Event.category == filters["category_slug"])
        stmt = stmt.order_by(Event.start_time_utc.asc())
        rows = list(session.scalars(stmt).all())

    EVENT_QUERY_CACHE[cache_key] = (utcnow_naive(), rows)
    return rows


def clear_event_cache() -> None:
    EVENT_QUERY_CACHE.clear()


def get_color_map() -> dict[str, str]:
    return {slug: cfg.color for slug, cfg in CATEGORY_DEFINITIONS.items()}


def should_keep_category(category: str) -> bool:
    focused = set(Config.SCRAPE_FOCUS_CATEGORIES)
    if not focused:
        return True
    return category in focused


def seed_sample_events() -> int:
    inserted = 0
    for scraped in SampleHongKongScraper().fetch():
        category = infer_category(scraped.name, scraped.description, scraped.source_name)
        upsert_event(scraped, category=category, quality_score=90)
        inserted += 1
    return inserted


def purge_invalid_events() -> int:
    ensure_schema()
    removed = 0
    with SessionLocal() as session:
        rows = list(session.scalars(select(Event)).all())
        for row in rows:
            if not is_invalid_persisted_event(row):
                continue
            session.delete(row)
            removed += 1
        if removed:
            session.commit()
            clear_event_cache()
    return removed


def is_invalid_persisted_event(row: Event) -> bool:
    title = normalize_text(row.name)
    if not title:
        return True
    if is_low_quality_title(title) or looks_like_date_bucket(title) or looks_like_date_title(title):
        return True
    normalized_source = normalize_source_name(row.source_name)
    if normalized_source == "hong kong cheapo" and row.source_url and "/events/" not in row.source_url.lower():
        return True
    if row.source_url and is_listing_like_event_url(row.source_url):
        return True
    return False


def source_event_counts_upcoming() -> list[dict[str, Any]]:
    ensure_schema()
    cutoff = utcnow_naive() - timedelta(days=1)
    with SessionLocal() as session:
        rows = session.execute(
            select(Event.source_name, func.count(Event.id), func.avg(Event.quality_score))
            .where(Event.start_time_utc >= cutoff)
            .group_by(Event.source_name)
            .order_by(func.count(Event.id).desc())
        ).all()

    return [
        {
            "source_name": source_name,
            "upcoming_events": int(count),
            "avg_quality_score": round(avg_quality or 0, 1),
        }
        for source_name, count, avg_quality in rows
    ]


def start_scrape_worker() -> None:
    global WORKER_STARTED
    with SCRAPE_STATE_LOCK:
        if WORKER_STARTED:
            return
        worker = threading.Thread(target=_scrape_worker_loop, daemon=True, name="scrape-worker")
        worker.start()
        WORKER_STARTED = True


def enqueue_scrape(triggered_by: str = "manual") -> dict[str, Any]:
    start_scrape_worker()
    job_id = uuid.uuid4().hex[:12]
    job = {
        "job_id": job_id,
        "status": "queued",
        "triggered_by": triggered_by,
        "queued_at_utc": utcnow_naive().isoformat(),
        "message": "Queued scrape job",
        "progress": {"current": 0, "total": len(build_scrapers())},
        "report": None,
    }
    with SCRAPE_STATE_LOCK:
        SCRAPE_JOBS[job_id] = job
    SCRAPE_QUEUE.put({"job_id": job_id, "triggered_by": triggered_by})
    trim_job_history()
    return copy.deepcopy(job)


def get_scrape_status(job_id: str | None = None) -> dict[str, Any]:
    with SCRAPE_STATE_LOCK:
        jobs = sorted(
            SCRAPE_JOBS.values(),
            key=lambda item: item.get("queued_at_utc", ""),
            reverse=True,
        )
        selected_job = SCRAPE_JOBS.get(job_id) if job_id else (jobs[0] if jobs else None)
        return {
            "job": copy.deepcopy(selected_job),
            "jobs": copy.deepcopy(jobs[: Config.SCRAPE_STATUS_RETENTION]),
            "last_completed": copy.deepcopy(LAST_COMPLETED_REPORT),
        }


def persist_scrape_run(report: dict[str, Any], job_id: str | None = None) -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    with SessionLocal() as session:
        run = ScrapeRun(
            job_id=job_id or uuid.uuid4().hex[:12],
            status="completed",
            triggered_by=report.get("triggered_by", "manual"),
            sources_total=report.get("sources_total", 0),
            processed=report.get("processed", 0),
            failed_sources=report.get("failed_sources", 0),
            empty_sources=report.get("empty_sources", 0),
            rejected_events=report.get("rejected_events", 0),
            used_sample_fallback=1 if report.get("used_sample_fallback") else 0,
            summary_json=json.dumps(report),
            started_at_utc=datetime.fromisoformat(report["started_at_utc"]),
            finished_at_utc=datetime.fromisoformat(report["finished_at_utc"]),
        )
        session.add(run)
        session.commit()


def latest_scrape_runs(limit: int = 5) -> list[dict[str, Any]]:
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    with SessionLocal() as session:
        runs = session.scalars(select(ScrapeRun).order_by(ScrapeRun.started_at_utc.desc()).limit(limit)).all()
    return [
        {
            "job_id": run.job_id,
            "status": run.status,
            "triggered_by": run.triggered_by,
            "sources_total": run.sources_total,
            "processed": run.processed,
            "failed_sources": run.failed_sources,
            "empty_sources": run.empty_sources,
            "rejected_events": run.rejected_events,
            "used_sample_fallback": bool(run.used_sample_fallback),
            "started_at_utc": run.started_at_utc.isoformat(),
            "finished_at_utc": run.finished_at_utc.isoformat() if run.finished_at_utc else None,
        }
        for run in runs
    ]


def set_last_completed_report(report: dict[str, Any]) -> None:
    global LAST_COMPLETED_REPORT
    with SCRAPE_STATE_LOCK:
        LAST_COMPLETED_REPORT = copy.deepcopy(report)


def trim_job_history() -> None:
    with SCRAPE_STATE_LOCK:
        jobs = sorted(SCRAPE_JOBS.items(), key=lambda item: item[1].get("queued_at_utc", ""), reverse=True)
        for job_id, _job in jobs[Config.SCRAPE_STATUS_RETENTION :]:
            SCRAPE_JOBS.pop(job_id, None)


def _scrape_worker_loop() -> None:
    while True:
        try:
            queued = SCRAPE_QUEUE.get(timeout=1)
        except Empty:
            continue

        job_id = queued["job_id"]
        triggered_by = queued["triggered_by"]
        _update_job(job_id, status="running", message="Starting scrape job")

        try:
            report = run_scrape_detailed(
                triggered_by=triggered_by,
                job_id=job_id,
                progress_callback=lambda progress: _update_job(
                    job_id,
                    status="running",
                    message=progress["message"],
                    progress={"current": progress["current"], "total": progress["total"], "source_name": progress["source_name"]},
                ),
            )
            _update_job(job_id, status="completed", message="Scrape completed", report=report, finished_at_utc=utcnow_naive().isoformat())
        except Exception as exc:
            _update_job(job_id, status="failed", message=str(exc), finished_at_utc=utcnow_naive().isoformat())
        finally:
            SCRAPE_QUEUE.task_done()


def _update_job(job_id: str, **updates: Any) -> None:
    with SCRAPE_STATE_LOCK:
        if job_id not in SCRAPE_JOBS:
            return
        SCRAPE_JOBS[job_id].update(updates)
