from __future__ import annotations

from pathlib import Path
import random
import sys
import tomllib
import unittest

import pygame

import hermetic_volume


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "posta_di_leo"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from postcard_content import RECIPIENTS, STAMPS, VALID_RECIPIENT_IDS, VALID_STAMP_IDS  # noqa: E402
from postcard_model import (  # noqa: E402
    MAX_GRAPHEMES,
    MAX_SAVED_CARDS,
    PostcardDraft,
    PostcardLibrary,
    SavedPostcard,
)
from postcard_services import GreiaPostcardStorage, StoragePort  # noqa: E402


def setUpModule() -> None:
    # The Simulator supervision test exercises real history/storage services,
    # whose production capacity policy depends on how full the host disk is.
    hermetic_volume.install_for_module()


class PostcardContentTests(unittest.TestCase):
    def test_content_is_complete_and_valid(self) -> None:
        self.assertEqual(len(RECIPIENTS), 6)
        self.assertEqual(len(STAMPS), 6)
        self.assertIn("leo", VALID_RECIPIENT_IDS)
        self.assertIn("heart", VALID_STAMP_IDS)


class GraphemeEditingTests(unittest.TestCase):
    def test_atomic_emoji_and_grapheme_editing(self) -> None:
        draft = PostcardDraft()

        # Insert emoji sequence (astronaut woman with medium-dark skin: 👩🏾‍🚀)
        astronaut = "👩🏾‍🚀"
        draft.insert(astronaut)
        self.assertEqual(draft.grapheme_count, 1)

        # Insert standard text
        draft.insert(" Ciao Momo!")
        self.assertEqual(draft.text, f"{astronaut} Ciao Momo!")

        # Backspace on end removes "!"
        draft.backspace()
        self.assertEqual(draft.text, f"{astronaut} Ciao Momo")

        # Move cursor to after astronaut (index after first grapheme) and backspace
        draft.move_left()  # before o
        draft.move_left()  # before m
        draft.move_left()  # before o
        draft.move_left()  # before M
        draft.move_left()  # before space
        draft.move_left()  # before o
        draft.move_left()  # before a
        draft.move_left()  # before i
        draft.move_left()  # before C
        draft.move_left()  # after astronaut

        draft.backspace()  # removes astronaut completely in one atomic deletion
        self.assertEqual(draft.text, " Ciao Momo")

    def test_maximum_eighty_graphemes_enforced(self) -> None:
        draft = PostcardDraft()
        long_text = "A" * MAX_GRAPHEMES
        self.assertTrue(draft.insert(long_text))
        self.assertEqual(draft.grapheme_count, 80)

        # 81st grapheme must be rejected
        self.assertFalse(draft.insert("B"))
        self.assertEqual(draft.grapheme_count, 80)

    def test_empty_text_with_stamp_is_valid(self) -> None:
        draft = PostcardDraft(recipient_id="momo", stamp_id="rainbow", text="")
        self.assertEqual(draft.text, "")
        card = SavedPostcard(
            card_id="card-1",
            created_at=1000,
            recipient_id=draft.recipient_id,
            stamp_id=draft.stamp_id,
            text=draft.text,
        )
        self.assertEqual(card.text, "")


class PostcardLibraryTests(unittest.TestCase):
    def test_library_capacity_and_no_auto_eviction(self) -> None:
        library = PostcardLibrary()

        # Add 20 cards
        for i in range(MAX_SAVED_CARDS):
            card = SavedPostcard(
                card_id=f"card-{i}",
                created_at=1000 + i,
                recipient_id="leo",
                stamp_id="heart",
                text=f"Msg {i}",
            )
            self.assertTrue(library.add(card))

        self.assertEqual(library.count, 20)
        self.assertTrue(library.is_full)

        # 21st card cannot be added (no silent auto-eviction!)
        card21 = SavedPostcard(
            card_id="card-21",
            created_at=2000,
            recipient_id="leo",
            stamp_id="heart",
            text="Msg 21",
        )
        self.assertFalse(library.add(card21))
        self.assertEqual(library.count, 20)
        self.assertEqual(library.cards[-1].card_id, "card-0")

    def test_delete_card(self) -> None:
        card = SavedPostcard("c1", 1000, "momo", "sun", "Hello")
        library = PostcardLibrary([card])
        self.assertEqual(library.count, 1)

        self.assertTrue(library.delete("c1"))
        self.assertEqual(library.count, 0)
        self.assertFalse(library.delete("c1"))


class _Storage:
    def __init__(self, value=None) -> None:
        self.value = value
        self.saved = None
        self.fail_save = False
        self.files: dict[str, bytes] = {}

    def kv_get(self, key):
        return self.value

    def kv_set(self, key, value):
        if self.fail_save:
            raise RuntimeError("storage write failed")
        self.saved = value
        self.value = value

    def file_write_atomic(self, name, payload):
        self.files[name] = bytes(payload)

    def file_read(self, name):
        if name not in self.files:
            raise RuntimeError("missing file")
        return self.files[name]

    def file_delete(self, name):
        return self.files.pop(name, None) is not None


class StorageTests(unittest.TestCase):
    def test_storage_sanitization_and_recovery(self) -> None:
        raw = {
            "schema_version": 1,
            "cards": [
                {"id": "c1", "created_at": 1000, "recipient": "momo", "stamp": "star", "text": "Valid"},
                {"id": "c2", "created_at": 1001, "recipient": "unknown", "stamp": "star", "text": "Bad Recipient"},
                {"id": "c3", "created_at": 1002, "recipient": "leo", "stamp": "unknown", "text": "Bad Stamp"},
                {"id": "c4", "created_at": 1003, "recipient": "leo", "stamp": "star", "text": "A" * 100},
                {"id": "c5", "created_at": 1004, "recipient": "leo", "stamp": "star", "text": "Bad\x00Control"},
                {"id": "c1", "created_at": 1005, "recipient": "leo", "stamp": "star", "text": "Duplicate"},
            ],
        }
        storage = _Storage(raw)
        repo = GreiaPostcardStorage(storage)
        lib = repo.load()
        self.assertEqual(lib.count, 1)
        self.assertEqual(lib.cards[0].card_id, "c1")


class ManifestTests(unittest.TestCase):
    def test_manifest_metadata_and_open_ended_age(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["id"], "org.greia.posta-di-leo")
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])
        self.assertEqual(manifest["input"]["profile"], "text")
        self.assertEqual(manifest["education"]["difficulty"], 2)
        self.assertEqual(manifest["education"]["recommended_age_min"], 5)
        self.assertNotIn("recommended_age_max", manifest["education"])
        self.assertNotIn("adaptive_difficulty", manifest["education"])
        self.assertEqual(
            manifest["education"]["events"],
            [{"id": "postcard.created", "kind": "creation"}],
        )


class _MockEvents:
    def __init__(self) -> None:
        self.created: list[SavedPostcard] = []

    def postcard_created(self, card: SavedPostcard) -> None:
        self.created.append(card)


class AppIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import os
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _build_app(self, library: PostcardLibrary | None = None):
        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from postcard_app import PostcardActivity
        from postcard_art import PostcardArt
        from postcard_audio import PostcardAudio
        from postcard_renderer import PostcardRenderer

        screen = pygame.display.get_surface()
        assert screen is not None
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        typography = GreiaTypography()
        canvas = PygameReferenceCanvas(screen)
        art = PostcardArt(1024, 600, typography)
        renderer = PostcardRenderer(art, typography, resources)
        storage = _Storage({"schema_version": 1, "cards": []})
        repo = GreiaPostcardStorage(storage)
        events = _MockEvents()
        audio = PostcardAudio()
        rng = random.Random(99)
        draft = PostcardDraft(recipient_id="leo", stamp_id="heart")
        lib = library if library is not None else PostcardLibrary()

        simulated_time = [100.0]

        def clock() -> float:
            return simulated_time[0]

        app = PostcardActivity(
            screen=screen,
            canvas=canvas,
            draft=draft,
            library=lib,
            renderer=renderer,
            typography=typography,
            resources=resources,
            storage=repo,
            events=events,
            audio=audio,
            rng=rng,
            session_id="postcard-session-1",
            clock=clock,
        )
        return app, simulated_time, events, storage

    def test_save_postcard_flow_and_privacy_invariant(self) -> None:
        from postcard_app import ViewMode
        from postcard_renderer import SEND_BTN_RECT

        app, sim_time, events, storage = self._build_app()

        # Type message
        app._handle_event(pygame.event.Event(pygame.TEXTINPUT, text="Caro Leo, ciao!"))
        self.assertEqual(app.draft.text, "Caro Leo, ciao!")

        # Click send
        app._handle_pointer((SEND_BTN_RECT.centerx, SEND_BTN_RECT.centery))

        # Check library saved
        self.assertEqual(app.library.count, 1)
        self.assertEqual(app.draft.text, "")
        self.assertEqual(len(events.created), 1)
        # Event payload must contain recipient and stamp, but NO text
        self.assertEqual(events.created[0].recipient_id, "leo")
        self.assertEqual(events.created[0].stamp_id, "heart")

    def test_full_library_triggers_dialog_and_gallery_delete(self) -> None:
        from postcard_app import ViewMode
        from postcard_renderer import GALLERY_BTN_RECT, SEND_BTN_RECT

        # Create library with 20 cards
        lib = PostcardLibrary([
            SavedPostcard(f"c{i}", 1000 + i, "momo", "sun", f"msg {i}") for i in range(20)
        ])
        app, sim_time, events, storage = self._build_app(library=lib)

        # Try to send when full -> must open full dialog
        app._handle_pointer((SEND_BTN_RECT.centerx, SEND_BTN_RECT.centery))
        self.assertEqual(app.view_mode, ViewMode.FULL_DIALOG)
        self.assertEqual(len(events.created), 0)

        # Tap anywhere in full dialog to dismiss
        app._handle_pointer((500, 300))
        self.assertEqual(app.view_mode, ViewMode.EDITOR)

        # Open Gallery
        app._handle_pointer((GALLERY_BTN_RECT.centerx, GALLERY_BTN_RECT.centery))
        self.assertEqual(app.view_mode, ViewMode.GALLERY)

        # Tap first card in gallery to open preview modal
        c_rect = app.renderer.gallery_card_rect_at(0)
        app._handle_pointer((c_rect.centerx, c_rect.centery))
        self.assertIsNotNone(app.selected_gallery_card_id)

        # Tap delete button
        del_rect = app.renderer.delete_btn_rect()
        app._handle_pointer((del_rect.centerx, del_rect.centery))
        self.assertTrue(app.confirm_delete)

        # Confirm delete
        app._handle_pointer((del_rect.centerx, del_rect.centery))
        self.assertFalse(app.confirm_delete)
        self.assertEqual(app.library.count, 19)


class SimulatorSupervisorTests(unittest.TestCase):
    def test_simulator_supervises_posta_di_leo(self) -> None:
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
        # Honor TMPDIR (device /tmp is noexec); no exec artifact or
        # explicit broker socket lives here — broker defaults already
        # handle sun_path length with a /tmp fallback. T02-SPAWN-HYGIENE.
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = SimulatorWorkspace(ROOT, base / "state")
            device = SimulatedDeviceProfile(1024, 600, DEFAULT_CAPABILITIES)
            adapter = SimulatorPythonRuntimeAdapter(
                device,
                policy=PythonRuntimePolicy.load(ROOT / "runtime" / "child-runtime.toml"),
            )
            source = ActivitySource(ROOT / "activities", PackageTrust.BUILT_IN, "builtin")
            registrations = ActivityRegistry([source], runtime).discover_registrations()
            registration = next(r for r in registrations if r.manifest.activity_id == "org.greia.posta-di-leo")
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
