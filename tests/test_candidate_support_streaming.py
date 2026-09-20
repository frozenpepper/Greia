"""R4-EF-STAGE: streaming bounded-memory inspection, single-pass staging.

Proves, through the real production seams:

- the shared and runtime hashing/counting readers refuse unbounded
  ``read(-1)`` (the old whole-stream ``b"".join`` buffering regression
  fails closed here) and record the maximum read size, so a
  multi-chunk archive is proven to hash in bounded chunks;
- the conservative extracted-bytes bound is ``ceil(size/4096)*4096``
  per file plus per-member headers plus a bounded metadata allowance
  (never a bare byte sum), is declared by the release builder from the
  exact archived files, and travels as the stable
  ``extracted_bytes_bound`` builder-manifest field and inner-manifest
  field;
- one stage performs exactly one archive traversal and one tree
  extraction (no initial full-decompression pass, no intermediate
  compressed temp file), the resolver and installer share the one
  verified pool instance, and cleanup holds after success and failure;
- the PERSIST preflight spends the builder-declared bound;
- digest mismatch and observed-vs-declared bound mismatch (both
  directions) refuse, and a pool payload preceding ``manifest.json``
  is refused by staging (manifest-first order: the bound must be known
  before payload writes).

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

from support_artifacts import build_unchecked_support_bundle

from greia_installer import hardware_support_archive as _shared
from greia_installer.hardware_support import (
    HardwareSupportPoolError,
    installed_size_bound_from_support_archive,
)
from greia_platform import candidate_support as _candidate
from greia_platform.system_updates import (
    SystemUpdateInbox,
    UpdateBackendUnavailable,
    build_production_update_seams,
    build_update_bundle,
)

_spec = importlib.util.spec_from_file_location(
    "build_release_tool_ef_stage",
    Path(__file__).resolve().parents[1] / "tools" / "build_release.py",
)
assert _spec is not None and _spec.loader is not None
_build_release = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _build_release
_spec.loader.exec_module(_build_release)

_FAMILY = "efstage"
_ARCH = "efarch"
_PROFILE = "efprofile"
_FIRMWARE = "firmware-ef"
_MICROCODE = "ef-microcode"


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _pool_tree(root: Path, *, name: str = "ef", firmware: bytes | None = None) -> Path:
    """Write a minimal verified hardware-support pool (no bound field)."""
    fw = firmware if firmware is not None else b"ef-firmware-bytes"
    uc = b"ef-microcode-bytes"
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
        "firmware_providers": {"ef-firmware.bin": [_FIRMWARE]},
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


def _build_hw_archive(pool: Path, output: Path) -> dict:
    """Build the support archive through the real release builder."""
    return _build_release.build_hardware_support_set(pool, output)


def _payload_bytes(tag: bytes, size: int = 64 * 1024) -> bytes:
    body = bytes((index * 31 + 7) % 256 for index in range(size - len(tag)))
    return tag + body


def _candidate_bundle(
    root: Path, raw: bytes, *, hw_path: Path | None, work_name: str = "release-ef",
    bundle_name: str = "candidate.greiaupdate",
) -> Path:
    import zstandard

    work = root / work_name
    work.mkdir(parents=True, exist_ok=True)
    payload_path = work / "slot.ext4.zst"
    payload_path.write_bytes(zstandard.ZstdCompressor(level=3).compress(raw))
    bundle = work / bundle_name
    if bundle.exists():
        bundle.unlink()
    build_update_bundle(
        payload_path=payload_path,
        hardware_support_path=hw_path,
        output_path=bundle,
        version="0.99.0",
        release_id="greia-ef",
        platform_family=_FAMILY,
        architecture=_ARCH,
        profile=_PROFILE,
        payload_uncompressed_bytes=len(raw),
        minimum_slot_bytes=len(raw),
        persist_read_schema_min=1,
        persist_read_schema_max=1,
        persist_write_schema=1,
        release_notes="EF-STAGE streaming proof release.",
    )
    return bundle


def _rig(root: Path):
    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    layout_path = root / "installed-layout.json"
    layout_path.write_text("{}\n", encoding="utf-8")
    seams = build_production_update_seams(
        layout_record_path=layout_path, state_dir=state_dir
    )
    return seams, state_dir


def _staging_names(state_dir: Path) -> list[str]:
    parent = state_dir / "system-updates" / "candidate-support"
    if not parent.is_dir():
        return []
    return sorted(p.name for p in parent.iterdir())


def _assert_no_compressed_tmp(state_dir: Path) -> None:
    parent = state_dir / "system-updates" / "candidate-support"
    if not parent.is_dir():
        return
    leftovers = list(parent.rglob("*.tar.zst.tmp")) + list(
        parent.rglob(".hardware-support.tar.zst.tmp")
    )
    assert leftovers == [], f"intermediate compressed temp file escaped: {leftovers}"


def _context_of(seams: object) -> object:
    """Reach the shared production context cell behind the factories."""
    factory = getattr(seams, "support_set_factory")
    closure = getattr(factory, "__closure__", None) or ()
    for cell in closure:
        candidate = cell.cell_contents
        if hasattr(candidate, "support_stage"):
            return candidate
    raise AssertionError("production support factory must close over its context")


def _bundle_for_hw(
    root: Path, hw_path: Path, *, tag: bytes, work_name: str = "release-ef"
) -> Path:
    raw = _payload_bytes(tag)
    return _candidate_bundle(root, raw, hw_path=hw_path, work_name=work_name)


class ReaderDisciplineTests(unittest.TestCase):
    """Unbounded reads are refused; hashing is provably chunked."""

    def test_shared_reader_refuses_unbounded_read(self) -> None:
        reader = _shared.HashingCountingReader(
            io.BytesIO(b"0123456789"), expected_size=10
        )
        with self.assertRaises(_shared.HardwareSupportArchiveError) as raised:
            reader.read(-1)
        self.assertIn("unbounded", str(raised.exception))
        with self.assertRaises(_shared.HardwareSupportArchiveError):
            reader.read(None)  # type: ignore[arg-type]
        # Bounded reads still hash/count exactly.
        self.assertEqual(reader.read(4), b"0123")
        self.assertEqual(reader.read(0), b"")
        self.assertEqual(reader.read(6), b"456789")
        self.assertEqual(reader.read_bytes, 10)
        self.assertEqual(reader.digest_hex(), _sha(b"0123456789"))
        self.assertEqual(reader.max_read_size, 6)

    def test_runtime_wrapper_refuses_unbounded_read(self) -> None:
        reader = _candidate._HashingCountingReader(
            io.BytesIO(b"abcdef"), expected_size=6
        )
        with self.assertRaises(_candidate.CandidateSupportError) as raised:
            reader.read(-1)
        self.assertIn("unbounded", str(raised.exception))
        self.assertEqual(reader.read(6), b"abcdef")
        self.assertEqual(reader.max_read_size, 6)

    def test_inspection_hashes_large_member_in_bounded_chunks(self) -> None:
        import os

        big = os.urandom(3 * 1024 * 1024)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root, firmware=big)
            hw_path = root / "hw-big.tar.zst"
            _build_hw_archive(pool, hw_path)
            assert hw_path.stat().st_size > 3 * 1024 * 1024
            instances: list[object] = []
            real = _shared._HashingCountingReader

            class Spy(real):  # type: ignore[valid-type,misc]
                def __init__(self, *args: object, **kwargs: object) -> None:
                    super().__init__(*args, **kwargs)  # type: ignore[arg-type]
                    instances.append(self)

            with mock.patch.object(_shared, "_HashingCountingReader", Spy):
                metadata = _shared.inspect_archive_file(hw_path)
            # One counting reader served the whole compressed stream.
            self.assertEqual(len(instances), 1)
            spy = instances[0]
            assert isinstance(spy, _shared.HashingCountingReader)
            self.assertEqual(spy.read_bytes, hw_path.stat().st_size)
            self.assertEqual(spy.digest_hex(), _sha(hw_path.read_bytes()))
            # Chunked proof: every single read was bounded (the old
            # whole-stream read(-1)/b"".join path would have raised
            # above instead of completing).
            self.assertGreater(spy.max_read_size, 0)
            self.assertLessEqual(spy.max_read_size, _shared._CHUNK_BYTES)
            self.assertGreater(metadata.extracted_size_bound, 0)


class BoundModelTests(unittest.TestCase):
    """The conservative allocation model, pinned arithmetically."""

    def test_block_rounding_plus_headers_plus_allowance(self) -> None:
        bound = _shared.extracted_bytes_bound_for_members([0, 1, 4096, 4097, 100])
        blocks = 0 + 1 + 1 + 2 + 1
        expected = (
            blocks * 4096 + 5 * 512 + _shared.EXTRACTED_METADATA_ALLOWANCE_BYTES
        )
        self.assertEqual(bound, expected)
        self.assertEqual(_shared.EXTRACTED_BLOCK_BYTES, 4096)
        self.assertEqual(_shared.EXTRACTED_TAR_HEADER_BYTES, 512)
        # Never a bare byte sum: block rounding and the metadata
        # allowance strictly exceed sum(sizes)+512/member for small files.
        bare = 0 + 1 + 4096 + 4097 + 100 + 5 * 512
        self.assertGreater(bound, bare)

    def test_member_count_padding_is_conservative(self) -> None:
        tight = _shared.extracted_bytes_bound_for_members([10, 20], member_count=2)
        padded = _shared.extracted_bytes_bound_for_members(
            [10, 20], member_count=2048
        )
        self.assertEqual(padded - tight, (2048 - 2) * 512)

    def test_invalid_sizes_refuse(self) -> None:
        for bad in (-1, True, "10", 3.5, None):
            with self.assertRaises(_shared.HardwareSupportArchiveError):
                _shared.extracted_bytes_bound_for_members([10, bad])  # type: ignore[list-item]
        with self.assertRaises(_shared.HardwareSupportArchiveError):
            _shared.extracted_bytes_bound_for_members("not-a-list")  # type: ignore[arg-type]
        with self.assertRaises(_shared.HardwareSupportArchiveError):
            _shared.extracted_bytes_bound_for_members(
                [10], member_count=0
            )
        # A bound beyond the uncompressed cap refuses instead of staging.
        with self.assertRaises(_shared.HardwareSupportArchiveError):
            _shared.extracted_bytes_bound_for_members(
                [_shared.MAX_ARCHIVE_FILE_BYTES]
                * (_shared.MAX_ARCHIVE_MEMBERS // 2)
            )


class BuilderBoundTests(unittest.TestCase):
    """The builder declares the bound from the exact archived files."""

    def test_builder_declares_model_bound_and_embeds_field(self) -> None:
        import zstandard

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            result = _build_hw_archive(pool, hw_path)
            declared = result["extracted_bytes_bound"]
            self.assertIsInstance(declared, int)
            self.assertGreater(declared, 0)
            # The archived bytes carry the same declaration.
            raw_tar = zstandard.ZstdDecompressor().stream_reader(
                hw_path.open("rb")
            )
            with raw_tar as reader, tarfile.open(fileobj=reader, mode="r|") as tar:
                sizes: dict[str, int] = {}
                manifest_blob: bytes | None = None
                count = 0
                for member in tar:
                    count += 1
                    if not member.isfile():
                        continue
                    body = tar.extractfile(member)
                    assert body is not None
                    with body:
                        payload = body.read()
                    sizes[member.name] = len(payload)
                    if member.name == "manifest.json":
                        manifest_blob = payload
            assert manifest_blob is not None
            document = json.loads(manifest_blob.decode("utf-8"))
            self.assertEqual(document["extracted_bytes_bound"], declared)
            # The declaration equals the shared model on the exact
            # archived file sizes and member count.
            self.assertEqual(
                declared,
                _shared.extracted_bytes_bound_for_members(
                    list(sizes.values()), member_count=count
                ),
            )
            # The runtime shared inspect binds the same observed bound.
            metadata = _shared.inspect_archive_file(hw_path)
            self.assertEqual(metadata.extracted_size_bound, declared)
            self.assertEqual(
                installed_size_bound_from_support_archive(hw_path),
                metadata.total_installed_bytes,
            )

    def test_builder_bound_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root)
            first = _build_hw_archive(pool, root / "hw-a.tar.zst")
            second = _build_hw_archive(pool, root / "hw-b.tar.zst")
            self.assertEqual(
                first["extracted_bytes_bound"], second["extracted_bytes_bound"]
            )


class SingleTraversalTests(unittest.TestCase):
    """One stage: one traversal, one tree extraction, one shared pool."""

    def test_one_traversal_one_extraction_shared_pool(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            _build_hw_archive(pool, hw_path)
            hw_bytes = hw_path.read_bytes()
            raw = _payload_bytes(b"ef-single:")
            bundle = _candidate_bundle(root, raw, hw_path=hw_path)
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            seams, state_dir = _rig(root)
            real_zstd = _candidate._zstd_stream
            real_tree = _candidate.extract_support_tree
            real_member = _candidate._extract_one
            traversals: list[int] = []
            trees: list[int] = []
            members: list[str] = []

            def _count_zstd(source: object) -> object:
                traversals.append(1)
                return real_zstd(source)  # type: ignore[arg-type]

            def _count_tree(*args: object, **kwargs: object) -> object:
                trees.append(1)
                return real_tree(*args, **kwargs)  # type: ignore[arg-type]

            def _count_member(tar: object, member: object, **kwargs: object) -> object:
                result = real_member(tar, member, **kwargs)  # type: ignore[arg-type]
                members.append(getattr(member, "name", "?"))
                return result

            with mock.patch.object(
                _candidate, "_zstd_stream", side_effect=_count_zstd
            ), mock.patch.object(
                _candidate, "extract_support_tree", side_effect=_count_tree
            ), mock.patch.object(
                _candidate, "_extract_one", side_effect=_count_member
            ), mock.patch.object(
                _candidate,
                "inspect_support_metadata",
                side_effect=AssertionError("stage must not run a second traversal"),
            ):
                support = seams.support_set_factory(inspected)
                # Resolver sees the candidate pool through the one stage.
                self.assertEqual(support.support_digest, _sha(hw_bytes))
                context = _context_of(seams)
                stage = context.support_stage
                self.assertIsInstance(stage, _candidate.CandidateSupportStage)
                try:
                    # Exactly one archive traversal and one tree extraction
                    # for the whole stage so far.
                    self.assertEqual(len(traversals), 1)
                    self.assertEqual(len(trees), 1)
                    # Every pool payload streamed to disk exactly once
                    # (small metadata bypasses _extract_one by design).
                    self.assertEqual(len(members), 2)
                    # The installer factory of the same stage reuses the
                    # open stage: no second traversal, no second extraction.
                    mountpoint = root / "mnt"
                    mountpoint.mkdir(parents=True)
                    context.filesystem_tracker = SimpleNamespace(
                        current_mountpoint=mountpoint
                    )
                    installer = seams.package_installer_factory()
                    self.assertIsNotNone(installer)
                    self.assertEqual(len(traversals), 1)
                    self.assertEqual(len(trees), 1)
                    self.assertEqual(len(members), 2)
                    pool_before = stage.pool
                    root_before = stage.root
                    self.assertEqual(
                        {p.name for p in root_before.iterdir()},
                        {"manifest.json", "Packages", "Packages.gz", "pool"},
                    )
                    self.assertEqual(
                        {p.name for p in (root_before / "pool").iterdir()},
                        {
                            f"{_FIRMWARE}_1_all.deb",
                            f"{_MICROCODE}_1_amd64.deb",
                        },
                    )
                finally:
                    seams.support_stage_cleanup()
            self.assertEqual(len(traversals), 1)
            self.assertEqual(len(trees), 1)
            self.assertIs(stage.pool, pool_before)
            _assert_no_compressed_tmp(state_dir)
            self.assertEqual(_staging_names(state_dir), [])


class DeclaredBoundPreflightTests(unittest.TestCase):
    """The PERSIST preflight spends the builder-declared bound."""

    def test_preflight_consumes_declared_bound(self) -> None:
        import shutil as _shutil

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            result = _build_hw_archive(pool, hw_path)
            declared = int(result["extracted_bytes_bound"])
            raw = _payload_bytes(b"ef-preflight:")
            bundle = _candidate_bundle(root, raw, hw_path=hw_path)
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            seams, state_dir = _rig(root)
            real_usage = _shutil.disk_usage
            seen_bounds: list[int] = []
            real_preflight = _candidate.require_support_staging_free_space

            def _spy_preflight(parent: object, **kwargs: object) -> object:
                seen_bounds.append(int(kwargs["extracted_size_bound"]))
                return real_preflight(parent, **kwargs)  # type: ignore[arg-type]

            reserve = _candidate.STAGING_OPERATING_RESERVE_BYTES
            with mock.patch.object(
                _candidate, "require_support_staging_free_space",
                side_effect=_spy_preflight,
            ):
                support = seams.support_set_factory(inspected)
                try:
                    self.assertEqual(seen_bounds, [declared])
                    self.assertIsNotNone(support)
                finally:
                    seams.support_stage_cleanup()
            # One byte short of declared+reserve refuses before extraction.
            member_calls: list[int] = []
            real_member = _candidate._extract_one

            def _count_member(tar: object, member: object, **kwargs: object) -> object:
                member_calls.append(1)
                return real_member(tar, member, **kwargs)  # type: ignore[arg-type]

            def _short(path: object) -> SimpleNamespace:
                return SimpleNamespace(
                    total=real_usage(path).total, used=0,
                    free=declared + reserve - 1,
                )

            with mock.patch.object(
                _candidate.shutil, "disk_usage", _short
            ), mock.patch.object(
                _candidate, "_extract_one", side_effect=_count_member
            ), mock.patch.object(
                _candidate, "require_support_staging_free_space",
                side_effect=_spy_preflight,
            ):
                with self.assertRaises(UpdateBackendUnavailable) as raised:
                    seams.support_set_factory(inspected)
                self.assertIn("PERSIST", str(raised.exception))
                self.assertEqual(member_calls, [])
            self.assertEqual(_staging_names(state_dir), [])
            _assert_no_compressed_tmp(state_dir)


class MismatchRefusalTests(unittest.TestCase):
    """Digest and observed-vs-declared bound mismatches refuse."""

    def _retar_with_manifest(
        self, hw_path: Path, output: Path, *, manifest_mutation
    ) -> None:
        """Repack the archive with a mutated inner manifest (same order)."""
        import zstandard

        decompressor = zstandard.ZstdDecompressor()
        with hw_path.open("rb") as handle:
            raw_tar = decompressor.stream_reader(handle).read()
        entries: list[tuple[str, bytes, int]] = []
        with tarfile.open(fileobj=io.BytesIO(raw_tar), mode="r") as tar:
            for member in tar.getmembers():
                body = tar.extractfile(member)
                payload = body.read() if body is not None else b""
                entries.append((member.name, payload, member.type))
        repacked = io.BytesIO()
        with tarfile.open(fileobj=repacked, mode="w", format=tarfile.PAX_FORMAT) as tar:
            for name, payload, kind in entries:
                info = tarfile.TarInfo(name=name)
                info.mtime = 0
                info.mode = 0o755 if kind == tarfile.DIRTYPE else 0o644
                info.type = kind
                if name == "manifest.json":
                    document = json.loads(payload.decode("utf-8"))
                    manifest_mutation(document)
                    payload = (
                        json.dumps(document, sort_keys=True, indent=2) + "\n"
                    ).encode("utf-8")
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))
        output.write_bytes(
            zstandard.ZstdCompressor(level=3).compress(repacked.getvalue())
        )

    def test_tampered_member_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            _build_hw_archive(pool, hw_path)
            bundle = _bundle_for_hw(root, hw_path, tag=b"ef-tamper:")
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            seams, state_dir = _rig(root)
            staged = inspected.path
            with zipfile.ZipFile(staged, "r") as source:
                members = {
                    info.filename: source.read(info.filename)
                    for info in source.infolist()
                }
            swapped = bytearray(members["hardware-support.tar.zst"])
            swapped[10] ^= 0xFF
            members["hardware-support.tar.zst"] = bytes(swapped)
            with zipfile.ZipFile(staged, "w", compression=zipfile.ZIP_STORED) as target:
                for name, payload in members.items():
                    target.writestr(name, payload)
            with self.assertRaises(UpdateBackendUnavailable):
                seams.support_set_factory(inspected)
            self.assertEqual(_staging_names(state_dir), [])
            _assert_no_compressed_tmp(state_dir)

    def test_declared_bound_mismatch_refuses_both_directions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            result = _build_hw_archive(pool, hw_path)
            declared = int(result["extracted_bytes_bound"])
            for label, delta in (("under", -512), ("over", 4096)):
                with self.subTest(direction=label):
                    mutated = root / f"hw-{label}.tar.zst"
                    self._retar_with_manifest(
                        hw_path,
                        mutated,
                        manifest_mutation=lambda doc: doc.update(
                            {"extracted_bytes_bound": declared + delta}
                        ),
                    )
                    # The shared build-inspect path refuses as well:
                    # verdict agreement holds for the new shape.
                    with self.assertRaises(HardwareSupportPoolError) as build_raised:
                        installed_size_bound_from_support_archive(mutated)
                    self.assertIn("bound", str(build_raised.exception))
                    # R4-G2-SUPPORT-BOUND: the outer-manifest builder now
                    # refuses the inner mismatch before publication with
                    # no output (stronger than staging refusal).
                    from greia_platform.system_updates import UpdateBundleError

                    with self.assertRaises(UpdateBundleError) as bundle_raised:
                        _bundle_for_hw(
                            root,
                            mutated,
                            tag=f"ef-bound-{label}:".encode(),
                            work_name=f"release-{label}",
                        )
                    self.assertIn("bound", str(bundle_raised.exception).lower())
                    candidate = root / f"release-{label}" / "candidate.greiaupdate"
                    self.assertFalse(candidate.exists())

    def test_pool_payload_before_manifest_refused_by_stage(self) -> None:
        import zstandard

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            _build_hw_archive(pool, hw_path)
            decompressor = zstandard.ZstdDecompressor()
            with hw_path.open("rb") as handle:
                raw_tar = decompressor.stream_reader(handle).read()
            entries: list[tuple[str, bytes]] = []
            with tarfile.open(fileobj=io.BytesIO(raw_tar), mode="r") as tar:
                for member in tar.getmembers():
                    body = tar.extractfile(member)
                    entries.append(
                        (member.name, body.read() if body is not None else b"")
                    )
            # Move the first pool payload ahead of manifest.json; every
            # member stays digest/size consistent.
            debs = [entry for entry in entries if entry[0].startswith("pool/")]
            rest = [entry for entry in entries if not entry[0].startswith("pool/")]
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
            shuffled = root / "hw-shuffled.tar.zst"
            shuffled.write_bytes(
                zstandard.ZstdCompressor(level=3).compress(repacked.getvalue())
            )
            # Pure shared inspection still accepts the shape (no order
            # rule there); R4-G2-SUPPORT-BOUND lifts the manifest-first
            # order refusal once the outer-bound pre-stream preflight
            # owns capacity, so the shuffled archive with a valid outer
            # bound now stages. The old absent-outer path keeps the
            # refusal (proved below by stripping the outer field).
            metadata = _shared.inspect_archive_file(shuffled)
            self.assertGreater(metadata.extracted_size_bound, 0)
            bundle = _bundle_for_hw(root, shuffled, tag=b"ef-order:")
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            self.assertIsNotNone(
                inspected.manifest.hardware_support_extracted_bytes_bound
            )
            seams, state_dir = _rig(root)
            try:
                support = seams.support_set_factory(inspected)
                self.assertIsNotNone(support)
            finally:
                seams.support_stage_cleanup()
            self.assertEqual(_staging_names(state_dir), [])
            _assert_no_compressed_tmp(state_dir)
            # Absent outer bound (old bundle) keeps the order gate.
            import json as _json
            import zipfile as _zipfile

            from greia_platform.system_updates import MANIFEST_NAME as _MN
            from greia_platform.system_updates import UpdateManifest as _UM

            with _zipfile.ZipFile(bundle, "r") as _src:
                _members = {
                    _info.filename: _src.read(_info.filename)
                    for _info in _src.infolist()
                }
            _doc = _json.loads(_members[_MN].decode("utf-8"))
            _doc["hardware_support"].pop("extracted_bytes_bound", None)
            _members[_MN] = _UM.from_json_dict(_doc).canonical_bytes()
            _old = root / "old-order.greiaupdate"
            with _zipfile.ZipFile(_old, "w", compression=_zipfile.ZIP_STORED) as _dst:
                for _name, _payload in _members.items():
                    _info = _zipfile.ZipInfo(
                        filename=_name, date_time=(1980, 1, 1, 0, 0, 0)
                    )
                    _info.create_system = 3
                    _info.external_attr = (0o644 << 16) | 0x20
                    _info.compress_type = (
                        _zipfile.ZIP_DEFLATED
                        if _name == _MN
                        else _zipfile.ZIP_STORED
                    )
                    _dst.writestr(_info, _payload)
            _old_inspected = SystemUpdateInbox(root / "state-old").receive(_old)
            seams_old, state_old = _rig(root / "old-state")
            with self.assertRaises(UpdateBackendUnavailable) as raised:
                seams_old.support_set_factory(_old_inspected)
            self.assertIn("precedes manifest", str(raised.exception))
            self.assertEqual(_staging_names(state_old), [])
            _assert_no_compressed_tmp(state_old)


class MidStreamFailureCleanupTests(unittest.TestCase):
    """A truncated member fails closed with no staging residue."""

    def test_truncated_member_refuses_and_cleans_up(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            _build_hw_archive(pool, hw_path)
            import zstandard

            decompressor = zstandard.ZstdDecompressor()
            with hw_path.open("rb") as handle:
                raw_tar = decompressor.stream_reader(handle).read()
            # Locate the last pool payload body and cut the tar off
            # mid-body: the header still announces the full size, so the
            # single pass starts and then fails closed mid-member.
            with tarfile.open(fileobj=io.BytesIO(raw_tar), mode="r") as tar:
                last_deb = max(
                    member.name
                    for member in tar.getmembers()
                    if member.name.startswith("pool/")
                )
                offsets = {
                    member.name: (member.offset_data, member.size)
                    for member in tar.getmembers()
                }
            data_offset, data_size = offsets[last_deb]
            assert data_size > 16
            cut = raw_tar[: data_offset + data_size // 2]
            broken = root / "hw-broken.tar.zst"
            broken.write_bytes(
                zstandard.ZstdCompressor(level=3).compress(cut)
            )
            bundle = build_unchecked_support_bundle(
                output_path=root / "candidate-truncated.greiaupdate",
                raw_payload=_payload_bytes(b"ef-trunc:"),
                raw_support=broken.read_bytes(),
                version="0.99.0",
                release_id="greia-ef-truncated",
                platform_family=_FAMILY,
                architecture=_ARCH,
                profile=_PROFILE,
            )
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            seams, state_dir = _rig(root)
            with self.assertRaises(UpdateBackendUnavailable):
                seams.support_set_factory(inspected)
            self.assertEqual(_staging_names(state_dir), [])
            _assert_no_compressed_tmp(state_dir)


class SingleOpenPerMemberTests(unittest.TestCase):
    """R4-D2-HYGIENE2: exactly one extractfile open owns each member.

    The staging loop opens each tar member once and threads the
    already-open payload body through to ``_extract_one`` instead of
    re-opening the same member inside it (the fragile double-open).
    """

    def test_each_member_opened_exactly_once_with_threaded_body(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            _build_hw_archive(pool, hw_path)
            raw = _payload_bytes(b"ef-single-open:")
            bundle = _candidate_bundle(root, raw, hw_path=hw_path)
            inspected = SystemUpdateInbox(root / "state").receive(bundle)
            manifest = inspected.manifest
            assert manifest.hardware_support_sha256 is not None
            assert manifest.hardware_support_size is not None
            opens: dict[str, int] = {}
            real_extractfile = tarfile.TarFile.extractfile

            def _counting_extractfile(tar_self: object, member: object) -> object:
                body = real_extractfile(tar_self, member)  # type: ignore[arg-type]
                name = getattr(member, "name", "?")
                opens[name] = opens.get(name, 0) + 1
                return body

            bodies_seen: list[bool] = []
            real_member = _candidate._extract_one

            def _recording_member(
                tar: object, member: object, **kwargs: object
            ) -> object:
                bodies_seen.append(kwargs.get("body") is not None)
                return real_member(tar, member, **kwargs)  # type: ignore[arg-type]

            dest = root / "staged"
            dest.mkdir()
            with mock.patch.object(
                tarfile.TarFile, "extractfile",
                autospec=True, side_effect=_counting_extractfile,
            ), mock.patch.object(
                _candidate, "_extract_one", side_effect=_recording_member
            ):
                metadata = _candidate.extract_support_tree(
                    bundle,
                    expected_sha=manifest.hardware_support_sha256,
                    expected_size=manifest.hardware_support_size,
                    destination=dest,
                    preflight=None,
                )
            self.assertGreater(metadata.extracted_size_bound, 0)
            # Every visited member — small metadata and pool payloads —
            # was opened exactly once; the old re-open would show 2x
            # for each payload member.
            self.assertTrue(opens)
            for name, count in opens.items():
                self.assertEqual(count, 1, f"member opened {count}x: {name}")
            # Both pool payloads went through the threaded-body path
            # (small metadata bypasses _extract_one by design).
            self.assertEqual(len(bodies_seen), 2)
            self.assertTrue(all(bodies_seen))


if __name__ == "__main__":
    unittest.main()
