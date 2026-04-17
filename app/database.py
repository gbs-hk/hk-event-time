from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import Config


class Base(DeclarativeBase):
    pass


engine = create_engine(Config.DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def ensure_schema() -> None:
    with engine.begin() as connection:
        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(events)")).fetchall()
        }

        if columns:
            if "source_url" not in columns:
                connection.execute(text("ALTER TABLE events ADD COLUMN source_url VARCHAR(512) DEFAULT ''"))
            if "price_text" not in columns:
                connection.execute(text("ALTER TABLE events ADD COLUMN price_text VARCHAR(255) DEFAULT ''"))
            if "quality_score" not in columns:
                connection.execute(text("ALTER TABLE events ADD COLUMN quality_score INTEGER DEFAULT 0"))
