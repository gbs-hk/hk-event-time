from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import re
from zoneinfo import ZoneInfo

from dateutil import parser as dt_parser
from flask import Flask, jsonify, render_template, request

from .categories import categories_for_api
from .config import Config
from .database import Base, check_database_ready, engine
from .scheduler import start_scheduler
from .services import get_color_map, query_events, run_scrape, run_scrape_detailed, source_event_counts_upcoming

HK_TZ = ZoneInfo("Asia/Hong_Kong")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ANALYTICS_EVENT_PATTERN = re.compile(r"^HKET\.[a-z0-9_.-]{1,80}$")
ANALYTICS_SESSION_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
ANALYTICS_ALLOWED_PROPERTIES = {
    "category_count",
    "event_category",
    "event_source",
    "has_query",
    "result_count",
    "route",
    "search_length",
    "selected_all",
    "source",
    "view_type",
}


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
        database = check_database_ready()
        status = "ok" if database["status"] == "ok" else "down"
        status_code = 200 if status == "ok" else 503
        return jsonify({"status": status, "database": database}), status_code

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

    @app.post("/api/analytics/events")
    def analytics_event():
        payload = request.get_json(silent=True) or {}
        event_name = str(payload.get("event_name", "")).strip()
        session_id = str(payload.get("session_id", "")).strip()
        route = normalize_analytics_route(payload.get("route", request.path))

        if not ANALYTICS_EVENT_PATTERN.fullmatch(event_name):
            return jsonify({"error": "event_name must start with HKET. and use safe characters"}), 400
        if not ANALYTICS_SESSION_PATTERN.fullmatch(session_id):
            return jsonify({"error": "session_id is required"}), 400

        event_payload = {
            "event_name": event_name,
            "session_id": session_id,
            "route": route,
            "properties": sanitize_analytics_properties(payload.get("properties", {})),
        }
        logger.info("analytics.event %s", json.dumps(event_payload, sort_keys=True))
        return jsonify({"accepted": True}), 202

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


def normalize_analytics_route(value: object) -> str:
    route = str(value or "/").split("?", 1)[0].strip() or "/"
    if not route.startswith("/"):
        route = "/"
    return route[:120]


def sanitize_analytics_properties(properties: object) -> dict[str, bool | int | str]:
    if not isinstance(properties, dict):
        return {}

    sanitized: dict[str, bool | int | str] = {}
    for key, value in properties.items():
        key = str(key)
        if key not in ANALYTICS_ALLOWED_PROPERTIES:
            continue
        if isinstance(value, bool):
            sanitized[key] = value
        elif isinstance(value, int):
            sanitized[key] = value
        elif isinstance(value, str):
            sanitized[key] = value[:120]
    return sanitized


def parse_request_datetime_to_utc(value: str) -> datetime:
    parsed = dt_parser.parse(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=HK_TZ)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def utc_naive_to_hk_iso(value: datetime) -> str:
    return value.replace(tzinfo=timezone.utc).astimezone(HK_TZ).isoformat()
