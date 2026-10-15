"""Pure content and bounds for Leo's Post (no pygame imports).

Leo's Post is one experience: make a *picture* postcard for a cast friend and
send it. Every picture is shared-library art resolved by semantic ID:

* friends — the six canonical cast characters (``character.<id>``); the
  historical non-cast placeholder ``pina`` migrates to ``flash``;
* card fronts — the eight shared wallpapers (``bg.wallpaper.*``) or a picture
  the child brings from My Creations;
* stickers — shared props and creatures;
* stamps — shared props, one per friend ("each friend has their own stamp"),
  drawn in the stamp box on the back of the card.

Child-authored message text is never part of this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600

# A postcard is 1.7:1, the same shape as the shared wallpapers (1024x600).
CARD_ASPECT: Final = 1.7
# Stored size of an imported card-front picture and of the shared PNG.
CARD_PICTURE_SIZE: Final[tuple[int, int]] = (680, 400)

MAX_GRAPHEMES: Final = 80
MAX_SAVED_CARDS: Final = 20
MAX_STICKERS: Final = 8
POSTBOX_PAGE_SIZE: Final = 6
# Sticker edge length as a fraction of the card height.
STICKER_SCALE: Final = 0.27


@dataclass(frozen=True, slots=True)
class Friend:
    """One canonical cast friend a postcard can be sent to."""

    friend_id: str
    name_key: str
    stamp_id: str

    @property
    def asset_id(self) -> str:
        return f"character.{self.friend_id}"


@dataclass(frozen=True, slots=True)
class Scene:
    """One shared-library card front."""

    scene_id: str
    asset_id: str


@dataclass(frozen=True, slots=True)
class Sticker:
    sticker_id: str
    asset_id: str


@dataclass(frozen=True, slots=True)
class Stamp:
    stamp_id: str
    asset_id: str


FRIENDS: Final[tuple[Friend, ...]] = (
    Friend("leo", "friend.leo", "star"),
    Friend("lilli", "friend.lilli", "rainbow"),
    Friend("momo", "friend.momo", "heart"),
    Friend("dani", "friend.dani", "sun"),
    Friend("tito", "friend.tito", "flower"),
    Friend("flash", "friend.flash", "butterfly"),
)
# Backwards-compatible alias (older tests/tools import RECIPIENTS).
RECIPIENTS: Final = FRIENDS
# ``pina`` was a placeholder that never existed in the cast library.
LEGACY_RECIPIENTS: Final[dict[str, str]] = {"pina": "flash"}

SCENES: Final[tuple[Scene, ...]] = tuple(
    Scene(scene_id, f"bg.wallpaper.{scene_id}")
    for scene_id in ("meadow", "ocean", "forest", "castle", "rainbow", "space", "snow", "candy")
)

STICKERS: Final[tuple[Sticker, ...]] = (
    Sticker("heart", "prop.shape.heart"),
    Sticker("star", "prop.vocab.star"),
    Sticker("flower", "prop.nature.flower"),
    Sticker("sun", "prop.nature.sun"),
    Sticker("rainbow", "prop.nature.rainbow"),
    Sticker("butterfly", "creature.woodland.butterfly"),
    Sticker("puppy", "creature.pet.puppy"),
    Sticker("kitten", "creature.pet.kitten"),
    Sticker("cake", "prop.vocab.cake"),
    Sticker("crown", "prop.vocab.crown"),
)

STAMPS: Final[tuple[Stamp, ...]] = (
    Stamp("heart", "prop.shape.heart"),
    Stamp("sun", "prop.nature.sun"),
    Stamp("star", "prop.shape.star"),
    Stamp("rainbow", "prop.nature.rainbow"),
    Stamp("flower", "prop.nature.flower"),
    Stamp("butterfly", "creature.woodland.butterfly"),
)
# Version-1 postcards had no picture: they get the front that matches their
# stamp, so an old card still looks like a postcard (its text is unchanged).
LEGACY_STAMP_SCENES: Final[dict[str, str]] = {
    "heart": "candy",
    "sun": "meadow",
    "star": "space",
    "rainbow": "rainbow",
    "flower": "forest",
    "butterfly": "meadow",
}

# Where new stickers land (normalised card coordinates), so keyboard and
# controller players get a pleasant layout without dragging.
STICKER_SPOTS: Final[tuple[tuple[float, float], ...]] = (
    (0.22, 0.70),
    (0.78, 0.30),
    (0.50, 0.55),
    (0.80, 0.74),
    (0.22, 0.30),
    (0.50, 0.24),
    (0.64, 0.80),
    (0.36, 0.80),
)

# One row of quick picture-words for pre-readers (typing stays optional).
MESSAGE_EMOJI: Final[tuple[str, ...]] = ("❤️", "😊", "🥰", "⭐", "🌈", "🎈", "🐶", "🌸")

# Roles accepted from My Creations.
FRONT_PICTURE_ROLES: Final[tuple[str, ...]] = ("drawing", "composition", "picture", "postcard")
MESSAGE_TEXT_ROLES: Final[tuple[str, ...]] = ("document", "postcard")
SHARE_ROLE: Final = "postcard"

# Shared character reaction clips (owner-approved, selected language ->
# English -> silence). "Wonderful!" / "Hooray!" fit receiving a postcard.
FRIEND_REACTION_CUE: Final = "celebrate.success"
FRIEND_REACTION_VARIANTS: Final[tuple[int, ...]] = (3, 2)
HOST: Final = "leo"

VALID_RECIPIENT_IDS: Final[frozenset[str]] = frozenset(f.friend_id for f in FRIENDS)
VALID_STAMP_IDS: Final[frozenset[str]] = frozenset(s.stamp_id for s in STAMPS)
VALID_SCENE_IDS: Final[frozenset[str]] = frozenset(s.scene_id for s in SCENES)
VALID_STICKER_IDS: Final[frozenset[str]] = frozenset(s.sticker_id for s in STICKERS)

_FRIENDS_BY_ID: Final = {friend.friend_id: friend for friend in FRIENDS}
_SCENES_BY_ID: Final = {scene.scene_id: scene for scene in SCENES}
_STICKERS_BY_ID: Final = {sticker.sticker_id: sticker for sticker in STICKERS}
_STAMPS_BY_ID: Final = {stamp.stamp_id: stamp for stamp in STAMPS}


def friend(friend_id: str) -> Friend:
    return _FRIENDS_BY_ID[friend_id]


def scene(scene_id: str) -> Scene:
    return _SCENES_BY_ID[scene_id]


def sticker(sticker_id: str) -> Sticker:
    return _STICKERS_BY_ID[sticker_id]


def stamp(stamp_id: str) -> Stamp:
    return _STAMPS_BY_ID[stamp_id]


def canonical_recipient(recipient_id: object) -> str | None:
    """Return the canonical friend id for a stored recipient, or ``None``."""

    if not isinstance(recipient_id, str):
        return None
    recipient_id = LEGACY_RECIPIENTS.get(recipient_id, recipient_id)
    return recipient_id if recipient_id in VALID_RECIPIENT_IDS else None


__all__ = [
    "CARD_ASPECT",
    "CARD_PICTURE_SIZE",
    "FRIENDS",
    "FRIEND_REACTION_CUE",
    "FRIEND_REACTION_VARIANTS",
    "FRONT_PICTURE_ROLES",
    "Friend",
    "HOST",
    "LEGACY_RECIPIENTS",
    "LEGACY_STAMP_SCENES",
    "MAX_GRAPHEMES",
    "MAX_SAVED_CARDS",
    "MAX_STICKERS",
    "MESSAGE_EMOJI",
    "MESSAGE_TEXT_ROLES",
    "POSTBOX_PAGE_SIZE",
    "RECIPIENTS",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SCENES",
    "SHARE_ROLE",
    "STAMPS",
    "STICKERS",
    "STICKER_SCALE",
    "STICKER_SPOTS",
    "Scene",
    "Stamp",
    "Sticker",
    "VALID_RECIPIENT_IDS",
    "VALID_SCENE_IDS",
    "VALID_STAMP_IDS",
    "VALID_STICKER_IDS",
    "canonical_recipient",
    "friend",
    "scene",
    "stamp",
    "sticker",
]
