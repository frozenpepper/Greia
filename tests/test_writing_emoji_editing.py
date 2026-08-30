from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


def _load_writing_module():
    # Support both the historical monolith (file-spec load) and the
    # decomposed package layout (activities.writing.*). Prefer the
    # package import so sibling modules resolve via relative imports.
    try:
        import importlib

        return importlib.import_module("activities.writing.main")
    except Exception:
        pass
    root = Path(__file__).resolve().parents[1]
    path = root / "activities" / "writing" / "main.py"
    spec = importlib.util.spec_from_file_location(
        "activities.writing.main", path, submodule_search_locations=[str(path.parent)]
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Writing Activity module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    # Ensure the package parent is loadable when executed as a file spec.
    parent_spec = importlib.util.spec_from_file_location(
        "activities.writing", path.parent / "__init__.py"
    )
    if parent_spec is None:
        # Namespace package fallback: create a minimal package module.
        import types

        pkg = types.ModuleType("activities.writing")
        pkg.__path__ = [str(path.parent)]  # type: ignore[attr-defined]
        sys.modules["activities.writing"] = pkg
    else:
        if "activities.writing" not in sys.modules:
            pkg = importlib.util.module_from_spec(parent_spec)
            sys.modules["activities.writing"] = pkg
            if parent_spec.loader is not None:
                try:
                    parent_spec.loader.exec_module(pkg)  # type: ignore[union-attr]
                except FileNotFoundError:
                    pkg.__path__ = [str(path.parent)]  # type: ignore[attr-defined]
    spec.loader.exec_module(module)
    # Keep legacy alias for any external consumers expecting the old name.
    sys.modules["greia_test_writing_activity"] = module
    return module


writing = _load_writing_module()


class WritingEmojiEditingTests(unittest.TestCase):
    def test_backspace_removes_one_complete_zwj_skin_tone_cluster(self) -> None:
        emoji = "👩🏽‍🔬"
        buffer = writing.TextBuffer(f"A{emoji}B", 1 + len(emoji))
        edit = buffer.backspace()
        self.assertIsNotNone(edit)
        assert edit is not None
        self.assertEqual(edit.removed, emoji)
        self.assertEqual(buffer.text, "AB")
        self.assertEqual(buffer.cursor, 1)

    def test_delete_removes_one_complete_flag_cluster(self) -> None:
        flag = "🇮🇹"
        buffer = writing.TextBuffer(f"A{flag}B", 1)
        edit = buffer.delete()
        self.assertIsNotNone(edit)
        assert edit is not None
        self.assertEqual(edit.removed, flag)
        self.assertEqual(buffer.text, "AB")
        self.assertEqual(buffer.cursor, 1)

    def test_horizontal_cursor_moves_by_user_perceived_character(self) -> None:
        emoji = "👍🏽"
        buffer = writing.TextBuffer(f"A{emoji}B", 1)
        buffer.move(1)
        self.assertEqual(buffer.cursor, 1 + len(emoji))
        buffer.move(-1)
        self.assertEqual(buffer.cursor, 1)

    def test_undo_restores_entire_emoji_and_safe_cursor(self) -> None:
        emoji = "👩‍🔬"
        buffer = writing.TextBuffer(f"A{emoji}B", 1 + len(emoji))
        edit = buffer.backspace()
        assert edit is not None
        edit.undo(buffer)
        self.assertEqual(buffer.text, f"A{emoji}B")
        self.assertEqual(buffer.cursor, 1 + len(emoji))

    def test_preview_and_character_limit_do_not_split_sequences(self) -> None:
        compact = writing.preview_text("hello 👩🏽‍🔬 world")
        self.assertIn("👩🏽‍🔬", compact)
        cluster = "👩🏽‍🔬"
        value = "A" * (writing.MAX_CHARACTERS - 2) + cluster
        clamped = writing.clamp_text(value)
        self.assertFalse(clamped.endswith(cluster[:-1]))
        self.assertLessEqual(len(clamped), writing.MAX_CHARACTERS)


if __name__ == "__main__":
    unittest.main()
