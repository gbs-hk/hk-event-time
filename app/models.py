from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(128))
    source_url: Mapped[str] = mapped_column(String(512), default="")
    organizer: Mapped[str] = mapped_column(String(255), default="")
    location_name: Mapped[str] = mapped_column(String(255), default="")
    location_address: Mapped[str] = mapped_column(String(255), default="")
    map_url: Mapped[str] = mapped_column(String(512), default="")
    start_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=False), index=True)
    end_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=True)
    ticket_url: Mapped[str] = mapped_column(String(512), default="")
    price_text: Mapped[str] = mapped_column(String(255), default="")
    discount_text: Mapped[str] = mapped_column(String(255), default="")
    discount_url: Mapped[str] = mapped_column(String(512), default="")
    quality_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    scraped_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    triggered_by: Mapped[str] = mapped_column(String(32), default="manual")
    sources_total: Mapped[int] = mapped_column(Integer, default=0)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    failed_sources: Mapped[int] = mapped_column(Integer, default=0)
    empty_sources: Mapped[int] = mapped_column(Integer, default=0)
    rejected_events: Mapped[int] = mapped_column(Integer, default=0)
    used_sample_fallback: Mapped[int] = mapped_column(Integer, default=0)
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    started_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow, index=True)
    finished_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=True)
