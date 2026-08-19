from __future__ import annotations

from pathlib import Path
import unittest

from greia_platform.emoji_palette import DEFAULT_EMOJI_CATEGORIES, EmojiPalette
from greia_platform.typography import (
    GreiaTypography,
    grapheme_boundaries,
    grapheme_spans,
    is_emoji_cluster,
    next_grapheme_boundary,
    previous_grapheme_boundary,
    snap_grapheme_boundary,
    truncate_grapheme_safe,
)


class GraphemeContractTests(unittest.TestCase):
    def test_unicode_grapheme_segmentation_keeps_emoji_sequences_atomic(self) -> None:
        text = "A👩🏽‍🔬🇮🇹1️⃣e\u0301"
        spans = grapheme_spans(text)
        self.assertEqual(
            [span.text for span in spans],
            ["A", "👩🏽‍🔬", "🇮🇹", "1️⃣", "e\u0301"],
        )
        self.assertEqual(
            [span.emoji for span in spans],
            [False, True, True, True, False],
        )
        self.assertEqual(grapheme_boundaries(text), (0, 1, 5, 7, 10, 12))

    def test_cursor_helpers_never_land_inside_zwj_or_modifier_sequence(self) -> None:
        text = "A👩🏽‍🔬B"
        scientist_end = 1 + len("👩🏽‍🔬")
        self.assertEqual(previous_grapheme_boundary(text, scientist_end), 1)
        self.assertEqual(next_grapheme_boundary(text, 1), scientist_end)
        self.assertEqual(snap_grapheme_boundary(text, 3), 1)

    def test_truncation_never_retains_partial_grapheme(self) -> None:
        text = "AB👩🏽‍🔬CD"
        self.assertEqual(truncate_grapheme_safe(text, 2), "AB")
        self.assertEqual(truncate_grapheme_safe(text, 4), "AB")
        self.assertEqual(truncate_grapheme_safe(text, 6), "AB👩🏽‍🔬")
        self.assertEqual(truncate_grapheme_safe(text, len(text)), text)

    def test_emoji_classification_covers_required_sequence_families(self) -> None:
        for cluster in (
            "🙂",
            "🚀",
            "🦄",
            "❤️",
            "👍🏽",
            "👩‍🔬",
            "🏳️‍🌈",
            "🇮🇹",
            "1️⃣",
        ):
            with self.subTest(cluster=cluster):
                self.assertTrue(is_emoji_cluster(cluster))
        for cluster in ("A", "é", "e\u0301"):
            with self.subTest(cluster=cluster):
                self.assertFalse(is_emoji_cluster(cluster))


class EmojiPaletteTests(unittest.TestCase):
    def test_default_palette_is_bounded_and_every_item_is_one_emoji_grapheme(self) -> None:
        palette = EmojiPalette()
        self.assertEqual(palette.categories, DEFAULT_EMOJI_CATEGORIES)
        self.assertLessEqual(len(palette.categories), 12)
        for category in palette.categories:
            with self.subTest(category=category.category_id):
                self.assertLessEqual(len(category.emoji), 24)
                self.assertEqual(len(grapheme_spans(category.icon)), 1)
                self.assertTrue(is_emoji_cluster(category.icon))
                for cluster in category.emoji:
                    self.assertEqual(len(grapheme_spans(cluster)), 1)
                    self.assertTrue(is_emoji_cluster(cluster))

    def test_category_selection_is_semantic_and_bounded(self) -> None:
        palette = EmojiPalette()
        animals = palette.select_id("animals")
        self.assertEqual(animals.category_id, "animals")
        self.assertEqual(palette.selected.category_id, "animals")
        with self.assertRaises(KeyError):
            palette.select_id("not-a-category")
        with self.assertRaises(IndexError):
            palette.select(len(palette.categories))


class TypographyCompositionTests(unittest.TestCase):
    def test_missing_emoji_font_is_a_safe_capability_degradation(self) -> None:
        typography = GreiaTypography(
            emoji_font_path=Path("/definitely/missing/NotoColorEmoji.ttf")
        )
        self.assertFalse(typography.emoji_available)
        self.assertEqual(typography.cached_emoji_count, 0)

    def test_runtime_package_sets_include_shipping_emoji_dependencies(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for relative in (
            "build/package-sets/platform-shell-pygame.txt",
            "build/package-sets/runtime-python.txt",
        ):
            with self.subTest(path=relative):
                content = (root / relative).read_text(encoding="utf-8")
                self.assertIn("fonts-noto-color-emoji", content.splitlines())
                self.assertIn("python3-regex", content.splitlines())


if __name__ == "__main__":
    unittest.main()
