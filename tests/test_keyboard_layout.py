from __future__ import annotations

import unittest

from greia_platform.keyboard_layout import (
    PROBES,
    _XKB_TO_HID,
    _character_for_layout,
    available_layouts,
    infer_layout,
    layout_by_id,
    layout_candidates,
)


def simulate(real_layout: str) -> dict[str, tuple[int, bool, str]]:
    """Simulate a parent pressing each probe key on a real keyboard layout.

    The parent is told which physical key to press; under the (currently
    configured) layout that key produces a character. We record the scancode,
    the shift state, and the produced character, exactly as the installer does.
    """
    results: dict[str, tuple[int, bool, str]] = {}
    for probe in PROBES:
        sc = _XKB_TO_HID[probe.keycode]
        char = _character_for_layout(real_layout, probe.keycode, probe.shift)
        if char:
            results[probe.keycode] = (sc, probe.shift, char)
    return results


class KeyboardLayoutTests(unittest.TestCase):
    def test_available_layouts_are_curated_and_valid(self) -> None:
        layouts = available_layouts()
        self.assertGreaterEqual(len(layouts), 10)
        ids = [layout.id for layout in layouts]
        self.assertEqual(len(ids), len(set(ids)))
        for layout in layouts:
            self.assertTrue(layout.label)
            layout_by_id(layout.id)

    def test_probes_use_discriminating_punctuation_keys(self) -> None:
        # The probe set must target punctuation/symbol keys that differ between
        # keyboard families, not letters (almost all layouts are QWERTY).
        keycodes = [probe.keycode for probe in PROBES]
        self.assertIn("AE07", keycodes)
        self.assertIn("AB10", keycodes)
        self.assertIn("AE02", keycodes)
        self.assertFalse(
            any(keycode in keycodes for keycode in ("AC01", "AD01", "AD06"))
        )

    def test_us_layout_typing_roundtrip(self) -> None:
        results = simulate("us")
        self.assertEqual(infer_layout(results), "us")
        self.assertEqual(layout_candidates(results)[0], "us")

    def test_italian_layout_is_identified(self) -> None:
        results = simulate("it")
        self.assertEqual(infer_layout(results), "it")
        self.assertIn("it", layout_candidates(results)[:3])

    def test_german_layout_is_identified(self) -> None:
        results = simulate("de")
        self.assertEqual(infer_layout(results), "de")
        self.assertIn("de", layout_candidates(results)[:3])

    def test_french_azerty_is_identified(self) -> None:
        results = simulate("fr")
        self.assertEqual(infer_layout(results), "fr")
        self.assertIn("fr", layout_candidates(results)[:3])

    def test_uk_layout_is_identified(self) -> None:
        results = simulate("gb")
        self.assertEqual(infer_layout(results), "gb")

    def test_brazilian_layout_is_identified(self) -> None:
        results = simulate("br")
        self.assertEqual(infer_layout(results), "br")

    def test_all_layouts_resolve_exactly_or_to_near_matches(self) -> None:
        # Every curated layout must either resolve exactly or appear in the
        # top-2 candidates so the selector can confirm it.
        for layout in available_layouts():
            results = simulate(layout.id)
            guess = infer_layout(results)
            candidates = layout_candidates(results)[:2]
            self.assertTrue(
                guess == layout.id or layout.id in candidates,
                f"{layout.id}: guessed {guess}, candidates {candidates}",
            )

    def test_empty_results_default_to_us(self) -> None:
        self.assertEqual(infer_layout({}), "us")
        self.assertEqual(layout_candidates({}), ("us",))

    def test_unknown_scancodes_fall_back_to_us(self) -> None:
        self.assertEqual(infer_layout({"AE07": (-1, True, "x")}), "us")


if __name__ == "__main__":
    unittest.main()
