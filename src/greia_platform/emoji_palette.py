from __future__ import annotations

from dataclasses import dataclass

from .typography import grapheme_spans, is_emoji_cluster


@dataclass(frozen=True, slots=True)
class EmojiCategory:
    """Small semantic group for Greia's child-facing emoji picker."""

    category_id: str
    icon: str
    emoji: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.category_id or not self.category_id.replace("_", "").isalnum():
            raise ValueError("emoji category id must be a simple semantic identifier")
        if len(grapheme_spans(self.icon)) != 1 or not is_emoji_cluster(self.icon):
            raise ValueError("emoji category icon must be exactly one emoji grapheme")
        if not self.emoji:
            raise ValueError("emoji category must not be empty")
        if len(self.emoji) > 24:
            raise ValueError("emoji category exceeds Greia's bounded picker size")
        seen: set[str] = set()
        for cluster in self.emoji:
            if len(grapheme_spans(cluster)) != 1 or not is_emoji_cluster(cluster):
                raise ValueError(f"picker item is not one emoji grapheme: {cluster!r}")
            if cluster in seen:
                raise ValueError(f"duplicate emoji in category: {cluster!r}")
            seen.add(cluster)


DEFAULT_EMOJI_CATEGORIES: tuple[EmojiCategory, ...] = (
    EmojiCategory(
        "faces",
        "😊",
        (
            "😀", "😃", "😄", "😁", "😊", "🥰",
            "😂", "🤩", "😮", "🤔", "😴", "😎",
            "🥳", "🤗", "😋", "😉", "🙃", "🥹",
        ),
    ),
    EmojiCategory(
        "animals",
        "🦄",
        (
            "🐱", "🐶", "🐰", "🦊", "🐻", "🐼",
            "🦄", "🦖", "🦕", "🐸", "🐵", "🦁",
            "🐯", "🐮", "🐷", "🐙", "🐬", "🦋",
        ),
    ),
    EmojiCategory(
        "nature",
        "🌈",
        (
            "🌈", "⭐", "🌟", "✨", "☀️", "🌙",
            "☁️", "❄️", "🌸", "🌻", "🌷", "🌳",
            "🍀", "🔥", "🌊", "🍄", "🌍", "🌱",
        ),
    ),
    EmojiCategory(
        "food",
        "🍓",
        (
            "🍎", "🍓", "🍉", "🍌", "🍇", "🍒",
            "🥕", "🌽", "🍕", "🍔", "🍟", "🍪",
            "🍩", "🍦", "🧁", "🎂", "🍿", "🥛",
        ),
    ),
    EmojiCategory(
        "play",
        "🎨",
        (
            "⚽", "🏀", "🎾", "🛝", "🧩", "🎲",
            "🎨", "🎵", "🎸", "🥁", "📚", "✏️",
            "🔭", "🔬", "🧪", "🪁", "🎈", "🎁",
        ),
    ),
    EmojiCategory(
        "adventure",
        "🚀",
        (
            "🚗", "🚲", "🚂", "✈️", "🚀", "⛵",
            "🏠", "🏰", "⛺", "🗺️", "🧭", "🏔️",
            "🏖️", "🌋", "🛸", "🤖", "👩‍🔬", "👨‍🚀",
        ),
    ),
    EmojiCategory(
        "symbols",
        "❤️",
        (
            "❤️", "🧡", "💛", "💚", "💙", "💜",
            "💖", "💕", "👍", "👏", "🙌", "🤝",
            "✅", "❌", "❓", "❗", "💡", "🏆",
        ),
    ),
)


class EmojiPalette:
    """Bounded, renderer-neutral selection model for the Greia emoji sheet."""

    def __init__(self, categories: tuple[EmojiCategory, ...] = DEFAULT_EMOJI_CATEGORIES) -> None:
        if not categories:
            raise ValueError("emoji palette must contain at least one category")
        if len(categories) > 12:
            raise ValueError("emoji palette category count exceeds Greia bound")
        ids = [category.category_id for category in categories]
        if len(ids) != len(set(ids)):
            raise ValueError("emoji palette category ids must be unique")
        self.categories = tuple(categories)
        self._selected = 0

    @property
    def selected_index(self) -> int:
        return self._selected

    @property
    def selected(self) -> EmojiCategory:
        return self.categories[self._selected]

    def select(self, index: int) -> EmojiCategory:
        if not 0 <= int(index) < len(self.categories):
            raise IndexError("emoji category index out of range")
        self._selected = int(index)
        return self.selected

    def select_id(self, category_id: str) -> EmojiCategory:
        for index, category in enumerate(self.categories):
            if category.category_id == category_id:
                return self.select(index)
        raise KeyError(category_id)
