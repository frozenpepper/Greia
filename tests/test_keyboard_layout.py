from __future__ import annotations

import unittest

from greia_platform.keyboard_layout import (
    PROBES,
    available_layouts,
    infer_layout,
    layout_by_id,
    layout_candidates,
)


class KeyboardLayoutTests(unittest.TestCase):
    def test_available_layouts_are_curated_and_valid(self) -> None:
        layouts = available_layouts()
        self.assertGreaterEqual(len(layouts), 10)
        ids = [layout.id for layout in layouts]
        self.assertEqual(len(ids), len(set(ids)))
        for layout in layouts:
            self.assertTrue(layout.label)
            layout_by_id(layout.id)

    def test_probes_use_discriminating_letters(self) -> None:
        characters = [probe.character for probe in PROBES]
        self.assertIn("z", characters)
        self.assertIn("y", characters)
        self.assertIn("q", characters)

    def test_us_layout_typing_roundtrip(self) -> None:
        # US qwerty: z, y, q, a, w, m, e at their standard HID positions.
        results = {
            "z": (29, False),
            "y": (28, False),
            "q": (20, False),
            "a": (4, False),
            "w": (26, False),
            "m": (16, False),
            "e": (8, False),
        }
        self.assertEqual(infer_layout(results), "us")
        self.assertEqual(layout_candidates(results)[0], "us")

    def test_qwertz_typing_identifies_german(self) -> None:
        # German QWERTZ: 'z' on the y physical key, 'y' on the z key.
        results = {
            "z": (28, False),
            "y": (29, False),
            "q": (20, False),
            "a": (4, False),
            "w": (26, False),
            "m": (16, False),
            "e": (8, False),
        }
        self.assertEqual(infer_layout(results), "de")
        candidates = layout_candidates(results)
        self.assertIn("de", candidates[:3])

    def test_azerty_typing_identifies_french(self) -> None:
        # French AZERTY: 'q' on the a key, 'a' on the q key, 'w' on the z key.
        results = {
            "z": (26, False),
            "y": (28, False),
            "q": (4, False),
            "a": (20, False),
            "w": (29, False),
            "m": (16, False),
            "e": (8, False),
        }
        self.assertEqual(infer_layout(results), "fr")
        candidates = layout_candidates(results)
        self.assertIn("fr", candidates[:3])

    def test_empty_results_default_to_us(self) -> None:
        self.assertEqual(infer_layout({}), "us")
        self.assertEqual(layout_candidates({}), ("us",))

    def test_unknown_scancodes_fall_back_to_us(self) -> None:
        self.assertEqual(infer_layout({"z": (-1, False)}), "us")


if __name__ == "__main__":
    unittest.main()
