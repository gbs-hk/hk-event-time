import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-me")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///events.db")
    SCRAPE_TIMEOUT_SECONDS = int(os.getenv("SCRAPE_TIMEOUT_SECONDS", "15"))
    SCRAPE_USER_AGENT = os.getenv(
        "SCRAPE_USER_AGENT",
        "Mozilla/5.0 (compatible; HKEventsBot/1.0; +https://example.local)",
    )
    SCHEDULE_HOUR_UTC = int(os.getenv("SCHEDULE_HOUR_UTC", "1"))
    SCRAPE_MAX_DETAIL_PAGES_PER_SOURCE = int(os.getenv("SCRAPE_MAX_DETAIL_PAGES_PER_SOURCE", "12"))
    SCRAPE_INCLUDE_SAMPLE = os.getenv("SCRAPE_INCLUDE_SAMPLE", "0") == "1"
    SCRAPE_SOURCE_MODE = os.getenv("SCRAPE_SOURCE_MODE", "lkf_nightlife")
    SCRAPE_FOCUS_CATEGORIES = tuple(
        value.strip().lower()
        for value in os.getenv("SCRAPE_FOCUS_CATEGORIES", "party,music").split(",")
        if value.strip()
    )

    @classmethod
    def normalized_database_url(cls) -> str:
        url = cls.DATABASE_URL.strip()
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://") :]
        if url.startswith("postgresql://") and "+psycopg" not in url:
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url
