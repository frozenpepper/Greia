from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS = PROJECT_ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from build_profile import BuildProfile  # noqa: E402
from provision_developer_image import (  # noqa: E402
    DeveloperImageProvisionError,
    DeveloperImageProvisioner,
    ProvisionConfig,
)


class DeveloperRemoteProfileTests(unittest.TestCase):
    PAIRS = (
        ("acer-aspire-one-i386", "acer-aspire-one-i386-dev"),
        ("acer-aspire-one-i386-nonpae", "acer-aspire-one-i386-nonpae-dev"),
        ("acer-aspire-one-amd64", "acer-aspire-one-amd64-dev"),
    )

    def test_acer_developer_profiles_preserve_hardware_profile_and_add_only_dev_capability(self) -> None:
        for normal_name, dev_name in self.PAIRS:
            with self.subTest(dev_name=dev_name):
                normal = BuildProfile.load(PROJECT_ROOT / "build/profiles" / f"{normal_name}.toml")
                dev = BuildProfile.load(PROJECT_ROOT / "build/profiles" / f"{dev_name}.toml")
                self.assertEqual(dev.base.architecture, normal.base.architecture)
                self.assertEqual(dev.base.kernel_package, normal.base.kernel_package)
                self.assertEqual(dev.platform.family, normal.platform.family)
                self.assertEqual(
                    dev.platform.compatibility_class,
                    normal.platform.compatibility_class,
                )
                self.assertEqual(dev.display, normal.display)
                self.assertEqual(dev.boot, normal.boot)
                self.assertEqual(dev.runtimes, normal.runtimes)
                self.assertEqual(dev.image.size_mib, normal.image.size_mib)
                self.assertEqual(dev.image.layout, normal.image.layout)
                self.assertEqual(dev.image.hostname, "greia-dev")
                self.assertEqual(dev.identity.certification_state, "experimental")
                self.assertNotIn("developer-remote", normal.package_set_names("target"))
                self.assertIn("developer-remote", dev.package_set_names("target"))
                packages = dev.resolve_packages(PROJECT_ROOT / "build/package-sets", "target")
                self.assertIn("openssh-server", packages)
                self.assertIn("python3-pil", packages)
                self.assertIn("xdotool", packages)

    def test_provisioner_validates_exact_requested_acer_dev_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_path = root / "etc/greia-os/image-profile.json"
            profile_path.parent.mkdir(parents=True)
            profile_path.write_text(
                json.dumps(
                    {
                        "profile": {"profile_id": "acer-aspire-one-i386-dev"},
                        "package_sets": {"target": ["developer-remote"]},
                    }
                ),
                encoding="utf-8",
            )
            provisioner = DeveloperImageProvisioner(
                ProvisionConfig(
                    image=root / "unused.img",
                    output_dir=root / "out",
                    expected_profile="acer-aspire-one-i386-dev",
                )
            )
            payload = provisioner._validate_profile(root)
            self.assertEqual(payload["profile"]["profile_id"], "acer-aspire-one-i386-dev")

            wrong = DeveloperImageProvisioner(
                ProvisionConfig(
                    image=root / "unused.img",
                    output_dir=root / "out",
                    expected_profile="acer-aspire-one-i386-nonpae-dev",
                )
            )
            with self.assertRaisesRegex(DeveloperImageProvisionError, "unexpected profile"):
                wrong._validate_profile(root)

    def test_provisioner_still_refuses_profile_without_developer_remote_package_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_path = root / "etc/greia-os/image-profile.json"
            profile_path.parent.mkdir(parents=True)
            profile_path.write_text(
                json.dumps(
                    {
                        "profile": {"profile_id": "acer-aspire-one-i386-dev"},
                        "package_sets": {"target": ["platform-base"]},
                    }
                ),
                encoding="utf-8",
            )
            provisioner = DeveloperImageProvisioner(
                ProvisionConfig(
                    image=root / "unused.img",
                    output_dir=root / "out",
                    expected_profile="acer-aspire-one-i386-dev",
                )
            )
            with self.assertRaisesRegex(DeveloperImageProvisionError, "developer-remote"):
                provisioner._validate_profile(root)

    def test_developer_builder_passes_exact_profile_to_canonical_builder_and_provisioner(self) -> None:
        wrapper = (PROJECT_ROOT / "build/build-developer-image.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn('PROFILE="${2:-modern-amd64-dev}"', wrapper)
        self.assertIn('"$SCRIPT_DIR/build-image.sh" "$PROFILE" "$OUTPUT_DIR"', wrapper)
        self.assertIn('--expected-profile "$PROFILE"', wrapper)


if __name__ == "__main__":
    unittest.main()
