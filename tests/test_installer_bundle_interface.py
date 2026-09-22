"""Session 04: installer-image release-bundle interface contract (source scope).

The A/B installer medium must consume the release artifact through one
explicit, source-owned input instead of undocumented environment
archaeology:

- ``build/build-installer-image.sh`` accepts ``--release-bundle PATH``
  as normal production input;
- the bundle is v3-inspected with a profile-identity match before any
  disk mutation;
- ``GREIA_AB_RELEASE_BUNDLE_SRC`` remains only as an explicit override
  for tests/harness wiring;
- the medium still carries the exact validated bundle bytes and records
  its SHA in the report;
- both wrapper builders forward the flag without changing their
  boot-critical recipes.
"""

from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class InstallerBundleInterfaceTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (PROJECT_ROOT / relative).read_text(encoding="utf-8")

    def test_canonical_builder_takes_explicit_release_bundle_flag(self) -> None:
        builder = self.read("build/build-installer-image.sh")
        self.assertIn("--release-bundle", builder)
        self.assertIn("RELEASE_BUNDLE_FLAG", builder)
        # Normal production input is the flag; the env var is only a
        # fallback override, never the sole required mechanism.
        self.assertIn("GREIA_AB_RELEASE_BUNDLE_SRC", builder)
        self.assertIn(
            "pass --release-bundle with the unsigned deterministic",
            builder,
        )

    def test_canonical_builder_validates_bundle_before_disk_mutation(self) -> None:
        builder = self.read("build/build-installer-image.sh")
        self.assertIn("inspect_update_bundle", builder)
        self.assertIn("does not match image profile", builder)
        # Validation order: profile resolve -> bundle authority check ->
        # target build. The check must precede the expensive target-image
        # build, not hide after debootstrap.
        resolve = builder.index('compose_resolve_profile "$PROFILE_PATH"')
        validated = builder.index("A/B release-bundle authority")
        target_build = builder.index('"$SCRIPT_DIR/build-image.sh"')
        self.assertLess(resolve, validated)
        self.assertLess(validated, target_build)

    def test_canonical_builder_still_embeds_exact_validated_bundle(self) -> None:
        builder = self.read("build/build-installer-image.sh")
        self.assertIn(
            'cp "$AB_RELEASE_SRC" "$USB_MOUNT/payload/greia-release.greiaupdate"',
            builder,
        )
        self.assertIn("installer_ab_bundle_sha256=${ab_bundle_sha256", builder)

    def test_wrappers_forward_release_bundle_without_recipe_change(self) -> None:
        legacy = self.read("build/build-legacy-x86-sd-installer.sh")
        self.assertIn("--release-bundle", legacy)
        self.assertIn(
            '"$SCRIPT_DIR/build-installer-image.sh" "$PROFILE" "$OUTPUT_DIR"',
            legacy,
        )
        dev = self.read("tools/build-development-installer.sh")
        self.assertIn("--release-bundle", dev)
        # Physically proven routing untouched.
        self.assertIn('bash "$LEGACY_BUILDER" "$PROFILE_ID"', dev)
        self.assertIn('bash "$CANONICAL_BUILDER" "$PROFILE_PATH"', dev)


if __name__ == "__main__":
    unittest.main()
