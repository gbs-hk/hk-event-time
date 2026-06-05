import json
import logging
from datetime import datetime, timedelta

from app.scrapers.base import ScrapedEvent
from app import services


class FakeScraper:
    source_name = "Test Source"

    def fetch(self):
        return [
            ScrapedEvent(
                external_id="test-1",
                name="Harbour Food Market",
                description="A public food market with live music and local vendors.",
                source_name=self.source_name,
                organizer="HK Events",
                location_name="Central Harbourfront",
                location_address="Central",
                map_url="https://maps.example.test/central",
                start_time_utc=datetime.utcnow() + timedelta(days=3),
                end_time_utc=None,
                ticket_url="https://tickets.example.test/market",
                discount_text="",
                discount_url="",
            )
        ]


def test_run_scrape_detailed_emits_structured_completion_log(monkeypatch, caplog):
    monkeypatch.setattr(services, "build_scrapers", lambda: [FakeScraper()])
    monkeypatch.setattr(services, "upsert_event", lambda scraped, category: object())

    with caplog.at_level(logging.INFO, logger="app.services"):
        report = services.run_scrape_detailed()

    assert report["processed"] == 1
    assert report["failed_sources"] == 0
    assert report["empty_sources"] == 0
    assert report["sources_total"] == 1
    assert report["success"] is True
    assert "duration_ms" in report
    assert "started_at_utc" in report
    assert "finished_at_utc" in report

    finished = [record for record in caplog.records if "scrape.run.finished" in record.message]
    assert len(finished) == 1
    payload = json.loads(finished[0].message.split("scrape.run.finished ", 1)[1])
    assert payload["event"] == "scrape.run.finished"
    assert payload["scrape.events_persisted"] == 1
    assert payload["failed_sources"] == 0
    assert payload["success"] is True
