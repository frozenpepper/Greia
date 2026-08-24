"""Recipients and picture stamps for Posta di Leo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class Recipient:
    recipient_id: str
    name_key: str
    avatar_key: str


@dataclass(frozen=True, slots=True)
class Stamp:
    stamp_id: str
    symbol: str
    bg_color: tuple[int, int, int]
    border_color: tuple[int, int, int]


RECIPIENTS: Final[tuple[Recipient, ...]] = (
    Recipient("momo", "recipient.momo", "character.momo"),
    Recipient("dani", "recipient.dani", "character.dani"),
    Recipient("lilli", "recipient.lilli", "character.lilli"),
    Recipient("leo", "recipient.leo", "character.leo"),
    Recipient("pina", "recipient.pina", "character.pina"),
    Recipient("tito", "recipient.tito", "character.tito"),
)

STAMPS: Final[tuple[Stamp, ...]] = (
    Stamp("heart", "❤️", (254, 205, 211), (225, 29, 72)),
    Stamp("sun", "☀️", (254, 240, 138), (202, 138, 4)),
    Stamp("star", "⭐", (254, 249, 195), (234, 179, 8)),
    Stamp("rainbow", "🌈", (219, 234, 254), (37, 99, 235)),
    Stamp("flower", "🌸", (252, 231, 243), (219, 39, 119)),
    Stamp("butterfly", "🦋", (233, 213, 255), (147, 51, 234)),
)

VALID_RECIPIENT_IDS: Final[frozenset[str]] = frozenset(r.recipient_id for r in RECIPIENTS)
VALID_STAMP_IDS: Final[frozenset[str]] = frozenset(s.stamp_id for s in STAMPS)
