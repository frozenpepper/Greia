"""Candidate hardware-support staging (Repair D / T03 single-materialization).

Routes the exact candidate ``.greiaupdate`` ``hardware-support.tar.zst``
member — not the running system's ``/opt/greia-hardware-support`` pool —
into candidate finalization::

    candidate.greiaupdate -> ZipExtFile -> hashing/counting reader
    -> ZstdDecompressor.stream_reader -> tarfile streaming extraction
    -> temp candidate support root -> VerifiedHardwareSupportPool.load
    -> selection + TargetHardwareSupportInstaller -> cleanup temp root

One :class:`CandidateSupportStage` owns one stage: it inspects the
digest-verified member metadata first (no filesystem writes), runs the
PERSIST free-space preflight, then performs exactly one streaming
extraction and loads exactly one verified pool instance. That same pool
instance drives both support-set resolution and package installation, so
a stage never materializes the member twice and the installer can never
substitute the running-image pool. The temp root is removed on success
and on any exception. There is no intermediate compressed temp file
(never ``.hardware-support.tar.zst.tmp``) and the full archive is never
loaded into RAM: both the metadata-inspection pass and the extraction
pass stream in bounded chunks.

Reliability/path-safety grade (not a hostile-owner project): the member
bytes are re-verified against the inspected manifest (size + SHA-256) at
extraction time so a candidate that changed between inspection and staging
cannot slip through, the tar shape is restricted to the exact
release-builder tree (``manifest.json``, ``Packages``, ``Packages.gz``,
``pool/*.deb``), and compressed/uncompressed/member-count bounds are
enforced while streaming. No shell, no ``tar`` subprocess: extraction uses
:mod:`tarfile` in streaming mode over a :mod:`zstandard` stream reader.

Staging lives under a Greia-owned temp dir on the update service's
writable area (``<state>/system-updates/candidate-support/``) and is
removed on success and on failure. A null manifest support declaration is
a no-op: nothing is extracted and the caller receives ``None``.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Callable


class CandidateSupportError(RuntimeError):
    """The candidate hardware-support member is missing or unsafe."""


#: Zip member name inside the candidate bundle. Mirrors
#: ``greia_platform.system_updates.HARDWARE_SUPPORT_NAME`` (kept local so
#: this module never imports the service composition it serves).
HARDWARE_SUPPORT_MEMBER = "hardware-support.tar.zst"

#: Staging directory name under ``<state>/system-updates/``.
STAGING_DIR_NAME = "candidate-support"

#: Compressed member bound. Mirrors
#: ``system_updates.MAX_HARDWARE_SUPPORT_BYTES`` (sync-tested there); the
#: inspected manifest already enforces it, the stager re-enforces it
#: on the exact bytes it streams.
MAX_CANDIDATE_SUPPORT_COMPRESSED_BYTES = 512 * 1024 * 1024

#: Uncompressed tar bound. Debian payloads do not compress further inside
#: the tar, so legitimate trees stay near their compressed size; twice the
#: compressed bound leaves tar-header headroom without opening a
#: decompression-bomb surface on the low-resource reference floor.
MAX_CANDIDATE_SUPPORT_UNCOMPRESSED_BYTES = 1024 * 1024 * 1024

#: Per-file bound inside the tar (no single payload may exceed it).
MAX_CANDIDATE_SUPPORT_FILE_BYTES = 512 * 1024 * 1024

#: Member-count bound: at most 1024 pool payloads plus the three top-level
#: release files, with headroom for the single ``pool/`` directory entry.
MAX_CANDIDATE_SUPPORT_MEMBERS = 2048

#: Bound for buffering the inner support ``manifest.json`` during the
#: metadata-inspection pass (mirrors the installer archive-inspection bound;
#: kept local so this module never imports the installer it serves).
MAX_SUPPORT_MANIFEST_BYTES = 8 * 1024 * 1024

#: Operating reserve kept free on the staging filesystem alongside the
#: staged bundle and the extracted tree. Mirrors the inbox reserve
#: (``system_updates`` 256 MiB operating reserve); kept local so this
#: module never imports the service composition it serves.
STAGING_OPERATING_RESERVE_BYTES = 256 * 1024 * 1024

#: Exact expected top-level release files (see ``tools/build_release.py``
#: ``build_hardware_support_set``: manifest, both repository indexes, and
#: the ``pool/`` payload directory).
_TOP_FILES = frozenset({"manifest.json", "Packages", "Packages.gz"})
_POOL_DIR = "pool"
_CHUNK_BYTES = 1024 * 1024


def has_candidate_support(manifest: object) -> bool:
    """Return True when the manifest declares a hardware-support member."""
    return getattr(manifest, "hardware_support_sha256", None) is not None


def staging_parent_for(state_dir: Path) -> Path:
    """Greia-owned staging parent on the update service's writable area."""
    return Path(state_dir) / "system-updates" / STAGING_DIR_NAME


@dataclass(frozen=True, slots=True)
class InspectedSupportMetadata:
    """Digest-verified support facts read without touching the filesystem.

    Produced by :func:`inspect_support_metadata`, which streams the exact
    candidate member (hashing/counting every byte, verifying size and
    SHA-256 against the inspected bundle manifest) while validating the
    tar shape and the inner support-manifest installed accounting. No
    file is written: this is the deterministic extracted-size bound the
    PERSIST preflight and the slot-capacity refusal consume before any
    materialization begins.
    """

    support_sha256: str
    support_size: int
    total_bytes: int
    total_installed_bytes: int
    uncompressed_bytes: int
    member_count: int
    extracted_size_bound: int


class _HashingCountingReader:
    """Bounded hashing/counting adapter over a ZIP member stream.

    Counts and SHA-256 hashes every byte handed out and refuses to hand
    out more than ``expected_size`` bytes, so a member that grew after
    inspection fails closed mid-stream instead of loading unbounded data.
    Chunked reads keep the full archive out of RAM.
    """

    def __init__(self, source: BinaryIO, *, expected_size: int) -> None:
        self._source = source
        self._expected_size = expected_size
        self._read_bytes = 0
        self._digest = hashlib.sha256()

    @property
    def read_bytes(self) -> int:
        return self._read_bytes

    def digest_hex(self) -> str:
        return self._digest.hexdigest()

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            pieces: list[bytes] = []
            while True:
                chunk = self.read(_CHUNK_BYTES)
                if not chunk:
                    break
                pieces.append(chunk)
            return b"".join(pieces)
        if size == 0:
            return b""
        try:
            chunk = self._source.read(size)
        except OSError as exc:
            raise CandidateSupportError(
                "candidate hardware-support member stream failed"
            ) from exc
        if not chunk:
            return b""
        self._read_bytes += len(chunk)
        if self._read_bytes > self._expected_size:
            raise CandidateSupportError(
                "candidate hardware-support member grew during staging"
            )
        self._digest.update(chunk)
        return chunk


def _checked_manifest_facts(manifest: object) -> tuple[str, int]:
    """Return the (sha256, size) support facts from an inspected manifest."""
    expected_sha = getattr(manifest, "hardware_support_sha256", None)
    expected_size = getattr(manifest, "hardware_support_size", None)
    if (
        not isinstance(expected_sha, str)
        or not isinstance(expected_size, int)
        or isinstance(expected_size, bool)
    ):
        raise CandidateSupportError("candidate hardware-support facts are invalid")
    if expected_size <= 0 or expected_size > MAX_CANDIDATE_SUPPORT_COMPRESSED_BYTES:
        raise CandidateSupportError(
            "candidate hardware-support size is outside Greia bounds"
        )
    return expected_sha, expected_size


def _checked_bundle_size(bundle_path: Path) -> int:
    """Return the on-disk size of the candidate bundle (fail closed)."""
    try:
        bundle_stat = bundle_path.lstat()
    except OSError as exc:
        raise CandidateSupportError(
            "candidate bundle is unavailable for support extraction"
        ) from exc
    if not stat.S_ISREG(bundle_stat.st_mode):
        raise CandidateSupportError("candidate bundle is not a regular file")
    return bundle_stat.st_size


def _open_member_stream(bundle_path: Path, *, expected_size: int):
    """Open the ZIP member stream after enforcing the inspected size fact."""
    try:
        archive = zipfile.ZipFile(bundle_path, "r")
    except (zipfile.BadZipFile, OSError) as exc:
        raise CandidateSupportError(
            "candidate bundle is not a readable Greia artifact"
        ) from exc
    try:
        try:
            info = archive.getinfo(HARDWARE_SUPPORT_MEMBER)
        except KeyError as exc:
            raise CandidateSupportError(
                "candidate hardware-support member is absent"
            ) from exc
        if info.is_dir() or info.file_size != expected_size:
            raise CandidateSupportError(
                "candidate hardware-support size does not match manifest"
            )
        if info.file_size <= 0 or info.file_size > MAX_CANDIDATE_SUPPORT_COMPRESSED_BYTES:
            raise CandidateSupportError(
                "candidate hardware-support size is outside Greia bounds"
            )
        try:
            return archive, archive.open(HARDWARE_SUPPORT_MEMBER, "r")
        except (zipfile.BadZipFile, OSError) as exc:
            raise CandidateSupportError(
                "candidate hardware-support member is unreadable"
            ) from exc
    except Exception:
        archive.close()
        raise


def _zstd_stream(source: BinaryIO):
    """Wrap a byte stream in a zstd decompression stream reader."""
    try:
        import zstandard
    except ImportError as exc:
        raise CandidateSupportError(
            "zstd decompression backend is unavailable; refusing support staging"
        ) from exc
    try:
        return zstandard.ZstdDecompressor().stream_reader(source)
    except Exception as exc:
        raise CandidateSupportError(
            f"candidate hardware-support archive is not a safe Greia tree: {exc}"
        ) from exc


def _close_stream(stream: object) -> None:
    closer = getattr(stream, "close", None)
    if callable(closer):
        try:
            closer()
        except Exception:
            pass


def _check_member_shape(member: tarfile.TarInfo) -> bool:
    """Validate one streaming tar header; return True for regular files."""
    name = member.name
    _reject_unsafe_name(name)
    if member.issym() or member.islnk():
        raise CandidateSupportError(
            "candidate hardware-support symlinks are not supported"
        )
    if member.isdev() or member.isfifo():
        raise CandidateSupportError(
            "candidate hardware-support special files are not supported"
        )
    if member.isdir():
        if name.rstrip("/") not in ("", ".", _POOL_DIR):
            raise CandidateSupportError(
                f"candidate hardware-support has an unexpected directory: {name}"
            )
        return False
    if not member.isfile():
        raise CandidateSupportError(
            f"candidate hardware-support has an unexpected shape: {name}"
        )
    _require_expected_file(name)
    if member.size < 0 or member.size > MAX_CANDIDATE_SUPPORT_FILE_BYTES:
        raise CandidateSupportError(
            f"candidate hardware-support file is outside Greia bounds: {name}"
        )
    return True


def _drain_member(tar: tarfile.TarFile, member: tarfile.TarInfo) -> bytes | None:
    """Consume one streaming member body, buffering only manifest.json."""
    source = tar.extractfile(member)
    if source is None:
        raise CandidateSupportError(
            f"candidate hardware-support member is unreadable: {member.name}"
        )
    if member.name == "manifest.json":
        if member.size > MAX_SUPPORT_MANIFEST_BYTES:
            raise CandidateSupportError(
                "candidate hardware-support manifest is outside Greia bounds"
            )
        pieces: list[bytes] = []
        remaining = member.size
        with source:
            while remaining > 0:
                chunk = source.read(min(_CHUNK_BYTES, remaining))
                if not chunk:
                    raise CandidateSupportError(
                        "candidate hardware-support member is truncated: "
                        f"{member.name}"
                    )
                remaining -= len(chunk)
                pieces.append(chunk)
        return b"".join(pieces)
    with source:
        remaining = member.size
        while remaining > 0:
            chunk = source.read(min(_CHUNK_BYTES, remaining))
            if not chunk:
                raise CandidateSupportError(
                    f"candidate hardware-support member is truncated: {member.name}"
                )
            remaining -= len(chunk)
    return None


def _validated_support_metadata(
    manifest_raw: bytes, *, expected_sha: str, expected_size: int
) -> InspectedSupportMetadata:
    """Validate the inner support manifest accounting (no filesystem use)."""
    try:
        raw = json.loads(manifest_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateSupportError(
            "candidate hardware-support manifest is not valid JSON"
        ) from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise CandidateSupportError(
            "unsupported candidate hardware-support manifest schema"
        )
    entries = raw.get("packages")
    if not isinstance(entries, list) or len(entries) > MAX_CANDIDATE_SUPPORT_MEMBERS:
        raise CandidateSupportError(
            "candidate hardware-support package list is invalid"
        )
    total = 0
    total_installed = 0
    for entry in entries:
        if not isinstance(entry, dict):
            raise CandidateSupportError(
                "candidate hardware-support package entry is invalid"
            )
        size = entry.get("size")
        installed = entry.get("installed_bytes")
        if (
            not isinstance(size, int)
            or isinstance(size, bool)
            or not isinstance(installed, int)
            or isinstance(installed, bool)
            or size < 0
            or installed < 0
        ):
            raise CandidateSupportError(
                "candidate hardware-support package size facts are invalid"
            )
        total += size
        total_installed += installed
    manifest_total = raw.get("total_bytes")
    manifest_installed = raw.get("total_installed_bytes")
    if (
        not isinstance(manifest_total, int)
        or isinstance(manifest_total, bool)
        or manifest_total != total
        or not isinstance(manifest_installed, int)
        or isinstance(manifest_installed, bool)
        or manifest_installed != total_installed
    ):
        raise CandidateSupportError(
            "candidate hardware-support installed total does not match manifest"
        )
    if not 0 <= total <= MAX_CANDIDATE_SUPPORT_UNCOMPRESSED_BYTES:
        raise CandidateSupportError(
            "candidate hardware-support total size is outside Greia bounds"
        )
    if not 0 <= total_installed <= MAX_CANDIDATE_SUPPORT_UNCOMPRESSED_BYTES:
        raise CandidateSupportError(
            "candidate hardware-support installed total is outside Greia bounds"
        )
    index_bytes = 0
    indexes = raw.get("repository_indexes")
    if isinstance(indexes, dict):
        for _name, facts in indexes.items():
            if isinstance(facts, dict):
                size = facts.get("size")
                if isinstance(size, int) and not isinstance(size, bool) and size >= 0:
                    index_bytes += size
    return InspectedSupportMetadata(
        support_sha256=expected_sha,
        support_size=expected_size,
        total_bytes=total,
        total_installed_bytes=total_installed,
        uncompressed_bytes=0,
        member_count=0,
        extracted_size_bound=0,
    )


def _finish_inspection(
    *,
    counted: _HashingCountingReader,
    expected_sha: str,
    expected_size: int,
    manifest_raw: bytes | None,
    uncompressed_bytes: int,
    member_count: int,
) -> InspectedSupportMetadata:
    """Verify the streamed size/digest and bind the validated metadata."""
    if counted.read_bytes != expected_size:
        raise CandidateSupportError(
            "candidate hardware-support size does not match manifest"
        )
    if counted.digest_hex() != expected_sha:
        raise CandidateSupportError(
            "candidate hardware-support digest does not match manifest"
        )
    if manifest_raw is None:
        raise CandidateSupportError(
            "candidate hardware-support tree has no manifest.json"
        )
    checked = _validated_support_metadata(
        manifest_raw, expected_sha=expected_sha, expected_size=expected_size
    )
    extracted_bound = (
        uncompressed_bytes + member_count * 512 + 10 * 1024
    )
    if extracted_bound > MAX_CANDIDATE_SUPPORT_UNCOMPRESSED_BYTES:
        raise CandidateSupportError(
            "candidate hardware-support uncompressed size is outside Greia bounds"
        )
    return InspectedSupportMetadata(
        support_sha256=expected_sha,
        support_size=expected_size,
        total_bytes=checked.total_bytes,
        total_installed_bytes=checked.total_installed_bytes,
        uncompressed_bytes=uncompressed_bytes,
        member_count=member_count,
        extracted_size_bound=extracted_bound,
    )


def inspect_support_metadata(
    bundle_path: Path,
    *,
    expected_sha: str,
    expected_size: int,
) -> InspectedSupportMetadata:
    """Stream the member for digest-verified facts without writing files.

    Reads ``ZipExtFile`` through the bounded hashing/counting reader into
    the zstd stream reader and the streaming tar parser, validating the
    exact support-tree shape while buffering only ``manifest.json``
    (bounded) and discarding every other member body in chunks. Verifies
    the streamed size and SHA-256 against the inspected manifest facts and
    validates the inner installed accounting, so the returned
    ``extracted_size_bound`` is deterministic authenticated metadata the
    PERSIST preflight may spend before any materialization begins. The
    full archive never resides in RAM and nothing is written to disk.
    """
    if expected_size <= 0 or expected_size > MAX_CANDIDATE_SUPPORT_COMPRESSED_BYTES:
        raise CandidateSupportError(
            "candidate hardware-support size is outside Greia bounds"
        )
    _checked_bundle_size(Path(bundle_path))
    archive, source = _open_member_stream(
        Path(bundle_path), expected_size=expected_size
    )
    counted = _HashingCountingReader(source, expected_size=expected_size)
    reader = _zstd_stream(counted)
    manifest_raw: bytes | None = None
    uncompressed_bytes = 0
    member_count = 0
    try:
        try:
            with tarfile.open(fileobj=reader, mode="r|") as tar:
                for member in tar:
                    member_count += 1
                    if member_count > MAX_CANDIDATE_SUPPORT_MEMBERS:
                        raise CandidateSupportError(
                            "candidate hardware-support member count is "
                            "outside Greia bounds"
                        )
                    if not _check_member_shape(member):
                        continue
                    uncompressed_bytes += member.size
                    if (
                        uncompressed_bytes
                        > MAX_CANDIDATE_SUPPORT_UNCOMPRESSED_BYTES
                    ):
                        raise CandidateSupportError(
                            "candidate hardware-support uncompressed size is "
                            "outside Greia bounds"
                        )
                    buffered = _drain_member(tar, member)
                    if buffered is not None:
                        if manifest_raw is not None:
                            raise CandidateSupportError(
                                "candidate hardware-support carries a duplicate "
                                "member: 'manifest.json'"
                            )
                        manifest_raw = buffered
                drained = reader.read(_CHUNK_BYTES)
                while drained:
                    uncompressed_bytes += len(drained)
                    if (
                        uncompressed_bytes
                        > MAX_CANDIDATE_SUPPORT_UNCOMPRESSED_BYTES
                    ):
                        raise CandidateSupportError(
                            "candidate hardware-support uncompressed size is "
                            "outside Greia bounds"
                        )
                    drained = reader.read(_CHUNK_BYTES)
        except CandidateSupportError:
            raise
        except Exception as exc:
            raise CandidateSupportError(
                "candidate hardware-support archive is not a safe Greia "
                f"tree: {exc}"
            ) from exc
    finally:
        _close_stream(reader)
        try:
            source.close()
        except Exception:
            pass
        archive.close()
    return _finish_inspection(
        counted=counted,
        expected_sha=expected_sha,
        expected_size=expected_size,
        manifest_raw=manifest_raw,
        uncompressed_bytes=uncompressed_bytes,
        member_count=member_count,
    )


def refuse_unless_persist_fits(
    staging_parent: Path,
    *,
    bundle_size: int,
    extracted_size_bound: int,
) -> int:
    """Refuse staging unless PERSIST keeps bundle + tree + reserve free.

    The staging filesystem must currently offer at least the already
    stored ``candidate.greiaupdate`` bytes plus the deterministic
    extracted-tree requirement plus the 256 MiB Greia operating reserve.
    Materialization never begins when it could exhaust PERSIST; scratch
    is never moved elsewhere to evade this accounting. Returns the
    required bytes so callers and tests can assert headroom explicitly.
    """
    if bundle_size <= 0 or extracted_size_bound < 0:
        raise CandidateSupportError(
            "candidate support staging facts are invalid"
        )
    parent = Path(staging_parent)
    try:
        parent.mkdir(parents=True, exist_ok=True)
        os.chmod(parent, 0o700)
    except OSError as exc:
        raise CandidateSupportError(
            "candidate support staging area is unavailable"
        ) from exc
    try:
        free_bytes = shutil.disk_usage(parent).free
    except OSError as exc:
        raise CandidateSupportError(
            "candidate support staging area is unavailable"
        ) from exc
    required = bundle_size + extracted_size_bound + STAGING_OPERATING_RESERVE_BYTES
    if free_bytes < required:
        raise CandidateSupportError(
            "candidate support staging would exhaust PERSIST: "
            f"need {required} bytes (bundle {bundle_size} + extracted "
            f"{extracted_size_bound} + reserve "
            f"{STAGING_OPERATING_RESERVE_BYTES}) but only {free_bytes} "
            "bytes are free; refusing before extraction"
        )
    return required


def extract_support_tree(
    bundle_path: Path,
    *,
    expected_sha: str,
    expected_size: int,
    destination: Path,
) -> InspectedSupportMetadata:
    """Stream the member directly into ``destination`` (single extraction).

    Data path: ``ZipExtFile`` → bounded hashing/counting reader →
    ``ZstdDecompressor.stream_reader`` → streaming ``tarfile`` extraction.
    No full-archive RAM load, no intermediate compressed temp file. The
    streamed size and SHA-256 are re-verified against the inspected
    manifest facts, so a candidate that changed after inspection fails
    closed here. Returns the same digest-verified metadata
    :func:`inspect_support_metadata` reports.
    """
    if expected_size <= 0 or expected_size > MAX_CANDIDATE_SUPPORT_COMPRESSED_BYTES:
        raise CandidateSupportError(
            "candidate hardware-support size is outside Greia bounds"
        )
    _checked_bundle_size(Path(bundle_path))
    target_dir = Path(destination)
    archive, source = _open_member_stream(
        Path(bundle_path), expected_size=expected_size
    )
    counted = _HashingCountingReader(source, expected_size=expected_size)
    reader = _zstd_stream(counted)
    manifest_raw: bytes | None = None
    uncompressed_bytes = 0
    member_count = 0
    try:
        try:
            with tarfile.open(fileobj=reader, mode="r|") as tar:
                for member in tar:
                    member_count += 1
                    if member_count > MAX_CANDIDATE_SUPPORT_MEMBERS:
                        raise CandidateSupportError(
                            "candidate hardware-support member count is "
                            "outside Greia bounds"
                        )
                    # _extract_one re-validates the header shape (names,
                    # symlinks, device nodes, expected tree, per-file and
                    # total bounds) while streaming the body straight to
                    # disk in bounded chunks: one extraction, no RAM load.
                    uncompressed_bytes = _extract_one(
                        tar,
                        member,
                        destination=target_dir,
                        total_uncompressed=uncompressed_bytes,
                    )
                drained = reader.read(_CHUNK_BYTES)
                while drained:
                    uncompressed_bytes += len(drained)
                    if (
                        uncompressed_bytes
                        > MAX_CANDIDATE_SUPPORT_UNCOMPRESSED_BYTES
                    ):
                        raise CandidateSupportError(
                            "candidate hardware-support uncompressed size is "
                            "outside Greia bounds"
                        )
                    drained = reader.read(_CHUNK_BYTES)
        except CandidateSupportError:
            raise
        except Exception as exc:
            raise CandidateSupportError(
                "candidate hardware-support archive is not a safe Greia "
                f"tree: {exc}"
            ) from exc
    finally:
        _close_stream(reader)
        try:
            source.close()
        except Exception:
            pass
        archive.close()
    manifest_path = target_dir / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise CandidateSupportError(
            "candidate hardware-support tree has no manifest.json"
        )
    try:
        manifest_raw = manifest_path.read_bytes()
    except OSError as exc:
        raise CandidateSupportError(
            "candidate hardware-support manifest is unreadable"
        ) from exc
    if len(manifest_raw) > MAX_SUPPORT_MANIFEST_BYTES:
        raise CandidateSupportError(
            "candidate hardware-support manifest is outside Greia bounds"
        )
    metadata = _finish_inspection(
        counted=counted,
        expected_sha=expected_sha,
        expected_size=expected_size,
        manifest_raw=manifest_raw,
        uncompressed_bytes=uncompressed_bytes,
        member_count=member_count,
    )
    return metadata


class CandidateSupportStage:
    """One stage-owned hardware-support materialization (T03).

    Exactly one streaming extraction per stage: :meth:`open` inspects the
    digest-verified member metadata, runs the PERSIST preflight, extracts
    the tree once, and loads one verified pool instance. That same pool
    instance drives both support-set resolution (via
    ``pool_to_support_set``) and package installation (via
    ``InstallerSlotPackageInstaller``): no second materialization, no
    running-image pool substitution, no global mutable state. Restages
    open a fresh stage; a stage never reuses another stage's pool.
    :meth:`close` removes the temp root on success and on any exception
    and is idempotent, so backend ``finally`` blocks and tests share one
    cleanup owner.
    """

    __slots__ = (
        "bundle_path",
        "expected_sha",
        "expected_size",
        "staging_parent",
        "metadata",
        "root",
        "pool",
        "closed",
    )

    def __init__(
        self,
        *,
        bundle_path: Path,
        expected_sha: str,
        expected_size: int,
        staging_parent: Path,
        metadata: InspectedSupportMetadata,
        root: Path,
        pool: object,
    ) -> None:
        self.bundle_path = bundle_path
        self.expected_sha = expected_sha
        self.expected_size = expected_size
        self.staging_parent = staging_parent
        self.metadata = metadata
        self.root = root
        self.pool = pool
        self.closed = False

    @classmethod
    def open(
        cls,
        bundle_path: Path,
        manifest: object,
        staging_parent: Path,
        *,
        pool_loader: Callable[[Path], object] | None = None,
    ) -> "CandidateSupportStage":
        """Inspect, preflight, extract once, and load the stage pool."""
        expected_sha, expected_size = _checked_manifest_facts(manifest)
        bundle = Path(bundle_path)
        bundle_size = _checked_bundle_size(bundle)
        metadata = inspect_support_metadata(
            bundle, expected_sha=expected_sha, expected_size=expected_size
        )
        refuse_unless_persist_fits(
            Path(staging_parent),
            bundle_size=bundle_size,
            extracted_size_bound=metadata.extracted_size_bound,
        )
        parent = Path(staging_parent)
        try:
            root = Path(
                tempfile.mkdtemp(prefix="candidate-support-", dir=str(parent))
            )
            os.chmod(root, 0o700)
        except OSError as exc:
            raise CandidateSupportError(
                "candidate support staging area is unavailable"
            ) from exc
        try:
            extract_support_tree(
                bundle,
                expected_sha=expected_sha,
                expected_size=expected_size,
                destination=root,
            )
            if pool_loader is None:
                from greia_installer.hardware_support import (
                    VerifiedHardwareSupportPool,
                )

                pool = VerifiedHardwareSupportPool.load(root)
            else:
                pool = pool_loader(root)
        except Exception:
            shutil.rmtree(root, ignore_errors=True)
            raise
        return cls(
            bundle_path=bundle,
            expected_sha=expected_sha,
            expected_size=expected_size,
            staging_parent=parent,
            metadata=metadata,
            root=root,
            pool=pool,
        )

    @property
    def installed_size_bound(self) -> int:
        """Verified installed-size bound carried into capacity accounting."""
        bound = getattr(self.pool, "total_installed_bytes", None)
        if (
            not isinstance(bound, int)
            or isinstance(bound, bool)
            or bound < 0
        ):
            raise CandidateSupportError(
                "candidate support installed-size bound is not authoritative"
            )
        return bound

    def stage_identity(self) -> tuple[str, str, int]:
        """Bundle identity this stage materialized (restage comparison)."""
        return (str(self.bundle_path), self.expected_sha, self.expected_size)

    def close(self) -> None:
        """Remove the temp root; idempotent, never raises."""
        if self.closed:
            return
        self.closed = True
        shutil.rmtree(self.root, ignore_errors=True)

    def __enter__(self) -> "CandidateSupportStage":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def _extract_one(
    tar: tarfile.TarFile,
    member: tarfile.TarInfo,
    *,
    destination: Path,
    total_uncompressed: int,
) -> int:
    """Validate and extract one streaming tar member; return the new total."""
    name = member.name
    _reject_unsafe_name(name)
    if member.issym() or member.islnk():
        raise CandidateSupportError(
            "candidate hardware-support symlinks are not supported"
        )
    if member.isdev() or member.isfifo():
        raise CandidateSupportError(
            "candidate hardware-support special files are not supported"
        )
    if member.isdir():
        if name.rstrip("/") not in ("", ".", _POOL_DIR):
            raise CandidateSupportError(
                f"candidate hardware-support has an unexpected directory: {name}"
            )
        return total_uncompressed
    if not member.isfile():
        raise CandidateSupportError(
            f"candidate hardware-support has an unexpected shape: {name}"
        )
    _require_expected_file(name)
    if member.size < 0 or member.size > MAX_CANDIDATE_SUPPORT_FILE_BYTES:
        raise CandidateSupportError(
            f"candidate hardware-support file is outside Greia bounds: {name}"
        )
    total_uncompressed += member.size
    if total_uncompressed > MAX_CANDIDATE_SUPPORT_UNCOMPRESSED_BYTES:
        raise CandidateSupportError(
            "candidate hardware-support uncompressed size is outside Greia bounds"
        )
    target = destination / name
    if target.is_symlink():
        raise CandidateSupportError(
            f"candidate hardware-support target is unsafe: {name}"
        )
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(target.parent, 0o700)
    except OSError as exc:
        raise CandidateSupportError(
            f"candidate hardware-support directory is not ownable: {name}"
        ) from exc
    source = tar.extractfile(member)
    if source is None:
        raise CandidateSupportError(
            f"candidate hardware-support member is unreadable: {name}"
        )
    try:
        with source, target.open("wb") as handle:
            remaining = member.size
            while remaining > 0:
                chunk = source.read(min(_CHUNK_BYTES, remaining))
                if not chunk:
                    raise CandidateSupportError(
                        f"candidate hardware-support member is truncated: {name}"
                    )
                remaining -= len(chunk)
                handle.write(chunk)
        os.chmod(target, 0o600)
    except OSError as exc:
        raise CandidateSupportError(
            f"candidate hardware-support extraction failed: {name}"
        ) from exc
    return total_uncompressed


def _reject_unsafe_name(name: str) -> None:
    """Reject absolute paths, escapes, and non-portable separators."""
    if not name or name.startswith("/") or "\\" in name:
        raise CandidateSupportError(
            "candidate hardware-support contains an unsafe member"
        )
    parts = Path(name).parts
    if not parts or ".." in parts or "." in parts:
        raise CandidateSupportError(
            "candidate hardware-support contains an unsafe member"
        )


def _require_expected_file(name: str) -> None:
    """Restrict regular files to the exact release-builder tree shape."""
    if name in _TOP_FILES:
        return
    parts = Path(name).parts
    if (
        len(parts) == 2
        and parts[0] == _POOL_DIR
        and parts[1].endswith(".deb")
        and parts[1] not in (".deb",)
    ):
        return
    raise CandidateSupportError(
        f"candidate hardware-support has an unexpected file: {name}"
    )
