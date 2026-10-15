"""Teatrino delle Fiabe: content, model, art, layout and the real app loop."""
from __future__ import annotations

import json
import unittest

import pygame

from teatrino_doubles import ROOT, FakeMic, ManualClock, MemoryStorage, advance, make_app, record_show

from greia_platform.activity_api import get_shared_visual_path
from greia_platform.activity_controls import ControlLayout, KitPointer, PointerPhase
from greia_platform.pygame_canvas import PygameReferenceCanvas

from activities.teatrino_fiabe.teatrino_art import TeatrinoArt, opaque_bounds
from activities.teatrino_fiabe.teatrino_content import (
    FX,
    MAX_ON_STAGE,
    MAX_FRAMES,
    PRIVATE_PUPPETS,
    PUPPETS,
    SCENES,
    STAGE_FLOOR,
    STAGE_FRONT,
    ArtSource,
)
from activities.teatrino_fiabe.teatrino_controls import StageMode
from activities.teatrino_fiabe.teatrino_layout import TheatreLayout
from activities.teatrino_fiabe.teatrino_model import (
    MAX_TILT,
    Puppet,
    ShowPlayback,
    ShowRecorder,
    ShowRepository,
    Stage,
)

PACKAGE = ROOT / "activities" / "teatrino_fiabe"
CAST = ("lilli", "leo", "flash", "dani", "tito", "momo")


class ContentAndArtTests(unittest.TestCase):
    def test_cast_puppets_are_the_shared_canonical_characters(self) -> None:
        by_id = {spec.puppet_id: spec for spec in PUPPETS}
        for cast_id in CAST:
            spec = by_id[cast_id]
            self.assertEqual(spec.source, ArtSource.CAST)
            self.assertEqual(spec.asset_id, f"character.{cast_id}")
            self.assertFalse(spec.mirror, "front-facing cast is never mirrored")
            for variant in ("default", spec.talk, spec.cheer, spec.wave, spec.bow):
                self.assertTrue(get_shared_visual_path(spec.asset_id, variant=variant).is_file())
            # No private redraw of the cast may ship in the package.
            self.assertFalse((PACKAGE / "assets" / "source" / f"puppet_{cast_id}.svg").exists())
            self.assertFalse((PACKAGE / "assets" / "runtime" / f"puppet_{cast_id}.png").exists())

    def test_roster_ids_are_unique_and_keep_old_saved_show_ids(self) -> None:
        ids = [spec.puppet_id for spec in PUPPETS]
        self.assertEqual(len(ids), len(set(ids)))
        for legacy in ("principessa", "draghetto", "cavaliere", "bebe", "re", "lupetto", "orsetto", "sirenetta", "mago", "fatina"):
            self.assertIn(legacy, ids)

    def test_private_puppets_ship_source_and_rendition(self) -> None:
        for puppet_id in PRIVATE_PUPPETS:
            source = PACKAGE / "assets" / "source" / f"puppet_{puppet_id}.svg"
            runtime = PACKAGE / "assets" / "runtime" / f"puppet_{puppet_id}.png"
            self.assertTrue(source.is_file(), puppet_id)
            self.assertTrue(runtime.is_file(), puppet_id)
            text = source.read_text(encoding="utf-8")
            for forbidden in ("<image", "<text", "<filter", "<style", "<script"):
                self.assertNotIn(forbidden, text, puppet_id)
            self.assertLessEqual(len(text.encode()), 8 * 1024)

    def test_library_animals_scenes_stage_and_stickers_resolve(self) -> None:
        for spec in PUPPETS:
            if spec.source == ArtSource.LIBRARY:
                self.assertTrue(get_shared_visual_path(spec.asset_id).is_file(), spec.asset_id)
        for scene in SCENES:
            for layer in scene.layers:
                self.assertTrue(get_shared_visual_path(layer).is_file(), layer)
            for prop in scene.props:
                self.assertTrue(get_shared_visual_path(prop.asset_id).is_file(), prop.asset_id)
        for layer in (STAGE_FLOOR, *STAGE_FRONT):
            self.assertTrue(get_shared_visual_path(layer).is_file(), layer)
        for spec in FX:
            self.assertTrue(get_shared_visual_path(spec.picture, variant=spec.picture_variant).is_file(), spec.picture)
            self.assertTrue(get_shared_visual_path(f"fx.{spec.burst}").is_file(), spec.burst)

    def test_bundles_are_word_free_and_in_key_parity(self) -> None:
        keys = None
        for locale in ("en", "it", "es", "fr"):
            data = json.loads((PACKAGE / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], 1)
            strings = set(data["strings"])
            keys = strings if keys is None else keys
            self.assertEqual(strings, keys)
        self.assertEqual(keys, {"activity.title", "activity.description"})

    def test_puppet_look_drops_the_baked_shadow_and_keeps_one_frame(self) -> None:
        pygame.init()
        pygame.display.set_mode((64, 64))
        art = TeatrinoArt()
        look = art.look("lilli")
        assert look is not None
        neutral = look.frame(None)
        for variant in ("surprised", "pose_cheer", "pose_wave", "happy"):
            self.assertEqual(look.frame(variant).get_size(), neutral.get_size())
        # The shadow ellipse (14 % alpha) sits below the feet: nothing faint
        # remains under the lowest opaque row.
        bounds = opaque_bounds(neutral)
        self.assertLessEqual(neutral.get_height() - bounds.bottom, 4)
        self.assertTrue(0 < look.anchor[1] < look.rod_y <= neutral.get_height())
        ax, ay = look.posed("default", MAX_TILT, False)[1]
        self.assertTrue(abs(ax - look.anchor[0]) < 30 and abs(ay - look.anchor[1]) < 30)
        for puppet_id in ("principessa", "lupetto", "ranocchio"):
            other = art.look(puppet_id)
            assert other is not None
            # Every friend is scaled to the same body size (+/- the size tweak).
            self.assertLess(abs(other.half_height - look.half_height), 30, puppet_id)


class StageModelTests(unittest.TestCase):
    def test_one_of_each_and_at_most_six(self) -> None:
        stage = Stage()
        ids = [spec.puppet_id for spec in PUPPETS]
        for puppet_id in ids[:MAX_ON_STAGE]:
            self.assertIsNotNone(stage.add(puppet_id))
        self.assertTrue(stage.full)
        self.assertIsNone(stage.add(ids[MAX_ON_STAGE]))
        self.assertIsNone(stage.add(ids[0]))
        xs = sorted(p.x for p in stage.puppets)
        self.assertTrue(all(b - a > 40 for a, b in zip(xs, xs[1:])), "newcomers pop up at a free spot")

    def test_dragging_into_the_tray_is_the_remove_zone(self) -> None:
        stage = Stage()
        puppet = stage.add("leo")
        assert puppet is not None
        stage.move(puppet, puppet.x, 2000, allow_remove=True)
        self.assertTrue(stage.in_remove_zone(puppet))
        stage.move(puppet, puppet.x, 2000)
        self.assertFalse(stage.in_remove_zone(puppet), "a normal move stays on stage")

    def test_restore_ignores_unknown_and_duplicate_puppets(self) -> None:
        stage = Stage()
        stage.restore([{"id": "lilli", "x": 300, "y": 300}, {"id": "lilli"}, {"id": "ghost"}, "junk"], {"lilli"})
        self.assertEqual(stage.ids(), ("lilli",))

    def test_gestures_are_time_based_and_lean_within_the_cast_rule(self) -> None:
        puppet = Puppet("bebe", 400, 260)
        puppet.speak()
        puppet.jump()
        flaps = set()
        for _ in range(12):
            puppet.update(1 / 30)
            flaps.add(puppet.mouth_open)
        self.assertEqual(flaps, {True, False}, "the mouth flaps while talking")
        self.assertGreater(puppet.jump_offset(), 0)
        puppet.x += 80
        puppet.update(1 / 30)
        self.assertLessEqual(abs(puppet.tilt), MAX_TILT)
        for _ in range(90):
            puppet.update(1 / 30)
        self.assertFalse(puppet.talking or puppet.jumping)

    def test_recorder_is_bounded_and_playback_interpolates(self) -> None:
        stage = Stage()
        puppet = stage.add("tito", x=300)
        assert puppet is not None
        recorder = ShowRecorder()
        recorder.start(0.0)
        t = 0.0
        while t < 120.0:  # far longer than a show: frames stay bounded
            puppet.x = 300 + (t % 10) * 10
            recorder.sample(t, stage)
            recorder.note_sfx(t, "boing")
            t += 1 / 30
        self.assertLessEqual(len(recorder.frames), MAX_FRAMES)
        self.assertLessEqual(len(recorder.sfx), 240)
        frames = [
            {"t": 0.0, "puppets": [{"id": "tito", "x": 200, "y": 300, "flip": False, "jumping": False, "talking": False}]},
            {"t": 1.0, "puppets": [{"id": "tito", "x": 400, "y": 300, "flip": False, "jumping": True, "talking": True}]},
        ]
        playback = ShowPlayback(frames, [{"t": 0.5, "sound": "magic"}], 1.0)
        middle = playback.poses_at(0.5)[0]
        self.assertAlmostEqual(middle.x, 300, delta=1)
        target = Stage()
        self.assertEqual(playback.drive(target, 0.6, {"tito"}), ["magic"])
        self.assertEqual(target.ids(), ("tito",))
        self.assertTrue(playback.finished(1.0))

    def test_old_shows_with_two_of_the_same_puppet_still_play(self) -> None:
        frames = [{"t": 0.0, "puppets": [{"id": "lilli", "x": 300, "y": 300}, {"id": "lilli", "x": 600, "y": 300}]}]
        playback = ShowPlayback(frames, [], 2.0)
        self.assertEqual(len(playback.poses_at(0.1)), 2)
        stage = Stage()
        playback.drive(stage, 0.1, {"lilli"})
        self.assertEqual(stage.ids(), ("lilli",))

    def test_repository_round_trip_keeps_the_poster_line_up(self) -> None:
        repo = ShowRepository(MemoryStorage())
        meta = repo.save_show(
            "forest", [{"id": "re"}], [], [{"t": 0.5, "sound": "trumpet"}], 3.0, b"RIFFWAVE",
            poster=[{"id": "re", "x": 400, "y": 300, "flip": True}],
        )
        listed = repo.list_shows()[0]
        self.assertEqual(listed["poster"], [{"id": "re", "x": 400.0, "y": 300.0, "flip": True}])
        data, wav = repo.load_show(meta["id"])
        self.assertEqual(wav, b"RIFFWAVE")
        self.assertEqual(data["sfx_events"][0]["sound"], "trumpet")
        repo.delete_show(meta["id"])
        self.assertEqual(repo.list_shows(), [])


class LayoutTests(unittest.TestCase):
    def test_controls_stay_clear_of_home_back_and_touch_sized(self) -> None:
        pygame.init()
        for size in ((1024, 600), (800, 480), (480, 320), (1280, 800)):
            with self.subTest(size=size):
                canvas = PygameReferenceCanvas(pygame.Surface(size))
                control = ControlLayout.for_canvas(canvas, size)
                layout = TheatreLayout.build(control)
                rects = [layout.shows, layout.scene, layout.clear, layout.mic, layout.rec, *layout.fx,
                         layout.tray_prev, layout.tray_next, *layout.cards]
                screen = pygame.Rect(0, 0, 1024, 600)
                for rect in rects:
                    self.assertFalse(rect.colliderect(control.protected), rect)
                    self.assertTrue(screen.contains(rect), rect)
                    self.assertGreaterEqual(min(rect.size) * control.scale, 39.5, rect)
                for index, rect in enumerate(rects):
                    for other in rects[index + 1:]:
                        self.assertFalse(rect.colliderect(other), (rect, other))
                self.assertLess(layout.bounds.bottom, layout.tray.top)


class AppLoopTests(unittest.TestCase):
    def test_a_whole_show_from_staging_to_watching_it_again(self) -> None:
        events: list = []
        storage = MemoryStorage()
        app = make_app(storage=storage, events=events)
        app.render()
        app.tap(app.controls.cards[1].rect.center)  # Leo pops up on stage
        self.assertIn("leo", app.stage.ids())
        app.tap(app.controls.fx[0].rect.center)  # a trumpet before recording: not saved
        meta = record_show(app, seconds=2.0)
        self.assertIsNotNone(meta)
        self.assertEqual(app.mode, StageMode.EDIT)
        self.assertEqual(app.top_sheet, "teatrino.call", "the curtain call follows a saved show")
        self.assertEqual(events[-1][0], "story.recorded")
        saved = app.show_repo.list_shows()
        self.assertEqual(len(saved), 1)
        self.assertEqual({item["id"] for item in saved[0]["poster"]}, set(app.stage.ids()))
        self.assertEqual(app.host.said[:2], ["ready.go", "celebrate.success"])
        app.render()
        line_up = app.stage.snapshot()

        watch = app.surfaces.overlays[-1].layer.target("call.watch")
        app.tap(watch.rect.center)
        self.assertEqual(app.mode, StageMode.WATCHING)
        advance(app, 4.0, render=True)
        self.assertEqual(app.top_sheet, "teatrino.call", "the end of a show brings the curtain call back")
        self.assertIn("story.played", [event for event, _kwargs in events])
        done = app.surfaces.overlays[-1].layer.target("call.done")
        app.tap(done.rect.center)
        advance(app, 1.0)
        self.assertEqual(app.mode, StageMode.EDIT)
        self.assertEqual(app.stage.snapshot(), line_up, "watching never changes the child's staging")

    def test_a_full_stage_wobbles_instead_of_adding(self) -> None:
        app = make_app()
        app.stage.clear()
        for page in range(3):
            for card in app.controls.cards:
                if card.visible:
                    app.tap(card.rect.center)
            app.tap(app.controls.tray_next.rect.center)
        self.assertEqual(len(app.stage.puppets), MAX_ON_STAGE)
        self.assertIn("full", app.sound_mgr.played)

    def test_a_card_tap_never_removes_and_a_drag_into_the_tray_does(self) -> None:
        app = make_app()
        lilli = app.stage.find("lilli")
        assert lilli is not None
        app.tap(app.controls.cards[0].rect.center)
        self.assertIn("lilli", app.stage.ids())
        start = (int(lilli.x), int(lilli.y))
        app.drag(start, (start[0], app.layout.tray.top + 40))
        self.assertNotIn("lilli", app.stage.ids())
        self.assertFalse(app.controls.cards[0].selected)

    def test_tapping_a_puppet_makes_it_bow_and_talk(self) -> None:
        app = make_app()
        lilli = app.stage.find("lilli")
        assert lilli is not None
        app.tap((int(lilli.x), int(lilli.y)))
        self.assertTrue(lilli.talking)
        self.assertGreater(lilli.bow_timer, 0)

    def test_keyboard_picks_up_moves_and_puts_back_a_puppet(self) -> None:
        app = make_app()
        app.controls.layer.focus("puppet.lilli", visible=True)
        app.press(pygame.K_RETURN)
        self.assertTrue(app.key_grab)
        lilli = app.stage.find("lilli")
        assert lilli is not None
        x0 = lilli.x
        app.press(pygame.K_RIGHT)
        self.assertGreater(lilli.x, x0)
        for _ in range(20):
            app.press(pygame.K_DOWN)
        app.press(pygame.K_SPACE)
        self.assertNotIn("lilli", app.stage.ids(), "moved down into the tray: back in the box")

    def test_the_held_puppet_mouths_along_with_the_childs_voice(self) -> None:
        app = make_app()
        lilli = app.stage.find("lilli")
        assert lilli is not None
        app.tap((int(lilli.x), int(lilli.y)))
        app.tap(app.layout.rec.center)
        advance(app, 3.0)
        mic: FakeMic = app.mic_recorder  # type: ignore[assignment]
        mic.current_volume = 0.6
        advance(app, 0.2)
        self.assertTrue(lilli.voice_talking)
        self.assertFalse(app.stage.find("draghetto").voice_talking)
        mic.current_volume = 0.0
        advance(app, 0.2)
        self.assertFalse(lilli.voice_talking)

    def test_idle_hint_glows_the_tray_then_the_record_button(self) -> None:
        app = make_app()
        self.assertIsNone(app._hint_target(app.clock()))
        advance(app, 9.0)
        self.assertEqual(app._hint_target(app.clock()), app.layout.rec)
        app.stage.clear()
        self.assertTrue(app._hint_target(app.clock()).colliderect(app.controls.cards[0].rect))
        app.tap(app.controls.cards[2].rect.center)
        self.assertIsNone(app._hint_target(app.clock()))

    def test_staging_is_remembered_between_visits(self) -> None:
        storage = MemoryStorage()
        app = make_app(storage=storage)
        app.tap(app.controls.cards[3].rect.center)
        app.shutdown()
        again = make_app(storage=storage)
        self.assertIn("dani", again.stage.ids())

    def test_sheets_and_viewports_render(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320)):
            with self.subTest(size=size):
                app = make_app(size=size)
                record_show(app, 1.0)
                app.render()
                app.tap(app.surfaces.overlays[-1].layer.target("call.done").rect.center)
                app.tap(app.layout.shows.center)
                self.assertEqual(app.top_sheet, "teatrino.library")
                app.render()
                app.press(pygame.K_ESCAPE)
                app.tap(app.layout.scene.center)
                self.assertEqual(app.top_sheet, "teatrino.scenes")
                app.render()
                app.press(pygame.K_ESCAPE)
                app.tap(app.layout.mic.center)
                self.assertEqual(app.top_sheet, "teatrino.voice")
                app.render()
                app.canvas.present()

    def test_choosing_a_scene_and_no_voice(self) -> None:
        app = make_app()
        app.tap(app.layout.scene.center)
        night = app.surfaces.overlays[-1].layer.target("scene.night")
        app.tap(night.rect.center)
        self.assertEqual(app.scene_id, "night")
        self.assertEqual(app.top_sheet, "")
        app.tap(app.layout.mic.center)
        app.tap(app.surfaces.overlays[-1].layer.target("voice.off").rect.center)
        self.assertFalse(app.mic_recorder.enabled)
        self.assertEqual(app.voice.state, "off")

    def test_escape_while_recording_saves_and_quit_never_saves_a_half_show(self) -> None:
        app = make_app()
        app.tap(app.layout.rec.center)
        advance(app, 3.0)
        app.press(pygame.K_ESCAPE)
        self.assertEqual(len(app.show_repo.list_shows()), 1)
        other = make_app()
        other.tap(other.layout.rec.center)
        advance(other, 3.0)
        other.shutdown()
        self.assertEqual(other.show_repo.list_shows(), [])
        self.assertEqual(other.mic_recorder.stopped, 1, "the microphone is always closed")


class PointerInputTests(unittest.TestCase):
    def test_pointer_moves_reach_the_kit_and_drags_follow(self) -> None:
        app = make_app(clock=ManualClock())
        lilli = app.stage.find("lilli")
        assert lilli is not None
        app._dispatch(KitPointer(PointerPhase.DOWN, (int(lilli.x), int(lilli.y))))
        self.assertTrue(lilli.held)
        app._dispatch(KitPointer(PointerPhase.MOVE, (int(lilli.x) + 60, int(lilli.y))))
        self.assertGreater(lilli.x, 300)
        app._dispatch(KitPointer(PointerPhase.UP, (int(lilli.x), int(lilli.y))))
        self.assertFalse(lilli.held)


if __name__ == "__main__":
    unittest.main()
