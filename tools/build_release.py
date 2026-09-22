#!/usr/bin/env python3
"""Deterministic Greia release builder (L7-RELEASE, R0/R1 source gate).

Builds the v3 release inputs without partition/boot writes:
- hardware-support.tar.zst (deterministic tar.zst from a verified pool);
- payload.ext4.zst (real relocatable ext4 slot image from a staging dir);
- read-only payload verification (ext4 superblock + required Greia paths).

The payload producer populates the composed target root into an ext4
image with the standard e2fsprogs sequence (populate -> e2fsck clean ->
shrink to practical minimum -> e2fsck clean), validates the staging tree
with the shared T03 slot validator before compression, then zstd-compresses
the shrunk image. No privileged operations, no network, no signing. The v3
bundle carries no signature, signer, or release sequence (see ADR 0036 §3
and system_updates).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from greia_installer.hardware_support import VerifiedHardwareSupportPool
from greia_installer import hardware_support_archive as _archive
from greia_platform.payload_receipt import (  # noqa: E402
    PAYLOAD_RECEIPT_SCHEMA_VERSION,
)
from greia_platform.slot_writer import SlotFinalizeError, check_slot_completeness
from greia_platform.system_updates import (
    MAX_HARDWARE_SUPPORT_BYTES,
    MAX_PAYLOAD_BYTES,
    build_persistent_state_contract_bytes,
    verify_persistent_state_contract_bytes,
)

PAYLOAD_MIN_HEADROOM = 1024 * 1024
REQUIRED_PAYLOAD_PATHS = (
    "etc/greia-os/build-info",
    "opt/greia-os/src",
    "boot/vmlinuz-generic",
    "boot/initrd-generic",
)
_ALLOWED_POOL_TOP = frozenset({"manifest.json", "Packages", "Packages.gz"})

_EXT4_SUPERBLOCK_OFFSET = 1080
_EXT4_MAGIC = b"\x53\xef"
_SLOT_LABEL = "greia-slot"
_ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"

# Per-command bound policy (T11).
#
# The production `build-payload` CLI previously applied a hard 120 s bound to
# every command including `zstd -19` over the ~1 GiB post-shrink Acer image.
# A host-native measurement of the same real content took ~811 s wall
# (~408 s user CPU), so the 120 s bound is exceeded by roughly 2-7x on the
# hardware actually available. The bound is an implementation constant: no
# governing authority fixes it or the compression level.
#
# Policy: keep `zstd -19` single-threaded output (no ratio/compat change) and
# raise the bound with real headroom instead:
# - DEFAULT_COMMAND_TIMEOUT_SECONDS (600 s) covers populate/check/shrink and
#   the smaller hardware-support compression step;
# - PAYLOAD_COMPRESSION_TIMEOUT_SECONDS (1800 s = 30 min) covers `zstd -19`
#   over the largest supported payload (MAX_PAYLOAD_BYTES = 1536 MiB):
#   linear extrapolation of the measured 1 GiB / ~811 s wall gives ~1220 s
#   at 1.5 GiB, so 1800 s leaves ~1.5x margin there and ~2.2x margin over the
#   measured Acer ~1 GiB case. Both bounds stay finite and fail-closed: an
#   expired or failing command still raises ReleaseBuildError.
DEFAULT_COMMAND_TIMEOUT_SECONDS = 600.0
PAYLOAD_COMPRESSION_TIMEOUT_SECONDS = 1800.0

# Image-content paths the read-only verifier proves with debugfs stat.
# Directory entries first, then the APT command files, then the generic
# boot pair seeded by the producer. Values mirror the documented T03
# shared-validator set plus the producer-seeded boot assets; the validator
# itself is reused directly on the staging tree at build time (see
# build_release_payload) so this list never becomes a second definition.
_IMAGE_COMPLETENESS_DIRS = (
    "usr",
    "bin",
    "etc",
    "var",
    "opt/greia-os",
    "etc/greia-os",
)
_IMAGE_COMPLETENESS_FILES = (
    "usr/bin/apt-get",
    "usr/bin/dpkg",
    "usr/bin/env",
)
_IMAGE_BOOT_FILES = (
    "boot/vmlinuz-generic",
    "boot/initrd-generic",
)
_IMAGE_IDENTITY_FILES = (
    "etc/greia-os/build-info",
    "etc/greia-os/release-identity.json",
)


class ReleaseBuildError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ReleaseCommandResult:
    """Narrow completed-command fact: raw stdout plus exit status."""

    stdout: bytes
    returncode: int


class ReleaseCommandRunner(Protocol):
    """Injectable command seam: argument arrays only, never shell strings.

    ``timeout_seconds`` is an explicit per-call bound override carried through
    the seam so tests can assert the applied bound; ``None`` means the
    runner's own default (``SubprocessReleaseRunner.timeout_seconds``).

    ``stream_to_file`` streams the command's stdout directly to ``output_path``
    without retaining the full payload in Python bytes (bounded RAM). It must
    raise :class:`ReleaseBuildError` on timeout, startup failure, or a
    non-zero exit status, and leave no partial output behind on failure
    beyond the (caller-cleaned) ``output_path`` itself.
    """

    def run(
        self, command: Sequence[str], *, timeout_seconds: float | None = None
    ) -> ReleaseCommandResult: ...  # pragma: no cover

    def stream_to_file(
        self,
        command: Sequence[str],
        output_path: Path | str,
        *,
        timeout_seconds: float | None = None,
    ) -> None: ...  # pragma: no cover


@dataclass(frozen=True, slots=True)
class SubprocessReleaseRunner:
    """Production runner: ``shell=False`` subprocess execution.

    ``stream_to_file`` connects the child stdout file descriptor directly to
    the output file, so the kernel pipes compressed bytes to disk without
    Python ever holding the full payload (bounded RAM regardless of the
    1536 MiB payload ceiling).
    """

    timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT_SECONDS

    def run(
        self, command: Sequence[str], *, timeout_seconds: float | None = None
    ) -> ReleaseCommandResult:
        effective = self.timeout_seconds if timeout_seconds is None else timeout_seconds
        try:
            completed = subprocess.run(
                list(command),
                check=False,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=effective,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ReleaseBuildError(f"release command is unavailable: {exc}") from exc
        return ReleaseCommandResult(stdout=completed.stdout, returncode=completed.returncode)

    def stream_to_file(
        self,
        command: Sequence[str],
        output_path: Path | str,
        *,
        timeout_seconds: float | None = None,
    ) -> None:
        effective = self.timeout_seconds if timeout_seconds is None else timeout_seconds
        target = Path(output_path)
        try:
            with target.open("wb") as out_handle:
                try:
                    proc = subprocess.Popen(
                        list(command),
                        stdin=subprocess.DEVNULL,
                        stdout=out_handle,
                        stderr=subprocess.PIPE,
                        shell=False,
                    )
                except OSError as exc:
                    raise ReleaseBuildError(
                        f"release command is unavailable: {exc}"
                    ) from exc
                try:
                    _, stderr = proc.communicate(timeout=effective)
                except subprocess.TimeoutExpired as exc:
                    proc.kill()
                    try:
                        proc.wait(timeout=30)
                    except (OSError, subprocess.SubprocessError):
                        pass
                    raise ReleaseBuildError(
                        f"release command is unavailable: timed out after {effective}s"
                    ) from exc
                except (OSError, subprocess.SubprocessError) as exc:
                    raise ReleaseBuildError(
                        f"release command is unavailable: {exc}"
                    ) from exc
        except ReleaseBuildError:
            raise
        except OSError as exc:
            raise ReleaseBuildError(f"payload staging write failed: {exc}") from exc
        if proc.returncode != 0:
            detail = (stderr or b"").decode("utf-8", "replace").strip()
            suffix = f": {detail}" if detail else ""
            raise ReleaseBuildError(
                f"streaming command failed ({' '.join(list(command)[:2])}){suffix}"
            )


def _runner_or_default(runner: ReleaseCommandRunner | None) -> ReleaseCommandRunner:
    return runner if runner is not None else SubprocessReleaseRunner()


def _run_checked(
    runner: ReleaseCommandRunner,
    command: Sequence[str],
    *,
    label: str,
    timeout_seconds: float | None = None,
) -> None:
    result = runner.run(command, timeout_seconds=timeout_seconds)
    if result.returncode != 0:
        detail = result.stdout.decode("utf-8", "replace").strip()
        suffix = f": {detail}" if detail else ""
        raise ReleaseBuildError(f"{label} failed ({' '.join(list(command)[:2])}){suffix}")


def _run_capture(
    runner: ReleaseCommandRunner,
    command: Sequence[str],
    *,
    label: str,
    timeout_seconds: float | None = None,
) -> bytes:
    result = runner.run(command, timeout_seconds=timeout_seconds)
    if result.returncode != 0:
        detail = result.stdout.decode("utf-8", "replace").strip()
        suffix = f": {detail}" if detail else ""
        raise ReleaseBuildError(f"{label} failed ({' '.join(list(command)[:2])}){suffix}")
    return result.stdout


# Chunk size for bounded-RAM file hashing (64 KiB: small vs the 1536 MiB
# payload ceiling, large enough to keep sha256 throughput reasonable).
_HASH_CHUNK_BYTES = 64 * 1024


def _sha256_file(path: Path) -> str:
    """Hash a file with bounded RAM (chunked reads, never ``read_bytes``)."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(_HASH_CHUNK_BYTES)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        raise ReleaseBuildError(f"payload digest read failed: {exc}") from exc
    return digest.hexdigest()


def _stream_checked(
    runner: ReleaseCommandRunner,
    command: Sequence[str],
    output_path: Path,
    *,
    label: str,
    timeout_seconds: float | None = None,
) -> None:
    """Stream ``command`` stdout to ``output_path`` through the runner seam.

    Small-command ``runner.run`` stays for bounded control output (e2fsck,
    debugfs probes); every full-payload byte transfer goes through this
    streaming seam so no ``_run_capture``/``.read()`` ever holds the whole
    payload in Python bytes.
    """
    try:
        runner.stream_to_file(command, output_path, timeout_seconds=timeout_seconds)
    except ReleaseBuildError:
        raise
    except (OSError, subprocess.SubprocessError) as exc:
        raise ReleaseBuildError(f"{label} is unavailable: {exc}") from exc


def _assert_clone_neutral_staging(staging: Path) -> None:
    """Fail closed unless the staging tree is clone-neutral (T12 gate).

    Mirrors the four composer predicates owned by
    ``build/lib/compose.sh:compose_prepare_clone_neutral_target``
    (read-only here): ``etc/machine-id`` exists as an empty regular file;
    ``var/lib/dbus/machine-id`` absent; ``var/lib/systemd/random-seed``
    absent; ``etc/ssh/ssh_host_*`` absent. This is verification only:
    never repairs the tree, only refuses with :class:`ReleaseBuildError`.
    Symlinks at the checked paths are refused rather than followed.
    """

    def _lexists(path: Path) -> bool:
        return path.is_symlink() or path.exists()

    machine_id = staging / "etc" / "machine-id"
    if machine_id.is_symlink() or not machine_id.is_file():
        raise ReleaseBuildError(
            "staging is not clone-neutral: etc/machine-id must exist as an empty regular file"
        )
    try:
        if machine_id.stat().st_size != 0:
            raise ReleaseBuildError(
                "staging is not clone-neutral: etc/machine-id must be empty"
            )
    except OSError as exc:
        raise ReleaseBuildError(
            f"staging is not clone-neutral: cannot stat etc/machine-id: {exc}"
        ) from exc
    for rel in ("var/lib/dbus/machine-id", "var/lib/systemd/random-seed"):
        if _lexists(staging / rel):
            raise ReleaseBuildError(f"staging is not clone-neutral: {rel} must be absent")
    ssh_dir = staging / "etc" / "ssh"
    if _lexists(ssh_dir) and not ssh_dir.is_dir():
        # A non-directory etc/ssh cannot hold host keys, but a symlinked or
        # regular-file etc/ssh at the identity path is itself unexpected
        # staging state: refuse rather than glob through it.
        raise ReleaseBuildError(
            "staging is not clone-neutral: etc/ssh must be a directory or absent"
        )
    try:
        host_keys = sorted(ssh_dir.glob("ssh_host_*")) if ssh_dir.is_dir() else []
    except OSError as exc:
        raise ReleaseBuildError(
            f"staging is not clone-neutral: cannot inspect etc/ssh: {exc}"
        ) from exc
    offenders = [path for path in host_keys if _lexists(path)]
    if offenders:
        raise ReleaseBuildError(
            "staging is not clone-neutral: etc/ssh/ssh_host_* must be absent "
            f"({len(offenders)} present)"
        )


def _assert_relocatable(head: bytes) -> None:
    if len(head) < 520:
        raise ReleaseBuildError("payload image is too small to be relocatable")
    if head[510:512] == b"\x55\xaa" or head[512:520] == b"EFI PART":
        raise ReleaseBuildError("payload carries a partition table; must be relocatable")


def _assert_ext4_magic(head: bytes) -> None:
    if len(head) < _EXT4_SUPERBLOCK_OFFSET + 2:
        raise ReleaseBuildError("payload is not a real ext4 image (too small)")
    if head[_EXT4_SUPERBLOCK_OFFSET : _EXT4_SUPERBLOCK_OFFSET + 2] != _EXT4_MAGIC:
        raise ReleaseBuildError("payload is not a real ext4 image (bad superblock magic)")


_EXT4_GEOMETRY_FIELDS = ("Block count", "Block size")


def _parse_dumpe2fs_field(report: str, label: str) -> int:
    """Extract one strictly-validated integer field from ``dumpe2fs -h`` text.

    The label must occur exactly once as a full ``Label: <int>`` line;
    anything else (missing, duplicated, non-numeric) fails closed so a
    localized or truncated tool report can never silently yield a wrong
    filesystem size.
    """
    matches = re.findall(rf"^{re.escape(label)}:\s+(\d+)\s*$", report, re.MULTILINE)
    if len(matches) != 1:
        raise ReleaseBuildError(
            f"ext4 geometry report has no single {label!r} field"
        )
    value = int(matches[0])
    if value <= 0:
        raise ReleaseBuildError(f"ext4 geometry field {label!r} is not positive")
    return value


def _ext4_filesystem_bytes(
    runner: ReleaseCommandRunner,
    image: Path,
    *,
    timeout_seconds: float | None = None,
) -> int:
    """Return the authoritative post-shrink ext4 filesystem extent in bytes.

    Single owner for payload geometry: ``dumpe2fs -h`` ``Block count`` times
    ``Block size`` through the injectable runner seam (argument array, no
    shell). Both fields are strictly validated; the product is bounded like
    any other payload size fact. Callers compare this against the container
    file size so a dead tail beyond the filesystem end fails closed instead
    of being recorded as payload bytes.
    """
    raw = _run_capture(
        runner,
        ["dumpe2fs", "-h", "--", str(image)],
        label="ext4 geometry",
        timeout_seconds=timeout_seconds,
    )
    try:
        report = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReleaseBuildError("ext4 geometry report is not decodable") from exc
    block_count = _parse_dumpe2fs_field(report, "Block count")
    block_size = _parse_dumpe2fs_field(report, "Block size")
    geometry_bytes = block_count * block_size
    if geometry_bytes <= 0 or geometry_bytes > MAX_PAYLOAD_BYTES:
        raise ReleaseBuildError("ext4 filesystem extent is outside Greia bounds")
    return geometry_bytes


def build_persistent_contract(output: Path) -> bytes:
    raw = build_persistent_state_contract_bytes()
    verify_persistent_state_contract_bytes(raw)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ReleaseBuildError(f"output already exists: {output}")
    output.write_bytes(raw)
    os.chmod(output, 0o644)
    return raw


# Machine-readable payload receipt (R4-G-RECEIPT).
#
# `build-payload` computes the real post-shrink image facts
# (`uncompressed_bytes`, compressed size, sha256) from the actual artifact.
# The receipt binds those facts to the release identity (profile/release)
# so `tools/greia_update.py build --payload-receipt` can derive capacity
# facts from the artifact instead of trusting operator-typed sizes. Schema
# and field names are stable for Session 03 release CLI work. The schema
# version constant lives in `greia_platform.payload_receipt` (single owner;
# R4-G3-RECEIPT-HARDENING) and is imported above.


def build_payload_receipt(
    *,
    payload_path: Path,
    uncompressed_bytes: int,
    minimum_slot_bytes: int,
    profile_id: str,
    release_id: str,
) -> dict[str, object]:
    """Build the machine-readable receipt dict for a finished payload artifact.

    All size facts except the compressed size come from the real
    ``build_release_payload`` result; the compressed size and sha256 are
    measured from the finished ``payload.ext4.zst`` file itself (chunked
    reads, bounded RAM). Refuses empty identities, non-positive sizes, or
    a minimum that does not cover the uncompressed image. Never reads the
    whole payload into RAM.
    """
    path = Path(payload_path)
    if path.is_symlink() or not path.is_file():
        raise ReleaseBuildError("payload artifact is not a regular file")
    if not isinstance(profile_id, str) or not profile_id:
        raise ReleaseBuildError("payload receipt profile_id must be non-empty text")
    if not isinstance(release_id, str) or not release_id:
        raise ReleaseBuildError("payload receipt release_id must be non-empty text")
    for label, value in (
        ("payload uncompressed_bytes", uncompressed_bytes),
        ("payload minimum_slot_bytes", minimum_slot_bytes),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ReleaseBuildError(f"payload receipt {label} must be a positive integer")
    if minimum_slot_bytes < uncompressed_bytes:
        raise ReleaseBuildError(
            "payload receipt minimum_slot_bytes must cover uncompressed_bytes"
        )
    try:
        compressed_bytes = path.stat().st_size
    except OSError as exc:
        raise ReleaseBuildError(f"payload artifact is unreadable: {exc}") from exc
    if compressed_bytes <= 0 or compressed_bytes > MAX_PAYLOAD_BYTES:
        raise ReleaseBuildError("payload artifact size is outside Greia bounds")
    digest = _sha256_file(path)
    return {
        "schema_version": PAYLOAD_RECEIPT_SCHEMA_VERSION,
        "payload_sha256": digest,
        "payload_compressed_bytes": compressed_bytes,
        "payload_uncompressed_bytes": uncompressed_bytes,
        "minimum_slot_bytes": minimum_slot_bytes,
        "profile_id": profile_id,
        "release_id": release_id,
    }


def write_payload_receipt(receipt_path: Path, receipt: dict[str, object]) -> Path:
    """Write a canonical payload receipt JSON file (refuses overwrite)."""
    target = Path(receipt_path)
    if receipt.get("schema_version") != PAYLOAD_RECEIPT_SCHEMA_VERSION:
        raise ReleaseBuildError("payload receipt schema_version is unsupported")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ReleaseBuildError(f"output already exists: {target}")
    try:
        blob = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ReleaseBuildError(
            f"payload receipt is not serializable: {exc}"
        ) from exc
    try:
        target.write_bytes(blob)
    except OSError as exc:
        raise ReleaseBuildError(f"payload receipt write failed: {exc}") from exc
    os.chmod(target, 0o644)
    return target


def _pool_layout(pool_root: Path) -> tuple[Path, list[Path]]:
    root = pool_root.resolve()
    manifest = root / "manifest.json"
    if manifest.is_symlink() or not manifest.is_file():
        raise ReleaseBuildError("hardware-support pool manifest is missing or unsafe")
    pool_dir = root / "pool"
    if pool_dir.is_symlink() or not pool_dir.is_dir():
        raise ReleaseBuildError("hardware-support pool directory is invalid")
    debs = sorted(pool_dir.glob("*.deb"))
    return root, debs


def _assert_no_hooks(root: Path) -> None:
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ReleaseBuildError(f"hardware-support pool symlink is forbidden: {path.name}")
        if path.is_file():
            if path.suffix in {".sh", ".hook"}:
                raise ReleaseBuildError(f"unexpected executable hook: {path.name}")
            try:
                mode = path.stat().st_mode
            except OSError as exc:
                raise ReleaseBuildError("unable to stat pool member") from exc
            if mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                raise ReleaseBuildError(f"unexpected executable bit: {path.name}")
    top_files = {p.name for p in root.iterdir() if p.is_file() or p.is_symlink()}
    unexpected = top_files - _ALLOWED_POOL_TOP
    if unexpected:
        raise ReleaseBuildError(f"unexpected pool top-level files: {sorted(unexpected)}")


def _manifest_with_extracted_bound(
    manifest_path: Path, *, other_member_sizes: list[int]
) -> bytes:
    """Return canonical archived ``manifest.json`` bytes with the bound field.

    Repair R4-EF-STAGE: the builder declares the authoritative
    ``extracted_bytes_bound`` derived deterministically from the exact
    archived files with the shared conservative allocation model
    (:func:`hardware_support_archive.extracted_bytes_bound_for_members`:
    ``ceil(size/4096)*4096`` per file plus per-member headers plus the
    bounded metadata allowance — never a bare byte sum). The field value
    covers the rewritten manifest itself, so the size is resolved by a
    tiny deterministic fixed-point loop (converges: one iteration unless
    the field digits cross a 4096-byte block boundary, bounded at four).
    Serialization is canonical (sorted keys, fixed indent) so identical
    pools produce identical archived bytes. The pool directory copy is
    never modified — only the archived bytes carry the declaration. The
    field name and bound semantics are stable for R4-G-RECEIPT-era
    release flows reading this builder artifact manifest.
    """
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReleaseBuildError(
            f"hardware-support pool manifest is unreadable: {exc}"
        ) from exc
    if not isinstance(document, dict):
        raise ReleaseBuildError("hardware-support pool manifest is invalid")
    try:
        manifest_size = manifest_path.stat().st_size
    except OSError as exc:
        raise ReleaseBuildError(
            f"hardware-support pool manifest is unreadable: {exc}"
        ) from exc
    blob = b""
    for _ in range(4):
        try:
            bound = _archive.extracted_bytes_bound_for_members(
                [*other_member_sizes, manifest_size],
                member_count=len(other_member_sizes) + 1,
            )
        except _archive.HardwareSupportArchiveError as exc:
            raise ReleaseBuildError(f"hardware-support staging bound refused: {exc}") from exc
        candidate = dict(document)
        candidate["extracted_bytes_bound"] = bound
        blob = (json.dumps(candidate, sort_keys=True, indent=2) + "\n").encode("utf-8")
        if len(blob) == manifest_size:
            break
        manifest_size = len(blob)
    else:
        raise ReleaseBuildError(
            "hardware-support extracted bound did not converge"
        )
    if len(blob) > _archive.MAX_ARCHIVE_MANIFEST_BYTES:
        raise ReleaseBuildError(
            "hardware-support archive manifest size is outside Greia bounds"
        )
    return blob


def build_hardware_support_set(
    pool_root: Path,
    output: Path,
    *,
    max_bytes: int = MAX_HARDWARE_SUPPORT_BYTES,
    command_timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT_SECONDS,
    runner: ReleaseCommandRunner | None = None,
) -> dict[str, object]:
    if (
        isinstance(command_timeout_seconds, bool)
        or not isinstance(command_timeout_seconds, (int, float))
        or not command_timeout_seconds > 0
    ):
        raise ReleaseBuildError("command_timeout_seconds must be a positive timeout")
    active = _runner_or_default(runner)
    pool = VerifiedHardwareSupportPool.load(pool_root)
    if pool.total_bytes > max_bytes:
        raise ReleaseBuildError("hardware-support pool exceeds release byte bound")
    root, debs = _pool_layout(pool_root)
    _assert_no_hooks(root)
    on_disk: list[tuple[str, Path]] = [
        ("Packages", root / "Packages"),
        ("Packages.gz", root / "Packages.gz"),
    ]
    on_disk.extend((f"pool/{deb.name}", deb) for deb in debs)
    for arcname, member in on_disk:
        if member.is_symlink() or not member.is_file():
            raise ReleaseBuildError(f"hardware-support member is missing: {arcname}")
    # Repair R4-EF-STAGE: the builder artifact manifest declares the
    # authoritative conservative extracted-bytes bound derived
    # deterministically from the exact archived files (shared allocation
    # model). The archived manifest.json copy carries the same field so
    # runtime staging can preflight and verify against it.
    try:
        other_sizes = [member.stat().st_size for _, member in on_disk]
    except OSError as exc:
        raise ReleaseBuildError(f"hardware-support member is unreadable: {exc}") from exc
    manifest_blob = _manifest_with_extracted_bound(
        root / "manifest.json", other_member_sizes=other_sizes
    )
    try:
        declared = json.loads(manifest_blob.decode("utf-8"))["extracted_bytes_bound"]
    except (ValueError, KeyError) as exc:
        raise ReleaseBuildError(
            "hardware-support staging bound declaration is invalid"
        ) from exc
    if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
        raise ReleaseBuildError(
            "hardware-support staging bound declaration is invalid"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ReleaseBuildError(f"output already exists: {output}")
    zstd = shutil.which("zstd")
    if zstd is None:
        raise ReleaseBuildError("zstd is required to build hardware-support.tar.zst")
    with tempfile.NamedTemporaryFile(
        prefix=".hwmanifest.", suffix=".json", dir=output.parent, delete=False
    ) as handle:
        manifest_tmp = Path(handle.name)
    try:
        manifest_tmp.write_bytes(manifest_blob)
        os.chmod(manifest_tmp, 0o644)
        members: list[tuple[str, Path]] = [("manifest.json", manifest_tmp)]
        members.extend(on_disk)
        with tempfile.NamedTemporaryFile(prefix=".hwset.", suffix=".tar", delete=False) as handle:
            tar_tmp = Path(handle.name)
        try:
            with tar_tmp.open("wb") as raw:
                with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
                    for arcname, member in sorted(members, key=lambda item: item[0]):
                        info = tar.gettarinfo(str(member), arcname=arcname)
                        info.uid = 0
                        info.gid = 0
                        info.uname = ""
                        info.gname = ""
                        info.mtime = 0
                        if info.isdir():
                            info.mode = 0o755
                        elif info.isfile():
                            info.mode = 0o644
                        else:
                            raise ReleaseBuildError(f"unsupported pool member type: {arcname}")
                        if info.issym() or info.islnk():
                            raise ReleaseBuildError(f"symlink archive member forbidden: {arcname}")
                        with member.open("rb") as src:
                            tar.addfile(info, src)
            # Bounded-RAM compression: the compressor streams stdout
            # straight to the temp output file through the runner seam, so
            # Python never holds the whole compressed archive (up to
            # 512 MiB) the way a captured ``run`` stdout would.
            with tempfile.NamedTemporaryFile(
                prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False
            ) as handle:
                tmp_out = Path(handle.name)
            try:
                _stream_checked(
                    active,
                    [zstd, "-19", "-c", "--rm", str(tar_tmp)],
                    tmp_out,
                    label="hardware-support compression",
                    timeout_seconds=command_timeout_seconds,
                )
                try:
                    with tmp_out.open("rb") as probe:
                        emitted_magic = probe.read(len(_ZSTD_MAGIC))
                except OSError as exc:
                    raise ReleaseBuildError(
                        f"compressed support is unreadable: {exc}"
                    ) from exc
                if emitted_magic != _ZSTD_MAGIC:
                    raise ReleaseBuildError(
                        "hardware-support compressor did not emit zstd bytes"
                    )
                if tmp_out.stat().st_size > max_bytes:
                    raise ReleaseBuildError("hardware-support.tar.zst exceeds release byte bound")
                os.chmod(tmp_out, 0o644)
                tmp_out.replace(output)
            finally:
                tmp_out.unlink(missing_ok=True)
        finally:
            tar_tmp.unlink(missing_ok=True)
    finally:
        manifest_tmp.unlink(missing_ok=True)
    digest = _sha256_file(output)
    return {
        "output": str(output),
        "size": output.stat().st_size,
        "sha256": digest,
        "pool_suite": pool.suite,
        "pool_architecture": pool.architecture,
        "pool_total_bytes": pool.total_bytes,
        "extracted_bytes_bound": declared,
    }


def build_release_payload(
    *,
    staging_dir: Path,
    kernel_path: Path,
    initramfs_path: Path,
    output: Path,
    profile_id: str,
    release_id: str,
    filesystem_bytes: int,
    minimum_slot_bytes: int | None,
    runner: ReleaseCommandRunner | None = None,
    command_timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT_SECONDS,
    compression_timeout_seconds: float = PAYLOAD_COMPRESSION_TIMEOUT_SECONDS,
) -> dict[str, object]:
    """Build a real relocatable ext4 slot image from the composed target root.

    Standard e2fsprogs sequence through the injectable runner seam:
    ``mkfs.ext4 -d <staging> -O ^flex_bg`` (populate without flex_bg so the
    image stays shrink-to-minimum capable) -> ``e2fsck -f -y`` (clean) ->
    ``resize2fs -M`` (shrink to practical minimum) -> ``e2fsck -f -y``
    (clean) -> ``dumpe2fs -h`` geometry authority (``Block count`` times
    ``Block size`` must equal the container file size, so a dead tail fails
    closed instead of being recorded) -> ``zstd -19`` (compress, streamed
    stdout-to-file with bounded RAM). The staging tree is validated with
    the shared T03 slot validator before any image byte is emitted, so a
    skeleton root is refused before compression. A fail-closed
    clone-neutrality gate re-verifies the four composer predicates on the
    seeded staging tree before any image byte is emitted, so a hand-built
    dirty tree is refused before compression. Returns the authoritative
    post-shrink filesystem extent (geometry, verified equal to the container
    file size) as ``uncompressed_bytes``.

    When ``minimum_slot_bytes`` is omitted the producer derives it after the
    shrink from the real ext4 byte size plus ``PAYLOAD_MIN_HEADROOM``. The
    explicit value remains a low-level override and must cover that derived
    minimum; callers no longer need to guess a pre-shrink number.

    Command-bound policy: populate/check/shrink run under
    ``command_timeout_seconds`` (default 600 s); the ``zstd -19`` step over
    the ~1 GiB post-shrink image runs under ``compression_timeout_seconds``
    (default 1800 s, ~2.2x margin over the measured ~811 s wall for the real
    Acer content and ~1.5x over the linear extrapolation to the 1536 MiB
    maximum). Both bounds stay finite: expiry raises ReleaseBuildError.
    """
    active = _runner_or_default(runner)
    staging = Path(staging_dir).resolve()
    kernel = Path(kernel_path)
    initramfs = Path(initramfs_path)
    for path, label in ((kernel, "kernel"), (initramfs, "initramfs")):
        if path.is_symlink() or not path.is_file():
            raise ReleaseBuildError(f"generic {label} input is not a regular file")
    if isinstance(filesystem_bytes, bool) or filesystem_bytes <= 0 or filesystem_bytes > MAX_PAYLOAD_BYTES:
        raise ReleaseBuildError("filesystem_bytes is outside Greia bounds")
    if minimum_slot_bytes is not None:
        if (
            isinstance(minimum_slot_bytes, bool)
            or not isinstance(minimum_slot_bytes, int)
            or minimum_slot_bytes <= 0
            or minimum_slot_bytes > 2 * 1024 * 1024 * 1024
        ):
            raise ReleaseBuildError(
                "minimum_slot_bytes must be a positive bounded integer or omitted"
            )
    for label, bound in (
        ("command_timeout_seconds", command_timeout_seconds),
        ("compression_timeout_seconds", compression_timeout_seconds),
    ):
        if (
            isinstance(bound, bool)
            or not isinstance(bound, (int, float))
            or not bound > 0
        ):
            raise ReleaseBuildError(f"{label} must be a positive timeout")
    if not staging.is_dir():
        raise ReleaseBuildError("payload staging dir is missing")
    # Seed generic kernel/initramfs + release identity deterministically.
    boot_dir = staging / "boot"
    etc_dir = staging / "etc" / "greia-os"
    boot_dir.mkdir(parents=True, exist_ok=True)
    etc_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(kernel, boot_dir / "vmlinuz-generic")
    shutil.copyfile(initramfs, boot_dir / "initrd-generic")
    identity = {
        "profile": profile_id,
        "release_id": release_id,
    }
    (etc_dir / "release-identity.json").write_text(
        json.dumps(identity, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    # Fail-closed clone-neutrality gate (T12): the composer owns producing
    # neutrality; this seam only re-verifies the four predicates on the exact
    # seeded tree that populate would consume. The seeding writes above
    # (boot/vmlinuz-generic, boot/initrd-generic,
    # etc/greia-os/release-identity.json) touch disjoint paths, so they can
    # neither satisfy nor bypass the check. Runs before any runner call, so
    # refusal emits no image byte and leaves no temp image behind.
    _assert_clone_neutral_staging(staging)
    for required in REQUIRED_PAYLOAD_PATHS:
        candidate = staging / required
        if required.endswith("src"):
            if candidate.is_symlink() or not candidate.is_dir():
                raise ReleaseBuildError(f"staging is missing required path: {required}")
        elif candidate.is_symlink() or not candidate.is_file():
            raise ReleaseBuildError(f"staging is missing required path: {required}")
    try:
        check_slot_completeness(staging)
    except SlotFinalizeError as exc:
        raise ReleaseBuildError(f"staging lacks required Greia userspace: {exc}") from exc
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        raise ReleaseBuildError(f"output already exists: {out_path}")
    fd, tmp_name = tempfile.mkstemp(
        prefix=".slot.", suffix=".ext4", dir=str(out_path.parent)
    )
    os.close(fd)
    tmp_img = Path(tmp_name)
    try:
        kib = max(1, filesystem_bytes // 1024)
        # flex_bg packs all block groups of a slot-sized image into one flex
        # group, after which e2fsprogs resize2fs -M/-P reports the full size
        # as the minimum and the shrink step below becomes a silent no-op
        # (measured: 12-group image with ~30% free refuses any shrink, while
        # the identical image without flex_bg shrinks normally). Payload
        # images must stay shrink-to-minimum capable, so the feature stays
        # off here; read-mostly slot images do not need flex packing.
        _run_checked(
            active,
            [
                "mkfs.ext4",
                "-d",
                str(staging),
                "-O",
                "^flex_bg",
                "-L",
                _SLOT_LABEL,
                str(tmp_img),
                f"{kib}K",
            ],
            label="ext4 population",
            timeout_seconds=command_timeout_seconds,
        )
        _run_checked(
            active,
            ["e2fsck", "-f", "-y", "--", str(tmp_img)],
            label="ext4 check",
            timeout_seconds=command_timeout_seconds,
        )
        _run_checked(
            active,
            ["resize2fs", "-M", "--", str(tmp_img)],
            label="ext4 shrink",
            timeout_seconds=command_timeout_seconds,
        )
        _run_checked(
            active,
            ["e2fsck", "-f", "-y", "--", str(tmp_img)],
            label="ext4 re-check",
            timeout_seconds=command_timeout_seconds,
        )
        geometry_bytes = _ext4_filesystem_bytes(
            active, tmp_img, timeout_seconds=command_timeout_seconds
        )
        try:
            container_bytes = tmp_img.stat().st_size
        except OSError as exc:
            raise ReleaseBuildError("shrunk slot image is unavailable") from exc
        if container_bytes != geometry_bytes:
            raise ReleaseBuildError(
                "slot image container does not match ext4 filesystem extent"
            )
        shrunk_bytes = geometry_bytes
        if shrunk_bytes <= 0 or shrunk_bytes > MAX_PAYLOAD_BYTES:
            raise ReleaseBuildError("shrunk slot image is outside Greia bounds")
        if shrunk_bytes > filesystem_bytes:
            raise ReleaseBuildError("shrunk slot image exceeds filesystem_bytes")
        try:
            with tmp_img.open("rb") as handle:
                head = handle.read(2048)
        except OSError as exc:
            raise ReleaseBuildError("slot image is unreadable") from exc
        _assert_ext4_magic(head)
        _assert_relocatable(head)
        derived_minimum = shrunk_bytes + PAYLOAD_MIN_HEADROOM
        if minimum_slot_bytes is None:
            minimum_slot_bytes = derived_minimum
        elif minimum_slot_bytes < derived_minimum:
            raise ReleaseBuildError(
                "minimum_slot_bytes must cover the shrunk image plus finalization headroom"
            )
        # Stream `zstd -19` stdout directly to the temp output file: the
        # child fd writes to disk while Python holds no payload bytes
        # (bounded RAM even at the 1536 MiB payload ceiling). Single-threaded
        # `-19` output policy unchanged; the finite compression bound still
        # applies through the streaming seam.
        with tempfile.NamedTemporaryFile(
            prefix=f".{out_path.name}.", suffix=".tmp", dir=str(out_path.parent), delete=False
        ) as handle:
            tmp_out = Path(handle.name)
        try:
            _stream_checked(
                active,
                ["zstd", "-19", "-c", "--", str(tmp_img)],
                tmp_out,
                label="payload compression",
                timeout_seconds=compression_timeout_seconds,
            )
            try:
                compressed_size = tmp_out.stat().st_size
            except OSError as exc:
                raise ReleaseBuildError("compressed payload is unavailable") from exc
            if compressed_size <= 0:
                raise ReleaseBuildError("payload compressor emitted no bytes")
            try:
                with tmp_out.open("rb") as handle:
                    compressed_magic = handle.read(len(_ZSTD_MAGIC))
            except OSError as exc:
                raise ReleaseBuildError("compressed payload is unreadable") from exc
            if compressed_magic != _ZSTD_MAGIC:
                raise ReleaseBuildError("payload compressor did not emit zstd bytes")
            os.chmod(tmp_out, 0o644)
            tmp_out.replace(out_path)
        finally:
            tmp_out.unlink(missing_ok=True)
    finally:
        tmp_img.unlink(missing_ok=True)
    digest = _sha256_file(out_path)
    return {
        "output": str(out_path),
        "filesystem_bytes": filesystem_bytes,
        "uncompressed_bytes": shrunk_bytes,
        "minimum_slot_bytes": minimum_slot_bytes,
        "sha256": digest,
        "size": out_path.stat().st_size,
    }


def verify_release_payload(
    payload: Path, *, runner: ReleaseCommandRunner | None = None
) -> dict[str, object]:
    """Verify a real ext4 slot payload plus Greia completeness (read-only).

    Stream-decompresses ``payload.ext4.zst`` directly into a temp file (no
    mount, no full-payload bytes in Python RAM), proves the ext4 superblock
    magic and relocatability (no MBR/GPT signature) from a bounded 2048-byte
    head read, runs a read-only ``e2fsck -n`` through the seam, then proves
    every required Greia path with read-only ``debugfs -R "stat <path>"``
    probes. Any tar-body payload is rejected as not-a-real-ext4-image.
    """
    active = _runner_or_default(runner)
    path = Path(payload)
    if path.is_symlink() or not path.is_file():
        raise ReleaseBuildError("payload is not a regular file")
    with path.open("rb") as handle:
        magic = handle.read(4)
    if magic != _ZSTD_MAGIC:
        raise ReleaseBuildError("payload.ext4.zst must be zstd-compressed bytes")
    fd, tmp_name = tempfile.mkstemp(prefix=".verify-slot.", suffix=".ext4")
    os.close(fd)
    tmp_img = Path(tmp_name)
    try:
        _stream_checked(
            active,
            ["zstd", "-d", "-c", "--", str(path)],
            tmp_img,
            label="payload decompression",
        )
        try:
            decompressed_size = tmp_img.stat().st_size
        except OSError as exc:
            raise ReleaseBuildError("payload staging write failed") from exc
        if decompressed_size <= 0 or decompressed_size > MAX_PAYLOAD_BYTES:
            raise ReleaseBuildError("decompressed payload is outside Greia bounds")
        try:
            with tmp_img.open("rb") as handle:
                head = handle.read(2048)
        except OSError as exc:
            raise ReleaseBuildError("payload staging write failed") from exc
        _assert_ext4_magic(head)
        _assert_relocatable(head)
        _run_checked(active, ["e2fsck", "-n", "-f", "--", str(tmp_img)], label="payload read-only check")
        required = (
            *_IMAGE_COMPLETENESS_DIRS,
            *_IMAGE_COMPLETENESS_FILES,
            *_IMAGE_BOOT_FILES,
            *_IMAGE_IDENTITY_FILES,
        )
        for rel in required:
            result = active.run(["debugfs", "-R", f"stat {rel}", str(tmp_img)])
            stdout_text = result.stdout.decode("utf-8", "replace")
            lowered = stdout_text.lower()
            if result.returncode != 0 or "not found" in lowered or "no such file" in lowered:
                raise ReleaseBuildError(f"payload is missing required Greia path: {rel}")
    finally:
        tmp_img.unlink(missing_ok=True)
    return {
        "payload": str(path),
        "size": path.stat().st_size,
        "uncompressed_bytes": decompressed_size,
        "checked_paths": len(required),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    contract = sub.add_parser("build-persistent-contract")
    contract.add_argument("--output", type=Path, required=True)
    hwset = sub.add_parser("build-hardware-support")
    hwset.add_argument("--pool-root", type=Path, required=True)
    hwset.add_argument("--output", type=Path, required=True)
    hwset.add_argument("--max-bytes", type=int, default=MAX_HARDWARE_SUPPORT_BYTES)
    hwset.add_argument(
        "--command-timeout-seconds",
        type=float,
        default=DEFAULT_COMMAND_TIMEOUT_SECONDS,
        help="Per-command bound in seconds (fail-closed).",
    )
    payload = sub.add_parser("build-payload")
    payload.add_argument("--staging-dir", type=Path, required=True)
    payload.add_argument("--kernel", type=Path, required=True)
    payload.add_argument("--initramfs", type=Path, required=True)
    payload.add_argument("--output", type=Path, required=True)
    payload.add_argument("--profile-id", required=True)
    payload.add_argument("--release-id", required=True)
    payload.add_argument("--filesystem-bytes", type=int, required=True)
    payload.add_argument(
        "--minimum-slot-bytes",
        type=int,
        default=None,
        help=(
            "Optional low-level override. When omitted, the producer derives "
            "the minimum from the real shrunk ext4 size plus PAYLOAD_MIN_HEADROOM."
        ),
    )
    payload.add_argument(
        "--receipt-output",
        type=Path,
        default=None,
        help=(
            "Write the machine-readable payload receipt JSON "
            "(schema_version, payload sha256/sizes, minimum_slot_bytes, "
            "profile_id, release_id) measured from the finished artifact."
        ),
    )
    payload.add_argument(
        "--command-timeout-seconds",
        type=float,
        default=DEFAULT_COMMAND_TIMEOUT_SECONDS,
        help="Bound for populate/check/shrink commands in seconds (fail-closed).",
    )
    payload.add_argument(
        "--compression-timeout-seconds",
        type=float,
        default=PAYLOAD_COMPRESSION_TIMEOUT_SECONDS,
        help="Bound for the zstd -19 payload compression step in seconds (fail-closed).",
    )
    verify = sub.add_parser("verify-payload")
    verify.add_argument("--payload", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "build-persistent-contract":
            build_persistent_contract(args.output)
            print(json.dumps({"output": str(args.output)}, indent=2))
        elif args.command == "build-hardware-support":
            print(json.dumps(build_hardware_support_set(args.pool_root, args.output, max_bytes=args.max_bytes, command_timeout_seconds=args.command_timeout_seconds), indent=2))
        elif args.command == "build-payload":
            result = build_release_payload(
                staging_dir=args.staging_dir,
                kernel_path=args.kernel,
                initramfs_path=args.initramfs,
                output=args.output,
                profile_id=args.profile_id,
                release_id=args.release_id,
                filesystem_bytes=args.filesystem_bytes,
                minimum_slot_bytes=args.minimum_slot_bytes,
                command_timeout_seconds=args.command_timeout_seconds,
                compression_timeout_seconds=args.compression_timeout_seconds,
            )
            if args.receipt_output is not None:
                receipt = build_payload_receipt(
                    payload_path=Path(str(result["output"])),
                    uncompressed_bytes=int(result["uncompressed_bytes"]),
                    minimum_slot_bytes=int(result["minimum_slot_bytes"]),
                    profile_id=args.profile_id,
                    release_id=args.release_id,
                )
                write_payload_receipt(args.receipt_output, receipt)
                result = {
                    **result,
                    "receipt_output": str(args.receipt_output),
                    "receipt": receipt,
                }
            print(json.dumps(result, indent=2))
        elif args.command == "verify-payload":
            print(json.dumps(verify_release_payload(args.payload), indent=2))
        else:  # pragma: no cover
            raise ReleaseBuildError(f"unknown command: {args.command}")
    except ReleaseBuildError as exc:
        print(f"build-release: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
