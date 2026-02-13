from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category
from app.schemas import CategoryOut, EventOut
from app.scrape import get_events, scrape_all_sources

router = APIRouter()


@router.get("/events", response_model=list[EventOut])
def list_events(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    categories: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=1000),
    db: Session = Depends(get_db)
) -> list[EventOut]:
    category_slugs = [item.strip() for item in categories.split(",")] if categories else None
    return get_events(db, start=start, end=end, category_slugs=category_slugs, limit=limit)


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryOut]:
    return list(db.scalars(select(Category).order_by(Category.name.asc())).all())


@router.post("/events/run-scrape")
def run_scrape(db: Session = Depends(get_db)) -> dict[str, int]:
    return scrape_all_sources(db)
