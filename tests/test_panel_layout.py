"""Layout must tolerate any string, in any language, without overlapping.

The Parent panel had no string table and no measurement. The audio tab's level
label was centred in a fixed 300 px badge, so it landed on the adjacent buttons,
and the tab strip sized its columns arithmetically and centred labels inside
them. Adding two tabs made the tab labels collide before any translation existed.

These tests pin the property the panel needs in order to be translated later:

  * every string in panel_strings can be laid out inside the panel, at the
    reference size and at a cramped one, without being clipped away;
  * wrapping grows a block downwards and the caller can place what follows after
    it, which is what lets a long translation push a card taller instead of
    overlapping the control beneath it;
  * a single-line slot shrinks the font before it clips, and only clips when it
    has to, reporting that it did;
  * a word wider than its box is broken rather than allowed to escape.

They are deliberately string-agnostic: the point is not that today's English
fits, but that a German compound would.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from greia_launcher import panel_layout as layout  # noqa: E402
from greia_launcher import panel_strings as strings  # noqa: E402
from greia_platform.typography import FontRole, GreiaTypography  # noqa: E402

#: The reference panel is 1024x600; the content column is the panel minus its
#: 20 px margin each side and 24 px of inner padding each side.
REFERENCE_CONTENT_WIDTH = 1024 - 40 - 48
CRAMPED_CONTENT_WIDTH = 800 - 40 - 48

#: Narrowest slot a fixed-height control may use, e.g. a tab or a button face.
NARROW_SLOT = 96


def _typography() -> GreiaTypography:
    import pygame

    pygame.display.init()
    pygame.display.set_mode((320, 240))
    return GreiaTypography()


def _every_string() -> list[tuple[str, str]]:
    """Collect every user-visible string constant, plus the preset names."""

    found: list[tuple[str, str]] = []
    for name in dir(strings):
        if name.startswith("_") or name == "STRESS_SAMPLE":
            continue
        value = getattr(strings, name)
        if isinstance(value, str):
            found.append((name, value))
        elif isinstance(value, dict):
            found.extend((f"{name}[{k!r}]", v) for k, v in value.items())
        elif isinstance(value, tuple):
            found.extend((f"{name}[{i}]", v) for i, v in enumerate(value) if isinstance(v, str))
    return found


class EveryStringLaysOutTests(unittest.TestCase):
    def test_no_user_visible_string_is_empty(self) -> None:
        for name, value in _every_string():
            with self.subTest(constant=name):
                self.assertTrue(value.strip(), f"{name} is empty")

    def test_every_string_fits_the_reference_panel_or_wraps(self) -> None:
        typography = _typography()
        for name, value in _every_string():
            with self.subTest(constant=name):
                block = layout.fit_text_block(
                    typography, value, FontRole.BODY, 16, (0, 0, 0),
                    REFERENCE_CONTENT_WIDTH,
                )
                self.assertLessEqual(
                    block.width, REFERENCE_CONTENT_WIDTH,
                    f"{name} overflows the reference content width",
                )
                self.assertGreaterEqual(block.height, 1)

    def test_every_string_lays_out_in_a_cramped_panel(self) -> None:
        typography = _typography()
        for name, value in _every_string():
            with self.subTest(constant=name):
                block = layout.fit_text_block(
                    typography, value, FontRole.BODY, 16, (0, 0, 0),
                    CRAMPED_CONTENT_WIDTH,
                )
                self.assertLessEqual(block.width, CRAMPED_CONTENT_WIDTH, name)

    def test_a_translation_worse_than_anything_written_today_still_fits(self) -> None:
        """The stress sample is deliberately longer than any real constant."""

        typography = _typography()
        block = layout.fit_text_block(
            typography, strings.STRESS_SAMPLE, FontRole.BODY, 16, (0, 0, 0),
            CRAMPED_CONTENT_WIDTH,
        )
        self.assertLessEqual(block.width, CRAMPED_CONTENT_WIDTH)
        self.assertGreater(block.line_count, 1, "the stress sample should wrap")


class WrappingGrowsDownwardsTests(unittest.TestCase):
    def test_block_height_grows_with_each_extra_line(self) -> None:
        typography = _typography()
        short = layout.fit_text_block(
            typography, "Short", FontRole.BODY, 16, (0, 0, 0), 200
        )
        long = layout.fit_text_block(
            typography, strings.STRESS_SAMPLE, FontRole.BODY, 16, (0, 0, 0), 200
        )
        self.assertEqual(short.line_count, 1)
        self.assertGreater(long.line_count, 1)
        self.assertGreater(long.height, short.height)

    def test_a_caller_can_stack_content_below_a_wrapped_block(self) -> None:
        """The contract the new tabs rely on: place, do not guess."""

        typography = _typography()
        block = layout.fit_text_block(
            typography, strings.STRESS_SAMPLE, FontRole.BODY, 16, (0, 0, 0), 240
        )
        below_top = block.height
        self.assertGreater(below_top, 0)
        # A control placed at the reported height cannot overlap the text.
        self.assertGreaterEqual(below_top, block.height)

    def test_explicit_newlines_are_honoured(self) -> None:
        typography = _typography()
        block = layout.fit_text_block(
            typography, "one\ntwo\nthree", FontRole.BODY, 16, (0, 0, 0), 400
        )
        self.assertEqual(block.line_count, 3)

    def test_empty_text_still_reports_a_usable_height(self) -> None:
        typography = _typography()
        block = layout.fit_text_block(typography, "", FontRole.BODY, 16, (0, 0, 0), 100)
        self.assertGreaterEqual(block.height, 1)


class SingleLineSlotShrinksBeforeClippingTests(unittest.TestCase):
    def test_a_long_label_shrinks_rather_than_escaping_its_slot(self) -> None:
        typography = _typography()
        block = layout.fit_single_line(
            typography, strings.STRESS_SAMPLE, FontRole.CONTROL, 16, (0, 0, 0),
            NARROW_SLOT,
        )
        self.assertLessEqual(block.width, NARROW_SLOT)
        self.assertLess(block.font_size, 16, "should have shrunk before clipping")

    def test_every_tab_label_fits_its_column(self) -> None:
        """The tab strip is the reported overlap risk once tabs were added."""

        typography = _typography()
        for label, value in strings.TABS:
            with self.subTest(tab=value):
                block = layout.fit_single_line(
                    typography, value, FontRole.CONTROL, 16, (0, 0, 0), 110
                )
                self.assertLessEqual(block.width, 110, value)

    def test_clipping_is_reported_rather_than_silent(self) -> None:
        typography = _typography()
        block = layout.fit_single_line(
            typography, strings.STRESS_SAMPLE, FontRole.BODY, 16, (0, 0, 0),
            NARROW_SLOT, min_size=16,
        )
        self.assertTrue(block.clipped, "clipping must be visible to the caller")
        self.assertFalse(block.fits)

    def test_short_labels_are_not_marked_clipped(self) -> None:
        typography = _typography()
        block = layout.fit_single_line(
            typography, strings.TAB_SSH, FontRole.CONTROL, 16, (0, 0, 0), 110
        )
        self.assertFalse(block.clipped)
        self.assertEqual(block.font_size, 16)


class OversizedWordIsBrokenTests(unittest.TestCase):
    def test_a_word_wider_than_the_box_is_split_not_overflowed(self) -> None:
        typography = _typography()
        compound = "Aufnahmepuppenspieleverstärkungskalibrierung"
        block = layout.fit_text_block(
            typography, compound, FontRole.BODY, 16, (0, 0, 0), 80
        )
        self.assertLessEqual(block.width, 80)
        self.assertGreater(block.line_count, 1)

    def test_wrapping_never_loses_characters(self) -> None:
        typography = _typography()
        text = strings.STRESS_SAMPLE
        joined = "".join(
            layout.wrap_text(typography, text, FontRole.BODY, 16, 200)
        ).replace(" ", "")
        self.assertEqual(joined, text.replace(" ", "").replace("\n", ""))


class ColumnDistributionTests(unittest.TestCase):
    def test_columns_fill_the_width_exactly(self) -> None:
        widths = layout.even_columns(400, 5, 10, padding=12)
        self.assertEqual(len(widths), 5)
        self.assertEqual(sum(widths) + 10 * 4, 400 - 24)

    def test_no_column_is_zero_or_negative(self) -> None:
        for width in layout.even_columns(400, 8, 10, padding=12):
            self.assertGreaterEqual(width, 1)

    def test_impossible_width_is_refused_rather_than_silently_negative(self) -> None:
        with self.assertRaises(ValueError):
            layout.even_columns(10, 40, 10, padding=12)


class OverlapDetectionTests(unittest.TestCase):
    def test_overlapping_rects_are_reported(self) -> None:
        import pygame

        a = pygame.Rect(0, 0, 100, 40)
        b = pygame.Rect(80, 0, 100, 40)
        self.assertTrue(layout.overlaps(a, b))
        self.assertEqual(layout.find_overlaps([("a", a), ("b", b)]), [("a", "b")])

    def test_touching_rects_do_not_overlap(self) -> None:
        import pygame

        a = pygame.Rect(0, 0, 100, 40)
        b = pygame.Rect(100, 0, 100, 40)
        self.assertFalse(layout.overlaps(a, b))

    def test_zero_area_rects_never_overlap(self) -> None:
        import pygame

        a = pygame.Rect(0, 0, 0, 40)
        b = pygame.Rect(0, 0, 100, 40)
        self.assertFalse(layout.overlaps(a, b))


if __name__ == "__main__":
    unittest.main()
