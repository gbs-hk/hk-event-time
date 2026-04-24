import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-me")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///events.db")
    SCRAPE_TIMEOUT_SECONDS = int(os.getenv("SCRAPE_TIMEOUT_SECONDS", "15"))
    # More realistic user agent to avoid blocking
    SCRAPE_USER_AGENT = os.getenv(
        "SCRAPE_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    SCHEDULE_HOUR_UTC = int(os.getenv("SCHEDULE_HOUR_UTC", "1"))
    SCRAPE_MAX_DETAIL_PAGES_PER_SOURCE = int(
        os.getenv("SCRAPE_MAX_DETAIL_PAGES_PER_SOURCE", "12")
    )
    SCRAPE_MAX_MONTH_PAGES_PER_SOURCE = int(
        os.getenv("SCRAPE_MAX_MONTH_PAGES_PER_SOURCE", "6")
    )
    # Enable sample data by default so app works out of the box
    SCRAPE_INCLUDE_SAMPLE = os.getenv("SCRAPE_INCLUDE_SAMPLE", "1") == "1"
    SCRAPE_SOURCE_MODE = os.getenv("SCRAPE_SOURCE_MODE", "lkf_nightlife")
    # Default to empty (all categories) for more events
    SCRAPE_FOCUS_CATEGORIES = tuple(
        value.strip().lower()
        for value in os.getenv("SCRAPE_FOCUS_CATEGORIES", "").split(",")
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
