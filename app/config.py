import os


class Config:
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-me")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///events.db")
    SCRAPE_TIMEOUT_SECONDS = int(os.getenv("SCRAPE_TIMEOUT_SECONDS", "15"))
    SCRAPE_RETRY_COUNT = int(os.getenv("SCRAPE_RETRY_COUNT", "1"))
    SCRAPE_SOURCE_TIMEOUT_SECONDS = int(os.getenv("SCRAPE_SOURCE_TIMEOUT_SECONDS", "25"))
    SCRAPE_MIN_QUALITY_SCORE = int(os.getenv("SCRAPE_MIN_QUALITY_SCORE", "55"))
    SCRAPE_USER_AGENT = os.getenv(
        "SCRAPE_USER_AGENT",
        "Mozilla/5.0 (compatible; HKEventsBot/1.0; +https://example.local)",
    )
    SCHEDULE_HOUR_UTC = int(os.getenv("SCHEDULE_HOUR_UTC", "1"))
    SCRAPE_MAX_DETAIL_PAGES_PER_SOURCE = int(os.getenv("SCRAPE_MAX_DETAIL_PAGES_PER_SOURCE", "12"))
    SCRAPE_INCLUDE_SAMPLE = os.getenv("SCRAPE_INCLUDE_SAMPLE", "0") == "1"
    SCRAPE_SOURCE_MODE = os.getenv("SCRAPE_SOURCE_MODE", "priority")
    SCRAPE_FOCUS_CATEGORIES = tuple(
        value.strip().lower()
        for value in os.getenv("SCRAPE_FOCUS_CATEGORIES", "").split(",")
        if value.strip()
    )
    SCRAPE_STATUS_RETENTION = int(os.getenv("SCRAPE_STATUS_RETENTION", "12"))
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "180"))
    USE_RELOADER = os.getenv("USE_RELOADER", "0") == "1"
