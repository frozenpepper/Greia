"""R4-G2-SUPPORT-BOUND: outer .greiaupdate manifest carries extracted_bytes_bound.

Proves through the real production seams:
- new builds emit the outer bound equal to the inner/shared-model value and
  inspect round-trips it;
- outer-vs-inner mismatch refuses before publication (no output) and at
  staging;
- absent outer bound keeps mid-stream preflight + order gate;
- pre-stream preflight fires before stream traversal (spy sees the outer
  bound, zero _extract_one writes on short space);
- payload-before-manifest with a valid outer bound stages (order lift).

All state stays in disposable tmpdirs; no mounts, no Docker.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from greia_installer import hardware_support_archive as _shared
from greia_platform import candidate_support as _candidate
from greia_platform.system_updates import (
    MANIFEST_NAME,
    UpdateBackendUnavailable,
    UpdateBundleError,
    UpdateManifest,
    build_update_bundle,
    inspect_update_bundle,
    SystemUpdateInbox,
)

_spec = importlib.util.spec_from_file_location(
    "build_release_tool_g2_bound",
    Path(__file__).resolve().parents[1] / "tools" / "build_release.py",
)
assert _spec is not None and _spec.loader is not None
_build_release = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _build_release
_spec.loader.exec_module(_build_release)

_FAMILY = "g2bound"
_ARCH = "g2arch"
_PROFILE = "g2profile"
_FIRMWARE = "firmware-g2"
_MICROCODE = "g2-microcode"


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _pool_tree(root: Path, *, name: str = "g2") -> Path:
    fw = b"g2-firmware-bytes"
    uc = b"g2-microcode-bytes"
    pool = root / f"pool-{name}"
    deb_dir = pool / "pool"
    deb_dir.mkdir(parents=True)
    fw_name = f"{_FIRMWARE}_1_all.deb"
    uc_name = f"{_MICROCODE}_1_amd64.deb"
    (deb_dir / fw_name).write_bytes(fw)
    (deb_dir / uc_name).write_bytes(uc)
    packages_payload = f"Package: {_FIRMWARE}\n".encode()
    packages_gzip_payload = b"gzip-placeholder"
    (pool / "Packages").write_bytes(packages_payload)
    (pool / "Packages.gz").write_bytes(packages_gzip_payload)
    manifest = {
        "schema_version": 1,
        "suite": "trixie",
        "architecture": "amd64",
        "package_count": 2,
        "total_bytes": len(fw) + len(uc),
        "total_installed_bytes": len(fw) + len(uc) + 2 * 32 * 1024,
        "provided_candidate_packages": [_FIRMWARE, _MICROCODE],
        "provided_firmware_packages": [_FIRMWARE],
        "provided_microcode_packages": [_MICROCODE],
        "broad_firmware_packages": [_FIRMWARE],
        "firmware_providers": {"g2-firmware.bin": [_FIRMWARE]},
        "unavailable_candidate_packages": [],
        "packages": [
            {
                "package": _FIRMWARE, "version": "1",
                "architecture": "all", "filename": f"pool/{fw_name}",
                "size": len(fw), "sha256": _sha(fw), "candidate": True,
                "installed_bytes": len(fw) + 32 * 1024,
            },
            {
                "package": _MICROCODE, "version": "1",
                "architecture": "amd64", "filename": f"pool/{uc_name}",
                "size": len(uc), "sha256": _sha(uc), "candidate": True,
                "installed_bytes": len(uc) + 32 * 1024,
            },
        ],
        "repository_indexes": {
            "Packages": {"size": len(packages_payload), "sha256": _sha(packages_payload)},
            "Packages.gz": {
                "size": len(packages_gzip_payload),
                "sha256": _sha(packages_gzip_payload),
            },
        },
    }
    (pool / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pool


def _payload_bytes(tag: bytes, size: int = 64 * 1024) -> bytes:
    body = bytes((index * 31 + 7) % 256 for index in range(size - len(tag)))
    return tag + body


def _candidate_bundle(root: Path, raw: bytes, *, hw_path: Path | None) -> Path:
    import zstandard

    work = root / "release-g2"
    work.mkdir(parents=True, exist_ok=True)
    payload_path = work / "slot.ext4.zst"
    payload_path.write_bytes(zstandard.ZstdCompressor(level=3).compress(raw))
    bundle = work / "candidate.greiaupdate"
    if bundle.exists():
        bundle.unlink()
    build_update_bundle(
        payload_path=payload_path,
        hardware_support_path=hw_path,
        output_path=bundle,
        version="0.99.0",
        release_id="greia-g2",
        platform_family=_FAMILY,
        architecture=_ARCH,
        profile=_PROFILE,
        payload_uncompressed_bytes=len(raw),
        minimum_slot_bytes=len(raw),
        persist_read_schema_min=1,
        persist_read_schema_max=1,
        persist_write_schema=1,
        release_notes="G2 bound proof release.",
    )
    return bundle


def _rig(root: Path):
    from greia_platform.system_updates import build_production_update_seams

    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    layout_path = root / "installed-layout.json"
    layout_path.write_text("{}\n", encoding="utf-8")
    seams = build_production_update_seams(
        layout_record_path=layout_path, state_dir=state_dir
    )
    return seams, state_dir


def _retar_shuffled(hw_path: Path, output: Path) -> None:
    import zstandard

    with hw_path.open("rb") as handle:
        raw_tar = zstandard.ZstdDecompressor().stream_reader(handle).read()
    entries: list[tuple[str, bytes]] = []
    with tarfile.open(fileobj=io.BytesIO(raw_tar), mode="r") as tar:
        for member in tar.getmembers():
            body = tar.extractfile(member)
            entries.append((member.name, body.read() if body is not None else b""))
    debs = [e for e in entries if e[0].startswith("pool/")]
    rest = [e for e in entries if not e[0].startswith("pool/")]
    reordered = [debs[0]] + rest + debs[1:]
    assert reordered[0][0].startswith("pool/")
    repacked = io.BytesIO()
    with tarfile.open(fileobj=repacked, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for name, payload in reordered:
            info = tarfile.TarInfo(name=name)
            info.size = len(payload)
            info.mode = 0o644
            info.mtime = 0
            tar.addfile(info, io.BytesIO(payload))
    output.write_bytes(
        zstandard.ZstdCompressor(level=3).compress(repacked.getvalue())
    )


def _rewrite_outer_bound(bundle: Path, output: Path, *, new_bound) -> None:
    with zipfile.ZipFile(bundle, "r") as source:
        members = {info.filename: source.read(info.filename) for info in source.infolist()}
    document = json.loads(members[MANIFEST_NAME].decode("utf-8"))
    if new_bound is None:
        document["hardware_support"].pop("extracted_bytes_bound", None)
    else:
        document["hardware_support"]["extracted_bytes_bound"] = new_bound
    manifest = UpdateManifest.from_json_dict(document)
    members[MANIFEST_NAME] = manifest.canonical_bytes()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as target:
        for name, payload in members.items():
            info = zipfile.ZipInfo(filename=name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o644 << 16) | 0x20
            info.compress_type = (
                zipfile.ZIP_DEFLATED if name == MANIFEST_NAME else zipfile.ZIP_STORED
            )
            target.writestr(info, payload)


class OuterBoundRoundTripTests(unittest.TestCase):
    def test_new_build_emits_outer_equal_to_inner_and_shared(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            result = _build_release.build_hardware_support_set(pool, hw_path)
            inner = int(result["extracted_bytes_bound"])
            bundle = _candidate_bundle(root, _payload_bytes(b"g2-round:"), hw_path=hw_path)
            inspected = inspect_update_bundle(bundle)
            outer = inspected.manifest.hardware_support_extracted_bytes_bound
            self.assertEqual(outer, inner)
            shared = _shared.inspect_archive_file(hw_path)
            self.assertEqual(outer, shared.extracted_size_bound)

    def test_outer_bound_type_range_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            _build_release.build_hardware_support_set(pool, hw_path)
            bundle = _candidate_bundle(root, _payload_bytes(b"g2-type:"), hw_path=hw_path)
            with zipfile.ZipFile(bundle, "r") as archive:
                base = json.loads(archive.read(MANIFEST_NAME).decode())
            for bad in (True, -1, 2 * 1024 * 1024 * 1024, "10", 3.5, None):
                bad_doc = json.loads(json.dumps(base))
                if bad is None:
                    bad_doc["hardware_support"].pop("extracted_bytes_bound", None)
                    # Absent field is the backward-compatible path: accepted.
                    manifest = UpdateManifest.from_json_dict(bad_doc)
                    self.assertIsNone(manifest.hardware_support_extracted_bytes_bound)
                    continue
                bad_doc["hardware_support"]["extracted_bytes_bound"] = bad
                with self.assertRaises(UpdateBundleError):
                    UpdateManifest.from_json_dict(bad_doc)


class OuterMismatchRefusalTests(unittest.TestCase):
    def test_build_inner_mismatch_refuses_with_no_output(self) -> None:
        import zstandard

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            result = _build_release.build_hardware_support_set(pool, hw_path)
            declared = int(result["extracted_bytes_bound"])
            # Repack with a mutated inner declaration (same order).
            with hw_path.open("rb") as handle:
                raw_tar = zstandard.ZstdDecompressor().stream_reader(handle).read()
            entries: list[tuple[str, bytes, int]] = []
            with tarfile.open(fileobj=io.BytesIO(raw_tar), mode="r") as tar:
                for member in tar.getmembers():
                    body = tar.extractfile(member)
                    entries.append((member.name, body.read() if body is not None else b"", member.type))
            mutated = root / "hw-mut.tar.zst"
            repacked = io.BytesIO()
            with tarfile.open(fileobj=repacked, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for name, payload, kind in entries:
                    info = tarfile.TarInfo(name=name)
                    info.mtime = 0
                    info.mode = 0o755 if kind == tarfile.DIRTYPE else 0o644
                    info.type = kind
                    if name == "manifest.json":
                        document = json.loads(payload.decode("utf-8"))
                        document["extracted_bytes_bound"] = declared + 4096
                        payload = (json.dumps(document, sort_keys=True, indent=2) + "\n").encode()
                    info.size = len(payload)
                    tar.addfile(info, io.BytesIO(payload))
            mutated.write_bytes(zstandard.ZstdCompressor(level=3).compress(repacked.getvalue()))
            import zstandard as _z

            work = root / "build-mut"
            work.mkdir()
            payload_path = work / "slot.ext4.zst"
            payload_path.write_bytes(_z.ZstdCompressor(level=3).compress(_payload_bytes(b"g2-mut:")))
            out = work / "mut.greiaupdate"
            with self.assertRaises(UpdateBundleError) as raised:
                build_update_bundle(
                    payload_path=payload_path,
                    hardware_support_path=mutated,
                    output_path=out,
                    version="0.99.0",
                    release_id="greia-g2",
                    platform_family=_FAMILY,
                    architecture=_ARCH,
                    profile=_PROFILE,
                    payload_uncompressed_bytes=64 * 1024,
                    persist_read_schema_min=1,
                    persist_read_schema_max=1,
                    persist_write_schema=1,
                )
            self.assertIn("bound", str(raised.exception).lower())
            self.assertFalse(out.exists())

    def test_staging_outer_mismatch_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            result = _build_release.build_hardware_support_set(pool, hw_path)
            declared = int(result["extracted_bytes_bound"])
            bundle = _candidate_bundle(root, _payload_bytes(b"g2-stagemis:"), hw_path=hw_path)
            mutated = root / "mut-outer.greiaupdate"
            _rewrite_outer_bound(bundle, mutated, new_bound=declared + 4096)
            inspected = SystemUpdateInbox(root / "state").receive(mutated)
            seams, state_dir = _rig(root)
            with self.assertRaises(UpdateBackendUnavailable) as raised:
                seams.support_set_factory(inspected)
            self.assertIn("bound", str(raised.exception).lower())
            parent = state_dir / "system-updates" / "candidate-support"
            self.assertEqual(list(parent.iterdir()) if parent.is_dir() else [], [])


class PreStreamPreflightTests(unittest.TestCase):
    def test_preflight_uses_outer_before_stream_traversal(self) -> None:
        import shutil as _shutil

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            result = _build_release.build_hardware_support_set(pool, hw_path)
            outer = int(result["extracted_bytes_bound"])
            bundle = _candidate_bundle(root, _payload_bytes(b"g2-pre:"), hw_path=hw_path)
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            self.assertEqual(inspected.manifest.hardware_support_extracted_bytes_bound, outer)
            seams, state_dir = _rig(root)
            real_preflight = _candidate.require_support_staging_free_space
            seen: list[int] = []

            def _spy(parent: object, **kwargs: object) -> object:
                seen.append(int(kwargs["extracted_size_bound"]))
                return real_preflight(parent, **kwargs)  # type: ignore[arg-type]

            with mock.patch.object(
                _candidate, "require_support_staging_free_space", side_effect=_spy
            ):
                support = seams.support_set_factory(inspected)
                try:
                    self.assertEqual(seen, [outer])
                    self.assertIsNotNone(support)
                finally:
                    seams.support_stage_cleanup()
            # One byte short of outer+reserve refuses before any staged byte.
            real_usage = _shutil.disk_usage
            reserve = _candidate.STAGING_OPERATING_RESERVE_BYTES
            member_calls: list[int] = []
            real_member = _candidate._extract_one

            def _count(tar: object, member: object, **kwargs: object) -> object:
                member_calls.append(1)
                return real_member(tar, member, **kwargs)  # type: ignore[arg-type]

            def _short(path: object) -> SimpleNamespace:
                return SimpleNamespace(
                    total=real_usage(path).total, used=0, free=outer + reserve - 1
                )

            with mock.patch.object(_candidate.shutil, "disk_usage", _short), mock.patch.object(
                _candidate, "_extract_one", side_effect=_count
            ):
                with self.assertRaises(UpdateBackendUnavailable) as raised:
                    seams.support_set_factory(inspected)
                self.assertIn("PERSIST", str(raised.exception))
                self.assertEqual(member_calls, [])
            parent = state_dir / "system-updates" / "candidate-support"
            self.assertEqual(list(parent.iterdir()) if parent.is_dir() else [], [])

    def test_absent_outer_keeps_midstream_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            _build_release.build_hardware_support_set(pool, hw_path)
            bundle = _candidate_bundle(root, _payload_bytes(b"g2-abs:"), hw_path=hw_path)
            stripped = root / "old.greiaupdate"
            _rewrite_outer_bound(bundle, stripped, new_bound=None)
            inspected = SystemUpdateInbox(root / "state").receive(stripped)
            self.assertIsNone(inspected.manifest.hardware_support_extracted_bytes_bound)
            seams, _ = _rig(root)
            try:
                support = seams.support_set_factory(inspected)
                self.assertIsNotNone(support)
            finally:
                seams.support_stage_cleanup()


class OrderLiftTests(unittest.TestCase):
    def test_payload_before_manifest_stages_with_valid_outer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            _build_release.build_hardware_support_set(pool, hw_path)
            shuffled = root / "hw-shuffled.tar.zst"
            _retar_shuffled(hw_path, shuffled)
            raw = _payload_bytes(b"g2-order:")
            bundle = _candidate_bundle(root, raw, hw_path=shuffled)
            # New builds carry the outer bound for the shuffled archive.
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            self.assertIsNotNone(inspected.manifest.hardware_support_extracted_bytes_bound)
            seams, state_dir = _rig(root)
            try:
                support = seams.support_set_factory(inspected)
                self.assertIsNotNone(support)
            finally:
                seams.support_stage_cleanup()
            parent = state_dir / "system-updates" / "candidate-support"
            self.assertEqual(list(parent.iterdir()) if parent.is_dir() else [], [])


if __name__ == "__main__":
    unittest.main()
