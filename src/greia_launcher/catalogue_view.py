from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from greia_platform.activities import ActivityManifest
from greia_platform.ui_core import Collection


ALL_ACTIVITIES_ID = "all"


@dataclass(frozen=True, slots=True)
class ActivityCatalogue:
    """Category projection of the authoritative Activity registry.

    Activities remain registry-owned objects; this class only builds semantic
    UI Collections. One Activity may appear in multiple categories without
    duplicating package state or changing launch identity.
    """

    collections: tuple[Collection[ActivityManifest], ...]

    @classmethod
    def from_activities(cls, activities: Iterable[ActivityManifest]) -> "ActivityCatalogue":
        ordered = tuple(activities)
        buckets: dict[str, list[ActivityManifest]] = {}
        for activity in ordered:
            for category in activity.categories:
                normalized = category.strip().casefold()
                if not normalized:
                    continue
                buckets.setdefault(normalized, []).append(activity)
        collections: list[Collection[ActivityManifest]] = [
            Collection(ALL_ACTIVITIES_ID, ordered, title="All")
        ]
        for category_id in sorted(buckets, key=_category_sort_key):
            collections.append(
                Collection(
                    category_id,
                    tuple(buckets[category_id]),
                    title=_category_title(category_id),
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
    # Creation/play/learning-style buckets can later receive localized display
    # ordering from platform metadata. Stable lexical order is deterministic in
    # the meantime and never derives authority from display text.
    return (0, value)


def _category_title(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip().title() or "Other"
