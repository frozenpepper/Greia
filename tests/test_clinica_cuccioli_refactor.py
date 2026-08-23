from __future__ import annotations

from pathlib import Path
import sys
import tomllib
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "clinica_cuccioli"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from clinic_model import ClinicSession, TreatmentResult  # noqa: E402
from clinic_services import GreiaClinicEvents  # noqa: E402


class FixedRandom:
    """Predictable two-step prescription source for provider-free tests."""

    def choice(self, seq):
        return 2

    def sample(self, population, k):
        return list(population[:k])


class ClinicSessionTests(unittest.TestCase):
    def test_one_ordered_rule_applies_to_palette_and_patient_paths(self) -> None:
        session = ClinicSession(rng=FixedRandom())
        self.assertEqual(session.required_steps, ["stethoscope", "bath"])

        wrong = session.use_tool("bath")
        self.assertFalse(wrong.applied)
        self.assertEqual(session.completed_steps, [])

        first = session.use_tool("stethoscope")
        self.assertTrue(first.applied)
        self.assertFalse(first.patient_healed)
        self.assertEqual(session.next_needed, "bath")
        self.assertEqual(session.selected_tool_id, "bath")

        second = session.use_selected_tool()
        self.assertTrue(second.applied)
        self.assertTrue(second.patient_healed)
        self.assertEqual(second.patient_id, "dog")
        self.assertEqual(session.total_stars, 1)
        self.assertEqual(session.patient_id, "cat")

    def test_five_healed_patients_finish_session_and_restart_keeps_stars(self) -> None:
        session = ClinicSession(total_stars=3, rng=FixedRandom())
        healed = []
        while not session.is_victory:
            needed = session.next_needed
            self.assertIsNotNone(needed)
            result = session.use_tool(needed)
            if result.patient_healed:
                healed.append(result.patient_id)

        self.assertEqual(healed, ["dog", "cat", "bunny", "bear", "dog"])
        self.assertEqual(session.total_stars, 8)
        self.assertEqual(session.patient_id, "dog")
        self.assertTrue(session.is_victory)

        session.restart()
        self.assertFalse(session.is_victory)
        self.assertEqual(session.patient_index, 0)
        self.assertEqual(session.total_stars, 8)
        self.assertEqual(session.patient_id, "dog")


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
