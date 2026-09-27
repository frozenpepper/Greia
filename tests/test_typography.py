from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from greia_platform.typography import (
    FontRole,
    FontSpec,
    GreiaTypography,
    TypographyError,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = PROJECT_ROOT / "assets" / "fonts" / "nunito-sans"


class GreiaTypographyTests(unittest.TestCase):
    def test_regular_font_loads_from_bundled_assets(self) -> None:
        typography = GreiaTypography(FONT_DIR)
        font = typography.font(FontRole.BODY, 24)
        self.assertGreater(font.get_height(), 24)
        self.assertFalse(typography.degraded)

    def test_all_roles_resolve_to_fonts(self) -> None:
        typography = GreiaTypography(FONT_DIR)
        for role in FontRole:
            font = typography.font(role, 24)
            self.assertGreater(font.get_height(), 0)
        self.assertFalse(typography.degraded)

    def test_fonts_are_cached_by_role_and_size(self) -> None:
        typography = GreiaTypography(FONT_DIR)
        first = typography.font(FontRole.TITLE, 40)
        second = typography.font(FontRole.TITLE, 40)
        self.assertIs(first, second)
        different = typography.font(FontRole.TITLE, 41)
        self.assertIsNot(first, different)

    def test_bolder_roles_render_wider_glyphs(self) -> None:
        # Bold weights must produce measurably wider text than Regular.
        typography = GreiaTypography(FONT_DIR)
        regular = typography.font(FontRole.BODY, 30).render("MMM", True, (0, 0, 0))
        extra = typography.font(FontRole.DISPLAY, 30).render("MMM", True, (0, 0, 0))
        self.assertGreaterEqual(extra.get_width(), regular.get_width())

    def test_missing_font_dir_falls_back_to_default_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            empty = Path(temporary) / "none"
            empty.mkdir()
            typography = GreiaTypography(empty)
            font = typography.font(FontRole.BODY, 24)
            self.assertGreater(font.get_height(), 0)
            self.assertTrue(typography.degraded)

    def test_text_surfaces_are_cached_per_font_and_cleared_with_the_rest(self) -> None:
        """Identical copy must not be re-rasterized on every frame.

        The graphical installer and the child launcher repaint continuously.
        Rasterizing the same labels every frame pinned a full core on the
        reference Acer (Intel GMA 500, software rendering), which the child
        experiences as an unusable screen. The cache lives here, in the
        platform owner of text rendering, so neither surface grows its own.
        """

        typography = GreiaTypography()
        font = typography.font(FontRole.CONTROL, 27)
        first = typography.surface(font, "Pointer feel", (61, 44, 31))
        second = typography.surface(font, "Pointer feel", (61, 44, 31))
        self.assertIs(first, second, "the same line must reuse one surface")
        other_text = typography.surface(font, "Touchpad feel", (61, 44, 31))
        self.assertIsNot(first, other_text)
        other_colour = typography.surface(font, "Pointer feel", (255, 0, 0))
        self.assertIsNot(first, other_colour)
        self.assertEqual(typography.surface_width(font, "Pointer feel"), first.get_width())
        typography.clear()
        self.assertIsNot(
            first,
            typography.surface(font, "Pointer feel", (61, 44, 31)),
            "clear() must release renderer-owned surfaces",
        )

    def test_invalid_size_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            FontSpec(FontRole.BODY, 4)


if __name__ == "__main__":
    unittest.main()
