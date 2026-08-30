from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    # Prefer package import for decomposed Activities so sibling modules
    # resolve via relative imports. Fall back to file-spec with proper
    # package name for the legacy monolith path.
    package_map = {
        "greia_test_writing_activity": "activities.writing.main",
        "greia_test_painting_activity": "activities.painting.main",
    }
    pkg_name = package_map.get(name)
    if pkg_name is not None:
        try:
            import importlib

            mod = importlib.import_module(pkg_name)
            sys.modules[name] = mod
            return mod
        except Exception:
            pass
    # Legacy file-spec fallback.
    spec_name = pkg_name or name
    parent = str(path.parent)
    # Ensure submodule_search_locations so relative imports work for decomposed layout.
    spec = importlib.util.spec_from_file_location(
        spec_name, path, submodule_search_locations=[parent] if path.parent.is_dir() else None
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    if spec_name != name:
        sys.modules[spec_name] = module
    # Ensure package entry exists for relative import resolution.
    if "." in spec_name:
        pkg = spec_name.rpartition(".")[0]
        if pkg not in sys.modules:
            import types

            pkg_mod = types.ModuleType(pkg)
            pkg_mod.__path__ = [parent]  # type: ignore[attr-defined]
            sys.modules[pkg] = pkg_mod
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

    def file_delete(self, name: str) -> bool:
        return self.files.pop(name, None) is not None


class FailingIndexStorage(FakeStorage):
    def kv_set(self, key: str, value: object) -> None:
        if key == WRITING.INDEX_KEY:
            raise RuntimeError("simulated index failure")
        super().kv_set(key, value)


class WritingLogicTests(unittest.TestCase):
    def test_text_buffer_edits_and_inverse_edits(self) -> None:
        buffer = WRITING.TextBuffer("ciao", 4)
        insert = buffer.insert("!")
        self.assertIsNotNone(insert)
        self.assertEqual(buffer.text, "ciao!")
        assert insert is not None
        insert.undo(buffer)
        self.assertEqual(buffer.text, "ciao")
        self.assertEqual(buffer.cursor, 4)

        backspace = buffer.backspace()
        self.assertIsNotNone(backspace)
        self.assertEqual(buffer.text, "cia")
        assert backspace is not None
        backspace.undo(buffer)
        self.assertEqual(buffer.text, "ciao")
        self.assertEqual(buffer.cursor, 4)

        buffer.move(-2)
        delete = buffer.delete()
        self.assertIsNotNone(delete)
        self.assertEqual(buffer.text, "cio")
        assert delete is not None
        delete.undo(buffer)
        self.assertEqual(buffer.text, "ciao")
        self.assertEqual(buffer.cursor, 2)

    def test_text_buffer_line_navigation(self) -> None:
        buffer = WRITING.TextBuffer("ciao", 2)
        buffer.insert("\nabc")
        self.assertEqual(buffer.text, "ci\nabcao")
        buffer.home()
        self.assertEqual(buffer.cursor, 3)
        buffer.end()
        self.assertEqual(buffer.cursor, len(buffer.text))

    def test_undo_history_is_bounded_and_keeps_latest_edits(self) -> None:
        history = WRITING.UndoHistory(maximum=2)
        buffer = WRITING.TextBuffer()
        first = buffer.insert("a")
        second = buffer.insert("b")
        third = buffer.insert("c")
        assert first is not None and second is not None and third is not None
        history.remember(first)
        history.remember(second)
        history.remember(third)
        self.assertEqual(history.pop(), third)
        self.assertEqual(history.pop(), second)
        self.assertIsNone(history.pop())

    def test_undo_history_is_bounded_by_total_changed_text(self) -> None:
        history = WRITING.UndoHistory(maximum=10, max_payload_chars=4)
        buffer = WRITING.TextBuffer()
        first = buffer.insert("ab")
        second = buffer.insert("cd")
        third = buffer.insert("ef")
        assert first is not None and second is not None and third is not None
        history.remember(first)
        history.remember(second)
        self.assertEqual(history.payload_chars, 4)
        history.remember(third)
        self.assertEqual(history.payload_chars, 4)
        self.assertEqual(history.pop(), third)
        self.assertEqual(history.pop(), second)
        self.assertIsNone(history.pop())

    def test_oversized_single_undo_payload_is_not_retained(self) -> None:
        history = WRITING.UndoHistory(maximum=10, max_payload_chars=3)
        buffer = WRITING.TextBuffer()
        edit = buffer.insert("abcd")
        assert edit is not None
        history.remember(edit)
        self.assertEqual(history.payload_chars, 0)
        self.assertIsNone(history.pop())
        self.assertEqual(buffer.text, "abcd")

    def test_undo_edit_stores_only_changed_fragment_not_full_document(self) -> None:
        original = "x" * 50_000
        buffer = WRITING.TextBuffer(original, len(original))
        edit = buffer.insert("y")
        self.assertIsNotNone(edit)
        assert edit is not None
        self.assertEqual(edit.removed, "")
        self.assertEqual(edit.inserted, "y")
        self.assertEqual(edit.payload_chars, 1)
        edit.undo(buffer)
        self.assertEqual(buffer.text, original)

    def test_undo_rejects_mismatched_current_text(self) -> None:
        buffer = WRITING.TextBuffer("abc", 3)
        edit = buffer.insert("d")
        assert edit is not None
        buffer.text = "abXc"
        with self.assertRaises(ValueError):
            edit.undo(buffer)

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

    def test_document_create_rolls_back_private_file_if_index_fails(self) -> None:
        storage = FailingIndexStorage()
        with self.assertRaises(RuntimeError):
            WRITING.DocumentRepository(storage).create()
        self.assertEqual(storage.files, {})
        self.assertNotIn(WRITING.INDEX_KEY, storage.kv)

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
        first = repo.create(b"png-zero")
        second = repo.create(b"png-two")
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
            PAINTING.PaintingRepository(storage).create(b"png-new")
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

    def test_stroke_point_count_is_bounded(self) -> None:
        history = PAINTING.StrokeHistory()
        points = tuple((index, 0) for index in range(PAINTING.MAX_STROKE_POINTS + 1))
        with self.assertRaises(ValueError):
            history.add(PAINTING.Stroke((1, 2, 3), 8, points))

    def test_invalid_stroke_is_rejected(self) -> None:
        history = PAINTING.StrokeHistory()
        with self.assertRaises(ValueError):
            history.add(PAINTING.Stroke((0, 0, 0), 0, ((1, 1),)))
        with self.assertRaises(ValueError):
            history.add(PAINTING.Stroke((0, 0, 0), 8, ()))


if __name__ == "__main__":
    unittest.main()
