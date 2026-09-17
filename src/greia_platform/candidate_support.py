"""Candidate hardware-support materializer (Repair D / T04).

Routes the exact candidate ``.greiaupdate`` ``hardware-support.tar.zst``
member — not the running system's ``/opt/greia-hardware-support`` pool —
into candidate finalization::

    candidate.greiaupdate -> hardware-support.tar.zst member
    -> bounded streaming/extraction -> temp candidate support root
    -> VerifiedHardwareSupportPool.load(candidate root) -> selection
    -> TargetHardwareSupportInstaller -> cleanup temp root

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
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


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
#: inspected manifest already enforces it, the materializer re-enforces it
#: on the exact bytes it extracts.
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


@contextmanager
def materialized_candidate_support(
    bundle_path: Path,
    manifest: object,
    staging_parent: Path,
) -> Iterator[Path | None]:
    """Materialize the candidate's hardware-support member to a temp root.

    Yields ``None`` without touching the filesystem when the manifest
    declares no hardware support (absent-support no-op). Otherwise yields
    the temp candidate support root and removes it on context exit, on
    both success and failure paths.
    """
    if not has_candidate_support(manifest):
        yield None
        return
    expected_sha = getattr(manifest, "hardware_support_sha256", None)
    expected_size = getattr(manifest, "hardware_support_size", None)
    if (
        not isinstance(expected_sha, str)
        or not isinstance(expected_size, int)
        or isinstance(expected_size, bool)
    ):
        raise CandidateSupportError("candidate hardware-support facts are invalid")
    parent = Path(staging_parent)
    try:
        parent.mkdir(parents=True, exist_ok=True)
        os.chmod(parent, 0o700)
    except OSError as exc:
        raise CandidateSupportError(
            "candidate support staging area is unavailable"
        ) from exc
    root = Path(
        tempfile.mkdtemp(prefix="candidate-support-", dir=str(parent))
    )
    try:
        os.chmod(root, 0o700)
        _extract_member(
            Path(bundle_path),
            expected_sha=expected_sha,
            expected_size=expected_size,
            destination=root,
        )
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _extract_member(
    bundle_path: Path,
    *,
    expected_sha: str,
    expected_size: int,
    destination: Path,
) -> None:
    """Stream the exact member bytes to ``destination`` with full checks."""
    if expected_size <= 0 or expected_size > MAX_CANDIDATE_SUPPORT_COMPRESSED_BYTES:
        raise CandidateSupportError(
            "candidate hardware-support size is outside Greia bounds"
        )
    try:
        bundle_stat = bundle_path.lstat()
    except OSError as exc:
        raise CandidateSupportError(
            "candidate bundle is unavailable for support extraction"
        ) from exc
    if not stat.S_ISREG(bundle_stat.st_mode):
        raise CandidateSupportError("candidate bundle is not a regular file")
    compressed_path = destination / ".hardware-support.tar.zst.tmp"
    try:
        _stage_member_bytes(
            bundle_path,
            expected_sha=expected_sha,
            expected_size=expected_size,
            staging_file=compressed_path,
        )
        _extract_tar_stream(compressed_path, destination=destination)
    finally:
        compressed_path.unlink(missing_ok=True)
    manifest_path = destination / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise CandidateSupportError(
            "candidate hardware-support tree has no manifest.json"
        )


def _stage_member_bytes(
    bundle_path: Path,
    *,
    expected_sha: str,
    expected_size: int,
    staging_file: Path,
) -> None:
    """Copy exactly the inspected member to ``staging_file``, hash-checked."""
    try:
        archive = zipfile.ZipFile(bundle_path, "r")
    except (zipfile.BadZipFile, OSError) as exc:
        raise CandidateSupportError(
            "candidate bundle is not a readable Greia artifact"
        ) from exc
    with archive:
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
        digest = hashlib.sha256()
        written = 0
        try:
            with archive.open(HARDWARE_SUPPORT_MEMBER, "r") as source, staging_file.open(
                "wb"
            ) as target:
                while True:
                    chunk = source.read(_CHUNK_BYTES)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > expected_size:
                        raise CandidateSupportError(
                            "candidate hardware-support member grew during staging"
                        )
                    digest.update(chunk)
                    target.write(chunk)
        except OSError as exc:
            raise CandidateSupportError(
                "candidate hardware-support staging write failed"
            ) from exc
        if written != expected_size:
            raise CandidateSupportError(
                "candidate hardware-support size does not match manifest"
            )
        if digest.hexdigest() != expected_sha:
            raise CandidateSupportError(
                "candidate hardware-support digest does not match manifest"
            )
    try:
        os.chmod(staging_file, 0o600)
    except OSError as exc:
        raise CandidateSupportError(
            "candidate hardware-support staging is not ownable"
        ) from exc


def _extract_tar_stream(staged: Path, *, destination: Path) -> None:
    """Decompress + extract the staged tar with shape and byte bounds."""
    try:
        import zstandard
    except ImportError as exc:
        raise CandidateSupportError(
            "zstd decompression backend is unavailable; refusing support staging"
        ) from exc
    total_uncompressed = 0
    member_count = 0
    try:
        with staged.open("rb") as raw:
            reader = zstandard.ZstdDecompressor().stream_reader(raw)
            try:
                with tarfile.open(fileobj=reader, mode="r|") as tar:
                    for member in tar:
                        member_count += 1
                        if member_count > MAX_CANDIDATE_SUPPORT_MEMBERS:
                            raise CandidateSupportError(
                                "candidate hardware-support member count is outside Greia bounds"
                            )
                        total_uncompressed = _extract_one(
                            tar,
                            member,
                            destination=destination,
                            total_uncompressed=total_uncompressed,
                        )
            finally:
                closer = getattr(reader, "close", None)
                if callable(closer):
                    try:
                        closer()
                    except Exception:
                        pass
    except CandidateSupportError:
        raise
    except Exception as exc:
        raise CandidateSupportError(
            f"candidate hardware-support archive is not a safe Greia tree: {exc}"
        ) from exc


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
