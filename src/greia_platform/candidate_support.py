"""Candidate hardware-support staging (Repair D / T03 single-materialization).

Routes the exact candidate ``.greiaupdate`` ``hardware-support.tar.zst``
member — not the running system's ``/opt/greia-hardware-support`` pool —
into candidate finalization::

    candidate.greiaupdate -> ZipExtFile -> hashing/counting reader
    -> ZstdDecompressor.stream_reader -> tarfile streaming extraction
    -> temp candidate support root -> VerifiedHardwareSupportPool.load
    -> selection + TargetHardwareSupportInstaller -> cleanup temp root

One :class:`CandidateSupportStage` owns one stage: it performs exactly
one streaming traversal that parses the streamed inner manifest
mid-stream, runs the PERSIST free-space preflight against the
builder-declared extracted-bytes bound before any payload byte reaches
disk, extracts the tree, binds the observed-vs-declared verdicts, and
loads exactly one verified pool instance. That same pool instance
drives both support-set resolution and package installation, so a stage
never materializes the member twice and the installer can never
substitute the running-image pool. The temp root is removed on success
and on any exception. There is no intermediate compressed temp file
(never ``.hardware-support.tar.zst.tmp``) and the full archive is never
loaded into RAM: the single pass streams in bounded chunks while only
small metadata members are buffered under explicit caps.

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
import os
import shutil
import stat
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Callable

from greia_installer import hardware_support_archive as _archive


class CandidateSupportError(RuntimeError):
    """The candidate hardware-support member is missing or unsafe."""


def _wrap_archive_error(exc: Exception) -> CandidateSupportError:
    return CandidateSupportError(str(exc))


#: Zip member name inside the candidate bundle. Mirrors
#: ``greia_platform.system_updates.HARDWARE_SUPPORT_NAME`` (kept local so
#: this module never imports the service composition it serves).
HARDWARE_SUPPORT_MEMBER = "hardware-support.tar.zst"

#: Staging directory name under ``<state>/system-updates/``.
STAGING_DIR_NAME = "candidate-support"

#: Single production compressed member bound. Canonical owner is the
#: shared archive module (mirrors
#: ``system_updates.MAX_HARDWARE_SUPPORT_BYTES``, sync-tested there).
MAX_CANDIDATE_SUPPORT_COMPRESSED_BYTES = _archive.MAX_ARCHIVE_COMPRESSED_BYTES

#: Single production uncompressed-tar bound (canonical owner: shared).
MAX_CANDIDATE_SUPPORT_UNCOMPRESSED_BYTES = _archive.MAX_ARCHIVE_UNCOMPRESSED_BYTES

#: Single per-file bound inside the tar (canonical owner: shared).
MAX_CANDIDATE_SUPPORT_FILE_BYTES = _archive.MAX_ARCHIVE_FILE_BYTES

#: Single member-count bound (canonical owner: shared).
MAX_CANDIDATE_SUPPORT_MEMBERS = _archive.MAX_ARCHIVE_MEMBERS

#: Bound for buffering the inner support ``manifest.json`` (canonical
#: owner: shared archive module).
MAX_SUPPORT_MANIFEST_BYTES = _archive.MAX_ARCHIVE_MANIFEST_BYTES

#: Operating reserve kept free on the staging filesystem alongside the
#: staged bundle and the extracted tree. Mirrors the inbox reserve
#: (``system_updates`` 256 MiB operating reserve); kept local so this
#: module never imports the service composition it serves.
STAGING_OPERATING_RESERVE_BYTES = 256 * 1024 * 1024

#: Exact expected top-level release files (canonical owner: shared).
_TOP_FILES = _archive.TOP_FILES
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


class _HashingCountingReader(_archive.HashingCountingReader):
    """Backward-compat alias: counting ownership lives in shared module."""

    def read(self, size: int = -1) -> bytes:
        try:
            return super().read(size)
        except _archive.HardwareSupportArchiveError as exc:
            raise CandidateSupportError(str(exc)) from exc


def _checked_outer_bound(manifest: object) -> int | None:
    """Return the outer-manifest extracted-bytes bound when present.

    R4-G2-SUPPORT-BOUND: the outer ``.greiaupdate`` manifest may carry the
    stable ``extracted_bytes_bound`` alongside the sha/size facts. ``None``
    keeps the absent-field backward-compatible path (mid-stream preflight
    only). A present field must be a plain integer inside the shared
    uncompressed cap; anything else refuses before the support stream
    opens.
    """
    bound = getattr(manifest, "hardware_support_extracted_bytes_bound", None)
    if bound is None:
        return None
    if (
        isinstance(bound, bool)
        or not isinstance(bound, int)
        or bound < 0
        or bound > MAX_CANDIDATE_SUPPORT_UNCOMPRESSED_BYTES
    ):
        raise CandidateSupportError(
            "candidate hardware-support outer extracted bound is outside Greia bounds"
        )
    return bound


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
        return _archive._zstd_stream(source)
    except _archive.HardwareSupportArchiveError as exc:
        raise CandidateSupportError(str(exc)) from exc


def _close_stream(stream: object) -> None:
    _archive._close_stream(stream)


def _shared_to_inspected(
    metadata: _archive.HardwareSupportArchiveMetadata,
) -> InspectedSupportMetadata:
    """Convert shared metadata to the stable runtime metadata shape."""
    return InspectedSupportMetadata(
        support_sha256=metadata.support_sha256,
        support_size=metadata.support_size,
        total_bytes=metadata.total_bytes,
        total_installed_bytes=metadata.total_installed_bytes,
        uncompressed_bytes=metadata.uncompressed_bytes,
        member_count=metadata.member_count,
        extracted_size_bound=metadata.extracted_size_bound,
    )


def inspect_support_metadata(
    bundle_path: Path,
    *,
    expected_sha: str,
    expected_size: int,
) -> InspectedSupportMetadata:
    """Stream the member for digest-verified facts without writing files.

    Thin runtime wrapper: delegates every header/member/manifest verdict
    to the shared streaming parser
    (``hardware_support_archive.inspect_compressed_stream``). The
    returned ``extracted_size_bound`` is deterministic authenticated
    metadata the PERSIST preflight may spend before any materialization
    begins. The full archive never resides in RAM and nothing is written
    to disk.
    """
    if expected_size <= 0 or expected_size > MAX_CANDIDATE_SUPPORT_COMPRESSED_BYTES:
        raise CandidateSupportError(
            "candidate hardware-support size is outside Greia bounds"
        )
    _checked_bundle_size(Path(bundle_path))
    archive, source = _open_member_stream(
        Path(bundle_path), expected_size=expected_size
    )
    try:
        try:
            metadata = _archive.inspect_compressed_stream(
                source,  # type: ignore[arg-type]
                expected_compressed_bytes=expected_size,
                expected_sha256=expected_sha,
            )
        except _archive.HardwareSupportArchiveError as exc:
            raise CandidateSupportError(str(exc)) from exc
        except Exception as exc:
            raise CandidateSupportError(
                "candidate hardware-support archive is not a safe Greia "
                f"tree: {exc}"
            ) from exc
    finally:
        try:
            source.close()
        except Exception:
            pass
        archive.close()
    return _shared_to_inspected(metadata)


@dataclass(frozen=True, slots=True)
class SupportStagingCapacity:
    """Unambiguous PERSIST staging headroom verdict.

    ``free_bytes`` is the current free space observed on the staging
    filesystem. ``extracted_size_bound`` is the deterministic additional
    tree requirement and ``reserve_bytes`` is the final operating
    reserve that must remain free after staging. Their sum is
    ``required_additional_free_bytes`` — the only inequality the
    preflight enforces (``free_bytes >= required_additional_free_bytes``).

    ``bundle_size_bytes`` records the already-stored
    ``candidate.greiaupdate`` size for diagnostics only: ``free_bytes``
    already reflects those resident bytes, so they never enter the
    inequality.
    """

    free_bytes: int
    extracted_size_bound: int
    reserve_bytes: int
    required_additional_free_bytes: int
    bundle_size_bytes: int


def require_support_staging_free_space(
    staging_parent: Path,
    *,
    bundle_size: int,
    extracted_size_bound: int,
) -> SupportStagingCapacity:
    """Refuse staging unless PERSIST covers the tree plus reserve.

    The candidate bundle (``bundle_size`` bytes) is already stored on
    PERSIST when this preflight runs, so ``shutil.disk_usage(parent).free``
    already reflects those resident bytes. Only the additional bytes —
    the deterministic ``extracted_size_bound`` plus the Greia operating
    reserve — must fit in current free space::

        required_additional = extracted_size_bound + STAGING_OPERATING_RESERVE_BYTES
        refuse unless free_bytes >= required_additional

    ``bundle_size`` appears in diagnostics only and never in the
    inequality. Materialization never begins when it could exhaust
    PERSIST; scratch is never moved elsewhere to evade this accounting.
    Returns the typed :class:`SupportStagingCapacity` verdict so callers
    and tests can assert headroom explicitly.
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
    required_additional = (
        extracted_size_bound + STAGING_OPERATING_RESERVE_BYTES
    )
    if free_bytes < required_additional:
        raise CandidateSupportError(
            "candidate support staging would exhaust PERSIST: "
            f"need {required_additional} bytes additional (extracted "
            f"{extracted_size_bound} + reserve "
            f"{STAGING_OPERATING_RESERVE_BYTES}) but only {free_bytes} "
            f"bytes are free; bundle {bundle_size} bytes already stored, "
            "not additional; refusing before extraction"
        )
    return SupportStagingCapacity(
        free_bytes=free_bytes,
        extracted_size_bound=extracted_size_bound,
        reserve_bytes=STAGING_OPERATING_RESERVE_BYTES,
        required_additional_free_bytes=required_additional,
        bundle_size_bytes=bundle_size,
    )


def refuse_unless_persist_fits(
    staging_parent: Path,
    *,
    bundle_size: int,
    extracted_size_bound: int,
) -> SupportStagingCapacity:
    """Deprecated alias for :func:`require_support_staging_free_space`.

    Preserved so out-of-tree callers keep working. The corrected
    accounting applies: the already-stored bundle is diagnostic only and
    never enters the free-space inequality.
    """
    return require_support_staging_free_space(
        Path(staging_parent),
        bundle_size=bundle_size,
        extracted_size_bound=extracted_size_bound,
    )


#: Staging RAM buffer caps for the small metadata members held before the
#: mid-stream PERSIST preflight fires (Repair R4-EF-STAGE). Only
#: ``manifest.json`` (shared manifest bound) and the two repository
#: indexes (shared index bound) are ever buffered; pool payloads always
#: stream straight to disk. A member larger than its buffer cap is refused
#: before any byte is buffered — the shared finish would refuse such an
#: archive anyway (declared index sizes above the cap are invalid, member
#: sizes above the declared values are size mismatches), so the cap only
#: moves the refusal earlier while keeping RAM bounded.
_STAGED_MANIFEST_BUFFER_BYTES = _archive.MAX_ARCHIVE_MANIFEST_BYTES
_STAGED_INDEX_BUFFER_BYTES = _archive.MAX_ARCHIVE_INDEX_BYTES


def _read_exact_body(source: object, size: int, *, label: str) -> bytes:
    """Read exactly ``size`` streamed bytes into RAM (small metadata only)."""
    pieces: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = source.read(min(_CHUNK_BYTES, remaining))  # type: ignore[union-attr]
        if not chunk:
            raise CandidateSupportError(
                f"candidate hardware-support member is truncated: {label}"
            )
        remaining -= len(chunk)
        pieces.append(chunk)
    return b"".join(pieces)


def _write_staged_bytes(destination: Path, normalized: str, data: bytes) -> None:
    """Write buffered small-file bytes with staging ownership/permissions."""
    target = Path(destination) / normalized
    if target.is_symlink():
        raise CandidateSupportError(
            f"candidate hardware-support target is unsafe: {normalized}"
        )
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(target.parent, 0o700)
    except OSError as exc:
        raise CandidateSupportError(
            f"candidate hardware-support directory is not ownable: {normalized}"
        ) from exc
    try:
        with target.open("wb") as handle:
            handle.write(data)
        os.chmod(target, 0o600)
    except OSError as exc:
        raise CandidateSupportError(
            f"candidate hardware-support extraction failed: {normalized}"
        ) from exc


def _staged_preflight_bound(manifest_data: bytes, manifest_member_size: int) -> int:
    """Return the builder-declared extracted-bytes bound for preflight.

    Parses the streamed inner ``manifest.json`` (already digest-tracked)
    and returns the authoritative staging bound: the explicit builder
    ``extracted_bytes_bound`` field when present, otherwise the shared
    conservative model recomputed from the manifest-declared file sizes
    with the member-count cap as the conservative count padding. A
    present field must at least cover the manifest-declared file blocks;
    anything lower is an observed-vs-declared mismatch refused here,
    before any payload byte reaches disk. Exact byte-for-byte equality
    with the observed stream is enforced post-stream by the shared
    finish.
    """
    try:
        validated = _archive.parse_manifest_bytes(manifest_data)
    except _archive.HardwareSupportArchiveError as exc:
        raise CandidateSupportError(str(exc)) from exc
    declared_sizes = [item.size for item in validated.packages]
    for index_name in ("Packages", "Packages.gz"):
        declared_sizes.append(validated.repository_indexes[index_name]["size"])  # type: ignore[arg-type]
    declared_sizes.append(manifest_member_size)
    if validated.extracted_bound is not None:
        try:
            floor = _archive.extracted_bytes_bound_for_members(
                declared_sizes, member_count=len(declared_sizes)
            )
        except _archive.HardwareSupportArchiveError as exc:
            raise CandidateSupportError(str(exc)) from exc
        if validated.extracted_bound < floor:
            raise CandidateSupportError(
                "candidate hardware-support observed-vs-declared extracted "
                "bound mismatch: declared bound is below the declared file blocks"
            )
        return validated.extracted_bound
    try:
        return _archive.extracted_bytes_bound_for_members(
            declared_sizes, member_count=MAX_CANDIDATE_SUPPORT_MEMBERS
        )
    except _archive.HardwareSupportArchiveError as exc:
        raise CandidateSupportError(str(exc)) from exc


def extract_support_tree(
    bundle_path: Path,
    *,
    expected_sha: str,
    expected_size: int,
    destination: Path,
    preflight: Callable[[int], object] | None = None,
    outer_extracted_bound: int | None = None,
) -> InspectedSupportMetadata:
    """One archive traversal: stream the member, validate, extract, verify.

    Data path: ``ZipExtFile`` → bounded hashing/counting reader →
    ``ZstdDecompressor.stream_reader`` → streaming ``tarfile`` validation
    and extraction. The member is decompressed exactly once: small
    metadata members (``manifest.json`` + repository indexes, bounded RAM
    caps) are buffered while pool payloads stream straight to disk with
    incremental hashing — no separate metadata-inspection pass, no
    full-archive RAM load, no intermediate compressed temp file.

    When ``preflight`` is given (candidate staging) without an outer
    bound, nothing reaches disk before the streamed inner manifest is
    parsed and ``preflight`` accepts the builder-declared
    extracted-bytes bound, so the R4-C-PERSIST refusal still precedes
    any extraction, and a pool payload arriving before ``manifest.json``
    is refused (manifest-first staging order: the bound must be known
    before payload writes). When ``outer_extracted_bound`` carries the
    outer-manifest bound (R4-G2-SUPPORT-BOUND pre-stream preflight
    already passed in :meth:`CandidateSupportStage.open`), the
    manifest-first order refusal is lifted: payloads stream straight to
    disk under the outer reservation, the streamed inner declaration
    must equal the outer value byte-for-byte on arrival, and the shared
    finish still binds observed-vs-declared equality post-stream before
    ``VerifiedHardwareSupportPool.load``. Without ``preflight`` the
    pass is a pure verify-extract preserving the shared shape verdicts.

    Post-stream, the streamed size/SHA-256 are re-verified against the
    inspected manifest facts and the shared finish binds per-member
    sizes/digests, repository indexes and the observed-vs-declared
    extracted bound, so a candidate that changed after inspection fails
    closed here. Returns the same digest-verified metadata
    :func:`inspect_support_metadata` reports.
    """
    if expected_size <= 0 or expected_size > MAX_CANDIDATE_SUPPORT_COMPRESSED_BYTES:
        raise CandidateSupportError(
            "candidate hardware-support size is outside Greia bounds"
        )
    if outer_extracted_bound is not None and (
        isinstance(outer_extracted_bound, bool)
        or not isinstance(outer_extracted_bound, int)
        or outer_extracted_bound < 0
        or outer_extracted_bound > MAX_CANDIDATE_SUPPORT_UNCOMPRESSED_BYTES
    ):
        raise CandidateSupportError(
            "candidate hardware-support outer extracted bound is outside Greia bounds"
        )
    _checked_bundle_size(Path(bundle_path))
    target_dir = Path(destination)
    archive, source = _open_member_stream(
        Path(bundle_path), expected_size=expected_size
    )
    counted = _HashingCountingReader(source, expected_size=expected_size)
    reader = _zstd_stream(counted)
    member_sizes: dict[str, int] = {}
    member_digests: dict[str, str] = {}
    seen: set[str] = set()
    pending_small: dict[str, bytes] = {}
    uncompressed_bytes = 0
    member_count = 0
    # R4-G2-SUPPORT-BOUND: when the outer bound already owns capacity
    # (pre-stream preflight passed in Stage.open), the manifest-first
    # order gate is lifted so pool payloads need not wait for the inner
    # manifest; inner-vs-outer equality is still enforced on arrival and
    # observed-vs-declared equality post-stream.
    preflight_done = (preflight is None) or (outer_extracted_bound is not None)
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
                    try:
                        normalized, kind = _archive.validate_member_header(member)
                    except _archive.HardwareSupportArchiveError as exc:
                        raise CandidateSupportError(str(exc)) from exc
                    if normalized in seen:
                        raise CandidateSupportError(
                            "candidate hardware-support carries a duplicate "
                            f"member: {normalized!r}"
                        )
                    seen.add(normalized)
                    if kind == "dir":
                        continue
                    body = tar.extractfile(member)
                    if body is None:
                        raise CandidateSupportError(
                            f"candidate hardware-support member is unreadable: {normalized}"
                        )
                    if normalized in _TOP_FILES:
                        with body:
                            # Small metadata is accounted here (buffered
                            # bodies bypass _extract_one, which owns the
                            # accounting for streamed payloads below).
                            uncompressed_bytes += member.size
                            if (
                                uncompressed_bytes
                                > MAX_CANDIDATE_SUPPORT_UNCOMPRESSED_BYTES
                            ):
                                raise CandidateSupportError(
                                    "candidate hardware-support uncompressed "
                                    "size is outside Greia bounds"
                                )
                            cap = (
                                _STAGED_MANIFEST_BUFFER_BYTES
                                if normalized == "manifest.json"
                                else _STAGED_INDEX_BUFFER_BYTES
                            )
                            if member.size > cap or member.size <= 0:
                                raise CandidateSupportError(
                                    "candidate hardware-support metadata member "
                                    f"is outside Greia bounds: {normalized!r}"
                                )
                            data = _read_exact_body(
                                body, member.size, label=normalized
                            )
                            member_sizes[normalized] = member.size
                            member_digests[normalized] = hashlib.sha256(data).hexdigest()
                            if normalized == "manifest.json":
                                declared = _staged_preflight_bound(
                                    data, member.size
                                )
                                if outer_extracted_bound is not None:
                                    # When the inner manifest carries an
                                    # explicit bound, it must equal the
                                    # outer value byte-for-byte here;
                                    # when the inner predates the field
                                    # (absent), the mid-stream fallback is
                                    # the padded over-approximation, so
                                    # equality is deferred to the
                                    # post-stream outer-vs-observed check
                                    # (tight bound), which the outer
                                    # derivation already matches.
                                    try:
                                        _validated = _archive.parse_manifest_bytes(data)
                                    except _archive.HardwareSupportArchiveError as exc:
                                        raise CandidateSupportError(str(exc)) from exc
                                    if _validated.extracted_bound is not None and (
                                        declared != outer_extracted_bound
                                    ):
                                        raise CandidateSupportError(
                                            "candidate hardware-support outer-vs-inner "
                                            "extracted bound mismatch: outer "
                                            f"{outer_extracted_bound} != inner {declared}"
                                        )
                                if preflight is not None and outer_extracted_bound is None:
                                    preflight(declared)
                                    for pending_name, pending_data in pending_small.items():
                                        _write_staged_bytes(
                                            target_dir, pending_name, pending_data
                                        )
                                    pending_small.clear()
                                    _write_staged_bytes(target_dir, normalized, data)
                                    preflight_done = True
                                else:
                                    # Outer pre-stream owns capacity (or pure
                                    # verify): the inner declaration was
                                    # already checked against the outer value
                                    # above and the shared finish still binds
                                    # observed-vs-declared post-stream.
                                    for pending_name, pending_data in pending_small.items():
                                        _write_staged_bytes(
                                            target_dir, pending_name, pending_data
                                        )
                                    pending_small.clear()
                                    _write_staged_bytes(target_dir, normalized, data)
                                    preflight_done = True
                            elif preflight_done:
                                _write_staged_bytes(target_dir, normalized, data)
                            else:
                                pending_small[normalized] = data
                    else:
                        if not preflight_done:
                            try:
                                body.close()
                            except Exception:
                                pass
                            raise CandidateSupportError(
                                "candidate hardware-support pool payload "
                                f"precedes manifest.json (refused): {normalized!r}"
                            )
                        # The already-open body is threaded through:
                        # exactly one extractfile open owns this member.
                        # _extract_one owns the per-member header verdict
                        # (shared.validate_member_header) and the bounded
                        # chunked stream-to-disk
                        # (shared.hash_and_copy_streamed_body) while
                        # accounting the uncompressed total. The header was
                        # already validated above; the write identity is
                        # reconciled after the write.
                        try:
                            new_total, written, digest = _extract_one(
                                tar,
                                member,
                                destination=target_dir,
                                total_uncompressed=uncompressed_bytes,
                                body=body,
                            )
                        except _archive.HardwareSupportArchiveError as exc:
                            raise CandidateSupportError(str(exc)) from exc
                        if written != normalized:
                            raise CandidateSupportError(
                                "candidate hardware-support member identity "
                                f"changed during staging: {normalized!r}"
                            )
                        uncompressed_bytes = new_total
                        member_sizes[normalized] = member.size
                        member_digests[normalized] = digest
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
    if member_sizes.get("manifest.json") != len(manifest_raw):
        raise CandidateSupportError(
            "candidate hardware-support manifest size does not match stream"
        )
    try:
        shared_metadata = _archive.finish_streamed_inspection(
            expected_compressed_bytes=expected_size,
            expected_sha256=expected_sha,
            counted_bytes=counted.read_bytes,
            counted_digest=counted.digest_hex(),
            manifest_raw=manifest_raw,
            member_sizes=member_sizes,
            member_digests=member_digests,
            seen=set(seen),
            uncompressed_bytes=uncompressed_bytes,
            member_count=member_count,
        )
    except _archive.HardwareSupportArchiveError as exc:
        raise CandidateSupportError(str(exc)) from exc
    return _shared_to_inspected(shared_metadata)


class CandidateSupportStage:
    """One stage-owned hardware-support materialization (T03).

    Exactly one streaming traversal per stage (Repair R4-EF-STAGE):
    :meth:`open` runs a single pass that parses the streamed inner
    manifest mid-stream, performs the PERSIST preflight against the
    builder-declared extracted-bytes bound before any payload write,
    extracts the tree once, binds the observed-vs-declared verdicts, and
    loads one verified pool instance. That same pool instance drives
    both support-set resolution (via ``pool_to_support_set``) and
    package installation (via ``InstallerSlotPackageInstaller``): no
    second materialization, no running-image pool substitution, no
    global mutable state. Restages open a fresh stage; a stage never
    reuses another stage's pool. :meth:`close` removes the temp root on
    success and on any exception and is idempotent, so backend
    ``finally`` blocks and tests share one cleanup owner.
    """

    __slots__ = (
        "bundle_path",
        "expected_sha",
        "expected_size",
        "expected_outer_bound",
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
        expected_outer_bound: int | None = None,
    ) -> None:
        self.bundle_path = bundle_path
        self.expected_sha = expected_sha
        self.expected_size = expected_size
        self.expected_outer_bound = expected_outer_bound
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
        """Inspect, preflight, extract once, and load the stage pool.

        Single archive traversal (Repair R4-EF-STAGE): the member is
        decompressed exactly once by :func:`extract_support_tree`, which
        parses the streamed inner manifest mid-stream, runs the PERSIST
        preflight against the builder-declared extracted-bytes bound
        before any payload byte reaches disk, then streams the tree and
        binds the observed-vs-declared verdicts. There is no separate
        metadata-inspection pass and no intermediate compressed copy.

        R4-G2-SUPPORT-BOUND: when the outer manifest carries
        ``hardware_support_extracted_bytes_bound``, the PERSIST
        preflight runs pre-stream against that outer bound before the
        support stream opens (same ``extracted bound + 256 MiB reserve``
        helper contract), the manifest-first order refusal is lifted for
        the single pass, and the outer value must equal the observed
        shared-model bound byte-for-byte after extraction. Absent outer
        bound keeps the mid-stream preflight + order gate.
        """
        expected_sha, expected_size = _checked_manifest_facts(manifest)
        outer_bound = _checked_outer_bound(manifest)
        bundle = Path(bundle_path)
        bundle_size = _checked_bundle_size(bundle)
        parent = Path(staging_parent)
        try:
            parent.mkdir(parents=True, exist_ok=True)
            os.chmod(parent, 0o700)
        except OSError as exc:
            raise CandidateSupportError(
                "candidate support staging area is unavailable"
            ) from exc
        try:
            root = Path(
                tempfile.mkdtemp(prefix="candidate-support-", dir=str(parent))
            )
            os.chmod(root, 0o700)
        except OSError as exc:
            raise CandidateSupportError(
                "candidate support staging area is unavailable"
            ) from exc

        def _preflight(declared_extracted_bound: int) -> None:
            require_support_staging_free_space(
                parent,
                bundle_size=bundle_size,
                extracted_size_bound=declared_extracted_bound,
            )

        try:
            if outer_bound is not None:
                # Pre-stream PERSIST preflight owns capacity before the
                # support stream opens: zero member writes on short space.
                require_support_staging_free_space(
                    parent,
                    bundle_size=bundle_size,
                    extracted_size_bound=outer_bound,
                )
            metadata = extract_support_tree(
                bundle,
                expected_sha=expected_sha,
                expected_size=expected_size,
                destination=root,
                preflight=_preflight,
                outer_extracted_bound=outer_bound,
            )
            if outer_bound is not None and metadata.extracted_size_bound != outer_bound:
                raise CandidateSupportError(
                    "candidate hardware-support outer-vs-observed extracted "
                    f"bound mismatch: outer {outer_bound} != observed "
                    f"{metadata.extracted_size_bound}"
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
            expected_outer_bound=outer_bound,
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

    def stage_identity(self) -> tuple[str, str, int, int | None]:
        """Bundle identity this stage materialized (restage comparison)."""
        return (
            str(self.bundle_path),
            self.expected_sha,
            self.expected_size,
            self.expected_outer_bound,
        )

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
    body: BinaryIO | None = None,
) -> tuple[int, str, str]:
    """Validate and extract one streaming tar member.

    Header/shape ownership lives in the shared archive module
    (``validate_member_header``); bounded chunked body streaming and
    hashing ownership lives in ``shared.hash_and_copy_streamed_body``.
    Staging I/O (directory ownership, permission bits, truncation
    refusal translation) remains local.

    ``body`` is the already-open member stream owned by the single-pass
    loop in :func:`extract_support_tree`: passing it avoids the fragile
    double ``extractfile`` open of the same member. When ``body`` is
    ``None`` (out-of-band callers/tests) the member is opened here; the
    staging path always supplies it, so exactly one ``extractfile`` open
    owns each payload member there.
    Returns ``(new_total, normalized_name, sha256_hex)``; directory
    entries return the input total with an empty digest.
    """
    try:
        normalized, kind = _archive.validate_member_header(member)
    except _archive.HardwareSupportArchiveError as exc:
        raise CandidateSupportError(str(exc)) from exc
    if kind == "dir":
        if body is not None:
            try:
                body.close()
            except Exception:
                pass
        return total_uncompressed, normalized, ""
    total_uncompressed += member.size
    if total_uncompressed > MAX_CANDIDATE_SUPPORT_UNCOMPRESSED_BYTES:
        raise CandidateSupportError(
            "candidate hardware-support uncompressed size is outside Greia bounds"
        )
    target = destination / normalized
    if target.is_symlink():
        raise CandidateSupportError(
            f"candidate hardware-support target is unsafe: {normalized}"
        )
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(target.parent, 0o700)
    except OSError as exc:
        raise CandidateSupportError(
            f"candidate hardware-support directory is not ownable: {normalized}"
        ) from exc
    source = body
    if source is None:
        source = tar.extractfile(member)
        if source is None:
            raise CandidateSupportError(
                f"candidate hardware-support member is unreadable: {normalized}"
            )
    try:
        try:
            with source, target.open("wb") as handle:
                digest_hex = _archive.hash_and_copy_streamed_body(
                    source, handle, member.size, label=normalized
                )
        except _archive.HardwareSupportArchiveError as exc:
            raise CandidateSupportError(str(exc)) from exc
        os.chmod(target, 0o600)
    except CandidateSupportError:
        raise
    except OSError as exc:
        raise CandidateSupportError(
            f"candidate hardware-support extraction failed: {normalized}"
        ) from exc
    return total_uncompressed, normalized, digest_hex
