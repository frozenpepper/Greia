"""Leo's Post: picture postcards for cast friends (model, storage, app loop).

Source-level and headless (dummy SDL) evidence only; no hardware claim.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import sys
import tomllib
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import hermetic_volume


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "posta_di_leo"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from postcard_content import (  # noqa: E402
    FRIENDS,
    MAX_STICKERS,
    RECIPIENTS,
    SCENES,
    STAMPS,
    STICKERS,
    VALID_RECIPIENT_IDS,
    VALID_STAMP_IDS,
)
from postcard_model import (  # noqa: E402
    MAX_GRAPHEMES,
    MAX_SAVED_CARDS,
    CardFront,
    PlacedSticker,
    PostcardDraft,
    PostcardLibrary,
    SavedPostcard,
)
from postcard_services import DRAFT_KEY, STORAGE_KEY, GreiaPostcardStorage  # noqa: E402


def setUpModule() -> None:
    # The Simulator supervision test exercises real history/storage services,
    # whose production capacity policy depends on how full the host disk is.
    hermetic_volume.install_for_module()


class MemoryStorage:
    def __init__(self, value=None) -> None:
        self.kv: dict[str, object] = {}
        if value is not None:
            self.kv[STORAGE_KEY] = value
        self.files: dict[str, bytes] = {}
        self.fail_save = False

    @property
    def value(self):
        return self.kv.get(STORAGE_KEY)

    def kv_get(self, key, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        if self.fail_save and key == STORAGE_KEY:
            raise RuntimeError("storage write failed")
        self.kv[key] = value

    def kv_delete(self, key):
        return self.kv.pop(key, None) is not None

    def file_write_atomic(self, name, payload):
        self.files[name] = bytes(payload)

    def file_read(self, name):
        if name not in self.files:
            raise RuntimeError("missing file")
        return self.files[name]

    def file_delete(self, name):
        return self.files.pop(name, None) is not None


class PostcardContentTests(unittest.TestCase):
    def test_friends_are_the_canonical_cast(self) -> None:
        self.assertEqual({f.friend_id for f in FRIENDS}, {"leo", "lilli", "momo", "dani", "tito", "flash"})
        self.assertIs(RECIPIENTS, FRIENDS)
        self.assertNotIn("pina", VALID_RECIPIENT_IDS)
        self.assertEqual(len(STAMPS), 6)
        self.assertIn("heart", VALID_STAMP_IDS)
        self.assertTrue(all(f.stamp_id in VALID_STAMP_IDS for f in FRIENDS))

    def test_all_pictures_resolve_in_the_shared_library(self) -> None:
        from greia_platform.activity_api import get_shared_visual_path

        ids = [s.asset_id for s in SCENES] + [s.asset_id for s in STICKERS] + [s.asset_id for s in STAMPS]
        ids += [f"character.{f.friend_id}" for f in FRIENDS]
        for asset_id in ids:
            with self.subTest(asset=asset_id):
                self.assertTrue(Path(get_shared_visual_path(asset_id)).is_file())
        for friend in FRIENDS:
            for variant in ("happy", "pose_cheer", "pose_think", "pose_point"):
                self.assertTrue(Path(get_shared_visual_path(f"character.{friend.friend_id}", variant=variant)).is_file())

    def test_every_friend_has_an_approved_reaction_clip(self) -> None:
        from postcard_audio import reaction_clip_path

        for friend in FRIENDS:
            for locale in ("en", "it"):
                with self.subTest(friend=friend.friend_id, locale=locale):
                    path = reaction_clip_path(friend.friend_id, locale)
                    self.assertIsNotNone(path)
                    self.assertTrue(path.is_file())
                    self.assertIn("celebrate.success", path.name)


class GraphemeEditingTests(unittest.TestCase):
    def test_atomic_emoji_and_grapheme_editing(self) -> None:
        draft = PostcardDraft()
        astronaut = "👩🏾‍🚀"
        draft.insert(astronaut)
        self.assertEqual(draft.grapheme_count, 1)
        draft.insert(" Ciao Momo!")
        self.assertEqual(draft.text, f"{astronaut} Ciao Momo!")
        draft.backspace()
        self.assertEqual(draft.text, f"{astronaut} Ciao Momo")
        for _ in range(10):
            draft.move_left()
        draft.backspace()  # removes the astronaut completely in one deletion
        self.assertEqual(draft.text, " Ciao Momo")

    def test_maximum_eighty_graphemes_enforced(self) -> None:
        draft = PostcardDraft()
        self.assertTrue(draft.insert("A" * MAX_GRAPHEMES))
        self.assertEqual(draft.grapheme_count, 80)
        self.assertFalse(draft.insert("B"))
        self.assertEqual(draft.grapheme_count, 80)

    def test_empty_text_with_stamp_is_valid(self) -> None:
        draft = PostcardDraft(recipient_id="momo", stamp_id="rainbow", text="")
        card = SavedPostcard("card-1", 1000, draft.recipient_id, draft.stamp_id, draft.text)
        self.assertEqual(card.text, "")
        self.assertEqual(card.front, CardFront.scene("rainbow"))


class DraftRulesTests(unittest.TestCase):
    def test_ready_needs_a_friend_and_a_front_only(self) -> None:
        draft = PostcardDraft()
        self.assertTrue(draft.is_blank)
        self.assertFalse(draft.ready)
        draft.set_recipient("flash")
        self.assertFalse(draft.ready)
        self.assertEqual(draft.stamp_id, "butterfly")  # each friend has their own stamp
        draft.set_front(CardFront.scene("space"))
        self.assertTrue(draft.ready)  # stickers and the message stay optional

    def test_stickers_land_on_free_spots_and_are_bounded(self) -> None:
        draft = PostcardDraft()
        positions = set()
        for _ in range(MAX_STICKERS):
            index = draft.add_sticker("heart")
            self.assertIsNotNone(index)
            placed = draft.stickers[index]
            positions.add((placed.x, placed.y))
        self.assertEqual(len(positions), MAX_STICKERS)
        self.assertIsNone(draft.add_sticker("star"))
        self.assertTrue(draft.move_sticker(0, 1.4, -0.2))
        self.assertEqual((draft.stickers[0].x, draft.stickers[0].y), (1.0, 0.0))
        self.assertTrue(draft.pop_sticker())
        self.assertEqual(len(draft.stickers), MAX_STICKERS - 1)
        with self.assertRaises(ValueError):
            PlacedSticker("dragon", 0.5, 0.5)


class PostcardLibraryTests(unittest.TestCase):
    def test_library_capacity_and_no_auto_eviction(self) -> None:
        library = PostcardLibrary()
        for i in range(MAX_SAVED_CARDS):
            self.assertTrue(library.add(SavedPostcard(f"card-{i}", 1000 + i, "leo", "heart", f"Msg {i}")))
        self.assertTrue(library.is_full)
        self.assertFalse(library.add(SavedPostcard("card-21", 2000, "leo", "heart", "Msg 21")))
        self.assertEqual(library.count, 20)
        self.assertEqual(library.cards[-1].card_id, "card-0")

    def test_delete_card(self) -> None:
        library = PostcardLibrary([SavedPostcard("c1", 1000, "momo", "sun", "Hello")])
        self.assertTrue(library.delete("c1"))
        self.assertFalse(library.delete("c1"))


class StorageTests(unittest.TestCase):
    def test_version_one_postbox_loads_and_migrates_forward(self) -> None:
        raw = {
            "schema_version": 1,
            "cards": [
                {"id": "c1", "created_at": 1000, "recipient": "momo", "stamp": "star", "text": "Valid ☀️"},
                {"id": "c2", "created_at": 1001, "recipient": "unknown", "stamp": "star", "text": "Bad Recipient"},
                {"id": "c3", "created_at": 1002, "recipient": "leo", "stamp": "unknown", "text": "Bad Stamp"},
                {"id": "c4", "created_at": 1003, "recipient": "leo", "stamp": "star", "text": "A" * 100},
                {"id": "c5", "created_at": 1004, "recipient": "leo", "stamp": "star", "text": "Bad\x00Control"},
                {"id": "c1", "created_at": 1005, "recipient": "leo", "stamp": "star", "text": "Duplicate"},
                {"id": "c6", "created_at": 1006, "recipient": "pina", "stamp": "flower", "text": "Ciao Pina"},
            ],
        }
        storage = MemoryStorage(raw)
        repo = GreiaPostcardStorage(storage)
        library = repo.load()
        self.assertEqual([c.card_id for c in library.cards], ["c1", "c6"])
        legacy = library.get("c6")
        # The non-cast placeholder becomes Flash; the child's words are untouched.
        self.assertEqual(legacy.recipient_id, "flash")
        self.assertEqual(legacy.text, "Ciao Pina")
        self.assertEqual(legacy.front, CardFront.scene("forest"))
        self.assertEqual(library.get("c1").text, "Valid ☀️")
        self.assertTrue(repo.save(library))
        self.assertEqual(storage.value["schema_version"], 2)
        self.assertEqual(GreiaPostcardStorage(storage).load().get("c6").text, "Ciao Pina")

    def test_picture_card_round_trip_rollback_and_reclaim(self) -> None:
        storage = MemoryStorage()
        repo = GreiaPostcardStorage(storage)
        stickers = (PlacedSticker("puppy", 0.25, 0.7), PlacedSticker("heart", 0.8, 0.3))
        first = SavedPostcard("card-1-000001", 1, "lilli", "rainbow", "Ciao", CardFront.picture(), stickers)
        self.assertFalse(repo.save(PostcardLibrary([first])))  # a picture card needs its picture
        self.assertEqual(storage.files, {})
        self.assertTrue(repo.save(PostcardLibrary([first]), new_pictures={first.card_id: b"png-bytes"}))
        self.assertEqual(storage.files["postcards/card-1-000001.front.png"], b"png-bytes")
        self.assertEqual(storage.files["postcards/card-1-000001.txt"], "Ciao".encode("utf-8"))
        loaded = repo.load().get(first.card_id)
        self.assertEqual(loaded, first)
        self.assertEqual(repo.load_picture(first.card_id), b"png-bytes")

        second = SavedPostcard("card-2-000002", 2, "dani", "sun", "", CardFront.scene("space"))
        before_files, before_index = dict(storage.files), storage.value
        storage.fail_save = True
        self.assertFalse(repo.save(PostcardLibrary([second, first])))
        storage.fail_save = False
        self.assertEqual(storage.files, before_files)
        self.assertEqual(storage.value, before_index)

        self.assertTrue(repo.save(PostcardLibrary([second, first])))
        self.assertTrue(repo.save(PostcardLibrary([second])))
        self.assertNotIn("postcards/card-1-000001.front.png", storage.files)
        self.assertNotIn("postcards/card-1-000001.txt", storage.files)

    def test_unreadable_index_refuses_mutation(self) -> None:
        storage = MemoryStorage({"schema_version": 99, "cards": []})
        repo = GreiaPostcardStorage(storage)
        self.assertFalse(repo.save(PostcardLibrary([SavedPostcard("card-1", 1, "leo", "star", "x")])))
        self.assertEqual(storage.value["schema_version"], 99)

    def test_draft_survives_and_blank_drafts_are_not_saved(self) -> None:
        storage = MemoryStorage()
        repo = GreiaPostcardStorage(storage)
        self.assertTrue(repo.save_draft(PostcardDraft(), None))
        self.assertNotIn(DRAFT_KEY, storage.kv)
        draft = PostcardDraft(recipient_id="tito", front=CardFront.picture(), text="Ciao Tito 🦊")
        draft.add_sticker("sun")
        self.assertFalse(repo.save_draft(draft, None))  # picture fronts keep their picture
        self.assertTrue(repo.save_draft(draft, b"picture"))
        restored, picture = repo.load_draft()
        self.assertEqual((restored.recipient_id, restored.front, restored.text), ("tito", CardFront.picture(), "Ciao Tito 🦊"))
        self.assertEqual(restored.stickers, draft.stickers)
        self.assertEqual(picture, b"picture")
        repo.clear_draft()
        self.assertIsNone(repo.load_draft())
        self.assertNotIn("postcards/draft.front.png", storage.files)


class ManifestAndLocaleTests(unittest.TestCase):
    def test_manifest_matches_the_picture_postcard_experience(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["id"], "org.greia.posta-di-leo")
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])
        self.assertEqual(manifest["input"]["profile"], "hybrid")
        self.assertEqual(manifest["requirements"]["required_capabilities"], ["display", "pointer"])
        self.assertEqual(manifest["education"]["recommended_age_min"], 4)
        self.assertNotIn("recommended_age_max", manifest["education"])
        self.assertEqual(manifest["education"]["events"], [{"id": "postcard.created", "kind": "creation"}])
        self.assertEqual(set(manifest["creations"]["produces"]), {"image/png", "text/plain"})
        self.assertEqual(set(manifest["creations"]["consumes"]), {"image/png", "text/plain"})

    def test_four_locale_parity_and_friend_names(self) -> None:
        bundles = {
            locale: json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            for locale in ("en", "it", "es", "fr")
        }
        keys = set(bundles["en"]["strings"])
        for locale, bundle in bundles.items():
            with self.subTest(locale=locale):
                self.assertEqual(set(bundle["strings"]), keys)
        for friend in FRIENDS:
            self.assertIn(friend.name_key, keys)
        self.assertNotIn("friend.pina", keys)


def _app(*, library: PostcardLibrary | None = None, size=(1024, 600), creations=None, storage_backend=None, draft=None):
    from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
    from greia_platform.pygame_canvas import PygameReferenceCanvas
    from greia_platform.typography import GreiaTypography
    from postcard_app import PostcardActivity
    from postcard_audio import PostcardAudio

    screen = pygame.display.set_mode(size)
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    resources = LocalizedResources(ACTIVITY_ROOT, resolve_activity_locale("en", support))
    backend = storage_backend if storage_backend is not None else MemoryStorage()
    storage = GreiaPostcardStorage(backend)
    if library is not None:
        assert storage.save(library)
    events = _Events()
    now = [100.0]
    app = PostcardActivity(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        typography=GreiaTypography(),
        resources=resources,
        storage=storage,
        events=events,
        audio=PostcardAudio(locale="en"),
        rng=random.Random(7),
        creations=creations,
        draft=draft,
        clock=lambda: now[0],
        wall_clock=lambda: 1_700_000_000,
    )
    return app, now, events, backend


class _Events:
    def __init__(self) -> None:
        self.created: list[SavedPostcard] = []

    def postcard_created(self, card: SavedPostcard) -> None:
        self.created.append(card)


def _advance(app, now, seconds: float, step: float = 0.05) -> None:
    end = now[0] + seconds
    while now[0] < end:
        now[0] += step
        app.step_frame()
    app.render()


def _tap_control(app, control_id: str) -> None:
    rect = app.controls.layer.target(control_id).rect
    app.tap(rect.center)


class AppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    def test_pointer_round_from_friend_to_delivery_postbox_and_delete(self) -> None:
        from postcard_app import Screen

        app, now, events, backend = _app()
        app.render()
        self.assertEqual(app.step, "friend")
        _tap_control(app, "friend.lilli")
        self.assertEqual(app.draft.recipient_id, "lilli")
        _advance(app, now, 0.6)
        self.assertEqual(app.step, "picture")  # the next step opens by itself
        _tap_control(app, "scene.ocean")
        _advance(app, now, 0.6)
        self.assertEqual(app.step, "stickers")
        _tap_control(app, "sticker.puppy")
        _tap_control(app, "sticker.heart")
        self.assertEqual([s.sticker_id for s in app.draft.stickers], ["puppy", "heart"])
        _tap_control(app, "step.message")
        _advance(app, now, 0.4)
        for text in ("Ciao ", "Lilli ", "👩🏽‍🔬"):
            app.handle_event(pygame.event.Event(pygame.TEXTINPUT, text=text))
        _tap_control(app, "emoji.4")  # a picture-word for pre-readers
        self.assertEqual(app.draft.text, "Ciao Lilli 👩🏽‍🔬🌈")

        _tap_control(app, "send")
        self.assertEqual(app.state, Screen.SENDING)
        self.assertEqual(app.library.count, 1)
        card = app.library.cards[0]
        self.assertEqual((card.recipient_id, card.stamp_id, card.front), ("lilli", "rainbow", CardFront.scene("ocean")))
        self.assertEqual(backend.files[f"postcards/{card.card_id}.txt"], "Ciao Lilli 👩🏽‍🔬🌈".encode("utf-8"))
        self.assertEqual([c.card_id for c in events.created], [card.card_id])
        self.assertTrue(app.draft.is_blank)  # the next card starts fresh
        _advance(app, now, 2.4)
        self.assertEqual(app.state, Screen.DELIVERED)
        self.assertIn("voice.lilli", app.audio.played)
        self.assertEqual(app.friend_actor.character, "lilli")

        _tap_control(app, "delivered.mailbox")
        self.assertEqual(app.state, Screen.POSTBOX)
        _advance(app, now, 0.2)
        _tap_control(app, "card.0")
        self.assertEqual(app.state, Screen.CARD)
        _tap_control(app, "flip")
        self.assertTrue(app.card_back)
        _advance(app, now, 0.4)
        _tap_control(app, "card.delete")
        self.assertIsNotNone(app.sheet)
        app.tap(app.sheet.layer.target("delete.keep").rect.center)
        self.assertEqual(app.library.count, 1)  # back is the safe default
        _tap_control(app, "card.delete")
        app.tap(app.sheet.layer.target("delete.confirm").rect.center)
        self.assertEqual(app.library.count, 0)
        self.assertEqual(app.state, Screen.POSTBOX)
        self.assertEqual(backend.value["cards"], [])
        self.assertNotIn(f"postcards/{card.card_id}.txt", backend.files)

    def test_send_before_choosing_demonstrates_the_missing_step(self) -> None:
        from greia_platform.activity_feedback import CastPose
        from postcard_app import Screen

        app, now, events, _ = _app()
        _tap_control(app, "step.stickers")
        _advance(app, now, 0.3)
        _tap_control(app, "send")
        self.assertEqual(app.state, Screen.COMPOSER)
        self.assertEqual(app.host.feedback.pose, CastPose.THINK)
        self.assertEqual(app.step, "friend")
        self.assertIn("step.friend", app.motion.halos)
        self.assertEqual(app.library.count, 0)
        self.assertEqual(events.created, [])

    def test_idle_hint_points_to_the_next_choice(self) -> None:
        app, now, _, _ = _app()
        _advance(app, now, 6.5, step=0.25)
        self.assertTrue(app.host.pointing)
        self.assertIn("tray", app.motion.halos)

    def test_full_postbox_offers_a_sheet_and_never_evicts(self) -> None:
        from postcard_app import Screen

        library = PostcardLibrary([SavedPostcard(f"card-{i}", 1000 + i, "momo", "sun", f"msg {i}") for i in range(20)])
        draft = PostcardDraft(recipient_id="dani", front=CardFront.scene("snow"), text="Hi")
        app, now, events, backend = _app(library=library, draft=draft)
        _tap_control(app, "send")
        self.assertIsNotNone(app.sheet)
        self.assertEqual(app.library.count, 20)
        self.assertEqual(events.created, [])
        self.assertEqual(app.draft.text, "Hi")  # nothing is lost
        app.tap(app.sheet.layer.target("full.postbox").rect.center)
        self.assertEqual(app.state, Screen.POSTBOX)
        self.assertEqual(app._page_count(), 4)
        _tap_control(app, "page.next")
        self.assertEqual(app.postbox_page, 1)

    def test_keyboard_and_controller_make_and_send_a_card(self) -> None:
        from postcard_app import Screen

        app, now, events, _ = _app()
        app.press(pygame.K_DOWN)
        self.assertTrue(app.controls.layer.focus_visible)
        self.assertTrue(app.controls.layer.focused_id.startswith("friend."))
        app.press(pygame.K_SPACE, text=" ")
        self.assertIsNotNone(app.draft.recipient_id)
        _advance(app, now, 0.6)
        self.assertEqual(app.step, "picture")
        self.assertTrue(app.controls.layer.focused_id.startswith("scene."))
        # Controller: D-pad right, south (A) chooses the focused picture.
        right = pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=pygame.CONTROLLER_BUTTON_DPAD_RIGHT, instance_id=0)
        south = pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=pygame.CONTROLLER_BUTTON_A, instance_id=0)
        app.handle_event(right)
        app.handle_event(south)
        self.assertEqual(app.draft.front, CardFront.scene("ocean"))
        _advance(app, now, 0.6)
        self.assertEqual(app.step, "stickers")
        app.press(pygame.K_RETURN)  # first sticker
        self.assertEqual(len(app.draft.stickers), 1)
        app.controls.layer.focus("send", visible=True)
        app.press(pygame.K_RETURN)
        self.assertEqual(app.state, Screen.SENDING)
        self.assertEqual(len(events.created), 1)

    def test_writing_keeps_text_semantics_and_tab_reaches_controls(self) -> None:
        draft = PostcardDraft(recipient_id="momo", front=CardFront.scene("candy"))
        app, now, _, _ = _app(draft=draft)
        _tap_control(app, "step.message")
        _advance(app, now, 0.4)
        app.press(pygame.K_c, text="C")
        app.press(pygame.K_i, text="i")
        app.press(pygame.K_SPACE, text=" ")
        app.press(pygame.K_o, text="ò")
        self.assertEqual(app.draft.text, "Ci ò")  # Space typed a space, accents kept
        app.press(pygame.K_BACKSPACE)
        self.assertEqual(app.draft.text, "Ci ")
        app.press(pygame.K_TAB)
        self.assertTrue(app.toolbar_focus)
        app.press(pygame.K_SPACE, text=" ")  # activates the focused control, types nothing
        self.assertNotIn("  ", app.draft.text)
        app.press(pygame.K_ESCAPE)
        self.assertFalse(app.toolbar_focus)
        self.assertTrue(app._running)

    def test_navigation_keys_never_eat_the_first_typed_letter(self) -> None:
        draft = PostcardDraft(recipient_id="leo", front=CardFront.scene("space"))
        app, now, _, _ = _app(draft=draft)
        app.press(pygame.K_DOWN)  # consumed by the controls, no text follows
        _tap_control(app, "step.message")
        _advance(app, now, 0.4)
        app.press(pygame.K_c, text="C")
        self.assertEqual(app.draft.text, "C")

    def test_sticker_drag_moves_and_drag_off_the_card_removes(self) -> None:
        draft = PostcardDraft(recipient_id="tito", front=CardFront.scene("meadow"))
        app, now, _, _ = _app(draft=draft)
        _tap_control(app, "step.stickers")
        _advance(app, now, 0.3)
        _tap_control(app, "sticker.cake")
        placed = app.draft.stickers[0]
        start = app._sticker_centre(placed.x, placed.y)
        inner = app._card_inner()
        app.drag_to(start, (inner.left + inner.width // 2, inner.top + inner.height // 2))
        moved = app.draft.stickers[0]
        self.assertAlmostEqual(moved.x, 0.5, delta=0.02)
        self.assertAlmostEqual(moved.y, 0.5, delta=0.02)
        app.drag_to(app._sticker_centre(moved.x, moved.y), (1000, 300))
        self.assertEqual(app.draft.stickers, ())

    def test_unsent_card_survives_home(self) -> None:
        backend = MemoryStorage()
        app, now, _, _ = _app(storage_backend=backend)
        _tap_control(app, "friend.dani")
        app.shutdown()
        restored = GreiaPostcardStorage(backend).load_draft()
        self.assertIsNotNone(restored)
        self.assertEqual(restored[0].recipient_id, "dani")

    def test_every_screen_renders_clear_of_protected_chrome(self) -> None:
        from postcard_app import Screen

        library = PostcardLibrary([
            SavedPostcard(f"card-{i}", 1000 + i, ["leo", "flash"][i % 2], "star", "", CardFront.scene("castle"))
            for i in range(7)
        ])
        for size in ((1024, 600), (800, 480), (480, 320)):
            with self.subTest(size=size):
                app, now, _, _ = _app(library=library, size=size, draft=PostcardDraft(recipient_id="leo", front=CardFront.scene("space")))
                protected = app._layout_source.protected
                screens = [
                    lambda: None,
                    lambda: app._go_step("message"),
                    lambda: app._on_send(),
                    lambda: _advance(app, now, 2.4),
                    lambda: app.open_postbox(),
                    lambda: app.open_card(app.library.cards[0].card_id),
                ]
                for action in screens:
                    action()
                    app.render()
                    app.canvas.present()
                    for target in app.controls.layer.targets:
                        if getattr(target, "visible", True) and target.focusable:
                            self.assertFalse(target.rect.colliderect(protected), (size, app.state, target.control_id))
                self.assertEqual(app.state, Screen.CARD)


class SimulatorSupervisorTests(unittest.TestCase):
    def test_simulator_supervises_posta_di_leo(self) -> None:
        from simulator_supervision import supervise_builtin_activity

        supervise_builtin_activity(self, "org.greia.posta-di-leo")


if __name__ == "__main__":
    unittest.main()
