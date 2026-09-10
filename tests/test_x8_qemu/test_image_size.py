"""B3-SPANSYNC regression: the harness MBR table derives from the plan.

Source scope only (no root, no loop, no device contact): assembles in
tmp through the real production owner (``assemble_disposable_image``)
and asserts file size == plan bytes == derived span with zero
``max(...)`` growth; parses the four MBR extents back from the written
bytes and asserts they equal the plan-derived extents, are contiguous
from the 1 MiB reserve with persist remainder-fill (production
``parted`` semantics), and fit the file. RED controls pin the pre-fix
combination (64 MiB file vs the plan table) and tampered geometry
through the fail-closed guard, each by break -> RED -> restore -> GREEN.
"""

from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from tools.x8_qemu.lifecycle import (
    LifecycleHarnessError,
    _mbr_table_span_bytes,
    assemble_disposable_image,
    plan_mbr_sector_extents,
    write_mbr_table_for_plan,
)
from tools.x8_qemu.runner import layout_plan_for_device

PRE_FIX_IMAGE_BYTES = 64 * 1024 * 1024
PLAN_DEVICE_BYTES = 3072 * 1024 * 1024
SECTOR_BYTES = 512


def _read_mbr_extents(image: Path) -> list[tuple[int, int]]:
    """Parse the four MBR partition extents back from the written bytes."""
    with open(image, "rb") as handle:
        table = handle.read(512)
    extents = []
    for number in (1, 2, 3, 4):
        entry = table[446 + (number - 1) * 16: 446 + number * 16]
        _, _, _, _, start, count = struct.unpack("<B3sB3sII", entry)
        extents.append((start, count))
    return extents


class DisposableImageSizeTests(unittest.TestCase):
    def test_assembled_image_equals_plan_bytes_equals_derived_span(self) -> None:
        """Production path: plan is the single source of truth, no fudge."""
        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(str(manifest["image"]))
            self.assertTrue(image.is_file())
            file_size = image.stat().st_size
            plan = layout_plan_for_device(
                max(PRE_FIX_IMAGE_BYTES, PLAN_DEVICE_BYTES)
            )
            plan_bytes = int(getattr(plan, "device_size_bytes"))
            span_bytes = _mbr_table_span_bytes(plan)
            # No max(...) growth past the plan: all three agree exactly.
            self.assertEqual(file_size, plan_bytes)
            self.assertEqual(span_bytes, plan_bytes)
            # Parsed-back extents equal the plan-derived extents ...
            expected = plan_mbr_sector_extents(plan)
            parsed = _read_mbr_extents(image)
            for number, (start, count) in enumerate(parsed, start=1):
                self.assertEqual(
                    (start, count), expected[number],
                    f"partition {number} differs from the plan derivation",
                )
            # ... are contiguous from the 1 MiB reserve (no p1->p2 gap) ...
            self.assertEqual(parsed[0][0], 2048)
            for first, second in zip(parsed, parsed[1:]):
                self.assertEqual(second[0], first[0] + first[1])
            # ... persist remainder-fills the device ...
            self.assertEqual(
                parsed[3][1] * SECTOR_BYTES, int(plan.remainder_bytes())
            )
            self.assertEqual(
                parsed[3][0] + parsed[3][1], file_size // SECTOR_BYTES
            )
            # ... and every extent fits the file, which is exactly what
            # live partprobe enforces.
            file_sectors = file_size // SECTOR_BYTES
            for number, (start, count) in enumerate(parsed, start=1):
                self.assertGreater(count, 0, f"partition {number} is empty")
                self.assertLessEqual(
                    start + count,
                    file_sectors,
                    f"partition {number} extent ends outside the disk",
                )

    def test_prefixed_undersized_file_refused_by_guard(self) -> None:
        """Pre-fix combination (64 MiB file vs plan table) REDs at assembly."""
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "small.img"
            with open(image, "wb") as handle:
                handle.truncate(PRE_FIX_IMAGE_BYTES)
            plan = layout_plan_for_device(PLAN_DEVICE_BYTES)
            with self.assertRaises(LifecycleHarnessError):
                write_mbr_table_for_plan(image, plan=plan)

    def test_truncated_and_tampered_geometry_break_restore_round_trip(self) -> None:
        """Break -> RED -> restore -> GREEN on the sizing invariant."""
        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(str(manifest["image"]))
            plan = layout_plan_for_device(
                max(PRE_FIX_IMAGE_BYTES, PLAN_DEVICE_BYTES)
            )
            expected = plan_mbr_sector_extents(plan)
            with open(image, "rb") as _sector_handle:
                intact_table = _sector_handle.read(512)
            # BREAK 1: shrink the file 1 MiB below the plan span.
            with open(image, "r+b") as handle:
                handle.truncate(int(getattr(plan, "device_size_bytes")) - 1024 * 1024)
            # RED: the fail-closed guard refuses the sub-span file.
            with self.assertRaises(LifecycleHarnessError):
                write_mbr_table_for_plan(image, plan=plan)
            # RESTORE the exact plan size and rewrite the derived table.
            with open(image, "r+b") as handle:
                handle.truncate(int(getattr(plan, "device_size_bytes")))
            write_mbr_table_for_plan(image, plan=plan)
            # GREEN: parsed extents equal the derivation and fit the file.
            parsed = _read_mbr_extents(image)
            for number, (start, count) in enumerate(parsed, start=1):
                self.assertEqual((start, count), expected[number])
            # BREAK 2: tamper p4 with the pre-fix divergent overshoot
            # (fixed 1 GiB count past the declarative remainder end).
            tampered = bytearray(intact_table)
            tampered[446 + 3 * 16 + 8: 446 + 3 * 16 + 16] = struct.pack(
                "<II", 4263936, 2097152
            )
            with open(image, "r+b") as handle:
                handle.seek(0)
                handle.write(bytes(tampered))
            divergent = _read_mbr_extents(image)
            # RED: the divergent p4 no longer matches the derivation and
            # its end (sector 6361088) exceeds the plan-sized file
            # (6291456 sectors) — exactly what live partprobe would refuse.
            self.assertNotEqual(
                divergent[3], expected[4],
                "tampered p4 must differ from the plan derivation",
            )
            self.assertGreater(
                divergent[3][0] + divergent[3][1],
                image.stat().st_size // SECTOR_BYTES,
            )
            # RESTORE the derived table and re-prove GREEN.
            write_mbr_table_for_plan(image, plan=plan)
            restored = _read_mbr_extents(image)
            for number, (start, count) in enumerate(restored, start=1):
                self.assertEqual((start, count), expected[number])


if __name__ == "__main__":
    unittest.main()
