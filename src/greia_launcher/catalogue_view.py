from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from greia_platform.activities import ActivityManifest
from greia_platform.activity_discovery import AdaptiveCollectionPlanner
from greia_platform.ui_core import Collection


ALL_ACTIVITIES_ID = "all"
BROWSE_ACTIVITIES_ID = "browse"
PRIMARY_COLLECTION_IDS = (
    "create",
    "play",
    "learn",
    "explore",
    "my_greia",
)
# Sub-Collection vocabulary is platform-owned just like the root vocabulary.
# Packages may provide these semantic hints, but cannot invent arbitrary child
# navigation labels merely by writing a tag into their manifest.
DISCOVERY_GROUP_IDS = (
    "drawing",
    "writing",
    "music",
    "building",
    "numbers",
    "words",
    "puzzles",
    "nature",
    "stories",
    "making",
)
_CATEGORY_ORDER = {
    "create": 10,
    "play": 20,
    "learn": 30,
    "explore": 40,
    "my_greia": 50,
    BROWSE_ACTIVITIES_ID: 90,
}
_CATEGORY_ICONS = {
    ALL_ACTIVITIES_ID: "backpack",
    BROWSE_ACTIVITIES_ID: "backpack",
    "create": "palette",
    "play": "puzzle_pieces",
    "learn": "book",
    "explore": "magnifier",
    "my_greia": "unicorn",
}
_DISCOVERY_ICONS = {
    "drawing": "palette",
    "writing": "book",
    "music": "palette",
    "building": "puzzle_pieces",
    "numbers": "puzzle_pieces",
    "words": "book",
    "puzzles": "puzzle_pieces",
    "nature": "magnifier",
    "stories": "book",
    "making": "palette",
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
    BROWSE_ACTIVITIES_ID: {
        "it": "Altro",
        "en": "More",
        "es": "Más",
        "de": "Mehr",
        "fr": "Autres",
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

_DISCOVERY_TRANSLATIONS: dict[str, dict[str, str]] = {
    "drawing": {"it": "Disegna", "en": "Drawing", "es": "Dibujo", "de": "Malen", "fr": "Dessin"},
    "writing": {"it": "Scrivi", "en": "Writing", "es": "Escribir", "de": "Schreiben", "fr": "Écrire"},
    "music": {"it": "Musica", "en": "Music", "es": "Música", "de": "Musik", "fr": "Musique"},
    "building": {"it": "Costruisci", "en": "Building", "es": "Construir", "de": "Bauen", "fr": "Construire"},
    "numbers": {"it": "Numeri", "en": "Numbers", "es": "Números", "de": "Zahlen", "fr": "Nombres"},
    "words": {"it": "Parole", "en": "Words", "es": "Palabras", "de": "Wörter", "fr": "Mots"},
    "puzzles": {"it": "Rompicapi", "en": "Puzzles", "es": "Puzles", "de": "Rätsel", "fr": "Casse-têtes"},
    "nature": {"it": "Natura", "en": "Nature", "es": "Naturaleza", "de": "Natur", "fr": "Nature"},
    "stories": {"it": "Storie", "en": "Stories", "es": "Historias", "de": "Geschichten", "fr": "Histoires"},
    "making": {"it": "Crea cose", "en": "Making", "es": "Crear", "de": "Gestalten", "fr": "Créer"},
}


@dataclass(frozen=True, slots=True)
class ActivityCatalogue:
    """Navigation projection of the authoritative Activity registry.

    Activities remain registry-owned objects; this class only builds semantic
    UI Collections. One Activity may appear in multiple launcher categories
    without duplicating package state or changing launch identity. Older API 0.1
    packages without explicit presentation metadata temporarily fall back to
    their education categories for compatibility.

    The child Home vocabulary is deliberately platform-owned. Arbitrary package
    category IDs are accepted as metadata for compatibility, but they do not
    manufacture new child navigation levels. An Activity with no recognized
    primary Collection remains discoverable through a bounded platform-owned
    ``browse`` fallback Collection.

    ``subcollections`` is an optional one-level presentation projection. The
    primary Collection still owns the complete Activity tuple, so counts,
    identity and package authority remain unchanged when adaptive grouping is
    active.
    """

    collections: tuple[Collection[ActivityManifest], ...]
    subcollections: tuple[
        tuple[str, tuple[Collection[ActivityManifest], ...]], ...
    ] = ()

    @classmethod
    def from_activities(
        cls,
        activities: Iterable[ActivityManifest],
        locale: str = "it",
        *,
        previously_subdivided: Iterable[str] = (),
        adaptive: bool = True,
    ) -> "ActivityCatalogue":
        ordered = tuple(activities)
        buckets: dict[str, list[ActivityManifest]] = {}
        primary_membership: dict[str, bool] = {}

        for activity in ordered:
            launcher_categories = getattr(activity, "launcher_categories", ())
            categories = launcher_categories or activity.categories
            normalized_categories = tuple(
                category.strip().casefold()
                for category in categories
                if category.strip()
            )
            recognized = tuple(
                category
                for category in normalized_categories
                if category in PRIMARY_COLLECTION_IDS
            )
            for category in recognized:
                buckets.setdefault(category, []).append(activity)
            primary_membership[activity.activity_id] = bool(recognized)

        orphaned = tuple(
            activity
            for activity in ordered
            if not primary_membership.get(activity.activity_id, False)
        )
        if orphaned:
            buckets[BROWSE_ACTIVITIES_ID] = list(orphaned)

        collections: list[Collection[ActivityManifest]] = [
            Collection(
                ALL_ACTIVITIES_ID,
                ordered,
                title=_category_title(ALL_ACTIVITIES_ID, locale),
                icon_id=_category_icon(ALL_ACTIVITIES_ID),
            )
        ]
        subdivision_state = frozenset(previously_subdivided)
        planner = AdaptiveCollectionPlanner()
        nested: list[tuple[str, tuple[Collection[ActivityManifest], ...]]] = []

        for category_id in sorted(buckets, key=_category_sort_key):
            items = tuple(buckets[category_id])
            collections.append(
                Collection(
                    category_id,
                    items,
                    title=_category_title(category_id, locale),
                    icon_id=_category_icon(category_id),
                )
            )
            if not adaptive or category_id not in PRIMARY_COLLECTION_IDS:
                continue
            plan = planner.plan(
                category_id,
                items,
                allowed_group_ids=DISCOVERY_GROUP_IDS,
                previously_subdivided=category_id in subdivision_state,
            )
            if not plan.subdivided:
                continue
            groups = tuple(
                Collection(
                    group.group_id,
                    group.activities,
                    title=_discovery_title(group.group_id, locale),
                    icon_id=_discovery_icon(group.group_id),
                )
                for group in plan.groups
            )
            nested.append((category_id, groups))
        return cls(tuple(collections), tuple(nested))

    @property
    def category_ids(self) -> tuple[str, ...]:
        return tuple(item.collection_id for item in self.collections)

    @property
    def home_collections(self) -> tuple[Collection[ActivityManifest], ...]:
        """Return the bounded platform-owned child Home destinations."""

        return tuple(
            collection
            for collection in self.collections
            if collection.collection_id != ALL_ACTIVITIES_ID and collection.items
        )

    @property
    def subdivided_collection_ids(self) -> tuple[str, ...]:
        return tuple(collection_id for collection_id, _ in self.subcollections)

    def collection(self, category_id: str) -> Collection[ActivityManifest]:
        for collection in self.collections:
            if collection.collection_id == category_id:
                return collection
        return self.collections[0]

    def subcollections_for(
        self, category_id: str
    ) -> tuple[Collection[ActivityManifest], ...]:
        for collection_id, groups in self.subcollections:
            if collection_id == category_id:
                return groups
        return ()

    def subcollection(
        self, category_id: str, group_id: str
    ) -> Collection[ActivityManifest] | None:
        for group in self.subcollections_for(category_id):
            if group.collection_id == group_id:
                return group
        return None

    def nearest_category(self, category_id: str | None) -> str:
        if category_id and category_id in self.category_ids:
            return category_id
        return ALL_ACTIVITIES_ID


def _category_sort_key(value: str) -> tuple[int, str]:
    return (_CATEGORY_ORDER.get(value, 100), value)


def _category_title(value: str, locale: str = "it") -> str:
    return _localized_title(_CATEGORY_TRANSLATIONS, value, locale)


def _discovery_title(value: str, locale: str = "it") -> str:
    return _localized_title(_DISCOVERY_TRANSLATIONS, value, locale)


def _localized_title(
    translations: dict[str, dict[str, str]], value: str, locale: str
) -> str:
    lang = locale.split("-")[0].lower() if locale else "it"
    trans = translations.get(value)
    if trans:
        if lang in trans:
            return trans[lang]
        if "en" in trans:
            return trans["en"]
    return value.replace("_", " ").replace("-", " ").strip().title() or "Other"


def _category_icon(value: str) -> str:
    return _CATEGORY_ICONS.get(value, _DEFAULT_CATEGORY_ICON)


def _discovery_icon(value: str) -> str:
    return _DISCOVERY_ICONS.get(value, _DEFAULT_CATEGORY_ICON)
