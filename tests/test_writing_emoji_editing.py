from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


def _load_writing_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "activities" / "writing" / "main.py"
    spec = importlib.util.spec_from_file_location("greia_test_writing_activity", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Writing Activity module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
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
