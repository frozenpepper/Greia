"""Read-only Raspberry Pi firmware evidence tests. No real /proc or devices."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_platform.pi_boot_observation import PiBootObservation, PiBootObservationError
from greia_platform.pi_boot_assets import render_pi_autoboot


A = 'ab12cd34-05'
B = 'ab12cd34-06'


class PiFirmwareObservationTests(unittest.TestCase):
    def _observation(self, temp: Path, *, partition: int, tryboot: int,
                     root: str, autoboot: str):
        props = temp / 'properties'
        props.mkdir()
        (props / 'partition').write_bytes(partition.to_bytes(4, 'big'))
        (props / 'tryboot').write_bytes(tryboot.to_bytes(4, 'big'))
        cmd = temp / 'cmdline'
        cmd.write_text(f'console=tty1 root=PARTUUID={root} rootwait ro\n', encoding='ascii')
        return PiBootObservation.read(bootloader_properties=props, cmdline_file=cmd)

    def test_normal_and_trial_then_promoted_slot(self):
        for partition, trial, root, normal, expected in (
            (2, 0, A, 'A', 'A'),
            (3, 1, B, 'A', 'B'),
            (3, 0, B, 'B', 'B'),
            (2, 1, A, 'B', 'A'),
        ):
            with self.subTest(partition=partition, trial=trial, normal=normal), tempfile.TemporaryDirectory() as td:
                actual = self._observation(Path(td), partition=partition, tryboot=trial,
                                           root=root, autoboot=normal)
                self.assertEqual(expected, actual.checked_slot(
                    autoboot_text=render_pi_autoboot(normal),
                    system_a_partuuid=A, system_b_partuuid=B))

    def test_mismatched_firmware_partition_never_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            obs = self._observation(Path(td), partition=2, tryboot=1, root=A, autoboot='A')
            with self.assertRaisesRegex(PiBootObservationError, 'contradicts'):
                obs.checked_slot(autoboot_text=render_pi_autoboot('A'),
                                 system_a_partuuid=A, system_b_partuuid=B)

    def test_mismatched_root_never_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            obs = self._observation(Path(td), partition=3, tryboot=1, root=A, autoboot='A')
            with self.assertRaisesRegex(PiBootObservationError, 'root PARTUUID'):
                obs.checked_slot(autoboot_text=render_pi_autoboot('A'),
                                 system_a_partuuid=A, system_b_partuuid=B)

    def test_other_disk_system_identity_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            obs = self._observation(Path(td), partition=2, tryboot=0, root=A, autoboot='A')
            with self.assertRaisesRegex(PiBootObservationError, 'same MBR disk'):
                obs.checked_slot(autoboot_text=render_pi_autoboot('A'),
                                 system_a_partuuid=A, system_b_partuuid='fedcba98-06')

    def test_wrong_width_binary_properties_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            self._observation(temp, partition=2, tryboot=0, root=A, autoboot='A')
            (temp / 'properties' / 'tryboot').write_bytes(b'0')
            with self.assertRaisesRegex(PiBootObservationError, '4 binary bytes'):
                PiBootObservation.read(bootloader_properties=temp / 'properties', cmdline_file=temp / 'cmdline')

    def test_duplicate_root_hints_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            self._observation(temp, partition=2, tryboot=0, root=A, autoboot='A')
            (temp / 'cmdline').write_text(f'root=PARTUUID={A} root=PARTUUID={B}', encoding='ascii')
            with self.assertRaisesRegex(PiBootObservationError, 'exactly one'):
                PiBootObservation.read(bootloader_properties=temp / 'properties', cmdline_file=temp / 'cmdline')

    def test_outside_slot_boot_partition_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            temp=Path(td)
            with self.assertRaisesRegex(PiBootObservationError, 'outside'):
                self._observation(temp, partition=1, tryboot=0, root=A, autoboot='A')

    def test_unknown_trial_flag_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            temp=Path(td)
            with self.assertRaisesRegex(PiBootObservationError, 'neither 0 nor 1'):
                self._observation(temp, partition=2, tryboot=10, root=A, autoboot='A')


if __name__ == '__main__':
    unittest.main()
