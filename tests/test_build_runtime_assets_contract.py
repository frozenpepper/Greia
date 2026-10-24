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
import os
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
        # Reusing a staging root must also remove authoring references left by
        # an older composition rule, not merely stop copying new versions.
        stale = cls.rootfs / "opt/greia-os/assets/audio/characters/canonical/stale.wav"
        stale.parent.mkdir(parents=True)
        stale.write_bytes(b"old authoring reference")
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
        self.assertIn(
            'compose_install_runtime_assets "$rootfs" "$project_root" "$application_root"',
            function,
        )
        self.assertNotIn('"$project_root/assets/" "$rootfs/opt/greia-os/assets/"', function)

    def test_generation_base_and_stable_bootstrap_are_composed(self) -> None:
        function = _function_source("compose_install_target_content")
        self.assertIn('local generations_root="$rootfs/opt/greia-software/generations"', function)
        self.assertIn('local application_root="$generations_root/base"', function)
        self.assertIn('ln -s greia-software/generations/base "$rootfs/opt/greia-os"', function)
        self.assertIn(
            'ln -s ../../../opt/greia-os/activity-index-v1.json "$image_index"',
            function,
        )
        compose = COMPOSE.read_text(encoding="utf-8")
        self.assertIn("greia-software-update-apply.timer", compose)
        self.assertIn('"$rootfs/etc/greia-os/software-update-bootstrap.json"', compose)
        recover = PROJECT_ROOT / "build/overlay/etc/systemd/system/greia-software-update-recover.service"
        apply = PROJECT_ROOT / "build/overlay/etc/systemd/system/greia-software-update-apply.service"
        timer = PROJECT_ROOT / "build/overlay/etc/systemd/system/greia-software-update-apply.timer"
        self.assertIn("--recover", recover.read_text(encoding="utf-8"))
        self.assertIn("--apply", apply.read_text(encoding="utf-8"))
        self.assertIn("OnUnitActiveSec=15s", timer.read_text(encoding="utf-8"))

    def test_generation_and_index_aliases_resolve_inside_a_fake_root(self) -> None:
        function = _function_source("compose_install_target_content")
        app_alias_command = next(
            line.strip()
            for line in function.splitlines()
            if line.strip().startswith('ln -s ') and '"$rootfs/opt/greia-os"' in line
        )
        index_alias_command = next(
            line.strip()
            for line in function.splitlines()
            if line.strip().startswith('ln -s ') and '"$image_index"' in line
        )
        with tempfile.TemporaryDirectory(prefix="greia-fake-root-links-") as temporary:
            rootfs = Path(temporary) / "rootfs"
            script = f'''\
rootfs="$ROOTFS"
image_index="$rootfs/usr/share/greia/activity-index-v1.json"
mkdir -p "$rootfs/opt/greia-software/generations/base/src/greia_platform"
mkdir -p "$rootfs/usr/share/greia"
printf '%s\\n' 'print("inside image")' > "$rootfs/opt/greia-software/generations/base/src/greia_platform/probe.py"
printf '%s\\n' '{{"schema_version":1,"activities":[]}}' > "$rootfs/opt/greia-software/generations/base/activity-index-v1.json"
{app_alias_command}
{index_alias_command}
'''
            environment = dict(os.environ)
            environment["ROOTFS"] = str(rootfs)
            subprocess.run(
                ["bash", "-eu", "-c", script],
                check=True,
                shell=False,
                env=environment,
            )

            application_alias = rootfs / "opt/greia-os"
            index_alias = rootfs / "usr/share/greia/activity-index-v1.json"
            resolved_root = rootfs.resolve()
            resolved_app = application_alias.resolve(strict=True)
            resolved_index = index_alias.resolve(strict=True)
            self.assertTrue(resolved_app.is_relative_to(resolved_root))
            self.assertTrue(resolved_index.is_relative_to(resolved_root))
            self.assertEqual(
                (application_alias / "src/greia_platform/probe.py").read_text("utf-8"),
                'print("inside image")\n',
            )
            self.assertEqual(
                index_alias.read_text("utf-8"),
                '{"schema_version":1,"activities":[]}\n',
            )

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
        # All canonical versions are authoring references, never runtime banks.
        self.assertFalse((self.installed / "audio/characters/canonical").exists())
        self.assertTrue((self.installed / "audio/characters/shared/v0.2/manifest.toml").is_file())
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
