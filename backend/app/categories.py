from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryConfig:
    name: str
    slug: str
    color: str
    icon: str


CATEGORY_DEFINITIONS: list[CategoryConfig] = [
    CategoryConfig(name="Music / Concert", slug="music", color="#3B82F6", icon="music"),
    CategoryConfig(name="Party / Club", slug="party", color="#EF4444", icon="party"),
    CategoryConfig(name="Sports", slug="sports", color="#10B981", icon="sports"),
    CategoryConfig(name="Food & Dining", slug="food", color="#EAB308", icon="food"),
    CategoryConfig(name="Culture / Theater", slug="culture", color="#8B5CF6", icon="culture"),
    CategoryConfig(name="Networking / Business", slug="networking", color="#14B8A6", icon="networking")
]


def category_by_slug() -> dict[str, CategoryConfig]:
    return {category.slug: category for category in CATEGORY_DEFINITIONS}
