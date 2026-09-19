"""R4-A-BOOT: Acer legacy boot-control 64 MiB product contract (A21).

Binding lifecycle plan A21 fixes the legacy i386 MBR layout at 1 MiB
label/GRUB reservation + 64 MiB boot-control + 2x1536 MiB system slots +
PERSIST remainder (minimum 1024 MiB), i.e. 4161 MiB minimum device.
This test locks those facts literally so reverting BOOT_CONTROL_BYTES to
32 MiB fails. No mounts, Docker, or physical hardware involved.
"""

from __future__ import annotations

import unittest

from greia_installer.layout import (
    LABEL_RESERVED_BYTES,
    MIB,
    LayoutError,
    LegacyBiosAbAdapter,
    ProfileSizing,
    plan_for_profile,
)

#: A21 product facts, stated literally (never derived from the constant
#: under test, so drift fails loudly).
BOOT_CONTROL_64_MIB = 64 * MIB
SLOT_1536_MIB = 1536 * MIB
PERSIST_1024_MIB = 1024 * MIB
MINIMUM_DEVICE_4161_MIB = 4161 * MIB


def _acer_sizing() -> ProfileSizing:
    return ProfileSizing(
        layout_adapter_id="legacy-bios-ab-v1",
        slot_bytes=SLOT_1536_MIB,
        persist_minimum_bytes=PERSIST_1024_MIB,
        boot_backend="grub-ab-v1",
    )


class LegacyBootControlContractTests(unittest.TestCase):
    def test_boot_control_is_the_fixed_64_mib_product_default(self) -> None:
        # Literal assertion: must not derive from the constant itself.
        self.assertEqual(LegacyBiosAbAdapter.BOOT_CONTROL_BYTES, 64 * MIB)
        self.assertEqual(LegacyBiosAbAdapter.BOOT_CONTROL_BYTES, 67108864)

    def test_minimum_device_facts_come_from_adapter_and_planner(self) -> None:
        sizing = _acer_sizing()
        # Code derives the minimum from adapter/planner facts (no hand
        # arithmetic in production); here we prove that derived value
        # equals the literal A21 contract.
        derived_minimum = (
            LABEL_RESERVED_BYTES
            + LegacyBiosAbAdapter.BOOT_CONTROL_BYTES
            + 2 * sizing.slot_bytes
            + sizing.persist_minimum_bytes
        )
        self.assertEqual(derived_minimum, MINIMUM_DEVICE_4161_MIB)
        self.assertEqual(derived_minimum, 4363124736)

    def test_minimum_device_boundary_through_plan_for_profile(self) -> None:
        sizing = _acer_sizing()
        with self.assertRaisesRegex(LayoutError, "does not fit"):
            plan_for_profile(sizing, device_size_bytes=MINIMUM_DEVICE_4161_MIB - 1)
        plan = plan_for_profile(sizing, device_size_bytes=MINIMUM_DEVICE_4161_MIB)
        self.assertEqual(plan.remainder_bytes(), PERSIST_1024_MIB)
        self.assertEqual(plan.remainder_bytes(), 1073741824)
        self.assertEqual(plan.by_role("boot-control").size_bytes, 64 * MIB)


if __name__ == "__main__":
    unittest.main()
