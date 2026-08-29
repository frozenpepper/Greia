from __future__ import annotations

from pathlib import Path
import sys
import tomllib
import unittest
from unittest.mock import patch

import pygame


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "clinica_cuccioli"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from clinic_app import ClinicActivity  # noqa: E402
from clinic_model import ClinicSession, TreatmentResult  # noqa: E402
from clinic_renderer import (  # noqa: E402
    ClinicRenderer,
    PLAY_AGAIN_RECT,
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
)
from clinic_services import GreiaClinicEvents  # noqa: E402


class FixedRandom:
    """Predictable two-step prescription source for provider-free tests."""

    def choice(self, seq):
        return 2

    def sample(self, population, k):
        return list(population[:k])


class ClinicSessionTests(unittest.TestCase):
    def test_each_treatment_requires_an_explicit_tool_choice(self) -> None:
        session = ClinicSession(rng=FixedRandom())
        self.assertEqual(session.required_steps, ["stethoscope", "bath"])
        self.assertIsNone(session.selected_tool_id)
        self.assertIsNone(session.use_selected_tool())

        session.select_tool("bath")
        wrong = session.use_selected_tool()
        self.assertIsNotNone(wrong)
        assert wrong is not None
        self.assertFalse(wrong.applied)
        self.assertEqual(session.completed_steps, [])
        self.assertEqual(session.selected_tool_id, "bath")

        session.select_tool("stethoscope")
        first = session.use_selected_tool()
        self.assertIsNotNone(first)
        assert first is not None
        self.assertTrue(first.applied)
        self.assertFalse(first.patient_healed)
        self.assertEqual(session.next_needed, "bath")
        self.assertIsNone(session.selected_tool_id)

        # Touching the animal again cannot silently apply the next correct answer.
        self.assertIsNone(session.use_selected_tool())
        self.assertEqual(session.completed_steps, ["stethoscope"])

        session.select_tool("bath")
        second = session.use_selected_tool()
        self.assertIsNotNone(second)
        assert second is not None
        self.assertTrue(second.applied)
        self.assertTrue(second.patient_healed)
        self.assertEqual(second.patient_id, "dog")
        self.assertEqual(session.total_stars, 1)
        self.assertEqual(session.patient_id, "cat")
        self.assertIsNone(session.selected_tool_id)

    def test_five_healed_patients_finish_session_and_restart_keeps_stars(self) -> None:
        session = ClinicSession(total_stars=3, rng=FixedRandom())
        healed = []
        while not session.is_victory:
            needed = session.next_needed
            self.assertIsNotNone(needed)
            assert needed is not None
            result = session.use_tool(needed)
            if result.patient_healed:
                healed.append(result.patient_id)

        self.assertEqual(healed, ["dog", "cat", "bunny", "bear", "dog"])
        self.assertEqual(session.total_stars, 8)
        self.assertEqual(session.patient_id, "dog")
        self.assertTrue(session.is_victory)
        self.assertIsNone(session.selected_tool_id)

        session.restart()
        self.assertFalse(session.is_victory)
        self.assertEqual(session.patient_index, 0)
        self.assertEqual(session.total_stars, 8)
        self.assertEqual(session.patient_id, "dog")
        self.assertIsNone(session.selected_tool_id)


class _IdentityCanvas:
    def pointer(self, position):
        return position


class _InteractionRenderer:
    TOOL_POINT = (100, 100)
    PATIENT_POINT = (200, 200)

    def __init__(self) -> None:
        self.celebrations: list[tuple[str, tuple[int, int]]] = []

    def tool_at(self, point):
        return "stethoscope" if point == self.TOOL_POINT else (
            "bath" if point == (110, 100) else None
        )

    def patient_contains(self, point):
        return point == self.PATIENT_POINT

    def play_again_contains(self, point):
        return False

    def celebrate(self, tool_id, origin):
        self.celebrations.append((tool_id, origin))

    def reset_transients(self):
        pass


class _AudioRecorder:
    def __init__(self) -> None:
        self.played: list[str] = []

    def play(self, name: str) -> None:
        self.played.append(name)


class _ProgressRecorder:
    def __init__(self) -> None:
        self.saved: list[int] = []

    def load_stars(self) -> int:
        return 0

    def save_stars(self, stars: int) -> None:
        self.saved.append(stars)


class _EventRecorder:
    def __init__(self) -> None:
        self.treatments: list[TreatmentResult] = []
        self.healed: list[TreatmentResult] = []

    def treatment_applied(self, result: TreatmentResult) -> None:
        self.treatments.append(result)

    def patient_healed(self, result: TreatmentResult) -> None:
        self.healed.append(result)


class ClinicInteractionTests(unittest.TestCase):
    def test_palette_selects_and_patient_applies_without_auto_answer(self) -> None:
        session = ClinicSession(rng=FixedRandom())
        renderer = _InteractionRenderer()
        audio = _AudioRecorder()
        progress = _ProgressRecorder()
        events = _EventRecorder()
        app = ClinicActivity(
            screen=object(),
            canvas=_IdentityCanvas(),
            session=session,
            renderer=renderer,
            audio=audio,
            progress=progress,
            events=events,
        )

        # The real Greia Home/Back path is no longer owned by the
        # Activity; is_home_clicked is gone from clinic_app. The
        # protected-region gate _is_safe_point is the only pointer
        # filter remaining under the Activity's control.
        with patch("clinic_app._is_safe_point", return_value=True):
            self.assertFalse(app._handle_pointer(renderer.PATIENT_POINT))
            self.assertEqual(session.completed_steps, [])

            self.assertTrue(app._handle_pointer(renderer.TOOL_POINT))
            self.assertEqual(session.selected_tool_id, "stethoscope")
            self.assertEqual(session.completed_steps, [])
            self.assertEqual(audio.played, [])

            self.assertTrue(app._handle_pointer(renderer.PATIENT_POINT))
            self.assertEqual(session.completed_steps, ["stethoscope"])
            self.assertIsNone(session.selected_tool_id)
            self.assertEqual(audio.played, ["stethoscope"])
            self.assertEqual(len(events.treatments), 1)

            # A second animal click cannot consume the automatically known next step.
            self.assertFalse(app._handle_pointer(renderer.PATIENT_POINT))
            self.assertEqual(session.completed_steps, ["stethoscope"])

            self.assertTrue(app._handle_pointer((110, 100)))
            self.assertEqual(session.selected_tool_id, "bath")
            self.assertTrue(app._handle_pointer(renderer.PATIENT_POINT))
            self.assertEqual(len(events.healed), 1)
            self.assertEqual(progress.saved, [1])
            self.assertIsNone(session.selected_tool_id)


class _StubResources:
    def text(self, key: str) -> str:
        return key


class _StubTypography:
    def render(self, text, role, size, color):
        width = max(1, len(str(text)) * max(4, int(size) // 2))
        return pygame.Surface((width, max(1, int(size) + 4)))


class ClinicVictoryRendererTests(unittest.TestCase):
    def test_terminal_state_renders_repeatedly_without_active_treatment_state(self) -> None:
        session = ClinicSession(rng=FixedRandom())
        while not session.is_victory:
            needed = session.next_needed
            self.assertIsNotNone(needed)
            assert needed is not None
            session.use_tool(needed)

        renderer = ClinicRenderer(_StubTypography(), _StubResources())
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))

        # Render twice to cover both the transition and a later invalidation such as resize.
        renderer.render(surface, session, 0.0)
        renderer.render(surface, session, 1.0)

        self.assertTrue(renderer.play_again_contains(PLAY_AGAIN_RECT.center))


class ClinicEventContractTests(unittest.TestCase):
    def test_event_adapter_publishes_only_manifest_declared_ids(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        declared = {event["id"] for event in manifest["education"]["events"]}
        result = TreatmentResult(
            tool_id="bath",
            patient_id="cat",
            applied=True,
            patient_healed=True,
            session_complete=False,
            total_stars=4,
        )

        with patch("clinic_services.emit_activity_event") as emit:
            events = GreiaClinicEvents()
            events.treatment_applied(result)
            events.patient_healed(result)

        emitted = [call.args[0] for call in emit.call_args_list]
        self.assertEqual(emitted, ["vet.treatment_applied", "vet.patient_healed"])
        self.assertTrue(set(emitted).issubset(declared))
        self.assertNotIn("clinic.patient_cured", emitted)


if __name__ == "__main__":
    unittest.main()
