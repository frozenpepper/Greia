from __future__ import annotations

from pathlib import Path
import random
import sys
import tomllib
import unittest

import pygame


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "tre_carte_una_storia"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from story_cards_content import STORY_SEEDS, VALID_SEED_IDS, StoryCard, StorySeed  # noqa: E402
from story_cards_model import (  # noqa: E402
    MAX_GRAPHEMES,
    MAX_SAVED_STORIES,
    SavedStory,
    StoryLibrary,
    StoryRound,
    StoryStage,
    create_shuffled_round,
)
from story_cards_services import GreiaStoryStorage, StoragePort  # noqa: E402


class StoryContentTests(unittest.TestCase):
    def test_seeds_are_eight_and_valid(self) -> None:
        self.assertEqual(len(STORY_SEEDS), 8)
        for seed in STORY_SEEDS:
            with self.subTest(seed=seed.seed_id):
                self.assertIn(seed.seed_id, VALID_SEED_IDS)
                self.assertEqual(len(seed.cards), 3)
                self.assertEqual(len(seed.caption_keys), 3)


class StoryRoundTests(unittest.TestCase):
    def test_initial_shuffle_is_never_correct_order(self) -> None:
        rng = random.Random(42)
        seed = STORY_SEEDS[0]
        for _ in range(100):
            round_state = create_shuffled_round(seed, rng)
            self.assertFalse(round_state.is_correct_order)

    def test_swap_and_error_hint_after_two_attempts(self) -> None:
        seed = STORY_SEEDS[0]
        # Start with deliberately inverted order: [card_3, card_2, card_1]
        round_state = StoryRound(seed, [seed.cards[2], seed.cards[1], seed.cards[0]])
        self.assertFalse(round_state.is_correct_order)
        self.assertFalse(round_state.hint_revealed)

        # Attempt 1: wrong check
        self.assertFalse(round_state.check_sequence())
        self.assertEqual(round_state.error_count, 1)
        self.assertFalse(round_state.hint_revealed)

        # Attempt 2: wrong check -> triggers hint
        self.assertFalse(round_state.check_sequence())
        self.assertEqual(round_state.error_count, 2)
        self.assertTrue(round_state.hint_revealed)

        # Swap slot 0 and slot 2 -> now correct [card_1, card_2, card_3]
        self.assertTrue(round_state.swap_slots(0, 2))
        self.assertTrue(round_state.is_correct_order)
        self.assertTrue(round_state.check_sequence())
        self.assertEqual(round_state.stage, StoryStage.CAPTION)


class StoryLibraryTests(unittest.TestCase):
    def test_library_capacity_twelve_and_no_auto_eviction(self) -> None:
        lib = StoryLibrary()
        for i in range(MAX_SAVED_STORIES):
            story = SavedStory(
                story_id=f"story-{i}",
                created_at=1000 + i,
                seed_id="drawing",
                card_ids=("drawing_1", "drawing_2", "drawing_3"),
                caption_mode="preset_0",
                caption_text=f"Story {i}",
            )
            self.assertTrue(lib.add(story))

        self.assertEqual(lib.count, 12)
        self.assertTrue(lib.is_full)

        # 13th story cannot be added
        story13 = SavedStory(
            story_id="story-13",
            created_at=2000,
            seed_id="drawing",
            card_ids=("drawing_1", "drawing_2", "drawing_3"),
            caption_mode="preset_0",
            caption_text="Story 13",
        )
        self.assertFalse(lib.add(story13))
        self.assertEqual(lib.count, 12)

    def test_delete_story(self) -> None:
        story = SavedStory("s1", 1000, "drawing", ("drawing_1", "drawing_2", "drawing_3"), "preset_0", "Text")
        lib = StoryLibrary([story])
        self.assertEqual(lib.count, 1)
        self.assertTrue(lib.delete("s1"))
        self.assertEqual(lib.count, 0)


class _Storage:
    def __init__(self, value=None) -> None:
        self.value = value
        self.saved = None
        self.fail_save = False

    def kv_get(self, key):
        return self.value

    def kv_set(self, key, value):
        if self.fail_save:
            raise RuntimeError("storage write failed")
        self.saved = value


class StorageTests(unittest.TestCase):
    def test_storage_sanitization_and_recovery(self) -> None:
        raw = {
            "schema_version": 1,
            "stories": [
                {
                    "id": "s1",
                    "created_at": 1000,
                    "seed": "drawing",
                    "cards": ["drawing_1", "drawing_2", "drawing_3"],
                    "mode": "preset_0",
                    "caption": "Valid story",
                },
                {
                    "id": "s2",
                    "created_at": 1001,
                    "seed": "unknown_seed",
                    "cards": ["c1", "c2", "c3"],
                    "mode": "preset_0",
                    "caption": "Bad Seed",
                },
                {
                    "id": "s3",
                    "created_at": 1002,
                    "seed": "drawing",
                    "cards": ["c1", "c2"],
                    "mode": "preset_0",
                    "caption": "Bad Cards",
                },
                {
                    "id": "s4",
                    "created_at": 1003,
                    "seed": "drawing",
                    "cards": ["c1", "c2", "c3"],
                    "mode": "preset_0",
                    "caption": "A" * 100,
                },
            ],
        }
        storage = _Storage(raw)
        repo = GreiaStoryStorage(storage)
        lib = repo.load()
        self.assertEqual(lib.count, 1)
        self.assertEqual(lib.stories[0].story_id, "s1")


class ManifestTests(unittest.TestCase):
    def test_manifest_metadata_and_open_ended_age(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["id"], "org.greia.tre-carte-una-storia")
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])
        self.assertEqual(manifest["input"]["profile"], "hybrid")
        self.assertEqual(manifest["education"]["difficulty"], 2)
        self.assertEqual(manifest["education"]["recommended_age_min"], 5)
        self.assertNotIn("recommended_age_max", manifest["education"])
        self.assertNotIn("adaptive_difficulty", manifest["education"])
        self.assertEqual(
            manifest["education"]["events"],
            [
                {"id": "story.sequence_completed", "kind": "completion"},
                {"id": "story.created", "kind": "creation"},
            ],
        )


class _MockEvents:
    def __init__(self) -> None:
        self.sequence_completed_seeds: list[StorySeed] = []
        self.created_stories: list[SavedStory] = []

    def sequence_completed(self, seed: StorySeed) -> None:
        self.sequence_completed_seeds.append(seed)

    def story_created(self, story: SavedStory) -> None:
        self.created_stories.append(story)


class AppIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import os
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _build_app(self, library: StoryLibrary | None = None):
        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from story_cards_app import StoryActivity
        from story_cards_art import StoryArt
        from story_cards_audio import StoryAudio
        from story_cards_renderer import StoryRenderer

        screen = pygame.display.get_surface()
        assert screen is not None
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        typography = GreiaTypography()
        canvas = PygameReferenceCanvas(screen)
        art = StoryArt(1024, 600, typography)
        renderer = StoryRenderer(art, typography, resources)
        storage = _Storage({"schema_version": 1, "stories": []})
        repo = GreiaStoryStorage(storage)
        events = _MockEvents()
        audio = StoryAudio()
        rng = random.Random(42)
        seed = STORY_SEEDS[0]
        # Inverted cards: [card_3, card_2, card_1]
        round_state = StoryRound(seed, [seed.cards[2], seed.cards[1], seed.cards[0]])
        lib = library if library is not None else StoryLibrary()

        simulated_time = [100.0]

        def clock() -> float:
            return simulated_time[0]

        app = StoryActivity(
            screen=screen,
            canvas=canvas,
            round_state=round_state,
            library=lib,
            renderer=renderer,
            typography=typography,
            resources=resources,
            storage=repo,
            events=events,
            audio=audio,
            rng=rng,
            session_id="story-session-1",
            clock=clock,
        )
        return app, simulated_time, events, storage

    def test_full_puzzle_solve_caption_and_save_flow(self) -> None:
        from story_cards_app import ViewMode
        from story_cards_renderer import CHECK_BTN_RECT, SAVE_BTN_RECT

        app, sim_time, events, storage = self._build_app()

        # Step 1: Swap slot 0 and slot 2
        slot0_rect = app.renderer.slot_rect_at(0)
        slot2_rect = app.renderer.slot_rect_at(2)
        app._handle_pointer((slot0_rect.centerx, slot0_rect.centery))
        app._handle_pointer((slot2_rect.centerx, slot2_rect.centery))
        self.assertTrue(app.round_state.is_correct_order)

        # Step 2: Check sequence
        app._handle_pointer((CHECK_BTN_RECT.centerx, CHECK_BTN_RECT.centery))
        self.assertEqual(app.round_state.stage, StoryStage.CAPTION)
        self.assertEqual(len(events.sequence_completed_seeds), 1)

        # Step 3: Choose preset caption 1
        p1_rect = app.renderer.caption_preset_rect_at(1)
        app._handle_pointer((p1_rect.centerx, p1_rect.centery))
        self.assertEqual(app.round_state.caption_mode, "preset_1")

        # Step 4: Save Story
        app._handle_pointer((SAVE_BTN_RECT.centerx, SAVE_BTN_RECT.centery))
        self.assertEqual(app.library.count, 1)
        self.assertEqual(len(events.created_stories), 1)
        # Verify event payload privacy
        self.assertEqual(events.created_stories[0].seed_id, "drawing")
        self.assertEqual(events.created_stories[0].caption_mode, "preset_1")

    def test_audio_assets_and_speech_cues(self) -> None:
        from story_cards_audio import StoryAudio
        audio_it = StoryAudio(ACTIVITY_ROOT, locale="it")
        audio_en = StoryAudio(ACTIVITY_ROOT, locale="en")

        self.assertIn("welcome", audio_it._speech_clips)
        self.assertIn("welcome", audio_en._speech_clips)
        self.assertIn("slot_1", audio_it._speech_clips)
        self.assertIn("correct_1", audio_it._speech_clips)
        self.assertIn("story_drawing_c1", audio_it._speech_clips)

        # Nonverbal and speech playback does not raise
        audio_it.play("select")
        audio_it.play_welcome()
        audio_it.play_slot(0)
        audio_it.play_story_sentence("drawing", 0)
        audio_it.play_caption_intro()
        audio_it.play_feedback(True)
        audio_it.play_feedback(False)

    def test_listen_button_replays_welcome(self) -> None:
        from story_cards_renderer import LISTEN_BTN_RECT
        app, sim_time, events, storage = self._build_app()
        # Tap listen button
        handled = app._handle_pointer((LISTEN_BTN_RECT.centerx, LISTEN_BTN_RECT.centery))
        self.assertTrue(handled)


class SimulatorSupervisorTests(unittest.TestCase):
    def test_simulator_supervises_tre_carte_una_storia(self) -> None:
        import os
        import tempfile
        import time
        from greia_launcher.child_shell import ProfileVisualActivitySupervisor
        from greia_launcher.composition import build_launcher_runtime_services
        from greia_launcher.runtime_adapter import PythonRuntimePolicy
        from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
        from greia_platform.trust import ActivitySource, PackageTrust
        from greia_simulator.device import DEFAULT_CAPABILITIES, SimulatedDeviceProfile
        from greia_simulator.runtime import SimulatorPythonRuntimeAdapter
        from greia_simulator.workspace import SimulatorWorkspace

        runtime = RuntimeCatalogue.load(ROOT / "runtime" / "child-runtime.toml")
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            base = Path(directory)
            workspace = SimulatorWorkspace(ROOT, base / "state")
            device = SimulatedDeviceProfile(1024, 600, DEFAULT_CAPABILITIES)
            adapter = SimulatorPythonRuntimeAdapter(
                device,
                policy=PythonRuntimePolicy.load(ROOT / "runtime" / "child-runtime.toml"),
            )
            source = ActivitySource(ROOT / "activities", PackageTrust.BUILT_IN, "builtin")
            registrations = ActivityRegistry([source], runtime).discover_registrations()
            registration = next(r for r in registrations if r.manifest.activity_id == "org.greia.tre-carte-una-storia")
            manifest = registration.manifest

            services = build_launcher_runtime_services(
                runtime,
                tuple(r.manifest for r in registrations),
                runtime_policy_path=ROOT / "runtime" / "child-runtime.toml",
                permission_policy_path=ROOT / "runtime" / "permission-policy.toml",
                storage_policy_path=ROOT / "runtime" / "storage-policy.toml",
                history_policy_path=ROOT / "runtime" / "history-policy.toml",
                progression_policy_path=ROOT / "runtime" / "progression-policy.toml",
                hal=device.to_hal(),
                runtime_adapters=(adapter,),
            )
            profile = workspace.profile_store().context(workspace.profiles()[0].profile_id)
            authority = services.permission_broker.issue(registration)
            supervisor = ProfileVisualActivitySupervisor(
                runtime_manager=services.runtime_manager,
                storage_service=services.storage_service,
                history_service=services.history_service,
                display_coordinator=None,
            )
            environment = workspace.environment()
            environment.update(
                {
                    "SDL_VIDEODRIVER": "dummy",
                    "SDL_AUDIODRIVER": "dummy",
                    "PYGAME_HIDE_SUPPORT_PROMPT": "1",
                }
            )
            import unittest.mock as mock
            with mock.patch.dict(os.environ, environment, clear=False):
                session = supervisor.start(manifest, profile, authority)
                deadline = time.monotonic() + 10.0
                while (
                    session.result is None
                    and session.ready_at is None
                    and time.monotonic() < deadline
                ):
                    supervisor.poll(session)
                    time.sleep(0.02)
                self.assertIsNone(session.result, session.result)
                self.assertIsNotNone(session.ready_at)

                # Request stop
                result = supervisor.request_stop(session)
                deadline = time.monotonic() + 5.0
                while result is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                    result = supervisor.poll(session)
                self.assertIsNotNone(result)
                assert result is not None
                self.assertTrue(result.ready)
                self.assertTrue(result.succeeded)


if __name__ == "__main__":
    unittest.main()
