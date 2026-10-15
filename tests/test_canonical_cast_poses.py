"""Shared canonical cast poses stay on-model and resolvable at runtime."""

from __future__ import annotations

import re
import struct
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAST_DIR = ROOT / "assets" / "visual" / "characters" / "canonical" / "v0.1"
SOURCE_SPEC = ROOT / "assets" / "catalog" / "shared_visuals_v1_source.toml"
CAST = ("lilli", "leo", "flash", "dani", "tito", "momo")
POSES = ("pose_cheer", "pose_point", "pose_think")
RETIRED_FOLDERS = (
    "authoring_candidates",
    "authoring_kit",
    "pack_candidates",
    "generated_variants",
)
# GREIA_SVG_AUTHORING_RULES.md section 9 lint.
FORBIDDEN = re.compile(
    r'<image|data:|<text|<tspan|<filter|fe[A-Z]|<mask|<pattern|<style|<script'
    r'|foreignObject|<animate|blend-mode|skew|href="[^#]|xlink:href="[^#]'
    r"|sodipodi|inkscape:"
)
_SILHOUETTE_GROUPS = {
    "lilli": "body",
    "leo": "body",
    "flash": "body_fur",
    "dani": "body",
    "tito": "body",
    "momo": "fluff_body",
}


def _group(svg: str, group_id: str) -> str:
    match = re.search(r'( *)<g id="%s">.*?\n\1</g>' % group_id, svg, re.S)
    if match is None:
        raise AssertionError(f"group {group_id!r} missing")
    return match.group(0)


def _shapes(fragment: str) -> list[str]:
    return re.findall(r"<(?:path|ellipse|rect|circle)\b[^>]*/>", fragment)


class CanonicalCastPoseTests(unittest.TestCase):
    def test_cast_catalogue_registers_existing_poses(self) -> None:
        data = tomllib.loads((CAST_DIR / "catalog.toml").read_text(encoding="utf-8"))
        for character in data["characters"]:
            name = character["id"].removeprefix("character.")
            self.assertEqual(set(character["poses"]), set(POSES), name)
            for relative in character["poses"].values():
                self.assertTrue((CAST_DIR / relative).is_file(), relative)

    def test_cast_catalogue_provenance_does_not_cite_retired_folders(self) -> None:
        text = (CAST_DIR / "catalog.toml").read_text(encoding="utf-8")
        for folder in RETIRED_FOLDERS:
            self.assertNotIn(folder, text)

    def test_pose_sources_follow_svg_recipe(self) -> None:
        for name in CAST:
            for pose in POSES:
                path = CAST_DIR / name / f"{pose}.svg"
                svg = path.read_text(encoding="utf-8")
                self.assertIsNone(FORBIDDEN.search(svg), path.name)
                self.assertIn('viewBox="0 0 256 256" width="256" height="256"', svg)
                self.assertLessEqual(len(svg.encode("utf-8")), 8 * 1024, path)
                self.assertLessEqual(svg.count("<path"), 50, path)
                self.assertLessEqual(svg.count("Gradient id="), 3, path)
                self.assertNotIn("#000000", svg.upper())

    def test_pose_silhouette_and_identity_paths_are_canonical(self) -> None:
        for name in CAST:
            neutral = (CAST_DIR / name / "neutral.svg").read_text(encoding="utf-8")
            body = _shapes(_group(neutral, _SILHOUETTE_GROUPS[name]))
            self.assertTrue(body)
            for pose in POSES:
                svg = (CAST_DIR / name / f"{pose}.svg").read_text(encoding="utf-8")
                for shape in body:
                    self.assertIn(shape, svg, f"{name}/{pose} redrew its silhouette")

    def test_shared_visual_catalogue_exposes_pose_renditions(self) -> None:
        data = tomllib.loads(SOURCE_SPEC.read_text(encoding="utf-8"))
        visuals = {visual["id"]: visual for visual in data["visuals"]}
        for name in CAST:
            variants = {v["name"]: v for v in visuals[f"character.{name}"]["variants"]}
            for pose in POSES:
                variant = variants[pose]
                self.assertEqual(
                    variant["source"],
                    f"visual/characters/canonical/v0.1/{name}/{pose}.svg",
                )
                png = ROOT / "assets" / variant["output"]
                header = png.read_bytes()[:24]
                self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n", png)
                self.assertEqual(struct.unpack(">II", header[16:24]), (256, 256))


if __name__ == "__main__":
    unittest.main()
