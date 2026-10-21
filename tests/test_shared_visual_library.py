"""The shared visual catalogue is complete: every declared rendition exists.

Covers the whole explicit catalogue (UI, cast, biome layers, props, creatures,
HUD glyphs, FX) so a newly registered family cannot ship with a missing or
wrongly sized runtime PNG, and so aliases stay one-drawing-per-noun.
"""

from __future__ import annotations

import struct
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SOURCE_SPEC = ASSETS / "catalog" / "shared_visuals_v1_source.toml"
RUNTIME_CATALOG = ASSETS / "catalog" / "shared_visuals_v1.toml"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# prop.vocab nouns that are the same animal as a creature share its drawing.
VOCAB_CREATURE_ALIASES = {
    "prop.vocab.cat": "creature.pet.kitten",
    "prop.vocab.dog": "creature.pet.puppy",
    "prop.vocab.bear": "creature.woodland.bear",
    "prop.vocab.frog": "creature.woodland.frog",
    "prop.vocab.mouse": "creature.woodland.mouse",
    "prop.vocab.butterfly": "creature.woodland.butterfly",
    "prop.vocab.snail": "creature.woodland.snail",
    "prop.vocab.turtle": "creature.marine.turtle",
    "prop.vocab.whale": "creature.marine.whale",
    "prop.vocab.octopus": "creature.marine.octopus",
    "prop.vocab.crab": "creature.marine.crab",
}
LIBRARY_PREFIXES = ("bg.", "prop.", "creature.", "icon.hud.", "fx.")


def _visuals() -> dict[str, dict]:
    data = tomllib.loads(SOURCE_SPEC.read_text(encoding="utf-8"))
    return {visual["id"]: visual for visual in data["visuals"]}


def _variants(visual: dict) -> dict[str, dict]:
    return {variant["name"]: variant for variant in visual["variants"]}


class SharedVisualLibraryTests(unittest.TestCase):
    def test_every_variant_has_source_and_runtime_png_of_declared_size(self) -> None:
        count = 0
        for asset_id, visual in _visuals().items():
            for name, variant in _variants(visual).items():
                label = f"{asset_id}/{name}"
                self.assertTrue((ASSETS / variant["source"]).is_file(), label)
                png = ASSETS / variant["output"]
                self.assertTrue(png.is_file(), label)
                header = png.read_bytes()[:24]
                self.assertEqual(header[:8], PNG_SIGNATURE, label)
                self.assertEqual(
                    struct.unpack(">II", header[16:24]),
                    (variant["width"], variant["height"]),
                    label,
                )
                count += 1
        self.assertGreater(count, 500)

    def test_runtime_catalogue_lists_every_source_variant(self) -> None:
        runtime = tomllib.loads(RUNTIME_CATALOG.read_text(encoding="utf-8"))
        expected = {
            asset_id: {n: v["output"] for n, v in _variants(visual).items()}
            for asset_id, visual in _visuals().items()
        }
        actual = {entry["id"]: entry["variants"] for entry in runtime["visuals"]}
        self.assertEqual(actual, expected)

    def test_library_families_are_registered(self) -> None:
        ids = _visuals()
        for prefix in LIBRARY_PREFIXES:
            self.assertTrue(any(i.startswith(prefix) for i in ids), prefix)

    def test_runtime_png_without_a_catalogue_entry_is_not_shipped(self) -> None:
        declared = {
            (ASSETS / variant["output"]).resolve()
            for visual in _visuals().values()
            for variant in visual["variants"]
        }
        shipped = {
            path.resolve()
            for family in ("bg", "props", "creatures", "hud", "fx")
            for path in (ASSETS / "visual" / "runtime" / "v1" / family).rglob("*.png")
        }
        # An ``X@2x.png`` sibling is implied by a declared ``X.png``.
        shipped = {
            path.with_name(path.name.replace("@2x.png", ".png"))
            if path.name.endswith("@2x.png") else path
            for path in shipped
        }
        self.assertEqual(sorted(shipped - declared), [])

    def test_shipped_hires_siblings_are_exactly_double_size(self) -> None:
        import struct

        checked = 0
        for visual in _visuals().values():
            for variant in visual["variants"]:
                output = ASSETS / variant["output"]
                sibling = output.with_name(output.stem + "@2x" + output.suffix)
                if not sibling.is_file():
                    continue
                data = sibling.read_bytes()
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n", sibling)
                self.assertEqual(
                    struct.unpack(">II", data[16:24]),
                    (variant["width"] * 2, variant["height"] * 2),
                    sibling,
                )
                checked += 1
        self.assertGreater(checked, 0)

    def test_animal_vocabulary_aliases_share_the_creature_drawing(self) -> None:
        visuals = _visuals()
        for noun, creature in VOCAB_CREATURE_ALIASES.items():
            self.assertEqual(
                _variants(visuals[noun])["default"],
                _variants(visuals[creature])["default"],
                noun,
            )
            self.assertFalse(
                (ASSETS / "visual" / "props" / "vocab" / "v0.1"
                 / (noun.rsplit(".", 1)[1] + ".svg")).exists(),
                f"duplicate vocabulary drawing for {noun} must not ship",
            )

    def test_hud_glyphs_use_the_documented_id_scheme(self) -> None:
        hud = {i for i in _visuals() if i.startswith("icon.hud.")}
        self.assertTrue(
            {"icon.hud.listen", "icon.hud.replay", "icon.hud.check", "icon.hud.clear"}
            <= hud
        )
        self.assertNotIn("icon.hud.broom", hud)  # alias of icon.hud.clear

    def test_cast_extra_expressions_and_poses_are_variants_not_new_visuals(self) -> None:
        visuals = _visuals()
        for name in ("lilli", "leo", "flash", "dani", "tito", "momo"):
            variants = _variants(visuals[f"character.{name}"])
            for extra in ("sad", "angry", "silly", "pose_wave", "pose_play"):
                self.assertIn(extra, variants, f"{name}/{extra}")


if __name__ == "__main__":
    unittest.main()
