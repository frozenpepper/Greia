"""Fixed clinic content for Little Vet Clinic: tools, ailments, patients.

Every ailment owns ONE care sequence that never changes, so the order is
something a child can learn and reason about ("wash, then dry, then a
cuddle"; "clean the scratch before the bandage"; "you cannot see a tummy
ache - listen first"). Every visit ends with a cuddle. Difficulty grows by
adding ailments, distractor tools and patients, never by reshuffling the
steps of an ailment.

Patients are shared library creatures (``creature.pet.*`` with mood
variants, ``creature.woodland.*``). Anchors are points on the 256 px
master sprite where a body part sits; geometry scales them to the screen.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
PATIENTS_PER_DAY: Final = 5
MIN_LEVEL: Final = 1
MAX_LEVEL: Final = 3
SPRITE_MASTER: Final = 256


class Tool(StrEnum):
    """Kit-tray tools. Values are stable save/event identifiers."""

    STETHOSCOPE = "stethoscope"
    SPONGE = "sponge"
    TOWEL = "towel"
    MEDICINE = "medicine"
    BANDAGE = "bandage"
    CUDDLE = "cuddle"


# Fixed tray order (left -> right) for levels 1-2: tools never jump around,
# so a young child can find them again. Level 3 shuffles the tray per patient.
TRAY_ORDER: Final[tuple[Tool, ...]] = (
    Tool.STETHOSCOPE,
    Tool.SPONGE,
    Tool.TOWEL,
    Tool.MEDICINE,
    Tool.BANDAGE,
    Tool.CUDDLE,
)


class BodyPart(StrEnum):
    """Where a patient can be looked at during the "where does it hurt?" step."""

    EAR = "ear"
    PAW = "paw"
    TUMMY = "tummy"
    FUR = "fur"  # the whole coat: any part of a muddy patient is right


class AilmentId(StrEnum):
    MUDDY_FUR = "muddy_fur"
    SORE_EAR = "sore_ear"
    SORE_PAW = "sore_paw"
    TUMMY_ACHE = "tummy_ache"


@dataclass(frozen=True, slots=True)
class Ailment:
    """One visible problem, where it is, and its fixed care sequence."""

    ailment_id: AilmentId
    part: BodyPart
    steps: tuple[Tool, ...]
    min_level: int
    pets_only: bool = False

    def __post_init__(self) -> None:
        if not self.steps or self.steps[-1] is not Tool.CUDDLE:
            raise ValueError("every visit ends with a cuddle")
        if len(set(self.steps)) != len(self.steps):
            raise ValueError("a care sequence never repeats a tool")


AILMENTS: Final[dict[AilmentId, Ailment]] = {
    # Wash the mud off, dry the wet fur, then a cuddle.
    AilmentId.MUDDY_FUR: Ailment(
        AilmentId.MUDDY_FUR, BodyPart.FUR, (Tool.SPONGE, Tool.TOWEL, Tool.CUDDLE), 1, pets_only=True
    ),
    # The ear was found by looking: ear drops, then a cuddle.
    AilmentId.SORE_EAR: Ailment(AilmentId.SORE_EAR, BodyPart.EAR, (Tool.MEDICINE, Tool.CUDDLE), 1),
    # Clean the scratch first, then the bandage, then a cuddle.
    AilmentId.SORE_PAW: Ailment(
        AilmentId.SORE_PAW, BodyPart.PAW, (Tool.SPONGE, Tool.BANDAGE, Tool.CUDDLE), 1, pets_only=True
    ),
    # A tummy ache cannot be seen: listen first, then medicine, then a cuddle.
    AilmentId.TUMMY_ACHE: Ailment(
        AilmentId.TUMMY_ACHE, BodyPart.TUMMY, (Tool.STETHOSCOPE, Tool.MEDICINE, Tool.CUDDLE), 2
    ),
}


@dataclass(frozen=True, slots=True)
class Species:
    """A shared-library creature plus where its body parts are on the master.

    ``mood_variants`` is False for woodland creatures, which only have the
    default (cheerful) pose; their problems are then shown by overlays only.
    """

    species_id: str
    asset_id: str
    mood_variants: bool
    ear_left: tuple[int, int]
    ear_right: tuple[int, int]
    tummy: tuple[int, int]
    mouth: tuple[int, int]
    paw: tuple[int, int]  # resting front paw (default / happy pose)
    paw_hurt: tuple[int, int]  # the paw held up in the ``hurt`` pose
    paw_happy: tuple[int, int] = (0, 0)  # front paw in the ``happy`` pose (pets)
    vocab: str | None = None  # shared spoken noun (assets/audio/vocab/v1)
    min_level: int = 1


SPECIES: Final[dict[str, Species]] = {
    "puppy": Species(
        "puppy", "creature.pet.puppy", True,
        ear_left=(56, 104), ear_right=(200, 104), tummy=(128, 168), mouth=(128, 130),
        paw=(146, 212), paw_hurt=(166, 190), paw_happy=(146, 202), vocab="dog",
    ),
    "kitten": Species(
        "kitten", "creature.pet.kitten", True,
        ear_left=(84, 58), ear_right=(176, 58), tummy=(128, 170), mouth=(128, 124),
        paw=(146, 214), paw_hurt=(166, 190), paw_happy=(148, 210), vocab="cat",
    ),
    "guinea_pig": Species(
        "guinea_pig", "creature.pet.guinea_pig", True,
        ear_left=(80, 114), ear_right=(178, 110), tummy=(118, 176), mouth=(128, 160),
        paw=(150, 214), paw_hurt=(166, 196), paw_happy=(150, 204),
    ),
    "bear": Species(
        "bear", "creature.woodland.bear", False,
        ear_left=(60, 56), ear_right=(196, 56), tummy=(128, 172), mouth=(128, 140),
        paw=(150, 214), paw_hurt=(150, 214), min_level=2,
    ),
    "mouse": Species(
        "mouse", "creature.woodland.mouse", False,
        ear_left=(56, 74), ear_right=(198, 74), tummy=(128, 184), mouth=(128, 146),
        paw=(150, 222), paw_hurt=(150, 222), vocab="mouse", min_level=2,
    ),
    "squirrel": Species(
        "squirrel", "creature.woodland.squirrel", False,
        ear_left=(72, 50), ear_right=(184, 50), tummy=(128, 186), mouth=(128, 142),
        paw=(150, 226), paw_hurt=(150, 226), min_level=2,
    ),
}


class Overlay(StrEnum):
    """Activity-drawn marks on a patient (none of them names a tool)."""

    THROB = "throb"  # "it hurts here" arcs beside a sore ear
    SWIRL = "swirl"  # tummy-ache swirl
    WET = "wet"  # water drops on just-washed fur
    BANDAGE = "bandage"  # a plaster on the treated paw


@dataclass(frozen=True, slots=True)
class PatientLook:
    """What the patient looks like now: library variant + overlays at anchors."""

    variant: str
    overlays: tuple[tuple[Overlay, tuple[int, int]], ...] = ()


def patient_look(species: Species, ailment: Ailment, steps_done: int, *, healed: bool) -> PatientLook:
    """Derive the patient's appearance from care progress alone.

    The look shows the *problem* (mud, scratch, sore ear, tummy swirl) and
    the result of care already given; it never shows which tool comes next.
    """

    done = set(ailment.steps[:steps_done])
    happy = "happy" if species.mood_variants else "default"
    if ailment.ailment_id is AilmentId.MUDDY_FUR:
        if healed:
            return PatientLook(happy)
        if Tool.SPONGE not in done:
            return PatientLook("dirty" if species.mood_variants else "default")
        if Tool.TOWEL not in done:
            return PatientLook("default", ((Overlay.WET, species.tummy),))
        return PatientLook("default")
    if ailment.ailment_id is AilmentId.SORE_PAW:
        if healed:
            return PatientLook(happy, ((Overlay.BANDAGE, species.paw_happy if species.mood_variants else species.paw),))
        variant = "hurt" if species.mood_variants else "default"
        if Tool.BANDAGE in done:
            return PatientLook(variant, ((Overlay.BANDAGE, species.paw_hurt),))
        return PatientLook(variant)
    if ailment.ailment_id is AilmentId.SORE_EAR:
        if healed:
            return PatientLook(happy)
        if Tool.MEDICINE in done:
            return PatientLook("default")
        return PatientLook("default", ((Overlay.THROB, species.ear_right),))
    # Tummy ache: the swirl stays until the medicine works.
    if healed:
        return PatientLook(happy)
    if Tool.MEDICINE in done:
        return PatientLook("default")
    return PatientLook("default", ((Overlay.SWIRL, species.tummy),))


def tool_target(species: Species, ailment: Ailment, tool: Tool, steps_done: int) -> tuple[int, int]:
    """Master-sprite point a tool flies to when it is used on the patient."""

    if tool is Tool.MEDICINE:
        return species.ear_right if ailment.part is BodyPart.EAR else species.mouth
    if tool in {Tool.STETHOSCOPE, Tool.CUDDLE}:
        return species.tummy
    if ailment.part is BodyPart.PAW:
        return species.paw_hurt
    if ailment.part is BodyPart.EAR:
        return species.ear_right
    return species.tummy


def sore_anchor(species: Species, ailment: Ailment) -> tuple[int, int]:
    """Master-sprite point of the visible problem (for "look here" glows)."""

    if ailment.part is BodyPart.EAR:
        return species.ear_right
    if ailment.part is BodyPart.PAW:
        return species.paw_hurt if species.mood_variants else species.paw
    return species.tummy


@dataclass(frozen=True, slots=True)
class LevelSpec:
    """One stage of the same clinic loop."""

    level: int
    ailments: tuple[AilmentId, ...]
    tools: tuple[Tool, ...]
    shuffle_tray: bool
    idle_hint_seconds: float


LEVELS: Final[dict[int, LevelSpec]] = {
    1: LevelSpec(
        1,
        (AilmentId.MUDDY_FUR, AilmentId.SORE_EAR, AilmentId.SORE_PAW),
        tuple(tool for tool in TRAY_ORDER if tool is not Tool.STETHOSCOPE),
        shuffle_tray=False,
        idle_hint_seconds=6.0,
    ),
    2: LevelSpec(2, tuple(AILMENTS), TRAY_ORDER, shuffle_tray=False, idle_hint_seconds=6.0),
    3: LevelSpec(3, tuple(AILMENTS), TRAY_ORDER, shuffle_tray=True, idle_hint_seconds=9.0),
}


def level_spec(level: int) -> LevelSpec:
    return LEVELS[max(MIN_LEVEL, min(MAX_LEVEL, int(level)))]


__all__ = [
    "AILMENTS",
    "Ailment",
    "AilmentId",
    "BodyPart",
    "LEVELS",
    "LevelSpec",
    "MAX_LEVEL",
    "MIN_LEVEL",
    "Overlay",
    "PATIENTS_PER_DAY",
    "PatientLook",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SPECIES",
    "SPRITE_MASTER",
    "Species",
    "TRAY_ORDER",
    "Tool",
    "level_spec",
    "patient_look",
    "sore_anchor",
    "tool_target",
]
