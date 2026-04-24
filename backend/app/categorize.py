from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryRule:
    slug: str
    keywords: tuple[str, ...]
    source_hints: tuple[str, ...] = ()


RULES: tuple[CategoryRule, ...] = (
    CategoryRule(
        slug="music",
        keywords=("concert", "music", "live", "dj", "gig", "band", "orchestra", "festival"),
        source_hints=("ticketflap",)
    ),
    CategoryRule(
        slug="party",
        keywords=("club", "party", "nightlife", "rave", "drink", "bar", "dance"),
        source_hints=("club", "bar")
    ),
    CategoryRule(
        slug="sports",
        keywords=("sport", "football", "tennis", "run", "marathon", "match", "race", "fitness"),
        source_hints=("sports",)
    ),
    CategoryRule(
        slug="food",
        keywords=("food", "dining", "restaurant", "tasting", "brunch", "wine", "cocktail"),
        source_hints=("restaurant",)
    ),
    CategoryRule(
        slug="networking",
        keywords=("networking", "startup", "business", "conference", "seminar", "workshop", "meetup"),
        source_hints=("meetup", "eventbrite")
    ),
    CategoryRule(
        slug="culture",
        keywords=("theater", "culture", "museum", "art", "exhibition", "performance", "heritage"),
        source_hints=("discoverhongkong", "klook")
    )
)


def categorize_event(
    title: str | None,
    description: str | None,
    source_name: str,
    source_url: str
) -> str:
    source_blob = f"{source_name} {source_url}".lower()
    text_blob = f"{title or ''} {description or ''}".lower()

    for rule in RULES:
        if any(hint in source_blob for hint in rule.source_hints) and any(
            keyword in text_blob for keyword in rule.keywords
        ):
            return rule.slug

    for rule in RULES:
        if any(keyword in text_blob for keyword in rule.keywords):
            return rule.slug

    return "culture"
