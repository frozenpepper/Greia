"""Pure content for Teatrino delle Fiabe (no pygame imports).

Everything the theatre shows is described here as data: the puppet troupe
(canonical cast puppets drawn from the shared ``character.<id>`` variants,
shared-library animals, and this package's own fairy-tale puppets), the
scenes (shared-library biome layers), the six sound "stickers" and the
storage bounds. Rendering and behaviour live elsewhere; ids here are stable
because saved shows store them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600

# -- storage / recording bounds -------------------------------------------------
MAX_RECORDING_SECONDS: Final = 45.0
MAX_SAVED_SHOWS: Final = 16
SHOWS_INDEX_KEY: Final = "teatrino.shows.index.v1"
# STORAGE_KEY alias for app wiring; canonical key is SHOWS_INDEX_KEY.
STORAGE_KEY: Final = SHOWS_INDEX_KEY
# Frames are sampled at this rate and interpolated on playback (45 s -> 675).
RECORD_HZ: Final = 15
MAX_FRAMES: Final = int(MAX_RECORDING_SECONDS * RECORD_HZ) + 2
MAX_SFX_EVENTS: Final = 240
# Only a few friends fit on the little stage at once.
MAX_ON_STAGE: Final = 6
# The private file a poster is written to before it is published to My
# Creations (overwritten each time, so it never accumulates).
POSTER_FILE: Final = "poster_share.png"
POSTER_ROLE: Final = "picture"

HOST: Final = "lilli"  # the theatre's host friend (celebrations, hints)


class ArtSource:
    """Where a puppet's pictures come from."""

    CAST = "cast"  # shared character.<id> variants (on-model, never redrawn)
    LIBRARY = "library"  # a shared prop/creature picture
    PRIVATE = "private"  # this package's assets/runtime/puppet_<id>.png


@dataclass(frozen=True, slots=True)
class PuppetSpec:
    """One puppet in the tray.

    ``talk``/``cheer``/``wave``/``bow`` name the shared variants used for the
    mouth-flap, jump, held and bow moments; ``None`` means the puppet has a
    single picture and those moments are pure motion (bob, hop, tilt).
    ``mirror`` is False for the canonical cast: front-facing friends are never
    mirrored (Leo's glasses and Flash's bolt must keep reading correctly).
    """

    puppet_id: str
    source: str
    asset_id: str | None = None
    talk: str | None = None
    cheer: str | None = None
    wave: str | None = None
    bow: str | None = None
    mirror: bool = True
    # Uniform scale tweak so library animals read as big as the cast.
    scale: float = 1.0


def _cast(puppet_id: str) -> PuppetSpec:
    return PuppetSpec(
        puppet_id,
        ArtSource.CAST,
        f"character.{puppet_id}",
        talk="surprised",
        cheer="pose_cheer",
        wave="pose_wave",
        bow="happy",
        mirror=False,
    )


def _private(puppet_id: str) -> PuppetSpec:
    return PuppetSpec(puppet_id, ArtSource.PRIVATE)


PUPPETS: Final[tuple[PuppetSpec, ...]] = (
    # Tray page 1: the canonical Greia friends.
    _cast("lilli"),
    _cast("leo"),
    _cast("flash"),
    _cast("dani"),
    _cast("tito"),
    _cast("momo"),
    # Tray page 2: the fairy-tale troupe (package art, cast grammar).
    _private("principessa"),
    _private("cavaliere"),
    _private("re"),
    _private("fatina"),
    _private("mago"),
    _private("draghetto"),
    # Tray page 3: story animals from the shared library + two more friends.
    PuppetSpec("lupetto", ArtSource.LIBRARY, "prop.vocab.wolf", scale=1.0),
    PuppetSpec("maialino", ArtSource.LIBRARY, "prop.vocab.pig", scale=0.9),
    PuppetSpec("ranocchio", ArtSource.LIBRARY, "creature.woodland.frog", scale=0.82),
    PuppetSpec("orsetto", ArtSource.LIBRARY, "creature.woodland.bear", scale=0.88),
    _private("sirenetta"),
    _private("bebe"),
)
PUPPETS_BY_ID: Final[dict[str, PuppetSpec]] = {spec.puppet_id: spec for spec in PUPPETS}
PUPPET_IDS: Final[tuple[str, ...]] = tuple(spec.puppet_id for spec in PUPPETS)
PRIVATE_PUPPETS: Final[tuple[str, ...]] = tuple(
    spec.puppet_id for spec in PUPPETS if spec.source == ArtSource.PRIVATE
)
TRAY_PAGE_SIZE: Final = 6
TRAY_PAGES: Final = (len(PUPPETS) + TRAY_PAGE_SIZE - 1) // TRAY_PAGE_SIZE
# The two puppets on stage the first time the theatre opens.
OPENING_CAST: Final[tuple[str, ...]] = ("lilli", "draghetto")


@dataclass(frozen=True, slots=True)
class SceneProp:
    """One shared-library picture standing in a scene (base centre, size)."""

    asset_id: str
    size: int
    midbottom: tuple[int, int]


@dataclass(frozen=True, slots=True)
class SceneSpec:
    """A stage backdrop composed from shared 1024x600 scene layers."""

    scene_id: str
    layers: tuple[str, ...]
    props: tuple[SceneProp, ...] = ()
    # Ambient tint behind the layers (only visible if a layer is missing).
    base: tuple[int, int, int] = (207, 234, 247)


SCENES: Final[tuple[SceneSpec, ...]] = (
    SceneSpec(
        "cottage",
        tuple(f"bg.meadow_day.{name}" for name in ("sky", "far", "mid", "ground", "foreground")),
        (SceneProp("prop.vocab.house", 250, (512, 420)),),
    ),
    SceneSpec("castle", ("bg.wallpaper.castle",)),
    SceneSpec(
        "forest",
        tuple(f"bg.woodland_pond.{name}" for name in ("sky", "far", "mid", "ground", "foreground")),
    ),
    SceneSpec(
        "ocean",
        tuple(f"bg.underwater.{name}" for name in ("water", "far", "mid", "ground", "foreground")),
        base=(120, 190, 210),
    ),
    SceneSpec("sky", ("bg.wallpaper.rainbow",)),
    SceneSpec(
        "night",
        tuple(f"bg.night_sky.{name}" for name in ("sky", "stars", "far", "mid", "ground")),
        base=(37, 59, 89),
    ),
)
SCENES_BY_ID: Final[dict[str, SceneSpec]] = {scene.scene_id: scene for scene in SCENES}
SCENE_IDS: Final[tuple[str, ...]] = tuple(scene.scene_id for scene in SCENES)
DEFAULT_SCENE: Final = "cottage"

# Shared stage layers: the floor sits behind the puppets, the curtains and the
# valance in front of them.
STAGE_FLOOR: Final = "bg.stage.boards"
STAGE_FRONT: Final[tuple[str, ...]] = ("bg.stage.curtain_left", "bg.stage.curtain_right", "bg.stage.valance")


@dataclass(frozen=True, slots=True)
class FxSpec:
    """A sound sticker: its button picture, the puppets' reaction and the burst.

    ``sound`` is the synthesized cue id (also stored in saved shows),
    ``reaction`` the cast variant every cast puppet shows for a moment.
    """

    sound: str
    picture: str
    picture_variant: str
    reaction: str
    burst: str


FX: Final[tuple[FxSpec, ...]] = (
    FxSpec("trumpet", "prop.instrument.trumpet", "default", "pose_play", "note_burst"),
    FxSpec("magic", "fx.sparkle", "default", "happy", "sparkle"),
    FxSpec("applause", "fx.firework", "default", "pose_cheer", "confetti"),
    FxSpec("giggle", "character.momo", "silly", "silly", "heart_pop"),
    FxSpec("mystery", "prop.vocab.moon", "default", "surprised", "shooting_star"),
    FxSpec("boing", "prop.everyday.ball", "default", "pose_cheer", "star_burst"),
)
FX_BY_SOUND: Final[dict[str, FxSpec]] = {spec.sound: spec for spec in FX}

# Pre-reader host voice: owner-approved shared character takes only.
VOICE_READY: Final = "ready.go"  # "Come on, let's go!" before the curtain opens
VOICE_SAVED: Final = "celebrate.success"  # "Hooray!" at the curtain call
VOICE_WATCHED: Final = "praise.general"  # after watching a show to the end

__all__ = [
    "ArtSource",
    "DEFAULT_SCENE",
    "FX",
    "FX_BY_SOUND",
    "FxSpec",
    "HOST",
    "MAX_FRAMES",
    "MAX_ON_STAGE",
    "MAX_RECORDING_SECONDS",
    "MAX_SAVED_SHOWS",
    "MAX_SFX_EVENTS",
    "OPENING_CAST",
    "POSTER_FILE",
    "POSTER_ROLE",
    "PRIVATE_PUPPETS",
    "PUPPETS",
    "PUPPETS_BY_ID",
    "PUPPET_IDS",
    "PuppetSpec",
    "RECORD_HZ",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SCENES",
    "SCENES_BY_ID",
    "SCENE_IDS",
    "STAGE_FLOOR",
    "STAGE_FRONT",
    "SHOWS_INDEX_KEY",
    "STORAGE_KEY",
    "SceneProp",
    "SceneSpec",
    "TRAY_PAGES",
    "TRAY_PAGE_SIZE",
    "VOICE_READY",
    "VOICE_SAVED",
    "VOICE_WATCHED",
]
