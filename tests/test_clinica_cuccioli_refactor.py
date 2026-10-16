"""Little Vet Clinic: fixed care sequences, no answer-revealing UI, full day.

Model, persistence, event and real-Pygame app-loop tests (dummy video).
No physical hardware, audio output or rendered acceptance is implied.
"""

from __future__ import annotations

import os
from pathlib import Path
import random
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

from clinic_content import (  # noqa: E402
    AILMENTS,
    LEVELS,
    PATIENTS_PER_DAY,
    SPECIES,
    TRAY_ORDER,
    AilmentId,
    BodyPart,
    Overlay,
    Tool,
    patient_look,
)
from clinic_model import (  # noqa: E402
    CareResult,
    ClinicDay,
    ClinicDayFactory,
    PatientCase,
    Phase,
    adapt_level,
)
from clinic_services import (  # noqa: E402
    STORAGE_KEY,
    ClinicProgressState,
    GreiaClinicEvents,
    GreiaClinicProgress,
)


def _day(*cases: tuple[str, AilmentId], level: int = 2) -> ClinicDay:
    return ClinicDay(tuple(PatientCase(species, ailment) for species, ailment in cases), level=level)


class CareSequenceTests(unittest.TestCase):
    def test_each_ailment_has_one_fixed_meaningful_sequence(self) -> None:
        self.assertEqual(AILMENTS[AilmentId.MUDDY_FUR].steps, (Tool.SPONGE, Tool.TOWEL, Tool.CUDDLE))
        self.assertEqual(AILMENTS[AilmentId.SORE_PAW].steps, (Tool.SPONGE, Tool.BANDAGE, Tool.CUDDLE))
        self.assertEqual(AILMENTS[AilmentId.SORE_EAR].steps, (Tool.MEDICINE, Tool.CUDDLE))
        self.assertEqual(AILMENTS[AilmentId.TUMMY_ACHE].steps, (Tool.STETHOSCOPE, Tool.MEDICINE, Tool.CUDDLE))
        for ailment in AILMENTS.values():
            self.assertIs(ailment.steps[-1], Tool.CUDDLE, "every visit ends with a cuddle")

    def test_sequence_is_identical_for_every_patient_and_seed(self) -> None:
        seen: dict[AilmentId, tuple[Tool, ...]] = {}
        for seed in range(30):
            for level in LEVELS:
                for case in ClinicDayFactory(random.Random(seed)).build(level):
                    steps = case.ailment.steps
                    self.assertEqual(seen.setdefault(case.ailment_id, steps), steps)

    def test_factory_is_deterministic_varied_and_level_gated(self) -> None:
        first = ClinicDayFactory(random.Random(4)).build(2)
        self.assertEqual(first, ClinicDayFactory(random.Random(4)).build(2))
        for seed in range(40):
            for level, spec in LEVELS.items():
                cases = ClinicDayFactory(random.Random(seed)).build(level)
                self.assertEqual(len(cases), PATIENTS_PER_DAY)
                self.assertEqual({c.ailment_id for c in cases}, set(spec.ailments), "every ailment appears")
                for previous, current in zip(cases, cases[1:]):
                    self.assertNotEqual(previous.species_id, current.species_id, "a new visitor each time")
                    self.assertNotEqual(previous.ailment_id, current.ailment_id, "problems are spaced out")
                for case in cases:
                    self.assertLessEqual(case.species.min_level, level)
                    if case.ailment.pets_only:
                        self.assertTrue(case.species.mood_variants)

    def test_tray_grows_then_shuffles_only_at_the_top_level(self) -> None:
        factory = ClinicDayFactory(random.Random(2))
        self.assertNotIn(Tool.STETHOSCOPE, factory.tray(1))
        self.assertEqual(factory.tray(2), TRAY_ORDER)
        orders = {factory.tray(3) for _ in range(12)}
        self.assertGreater(len(orders), 1)
        self.assertTrue(all(sorted(order) == sorted(TRAY_ORDER) for order in orders))


class ClinicDayTests(unittest.TestCase):
    def test_find_then_care_in_order_with_kind_unlimited_retries(self) -> None:
        day = _day(("puppy", AilmentId.SORE_PAW), ("kitten", AilmentId.SORE_EAR))
        self.assertIsNone(day.find(BodyPart.PAW), "nothing happens while the patient walks in")
        day.arrived()
        self.assertIsNone(day.use_tool(Tool.SPONGE), "no care before looking")
        for _ in range(3):
            self.assertFalse(day.find(BodyPart.EAR).correct)
        self.assertIs(day.phase, Phase.FIND)
        self.assertTrue(day.find(BodyPart.PAW).correct)
        self.assertIs(day.phase, Phase.CARE)

        wrong = day.use_tool(Tool.BANDAGE)
        assert wrong is not None
        self.assertFalse(wrong.correct, "bandage before cleaning is not the next step")
        self.assertEqual(day.steps_done, 0)
        self.assertFalse(day.use_tool(Tool.CUDDLE).correct)
        self.assertTrue(day.use_tool(Tool.SPONGE).correct)
        self.assertTrue(day.use_tool(Tool.BANDAGE).correct)
        last = day.use_tool(Tool.CUDDLE)
        assert last is not None
        self.assertTrue(last.healed)
        self.assertIs(day.phase, Phase.HEALED)
        self.assertEqual(day.mistakes, 5)
        self.assertEqual(day.healed_count, 1)

        self.assertTrue(day.next_patient())
        self.assertEqual(day.case.species_id, "kitten")
        self.assertEqual((day.steps_done, day.patient_mistakes), (0, 0))

    def test_muddy_fur_is_found_anywhere(self) -> None:
        for part in (BodyPart.EAR, BodyPart.PAW, BodyPart.TUMMY):
            day = _day(("puppy", AilmentId.MUDDY_FUR))
            day.arrived()
            self.assertTrue(day.find(part).correct)

    def test_day_completes_once_and_level_adapts_within_bounds(self) -> None:
        day = _day(("bear", AilmentId.TUMMY_ACHE))
        day.arrived()
        day.find(BodyPart.TUMMY)
        for tool in AILMENTS[AilmentId.TUMMY_ACHE].steps:
            day.use_tool(tool)
        self.assertFalse(day.next_patient())
        self.assertIs(day.phase, Phase.DONE)
        self.assertEqual(day.consume_completion(), {"level": 2, "patients": 1, "mistakes": 0})
        self.assertIsNone(day.consume_completion())
        self.assertEqual(adapt_level(1, 0), 2)
        self.assertEqual(adapt_level(3, 0), 3)
        self.assertEqual(adapt_level(2, 4), 2)
        self.assertEqual(adapt_level(2, 9), 1)
        self.assertEqual(adapt_level(1, 9), 1)

    def test_patient_look_shows_the_problem_and_progress_never_the_tool(self) -> None:
        puppy = SPECIES["puppy"]
        muddy = AILMENTS[AilmentId.MUDDY_FUR]
        self.assertEqual(patient_look(puppy, muddy, 0, healed=False).variant, "dirty")
        washed = patient_look(puppy, muddy, 1, healed=False)
        self.assertEqual((washed.variant, washed.overlays[0][0]), ("default", Overlay.WET))
        self.assertEqual(patient_look(puppy, muddy, 3, healed=True).variant, "happy")
        paw = AILMENTS[AilmentId.SORE_PAW]
        self.assertEqual(patient_look(puppy, paw, 0, healed=False).variant, "hurt")
        self.assertEqual(patient_look(puppy, paw, 2, healed=False).overlays[0][0], Overlay.BANDAGE)
        ear = AILMENTS[AilmentId.SORE_EAR]
        self.assertEqual(patient_look(SPECIES["mouse"], ear, 0, healed=False).overlays[0][0], Overlay.THROB)
        self.assertEqual(patient_look(SPECIES["mouse"], ear, 2, healed=True).variant, "default")


class _Storage:
    def __init__(self, value=None) -> None:
        self.value = value
        self.saved = None

    def kv_get(self, key):
        return self.value

    def kv_set(self, key, value):
        self.saved = value
        self.value = value


class ProgressTests(unittest.TestCase):
    def test_existing_star_only_saves_still_load(self) -> None:
        loaded = GreiaClinicProgress(_Storage({"stars": 7})).load()
        self.assertEqual(loaded, ClinicProgressState(stars=7, level=1, days=0))

    def test_malformed_saves_recover_and_writes_stay_bounded(self) -> None:
        self.assertEqual(GreiaClinicProgress(_Storage("junk")).load(), ClinicProgressState())
        storage = _Storage({"stars": -3, "level": 99, "days": True})
        self.assertEqual(GreiaClinicProgress(storage).load(), ClinicProgressState(0, 3, 0))
        GreiaClinicProgress(storage).save(ClinicProgressState(stars=12, level=7, days=2))
        self.assertEqual(storage.saved, {"version": 3, "stars": 12, "level": 3, "days": 2})
        self.assertEqual(STORAGE_KEY, "clinica_cuccioli.progress.v2")


class EventContractTests(unittest.TestCase):
    def test_event_adapter_publishes_only_manifest_declared_ids(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        declared = {event["id"] for event in manifest["education"]["events"]}
        result = CareResult(Tool.CUDDLE, True, 2, True, PatientCase("kitten", AilmentId.SORE_EAR))
        with patch("clinic_services.emit_activity_event") as emit:
            events = GreiaClinicEvents()
            events.treatment_applied(result, level=1)
            events.patient_healed(result, stars=4, level=1)
            events.day_completed({"level": 1, "patients": 5, "mistakes": 0})
        emitted = [call.args[0] for call in emit.call_args_list]
        self.assertEqual(emitted, ["vet.treatment_applied", "vet.patient_healed", "vet.clinic_day_completed"])
        self.assertTrue(set(emitted).issubset(declared))

    def test_locales_keep_key_parity(self) -> None:
        import json

        keys = {
            locale: set(json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text(encoding="utf-8"))["strings"])
            for locale in ("en", "it", "es", "fr")
        }
        self.assertTrue(all(value == keys["en"] for value in keys.values()))


class _Events:
    def __init__(self) -> None:
        self.treatments: list[CareResult] = []
        self.healed: list[CareResult] = []
        self.days: list[dict] = []

    def treatment_applied(self, result, *, level) -> None:
        self.treatments.append(result)

    def patient_healed(self, result, *, stars, level) -> None:
        self.healed.append(result)

    def day_completed(self, summary) -> None:
        self.days.append(summary)


class _Audio:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.played: list[str] = []

    def say(self, cue: str) -> None:
        self.spoken.append(cue)

    def name(self, noun) -> None:
        if noun:
            self.spoken.append(f"vocab.{noun}")

    def play(self, name: str) -> None:
        self.played.append(name)


class AppIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _build(self, level: int = 2, *, seed: int = 11, storage=None):
        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from clinic_app import ClinicActivity

        screen = pygame.display.get_surface()
        assert screen is not None
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("en", support)
        assert context is not None
        self._storage = storage if storage is not None else _Storage({"stars": 2, "level": level})
        progress = GreiaClinicProgress(self._storage)
        saved = progress.load()
        factory = ClinicDayFactory(random.Random(seed))
        clock = [100.0]
        self._clock = clock
        self._events = _Events()
        self._audio = _Audio()
        self._app = ClinicActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            day=ClinicDay(factory.build(saved.level), level=saved.level),
            factory=factory,
            typography=GreiaTypography(),
            resources=LocalizedResources(ACTIVITY_ROOT, context),
            progress=progress,
            saved=saved,
            events=self._events,
            audio=self._audio,
            clock=lambda: clock[0],
        )
        return self._app

    def _advance(self, seconds: float, step: float = 0.05) -> None:
        end = self._clock[0] + seconds
        while self._clock[0] < end:
            self._clock[0] += step
            self._app.step()

    def _tap_logical(self, point) -> bool:
        # The test display is 1024x600, so logical == physical.
        return self._app.tap(point)

    def _sore_target(self) -> str:
        part = self._app.day.case.ailment.part
        return {BodyPart.EAR: "part.ear_right", BodyPart.PAW: "part.paw", BodyPart.TUMMY: "part.tummy", BodyPart.FUR: "part.tummy"}[part]

    def test_play_screen_has_no_text_and_no_answer_marking(self) -> None:
        from greia_platform.activity_controls import HudChip, IconButton, PillButton, PromptBanner

        app = self._build(level=2)
        self._advance(1.3)
        targets = app.controls.layer.targets
        self.assertFalse(any(isinstance(t, (PromptBanner, HudChip, PillButton)) for t in targets))
        tiles = [t for t in targets if isinstance(t, IconButton)]
        self.assertEqual(len(tiles), len(TRAY_ORDER))
        self.assertTrue(all(not t.enabled for t in tiles), "tools wait until the child has looked")
        self.assertTrue(all(app.controls.parts[p].enabled for p in app.controls.parts))
        self._tap_logical(app.controls.parts[self._sore_target()].rect.center)
        self._advance(1.2)
        self.assertIs(app.day.phase, Phase.CARE)
        tiles = [t for t in app.controls.layer.targets if isinstance(t, IconButton)]
        self.assertTrue(all(t.enabled for t in tiles))
        self.assertEqual(len({(t.role, t.selected, t.caption) for t in tiles}), 1, "tiles look identical")
        self.assertIsNone(app.motion.tool_hop)
        app.render()

    def test_wrong_tool_thinks_shakes_then_demonstrates_and_allows_retry(self) -> None:
        from greia_platform.activity_feedback import CastPose
        from clinic_controls import tool_id

        app = self._build(level=2)
        self._advance(1.3)
        self._tap_logical(app.controls.parts[self._sore_target()].rect.center)
        self._advance(1.2)
        expected = app.day.expected_tool
        wrong = next(tool for tool in app.controls.tray if tool is not expected)
        self.assertTrue(self._tap_logical(app.controls.tiles[wrong].rect.center))
        self.assertIs(app.cast.pose, CastPose.THINK)
        self.assertIsNotNone(app.motion.shake_start)
        self.assertIn("encourage.retry", self._audio.spoken)
        self.assertEqual(app.day.steps_done, 0)
        self._advance(1.5)
        self.assertEqual(app.motion.tool_hop[0], tool_id(expected), "the right tool is demonstrated")
        self.assertTrue(self._tap_logical(app.controls.tiles[expected].rect.center))
        self.assertEqual(app.day.steps_done, 1)
        self.assertEqual(len(self._events.treatments), 1)

    def test_wrong_look_demonstrates_the_sore_place(self) -> None:
        app = self._build(level=2, seed=3)
        self._advance(1.3)
        part = app.day.case.ailment.part
        if part is BodyPart.FUR:
            self.skipTest("seed starts with a muddy patient")
        wrong = "part.ear_left" if part is not BodyPart.EAR else "part.paw"
        self.assertTrue(self._tap_logical(app.controls.parts[wrong].rect.center))
        self.assertIs(app.day.phase, Phase.FIND)
        self._advance(1.5)
        self.assertTrue(app.motion.halos, "the sore place glows after a wrong look")

    def test_keyboard_finds_and_cares(self) -> None:
        app = self._build(level=1, seed=5)
        self._advance(1.3)
        layer = app.controls.layer
        app.press(pygame.K_RIGHT)
        self.assertTrue(layer.focus_visible)
        layer.focus(self._sore_target(), visible=True)
        app.press(pygame.K_RETURN)
        self._advance(1.2)
        self.assertIs(app.day.phase, Phase.CARE)
        self.assertTrue(layer.focused_id.startswith("tool."))
        from clinic_controls import tool_id

        first = layer.focused_id
        app.press(pygame.K_RIGHT)
        self.assertNotEqual(layer.focused_id, first, "arrows move along the tray")
        layer.focus(tool_id(app.day.expected_tool), visible=True)
        app.press(pygame.K_SPACE)
        self.assertEqual(app.day.steps_done, 1)

    def test_idle_hints_are_graduated(self) -> None:
        app = self._build(level=2)
        self._advance(1.3)
        self._advance(6.3)
        self.assertTrue(app.cast.pointing)
        self.assertFalse(app.motion.halos, "the first nudge does not show the answer")
        self._advance(6.5)
        self.assertTrue(app.motion.halos or app.cast.pointing)

    def test_protected_chrome_region_is_ignored(self) -> None:
        app = self._build(level=1)
        self._advance(1.3)
        self.assertFalse(app.tap((4, 4)))
        self.assertIs(app.day.phase, Phase.FIND)

    def test_full_day_plays_to_completion_saves_and_restarts(self) -> None:
        from clinic_app import AppState

        app = self._build(level=1, seed=7)
        for _ in range(PATIENTS_PER_DAY):
            self._advance(1.3)
            self.assertTrue(self._tap_logical(app.controls.parts[self._sore_target()].rect.center))
            self._advance(1.2)
            while app.day.phase is Phase.CARE:
                self.assertTrue(self._tap_logical(app.controls.tiles[app.day.expected_tool].rect.center))
                self._advance(1.3)
            self._advance(3.6)
        self._advance(0.5)
        self.assertIs(app.state, AppState.TERMINAL)
        self.assertEqual(len(self._events.healed), PATIENTS_PER_DAY)
        self.assertEqual(self._events.days, [{"level": 1, "patients": 5, "mistakes": 0}])
        self.assertEqual(self._storage.saved["stars"], 2 + PATIENTS_PER_DAY)
        self.assertEqual(self._storage.saved["level"], 2, "a calm day moves up one level")
        self.assertIn("celebrate.success", self._audio.spoken)
        app.render()
        self.assertTrue(app.tap(app.completion.primary_rect.center))
        self.assertIs(app.state, AppState.PLAYING)
        self.assertEqual(app.day.level, 2)
        self.assertEqual(app.day.index, 0)
        self.assertIs(app.day.phase, Phase.ARRIVING)


if __name__ == "__main__":
    unittest.main()
