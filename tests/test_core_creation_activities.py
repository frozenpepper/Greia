from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


WRITING = _load("greia_test_writing_activity", ROOT / "activities" / "writing" / "main.py")
PAINTING = _load("greia_test_painting_activity", ROOT / "activities" / "painting" / "main.py")


class FakeStorage:
    def __init__(self) -> None:
        self.kv: dict[str, object] = {}
        self.files: dict[str, bytes] = {}

    def kv_get(self, key: str, default: object = None) -> object:
        return self.kv.get(key, default)

    def kv_set(self, key: str, value: object) -> None:
        self.kv[key] = value

    def file_write_atomic(self, name: str, payload: bytes) -> None:
        self.files[name] = bytes(payload)

    def file_read(self, name: str) -> bytes:
        if name not in self.files:
            raise RuntimeError("missing private file")
        return self.files[name]


class WritingLogicTests(unittest.TestCase):
    def test_text_buffer_edits_without_desktop_editor_semantics(self) -> None:
        buffer = WRITING.TextBuffer("ciao", 4)
        self.assertTrue(buffer.insert("!"))
        self.assertEqual(buffer.text, "ciao!")
        self.assertTrue(buffer.backspace())
        self.assertEqual(buffer.text, "ciao")
        buffer.move(-2)
        self.assertEqual(buffer.cursor, 2)
        self.assertTrue(buffer.delete())
        self.assertEqual(buffer.text, "cio")
        buffer.insert("\nabc")
        self.assertEqual(buffer.text, "ci\nabco")
        buffer.home()
        self.assertEqual(buffer.cursor, 3)
        buffer.end()
        self.assertEqual(buffer.cursor, len(buffer.text))

    def test_undo_history_is_bounded_and_keeps_latest_states(self) -> None:
        history = WRITING.UndoHistory(maximum=2)
        first = WRITING.TextSnapshot("a", 1)
        second = WRITING.TextSnapshot("ab", 2)
        third = WRITING.TextSnapshot("abc", 3)
        history.remember(first)
        history.remember(second)
        history.remember(third)
        self.assertEqual(history.pop(), third)
        self.assertEqual(history.pop(), second)
        self.assertIsNone(history.pop())

    def test_undo_history_deduplicates_adjacent_state(self) -> None:
        history = WRITING.UndoHistory(maximum=4)
        snapshot = WRITING.TextSnapshot("hello", 5)
        history.remember(snapshot)
        history.remember(snapshot)
        self.assertEqual(history.pop(), snapshot)
        self.assertIsNone(history.pop())

    def test_document_repository_keeps_text_portable_and_recent(self) -> None:
        storage = FakeStorage()
        repo = WRITING.DocumentRepository(storage)
        first = repo.create()
        updated = repo.save_text(first.document_id, "  Ciao   mondo\nGreia  ")
        self.assertEqual(updated.preview, "Ciao mondo Greia")
        self.assertEqual(repo.load_text(first.document_id), "  Ciao   mondo\nGreia  ")
        second = repo.create()
        self.assertEqual(repo.list_records()[0].document_id, second.document_id)
        repo.save_text(first.document_id, "again")
        self.assertEqual(repo.list_records()[0].document_id, first.document_id)

    def test_document_limit_refuses_new_work_instead_of_evicting_old_work(self) -> None:
        storage = FakeStorage()
        records = []
        for index in range(WRITING.MAX_DOCUMENTS):
            document_id = f"{index:032x}"
            records.append({"id": document_id, "preview": str(index)})
        storage.kv[WRITING.INDEX_KEY] = records
        before = list(records)
        with self.assertRaises(RuntimeError):
            WRITING.DocumentRepository(storage).create()
        self.assertEqual(storage.kv[WRITING.INDEX_KEY], before)

    def test_preview_is_bounded_and_removes_nul(self) -> None:
        preview = WRITING.preview_text("a\x00   b\n" + "c" * 200)
        self.assertNotIn("\x00", preview)
        self.assertLessEqual(len(preview), 80)


class PaintingLogicTests(unittest.TestCase):
    def test_painting_repository_preserves_recent_order(self) -> None:
        storage = FakeStorage()
        repo = PAINTING.PaintingRepository(storage)
        first = repo.create()
        second = repo.create()
        self.assertEqual(repo.list_records()[0].painting_id, second.painting_id)
        repo.save_png(first.painting_id, b"png-one")
        self.assertEqual(repo.list_records()[0].painting_id, first.painting_id)
        self.assertEqual(repo.load_png(first.painting_id), b"png-one")

    def test_painting_limit_refuses_new_work_without_eviction(self) -> None:
        storage = FakeStorage()
        records = [{"id": f"{index:032x}"} for index in range(PAINTING.MAX_PAINTINGS)]
        storage.kv[PAINTING.INDEX_KEY] = records
        before = list(records)
        with self.assertRaises(RuntimeError):
            PAINTING.PaintingRepository(storage).create()
        self.assertEqual(storage.kv[PAINTING.INDEX_KEY], before)

    def test_undo_history_is_bounded_and_returns_fold_candidate(self) -> None:
        history = PAINTING.StrokeHistory(maximum=2)
        first = PAINTING.Stroke((1, 2, 3), 8, ((1, 1),))
        second = PAINTING.Stroke((4, 5, 6), 8, ((2, 2),))
        third = PAINTING.Stroke((7, 8, 9), 8, ((3, 3),))
        self.assertIsNone(history.add(first))
        self.assertIsNone(history.add(second))
        self.assertEqual(history.add(third), first)
        self.assertEqual(history.items, (second, third))
        self.assertEqual(history.undo(), third)
        self.assertEqual(history.items, (second,))

    def test_invalid_stroke_is_rejected(self) -> None:
        history = PAINTING.StrokeHistory()
        with self.assertRaises(ValueError):
            history.add(PAINTING.Stroke((0, 0, 0), 0, ((1, 1),)))
        with self.assertRaises(ValueError):
            history.add(PAINTING.Stroke((0, 0, 0), 8, ()))


if __name__ == "__main__":
    unittest.main()
