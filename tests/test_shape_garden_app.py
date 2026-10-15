"""Shape Garden app loop: drag/drop, keyboard carry, ghosts, library and chrome.

Runs the real ``GardenApp`` on a dummy SDL display with an in-memory store,
a fake clock and silent sounds.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from activities.shape_garden import garden_app
from activities.shape_garden.garden_app import GardenApp
from activities.shape_garden.garden_content import (
    GARDEN_VIEW,
    INDEX_KEY,
    LEGACY_STORAGE_KEY,
    MAX_SHAPES,
    SHAPE_KINDS,
    ghost_picture,
)
from activities.shape_garden.garden_project_repository import GardenProjectRepository
from greia_platform.activity_controls import ControlLayout
from greia_platform.pygame_canvas import PygameReferenceCanvas



class MemoryStorage:
    def __init__(self):
        self.kv = {}
        self.files = {}

    def kv_get(self, key, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        self.kv[key] = value

    def kv_delete(self, key):
        return self.kv.pop(key, None) is not None

    def file_write_atomic(self, name, payload):
        self.files[name] = bytes(payload)

    def file_read(self, name):
        if name not in self.files:
            raise RuntimeError("missing")
        return self.files[name]

    def file_list(self, prefix=None):
        return tuple(sorted(n for n in self.files if not prefix or n.startswith(prefix)))

    def file_delete(self, name):
        return self.files.pop(name, None) is not None


class SilentSounds:
    def __init__(self):
        self.played = []
        self.spoken = []

    def play(self, name):
        self.played.append(name)

    def pop(self, kind):
        self.played.append(f"pop.{kind}")

    def say(self, cue):
        self.spoken.append(cue)


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def make_app(size=(1024, 600), storage=None, creations=None):
    pygame.init()
    screen = pygame.display.set_mode(size)
    clock = Clock()
    storage = storage if storage is not None else MemoryStorage()
    app = GardenApp(
        screen,
        repository=GardenProjectRepository(storage),
        creations=creations,
        sounds=SilentSounds(),
        clock=clock,
    )
    return app, storage, clock


def physical(app, point):
    x, y = app.canvas.mapper.transform.logical_to_physical(point)
    return int(round(x)), int(round(y))


def tray(app, kind):
    return physical(app, app.renderer.tray_tiles()[SHAPE_KINDS.index(kind)].center)


def garden(app, point):
    return physical(app, app.renderer.to_screen(point))


def key(app, code):
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=code, mod=0, unicode="", scancode=0))


class GardenAppTests(unittest.TestCase):
    def tearDown(self):
        pygame.quit()

    def test_first_screen_invites_with_dani_and_a_hopping_tray(self):
        app, _storage, clock = make_app()
        self.assertEqual(app.editor.shapes, ())
        clock.now += 1.5
        app._step_frame()
        self.assertEqual(app.cast.pose, "point")
        self.assertEqual(app.sounds.spoken, ["ready.go"])
        self.assertAlmostEqual(app._tray_hint_start, clock.now)
        app._draw()  # tray wave + drag hand render without error
        clock.now += 7
        app._step_frame()
        self.assertEqual(app.sounds.spoken, ["ready.go"])  # spoken once, then pictorial

    def test_drag_from_tray_plants_where_dropped_and_tap_plants_in_a_free_spot(self):
        app, _storage, _clock = make_app()
        app.drag(tray(app, "star"), garden(app, (300, 200)))
        shape = app.editor.shapes[-1]
        self.assertEqual(shape.kind, "star")
        self.assertLess(abs(shape.x - 300) + abs(shape.y - 200), 6)
        app.tap(tray(app, "heart"))
        self.assertEqual([s.kind for s in app.editor.shapes], ["star", "heart"])
        self.assertIn("pop.heart", app.sounds.played)
        self.assertFalse(app.carrying)  # pointer taps never enter carry mode

    def test_drop_outside_the_garden_plants_nothing(self):
        app, _storage, _clock = make_app()
        app.drag(tray(app, "oval"), tray(app, "diamond"))
        self.assertEqual(app.editor.shapes, ())

    def test_move_resize_turn_recolour_layer_bin_and_undo(self):
        app, _storage, _clock = make_app()
        app.drag(tray(app, "square"), garden(app, (300, 300)))
        app.drag(tray(app, "circle"), garden(app, (700, 300)))
        app.drag(garden(app, (300, 300)), garden(app, (500, 250)))
        moved = app.editor.shapes[-1]
        self.assertEqual(moved.kind, "square")
        self.assertLess(abs(moved.x - 500) + abs(moved.y - 250), 6)
        for name in ("grow", "turn"):
            app.controls.tools[name].activate()
        app.controls.pots[5].activate()  # ocean
        self.assertEqual(app.editor.selected_shape.colour, "ocean")
        self.assertEqual((app.editor.selected_shape.size, app.editor.selected_shape.turn), (3, 1))
        app.controls.tools["back"].activate()
        self.assertEqual(app.editor.shapes[0].kind, "square")
        app.drag(garden(app, (700, 300)), physical(app, app.renderer.bin_rect().center))
        self.assertEqual([s.kind for s in app.editor.shapes], ["square"])
        self.assertIn("swish", app.sounds.played)
        app.controls.undo.activate()
        self.assertEqual(len(app.editor.shapes), 2)

    def test_keyboard_plants_carries_and_puts_down(self):
        app, _storage, _clock = make_app()
        layer = app.controls.layer
        layer.focus("tray.triangle", visible=True)
        key(app, pygame.K_SPACE)
        self.assertTrue(app.carrying)
        start = app.editor.selected_shape
        key(app, pygame.K_RIGHT)
        key(app, pygame.K_UP)
        key(app, pygame.K_SPACE)
        self.assertFalse(app.carrying)
        shape = app.editor.selected_shape
        self.assertEqual((shape.x - start.x, shape.y - start.y), (24, -24))
        self.assertEqual(layer.focused_id, f"shape.{app.editor.selected}")
        # Space on a focused shape picks it up again; Escape puts it down.
        key(app, pygame.K_SPACE)
        self.assertTrue(app.carrying)
        key(app, pygame.K_ESCAPE)
        self.assertFalse(app.carrying)
        self.assertTrue(app.running)

    def test_controller_stick_pointer_drags_a_shape(self):
        axis_event = getattr(pygame, "CONTROLLERAXISMOTION", None)
        if axis_event is None:
            self.skipTest("SDL controller events unavailable")
        app, _storage, clock = make_app()
        app.drag(tray(app, "rectangle"), garden(app, (512, 300)))
        # The virtual pointer starts at the garden centre, on the rectangle.
        app.handle_event(pygame.event.Event(axis_event, axis=pygame.CONTROLLER_AXIS_LEFTX, value=30000, instance_id=0))
        self.assertTrue(app.controller_pointer.active)
        app.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=pygame.CONTROLLER_BUTTON_A, instance_id=0))
        for _ in range(4):
            clock.now += 0.1
            app._step_frame()
        self.assertTrue(app.editor.dragging)
        app.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONUP, button=pygame.CONTROLLER_BUTTON_A, instance_id=0))
        self.assertFalse(app.editor.dragging)
        self.assertGreater(app.editor.shapes[-1].x, 540)
        app._draw()  # virtual pointer drawn by the Activity, platform pointer off

    def test_ghost_picture_snaps_and_completion_cheers_once(self):
        app, _storage, clock = make_app()
        app._choose_ghost("flower")
        picture = ghost_picture("flower")
        for slot in picture.slots:
            app.drag(tray(app, slot.kind), garden(app, (slot.x + 14, slot.y - 10)))
        self.assertTrue(app.editor.ghost_complete())
        self.assertEqual(app.sounds.spoken.count("celebrate.success"), 1)
        self.assertEqual(app.cast.pose, "cheer")
        self.assertIn("snap", app.sounds.played)
        app._draw()

    def test_blank_garden_is_never_saved_and_new_reuses_it(self):
        app, storage, clock = make_app()
        clock.now += 5
        app._step_frame()
        app.controls.new.activate()
        self.assertTrue(app._save())
        self.assertNotIn(INDEX_KEY, storage.kv)
        self.assertFalse(any(key.startswith("shape_garden.garden.") for key in storage.kv))
        app.drag(tray(app, "circle"), garden(app, (200, 200)))
        clock.now += 2
        app._step_frame()
        self.assertEqual(len(storage.kv[INDEX_KEY]["gardens"]), 1)
        app.controls.new.activate()
        app.controls.new.activate()
        self.assertEqual(len(storage.kv[INDEX_KEY]["gardens"]), 1)
        self.assertTrue(app.state.blank)

    def test_gardens_reopen_newest_first_and_delete_is_deliberate(self):
        app, storage, clock = make_app()
        app.drag(tray(app, "circle"), garden(app, (200, 200)))
        app.controls.new.activate()
        app.drag(tray(app, "star"), garden(app, (400, 200)))
        app.controls.gallery.activate()
        self.assertEqual(app.mode, "gallery")
        self.assertEqual(len(app.records), 2)
        app._draw()
        app._ask_delete_index(1)
        sheet = app.surfaces.overlays[-1]
        self.assertEqual(sheet.layer.focused_id, "delete.cancel")
        key(app, pygame.K_SPACE)  # back is the default: nothing deleted
        self.assertEqual(len(GardenProjectRepository(storage).list_records()), 2)
        app._ask_delete_index(1)
        app.surfaces.overlays[-1].layer.target("delete.confirm").activate()
        self.assertEqual(len(GardenProjectRepository(storage).list_records()), 1)
        # A restart opens the newest garden with its shapes.
        pygame.quit()
        again, _storage, _clock = make_app(storage=storage)
        self.assertEqual([s.kind for s in again.editor.shapes], ["star"])

    def test_v1_project_opens_as_an_editable_garden(self):
        storage = MemoryStorage()
        storage.kv[LEGACY_STORAGE_KEY] = {
            "schema_version": 1,
            "stamps": [{"x": 300, "y": 200, "size": 30, "kind": 2, "color": 1}],
        }
        app, storage, _clock = make_app(storage=storage)
        self.assertEqual([(s.kind, s.colour) for s in app.editor.shapes], [("star", "sunshine")])
        self.assertIn(LEGACY_STORAGE_KEY, storage.kv)

    def test_full_garden_dims_tray_and_keeps_every_shape(self):
        app, _storage, _clock = make_app()
        for index in range(MAX_SHAPES):
            app._plant(SHAPE_KINDS[index % 8], (100 + index * 5, 300))
        self.assertTrue(all(not tile.enabled for tile in app.controls.tray))
        self.assertFalse(app._plant("circle", (500, 300)))
        self.assertEqual(len(app.editor.shapes), MAX_SHAPES)
        app._draw()

    def test_backdrop_sheet_changes_scene_and_controls_stay_off_protected_chrome(self):
        for size in ((1024, 600), (800, 480), (480, 320)):
            with self.subTest(size=size):
                app, _storage, _clock = make_app(size)
                layout = ControlLayout.for_canvas(PygameReferenceCanvas(app.screen), size)
                for target in app.controls.layer.targets:
                    self.assertFalse(target.rect.colliderect(layout.protected), target.control_id)
                self.assertFalse(pygame.Rect(GARDEN_VIEW).colliderect(layout.protected))
                app.controls.backdrop.activate()
                sheet = app.surfaces.overlays[-1]
                sheet.layer.target("backdrop.snow").activate()
                self.assertEqual(app.state.backdrop, "snow")
                self.assertEqual(app.surfaces.overlays, ())
                pygame.quit()

    def test_run_loop_plays_a_garden_and_saves_on_exit(self):
        app, storage, clock = make_app()
        start = tray(app, "triangle")
        end = garden(app, (512, 260))
        events = [
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start, button=1),
            pygame.event.Event(pygame.MOUSEMOTION, pos=((start[0] + end[0]) // 2, (start[1] + end[1]) // 2), rel=(0, 0), buttons=(1, 0, 0)),
            pygame.event.Event(pygame.MOUSEMOTION, pos=end, rel=(0, 0), buttons=(1, 0, 0)),
            pygame.event.Event(pygame.MOUSEBUTTONUP, pos=end, button=1),
        ]
        frames = {"n": 0}

        def stop():
            frames["n"] += 1
            clock.now += 0.05
            if frames["n"] == 2:
                for event in events:
                    pygame.event.post(event)
            return frames["n"] > 6

        presented = []
        original = app.canvas.present

        def present(**kwargs):
            presented.append(kwargs)
            return original(**kwargs)

        app.canvas.present = present
        with mock.patch.object(garden_app, "activity_stop_requested", side_effect=stop), \
                mock.patch.object(garden_app, "mark_activity_ready") as ready:
            self.assertEqual(app.run(), 0)
        ready.assert_called_once()
        self.assertTrue(presented and all(call.get("pointer", True) for call in presented))
        records = GardenProjectRepository(storage).list_records()
        self.assertEqual(len(records), 1)
        saved = GardenProjectRepository(storage).load(records[0].garden_id)
        self.assertEqual([s.kind for s in saved.state.shapes], ["triangle"])


if __name__ == "__main__":
    unittest.main()
