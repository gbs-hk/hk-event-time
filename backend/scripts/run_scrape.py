from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Ensure backend root is on path so "app" can be imported
_backend_root = Path(__file__).resolve().parent.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import SessionLocal
from app.scrape import scrape_all_sources

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def scrape_once() -> dict[str, int]:
    db = SessionLocal()
    try:
        result = scrape_all_sources(db)
        logger.info("scrape completed: %s", result)
        return result
    finally:
        db.close()


def run_scheduler() -> None:
    scheduler = BackgroundScheduler()
    scheduler.add_job(scrape_once, "interval", hours=settings.scrape_interval_hours, id="daily_scrape")
    scheduler.start()
    logger.info("scheduler started at %s-hour interval", settings.scrape_interval_hours)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("scheduler stopping")
        scheduler.shutdown(wait=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run HK event scraper")
    parser.add_argument("--mode", choices=["once", "scheduler"], default="once")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.mode == "scheduler":
        run_scheduler()
    else:
        scrape_once()
