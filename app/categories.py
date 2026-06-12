from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable


@dataclass(frozen=True)
class CategoryConfig:
    label: str
    color: str
    text_color: str
    keywords: tuple[str, ...]
    priority: int


CATEGORY_DEFINITIONS: Dict[str, CategoryConfig] = {
    "music": CategoryConfig(
        "Music / Concert",
        "#2f6df6",
        "#f8fbff",
        ("concert", "live", "dj", "gig", "music", "band", "techno", "house", "trance", "hip hop"),
        7,
    ),
    "party": CategoryConfig(
        "Party / Club",
        "#d94b3d",
        "#fff8f5",
        ("club", "party", "nightlife", "bar", "rave", "guestlist", "bottle service", "ladies night", "rooftop"),
        4,
    ),
    "sports": CategoryConfig(
        "Sports",
        "#169b72",
        "#f6fffc",
        ("football", "soccer", "rugby", "basketball", "marathon", "sports", "run"),
        8,
    ),
    "food": CategoryConfig(
        "Food & Dining",
        "#d69418",
        "#fffaf0",
        ("brunch", "wine", "dining", "restaurant", "food", "tasting"),
        6,
    ),
    "culture": CategoryConfig(
        "Culture / Theater",
        "#7d57c2",
        "#faf7ff",
        ("theater", "museum", "exhibition", "opera", "culture", "art"),
        5,
    ),
    "networking": CategoryConfig(
        "Networking / Business",
        "#167e8f",
        "#f3feff",
        ("networking", "startup", "summit", "conference", "business"),
        5,
    ),
    "other": CategoryConfig("Other", "#6c7284", "#f8f9fb", (), 0),
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
            "text_color": cfg.text_color,
        }
