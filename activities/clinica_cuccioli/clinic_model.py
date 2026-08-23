from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Protocol, Sequence


TOOL_IDS: tuple[str, ...] = (
    "stethoscope",
    "bath",
    "bandaid",
    "food",
    "cuddle",
)
PATIENT_IDS: tuple[str, ...] = ("dog", "cat", "bunny", "bear")
PATIENTS_PER_SESSION = 5


class RandomSource(Protocol):
    """Small injectable randomness contract used by the treatment planner."""

    def choice(self, seq: Sequence[int]) -> int: ...

    def sample(self, population: Sequence[str], k: int) -> list[str]: ...


@dataclass(frozen=True, slots=True)
class TreatmentResult:
    """Result of one tool attempt, independent from rendering or platform IO."""

    tool_id: str
    patient_id: str
    applied: bool
    patient_healed: bool
    session_complete: bool
    total_stars: int


@dataclass(slots=True)
class ClinicSession:
    """Own the deterministic gameplay state for one Little Vet Clinic session.

    Rendering, audio, storage and Greia event publication deliberately live outside
    this class. The child-facing interaction is intentionally two-step: choose a
    tool, then apply it to the patient. Successful treatment clears the selection
    so every prescription step requires an explicit child choice.
    """

    total_stars: int = 0
    rng: RandomSource = field(default_factory=random.Random, repr=False)
    patient_index: int = 0
    selected_tool_id: str | None = None
    required_steps: list[str] = field(default_factory=list)
    completed_steps: list[str] = field(default_factory=list)
    is_victory: bool = False

    def __post_init__(self) -> None:
        if self.total_stars < 0:
            self.total_stars = 0
        if self.selected_tool_id is not None:
            self._require_tool(self.selected_tool_id)
        if not self.required_steps:
            self._prepare_patient()

    @property
    def patient_id(self) -> str:
        # On victory ``patient_index`` points one past the final patient. Keep the
        # patient just healed available to the terminal renderer instead of wrapping.
        index = self.patient_index - 1 if self.is_victory else self.patient_index
        return PATIENT_IDS[index % len(PATIENT_IDS)]

    @property
    def next_needed(self) -> str | None:
        return next(
            (tool_id for tool_id in self.required_steps if tool_id not in self.completed_steps),
            None,
        )

    @property
    def has_mud(self) -> bool:
        return "bath" in self.required_steps and "bath" not in self.completed_steps

    @property
    def has_scratch(self) -> bool:
        return "bandaid" in self.required_steps and "bandaid" not in self.completed_steps

    def select_tool(self, tool_id: str) -> None:
        """Select a tool without applying treatment to the patient."""

        self._require_tool(tool_id)
        if not self.is_victory:
            self.selected_tool_id = tool_id

    def use_tool(self, tool_id: str) -> TreatmentResult:
        """Apply one explicit tool attempt to the current patient.

        This method owns treatment truth but does not choose a tool for the child.
        The application normally calls :meth:`select_tool` from the palette and
        :meth:`use_selected_tool` from the patient hit target. Direct calls remain
        useful for provider-free domain tests and alternate semantic input routes.
        """

        self._require_tool(tool_id)
        patient_id = self.patient_id

        if self.is_victory or tool_id != self.next_needed:
            return TreatmentResult(
                tool_id=tool_id,
                patient_id=patient_id,
                applied=False,
                patient_healed=False,
                session_complete=self.is_victory,
                total_stars=self.total_stars,
            )

        self.completed_steps.append(tool_id)
        # Never auto-arm the next answer. The child must explicitly choose a tool
        # for each treatment step before another patient tap can make progress.
        self.selected_tool_id = None
        healed = self.next_needed is None
        session_complete = False

        if healed:
            self.total_stars += 1
            self.patient_index += 1
            session_complete = self.patient_index >= PATIENTS_PER_SESSION
            if session_complete:
                self.is_victory = True
            else:
                self._prepare_patient()

        return TreatmentResult(
            tool_id=tool_id,
            patient_id=patient_id,
            applied=True,
            patient_healed=healed,
            session_complete=session_complete,
            total_stars=self.total_stars,
        )

    def use_selected_tool(self) -> TreatmentResult | None:
        """Apply the child's current selection, or do nothing when none is armed."""

        if self.selected_tool_id is None:
            return None
        return self.use_tool(self.selected_tool_id)

    def restart(self) -> None:
        """Start a new five-patient run without discarding durable stars."""

        self.patient_index = 0
        self.is_victory = False
        self._prepare_patient()

    def _prepare_patient(self) -> None:
        # The weighted choice preserves the original 2/3/4-step difficulty mix.
        step_count = self.rng.choice((2, 2, 3, 3, 4))
        self.required_steps = self.rng.sample(TOOL_IDS, step_count)
        self.completed_steps = []
        self.selected_tool_id = None

    @staticmethod
    def _require_tool(tool_id: str) -> None:
        if tool_id not in TOOL_IDS:
            raise ValueError(f"unknown clinic tool: {tool_id}")
