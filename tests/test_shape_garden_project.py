"""Shape Garden composition model, save format, library and v1 migration (no display)."""
from __future__ import annotations

import hashlib
import unittest

from activities.shape_garden.garden_content import (
    GARDEN_HEIGHT,
    GARDEN_WIDTH,
    INDEX_KEY,
    LEGACY_STORAGE_KEY,
    MAX_GARDENS,
    MAX_SHAPES,
    MAX_UNDO,
    SIZE_LEVELS,
    ghost_picture,
)
from activities.shape_garden.garden_model import GardenEditor, GardenState, PlacedShape, snap_slot
from activities.shape_garden.garden_project_model import GardenProject, legacy_state
from activities.shape_garden.garden_project_repository import (
    GardenProjectError,
    GardenProjectRepository,
)


class MemoryStorage:
    def __init__(self):
        self.kv = {}
        self.files = {}
        self.fail_kv = False

    def kv_get(self, key, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        if self.fail_kv:
            raise RuntimeError("kv failed")
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


class GardenEditorTests(unittest.TestCase):
    def test_plant_is_chosen_named_shape_selected_on_top(self):
        editor = GardenEditor()
        self.assertTrue(editor.plant("triangle", "leaf", (300, 200)))
        self.assertTrue(editor.plant("heart", "natural", (310, 210)))
        self.assertEqual([s.kind for s in editor.shapes], ["triangle", "heart"])
        self.assertEqual(editor.selected, 1)
        self.assertEqual(editor.shapes[0], PlacedShape("triangle", "leaf", 300, 200))

    def test_points_are_clamped_into_the_garden(self):
        editor = GardenEditor()
        editor.plant("circle", "coral", (-50, 5000))
        shape = editor.shapes[0]
        self.assertEqual((shape.x, shape.y), (0, GARDEN_HEIGHT))
        with self.assertRaises(ValueError):
            PlacedShape("pentagon", "coral", 1, 1)
        with self.assertRaises(ValueError):
            PlacedShape("circle", "coral", GARDEN_WIDTH + 1, 1)

    def test_resize_turn_recolour_and_layer_are_undoable_steps(self):
        editor = GardenEditor()
        editor.plant("square", "ocean", (100, 100))
        editor.plant("circle", "coral", (120, 120))
        self.assertTrue(editor.resize(1))
        self.assertTrue(editor.rotate())
        self.assertTrue(editor.recolour("grape"))
        self.assertTrue(editor.send_back())
        self.assertEqual(editor.shapes[0].kind, "circle")
        self.assertEqual(editor.selected, 0)
        top = editor.shapes[0]
        self.assertEqual((top.size, top.turn, top.colour), (3, 1, "grape"))
        for _ in range(4):
            self.assertTrue(editor.undo())
        self.assertEqual(editor.shapes[1], PlacedShape("circle", "coral", 120, 120))

    def test_size_steps_are_bounded(self):
        editor = GardenEditor()
        editor.plant("star", "sunshine", (500, 300))
        for _ in range(10):
            editor.resize(1)
        self.assertEqual(editor.selected_shape.size, len(SIZE_LEVELS) - 1)
        for _ in range(10):
            editor.resize(-1)
        self.assertEqual(editor.selected_shape.size, 0)

    def test_drag_is_one_undo_step_and_lifts_to_top(self):
        editor = GardenEditor()
        editor.plant("square", "ocean", (100, 100))
        editor.plant("circle", "coral", (400, 300))
        editor.begin_drag(0)
        self.assertEqual(editor.shapes[-1].kind, "square")
        for x in range(110, 300, 20):
            editor.drag_to((x, 150))
        editor.end_drag()
        self.assertEqual((editor.shapes[-1].x, editor.shapes[-1].y), (290, 150))
        editor.undo()
        self.assertEqual([s.kind for s in editor.shapes], ["square", "circle"])
        self.assertEqual(editor.shapes[0].x, 100)

    def test_drop_in_bin_removes_and_undo_restores(self):
        editor = GardenEditor()
        editor.plant("heart", "coral", (100, 100))
        editor.begin_drag(0)
        editor.drag_to((900, 590))
        self.assertTrue(editor.cancel_drag_into_bin())
        self.assertEqual(editor.shapes, ())
        editor.undo()
        self.assertEqual(editor.shapes[0].x, 100)

    def test_undo_history_is_bounded(self):
        editor = GardenEditor()
        for index in range(MAX_UNDO + 10):
            editor.plant("circle", "coral", (index, 10))
        undone = 0
        while editor.undo():
            undone += 1
        self.assertEqual(undone, MAX_UNDO)
        self.assertEqual(len(editor.shapes), 10)

    def test_full_garden_refuses_without_evicting(self):
        editor = GardenEditor()
        for index in range(MAX_SHAPES):
            self.assertTrue(editor.plant("circle", "coral", (index, 10)))
        first = editor.shapes[0]
        self.assertFalse(editor.plant("star", "coral", (500, 300)))
        self.assertEqual(len(editor.shapes), MAX_SHAPES)
        self.assertIs(editor.shapes[0], first)

    def test_ghost_slot_snaps_matching_shape_and_completion_is_derived(self):
        editor = GardenEditor()
        editor.set_ghost("house")
        picture = ghost_picture("house")
        roof = picture.slots[1]
        # A wrong shape near the slot does not snap: no failure, just free play.
        self.assertIs(editor.plant("circle", "coral", (roof.x + 10, roof.y)), True)
        snapped = editor.plant("triangle", "coral", (roof.x + 30, roof.y - 20))
        self.assertEqual(snapped, roof)
        self.assertEqual(editor.selected_shape.box, SIZE_LEVELS[roof.size])
        for slot in picture.slots:
            editor.plant(slot.kind, "leaf", (slot.x + 12, slot.y + 8))
        self.assertTrue(editor.ghost_complete())
        editor.undo()
        self.assertFalse(editor.ghost_complete())

    def test_snapped_pieces_stack_in_picture_order(self):
        editor = GardenEditor()
        editor.set_ghost("house")
        picture = ghost_picture("house")
        wall, roof, door = picture.slots[0], picture.slots[1], picture.slots[2]
        editor.plant("rectangle", "sunshine", (door.x, door.y))
        editor.plant("circle", "coral", (900, 100))
        editor.plant("square", "coral", (wall.x, wall.y))
        kinds = [s.kind for s in editor.shapes]
        self.assertLess(kinds.index("square"), kinds.index("rectangle"))
        self.assertEqual(kinds.index("circle"), 1)  # free shapes keep their layer
        self.assertEqual(editor.selected_shape.kind, "square")
        self.assertIsNone(snap_slot(PlacedShape("triangle", "coral", 10, 10), picture))
        self.assertEqual(snap_slot(PlacedShape("triangle", "coral", roof.x, roof.y), picture), roof)

    def test_blank_state_means_nothing_made(self):
        self.assertTrue(GardenState().blank)
        self.assertFalse(GardenState((PlacedShape("oval", "leaf", 1, 1),)).blank)
        self.assertFalse(GardenState((), "picture", "a" * 64).blank)
        with self.assertRaises(ValueError):
            GardenState((), "picture", None)
        with self.assertRaises(ValueError):
            GardenState((), "volcano")


class SaveFormatTests(unittest.TestCase):
    def test_round_trip_by_name(self):
        state = GardenState((PlacedShape("diamond", "grape", 10, 20, 4, 3),), "night", None)
        raw = GardenProject(state, "rocket").as_raw()
        self.assertEqual(raw["shapes"], [["diamond", "grape", 10, 20, 4, 3]])
        self.assertEqual(GardenProject.from_raw(raw), GardenProject(state, "rocket"))

    def test_invalid_records_fail_closed_and_retired_ghost_is_dropped(self):
        good = GardenProject(GardenState((PlacedShape("star", "leaf", 1, 1),))).as_raw()
        for broken in (
            {**good, "schema": 1},
            {**good, "shapes": [["star", "leaf", 1, 1, 99, 0]]},
            {**good, "shapes": [["star", "leaf", 1]]},
            {**good, "backdrop": "lava"},
            {**good, "shapes": "nope"},
            None,
        ):
            with self.assertRaises(ValueError):
                GardenProject.from_raw(broken)
        self.assertIsNone(GardenProject.from_raw({**good, "ghost": "unicorn"}).ghost)

    def test_v1_project_maps_to_named_shapes(self):
        digest = hashlib.sha256(b"png").hexdigest()
        legacy = {
            "schema_version": 1,
            "stamps": [
                {"x": 100, "y": 120, "size": 30, "kind": 2, "color": 0},
                {"x": 400, "y": 200, "size": 46, "kind": 0, "color": 4},
                {"x": "bad"},
            ],
            "background_sha256": digest,
        }
        state = legacy_state(legacy)
        self.assertEqual([(s.kind, s.colour) for s in state.shapes], [("star", "coral"), ("circle", "grape")])
        self.assertEqual((state.backdrop, state.picture), ("picture", digest))
        self.assertIsNone(legacy_state({"schema_version": 1, "stamps": []}))
        self.assertIsNone(legacy_state({"schema_version": 7}))


class RepositoryTests(unittest.TestCase):
    def project(self, *kinds):
        return GardenProject(GardenState(tuple(PlacedShape(k, "coral", 10 + i, 10) for i, k in enumerate(kinds))))

    def test_create_save_list_newest_first_and_delete(self):
        storage = MemoryStorage()
        repo = GardenProjectRepository(storage)
        first = repo.create(self.project("circle"))
        second = repo.create(self.project("square"))
        self.assertEqual([r.garden_id for r in repo.list_records()], [second.garden_id, first.garden_id])
        repo.save(first.garden_id, self.project("circle", "star"))
        self.assertEqual(repo.list_records()[0].garden_id, first.garden_id)
        self.assertEqual(len(repo.load(first.garden_id).state.shapes), 2)
        self.assertTrue(repo.delete(second.garden_id))
        self.assertFalse(repo.delete(second.garden_id))
        self.assertEqual([r.garden_id for r in repo.list_records()], [first.garden_id])
        with self.assertRaises(GardenProjectError):
            repo.load("not-an-id")

    def test_full_library_refuses_and_never_evicts(self):
        repo = GardenProjectRepository(MemoryStorage())
        records = [repo.create(self.project("oval")) for _ in range(MAX_GARDENS)]
        self.assertTrue(repo.is_full())
        with self.assertRaises(GardenProjectError):
            repo.create(self.project("heart"))
        self.assertEqual({r.garden_id for r in repo.list_records()}, {r.garden_id for r in records})

    def test_pictures_are_content_addressed_shared_and_reclaimed(self):
        storage = MemoryStorage()
        repo = GardenProjectRepository(storage)
        digest = repo.store_picture(b"picture-one")
        self.assertEqual(digest, hashlib.sha256(b"picture-one").hexdigest())
        self.assertEqual(repo.load_picture(digest), b"picture-one")
        using = GardenProject(GardenState((), "picture", digest))
        a = repo.create(using)
        b = repo.create(using)
        repo.delete(a.garden_id)
        self.assertIn(repo.picture_name(digest), storage.files)  # still used by b
        repo.delete(b.garden_id)
        self.assertNotIn(repo.picture_name(digest), storage.files)
        storage.files[repo.picture_name(digest)] = b"tampered"
        with self.assertRaises(GardenProjectError):
            repo.load_picture(digest)

    def test_failed_write_leaves_library_untouched(self):
        storage = MemoryStorage()
        repo = GardenProjectRepository(storage)
        kept = repo.create(self.project("circle"))
        storage.fail_kv = True
        with self.assertRaises(GardenProjectError):
            repo.create(self.project("square"))
        storage.fail_kv = False
        self.assertEqual([r.garden_id for r in repo.list_records()], [kept.garden_id])

    def test_v1_project_migrates_once_and_keeps_the_old_key(self):
        storage = MemoryStorage()
        legacy = {"schema_version": 1, "stamps": [{"x": 50, "y": 60, "size": 20, "kind": 1, "color": 2}]}
        storage.kv[LEGACY_STORAGE_KEY] = legacy
        repo = GardenProjectRepository(storage)
        records = repo.list_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(repo.list_records(), records)
        self.assertEqual(repo.load(records[0].garden_id).state.shapes[0].kind, "square")
        self.assertEqual(storage.kv[LEGACY_STORAGE_KEY], legacy)
        self.assertIn(INDEX_KEY, storage.kv)

    def test_v1_migration_on_a_read_only_store_stays_stable(self):
        storage = MemoryStorage()
        storage.kv[LEGACY_STORAGE_KEY] = {"schema_version": 1, "stamps": [{"x": 5, "y": 6, "size": 20, "kind": 0, "color": 0}]}
        storage.fail_kv = True
        repo = GardenProjectRepository(storage)
        first = repo.list_records()
        self.assertEqual(repo.list_records(), first)
        self.assertEqual(repo.load(first[0].garden_id).state.shapes[0].kind, "circle")
        storage.fail_kv = False
        repo.save(first[0].garden_id, repo.load(first[0].garden_id))
        self.assertEqual([r.garden_id for r in GardenProjectRepository(storage).list_records()], [first[0].garden_id])

    def test_export_staging_file_replaces_in_place(self):
        storage = MemoryStorage()
        repo = GardenProjectRepository(storage)
        self.assertEqual(repo.save_export(b"one"), "garden/shared.png")
        self.assertEqual(repo.save_export(b"two"), "garden/shared.png")
        self.assertEqual(storage.files["garden/shared.png"], b"two")
        with self.assertRaises(GardenProjectError):
            repo.save_export(b"")


if __name__ == "__main__":
    unittest.main()
