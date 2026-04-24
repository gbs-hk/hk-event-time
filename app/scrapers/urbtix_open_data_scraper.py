from __future__ import annotations

from datetime import UTC, datetime, timedelta
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

import requests

from ..config import Config
from .base import BaseScraper, ScrapedEvent
from .html_event_scraper import build_map_url, normalize_text, sanitize_url, stable_external_id

HK_TZ = ZoneInfo("Asia/Hong_Kong")


class UrbtixOpenDataScraper(BaseScraper):
    source_name = "URBTIX Open Data"
    batch_url_template = "https://fs-open-1304240968.cos.ap-hongkong.myqcloud.com/prod/gprd/URBTIX_eventBatch_{date}.xml"

    def fetch(self) -> list[ScrapedEvent]:
        for publish_date in self._candidate_publish_dates():
            xml_text = self._fetch_batch_xml(publish_date)
            if not xml_text:
                continue
            events = self._parse_batch_xml(xml_text)
            if events:
                return events
        return []

    def _candidate_publish_dates(self) -> list[str]:
        today = datetime.now(UTC)
        return [(today - timedelta(days=offset)).strftime("%Y%m%d") for offset in range(3)]

    def _fetch_batch_xml(self, publish_date: str) -> str:
        url = self.batch_url_template.format(date=publish_date)
        try:
            response = requests.get(
                url,
                timeout=Config.SCRAPE_TIMEOUT_SECONDS,
                headers={"User-Agent": Config.SCRAPE_USER_AGENT},
            )
            response.raise_for_status()
            return response.text
        except Exception:
            return ""

    def _parse_batch_xml(self, xml_text: str) -> list[ScrapedEvent]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        events: list[ScrapedEvent] = []
        for event_node in root.findall("./EVENTS/EVENT"):
            events.extend(self._parse_event_node(event_node))
        return events

    def _parse_event_node(self, event_node: ET.Element) -> list[ScrapedEvent]:
        event_name = normalize_text(event_node.findtext("EVENT_EG", default=""))
        event_link = sanitize_url(normalize_text(event_node.findtext("REFERENCE_LINK", default="")))
        main_category = normalize_text(event_node.findtext("./CATEGORY/MAIN_CAT/EG", default=""))
        sub_category = normalize_text(event_node.findtext("./CATEGORY/SUB_CAT/EG", default=""))
        venue_name = normalize_text(event_node.findtext("./LOCATION/VENUE_EG", default=""))
        region_name = normalize_text(event_node.findtext("./LOCATION/REGION_EG", default=""))
        city_name = normalize_text(event_node.findtext("./LOCATION/CITY_EG", default=""))
        location_name = venue_name if venue_name and venue_name != "-" else region_name
        location_address = ", ".join(part for part in [region_name, city_name] if part and part != location_name)

        description_parts = [part for part in [main_category, sub_category] if part]
        description = normalize_text(" | ".join(description_parts))

        scraped_events: list[ScrapedEvent] = []
        for performance in event_node.findall("./PERFORMANCES/PERFORMANCE"):
            start_raw = normalize_text(performance.findtext("PERFORMANCE_DATETIME", default=""))
            start_dt = self._parse_start_datetime(start_raw)
            if not start_dt:
                continue

            title = normalize_text(performance.findtext("TITLE_EG", default="")) or event_name
            if not title:
                continue

            performance_link = sanitize_url(normalize_text(performance.findtext("REFERENCE_LINK", default="")))
            source_url = performance_link or event_link
            remark = normalize_text(performance.findtext("REMARK_EG", default=""))
            full_description = normalize_text(" ".join(part for part in [description, remark] if part))[:500]
            external_id = stable_external_id("urbtix-open-data", source_url or event_link, title, start_dt)

            scraped_events.append(
                ScrapedEvent(
                    external_id=external_id,
                    name=title,
                    description=full_description,
                    source_name=self.source_name,
                    organizer="",
                    location_name=location_name,
                    location_address=location_address,
                    map_url=build_map_url(location_name, location_address),
                    start_time_utc=start_dt,
                    end_time_utc=None,
                    ticket_url=source_url or event_link,
                    discount_text="",
                    discount_url="",
                    source_url=source_url or event_link,
                    price_text="",
                )
            )

        return scraped_events

    @staticmethod
    def _parse_start_datetime(raw_value: str) -> datetime | None:
        if not raw_value:
            return None
        try:
            local_dt = datetime.strptime(raw_value, "%Y-%m-%d %H:%M").replace(tzinfo=HK_TZ)
        except ValueError:
            return None
        return local_dt.astimezone(UTC).replace(tzinfo=None)
