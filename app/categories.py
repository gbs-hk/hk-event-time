from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable


@dataclass(frozen=True)
class CategoryConfig:
    label: str
    color: str
    keywords: tuple[str, ...]
    priority: int


CATEGORY_DEFINITIONS: Dict[str, CategoryConfig] = {
    "music": CategoryConfig(
        "Music / Concert",
        "#2b73ff",
        ("concert", "live", "dj", "gig", "music", "band", "techno", "house", "trance", "hip hop"),
        7,
    ),
    "party": CategoryConfig(
        "Party / Club",
        "#e84141",
        ("club", "party", "nightlife", "bar", "rave", "guestlist", "bottle service", "ladies night", "rooftop"),
        4,
    ),
    "sports": CategoryConfig("Sports", "#1e9a56", ("football", "soccer", "rugby", "basketball", "marathon", "sports", "run"), 8),
    "food": CategoryConfig("Food & Dining", "#d5a10d", ("brunch", "wine", "dining", "restaurant", "food", "tasting"), 6),
    "culture": CategoryConfig("Culture / Theater", "#7a4ddb", ("theater", "museum", "exhibition", "opera", "culture", "art"), 5),
    "networking": CategoryConfig("Networking / Business", "#3f879f", ("networking", "startup", "summit", "conference", "business"), 5),
    "other": CategoryConfig("Other", "#6d7380", (), 0),
}


def infer_category(*texts: str) -> str:
    haystack = " ".join(t.lower() for t in texts if t).strip()
    if not haystack:
        return "other"

    winner = "other"
    winner_score = 0
    for slug, cfg in CATEGORY_DEFINITIONS.items():
        if slug == "other":
            continue
        hits = sum(1 for keyword in cfg.keywords if keyword in haystack)
        if hits <= 0:
            continue
        score = hits * 100 + cfg.priority
        if score > winner_score:
            winner = slug
            winner_score = score

    return winner


def categories_for_api() -> Iterable[dict[str, str]]:
    for slug, cfg in CATEGORY_DEFINITIONS.items():
        yield {
            "slug": slug,
            "label": cfg.label,
            "color": cfg.color,
        }
