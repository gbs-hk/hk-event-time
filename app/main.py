from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from dateutil import parser as dt_parser
from flask import Flask, jsonify, render_template, request

from .categories import categories_for_api
from .config import Config
from .database import Base, engine, ensure_schema
from .scheduler import start_scheduler
from .services import (
    enqueue_scrape,
    get_color_map,
    get_scrape_status,
    latest_scrape_runs,
    query_events,
    run_scrape_detailed,
    source_event_counts_upcoming,
    start_scrape_worker,
)

HK_TZ = ZoneInfo("Asia/Hong_Kong")


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
        static_url_path="/static",
    )

    Base.metadata.create_all(bind=engine)
    ensure_schema()
    start_scrape_worker()
    start_scheduler()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/categories")
    def categories():
        return jsonify(list(categories_for_api()))

    @app.get("/api/events")
    def events():
        start_raw = request.args.get("start")
        end_raw = request.args.get("end")
        if not start_raw or not end_raw:
            return jsonify({"error": "start and end query params are required"}), 400

        start_utc = parse_request_datetime_to_utc(start_raw)
        end_utc = parse_request_datetime_to_utc(end_raw)
        category_filter = request.args.getlist("category") or None
        extra_filters = {
            "free": request.args.get("free", "0").strip().lower() in {"1", "true", "yes"},
            "district": request.args.get("district", "").strip(),
            "category_slug": request.args.get("quick_category", "").strip(),
        }

        rows = query_events(start_utc=start_utc, end_utc=end_utc, categories=category_filter, filters=extra_filters)
        color_map = get_color_map()

        payload = [
            {
                "id": row.id,
                "title": row.name,
                "category": row.category,
                "start": utc_naive_to_hk_iso(row.start_time_utc),
                "end": utc_naive_to_hk_iso(row.end_time_utc) if row.end_time_utc else None,
                "backgroundColor": color_map.get(row.category, "#6d7380"),
                "borderColor": color_map.get(row.category, "#6d7380"),
                "extendedProps": {
                    "category": row.category,
                    "description": row.description,
                    "source_name": row.source_name,
                    "source_url": row.source_url,
                    "organizer": row.organizer,
                    "location_name": row.location_name,
                    "location_address": row.location_address,
                    "map_url": row.map_url,
                    "ticket_url": row.ticket_url,
                    "price_text": row.price_text,
                    "discount_text": row.discount_text,
                    "discount_url": row.discount_url,
                    "quality_score": row.quality_score,
                },
            }
            for row in rows
        ]
        return jsonify(payload)

    @app.post("/api/scrape-now")
    def scrape_now():
        result = enqueue_scrape(triggered_by="manual")
        return jsonify(result), 202

    @app.get("/api/scrape-status")
    def scrape_status():
        job_id = request.args.get("job_id")
        payload = get_scrape_status(job_id=job_id)
        payload["history"] = latest_scrape_runs()
        payload["source_mode"] = Config.SCRAPE_SOURCE_MODE
        payload["upcoming_by_source"] = source_event_counts_upcoming()
        return jsonify(payload)

    @app.get("/api/debug/sources")
    def debug_sources():
        run_flag = request.args.get("run", "0").strip().lower() in {"1", "true", "yes"}
        payload = {
            "checked_at_utc": datetime.utcnow().isoformat(),
            "source_mode": Config.SCRAPE_SOURCE_MODE,
            "focus_categories": Config.SCRAPE_FOCUS_CATEGORIES,
            "upcoming_by_source": source_event_counts_upcoming(),
            "history": latest_scrape_runs(limit=10),
        }
        if run_flag:
            payload["scrape_run"] = run_scrape_detailed()
        else:
            payload["scrape_status"] = get_scrape_status()
        return jsonify(payload)

    @app.get("/admin/debug")
    def admin_debug():
        return render_template("index.html")

    return app


app = create_app()


def parse_request_datetime_to_utc(value: str) -> datetime:
    parsed = dt_parser.parse(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=HK_TZ)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def utc_naive_to_hk_iso(value: datetime) -> str:
    return value.replace(tzinfo=timezone.utc).astimezone(HK_TZ).isoformat()
