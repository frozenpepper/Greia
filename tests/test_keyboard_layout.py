from __future__ import annotations

import unittest

from greia_platform.keyboard_layout import (
    PROBES,
    _HID_TO_XKB,
    _LAYOUT_TABLE,
    available_layouts,
    infer_layout,
    layout_by_id,
    layout_candidates,
)


def simulate(real_layout: str) -> dict[str, tuple[int, bool, str]]:
    """Simulate a parent typing each probe character on a real keyboard.

    The parent types the character; under the real layout that character is
    produced on a specific physical key with a specific shift state. We record
    (scancode, shift_held, character) exactly as the installer does.
    """
    results: dict[str, tuple[int, bool, str]] = {}
    hid_to_xkb = {sc: kc for kc, sc in _HID_TO_XKB.items()}
    for probe in PROBES:
        character = probe.character
        table = _LAYOUT_TABLE[real_layout]
        found = None
        for keycode, chars in table.items():
            for level, produced in enumerate(chars):
                if produced == character:
                    scancode = next((s for s, k in _HID_TO_XKB.items() if k == keycode), None)
                    if scancode is None:
                        continue
                    found = (scancode, bool(level), character)
                    break
            if found:
                break
        if found:
            results[character] = found
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

    def test_probes_use_discriminating_punctuation(self) -> None:
        # The probe set must target characters that sit on different physical
        # keys across keyboard families. Most are punctuation; 'z' is kept
        # because it separates QWERTY from QWERTZ/AZERTY.
        chars = [probe.character for probe in PROBES]
        self.assertIn("/", chars)
        self.assertIn("-", chars)
        self.assertIn(";", chars)
        self.assertGreaterEqual(
            len([c for c in chars if not c.isalpha()]), 4
        )
        self.assertNotIn("a", chars)
        self.assertNotIn("q", chars)
        self.assertNotIn("y", chars)

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
        # Every curated layout must resolve exactly or appear among the
        # highest-scoring candidates. Continental QWERTY layouts (pt/it/es) and
        # Nordic layouts (dk/fi/no/se) share the same probe positions and are
        # genuine ties the selector resolves; none must be scored into a
        # different family than its tie group.
        for layout in available_layouts():
            results = simulate(layout.id)
            guess = infer_layout(results)
            candidates = layout_candidates(results)
            self.assertTrue(
                guess == layout.id or layout.id in candidates[:8],
                f"{layout.id}: guessed {guess}, candidates {candidates[:8]}",
            )

    def test_empty_results_default_to_us(self) -> None:
        self.assertEqual(infer_layout({}), "us")
        self.assertEqual(layout_candidates({}), ("us",))

    def test_unknown_input_falls_back_to_us(self) -> None:
        self.assertEqual(infer_layout({"/": (-1, False, "x")}), "us")

    def test_italian_shift_7_slash_probe_works_with_any_active_layout(self) -> None:
        # On an Italian keyboard '/' is Shift+7 (scancode 36). The active layout
        # may produce a different character (e.g. '&'), but the physical press
        # must still resolve to Italian.
        results = {
            "/": (36, True, "&"),
            ";": (55, True, ";"),
            "-": (56, False, "-"),
            "?": (45, True, "?"),
            "z": (29, False, "z"),
        }
        self.assertEqual(infer_layout(results), "it")
        self.assertIn("it", layout_candidates(results)[:3])


if __name__ == "__main__":
    unittest.main()
