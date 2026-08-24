"""Domain model, recipe definition, and editor state for Morbidi Mostriciattoli."""

from __future__ import annotations

from dataclasses import dataclass
import random
import time
from typing import Final, Sequence
import uuid

from greia_platform.typography import (
    grapheme_spans,
    next_grapheme_boundary,
    previous_grapheme_boundary,
)

if __package__:
    from .monster_content import (
        ACCESSORY_OPTIONS,
        BODY_COLORS,
        BODY_SHAPES,
        DEFAULT_ACCESSORY_ID,
        DEFAULT_COLOR_ID,
        DEFAULT_EYES_ID,
        DEFAULT_MOUTH_ID,
        DEFAULT_SHAPE_ID,
        DEFAULT_TUFT_ID,
        EYE_OPTIONS,
        MOUTH_OPTIONS,
        TUFT_OPTIONS,
        VALID_ACCESSORY_IDS,
        VALID_COLOR_IDS,
        VALID_EYE_IDS,
        VALID_MOUTH_IDS,
        VALID_SHAPE_IDS,
        VALID_TUFT_IDS,
        Category,
    )
else:
    from monster_content import (
        ACCESSORY_OPTIONS,
        BODY_COLORS,
        BODY_SHAPES,
        DEFAULT_ACCESSORY_ID,
        DEFAULT_COLOR_ID,
        DEFAULT_EYES_ID,
        DEFAULT_MOUTH_ID,
        DEFAULT_SHAPE_ID,
        DEFAULT_TUFT_ID,
        EYE_OPTIONS,
        MOUTH_OPTIONS,
        TUFT_OPTIONS,
        VALID_ACCESSORY_IDS,
        VALID_COLOR_IDS,
        VALID_EYE_IDS,
        VALID_MOUTH_IDS,
        VALID_SHAPE_IDS,
        VALID_TUFT_IDS,
        Category,
    )


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
MAX_NAME_GRAPHEMES: Final = 24
MAX_UNDO_STACK: Final = 8
MAX_SAVED_PORTRAITS: Final = 24


@dataclass(frozen=True, slots=True)
class MonsterRecipe:
    """One immutable, portable semantic monster portrait recipe."""

    portrait_id: str
    body_shape: str
    body_color: str
    eyes: str
    mouth: str
    tuft: str
    accessory: str
    name: str = ""
    created_at: int = 0

    def __post_init__(self) -> None:
        if not self.portrait_id:
            raise ValueError("portrait_id must not be empty")
        if self.body_shape not in VALID_SHAPE_IDS:
            raise ValueError(f"unknown body_shape: {self.body_shape!r}")
        if self.body_color not in VALID_COLOR_IDS:
            raise ValueError(f"unknown body_color: {self.body_color!r}")
        if self.eyes not in VALID_EYE_IDS:
            raise ValueError(f"unknown eyes: {self.eyes!r}")
        if self.mouth not in VALID_MOUTH_IDS:
            raise ValueError(f"unknown mouth: {self.mouth!r}")
        if self.tuft not in VALID_TUFT_IDS:
            raise ValueError(f"unknown tuft: {self.tuft!r}")
        if self.accessory not in VALID_ACCESSORY_IDS:
            raise ValueError(f"unknown accessory: {self.accessory!r}")
        if len(grapheme_spans(self.name)) > MAX_NAME_GRAPHEMES:
            raise ValueError(f"monster name exceeds {MAX_NAME_GRAPHEMES} graphemes")

    @classmethod
    def default_recipe(cls, portrait_id: str | None = None) -> MonsterRecipe:
        return cls(
            portrait_id=portrait_id or str(uuid.uuid4()),
            body_shape=DEFAULT_SHAPE_ID,
            body_color=DEFAULT_COLOR_ID,
            eyes=DEFAULT_EYES_ID,
            mouth=DEFAULT_MOUTH_ID,
            tuft=DEFAULT_TUFT_ID,
            accessory=DEFAULT_ACCESSORY_ID,
            name="",
            created_at=int(time.time()),
        )

    def with_category(self, category: Category, option_id: str) -> MonsterRecipe:
        kwargs = {
            "portrait_id": self.portrait_id,
            "body_shape": self.body_shape,
            "body_color": self.body_color,
            "eyes": self.eyes,
            "mouth": self.mouth,
            "tuft": self.tuft,
            "accessory": self.accessory,
            "name": self.name,
            "created_at": self.created_at,
        }
        if category == Category.BODY_SHAPE and option_id in VALID_SHAPE_IDS:
            kwargs["body_shape"] = option_id
        elif category == Category.BODY_COLOR and option_id in VALID_COLOR_IDS:
            kwargs["body_color"] = option_id
        elif category == Category.EYES and option_id in VALID_EYE_IDS:
            kwargs["eyes"] = option_id
        elif category == Category.MOUTH and option_id in VALID_MOUTH_IDS:
            kwargs["mouth"] = option_id
        elif category == Category.TUFT and option_id in VALID_TUFT_IDS:
            kwargs["tuft"] = option_id
        elif category == Category.ACCESSORY and option_id in VALID_ACCESSORY_IDS:
            kwargs["accessory"] = option_id
        return MonsterRecipe(**kwargs)

    def with_name(self, name: str) -> MonsterRecipe:
        spans = grapheme_spans(name)
        if len(spans) > MAX_NAME_GRAPHEMES:
            last_span = spans[MAX_NAME_GRAPHEMES - 1]
            trimmed = name[: last_span.end_byte]
        else:
            trimmed = name
        return MonsterRecipe(
            portrait_id=self.portrait_id,
            body_shape=self.body_shape,
            body_color=self.body_color,
            eyes=self.eyes,
            mouth=self.mouth,
            tuft=self.tuft,
            accessory=self.accessory,
            name=trimmed,
            created_at=self.created_at,
        )


class MonsterEditor:
    """Manage active recipe, undo/redo history, category selection, and randomizer."""

    def __init__(self, recipe: MonsterRecipe | None = None) -> None:
        self.recipe = recipe or MonsterRecipe.default_recipe()
        self.active_category = Category.BODY_SHAPE
        self._undo_stack: list[MonsterRecipe] = []
        self._redo_stack: list[MonsterRecipe] = []

    def select_category(self, category: Category) -> None:
        self.active_category = category

    def apply_option(self, option_id: str) -> bool:
        new_recipe = self.recipe.with_category(self.active_category, option_id)
        if new_recipe == self.recipe:
            return False
        self._push_undo()
        self.recipe = new_recipe
        return True

    def set_name(self, name: str) -> bool:
        new_recipe = self.recipe.with_name(name)
        if new_recipe.name == self.recipe.name:
            return False
        self._push_undo()
        self.recipe = new_recipe
        return True

    def surprise_me(self, rng: random.Random) -> bool:
        """Pick one known ID per category; must produce a recipe different from current."""
        for _ in range(50):
            shape = rng.choice(BODY_SHAPES).option_id
            color = rng.choice(BODY_COLORS).option_id
            eyes = rng.choice(EYE_OPTIONS).option_id
            mouth = rng.choice(MOUTH_OPTIONS).option_id
            tuft = rng.choice(TUFT_OPTIONS).option_id
            acc = rng.choice(ACCESSORY_OPTIONS).option_id

            candidate = MonsterRecipe(
                portrait_id=self.recipe.portrait_id,
                body_shape=shape,
                body_color=color,
                eyes=eyes,
                mouth=mouth,
                tuft=tuft,
                accessory=acc,
                name=self.recipe.name,
                created_at=self.recipe.created_at,
            )
            if candidate != self.recipe:
                self._push_undo()
                self.recipe = candidate
                return True
        return False

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        self._redo_stack.append(self.recipe)
        self.recipe = self._undo_stack.pop()
        return True

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        self._undo_stack.append(self.recipe)
        self.recipe = self._redo_stack.pop()
        return True

    def _push_undo(self) -> None:
        self._undo_stack.append(self.recipe)
        if len(self._undo_stack) > MAX_UNDO_STACK:
            self._undo_stack.pop(0)
        self._redo_stack.clear()


class MonsterGallery:
    """Manage collection of up to 24 saved monster portrait recipes."""

    def __init__(self, recipes: Sequence[MonsterRecipe] = ()) -> None:
        self._recipes: list[MonsterRecipe] = list(recipes[:MAX_SAVED_PORTRAITS])

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
        if self.is_full:
            return False
        if any(r.portrait_id == recipe.portrait_id for r in self._recipes):
            return False
        self._recipes.insert(0, recipe)  # Newest first
        return True

    def delete(self, portrait_id: str) -> bool:
        initial = len(self._recipes)
        self._recipes = [r for r in self._recipes if r.portrait_id != portrait_id]
        return len(self._recipes) < initial

    def get(self, portrait_id: str) -> MonsterRecipe | None:
        for r in self._recipes:
            if r.portrait_id == portrait_id:
                return r
        return None
