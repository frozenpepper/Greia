"""Cozy blankets and cloud friend definitions for Nanna delle Nuvolette."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class Blanket:
    blanket_id: str
    primary_color: tuple[int, int, int]
    accent_color: tuple[int, int, int]
    name_key: str
    symbol: str

    @property
    def bg_color(self) -> tuple[int, int, int]:
        return self.primary_color

    @property
    def border_color(self) -> tuple[int, int, int]:
        return self.accent_color


BlanketPattern = Blanket

BLANKETS: Final[tuple[Blanket, ...]] = (
    Blanket("rose", (244, 114, 182), (219, 39, 119), "blanket.rose", "💖"),
    Blanket("amber", (253, 224, 71), (202, 138, 4), "blanket.amber", "☀️"),
    Blanket("mint", (134, 239, 172), (22, 163, 74), "blanket.mint", "🍃"),
    Blanket("sky", (125, 211, 252), (2, 132, 199), "blanket.sky", "🌊"),
    Blanket("lavender", (216, 180, 254), (147, 51, 234), "blanket.lavender", "⭐"),
    Blanket("peach", (253, 186, 116), (234, 88, 12), "blanket.peach", "🌸"),
)

BLANKET_PATTERNS = BLANKETS
BLANKETS_BY_ID: Final[dict[str, Blanket]] = {b.blanket_id: b for b in BLANKETS}
VALID_BLANKET_IDS: Final[frozenset[str]] = frozenset(BLANKETS_BY_ID.keys())
