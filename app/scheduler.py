from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import Config
from .services import enqueue_scrape


scheduler = BackgroundScheduler(timezone="UTC")


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        lambda: enqueue_scrape(triggered_by="scheduler"),
        trigger=CronTrigger(hour=Config.SCHEDULE_HOUR_UTC, minute=0),
        id="daily_scrape",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
