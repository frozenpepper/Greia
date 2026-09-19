"""R4-B-CAPACITY: installed-target capacity is layout-owned, not image-owned.

Proves the separation through the production owners: the Acer 4161 MiB
installed-disk minimum comes from the real layout adapter via the single
canonical owner (greia_installer.layout.minimum_device_bytes_for_profile),
a small image.size_mib keeps an otherwise valid A/B storage profile valid,
and truly undersized target devices are still refused at install time by
plan_for_profile. No mounts, Docker, or physical hardware involved.
"""

from __future__ import annotations

import dataclasses
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import build_profile  # noqa: E402
from build_profile import BuildProfile  # noqa: E402

from greia_installer.layout import (  # noqa: E402
    LayoutError,
    ProfileSizing,
    minimum_device_bytes_for_profile,
    plan_for_profile,
)

ACER_AB_PROFILE = PROJECT_ROOT / "build/profiles/acer-aspire-one-i386-ab.toml"

MIB = 1024 * 1024

#: A21 product facts, stated literally (never derived from the owner under
#: test, so drift fails loudly).
MINIMUM_DEVICE_4161_MIB = 4161 * MIB
MINIMUM_DEVICE_4161_BYTES = 4363124736


def _acer_sizing() -> ProfileSizing:
    profile = BuildProfile.load(ACER_AB_PROFILE)
    return ProfileSizing(
        layout_adapter_id=profile.storage.layout_adapter,
        slot_bytes=profile.storage.system_slot_bytes,
        persist_minimum_bytes=profile.storage.persistent_minimum_bytes,
        boot_backend=profile.updates.boot_backend,
    )


class TargetCapacitySeparationTests(unittest.TestCase):
    def test_acer_minimum_comes_from_the_real_adapter_owner(self) -> None:
        sizing = _acer_sizing()
        self.assertEqual(sizing.slot_bytes, 1536 * MIB)
        self.assertEqual(sizing.persist_minimum_bytes, 1024 * MIB)
        minimum = minimum_device_bytes_for_profile(sizing)
        self.assertEqual(minimum, MINIMUM_DEVICE_4161_MIB)
        self.assertEqual(minimum, MINIMUM_DEVICE_4161_BYTES)

    def test_small_image_size_mib_keeps_ab_profile_valid(self) -> None:
        profile = BuildProfile.load(ACER_AB_PROFILE)
        # The corrected artifact size sits far below the installed minimum.
        self.assertLess(profile.image.size_mib, 4161)
        # Shrinking further (still above the resource floor) stays valid:
        # image.size_mib is never validated against installed capacity.
        smaller = dataclasses.replace(
            profile,
            image=dataclasses.replace(profile.image, size_mib=1500),
        )
        smaller.validate()
        self.assertEqual(smaller.image.size_mib, 1500)

    def test_image_at_resource_floor_still_fails_closed(self) -> None:
        profile = BuildProfile.load(ACER_AB_PROFILE)
        floored = dataclasses.replace(
            profile,
            image=dataclasses.replace(
                profile.image, size_mib=profile.resources.required_core_mib
            ),
        )
        with self.assertRaisesRegex(
            build_profile.BuildProfileError, "must exceed resources.required_core_mib"
        ):
            floored.validate()

    def test_undersized_device_still_refused_via_plan_for_profile(self) -> None:
        sizing = _acer_sizing()
        with self.assertRaisesRegex(LayoutError, "does not fit"):
            plan_for_profile(sizing, device_size_bytes=MINIMUM_DEVICE_4161_MIB - 1)
        plan = plan_for_profile(sizing, device_size_bytes=MINIMUM_DEVICE_4161_MIB)
        self.assertEqual(plan.remainder_bytes(), 1024 * MIB)

    def test_no_duplicate_target_capacity_table_in_build_profile(self) -> None:
        self.assertFalse(hasattr(build_profile, "_LAYOUT_OVERHEAD_BYTES"))

    def test_all_repository_profiles_still_validate(self) -> None:
        profiles = sorted((PROJECT_ROOT / "build/profiles").glob("*.toml"))
        self.assertGreaterEqual(len(profiles), 4)
        for path in profiles:
            with self.subTest(profile=path.name):
                BuildProfile.load(path)


if __name__ == "__main__":
    unittest.main()
