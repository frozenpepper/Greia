from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from greia_platform.activities import ActivityManifest
from greia_platform.ui_core import Collection


ALL_ACTIVITIES_ID = "all"
_CATEGORY_ORDER = {
    "create": 10,
    "play": 20,
    "learn": 30,
    "explore": 40,
    "my_greia": 50,
}
_CATEGORY_ICONS = {
    ALL_ACTIVITIES_ID: "backpack",
    "create": "palette",
    "play": "puzzle_pieces",
    "learn": "book",
    "explore": "magnifier",
    "my_greia": "unicorn",
}
_DEFAULT_CATEGORY_ICON = "backpack"


_CATEGORY_TRANSLATIONS: dict[str, dict[str, str]] = {
    ALL_ACTIVITIES_ID: {
        "it": "Tutti",
        "en": "All",
        "es": "Todos",
        "de": "Alle",
        "fr": "Tous",
    },
    "create": {
        "it": "Crea",
        "en": "Create",
        "es": "Crea",
        "de": "Erschaffen",
        "fr": "Créer",
    },
    "play": {
        "it": "Gioca",
        "en": "Play",
        "es": "Jugar",
        "de": "Spielen",
        "fr": "Jouer",
    },
    "learn": {
        "it": "Impara",
        "en": "Learn",
        "es": "Aprender",
        "de": "Lernen",
        "fr": "Apprendre",
    },
    "explore": {
        "it": "Esplora",
        "en": "Explore",
        "es": "Explorar",
        "de": "Entdecken",
        "fr": "Explorer",
    },
    "my_greia": {
        "it": "Mio Greia",
        "en": "My Greia",
        "es": "Mi Greia",
        "de": "Mein Greia",
        "fr": "Mon Greia",
    },
}


@dataclass(frozen=True, slots=True)
class ActivityCatalogue:
    """Navigation-category projection of the authoritative Activity registry.

    Activities remain registry-owned objects; this class only builds semantic
    UI Collections. One Activity may appear in multiple launcher categories
    without duplicating package state or changing launch identity. Older API 0.1
    packages without explicit presentation metadata temporarily fall back to
    their education categories for compatibility.

    Each collection also carries a stable semantic Greia icon. The renderer may
    use that icon for category choices and for persistent in-category chrome;
    category identity never depends on a filesystem asset path.
    """

    collections: tuple[Collection[ActivityManifest], ...]

    @classmethod
    def from_activities(
        cls,
        activities: Iterable[ActivityManifest],
        locale: str = "it",
    ) -> "ActivityCatalogue":
        ordered = tuple(activities)
        buckets: dict[str, list[ActivityManifest]] = {}
        for activity in ordered:
            launcher_categories = getattr(activity, "launcher_categories", ())
            categories = launcher_categories or activity.categories
            for category in categories:
                normalized = category.strip().casefold()
                if not normalized:
                    continue
                buckets.setdefault(normalized, []).append(activity)
        collections: list[Collection[ActivityManifest]] = [
            Collection(
                ALL_ACTIVITIES_ID,
                ordered,
                title=_category_title(ALL_ACTIVITIES_ID, locale),
                icon_id=_category_icon(ALL_ACTIVITIES_ID),
            )
        ]
        for category_id in sorted(buckets, key=_category_sort_key):
            collections.append(
                Collection(
                    category_id,
                    tuple(buckets[category_id]),
                    title=_category_title(category_id, locale),
                    icon_id=_category_icon(category_id),
                )
            )
        return cls(tuple(collections))

    @property
    def category_ids(self) -> tuple[str, ...]:
        return tuple(item.collection_id for item in self.collections)

    def collection(self, category_id: str) -> Collection[ActivityManifest]:
        for collection in self.collections:
            if collection.collection_id == category_id:
                return collection
        return self.collections[0]

    def nearest_category(self, category_id: str | None) -> str:
        if category_id and category_id in self.category_ids:
            return category_id
        return ALL_ACTIVITIES_ID


def _category_sort_key(value: str) -> tuple[int, str]:
    return (_CATEGORY_ORDER.get(value, 100), value)


def _category_title(value: str, locale: str = "it") -> str:
    lang = locale.split("-")[0].lower() if locale else "it"
    trans = _CATEGORY_TRANSLATIONS.get(value)
    if trans:
        if lang in trans:
            return trans[lang]
        if "en" in trans:
            return trans["en"]
    return value.replace("_", " ").replace("-", " ").strip().title() or "Other"


def _category_icon(value: str) -> str:
    return _CATEGORY_ICONS.get(value, _DEFAULT_CATEGORY_ICON)
