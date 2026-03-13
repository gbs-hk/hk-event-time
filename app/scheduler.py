from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import Config
from .services import run_scrape


scheduler = BackgroundScheduler(timezone="UTC")


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        run_scrape,
        trigger=CronTrigger(hour=Config.SCHEDULE_HOUR_UTC, minute=0),
        id="daily_scrape",
        replace_existing=True,
    )
    scheduler.start()
