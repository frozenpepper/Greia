from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PROJECT_ROOT / "tools"))
from build_profile import BuildProfile, BuildProfileError  # noqa: E402


def _load_mutated(
    source_name: str, old: str, new: str, extra_replacements: list[tuple[str, str]] | None = None
) -> BuildProfile:
    """Load a repository profile with string replacements applied (fail-closed probe).

    Uses a temp dir so the repository tree is never modified. Raises
    BuildProfileError on invalid combinations (the expected fail-closed path).
    """
    source = (PROJECT_ROOT / "build/profiles" / source_name).read_text()
    source = source.replace(old, new)
    for find, replace in extra_replacements or []:
        source = source.replace(find, replace)
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "probe.toml"
        path.write_text(source)
        return BuildProfile.load(path)


class StorageLifecycleAdapterTests(unittest.TestCase):
    def test_single_root_with_updates_required_fails_closed(self) -> None:
        with self.assertRaisesRegex(BuildProfileError, "updates.required=true"):
            _load_mutated("acer-aspire-one-i386.toml", "required = false", "required = true")

    def test_ab_layout_without_registered_boot_backend_fails_closed(self) -> None:
        with self.assertRaisesRegex(BuildProfileError, "registered updates.boot_backend"):
            _load_mutated(
                "modern-amd64.toml",
                'layout_adapter = "bios-single-ext4"',
                'layout_adapter = "legacy-bios-ab-v1"',
            )

    def test_pi_layout_with_grub_backend_fails_closed(self) -> None:
        with self.assertRaisesRegex(BuildProfileError, "GRUB"):
            _load_mutated(
                "modern-amd64.toml",
                'layout_adapter = "bios-single-ext4"',
                'layout_adapter = "pi-mbr-tryboot-ab-v1"',
                [
                    ('architecture = "amd64"', 'architecture = "arm64"'),
                    ('family = "standard-x86-64"', 'family = "arm64"'),
                    ('board = "none"', 'board = "pi-400-v1"'),
                    ('target_policy = "pc-internal-v1"', 'target_policy = "pi-builtin-microsd-v1"'),
                    ('boot_backend = "none-v1"', 'boot_backend = "grub-ab-v1"'),
                    ('live_boot_adapter = "pc-live-syslinux-v1"', 'live_boot_adapter = "pi-live-usb-v1"'),
                ],
            )

    def test_unknown_adapter_identifiers_fail_closed(self) -> None:
        with self.assertRaisesRegex(BuildProfileError, "storage.layout_adapter"):
            _load_mutated(
                "acer-aspire-one-i386.toml",
                'layout_adapter = "bios-single-ext4"',
                'layout_adapter = "bogus-layout-v9"',
            )
        with self.assertRaisesRegex(BuildProfileError, "installer.target_policy"):
            _load_mutated(
                "acer-aspire-one-i386.toml",
                'target_policy = "pc-internal-v1"',
                'target_policy = "yes-to-everything-v1"',
            )
        with self.assertRaisesRegex(BuildProfileError, "updates.boot_backend"):
            _load_mutated(
                "acer-aspire-one-i386.toml",
                'boot_backend = "none-v1"',
                'boot_backend = "bogus-backend-v9"',
            )
        with self.assertRaisesRegex(BuildProfileError, "setup.live_boot_adapter"):
            _load_mutated(
                "acer-aspire-one-i386.toml",
                'live_boot_adapter = "pc-live-syslinux-v1"',
                'live_boot_adapter = "bogus-live-v9"',
            )

    def test_insufficient_slot_capacity_fails_closed(self) -> None:
        with self.assertRaisesRegex(BuildProfileError, "below the base release"):
            _load_mutated(
                "acer-aspire-one-i386.toml",
                "system_slot_bytes = 1073741824",
                "system_slot_bytes = 134217728",
            )

    def test_small_image_size_mib_is_not_installed_capacity(self) -> None:
        # R4-B-CAPACITY: image.size_mib sizes the intermediate single-root
        # build artifact, never the installed-device minimum, so shrinking
        # it below the old layout-capacity bound keeps a valid profile valid
        # (1501 MiB still exceeds the 1500 MiB resource floor that the owner
        # accepted for single-root images on 2026-10-21).
        profile = _load_mutated(
            "acer-aspire-one-i386.toml",
            "size_mib = 2048",
            "size_mib = 1501",
        )
        self.assertEqual(1501, profile.image.size_mib)

    def test_image_at_resource_floor_and_persist_below_schema_floor_fail_closed(self) -> None:
        # R4-B-CAPACITY: the remaining artifact-relevant image gates are the
        # resource floor (image must exceed required_core_mib) and the
        # generic PERSIST schema floor (exact installed sizing stays with
        # the real layout planner via plan_for_profile).
        with self.assertRaisesRegex(
            BuildProfileError, "must exceed resources.required_core_mib"
        ):
            _load_mutated(
                "acer-aspire-one-i386.toml",
                "size_mib = 2048",
                "size_mib = 1500",
            )
        with self.assertRaisesRegex(BuildProfileError, "below the PERSIST"):
            _load_mutated(
                "acer-aspire-one-i386.toml",
                "persistent_minimum_bytes = 268435456",
                "persistent_minimum_bytes = 134217728",
            )

    def test_unknown_arm_board_fallback_fails_closed(self) -> None:
        with self.assertRaisesRegex(BuildProfileError, "not a supported ARM board fallback"):
            _load_mutated(
                "modern-amd64.toml",
                'layout_adapter = "bios-single-ext4"',
                'layout_adapter = "pi-mbr-tryboot-ab-v1"',
                [
                    ('architecture = "amd64"', 'architecture = "arm64"'),
                    ('family = "standard-x86-64"', 'family = "arm64"'),
                    ('board = "none"', 'board = "generic-arm-fallback"'),
                    ('target_policy = "pc-internal-v1"', 'target_policy = "pi-builtin-microsd-v1"'),
                    ('boot_backend = "none-v1"', 'boot_backend = "pi-tryboot-ab-v1"'),
                    ('live_boot_adapter = "pc-live-syslinux-v1"', 'live_boot_adapter = "pi-live-usb-v1"'),
                ],
            )

    def test_allow_mmc_is_not_a_target_policy_api(self) -> None:
        source = (PROJECT_ROOT / "build/profiles/acer-aspire-one-i386.toml").read_text()
        source = source.replace(
            'target_policy = "pc-internal-v1"',
            'target_policy = "pc-internal-v1"\nallow_mmc = true',
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "probe.toml"
            path.write_text(source)
            with self.assertRaisesRegex(BuildProfileError, "allow_mmc.*target_policy"):
                BuildProfile.load(path)

    def test_legacy_ab_grub_profile_validates(self) -> None:
        profile = _load_mutated(
            "modern-amd64.toml",
            'layout_adapter = "bios-single-ext4"',
            'layout_adapter = "legacy-bios-ab-v1"',
            [
                ('boot_backend = "none-v1"', 'boot_backend = "grub-ab-v1"'),
                ("required = false", "required = true"),
            ],
        )
        self.assertEqual("legacy-bios-ab-v1", profile.storage.layout_adapter)
        self.assertEqual("grub-ab-v1", profile.updates.boot_backend)
        self.assertTrue(profile.updates.required)
        manifest = profile.declared_manifest("target")
        self.assertEqual("legacy-bios-ab-v1", manifest["storage"]["layout_adapter"])

    def test_pi_tryboot_profile_validates(self) -> None:
        profile = _load_mutated(
            "modern-amd64.toml",
            'layout_adapter = "bios-single-ext4"',
            'layout_adapter = "pi-mbr-tryboot-ab-v1"',
            [
                ('architecture = "amd64"', 'architecture = "arm64"'),
                ('family = "standard-x86-64"', 'family = "arm64"'),
                ('board = "none"', 'board = "pi-400-v1"'),
                ('target_policy = "pc-internal-v1"', 'target_policy = "pi-builtin-microsd-v1"'),
                ('boot_backend = "none-v1"', 'boot_backend = "pi-tryboot-ab-v1"'),
                ("required = false", "required = true"),
                ('live_boot_adapter = "pc-live-syslinux-v1"', 'live_boot_adapter = "pi-live-usb-v1"'),
            ],
        )
        self.assertEqual("pi-mbr-tryboot-ab-v1", profile.storage.layout_adapter)
        self.assertEqual("pi-tryboot-ab-v1", profile.updates.boot_backend)
        self.assertEqual("pi-400-v1", profile.platform.board)


if __name__ == "__main__":
    unittest.main()
