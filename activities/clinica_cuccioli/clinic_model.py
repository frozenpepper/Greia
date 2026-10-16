"""Gameplay rules for one Little Vet Clinic day (no Pygame, no IO).

A clinic day is a fixed queue of patients. Each patient goes through:

``ARRIVING`` -> ``FIND`` (the child looks and taps where it hurts) ->
``CARE`` (the child uses the tray tools in the ailment's fixed order) ->
``HEALED`` (the happy patient goes home) -> next patient ... -> ``DONE``.

The model owns truth (what is wrong, which step is next, mistakes) but
never chooses for the child: every find and every care step is an explicit
child action, and a wrong choice changes nothing but the mistake count.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import random

if __package__:
    from .clinic_content import (
        AILMENTS,
        MAX_LEVEL,
        MIN_LEVEL,
        PATIENTS_PER_DAY,
        SPECIES,
        Ailment,
        AilmentId,
        BodyPart,
        PatientLook,
        Species,
        Tool,
        level_spec,
        patient_look,
    )
else:
    from clinic_content import (
        AILMENTS,
        MAX_LEVEL,
        MIN_LEVEL,
        PATIENTS_PER_DAY,
        SPECIES,
        Ailment,
        AilmentId,
        BodyPart,
        PatientLook,
        Species,
        Tool,
        level_spec,
        patient_look,
    )

LEVEL_UP_MAX_MISTAKES = 2
LEVEL_DOWN_MIN_MISTAKES = 7


class Phase(StrEnum):
    ARRIVING = "arriving"
    FIND = "find"
    CARE = "care"
    HEALED = "healed"
    DONE = "done"


@dataclass(frozen=True, slots=True)
class PatientCase:
    """One visitor: which creature and what is wrong with it."""

    species_id: str
    ailment_id: AilmentId

    @property
    def species(self) -> Species:
        return SPECIES[self.species_id]

    @property
    def ailment(self) -> Ailment:
        return AILMENTS[self.ailment_id]


@dataclass(frozen=True, slots=True)
class FindResult:
    part: BodyPart
    correct: bool


@dataclass(frozen=True, slots=True)
class CareResult:
    """Outcome of one tool use; ``step_index`` is the step it was tried for."""

    tool: Tool
    correct: bool
    step_index: int
    healed: bool
    case: PatientCase


class ClinicDayFactory:
    """Build a varied, fair patient queue for one level (seedable)."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def build(self, level: int) -> tuple[PatientCase, ...]:
        spec = level_spec(level)
        pool = list(spec.ailments)
        # Every ailment of the level appears at least once, then random fill.
        ailments = pool[:]
        self._rng.shuffle(ailments)
        while len(ailments) < PATIENTS_PER_DAY:
            ailments.append(self._rng.choice(pool))
        ailments = self._spread(ailments[:PATIENTS_PER_DAY])
        cases: list[PatientCase] = []
        used: dict[str, int] = {}
        previous_species: str | None = None
        for ailment_id in ailments:
            ailment = AILMENTS[ailment_id]
            eligible = [
                species.species_id
                for species in SPECIES.values()
                if species.min_level <= spec.level and (species.mood_variants or not ailment.pets_only)
            ]
            fresh = [
                species_id
                for species_id in eligible
                if species_id != previous_species and PatientCase(species_id, ailment_id) not in cases
            ]
            # Relax "never the same visitor twice" before "never twice in a row".
            candidates = fresh or [s for s in eligible if s != previous_species] or eligible
            # Prefer creatures seen least today so a day feels like a queue of
            # different visitors; ties are broken by the seeded RNG.
            fewest = min(used.get(species_id, 0) for species_id in candidates)
            species_id = self._rng.choice(sorted(c for c in candidates if used.get(c, 0) == fewest))
            cases.append(PatientCase(species_id, ailment_id))
            used[species_id] = used.get(species_id, 0) + 1
            previous_species = species_id
        return tuple(cases)

    def _spread(self, ailments: list[AilmentId]) -> list[AilmentId]:
        """Avoid the same ailment twice in a row when the pool allows it."""

        result: list[AilmentId] = []
        remaining = ailments[:]
        while remaining:
            # Greedy: the most frequent remaining ailment that differs from the
            # last one, so duplicates are spaced out instead of left to the end.
            options = [a for a in remaining if not result or a != result[-1]] or remaining
            pick = max(options, key=remaining.count)
            remaining.remove(pick)
            result.append(pick)
        return result

    def tray(self, level: int) -> tuple[Tool, ...]:
        """Tool order for the next patient (shuffled only at the top level)."""

        spec = level_spec(level)
        tools = list(spec.tools)
        if spec.shuffle_tray:
            self._rng.shuffle(tools)
        return tuple(tools)


@dataclass(slots=True)
class ClinicDay:
    """Mutable state of one clinic day."""

    cases: tuple[PatientCase, ...]
    level: int = MIN_LEVEL
    index: int = 0
    phase: Phase = Phase.ARRIVING
    steps_done: int = 0
    patient_mistakes: int = 0
    mistakes: int = 0
    healed_count: int = 0
    _completion_reported: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        if not self.cases:
            raise ValueError("a clinic day needs at least one patient")
        self.level = max(MIN_LEVEL, min(MAX_LEVEL, int(self.level)))

    # -- queries -----------------------------------------------------------

    @property
    def case(self) -> PatientCase:
        return self.cases[min(self.index, len(self.cases) - 1)]

    @property
    def expected_tool(self) -> Tool | None:
        if self.phase is not Phase.CARE:
            return None
        steps = self.case.ailment.steps
        return steps[self.steps_done] if self.steps_done < len(steps) else None

    @property
    def look(self) -> PatientLook:
        case = self.case
        return patient_look(case.species, case.ailment, self.steps_done, healed=self.phase in {Phase.HEALED, Phase.DONE})

    @property
    def is_last_patient(self) -> bool:
        return self.index >= len(self.cases) - 1

    # -- child actions -------------------------------------------------------

    def arrived(self) -> None:
        if self.phase is Phase.ARRIVING:
            self.phase = Phase.FIND

    def find(self, part: BodyPart) -> FindResult | None:
        """The child points at a body part. ``None`` outside the find step."""

        if self.phase is not Phase.FIND:
            return None
        target = self.case.ailment.part
        correct = target is BodyPart.FUR or part is target
        if correct:
            self.phase = Phase.CARE
        else:
            self._mistake()
        return FindResult(part, correct)

    def use_tool(self, tool: Tool) -> CareResult | None:
        """The child uses one tray tool on the patient. ``None`` when not caring."""

        if self.phase is not Phase.CARE:
            return None
        step = self.steps_done
        expected = self.expected_tool
        if tool is not expected:
            self._mistake()
            return CareResult(tool, False, step, False, self.case)
        self.steps_done += 1
        healed = self.steps_done >= len(self.case.ailment.steps)
        if healed:
            self.phase = Phase.HEALED
            self.healed_count += 1
        return CareResult(tool, True, step, healed, self.case)

    def next_patient(self) -> bool:
        """Move on after a patient went home; False when the day is over."""

        if self.phase is not Phase.HEALED:
            return False
        if self.is_last_patient:
            self.phase = Phase.DONE
            return False
        self.index += 1
        self.phase = Phase.ARRIVING
        self.steps_done = 0
        self.patient_mistakes = 0
        return True

    def consume_completion(self) -> dict[str, object] | None:
        """One-shot day summary for events/adaptation (None until DONE)."""

        if self.phase is not Phase.DONE or self._completion_reported:
            return None
        self._completion_reported = True
        return {
            "level": self.level,
            "patients": self.healed_count,
            "mistakes": self.mistakes,
        }

    def _mistake(self) -> None:
        self.patient_mistakes += 1
        self.mistakes += 1


def adapt_level(level: int, mistakes: int) -> int:
    """Next day's level: up after a calm day, down after a hard one."""

    if mistakes <= LEVEL_UP_MAX_MISTAKES:
        level += 1
    elif mistakes >= LEVEL_DOWN_MIN_MISTAKES:
        level -= 1
    return max(MIN_LEVEL, min(MAX_LEVEL, level))


__all__ = [
    "CareResult",
    "ClinicDay",
    "ClinicDayFactory",
    "FindResult",
    "LEVEL_DOWN_MIN_MISTAKES",
    "LEVEL_UP_MAX_MISTAKES",
    "PatientCase",
    "Phase",
    "adapt_level",
]
