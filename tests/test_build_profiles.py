from __future__ import annotations

import sys
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = PROJECT_ROOT / "tools" / "build_profile.py"

sys.path.insert(0, str(PROJECT_ROOT / "tools"))
from build_profile import BuildProfile, BuildProfileError  # noqa: E402


class BuildProfileTests(unittest.TestCase):
    def test_all_repository_profiles_are_typed_toml_and_resolve_both_artifacts(self) -> None:
        package_root = PROJECT_ROOT / "build/package-sets"
        profiles = sorted((PROJECT_ROOT / "build/profiles").glob("*.toml"))
        self.assertGreaterEqual(len(profiles), 4)
        self.assertEqual([], list((PROJECT_ROOT / "build/profiles").glob("*.env")))
        for path in profiles:
            profile = BuildProfile.load(path)
            if profile.base.architecture == "arm64":
                # The typed profile schema accepts ARM64, but the Phase 0
                # builder has no board boot adapter yet. Do not fake support;
                # keep the declaration valid while the builder refuses it.
                for scope in ("target", "installer"):
                    with self.assertRaisesRegex(
                        BuildProfileError, "does not implement architecture 'arm64'"
                    ):
                        profile.check_phase0_builder_support(scope)
            else:
                profile.check_phase0_builder_support("target")
                profile.check_phase0_builder_support("installer")
            target = profile.resolve_packages(package_root, "target")
            installer = profile.resolve_packages(package_root, "installer")
            self.assertEqual(len(target), len(set(target)))
            self.assertEqual(len(installer), len(set(installer)))
            self.assertIn("python", profile.runtimes.enabled)
            self.assertIn("python3-pygame", target)
            self.assertIn("bubblewrap", target)
            self.assertIn("xserver-xorg-core", target)
            self.assertIn(profile.base.kernel_package, target)
            self.assertIn(profile.base.kernel_package, installer)

    def test_provisional_boot_cover_is_not_release_eligible(self) -> None:
        profile = BuildProfile.load(PROJECT_ROOT / "build/profiles/acer-aspire-one-i386.toml")
        with self.assertRaisesRegex(BuildProfileError, "not registered as release-safe"):
            profile.check_release_eligibility()

    def test_runtime_family_is_composed_separately_from_platform_shell(self) -> None:
        profile = BuildProfile.load(PROJECT_ROOT / "build/profiles/acer-aspire-one-i386.toml")
        sets = profile.package_set_names("target")
        self.assertIn("platform-shell-pygame", sets)
        self.assertIn("runtime-python", sets)
        self.assertNotIn("runtime-web", sets)

    def test_declared_manifest_separates_profile_from_runtime_capability_probe(self) -> None:
        profile = BuildProfile.load(PROJECT_ROOT / "build/profiles/acer-aspire-one-i386.toml")
        target = profile.declared_manifest("target")
        installer = profile.declared_manifest("installer")
        self.assertEqual("target", target["artifact_scope"])
        self.assertEqual("installer", installer["artifact_scope"])
        self.assertTrue(target["contract"]["capabilities_are_runtime_probed"])
        self.assertEqual("runtime-independent", target["contract"]["activity_abstraction"])
        self.assertEqual(["python"], target["runtimes"]["enabled"])
        self.assertEqual("C0", target["platform"]["compatibility_class"])

    def test_phase0_builder_rejects_arm_without_rejecting_arm_from_profile_schema(self) -> None:
        source = (PROJECT_ROOT / "build/profiles/modern-amd64.toml").read_text()
        source = source.replace('id = "modern-amd64"', 'id = "arm-schema-probe"')
        source = source.replace('family = "standard-x86-64"', 'family = "arm64"')
        source = source.replace('architecture = "amd64"', 'architecture = "arm64"')
        # A coherent Pi storage/lifecycle declaration: the typed schema accepts
        # ARM64 with an explicit Pi board/layout/backend, while the Phase 0
        # builder still has no ARM implementation.
        source = source.replace('board = "none"', 'board = "pi-400-v1"')
        source = source.replace(
            'layout_adapter = "bios-single-ext4"', 'layout_adapter = "pi-mbr-tryboot-ab-v1"'
        )
        source = source.replace(
            'target_policy = "pc-internal-v1"', 'target_policy = "pi-builtin-microsd-v1"'
        )
        source = source.replace('boot_backend = "none-v1"', 'boot_backend = "pi-tryboot-ab-v1"')
        source = source.replace("required = false", "required = true")
        source = source.replace(
            'live_boot_adapter = "pc-live-syslinux-v1"', 'live_boot_adapter = "pi-live-usb-v1"'
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "arm-schema-probe.toml"
            path.write_text(source)
            profile = BuildProfile.load(path)
            self.assertEqual("arm64", profile.base.architecture)
            with self.assertRaisesRegex(BuildProfileError, "does not implement architecture 'arm64'"):
                profile.check_phase0_builder_support("target")

    def test_invalid_resource_budget_is_rejected(self) -> None:
        source = (PROJECT_ROOT / "build/profiles/acer-aspire-one-i386.toml").read_text()
        source = source.replace("preferred_core_mib = 800", "preferred_core_mib = 1500")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.toml"
            path.write_text(source)
            with self.assertRaisesRegex(BuildProfileError, "resource limits"):
                BuildProfile.load(path)

    def test_builders_never_source_profile_files_and_embed_json_contracts(self) -> None:
        # T01: the thin target consumer delegates profile work to the shared
        # engine; all three files must use the typed tool, never source.
        for builder_name in ("build/build-image.sh", "build/build-installer-image.sh", "build/lib/compose.sh"):
            builder = (PROJECT_ROOT / builder_name).read_text()
            self.assertNotIn('source "$PROFILE_PATH"', builder)
            self.assertIn('tools/build_profile.py', builder)
            self.assertIn("image-profile.json", builder)
        for builder_name in ("build/build-image.sh", "build/build-installer-image.sh"):
            builder = (PROJECT_ROOT / builder_name).read_text()
            self.assertIn('manifest "$PROFILE_PATH"', builder)
        engine = (PROJECT_ROOT / "build/lib/compose.sh").read_text()
        self.assertIn('manifest "$COMPOSE_PROFILE_PATH"', engine)
        installer = (PROJECT_ROOT / "build/build-installer-image.sh").read_text()
        self.assertNotIn("payload/profile.env", installer)
        self.assertIn("payload/target-image-profile.json", installer)
        self.assertIn(".disk/installer-image-profile.json", installer)

    def test_cli_manifest_is_stable_json(self) -> None:
        result = subprocess.run(
            [str(TOOL_PATH), "manifest", "acer-aspire-one-i386", "--scope", "target"],
            cwd=PROJECT_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual("acer-aspire-one-i386", payload["profile"]["id"])
        self.assertEqual("legacy-x86", payload["platform"]["family"])

    def test_ab_profile_selects_system_update_in_both_scopes(self) -> None:
        """Regression: the A/B profile must select `system-update`.

        Shipped install/update/recovery entrypoints stage unsigned
        deterministic .greiaupdate v3 bundles (payload.ext4.zst) per
        ADR 0036, so the set must provide ``zstd`` payload decompression
        in both scopes. Ed25519/``python3-cryptography`` is retired from
        the v3 update path and is no longer required. Omitting the
        set from either scope reproduces Gate-P5 D4 on the built artifact.
        """
        profile = BuildProfile.load(
            PROJECT_ROOT / "build/profiles/acer-aspire-one-i386-ab.toml"
        )
        self.assertIn("system-update", profile.package_set_names("target"))
        self.assertIn("system-update", profile.package_set_names("installer"))
        package_root = PROJECT_ROOT / "build/package-sets"
        self.assertIn(
            "zstd",
            profile.resolve_packages(package_root, "target"),
        )
        self.assertIn(
            "zstd",
            profile.resolve_packages(package_root, "installer"),
        )


if __name__ == "__main__":
    unittest.main()
