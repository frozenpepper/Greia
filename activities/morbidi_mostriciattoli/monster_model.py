"""Domain model for Fluffy Monsters: recipe, studio editor and gallery.

Pure Python (no Pygame). A ``MonsterRecipe`` is an immutable, portable list of
semantic part IDs plus an optional child-made name; the studio ``MonsterEditor``
owns the recipe being built with a bounded undo history; ``MonsterGallery``
keeps up to ``MAX_SAVED_PORTRAITS`` saved friends (newest first, never evicted).
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
import random
import time
from typing import Final, Mapping, Sequence
import uuid

from greia_platform.typography import grapheme_spans

if __package__:
    from .monster_content import (
        CATEGORY_ORDER,
        DEFAULTS,
        LEGACY_MISSING,
        MAX_NAME_SYLLABLES,
        MAX_SAVED_PORTRAITS,
        OPTIONS,
        PRESET_NAMES,
        SYLLABLES,
        VALID_IDS,
        Category,
        canonical_id,
    )
else:
    from monster_content import (
        CATEGORY_ORDER,
        DEFAULTS,
        LEGACY_MISSING,
        MAX_NAME_SYLLABLES,
        MAX_SAVED_PORTRAITS,
        OPTIONS,
        PRESET_NAMES,
        SYLLABLES,
        VALID_IDS,
        Category,
        canonical_id,
    )

MAX_NAME_GRAPHEMES: Final = 24
MAX_UNDO_STACK: Final = 12
MAX_ID_LENGTH: Final = 80


def valid_portrait_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= MAX_ID_LENGTH
        and all((ch.isascii() and ch.isalnum() and not ch.isupper()) or ch in "-_" for ch in value)
    )


@dataclass(frozen=True, slots=True)
class MonsterRecipe:
    """One immutable monster: nine semantic part IDs, a name and identity."""

    portrait_id: str
    body_shape: str
    body_color: str
    eyes: str
    mouth: str
    tuft: str
    accessory: str
    pattern: str = "none"
    arms: str = "stubby"
    feet: str = "paws"
    name: str = ""
    created_at: int = 0

    def __post_init__(self) -> None:
        if not valid_portrait_id(self.portrait_id):
            raise ValueError("invalid portrait_id")
        for category in CATEGORY_ORDER:
            if self.get(category) not in VALID_IDS[category]:
                raise ValueError(f"unknown {category.value}: {self.get(category)!r}")
        if not isinstance(self.name, str) or "\x00" in self.name:
            raise ValueError("invalid monster name")
        if len(grapheme_spans(self.name)) > MAX_NAME_GRAPHEMES:
            raise ValueError(f"monster name exceeds {MAX_NAME_GRAPHEMES} graphemes")

    @classmethod
    def default_recipe(cls, portrait_id: str | None = None, *, created_at: int | None = None) -> "MonsterRecipe":
        values = {category.value: DEFAULTS[category] for category in CATEGORY_ORDER}
        return cls(
            portrait_id=portrait_id or str(uuid.uuid4()),
            created_at=int(time.time()) if created_at is None else created_at,
            **values,
        )

    def get(self, category: Category) -> str:
        return getattr(self, category.value)

    @property
    def parts_key(self) -> tuple[str, ...]:
        """The look of the monster (identity and name excluded)."""

        return tuple(self.get(category) for category in CATEGORY_ORDER)

    def with_choice(self, category: Category, option_id: str) -> "MonsterRecipe":
        if option_id not in VALID_IDS[category]:
            return self
        return replace(self, **{category.value: option_id})

    def with_name(self, name: str) -> "MonsterRecipe":
        return replace(self, name=clean_name(name))

    def with_identity(self, portrait_id: str, created_at: int) -> "MonsterRecipe":
        return replace(self, portrait_id=portrait_id, created_at=created_at)

    # -- portable JSON --------------------------------------------------------------

    def to_json(self) -> dict[str, object]:
        data: dict[str, object] = {"portrait_id": self.portrait_id, "name": self.name, "created_at": self.created_at}
        for category in CATEGORY_ORDER:
            data[category.value] = self.get(category)
        return data

    @classmethod
    def from_json(cls, raw: object) -> "MonsterRecipe | None":
        """Parse one stored recipe (current or first-release); None if unusable."""

        if not isinstance(raw, Mapping):
            return None
        values: dict[str, object] = {}
        for category in CATEGORY_ORDER:
            stored = raw.get(category.value)
            if stored is None and category in LEGACY_MISSING:
                values[category.value] = LEGACY_MISSING[category]
                continue
            mapped = canonical_id(category, stored)
            if mapped is None:
                return None
            values[category.value] = mapped
        created = raw.get("created_at", 0)
        name = raw.get("name", "")
        try:
            return cls(
                portrait_id=raw.get("portrait_id"),  # type: ignore[arg-type]
                name=clean_name(name if isinstance(name, str) else ""),
                created_at=int(created) if isinstance(created, (int, float)) and not isinstance(created, bool) else 0,
                **values,  # type: ignore[arg-type]
            )
        except (TypeError, ValueError):
            return None


def clean_name(name: str) -> str:
    """Trim to the grapheme limit and drop control characters."""

    name = "".join(ch for ch in name if ch.isprintable())
    spans = grapheme_spans(name)
    if len(spans) > MAX_NAME_GRAPHEMES:
        name = name[: spans[MAX_NAME_GRAPHEMES - 1].end]
    return name


class MonsterEditor:
    """The monster being built in the studio, with a bounded undo history.

    ``is_blank`` stays True until the child really changes something, so an
    untouched starting monster can never be saved as a "creation".
    """

    def __init__(self, recipe: MonsterRecipe | None = None, *, blank: bool | None = None) -> None:
        self.recipe = recipe or MonsterRecipe.default_recipe()
        self.active_category = Category.BODY_SHAPE
        self._start = self.recipe
        self._undo: list[MonsterRecipe] = []
        self._syllables: list[str] = self._split_syllables(self.recipe.name)
        self._forced_dirty = blank is False
        self.revision = 0

    @property
    def is_blank(self) -> bool:
        if self._forced_dirty:
            return False
        return self.recipe.parts_key == self._start.parts_key and self.recipe.name == self._start.name

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    def select_category(self, category: Category) -> None:
        self.active_category = category

    def choose(self, category: Category, option_id: str) -> bool:
        candidate = self.recipe.with_choice(category, option_id)
        if candidate == self.recipe:
            return False
        self._commit(candidate)
        return True

    def surprise(self, rng: random.Random) -> bool:
        """A random monster that differs from the current one (name kept)."""

        for _ in range(32):
            candidate = self.recipe
            for category in CATEGORY_ORDER:
                candidate = candidate.with_choice(category, rng.choice(OPTIONS[category]).option_id)
            if candidate.parts_key != self.recipe.parts_key:
                self._commit(candidate)
                return True
        return False

    # -- names from syllables ----------------------------------------------------------

    @property
    def syllable_count(self) -> int:
        return len(self._syllables)

    def add_syllable(self, syllable: str) -> bool:
        if syllable not in SYLLABLES:
            return False
        parts = list(self._syllables) if self._syllables or not self.recipe.name else []
        if len(parts) >= MAX_NAME_SYLLABLES:
            return False
        parts.append(syllable)
        self._commit(self.recipe.with_name("".join(parts)))
        self._syllables = parts
        return True

    def erase_syllable(self) -> bool:
        if not self.recipe.name:
            return False
        parts = self._syllables[:-1] if self._syllables else []
        self._commit(self.recipe.with_name("".join(parts)))
        self._syllables = parts
        return True

    def random_name(self, rng: random.Random) -> bool:
        name = self.recipe.name
        while name == self.recipe.name:
            # Half the time a ready-made silly name, otherwise two random syllables.
            name = rng.choice(PRESET_NAMES) if rng.random() < 0.5 else rng.choice(SYLLABLES) + rng.choice(SYLLABLES)
        self._commit(self.recipe.with_name(name))
        self._syllables = self._split_syllables(name)
        return True

    # -- history -------------------------------------------------------------------------

    def undo(self) -> bool:
        if not self._undo:
            return False
        self.recipe = self._undo.pop()
        self._syllables = self._split_syllables(self.recipe.name)
        self.revision += 1
        return True

    def _commit(self, candidate: MonsterRecipe) -> None:
        self._undo.append(self.recipe)
        del self._undo[:-MAX_UNDO_STACK]
        self.recipe = candidate
        self.revision += 1

    @staticmethod
    def _split_syllables(name: str) -> list[str]:
        if name and len(name) % 2 == 0:
            parts = [name[index:index + 2] for index in range(0, len(name), 2)]
            if len(parts) <= MAX_NAME_SYLLABLES and all(part in SYLLABLES for part in parts):
                return parts
        return []


class MonsterGallery:
    """Up to ``MAX_SAVED_PORTRAITS`` saved monsters, newest first; never evicts."""

    def __init__(self, recipes: Sequence[MonsterRecipe] = ()) -> None:
        unique: list[MonsterRecipe] = []
        seen: set[str] = set()
        for recipe in recipes:
            if recipe.portrait_id in seen:
                continue
            seen.add(recipe.portrait_id)
            unique.append(recipe)
        self._recipes = unique[:MAX_SAVED_PORTRAITS]

    @property
    def recipes(self) -> tuple[MonsterRecipe, ...]:
        return tuple(self._recipes)

    @property
    def count(self) -> int:
        return len(self._recipes)

    @property
    def is_full(self) -> bool:
        return len(self._recipes) >= MAX_SAVED_PORTRAITS

    def add(self, recipe: MonsterRecipe) -> bool:
        if self.is_full or self.get(recipe.portrait_id) is not None:
            return False
        self._recipes.insert(0, recipe)
        return True

    def delete(self, portrait_id: str) -> bool:
        before = len(self._recipes)
        self._recipes = [recipe for recipe in self._recipes if recipe.portrait_id != portrait_id]
        return len(self._recipes) < before

    def get(self, portrait_id: str) -> MonsterRecipe | None:
        for recipe in self._recipes:
            if recipe.portrait_id == portrait_id:
                return recipe
        return None

    def index_of(self, portrait_id: str) -> int | None:
        for index, recipe in enumerate(self._recipes):
            if recipe.portrait_id == portrait_id:
                return index
        return None

    def page(self, page: int, size: int) -> tuple[MonsterRecipe, ...]:
        start = max(0, page) * size
        return tuple(self._recipes[start:start + size])

    def page_count(self, size: int) -> int:
        return max(1, (len(self._recipes) + size - 1) // size)


RECIPE_FIELDS: Final = frozenset(field.name for field in fields(MonsterRecipe))

__all__ = [
    "MAX_NAME_GRAPHEMES",
    "MAX_SAVED_PORTRAITS",
    "MAX_UNDO_STACK",
    "MonsterEditor",
    "MonsterGallery",
    "MonsterRecipe",
    "RECIPE_FIELDS",
    "clean_name",
    "valid_portrait_id",
]
