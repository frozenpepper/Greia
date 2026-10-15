"""Contract: the image installs only the shared assets the runtime reads.

``build/lib/compose.sh::compose_install_runtime_assets`` must copy the runtime
subtree of ``assets/`` (fonts, core-icon PNGs, catalogues, boot art, audio,
scene definition, generated runtime PNG renditions) and nothing that exists
only for authoring/build tooling (SVG masters, candidate packs, source sheets,
developer previews). The test runs the real function against the real asset
tree into a temporary rootfs.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPOSE = PROJECT_ROOT / "build" / "lib" / "compose.sh"


def _function_source(name: str) -> str:
    text = COMPOSE.read_text(encoding="utf-8")
    match = re.search(rf"^{name}\(\) \{{\n.*?^\}}\n", text, re.S | re.M)
    if match is None:
        raise AssertionError(f"{name} missing from build/lib/compose.sh")
    return match.group(0)


@unittest.skipUnless(shutil.which("rsync") and shutil.which("bash"), "rsync/bash required")
class RuntimeAssetInstallContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="greia-runtime-assets-")
        cls.rootfs = Path(cls._tmp.name)
        script = (
            _function_source("compose_install_runtime_assets")
            + f'\ncompose_install_runtime_assets "{cls.rootfs}" "{PROJECT_ROOT}"\n'
        )
        subprocess.run(["bash", "-eu", "-c", script], check=True, shell=False)
        cls.installed = cls.rootfs / "opt" / "greia-os" / "assets"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_target_content_delegates_to_the_allowlist_installer(self) -> None:
        function = _function_source("compose_install_target_content")
        self.assertIn('compose_install_runtime_assets "$rootfs" "$project_root"', function)
        self.assertNotIn('"$project_root/assets/" "$rootfs/opt/greia-os/assets/"', function)

    def test_every_catalogued_runtime_file_is_installed(self) -> None:
        shared = tomllib.loads(
            (PROJECT_ROOT / "assets/catalog/shared_visuals_v1.toml").read_text("utf-8")
        )
        paths = [
            variant
            for entry in shared["visuals"]
            for variant in entry["variants"].values()
        ]
        core = tomllib.loads(
            (PROJECT_ROOT / "assets/catalog/core_icons_v1.toml").read_text("utf-8")
        )
        for entry in core.get("icons", core.get("assets", [])):
            paths.extend(v for k, v in entry.items() if k.startswith("path_"))
        self.assertTrue(paths)
        for relative in paths:
            self.assertTrue(
                (self.installed / relative).is_file(),
                f"catalogued runtime file not installed: {relative}",
            )

    def test_runtime_readers_find_their_fixed_inputs(self) -> None:
        for relative in (
            "catalog/core_icons_v1.toml",
            "catalog/shared_visuals_v1.toml",
            "scenes/forest_meadow_day_v1.toml",
            "boot/static/greia-boot-logo.png",
            "audio/system/greia-boot-chime.wav",
            "fonts/nunito-sans",
            "icons/core/v1/256/yellow_star.png",
            "icons/core/v1/256/robot.png",
        ):
            self.assertTrue((self.installed / relative).exists(), relative)

    def test_authoring_and_candidate_material_is_not_installed(self) -> None:
        visual = self.installed / "visual"
        self.assertEqual(["runtime"], sorted(p.name for p in visual.iterdir()))
        leaked = sorted(
            str(p.relative_to(self.installed))
            for p in self.installed.rglob("*")
            if p.suffix.lower() == ".svg" or "contact_sheet" in p.name
        )
        self.assertEqual([], leaked)
        self.assertEqual([], sorted(p.name for p in self.installed.rglob("source")))
        self.assertEqual(
            sorted(p.name for p in (self.installed / "catalog").iterdir()),
            sorted(
                p.name
                for p in (PROJECT_ROOT / "assets/catalog").glob("*.toml")
            ),
        )


if __name__ == "__main__":
    unittest.main()
