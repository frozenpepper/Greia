"""Domain model and session invariants for Tre Carte Una Storia."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import random
from typing import Final, Sequence

from greia_platform.typography import (
    grapheme_spans,
    next_grapheme_boundary,
    previous_grapheme_boundary,
    snap_grapheme_boundary,
)

if __package__:
    from .story_cards_content import STORY_SEEDS, STORY_SEEDS_BY_ID, VALID_SEED_IDS, StoryCard, StorySeed
else:
    from story_cards_content import STORY_SEEDS, STORY_SEEDS_BY_ID, VALID_SEED_IDS, StoryCard, StorySeed


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
MAX_GRAPHEMES: Final = 80
MAX_SAVED_STORIES: Final = 12


class StoryStage(StrEnum):
    SEQUENCE = "sequence"
    CAPTION = "caption"


@dataclass(frozen=True, slots=True)
class SavedStory:
    """One immutable saved storybook record."""

    story_id: str
    created_at: int
    seed_id: str
    card_ids: tuple[str, str, str]
    caption_mode: str
    caption_text: str

    def __post_init__(self) -> None:
        if not self.story_id:
            raise ValueError("story_id must not be empty")
        if self.seed_id not in VALID_SEED_IDS:
            raise ValueError(f"unknown seed_id: {self.seed_id!r}")
        if len(self.card_ids) != 3:
            raise ValueError("story must contain exactly 3 cards")
        if len(grapheme_spans(self.caption_text)) > MAX_GRAPHEMES:
            raise ValueError(f"caption exceeds {MAX_GRAPHEMES} graphemes")


class StoryRound:
    """Manage active sequencing puzzle and caption composition."""

    def __init__(self, seed: StorySeed, initial_order: Sequence[StoryCard]) -> None:
        self.seed = seed
        self.current_order: list[StoryCard] = list(initial_order)
        self.target_order: tuple[str, str, str] = tuple(c.card_id for c in seed.cards)  # type: ignore[assignment]
        self.selected_slot: int | None = None
        self.error_count: int = 0
        self.stage: StoryStage = StoryStage.SEQUENCE
        self.caption_mode: str = "preset_0"
        self.custom_caption: str = ""
        self._cursor: int = 0

    @property
    def is_correct_order(self) -> bool:
        return tuple(c.card_id for c in self.current_order) == self.target_order

    @property
    def hint_revealed(self) -> bool:
        return self.error_count >= 2

    @property
    def cursor(self) -> int:
        return self._cursor

    @property
    def grapheme_count(self) -> int:
        return len(grapheme_spans(self.custom_caption))

    def swap_slots(self, i: int, j: int) -> bool:
        if 0 <= i < 3 and 0 <= j < 3 and i != j:
            self.current_order[i], self.current_order[j] = self.current_order[j], self.current_order[i]
            return True
        return False

    def select_slot(self, slot_index: int) -> bool:
        """Handle tap/keyboard slot selection or swap."""
        if not (0 <= slot_index < 3):
            return False
        if self.selected_slot is None:
            self.selected_slot = slot_index
            return True
        elif self.selected_slot == slot_index:
            self.selected_slot = None
            return True
        else:
            prev = self.selected_slot
            self.selected_slot = None
            return self.swap_slots(prev, slot_index)

    def check_sequence(self) -> bool:
        """Evaluate order and progress to caption stage on success."""
        if self.is_correct_order:
            self.stage = StoryStage.CAPTION
            self.selected_slot = None
            return True
        else:
            self.error_count += 1
            return False

    def set_preset_caption(self, preset_index: int) -> None:
        if 0 <= preset_index < 3:
            self.caption_mode = f"preset_{preset_index}"

    def set_custom_mode(self) -> None:
        self.caption_mode = "custom"

    def insert_custom(self, segment: str) -> bool:
        if not segment:
            return False
        clean = "".join(c for c in segment if ord(c) >= 32 or c in " ")
        if not clean:
            return False
        self._cursor = snap_grapheme_boundary(self.custom_caption, self._cursor)
        new_text = self.custom_caption[:self._cursor] + clean + self.custom_caption[self._cursor:]
        if len(grapheme_spans(new_text)) > MAX_GRAPHEMES:
            return False
        self.custom_caption = new_text
        self._cursor += len(clean)
        self._cursor = snap_grapheme_boundary(self.custom_caption, self._cursor)
        self.caption_mode = "custom"
        return True

    def backspace_custom(self) -> bool:
        if not self.custom_caption or self._cursor <= 0:
            return False
        self._cursor = snap_grapheme_boundary(self.custom_caption, self._cursor)
        prev = previous_grapheme_boundary(self.custom_caption, self._cursor)
        self.custom_caption = self.custom_caption[:prev] + self.custom_caption[self._cursor:]
        self._cursor = prev
        self.caption_mode = "custom"
        return True

    def delete_custom_forward(self) -> bool:
        if not self.custom_caption or self._cursor >= len(self.custom_caption):
            return False
        self._cursor = snap_grapheme_boundary(self.custom_caption, self._cursor)
        nxt = next_grapheme_boundary(self.custom_caption, self._cursor)
        self.custom_caption = self.custom_caption[:self._cursor] + self.custom_caption[nxt:]
        self.caption_mode = "custom"
        return True

    def move_cursor_left(self) -> bool:
        if self._cursor <= 0:
            return False
        self._cursor = previous_grapheme_boundary(self.custom_caption, self._cursor)
        return True

    def move_cursor_right(self) -> bool:
        if self._cursor >= len(self.custom_caption):
            return False
        self._cursor = next_grapheme_boundary(self.custom_caption, self._cursor)
        return True


class StoryLibrary:
    """Manage collection of up to 12 saved storybooks."""

    def __init__(self, stories: Sequence[SavedStory] = ()) -> None:
        self._stories: list[SavedStory] = list(stories[:MAX_SAVED_STORIES])

    @property
    def stories(self) -> tuple[SavedStory, ...]:
        return tuple(self._stories)

    @property
    def count(self) -> int:
        return len(self._stories)

    @property
    def is_full(self) -> bool:
        return len(self._stories) >= MAX_SAVED_STORIES

    def add(self, story: SavedStory) -> bool:
        if self.is_full:
            return False
        if any(s.story_id == story.story_id for s in self._stories):
            return False
        self._stories.insert(0, story)  # Newest first
        return True

    def delete(self, story_id: str) -> bool:
        initial_len = len(self._stories)
        self._stories = [s for s in self._stories if s.story_id != story_id]
        return len(self._stories) < initial_len

    def get(self, story_id: str) -> SavedStory | None:
        for s in self._stories:
            if s.story_id == story_id:
                return s
        return None


def create_shuffled_round(seed: StorySeed, rng: random.Random) -> StoryRound:
    """Create a new round guaranteed not to start in the correct order [0, 1, 2]."""
    cards = list(seed.cards)
    # Permutations other than (0, 1, 2): (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)
    order = list(range(3))
    while order == [0, 1, 2]:
        rng.shuffle(order)
    shuffled_cards = [cards[i] for i in order]
    return StoryRound(seed, shuffled_cards)
