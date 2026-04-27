from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from dateutil import parser as dt_parser
from flask import Flask, jsonify, render_template, request

from .categories import categories_for_api
from .config import Config
from .database import Base, engine
from .scheduler import start_scheduler
from .services import get_color_map, query_events, run_scrape, run_scrape_detailed, source_event_counts_upcoming

HK_TZ = ZoneInfo("Asia/Hong_Kong")


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
        static_url_path="/static",
    )

    Base.metadata.create_all(bind=engine)
    start_scheduler()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

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

        rows = query_events(start_utc=start_utc, end_utc=end_utc, categories=category_filter)
        color_map = get_color_map()
        category_meta = {item["slug"]: item for item in categories_for_api()}

        payload = [
            {
                "id": row.id,
                "title": row.name,
                "category": row.category,
                "start": utc_naive_to_hk_iso(row.start_time_utc),
                "end": utc_naive_to_hk_iso(row.end_time_utc) if row.end_time_utc else None,
                "backgroundColor": color_map.get(row.category, "#6d7380"),
                "borderColor": color_map.get(row.category, "#6d7380"),
                "textColor": category_meta.get(row.category, {}).get("text_color", "#ffffff"),
                "extendedProps": {
                    "description": row.description,
                    "source_name": row.source_name,
                    "organizer": row.organizer,
                    "location_name": row.location_name,
                    "location_address": row.location_address,
                    "map_url": row.map_url,
                    "ticket_url": row.ticket_url,
                    "discount_text": row.discount_text,
                    "discount_url": row.discount_url,
                },
            }
            for row in rows
        ]
        return jsonify(payload)

    @app.post("/api/scrape-now")
    def scrape_now():
        result = run_scrape()
        result["ran_at_utc"] = datetime.utcnow().isoformat()
        return jsonify(result)

    @app.get("/api/debug/sources")
    def debug_sources():
        run_flag = request.args.get("run", "0").strip().lower() in {"1", "true", "yes"}
        payload = {
            "checked_at_utc": datetime.utcnow().isoformat(),
            "source_mode": Config.SCRAPE_SOURCE_MODE,
            "focus_categories": Config.SCRAPE_FOCUS_CATEGORIES,
            "upcoming_by_source": source_event_counts_upcoming(),
        }
        if run_flag:
            payload["scrape_run"] = run_scrape_detailed()
        return jsonify(payload)

    return app

def parse_request_datetime_to_utc(value: str) -> datetime:
    parsed = dt_parser.parse(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=HK_TZ)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def utc_naive_to_hk_iso(value: datetime) -> str:
    return value.replace(tzinfo=timezone.utc).astimezone(HK_TZ).isoformat()
