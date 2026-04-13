from __future__ import annotations

from ..config import Config
from .eventbrite_scraper import EventbriteScraper
from .html_event_scraper import MultiStrategyEventScraper
from .luma_scraper import LumaScraper
from .sample_scraper import SampleHongKongScraper


ALL_SOURCE_URLS: dict[str, list[str]] = {
    "discover-hk": [
        "https://www.discoverhongkong.com/eng/explore/events.html",
        "https://www.discoverhongkong.com",
    ],
    "hongkong-cheapo": [
        "https://hongkongcheapo.com/events",
    ],
    "timeout-hk": [
        "https://www.timeout.com/hong-kong",
        "https://www.timeout.com/hong-kong/things-to-do",
    ],
    "brandhk": [
        "https://www.brandhk.gov.hk",
    ],
    "meetup-hk": [
        "https://www.meetup.com/cities/hk/hong_kong",
    ],
    "eventbrite-hk": [
        "https://www.eventbrite.com/d/hong-kong-sar--hong-kong",
    ],
    "internations-hk": [
        "https://www.internations.org/hong-kong-expats",
    ],
    "letseventhk": [
        "https://www.letseventhk.com",
    ],
    "lcsd": [
        "https://www.lcsd.gov.hk",
    ],
    "hkcc": [
        "https://www.hkcc.gov.hk",
    ],
    "hkculturalcentre": [
        "https://www.hkculturalcentre.gov.hk",
    ],
    "hkcec": [
        "https://www.hkcec.com/en/event-calendar",
    ],
    "hktb-partnernet": [
        "https://partnernet.hktb.com/en/destination/events_festivals",
    ],
    "lan-kwai-fong": [
        "https://www.lankwaifong.com",
    ],
    "cassio-hk": [
        "https://www.cassiohk.com",
    ],
    "dragon-i": [
        "https://www.dragon-i.com.hk",
    ],
    "trilogy-hk": [
        "https://www.trilogyhk.com",
    ],
    "zeus-lkf": [
        "https://www.zeus-lkf.com",
    ],
    "oma-hk": [
        "https://www.omahk.com",
    ],
    "boomerang-hk": [
        "https://www.boomeranghk.com",
    ],
    "maggie-choos": [
        "https://www.maggiechoos.com/hongkong",
    ],
    "iron-fairies": [
        "https://www.theironfairies.com/hong-kong",
    ],
    "sahara-lkf": [
        "https://www.saharalkf.com",
    ],
    "qing-hk": [
        "https://www.qing.hk",
    ],
    "china-bar-hk": [
        "https://www.chinabarhk.com",
    ],
    "hongkong-pubcrawl": [
        "https://www.hongkongpubcrawl.com",
    ],
    "shuffle-hk": [
        "https://www.shuffle.hk",
    ],
}

# Additional reliable sources with better structured content
RELIABLE_SOURCES: dict[str, list[str]] = {
    "timeout-hk-events": [
        "https://www.timeout.com/hong-kong/things-to-do/best-events-in-hong-kong",
        "https://www.timeout.com/hong-kong/restaurants/best-restaurant-events",
        "https://www.timeout.com/hong-kong/bars/best-bar-events",
    ],
    "discover-hk-events": [
        "https://www.discoverhongkong.com/eng/explore/events/festivals.html",
        "https://www.discoverhongkong.com/eng/explore/events.html",
    ],
    "lcsd-events": [
        "https://www.lcsd.gov.hk/en/ce/cultureDefinition.html",
        "https://www.lcsd.gov.hk/en/ce/cultureDefinition/mus_11.html",
    ],
    "culture-portal": [
        "https://www.lcsd.gov.hk/en/ej.html",
    ],
}

LKF_NIGHTLIFE_SOURCE_KEYS = (
    "lan-kwai-fong",
    "cassio-hk",
    "dragon-i",
    "trilogy-hk",
    "zeus-lkf",
    "oma-hk",
    "boomerang-hk",
    "maggie-choos",
    "iron-fairies",
    "sahara-lkf",
    "qing-hk",
    "china-bar-hk",
    "hongkong-pubcrawl",
    "shuffle-hk",
    "eventbrite-hk",
    "meetup-hk",
    "letseventhk",
    "timeout-hk",
)


def selected_sources() -> dict[str, list[str]]:
    mode = Config.SCRAPE_SOURCE_MODE.strip().lower()
    if mode == "lkf_nightlife":
        sources = {key: ALL_SOURCE_URLS[key] for key in LKF_NIGHTLIFE_SOURCE_KEYS if key in ALL_SOURCE_URLS}
        # Include reliable sources for better event coverage
        sources.update(RELIABLE_SOURCES)
        return sources
    if mode == "all":
        all_src = dict(ALL_SOURCE_URLS)
        all_src.update(RELIABLE_SOURCES)
        return all_src
    return ALL_SOURCE_URLS


# Sources handled by dedicated scrapers (not the generic MultiStrategy scraper).
_DEDICATED_SCRAPERS = {"eventbrite-hk"}


def build_scrapers() -> list:
    scrapers = []
    if Config.SCRAPE_INCLUDE_SAMPLE:
        scrapers.append(SampleHongKongScraper())

    # Dedicated scrapers that use APIs / embedded JSON instead of generic HTML parsing.
    scrapers.append(LumaScraper())
    scrapers.append(EventbriteScraper())

    for source_name, urls in selected_sources().items():
        if source_name in _DEDICATED_SCRAPERS:
            continue  # handled above
        scrapers.append(MultiStrategyEventScraper(source_name=source_name, urls=urls))
    return scrapers
