from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Config
from .html_event_scraper import ConfiguredSourceScraper, MultiStrategyEventScraper
from .sample_scraper import SampleHongKongScraper


@dataclass(frozen=True)
class SourceDefinition:
    key: str
    label: str
    urls: list[str]
    priority: int
    card_selector: str | None = None
    title_selector: str | None = None
    date_selectors: tuple[str, ...] = ()
    location_selectors: tuple[str, ...] = ()
    detail_markers: tuple[str, ...] = ()
    category_hint: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)


PRIORITY_SOURCES: tuple[SourceDefinition, ...] = (
    SourceDefinition(
        key="discover-hk",
        label="Discover Hong Kong",
        urls=["https://www.discoverhongkong.com/eng/explore/events.html"],
        priority=100,
        card_selector="article, .card, .event-card, li",
        title_selector="h2, h3, .card-title, a",
        date_selectors=("time", ".date", ".event-date", ".card-date"),
        location_selectors=(".location", ".venue", ".place"),
        detail_markers=("event", "festival", "show"),
        category_hint="culture",
        tags=("official", "broad"),
    ),
    SourceDefinition(
        key="hongkong-cheapo",
        label="Hong Kong Cheapo",
        urls=["https://hongkongcheapo.com/events"],
        priority=95,
        card_selector="article, .post, .event, li",
        title_selector="h2, h3, .entry-title, a",
        date_selectors=("time", ".date", ".meta-date"),
        location_selectors=(".location", ".venue"),
        detail_markers=("event", "festival", "concert"),
        tags=("broad",),
    ),
    SourceDefinition(
        key="timeout-hk",
        label="Time Out Hong Kong",
        urls=[
            "https://www.timeout.com/hong-kong",
            "https://www.timeout.com/hong-kong/things-to-do",
        ],
        priority=90,
        card_selector="article, .tile, .feature-item, li",
        title_selector="h2, h3, .tile_content__heading, a",
        date_selectors=("time", ".date", ".listing__meta"),
        location_selectors=(".venue", ".location", ".listing__venue"),
        detail_markers=("event", "things-to-do", "music", "nightlife"),
        tags=("editorial",),
    ),
    SourceDefinition(
        key="hkcec",
        label="HKCEC",
        urls=["https://www.hkcec.com/en/event-calendar"],
        priority=85,
        card_selector="article, .event-item, tr, li",
        title_selector="h2, h3, .title, a",
        date_selectors=("time", ".date", ".event-date"),
        location_selectors=(".venue", ".hall", ".location"),
        detail_markers=("event", "calendar"),
        category_hint="networking",
        tags=("venue",),
    ),
    SourceDefinition(
        key="lan-kwai-fong",
        label="Lan Kwai Fong",
        urls=["https://www.lankwaifong.com"],
        priority=80,
        card_selector="article, .event, .post, li, .listing",
        title_selector="h2, h3, .title, a",
        date_selectors=("time", ".date", ".event-date"),
        location_selectors=(".venue", ".location", ".district"),
        detail_markers=("night", "party", "event"),
        category_hint="party",
        tags=("nightlife",),
    ),
)

SECONDARY_SOURCES: tuple[SourceDefinition, ...] = (
    SourceDefinition("eventbrite-hk", "Eventbrite Hong Kong", ["https://www.eventbrite.com/d/hong-kong-sar--hong-kong"], 60),
    SourceDefinition("meetup-hk", "Meetup Hong Kong", ["https://www.meetup.com/cities/hk/hong_kong"], 58),
    SourceDefinition("letseventhk", "LetsEvent HK", ["https://www.letseventhk.com"], 55),
    SourceDefinition("brandhk", "Brand Hong Kong", ["https://www.brandhk.gov.hk"], 45),
    SourceDefinition("lcsd", "LCSD", ["https://www.lcsd.gov.hk"], 45),
)

LKF_SOURCE_KEYS = {"lan-kwai-fong", "timeout-hk", "eventbrite-hk", "meetup-hk", "letseventhk"}


def all_source_definitions() -> tuple[SourceDefinition, ...]:
    return PRIORITY_SOURCES + SECONDARY_SOURCES


def selected_sources() -> tuple[SourceDefinition, ...]:
    mode = Config.SCRAPE_SOURCE_MODE.strip().lower()
    if mode == "all":
        return all_source_definitions()
    if mode == "lkf_nightlife":
        return tuple(source for source in all_source_definitions() if source.key in LKF_SOURCE_KEYS)
    return PRIORITY_SOURCES


def build_scrapers() -> list:
    scrapers = []
    if Config.SCRAPE_INCLUDE_SAMPLE:
        scrapers.append(SampleHongKongScraper())

    for definition in selected_sources():
        if definition.card_selector or definition.title_selector or definition.date_selectors:
            scrapers.append(ConfiguredSourceScraper(definition))
        else:
            scrapers.append(MultiStrategyEventScraper(source_name=definition.key, urls=definition.urls))
    return scrapers
