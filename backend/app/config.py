from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/hk_events"
    app_env: str = "development"
    cors_origins: str = "http://localhost:3000"
    scheduler_enabled: bool = True
    scrape_interval_hours: int = 24
    request_timeout_seconds: int = 15
    request_user_agent: str = "hk-event-discovery-bot/1.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


settings = Settings()
