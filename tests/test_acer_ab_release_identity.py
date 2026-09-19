"""T09: Acer A/B release-identity guard (Repair I).

Proves the documented/normal bundle path derives the Acer A/B identity
from the one profile file and refuses to bundle an Acer-sized payload
under the smaller generic single-root profile.

Normal path crossed: ``tools/greia_update.py main(build --profile-file)``
-> ``_target_from_profile_file`` (profile/family/arch/board/slot) ->
``_check_profile_capacity`` (profile-owned slot bound) ->
``build_update_bundle``/``inspect_update_bundle`` (manifest identity).

No Docker, signing/keys, mounts, flashing or network involved.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = PROJECT_ROOT / "tools" / "greia_update.py"

spec = importlib.util.spec_from_file_location("greia_update_tool_t09", TOOL_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

ACER_PROFILE = PROJECT_ROOT / "build" / "profiles" / "acer-aspire-one-i386-ab.toml"
GENERIC_PROFILE = PROJECT_ROOT / "build" / "profiles" / "legacy-x86-i686.toml"

#: Lifecycle plan A21 product default: 1536 MiB A/B system slots.
ACER_SLOT_BYTES = 1610612736
#: Generic single-root slot bound (1 GiB).
GENERIC_SLOT_BYTES = 1073741824

#: Documented Acer example sizing (Session 02 docs): 1 GiB shrunk image
#: plus the 1 MiB finalization headroom (PAYLOAD_MIN_HEADROOM).
ACER_UNCOMPRESSED_BYTES = 1073741824
ACER_MINIMUM_BYTES = 1074790400

_ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


def _profile_slot_bytes(path: Path) -> int:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    return int(raw["storage"]["system_slot_bytes"])


def _make_payload(directory: Path) -> Path:
    # Tiny fixture: only valid zstd framing for the bundle seam. Real sizes
    # travel via the payload receipt in production; these tests exercise the
    # capacity owner with producer-typed facts through the explicit
    # DEVELOPER-ONLY unverified seam (--developer-allow-unverified-
    # payload-facts), never the normal production path.
    payload = directory / "payload.ext4.zst"
    payload.write_bytes(_ZSTD_MAGIC + b"\x00" * 4096)
    return payload


class AcerAbReleaseIdentityTests(unittest.TestCase):
    def test_real_profiles_carry_expected_slot_bounds(self) -> None:
        self.assertEqual(_profile_slot_bytes(ACER_PROFILE), ACER_SLOT_BYTES)
        self.assertEqual(_profile_slot_bytes(GENERIC_PROFILE), GENERIC_SLOT_BYTES)

    def test_profile_file_derives_board_and_slot_facts(self) -> None:
        acer = module._target_from_profile_file(ACER_PROFILE)
        self.assertEqual(acer.profile, "acer-aspire-one-i386-ab")
        self.assertEqual(acer.platform_family, "legacy-x86")
        self.assertEqual(acer.architecture, "i386")
        # Both x86 profiles use platform.board "none", which becomes
        # manifest board null (no specific board authority).
        self.assertIsNone(acer.board)
        self.assertEqual(acer.system_slot_bytes, ACER_SLOT_BYTES)
        generic = module._target_from_profile_file(GENERIC_PROFILE)
        self.assertEqual(generic.profile, "legacy-x86-i686")
        self.assertIsNone(generic.board)
        self.assertEqual(generic.system_slot_bytes, GENERIC_SLOT_BYTES)

    def test_profile_file_rejects_explicit_board_mixing(self) -> None:
        import argparse

        args = argparse.Namespace(
            profile_file=ACER_PROFILE,
            platform_family=None,
            architecture=None,
            profile=None,
            board="none",
        )
        with self.assertRaisesRegex(Exception, "profile-file.*not both"):
            module._resolve_target(args)

    def test_acer_sized_payload_refused_under_generic_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            payload = _make_payload(tmp)
            output = tmp / "greia-0.14.0-legacy-x86-i686.greiaupdate"
            rc = module.main(
                [
                    "build",
                    "--payload",
                    str(payload),
                    "--payload-uncompressed-bytes",
                    str(ACER_UNCOMPRESSED_BYTES),
                    "--minimum-slot-bytes",
                    str(ACER_MINIMUM_BYTES),
                    "--developer-allow-unverified-payload-facts",
                    "--profile-file",
                    str(GENERIC_PROFILE),
                    "--version",
                    "0.14.0",
                    "--persist-read-min",
                    "1",
                    "--persist-read-max",
                    "1",
                    "--persist-write",
                    "1",
                    "--output",
                    str(output),
                ]
            )
            # Normal-path refusal is fail-closed exit 2 with no bundle.
            self.assertEqual(rc, 2)
            self.assertFalse(output.exists())
            # Direct capacity predicate names the cross-profile refusal.
            target = module._target_from_profile_file(GENERIC_PROFILE)
            with self.assertRaisesRegex(Exception, "cross-profile"):
                module._check_profile_capacity(
                    target,
                    payload_uncompressed_bytes=ACER_UNCOMPRESSED_BYTES,
                    minimum_slot_bytes=ACER_MINIMUM_BYTES,
                )

    def test_same_acer_payload_accepted_under_acer_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            payload = _make_payload(tmp)
            output = tmp / "greia-0.14.0-acer-aspire-one-i386-ab.greiaupdate"
            rc = module.main(
                [
                    "build",
                    "--payload",
                    str(payload),
                    "--payload-uncompressed-bytes",
                    str(ACER_UNCOMPRESSED_BYTES),
                    "--minimum-slot-bytes",
                    str(ACER_MINIMUM_BYTES),
                    "--developer-allow-unverified-payload-facts",
                    "--profile-file",
                    str(ACER_PROFILE),
                    "--version",
                    "0.14.0",
                    "--persist-read-min",
                    "1",
                    "--persist-read-max",
                    "1",
                    "--persist-write",
                    "1",
                    "--output",
                    str(output),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(output.is_file())
            from greia_platform.system_updates import inspect_update_bundle

            inspected = inspect_update_bundle(output)
            self.assertEqual(inspected.manifest.profile, "acer-aspire-one-i386-ab")
            self.assertEqual(inspected.manifest.platform_family, "legacy-x86")
            self.assertEqual(inspected.manifest.architecture, "i386")
            self.assertIsNone(inspected.manifest.board)
            self.assertEqual(
                inspected.manifest.payload_minimum_slot_bytes, ACER_MINIMUM_BYTES
            )


if __name__ == "__main__":
    unittest.main()
