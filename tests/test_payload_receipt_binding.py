"""R4-G-RECEIPT: profile-based builds bind payload capacity facts to the artifact.

Proves, through the normal ``tools/greia_update.py build --profile-file``
command, that size facts are derived from the producer receipt
(``build-payload --receipt-output``) and verified against the real payload
artifact — never trusted from operator typing:

- correct receipt builds; the manifest carries the receipt-derived facts
  and the finalized-slot capacity owner agrees on the identical total;
- understated receipt size (claims less than the measured decompressed
  length) refuses with no output published;
- digest mismatch refuses; compressed-size mismatch refuses;
- profile mismatch refuses; release-id mismatch refuses;
- manually typed sizes without a receipt refuse on the normal path;
- a manually typed understated override beside a correct receipt refuses;
- the explicit DEVELOPER-ONLY seam keeps tiny fixtures working.

Production path crossed: ``main(build --profile-file --payload-receipt)``
-> ``_resolve_payload_facts`` (receipt shape/identity/digest/decompressed
verification) -> ``_check_profile_capacity`` (single owner
``require_finalized_slot_capacity``) -> ``build_update_bundle``.

No mounts, Docker, signing, network or physical work. All fixtures live in
disposable tmpdirs; payloads are small real zstd streams.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPDATE_TOOL_PATH = PROJECT_ROOT / "tools" / "greia_update.py"
RELEASE_TOOL_PATH = PROJECT_ROOT / "tools" / "build_release.py"

_update_spec = importlib.util.spec_from_file_location(
    "greia_update_tool_receipt", UPDATE_TOOL_PATH
)
assert _update_spec is not None and _update_spec.loader is not None
update_module = importlib.util.module_from_spec(_update_spec)
sys.modules[_update_spec.name] = update_module
_update_spec.loader.exec_module(update_module)

_release_spec = importlib.util.spec_from_file_location(
    "build_release_tool_receipt", RELEASE_TOOL_PATH
)
assert _release_spec is not None and _release_spec.loader is not None
release_module = importlib.util.module_from_spec(_release_spec)
sys.modules[_release_spec.name] = release_module
_release_spec.loader.exec_module(release_module)

from greia_installer.layout import require_finalized_slot_capacity  # noqa: E402

try:
    import zstandard

    _ZSTANDARD = True
except ImportError:  # pragma: no cover
    _ZSTANDARD = False

ACER_PROFILE = PROJECT_ROOT / "build" / "profiles" / "acer-aspire-one-i386-ab.toml"
GENERIC_PROFILE = PROJECT_ROOT / "build" / "profiles" / "legacy-x86-i686.toml"

VERSION = "0.14.0"
RELEASE_ID = f"greia-{VERSION}"
HEADROOM = 1024 * 1024


def _compress(data: bytes) -> bytes:
    assert _ZSTANDARD, "zstandard backend is required for receipt fixtures"
    return zstandard.ZstdCompressor().compress(data)


def _write_payload(directory: Path, raw: bytes, *, name: str = "payload.ext4.zst") -> Path:
    payload = directory / name
    payload.write_bytes(_compress(raw))
    return payload


def _write_receipt(
    directory: Path,
    payload: Path,
    *,
    name: str = "payload.receipt.json",
    profile_id: str = "acer-aspire-one-i386-ab",
    release_id: str = RELEASE_ID,
    uncompressed_override: int | None = None,
    minimum_override: int | None = None,
    sha_override: str | None = None,
    compressed_override: int | None = None,
) -> tuple[Path, dict]:
    raw = payload.read_bytes()
    uncompressed = len(zstandard.ZstdDecompressor().decompress(raw))
    minimum = uncompressed + HEADROOM
    receipt = {
        "schema_version": 1,
        "payload_sha256": hashlib.sha256(raw).hexdigest(),
        "payload_compressed_bytes": len(raw),
        "payload_uncompressed_bytes": uncompressed,
        "minimum_slot_bytes": minimum,
        "profile_id": profile_id,
        "release_id": release_id,
    }
    if uncompressed_override is not None:
        receipt["payload_uncompressed_bytes"] = uncompressed_override
    if minimum_override is not None:
        receipt["minimum_slot_bytes"] = minimum_override
    if sha_override is not None:
        receipt["payload_sha256"] = sha_override
    if compressed_override is not None:
        receipt["payload_compressed_bytes"] = compressed_override
    path = directory / name
    path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path, receipt


def _build_argv(
    payload: Path,
    *,
    profile: Path,
    output: Path,
    receipt: Path | None = None,
    base: int | None = None,
    minimum: int | None = None,
    developer: bool = False,
    release_id: str | None = None,
) -> list[str]:
    argv = [
        "build",
        "--payload",
        str(payload),
        "--profile-file",
        str(profile),
        "--version",
        VERSION,
        "--persist-read-min",
        "1",
        "--persist-read-max",
        "1",
        "--persist-write",
        "1",
        "--output",
        str(output),
    ]
    if receipt is not None:
        argv.extend(["--payload-receipt", str(receipt)])
    if base is not None:
        argv.extend(["--payload-uncompressed-bytes", str(base)])
    if minimum is not None:
        argv.extend(["--minimum-slot-bytes", str(minimum)])
    if developer:
        argv.append("--developer-allow-unverified-payload-facts")
    if release_id is not None:
        argv.extend(["--release-id", release_id])
    return argv


def _build_explicit_argv(
    payload: Path,
    *,
    output: Path,
    profile: str = "acer-aspire-one-i386-ab",
    family: str = "x86",
    architecture: str = "i386",
    receipt: Path | None = None,
    base: int | None = None,
    minimum: int | None = None,
    developer: bool = False,
    release_id: str | None = None,
) -> list[str]:
    """Explicit-identity argv (no --profile-file; DEVELOPER-ONLY low-level seam)."""
    argv = [
        "build",
        "--payload",
        str(payload),
        "--platform-family",
        family,
        "--architecture",
        architecture,
        "--profile",
        profile,
        "--version",
        VERSION,
        "--persist-read-min",
        "1",
        "--persist-read-max",
        "1",
        "--persist-write",
        "1",
        "--output",
        str(output),
    ]
    if receipt is not None:
        argv.extend(["--payload-receipt", str(receipt)])
    if base is not None:
        argv.extend(["--payload-uncompressed-bytes", str(base)])
    if minimum is not None:
        argv.extend(["--minimum-slot-bytes", str(minimum)])
    if developer:
        argv.append("--developer-allow-unverified-payload-facts")
    if release_id is not None:
        argv.extend(["--release-id", release_id])
    return argv


class PayloadReceiptBindingTests(unittest.TestCase):
    def test_receipt_schema_is_pinned_across_producer_and_consumer(self) -> None:
        from greia_platform.payload_receipt import (
            PAYLOAD_RECEIPT_SCHEMA_VERSION as SHARED_VERSION,
        )

        self.assertEqual(release_module.PAYLOAD_RECEIPT_SCHEMA_VERSION, SHARED_VERSION)
        self.assertEqual(update_module.PAYLOAD_RECEIPT_SCHEMA_VERSION, SHARED_VERSION)
        self.assertEqual(SHARED_VERSION, 1)

    def test_correct_receipt_builds_with_receipt_derived_facts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            raw = b"greia-receipt-seed-" * 4096
            payload = _write_payload(tmp, raw)
            receipt_path, receipt = _write_receipt(tmp, payload)
            output = tmp / "out.greiaupdate"
            rc = update_module.main(
                _build_argv(payload, profile=ACER_PROFILE, output=output, receipt=receipt_path)
            )
            self.assertEqual(rc, 0)
            self.assertTrue(output.is_file())
            from greia_platform.system_updates import inspect_update_bundle

            inspected = inspect_update_bundle(output)
            self.assertEqual(
                inspected.manifest.payload_uncompressed_bytes,
                receipt["payload_uncompressed_bytes"],
            )
            self.assertEqual(
                inspected.manifest.payload_minimum_slot_bytes,
                receipt["minimum_slot_bytes"],
            )
            self.assertEqual(inspected.manifest.profile, "acer-aspire-one-i386-ab")
            # The capacity owner decides on the identical receipt-derived facts.
            owner_required = require_finalized_slot_capacity(
                slot_bytes=1610612736,
                base_bytes=int(receipt["payload_uncompressed_bytes"]),
                minimum_slot_bytes=int(receipt["minimum_slot_bytes"]),
                support_installed_bytes=0,
            )
            self.assertEqual(
                owner_required,
                max(
                    int(receipt["payload_uncompressed_bytes"]),
                    int(receipt["minimum_slot_bytes"]),
                )
                + 64 * 1024 * 1024
                + 16 * 1024 * 1024,
            )

    def test_understated_receipt_size_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            raw = b"greia-receipt-seed-" * 4096
            payload = _write_payload(tmp, raw)
            actual = len(zstandard.ZstdDecompressor().decompress(payload.read_bytes()))
            receipt_path, _ = _write_receipt(
                tmp, payload, uncompressed_override=actual - 1000
            )
            output = tmp / "out.greiaupdate"
            rc = update_module.main(
                _build_argv(payload, profile=ACER_PROFILE, output=output, receipt=receipt_path)
            )
            self.assertEqual(rc, 2)
            self.assertFalse(output.exists())

    def test_digest_mismatch_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            payload = _write_payload(tmp, b"greia-receipt-seed-" * 4096)
            receipt_path, _ = _write_receipt(tmp, payload, sha_override="0" * 64)
            output = tmp / "out.greiaupdate"
            rc = update_module.main(
                _build_argv(payload, profile=ACER_PROFILE, output=output, receipt=receipt_path)
            )
            self.assertEqual(rc, 2)
            self.assertFalse(output.exists())

    def test_compressed_size_mismatch_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            payload = _write_payload(tmp, b"greia-receipt-seed-" * 4096)
            receipt_path, receipt = _write_receipt(tmp, payload)
            receipt["payload_compressed_bytes"] = (
                int(receipt["payload_compressed_bytes"]) + 1
            )
            receipt_path.write_text(
                json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
            )
            output = tmp / "out.greiaupdate"
            rc = update_module.main(
                _build_argv(payload, profile=ACER_PROFILE, output=output, receipt=receipt_path)
            )
            self.assertEqual(rc, 2)
            self.assertFalse(output.exists())

    def test_profile_mismatch_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            payload = _write_payload(tmp, b"greia-receipt-seed-" * 4096)
            receipt_path, _ = _write_receipt(tmp, payload, profile_id="legacy-x86-i686")
            output = tmp / "out.greiaupdate"
            rc = update_module.main(
                _build_argv(payload, profile=ACER_PROFILE, output=output, receipt=receipt_path)
            )
            self.assertEqual(rc, 2)
            self.assertFalse(output.exists())

    def test_release_mismatch_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            payload = _write_payload(tmp, b"greia-receipt-seed-" * 4096)
            receipt_path, _ = _write_receipt(tmp, payload, release_id="greia-9.9.9")
            output = tmp / "out.greiaupdate"
            rc = update_module.main(
                _build_argv(payload, profile=ACER_PROFILE, output=output, receipt=receipt_path)
            )
            self.assertEqual(rc, 2)
            self.assertFalse(output.exists())

    def test_manual_sizes_without_receipt_refused_on_normal_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            payload = _write_payload(tmp, b"greia-receipt-seed-" * 1024)
            output = tmp / "out.greiaupdate"
            rc = update_module.main(
                _build_argv(
                    payload,
                    profile=ACER_PROFILE,
                    output=output,
                    base=1000000,
                    minimum=2000000,
                )
            )
            self.assertEqual(rc, 2)
            self.assertFalse(output.exists())

    def test_understated_manual_override_beside_correct_receipt_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            raw = b"greia-receipt-seed-" * 4096
            payload = _write_payload(tmp, raw)
            receipt_path, receipt = _write_receipt(tmp, payload)
            output = tmp / "out.greiaupdate"
            rc = update_module.main(
                _build_argv(
                    payload,
                    profile=ACER_PROFILE,
                    output=output,
                    receipt=receipt_path,
                    base=int(receipt["payload_uncompressed_bytes"]) - 1000,
                )
            )
            self.assertEqual(rc, 2)
            self.assertFalse(output.exists())

    def test_matching_manual_sizes_beside_receipt_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            payload = _write_payload(tmp, b"greia-receipt-seed-" * 4096)
            receipt_path, receipt = _write_receipt(tmp, payload)
            output = tmp / "out.greiaupdate"
            rc = update_module.main(
                _build_argv(
                    payload,
                    profile=ACER_PROFILE,
                    output=output,
                    receipt=receipt_path,
                    base=int(receipt["payload_uncompressed_bytes"]),
                    minimum=int(receipt["minimum_slot_bytes"]),
                )
            )
            self.assertEqual(rc, 0)
            self.assertTrue(output.is_file())

    def test_producer_receipt_functions_bind_real_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            raw = b"producer-proof-" * 2048
            payload = _write_payload(tmp, raw)
            uncompressed = len(zstandard.ZstdDecompressor().decompress(payload.read_bytes()))
            receipt = release_module.build_payload_receipt(
                payload_path=payload,
                uncompressed_bytes=uncompressed,
                minimum_slot_bytes=uncompressed + HEADROOM,
                profile_id="acer-aspire-one-i386-ab",
                release_id=RELEASE_ID,
            )
            self.assertEqual(receipt["schema_version"], 1)
            self.assertEqual(receipt["payload_sha256"], hashlib.sha256(payload.read_bytes()).hexdigest())
            self.assertEqual(receipt["payload_compressed_bytes"], payload.stat().st_size)
            self.assertEqual(receipt["payload_uncompressed_bytes"], uncompressed)
            target = tmp / "receipt.json"
            release_module.write_payload_receipt(target, receipt)
            reloaded = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(reloaded, receipt)
            with self.assertRaises(release_module.ReleaseBuildError):
                release_module.build_payload_receipt(
                    payload_path=payload,
                    uncompressed_bytes=uncompressed,
                    minimum_slot_bytes=uncompressed - 1,
                    profile_id="acer-aspire-one-i386-ab",
                    release_id=RELEASE_ID,
                )

    def test_developer_seam_keeps_tiny_framing_fixture_working(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            payload = tmp / "payload.ext4.zst"
            payload.write_bytes(b"\x28\xb5\x2f\xfd" + b"\x00" * 4096)
            output = tmp / "out.greiaupdate"
            rc = update_module.main(
                _build_argv(
                    payload,
                    profile=GENERIC_PROFILE,
                    output=output,
                    base=1000000,
                    minimum=1000000,
                    developer=True,
                )
            )
            self.assertEqual(rc, 0)
            self.assertTrue(output.is_file())

    def test_explicit_typed_without_receipt_and_without_seam_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            payload = _write_payload(tmp, b"greia-explicit-seed-" * 1024)
            output = tmp / "explicit.greiaupdate"
            rc = update_module.main(
                _build_explicit_argv(payload, output=output, base=1000000, minimum=2000000)
            )
            self.assertEqual(rc, 2)
            self.assertFalse(output.exists())

    def test_explicit_with_developer_seam_succeeds_as_low_level_build(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            payload = _write_payload(tmp, b"greia-explicit-seed-" * 1024)
            output = tmp / "explicit.greiaupdate"
            rc = update_module.main(
                _build_explicit_argv(
                    payload, output=output, base=1000000, minimum=1000000, developer=True
                )
            )
            self.assertEqual(rc, 0)
            self.assertTrue(output.is_file())

    def test_explicit_correct_receipt_builds_with_receipt_facts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            raw = b"greia-explicit-seed-" * 4096
            payload = _write_payload(tmp, raw)
            receipt_path, receipt = _write_receipt(tmp, payload)
            output = tmp / "explicit.greiaupdate"
            rc = update_module.main(
                _build_explicit_argv(payload, output=output, receipt=receipt_path)
            )
            self.assertEqual(rc, 0)
            self.assertTrue(output.is_file())
            from greia_platform.system_updates import inspect_update_bundle

            inspected = inspect_update_bundle(output)
            self.assertEqual(
                inspected.manifest.payload_uncompressed_bytes,
                receipt["payload_uncompressed_bytes"],
            )
            self.assertEqual(
                inspected.manifest.payload_minimum_slot_bytes,
                receipt["minimum_slot_bytes"],
            )

    def test_explicit_receipt_mismatches_refuse(self) -> None:
        cases = (
            "understated",
            "digest",
            "compressed",
            "profile",
            "release",
        )
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                tmp = Path(directory)
                payload = _write_payload(tmp, b"greia-explicit-seed-" * 4096)
                kwargs: dict = {}
                if case == "understated":
                    actual = len(
                        zstandard.ZstdDecompressor().decompress(payload.read_bytes())
                    )
                    kwargs["uncompressed_override"] = actual - 1000
                elif case == "digest":
                    kwargs["sha_override"] = "0" * 64
                elif case == "profile":
                    kwargs["profile_id"] = "legacy-x86-i686"
                elif case == "release":
                    kwargs["release_id"] = "greia-9.9.9"
                receipt_path, receipt = _write_receipt(tmp, payload, **kwargs)
                if case == "compressed":
                    receipt["payload_compressed_bytes"] = (
                        int(receipt["payload_compressed_bytes"]) + 1
                    )
                    receipt_path.write_text(
                        json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8",
                    )
                output = tmp / "explicit.greiaupdate"
                rc = update_module.main(
                    _build_explicit_argv(payload, output=output, receipt=receipt_path)
                )
                self.assertEqual(rc, 2)
                self.assertFalse(output.exists())

    def test_explicit_help_marks_developer_only_seam(self) -> None:
        import io
        from contextlib import redirect_stdout

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            try:
                update_module.main(["build", "--help"])
            except SystemExit as exc:
                self.assertEqual(exc.code, 0)
        text = buffer.getvalue()
        self.assertIn("DEVELOPER-ONLY", text)
        self.assertIn("--platform-family", text)


if __name__ == "__main__":
    unittest.main()
