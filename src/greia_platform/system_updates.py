from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import stat
import struct
import tempfile
import zipfile
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Callable, NoReturn, Protocol

from greia_installer import hardware_support_archive as _archive
from .boot_transaction import BOOT_JOURNAL_DIR_DEFAULT, BOOT_JOURNAL_DIR_ENV


BUNDLE_SUFFIX = ".greiaupdate"
BUNDLE_MEDIA_TYPE = "application/vnd.greia.system-update+zip"
MANIFEST_NAME = "manifest.json"
PAYLOAD_NAME = "payload.ext4.zst"
HARDWARE_SUPPORT_NAME = "hardware-support.tar.zst"
BUNDLE_MEMBERS_V3 = (MANIFEST_NAME, PAYLOAD_NAME)
BUNDLE_MEMBERS_V3_WITH_HW = (MANIFEST_NAME, PAYLOAD_NAME, HARDWARE_SUPPORT_NAME)
# ADR 0036 §3: v3 is the only accepted container. Historical v1/v2 signed
# layouts are rejected fail-closed with an explicit v3 rebuild/migration
# message (see _migration_error()); their member constants are intentionally
# absent so new code cannot rebuild them.
SCHEMA_VERSION = 3
V1_SCHEMA_VERSION = 1
V2_SCHEMA_VERSION = 2
MAX_MANIFEST_BYTES = 64 * 1024
# Owner decision 2026-10-25: the Acer A/B system slot is 1664 MiB
# (1500 MiB installed-core gate plus hardware-support/initramfs headroom).
# The payload builder uses the destination slot as its populate ceiling,
# so the payload bound must cover that slot even though the finalized
# payload itself stays below the installed-core gate.
MAX_PAYLOAD_BYTES = 1664 * 1024 * 1024
#: Single production compressed member bound. Canonical owner is the shared
#: archive module (mirrors ``candidate_support`` precedent); kept here as a
#: literal alias so a future second literal fails sync tests.
MAX_HARDWARE_SUPPORT_BYTES = _archive.MAX_ARCHIVE_COMPRESSED_BYTES
MAX_BUNDLE_BYTES = 2 * 1024 * 1024 * 1024
#: ADR 0036 §7 / A10: compressed candidate plus a 256 MiB operating reserve.
MIN_INBOX_FREE_BYTES = 256 * 1024 * 1024
#: A10 fixed inbox names: exactly one Greia-owned candidate, published by
#: atomic rename from the same-directory temporary name.
INBOX_CANDIDATE_NAME = "candidate.greiaupdate"
INBOX_UPLOADING_NAME = "candidate.uploading"
_MAX_RELEASE_ID = 96
_MAX_VERSION = 64
_MAX_NOTES = 4096
_MAX_BOARD = 64
_MAX_PERSIST_SCHEMA = 2_147_483_647
_ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
_DETERMINISTIC_ZIP_DATE = (1980, 1, 1, 0, 0, 0)
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_BLOCK_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
# BLKGETSIZE64 is _IOR(0x12, 114, size_t); the encoded length follows the
# userspace pointer width, so i386 (4-byte size_t) and x86_64 (8-byte) differ.
_BLKGETSIZE64_IOCTL_32BIT = 0x80041272
_BLKGETSIZE64_IOCTL_64BIT = 0x80081272
_SYSFS_BLOCK_ROOT = Path("/sys/class/block")
_MIN_BLOCK_NODE_BYTES = 512
_MAX_BLOCK_NODE_BYTES = 1 << 48
#: Installed PERSIST contract schema (not a bundle member in v3; the bundle
#: carries only the three readable/writable schema integers). Kept so the
#: installed-state helpers below stay importable for persistent_layout.
PERSISTENT_CONTRACT_SCHEMA_VERSION = 1
MAX_PERSISTENT_CONTRACT_BYTES = 64 * 1024
# L7-PERSIST audit owner: greia_platform.persistent_layout.PERSISTENT_NAMESPACE_ORDER.
# This tuple must stay identical (names and order); the sync test enforces it.
_PERSISTENT_NAMESPACES = (
    "layout-authority",
    "child-profiles",
    "activity-saves",
    "progression-rewards",
    "device-settings",
    "parent-credentials",
    "activity-activation",
    "update-acceptance-state",
    "network-state",
    "machine-identity",
    "developer-state",
    "hardware-receipts",
    "bounded-logs",
)
_PERSISTENT_MIGRATION_POLICY = "backward-compatible-or-transactional"


class SystemUpdateError(RuntimeError):
    pass


class UpdateBundleError(SystemUpdateError):
    pass


class UpdateCompatibilityError(SystemUpdateError):
    pass


class UpdateBackendUnavailable(SystemUpdateError):
    pass


class UpdateState(StrEnum):
    UNAVAILABLE = "unavailable"
    IDLE = "idle"
    RECEIVED = "received"
    VERIFIED = "verified"
    STAGING = "staging"
    READY_TO_RESTART = "ready_to_restart"
    PENDING_BOOT_CONFIRMATION = "pending_boot_confirmation"
    UPDATED = "updated"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class UpdateManifest:
    """ADR 0036 §3 v3 manifest: practical facts only, no provenance.

    ``release_id`` is a bounded non-security bookkeeping identity (journal /
    layout); there is no signer, key id, or anti-rollback sequence.
    ``board`` is a bounded board id or None. ``hardware_support_*`` are None
    when the optional member is absent. PERSIST compatibility is carried as
    three schema integers; there is no separate contract member.
    """

    schema_version: int
    release_id: str
    version: str
    platform_family: str
    architecture: str
    profile: str
    board: str | None
    payload_sha256: str
    payload_size: int
    payload_uncompressed_bytes: int
    payload_minimum_slot_bytes: int
    hardware_support_sha256: str | None
    hardware_support_size: int | None
    persist_read_schema_min: int
    persist_read_schema_max: int
    persist_write_schema: int
    release_notes: str = ""
    #: Conservative extracted-bytes bound for the support tree (R4-G2-SUPPORT-BOUND).
    #: Mirrors the stable inner ``extracted_bytes_bound`` field and the shared
    #: ``extracted_bytes_bound_for_members`` model. ``None`` when the bundle
    #: predates the field (old bundles fall back to mid-stream preflight).
    hardware_support_extracted_bytes_bound: int | None = None

    def __post_init__(self) -> None:
        if self.schema_version in (V1_SCHEMA_VERSION, V2_SCHEMA_VERSION):
            raise UpdateBundleError(_migration_error())
        if self.schema_version != SCHEMA_VERSION:
            raise UpdateBundleError(
                f"unsupported system-update schema {self.schema_version}"
            )
        _validate_identifier(self.release_id, "release_id", _MAX_RELEASE_ID)
        _validate_text(self.version, "version", _MAX_VERSION)
        _validate_identifier(self.platform_family, "platform_family", 64)
        _validate_identifier(self.architecture, "architecture", 32)
        _validate_identifier(self.profile, "profile", 96)
        _validate_board(self.board)
        if not re.fullmatch(r"[0-9a-f]{64}", self.payload_sha256):
            raise UpdateBundleError("payload_sha256 must be lower-case SHA-256 hex")
        if self.payload_size <= 0 or self.payload_size > MAX_PAYLOAD_BYTES:
            raise UpdateBundleError("payload_size is outside Greia bounds")
        if (
            self.payload_uncompressed_bytes <= 0
            or self.payload_uncompressed_bytes > MAX_PAYLOAD_BYTES
        ):
            raise UpdateBundleError("payload uncompressed_bytes is outside Greia bounds")
        if (
            self.payload_minimum_slot_bytes < self.payload_uncompressed_bytes
            or self.payload_minimum_slot_bytes <= 0
            or self.payload_minimum_slot_bytes > MAX_BUNDLE_BYTES
        ):
            raise UpdateBundleError(
                "payload minimum_slot_bytes must cover the uncompressed image"
            )
        hw_sha = self.hardware_support_sha256
        hw_size = self.hardware_support_size
        hw_bound = self.hardware_support_extracted_bytes_bound
        if (hw_sha is None) != (hw_size is None):
            raise UpdateBundleError(
                "hardware-support sha256/size must be present together or absent together"
            )
        if hw_sha is None and hw_bound is not None:
            raise UpdateBundleError(
                "hardware-support extracted bound requires the member"
            )
        if hw_sha is not None and hw_size is not None:
            if not re.fullmatch(r"[0-9a-f]{64}", hw_sha):
                raise UpdateBundleError(
                    "hardware-support sha256 must be lower-case SHA-256 hex"
                )
            if hw_size <= 0 or hw_size > MAX_HARDWARE_SUPPORT_BYTES:
                raise UpdateBundleError("hardware-support size is outside Greia bounds")
            if hw_bound is not None:
                if (
                    isinstance(hw_bound, bool)
                    or not isinstance(hw_bound, int)
                    or hw_bound < 0
                    or hw_bound > _archive.MAX_ARCHIVE_UNCOMPRESSED_BYTES
                ):
                    raise UpdateBundleError(
                        "hardware-support extracted bound is outside Greia bounds"
                    )
        _validate_persist_schema(
            self.persist_read_schema_min,
            self.persist_read_schema_max,
            self.persist_write_schema,
        )
        if not isinstance(self.release_notes, str) or len(self.release_notes) > _MAX_NOTES:
            raise UpdateBundleError("release_notes exceeds Greia bound")

    def as_json_dict(self) -> dict[str, object]:
        if self.hardware_support_sha256 is None or self.hardware_support_size is None:
            hardware: dict[str, object] | None = None
        else:
            hardware = {
                "name": HARDWARE_SUPPORT_NAME,
                "sha256": self.hardware_support_sha256,
                "size": self.hardware_support_size,
            }
            if self.hardware_support_extracted_bytes_bound is not None:
                hardware["extracted_bytes_bound"] = (
                    self.hardware_support_extracted_bytes_bound
                )
        return {
            "schema_version": self.schema_version,
            "release_id": self.release_id,
            "version": self.version,
            "platform_family": self.platform_family,
            "architecture": self.architecture,
            "profile": self.profile,
            "board": self.board,
            "payload": {
                "name": PAYLOAD_NAME,
                "sha256": self.payload_sha256,
                "size": self.payload_size,
                "uncompressed_bytes": self.payload_uncompressed_bytes,
                "minimum_slot_bytes": self.payload_minimum_slot_bytes,
            },
            "hardware_support": hardware,
            "persist_read_schema_min": self.persist_read_schema_min,
            "persist_read_schema_max": self.persist_read_schema_max,
            "persist_write_schema": self.persist_write_schema,
            "release_notes": self.release_notes,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.as_json_dict())

    @classmethod
    def from_json_dict(cls, raw: object) -> "UpdateManifest":
        if not isinstance(raw, dict):
            raise UpdateBundleError("manifest must be a JSON object")
        expected = {
            "schema_version",
            "release_id",
            "version",
            "platform_family",
            "architecture",
            "profile",
            "board",
            "payload",
            "hardware_support",
            "persist_read_schema_min",
            "persist_read_schema_max",
            "persist_write_schema",
            "release_notes",
        }
        if set(raw) != expected:
            raise UpdateBundleError("manifest has unknown or missing top-level fields")
        schema_version = raw.get("schema_version")
        if schema_version in (V1_SCHEMA_VERSION, V2_SCHEMA_VERSION):
            raise UpdateBundleError(_migration_error())
        payload = raw.get("payload")
        if not isinstance(payload, dict) or set(payload) != {
            "name",
            "sha256",
            "size",
            "uncompressed_bytes",
            "minimum_slot_bytes",
        }:
            raise UpdateBundleError("manifest payload object is invalid")
        if payload.get("name") != PAYLOAD_NAME:
            raise UpdateBundleError("unsupported system-update payload contract")
        hardware = raw.get("hardware_support")
        if hardware is not None:
            if not isinstance(hardware, dict) or set(hardware) not in (
                {"name", "sha256", "size"},
                {"name", "sha256", "size", "extracted_bytes_bound"},
            ):
                raise UpdateBundleError("manifest hardware-support object is invalid")
            if hardware.get("name") != HARDWARE_SUPPORT_NAME:
                raise UpdateBundleError("hardware-support member name is invalid")
        board = raw.get("board")
        if board is not None and not isinstance(board, str):
            raise UpdateBundleError("board must be text or null")
        values: dict[str, object] = {
            "schema_version": schema_version,
            "release_id": raw.get("release_id"),
            "version": raw.get("version"),
            "platform_family": raw.get("platform_family"),
            "architecture": raw.get("architecture"),
            "profile": raw.get("profile"),
            "board": board,
            "payload_sha256": payload.get("sha256"),
            "payload_size": payload.get("size"),
            "payload_uncompressed_bytes": payload.get("uncompressed_bytes"),
            "payload_minimum_slot_bytes": payload.get("minimum_slot_bytes"),
            "hardware_support_sha256": hardware.get("sha256") if isinstance(hardware, dict) else None,
            "hardware_support_size": hardware.get("size") if isinstance(hardware, dict) else None,
            "hardware_support_extracted_bytes_bound": hardware.get("extracted_bytes_bound")
            if isinstance(hardware, dict)
            else None,
            "persist_read_schema_min": raw.get("persist_read_schema_min"),
            "persist_read_schema_max": raw.get("persist_read_schema_max"),
            "persist_write_schema": raw.get("persist_write_schema"),
            "release_notes": raw.get("release_notes"),
        }
        if isinstance(values["schema_version"], bool) or not isinstance(
            values["schema_version"], int
        ):
            raise UpdateBundleError("schema_version must be an integer")
        for int_key in (
            "payload_size",
            "payload_uncompressed_bytes",
            "payload_minimum_slot_bytes",
            "persist_read_schema_min",
            "persist_read_schema_max",
            "persist_write_schema",
        ):
            if isinstance(values[int_key], bool) or not isinstance(values[int_key], int):
                raise UpdateBundleError(f"{int_key} must be an integer")
        hw_size = values["hardware_support_size"]
        if hw_size is not None and (
            isinstance(hw_size, bool) or not isinstance(hw_size, int)
        ):
            raise UpdateBundleError("hardware_support_size must be an integer or null")
        for key in (
            "release_id",
            "version",
            "platform_family",
            "architecture",
            "profile",
            "payload_sha256",
            "release_notes",
        ):
            if not isinstance(values[key], str):
                raise UpdateBundleError(f"{key} must be text")
        hw_sha = values["hardware_support_sha256"]
        if hw_sha is not None and not isinstance(hw_sha, str):
            raise UpdateBundleError("hardware_support_sha256 must be text or null")
        hw_bound = values["hardware_support_extracted_bytes_bound"]
        if hw_bound is not None and (
            isinstance(hw_bound, bool) or not isinstance(hw_bound, int)
        ):
            raise UpdateBundleError(
                "hardware_support_extracted_bytes_bound must be an integer or absent"
            )
        return cls(**values)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class InspectedUpdateBundle:
    path: Path
    manifest: UpdateManifest

    def as_json_dict(self) -> dict[str, object]:
        payload = self.manifest.as_json_dict()
        payload["bundle_sha256"] = sha256_file(self.path)
        payload["bundle_size"] = self.path.stat().st_size
        return payload


@dataclass(frozen=True, slots=True)
class SystemIdentity:
    version: str = "unknown"
    platform_family: str = "unknown"
    architecture: str = "unknown"
    profile: str = "unknown"
    board: str | None = None

    @property
    def compatibility_known(self) -> bool:
        return all(
            value and value != "unknown"
            for value in (self.platform_family, self.architecture, self.profile)
        )

    def assert_compatible(self, manifest: UpdateManifest) -> None:
        if not self.compatibility_known:
            raise UpdateCompatibilityError("installed system identity is incomplete")
        if manifest.platform_family != self.platform_family:
            raise UpdateCompatibilityError("update platform family does not match this Greia")
        if manifest.architecture != self.architecture:
            raise UpdateCompatibilityError("update architecture does not match this Greia")
        if manifest.profile != self.profile:
            raise UpdateCompatibilityError("update build profile does not match this Greia")
        candidate_board = manifest.board
        if candidate_board is not None:
            installed_board = self.board
            if not isinstance(installed_board, str) or not installed_board:
                raise UpdateCompatibilityError(
                    "update board does not match this Greia: "
                    "installed board identity is incomplete"
                )
            if candidate_board != installed_board:
                raise UpdateCompatibilityError(
                    "update board does not match this Greia"
                )


class SystemUpdateBackend(Protocol):
    """Privileged platform-specific inactive-slot activation boundary."""

    @property
    def available(self) -> bool: ...

    def stage(self, bundle: InspectedUpdateBundle) -> None: ...

    def arm(self) -> dict[str, object]: ...

    def confirm_boot_health(self) -> dict[str, object]: ...

    def reconcile(self) -> dict[str, object]: ...

    def status_payload(self) -> dict[str, object]: ...


class UnavailableSystemUpdateBackend:
    """Fail-closed backend for current single-root layouts."""

    def __init__(self, reason: str = "A/B system-slot backend is not configured") -> None:
        self.reason = reason

    @property
    def available(self) -> bool:
        return False

    def stage(self, bundle: InspectedUpdateBundle) -> None:
        raise UpdateBackendUnavailable(self.reason)

    def arm(self) -> dict[str, object]:
        raise UpdateBackendUnavailable(self.reason)

    def confirm_boot_health(self) -> dict[str, object]:
        raise UpdateBackendUnavailable(self.reason)

    def reconcile(self) -> dict[str, object]:
        raise UpdateBackendUnavailable(self.reason)

    def status_payload(self) -> dict[str, object]:
        return {"available": False, "reason": self.reason}


class SystemUpdateInbox:
    """Unprivileged single-candidate inbox for Parent-delivered update bytes.

    ADR 0036 §7 / A10: the running device holds at most one compressed
    candidate under the fixed Greia-owned name ``candidate.greiaupdate``.
    Uploads stream into the same-directory temporary
    ``candidate.uploading`` and become visible only through one atomic
    rename. The large candidate is deleted after successful inactive-slot
    staging/boot-asset preparation; only small status/journal state
    remains. Receiving a bundle is not activation authority. Compatibility
    and inactive-slot activation are re-established by the privileged
    SystemUpdateService before any system write. There are no
    content-addressed filenames and no bundle-digest authority.
    """

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = Path(state_dir)
        self.inbox_dir = self.state_dir / "system-updates" / "inbox"
        self.status_path = self.state_dir / "system-updates" / "status.json"

    @property
    def candidate_path(self) -> Path:
        """Fixed Greia-owned candidate name (A10)."""

        return self.inbox_dir / INBOX_CANDIDATE_NAME

    @property
    def uploading_path(self) -> Path:
        """Fixed same-directory temporary upload name (A10)."""

        return self.inbox_dir / INBOX_UPLOADING_NAME

    def create_receive_staging(self, incoming_size: int) -> Path:
        """Create the fixed same-filesystem staging file for streamed input."""

        if isinstance(incoming_size, bool) or incoming_size <= 0 or incoming_size > MAX_BUNDLE_BYTES:
            raise UpdateBundleError("incoming update size is outside Greia bounds")
        self._prepare_inbox()
        self._assert_receive_capacity(incoming_size)
        staging = self.uploading_path
        with staging.open("wb"):
            pass
        os.chmod(staging, 0o600)
        return staging

    def receive_staged(self, staged_path: Path) -> InspectedUpdateBundle:
        """Validate and publish the fixed temporary file via atomic rename."""

        staged = Path(staged_path)
        self._prepare_inbox(clean_temporaries=False)
        self._require_owned_staging(staged)
        inspected = inspect_update_bundle(staged)
        source_digest = sha256_file(staged)
        destination = self.candidate_path
        os.replace(staged, destination)
        os.chmod(destination, 0o600)
        self._prune_other_candidates(destination)
        self._remove_stale_temporaries()
        self._record_received(inspected, destination, source_digest)
        return InspectedUpdateBundle(destination, inspected.manifest)

    def receive(self, bundle_path: Path) -> InspectedUpdateBundle:
        """Receive a file source through the same staged-publication contract.

        This path is suitable for files arriving from removable media or another
        filesystem. Network handlers should use ``create_receive_staging`` and
        ``receive_staged`` so the uploaded bytes are not copied twice locally.
        """

        source = Path(bundle_path)
        if not source.is_file():
            raise UpdateBundleError("update bundle is not a regular file")
        incoming_size = source.stat().st_size
        staging = self.create_receive_staging(incoming_size)
        try:
            with source.open("rb") as input_handle, staging.open("wb") as output_handle:
                shutil.copyfileobj(input_handle, output_handle, length=1024 * 1024)
            os.chmod(staging, 0o600)
            if staging.stat().st_size != incoming_size:
                raise UpdateBundleError("queued update copy size mismatch")
            return self.receive_staged(staging)
        finally:
            staging.unlink(missing_ok=True)

    def status_payload(self) -> dict[str, object]:
        try:
            raw = json.loads(self.status_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            raw = None
        if self.candidate_path.exists():
            try:
                manifest = _read_candidate_manifest_summary(self.candidate_path)
            except (SystemUpdateError, OSError, zipfile.BadZipFile):
                manifest = None
            if manifest is not None and (
                not isinstance(raw, dict)
                or raw.get("bundle_path") != str(self.candidate_path)
                or raw.get("release") != manifest.as_json_dict()
            ):
                # Receipt/status is progress data only. Recover the visible
                # queued identity from the fixed candidate when that record
                # is absent, malformed or stale.
                raw = {
                    "state": UpdateState.RECEIVED.value,
                    "release": manifest.as_json_dict(),
                    "bundle_path": str(self.candidate_path),
                    "activation_available": False,
                }
        if raw is None:
            return {
                "state": UpdateState.IDLE.value,
                "queued": None,
                "activation_available": False,
            }
        if not isinstance(raw, dict):
            return {
                "state": UpdateState.FAILED.value,
                "error": "update status state is invalid",
                "activation_available": False,
            }
        public = dict(raw)
        public.pop("bundle_path", None)
        return public

    def _prepare_inbox(self, *, clean_temporaries: bool = True) -> None:
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.inbox_dir, 0o700)
        if clean_temporaries:
            self._remove_stale_temporaries()

    def _assert_receive_capacity(self, incoming_size: int) -> None:
        free_bytes = shutil.disk_usage(self.inbox_dir).free
        if free_bytes < incoming_size + MIN_INBOX_FREE_BYTES:
            raise UpdateBundleError(
                "not enough free space to receive update: "
                "need incoming bundle bytes plus the 256 MiB Greia reserve"
            )

    def _require_owned_staging(self, staged: Path) -> None:
        try:
            parent = staged.parent.resolve(strict=True)
            inbox = self.inbox_dir.resolve(strict=True)
            info = staged.lstat()
        except OSError as exc:
            raise UpdateBundleError("update receive staging file is unavailable") from exc
        if parent != inbox or not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise UpdateBundleError("update receive staging must be a regular inbox file")
        if staged.name != INBOX_UPLOADING_NAME:
            raise UpdateBundleError("update receive staging name is invalid")
        if info.st_size <= 0 or info.st_size > MAX_BUNDLE_BYTES:
            raise UpdateBundleError("staged update size is outside Greia bounds")

    def _record_received(
        self,
        inspected: InspectedUpdateBundle,
        destination: Path,
        source_digest: str,
    ) -> None:
        payload = {
            "state": UpdateState.RECEIVED.value,
            "release": inspected.manifest.as_json_dict(),
            "bundle_path": str(destination),
            "bundle_sha256": source_digest,
            "activation_available": False,
        }
        _atomic_json(self.status_path, payload)

    def discard_candidate_after_stage(
        self,
        inspected: InspectedUpdateBundle,
        source_digest: str,
    ) -> None:
        """Delete the large fixed candidate after successful staging.

        Keeps only bounded status/journal metadata (release facts plus the
        bundle digest). Called only after the backend confirms the
        inactive slot and boot assets are prepared; staging failures must
        never reach this path so the candidate is preserved for retry.
        """

        try:
            self.candidate_path.unlink(missing_ok=True)
        except OSError as exc:
            raise UpdateBundleError("unable to discard staged update candidate") from exc
        payload = {
            "state": UpdateState.STAGING.value,
            "release": inspected.manifest.as_json_dict(),
            "bundle_sha256": source_digest,
            "staged": True,
            "activation_available": False,
        }
        _atomic_json(self.status_path, payload)

    def _remove_stale_temporaries(self) -> None:
        try:
            self.uploading_path.unlink(missing_ok=True)
            for candidate in self.inbox_dir.glob(".incoming-*.tmp"):
                candidate.unlink(missing_ok=True)
        except OSError as exc:
            raise UpdateBundleError("unable to clean stale update inbox temporary") from exc

    def _prune_other_candidates(self, keep: Path) -> None:
        """Keep exactly the fixed candidate; remove legacy duplicates."""

        try:
            for candidate in self.inbox_dir.glob(f"*{BUNDLE_SUFFIX}"):
                if candidate != keep:
                    candidate.unlink(missing_ok=True)
            uploading = self.uploading_path
            if uploading.exists():
                uploading.unlink(missing_ok=True)
        except OSError as exc:
            raise UpdateBundleError("unable to bound update inbox candidates") from exc


class SystemUpdateService:
    """Privileged compatibility/backend coordinator for queued bundles.

    ADR 0036: no provenance trust. Verification is archive structure,
    manifest validity, member integrity (digests), and platform
    compatibility. PERSIST readability and slot staging belong to T02.
    """

    def __init__(
        self,
        state_dir: Path,
        identity: SystemIdentity,
        backend: SystemUpdateBackend | None = None,
    ) -> None:
        self.state_dir = Path(state_dir)
        self.identity = identity
        self.backend = backend or UnavailableSystemUpdateBackend()

    def verify(self, bundle_path: Path) -> InspectedUpdateBundle:
        inspected = inspect_update_bundle(bundle_path)
        self.identity.assert_compatible(inspected.manifest)
        return inspected

    def verify_for_activation(
        self, bundle_path: Path
    ) -> tuple[InspectedUpdateBundle, str]:
        """Verify compatibility; always classifies usable candidates as update.

        There is no signed anti-rollback authority in v3. Older bundles are
        refused at inspection with the v3 migration message.
        """

        inspected = self.verify(bundle_path)
        return inspected, "update"

    def stage(self, bundle_path: Path) -> InspectedUpdateBundle:
        inspected, _decision = self.verify_for_activation(bundle_path)
        if not self.backend.available:
            raise UpdateBackendUnavailable(
                str(self.backend.status_payload().get("reason", "update backend unavailable"))
            )
        self.backend.stage(inspected)
        self._discard_inbox_candidate_after_stage(inspected)
        return inspected

    def _discard_inbox_candidate_after_stage(
        self, inspected: InspectedUpdateBundle
    ) -> None:
        """Remove the large inbox candidate only after successful staging.

        Staging failures raise before this point, so the candidate is
        preserved for retry and never reported as success. Only an
        inbox-owned fixed candidate is discarded; out-of-inbox bundle
        paths used by offline tooling are left untouched.
        """

        inbox = SystemUpdateInbox(self.state_dir)
        try:
            base = inbox.inbox_dir.resolve(strict=False)
            candidate = inbox.candidate_path.resolve(strict=False)
            staged = Path(inspected.path).resolve(strict=False)
            staged.relative_to(base)
            candidate.relative_to(base)
        except (OSError, ValueError):
            return
        if staged != candidate:
            return
        try:
            digest = sha256_file(candidate)
        except OSError:
            return
        inbox.discard_candidate_after_stage(inspected, digest)

    def status_payload(self) -> dict[str, object]:
        return {
            "identity": {
                "version": self.identity.version,
                "platform_family": self.identity.platform_family,
                "architecture": self.identity.architecture,
                "profile": self.identity.profile,
                "board": self.identity.board,
            },
            "activation": self.backend.status_payload(),
        }

    def arm(self) -> dict[str, object]:
        """Arm the staged candidate one-shot via the privileged backend."""
        return self.backend.arm()

    def confirm_boot_health(self) -> dict[str, object]:
        """Commit or roll back the candidate from the authoritative boot observation."""
        return self.backend.confirm_boot_health()

    def reconcile(self) -> dict[str, object]:
        """Crash-reconcile the update journal against the boot observation."""
        return self.backend.reconcile()


def build_persistent_state_contract_bytes(
    namespaces: tuple[str, ...] = _PERSISTENT_NAMESPACES,
) -> bytes:
    return canonical_json(
        {
            "schema_version": PERSISTENT_CONTRACT_SCHEMA_VERSION,
            "namespaces": list(namespaces),
            "migration_policy": _PERSISTENT_MIGRATION_POLICY,
        }
    )


def verify_persistent_state_contract_bytes(raw: bytes) -> dict[str, object]:
    if len(raw) <= 0 or len(raw) > MAX_PERSISTENT_CONTRACT_BYTES:
        raise UpdateBundleError("persistent-state contract exceeds Greia bound")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateBundleError("persistent-state contract is not valid JSON") from exc
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "namespaces", "migration_policy"}
    ):
        raise UpdateBundleError("persistent-state contract fields are invalid")
    if value.get("schema_version") != PERSISTENT_CONTRACT_SCHEMA_VERSION:
        raise UpdateBundleError("persistent-state contract schema is unsupported")
    namespaces = value.get("namespaces")
    if (
        not isinstance(namespaces, list)
        or not namespaces
        or len(namespaces) > 64
        or not all(isinstance(item, str) and _IDENTIFIER.fullmatch(item) for item in namespaces)
        or len(set(namespaces)) != len(namespaces)
    ):
        raise UpdateBundleError("persistent-state contract namespaces are invalid")
    if value.get("migration_policy") != _PERSISTENT_MIGRATION_POLICY:
        raise UpdateBundleError("persistent-state contract migration policy is invalid")
    if raw != canonical_json(value):
        raise UpdateBundleError("persistent-state contract is not canonical JSON")
    return value


def build_update_bundle(
    *,
    payload_path: Path,
    hardware_support_path: Path | None,
    output_path: Path,
    version: str,
    release_id: str,
    platform_family: str,
    architecture: str,
    profile: str,
    board: str | None = None,
    payload_uncompressed_bytes: int,
    minimum_slot_bytes: int | None = None,
    persist_read_schema_min: int,
    persist_read_schema_max: int,
    persist_write_schema: int,
    release_notes: str = "",
) -> UpdateManifest:
    """Build one unsigned v3 bundle with no key material.

    ``payload_path`` must be ``payload.ext4.zst`` (zstd bytes, stored without
    double compression). ``hardware_support_path`` is optional. There is no
    separate persistent-state contract member; PERSIST compatibility travels
    as three manifest integers.
    """

    payload_path = Path(payload_path)
    output_path = Path(output_path)
    hw_path = Path(hardware_support_path) if hardware_support_path is not None else None
    if payload_path.is_symlink() or not payload_path.is_file():
        raise UpdateBundleError("payload is not a regular file")
    if hw_path is not None and (hw_path.is_symlink() or not hw_path.is_file()):
        raise UpdateBundleError("hardware-support is not a regular file")
    payload_size = payload_path.stat().st_size
    if payload_size <= 0 or payload_size > MAX_PAYLOAD_BYTES:
        raise UpdateBundleError("payload size is outside Greia bounds")
    _assert_zstd_file(payload_path, "payload")
    hardware_size: int | None = None
    hardware_sha: str | None = None
    hardware_bound: int | None = None
    if hw_path is not None:
        hardware_size = hw_path.stat().st_size
        if hardware_size <= 0 or hardware_size > MAX_HARDWARE_SUPPORT_BYTES:
            raise UpdateBundleError("hardware-support size is outside Greia bounds")
        _assert_zstd_file(hw_path, "hardware-support")
        hardware_sha = sha256_file(hw_path)
        # A supplied hardware-support member is a production artifact, not
        # an opaque container fixture. The canonical shared parser must
        # accept the exact bytes before the bundle can be published; this
        # keeps producer and runtime verdicts identical and prevents a
        # release from carrying support that the device is guaranteed to
        # reject later. Tests that need malformed ZIP members construct
        # those containers directly instead of weakening this producer.
        try:
            inspected_hw = _archive.inspect_archive_file(
                hw_path,
                expected_compressed_bytes=hardware_size,
                expected_sha256=hardware_sha,
            )
        except _archive.HardwareSupportArchiveError as exc:
            raise UpdateBundleError(
                f"hardware-support archive refused, refusing bundle: {exc}"
            ) from exc
        hardware_bound = inspected_hw.extracted_size_bound
    if isinstance(payload_uncompressed_bytes, bool) or not isinstance(
        payload_uncompressed_bytes, int
    ):
        raise UpdateBundleError("payload_uncompressed_bytes must be an integer")
    minimum = minimum_slot_bytes if minimum_slot_bytes is not None else payload_uncompressed_bytes
    if isinstance(minimum, bool) or not isinstance(minimum, int):
        raise UpdateBundleError("minimum_slot_bytes must be an integer")
    manifest = UpdateManifest(
        schema_version=SCHEMA_VERSION,
        release_id=release_id,
        version=version,
        platform_family=platform_family,
        architecture=architecture,
        profile=profile,
        board=board,
        payload_sha256=sha256_file(payload_path),
        payload_size=payload_size,
        payload_uncompressed_bytes=payload_uncompressed_bytes,
        payload_minimum_slot_bytes=minimum,
        hardware_support_sha256=hardware_sha,
        hardware_support_size=hardware_size,
        hardware_support_extracted_bytes_bound=hardware_bound,
        persist_read_schema_min=persist_read_schema_min,
        persist_read_schema_max=persist_read_schema_max,
        persist_write_schema=persist_write_schema,
        release_notes=release_notes,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise UpdateBundleError(f"output already exists: {output_path}")
    with tempfile.NamedTemporaryFile(
        prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_STORED,
            allowZip64=True,
        ) as archive:
            _writestr_deterministic(
                archive, MANIFEST_NAME, manifest.canonical_bytes(), compress=True
            )
            _write_file_deterministic(archive, PAYLOAD_NAME, payload_path, compress=False)
            if hw_path is not None:
                _write_file_deterministic(
                    archive, HARDWARE_SUPPORT_NAME, hw_path, compress=False
                )
        if temporary.stat().st_size <= 0 or temporary.stat().st_size > MAX_BUNDLE_BYTES:
            raise UpdateBundleError("generated update bundle exceeds Greia bound")
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return manifest


def inspect_update_bundle(path: Path) -> InspectedUpdateBundle:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise UpdateBundleError("update bundle is not a regular file")
    size = path.stat().st_size
    if size <= 0 or size > MAX_BUNDLE_BYTES:
        raise UpdateBundleError("update bundle size is outside Greia bounds")
    try:
        with zipfile.ZipFile(path, "r") as archive:
            manifest = inspect_update_bundle_archive(archive, archive_size=size)
    except (zipfile.BadZipFile, OSError) as exc:
        if isinstance(exc, UpdateBundleError):
            raise
        raise UpdateBundleError("update bundle is not a valid Greia ZIP artifact") from exc
    return InspectedUpdateBundle(path, manifest)


def inspect_update_bundle_archive(
    archive: zipfile.ZipFile, *, archive_size: int
) -> UpdateManifest:
    """Run the canonical v3 member, size, digest and zstd checks on an open ZIP.

    This lets a bounded stored member inside a typed software-update package
    use the same validator without copying a potentially multi-gigabyte image
    bundle into a temporary file.
    """

    if isinstance(archive_size, bool) or not 0 < archive_size <= MAX_BUNDLE_BYTES:
        raise UpdateBundleError("update bundle size is outside Greia bounds")
    infos = archive.infolist()
    names = [info.filename for info in infos]
    if names != list(BUNDLE_MEMBERS_V3) and names != list(BUNDLE_MEMBERS_V3_WITH_HW):
        _raise_for_legacy_members(archive, names)
        raise UpdateBundleError("update bundle members/order are invalid")
    _reject_unsafe_members(infos)
    by_name = {info.filename: info for info in infos}
    manifest_info = by_name[MANIFEST_NAME]
    payload_info = by_name[PAYLOAD_NAME]
    hw_info = by_name.get(HARDWARE_SUPPORT_NAME)
    if manifest_info.file_size <= 0 or manifest_info.file_size > MAX_MANIFEST_BYTES:
        raise UpdateBundleError("manifest exceeds Greia bound")
    if payload_info.file_size <= 0 or payload_info.file_size > MAX_PAYLOAD_BYTES:
        raise UpdateBundleError("payload exceeds Greia bound")
    if payload_info.compress_type != zipfile.ZIP_STORED:
        raise UpdateBundleError("payload member must be stored without recompression")
    if hw_info is not None:
        if hw_info.file_size <= 0 or hw_info.file_size > MAX_HARDWARE_SUPPORT_BYTES:
            raise UpdateBundleError("hardware-support exceeds Greia bound")
        if hw_info.compress_type != zipfile.ZIP_STORED:
            raise UpdateBundleError(
                "hardware-support member must be stored without recompression"
            )
    manifest_raw = archive.read(MANIFEST_NAME)
    try:
        manifest_json = json.loads(manifest_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateBundleError("manifest is not valid JSON") from exc
    if isinstance(manifest_json, dict) and manifest_json.get(
        "schema_version"
    ) in (V1_SCHEMA_VERSION, V2_SCHEMA_VERSION):
        raise UpdateBundleError(_migration_error())
    manifest = UpdateManifest.from_json_dict(manifest_json)
    if manifest_raw != manifest.canonical_bytes():
        raise UpdateBundleError("manifest is not canonical JSON")
    if payload_info.file_size != manifest.payload_size:
        raise UpdateBundleError("payload size does not match manifest")
    if hw_info is None:
        if manifest.hardware_support_sha256 is not None or manifest.hardware_support_size is not None:
            raise UpdateBundleError("hardware-support manifest facts require the member")
    else:
        if manifest.hardware_support_sha256 is None or manifest.hardware_support_size is None:
            raise UpdateBundleError("hardware-support member requires manifest facts")
        if hw_info.file_size != manifest.hardware_support_size:
            raise UpdateBundleError("hardware-support size does not match manifest")
    _verify_member_digest(archive, PAYLOAD_NAME, manifest.payload_sha256)
    if hw_info is not None and manifest.hardware_support_sha256 is not None:
        _verify_member_digest(archive, HARDWARE_SUPPORT_NAME, manifest.hardware_support_sha256)
    _assert_member_zstd_magic(archive, payload_info)
    if hw_info is not None:
        _assert_member_zstd_magic(archive, hw_info)
    return manifest


def _migration_error() -> str:
    return (
        "v1/v2 signed system-update bundle is not accepted: "
        "rebuild the release as v3 (.greiaupdate v3 migration required; "
        "see ADR 0036 §3)"
    )


def _raise_for_legacy_members(
    archive: zipfile.ZipFile, names: list[str]
) -> None:
    """Reject old signed layouts with the explicit v3 migration message."""

    for name in names:
        if name.endswith(".sig"):
            raise UpdateBundleError(_migration_error())
    try:
        raw = archive.read(MANIFEST_NAME)
    except KeyError:
        return
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return
    if isinstance(document, dict) and document.get("schema_version") in (
        V1_SCHEMA_VERSION,
        V2_SCHEMA_VERSION,
    ):
        raise UpdateBundleError(_migration_error())


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _validate_identifier(value: str, name: str, maximum: int) -> None:
    if not isinstance(value, str) or not value or len(value) > maximum or not _IDENTIFIER.fullmatch(value):
        raise UpdateBundleError(f"{name} must be a bounded ASCII identifier")


def _validate_text(value: str, name: str, maximum: int) -> None:
    if not isinstance(value, str) or not value or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise UpdateBundleError(f"{name} must be bounded printable text")


def _validate_board(value: str | None) -> None:
    if value is None:
        return
    _validate_identifier(value, "board", _MAX_BOARD)


def _validate_persist_schema(read_min: int, read_max: int, write: int) -> None:
    for name, value in (
        ("persist_read_schema_min", read_min),
        ("persist_read_schema_max", read_max),
        ("persist_write_schema", write),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise UpdateBundleError(f"{name} must be an integer")
        if value < 0 or value > _MAX_PERSIST_SCHEMA:
            raise UpdateBundleError(f"{name} is outside Greia bounds")
    if read_min > read_max:
        raise UpdateBundleError("persist readable schema range is inverted")


def _reject_unsafe_members(infos: list[zipfile.ZipInfo]) -> None:
    seen: set[str] = set()
    for info in infos:
        name = info.filename
        if name in seen:
            raise UpdateBundleError("update bundle contains a duplicate member")
        seen.add(name)
        if (
            info.is_dir()
            or name.startswith("/")
            or "\\" in name
            or "/" in name
            or ".." in Path(name).parts
        ):
            raise UpdateBundleError("update bundle contains an unsafe member")
        if info.flag_bits & 0x1:
            raise UpdateBundleError("encrypted ZIP members are not supported")
        if info.compress_type not in (
            zipfile.ZIP_STORED,
            zipfile.ZIP_DEFLATED,
        ):
            raise UpdateBundleError("unsupported ZIP compression method")
        mode = (info.external_attr >> 16) & 0o170000
        if mode == 0o120000:
            raise UpdateBundleError("update bundle symlinks are not supported")
        if info.file_size > MAX_BUNDLE_BYTES:
            raise UpdateBundleError("update bundle member exceeds Greia bound")


def _verify_member_digest(
    archive: zipfile.ZipFile, name: str, expected_hex: str
) -> None:
    digest = hashlib.sha256()
    with archive.open(name, "r") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    if digest.hexdigest() != expected_hex:
        raise UpdateBundleError(f"{name} digest does not match manifest")


def _assert_zstd_file(path: Path, label: str) -> None:
    with Path(path).open("rb") as handle:
        magic = handle.read(4)
    if magic != _ZSTD_MAGIC:
        raise UpdateBundleError(f"{label} must be zstd-compressed bytes")


def _assert_member_zstd_magic(
    archive: zipfile.ZipFile, info: zipfile.ZipInfo
) -> None:
    with archive.open(info.filename, "r") as handle:
        magic = handle.read(4)
    if magic != _ZSTD_MAGIC:
        raise UpdateBundleError(f"{info.filename} must be zstd-compressed bytes")


def _writestr_deterministic(
    archive: zipfile.ZipFile, name: str, data: bytes, *, compress: bool
) -> None:
    info = zipfile.ZipInfo(filename=name, date_time=_DETERMINISTIC_ZIP_DATE)
    info.create_system = 3
    info.external_attr = (0o644 << 16) | (0x20 if not compress else 0x20)
    info.compress_type = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    archive.writestr(info, data, compress_type=info.compress_type, compresslevel=6 if compress else None)


def _write_file_deterministic(
    archive: zipfile.ZipFile, name: str, source: Path, *, compress: bool
) -> None:
    info = zipfile.ZipInfo(filename=name, date_time=_DETERMINISTIC_ZIP_DATE)
    info.create_system = 3
    info.external_attr = (0o644 << 16) | 0x20
    info.compress_type = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    with source.open("rb") as input_handle, archive.open(info, "w") as output_handle:
        while True:
            chunk = input_handle.read(1024 * 1024)
            if not chunk:
                break
            output_handle.write(chunk)


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(canonical_json(payload))
        os.chmod(temporary, 0o600)
        temporary.replace(path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Step 8A.6: privileged update service on the common slot/journal seams
# ---------------------------------------------------------------------------
# The unprivileged inbox above keeps receiving Parent-delivered bytes; this
# section wires the privileged side behind the socket-activated
# ``greia-system-update`` service (separate from
# ``greia-install-transaction``):
#
#   inbox candidate -> SystemUpdateService compatibility -> SlotBackedSystemUpdateBackend
#   -> common SlotWriter stream -> common SlotFinalizer bind -> shared
#   BootTransactionJournal -> boot-backend one-shot arm -> health commit.
#
# The brief's four privileged phases map onto the existing six semantic ops
# (owned by ``greia_platform.update_privileged``; this module never redefines
# the protocol): VERIFY_AND_STAGE is VERIFY_CURRENT_CANDIDATE followed by
# STAGE_CURRENT_CANDIDATE, SCHEDULE is ARM_CURRENT_CANDIDATE, CONFIRM is
# CONFIRM_BOOT_HEALTH, and STATUS/RECONCILE observe and crash-reconcile the
# same journal the A8-FAULTS harness reads.
#
# Dependency direction: ``persistent_layout`` and ``slot_writer`` both import
# this module at their top level, so the privileged seam below reaches them
# through function-local imports. No shell, no partition-device authority and
# no network cross this seam: destination access arrives only through the
# injected typed factories (loop/disposable-media files and fakes in this
# phase), and every refusal leaves the destination seam untouched.

if TYPE_CHECKING:  # pragma: no cover - typing only; runtime imports stay local
    from .boot_transaction import BootTransactionJournal as _Journal
    from .persistent_layout import InstalledLayoutRecord as _LayoutRecord

#: Journal directory name under ``state_dir / "system-updates"`` for isolated
#: fixtures without an installed shared-journal override. Installed updater,
#: first-install and boot-health service use ``BOOT_JOURNAL_DIR_DEFAULT``.
UPDATE_JOURNAL_DIR_NAME = "journal"

#: Default peer UIDs for isolated endpoint use. The installed socket service
#: injects the greiapanel UID with the narrower operation allowlist in
#: ``update_privileged``; root retains the complete semantic vocabulary.
UPDATE_SERVICE_ALLOWED_UIDS = (0,)

#: Environment overrides for the socket-activated composition root. Defaults
#: bind the installed-system authorities; nothing here names a partition
#: device or a raw command.
UPDATE_STATE_DIR_ENV = "GREIA_UPDATE_STATE_DIR"
UPDATE_STATE_DIR_DEFAULT = "/var/lib/greia-os"
INSTALLED_LAYOUT_RECORD_ENV = "GREIA_INSTALLED_LAYOUT_RECORD"
INSTALLED_LAYOUT_RECORD_DEFAULT = "/etc/greia-os/layout/installed-layout.json"
#: Installed product identity: the single image-owned release authority written
#: by ``SlotFinalizer`` into every finalized slot
#: (``etc/greia-os/release-identity.json``), visible on the running system at
#: the default below. This file is the installed product identity contract;
#: the same ``GREIA_RELEASE_IDENTITY_PATH`` name the boot-health observer uses
#: (``greia_platform.boot_health``) so both readers resolve one path.
INSTALLED_RELEASE_IDENTITY_ENV = "GREIA_RELEASE_IDENTITY_PATH"
INSTALLED_RELEASE_IDENTITY_DEFAULT = "/etc/greia-os/release-identity.json"
#: Installed profile document baked by ``build/build-image.sh`` (declared
#: profile manifest): fallback for compatibility facts when an older slot
#: was finalized before the release authority stated them. Never a second
#: identity: the release-identity file always wins where it states a fact.
INSTALLED_IMAGE_PROFILE_ENV = "GREIA_IMAGE_PROFILE_PATH"
INSTALLED_IMAGE_PROFILE_DEFAULT = "/etc/greia-os/image-profile.json"
#: Upper bound for installed identity/profile reads (small by construction).
MAX_INSTALLED_IDENTITY_BYTES = 64 * 1024
#: Boot-control directory holding the production ``grubenv`` one-shot block.
#: The installer writes it to the boot-control filesystem; GRUB reads the
#: same block as ``$prefix/grubenv``. Explicit env or the on-device bind.
UPDATE_GRUBENV_DIR_ENV = "GREIA_GRUBENV_DIR"
UPDATE_GRUBENV_DIR_DEFAULT = "/boot/grub"
UPDATE_SYSTEM_VERSION_ENV = "GREIA_SYSTEM_VERSION"
UPDATE_SYSTEM_PLATFORM_ENV = "GREIA_SYSTEM_PLATFORM_FAMILY"
UPDATE_SYSTEM_ARCH_ENV = "GREIA_SYSTEM_ARCHITECTURE"
UPDATE_SYSTEM_PROFILE_ENV = "GREIA_SYSTEM_PROFILE"
UPDATE_SYSTEM_BOARD_ENV = "GREIA_SYSTEM_BOARD"
#: Test-only identity fallbacks. The shipped ``greia-system-update.service``
#: sets none of these: on device the identity resolves from the installed
#: release authority above. They remain so offline unit/proof harnesses can
#: compose an identity without installed image state; a fact stated by the
#: installed files always wins over the environment.
#: Deployment parameters for the production inactive-slot seams below.
#: Defaults bind the installed system; explicit values point the same
#: production factories at a disposable device tree (tests/proofs), never
#: at a Python-supplied seam. No Python caller supplies custom seams.
UPDATE_DEV_ROOT_ENV = "GREIA_UPDATE_DEV_ROOT"
UPDATE_DEV_ROOT_DEFAULT = "/dev"
#: Optional override for the udev PARTUUID directory. When unset, the
#: default owned by ``greia_platform.block_slots`` applies (that module,
#: not this service composition, names the installed udev path).
UPDATE_BY_PARTUUID_DIR_ENV = "GREIA_UPDATE_BY_PARTUUID_DIR"
UPDATE_MOUNT_ROOT_ENV = "GREIA_UPDATE_MOUNT_ROOT"
#: Updater-scoped runtime directory under the already-granted ``/run/greia-os``
#: tree (created by tmpfiles): the service mkdirs the per-stage mountpoint
#: itself, so no extra top-level runtime path needs a sandbox grant. The
#: installer keeps its own separate ``/run/greia-slots`` default.
UPDATE_MOUNT_ROOT_DEFAULT = "/run/greia-os/slots"
UPDATE_HARDWARE_SUPPORT_POOL_ENV = "GREIA_UPDATE_HARDWARE_SUPPORT_POOL"
UPDATE_HARDWARE_SUPPORT_POOL_DEFAULT = "/opt/greia-hardware-support"
UPDATE_SYSFS_DEVICES_ENV = "GREIA_UPDATE_SYSFS_DEVICES"
UPDATE_SYSFS_DEVICES_DEFAULT = "/sys/devices"


class UpdateLayoutError(SystemUpdateError):
    """Trusted layout facts are missing or not authoritative (fail-closed)."""


def installed_layout_record_path() -> Path:
    """Resolve the trusted layout-record path (explicit env or system bind)."""
    override = os.environ.get(INSTALLED_LAYOUT_RECORD_ENV, "").strip()
    return Path(override) if override else Path(INSTALLED_LAYOUT_RECORD_DEFAULT)


def load_installed_layout_record(path: Path | None = None) -> "_LayoutRecord | None":
    """Load the trusted installed-layout record, or None when absent.

    A missing record is the normal single-root case (no A/B authority), not
    an error. Symlinks, unreadable files and corrupt records fail closed via
    :class:`UpdateLayoutError`.
    """
    from .persistent_layout import InstalledLayoutRecord, PersistentLayoutError

    candidate = Path(path) if path is not None else installed_layout_record_path()
    if candidate.is_symlink():
        raise UpdateLayoutError("installed layout record must not be a symlink")
    try:
        raw = candidate.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise UpdateLayoutError("installed layout record is unreadable") from exc
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateLayoutError("installed layout record is not valid JSON") from exc
    try:
        return InstalledLayoutRecord.from_dict(document)
    except PersistentLayoutError as exc:
        raise UpdateLayoutError(
            f"installed layout record is not authoritative: {exc}"
        ) from exc


def installed_release_identity_path() -> Path:
    """Resolve the installed release-authority path (explicit env or image bind)."""
    override = os.environ.get(INSTALLED_RELEASE_IDENTITY_ENV, "").strip()
    return Path(override) if override else Path(INSTALLED_RELEASE_IDENTITY_DEFAULT)


def installed_image_profile_path() -> Path:
    """Resolve the installed profile-document path (explicit env or image bind)."""
    override = os.environ.get(INSTALLED_IMAGE_PROFILE_ENV, "").strip()
    return Path(override) if override else Path(INSTALLED_IMAGE_PROFILE_DEFAULT)


def load_installed_release_identity(
    path: Path | None = None,
) -> dict[str, object] | None:
    """Load the image-owned installed release authority, or None when absent.

    A missing file is the normal no-slot case (single-root images, offline
    harnesses), not an error: the caller falls back to the installed profile
    and test-only environment. A present file must be authoritative (regular
    file, never a symlink, bounded canonical JSON with the ``SlotFinalizer``
    keys); anything else fails closed via :class:`UpdateLayoutError`.
    """
    candidate = Path(path) if path is not None else installed_release_identity_path()
    if candidate.is_symlink():
        raise UpdateLayoutError("installed release identity must not be a symlink")
    try:
        raw_bytes = candidate.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise UpdateLayoutError("installed release identity is unreadable") from exc
    if len(raw_bytes) > MAX_INSTALLED_IDENTITY_BYTES:
        raise UpdateLayoutError("installed release identity exceeds Greia bounds")
    try:
        document = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateLayoutError(
            "installed release identity is not valid JSON"
        ) from exc
    if not isinstance(document, dict):
        raise UpdateLayoutError("installed release identity must be a JSON object")
    slot = document.get("slot")
    if slot not in ("A", "B"):
        raise UpdateLayoutError("installed release identity slot must be A or B")
    release_id = document.get("release_id")
    if (
        not isinstance(release_id, str)
        or not release_id
        or len(release_id) > _MAX_RELEASE_ID
        or not _IDENTIFIER.fullmatch(release_id)
    ):
        raise UpdateLayoutError("installed release identity release_id is invalid")
    for key, maximum in (
        ("platform_family", 64),
        ("architecture", 32),
        ("profile", 96),
    ):
        value = document.get(key)
        if value is None:
            continue
        if (
            not isinstance(value, str)
            or not value
            or len(value) > maximum
            or not _IDENTIFIER.fullmatch(value)
        ):
            raise UpdateLayoutError(
                f"installed release identity {key} is invalid"
            )
    version = document.get("version")
    if version is not None and (
        not isinstance(version, str)
        or not version
        or len(version) > _MAX_VERSION
        or any(ord(character) < 32 for character in version)
    ):
        raise UpdateLayoutError("installed release identity version is invalid")
    board = document.get("board")
    if board is not None and (
        not isinstance(board, str)
        or not board
        or len(board) > _MAX_BOARD
        or not _IDENTIFIER.fullmatch(board)
    ):
        raise UpdateLayoutError("installed release identity board is invalid")
    canonical = (
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    if canonical != raw_bytes:
        raise UpdateLayoutError("installed release identity is not canonical JSON")
    return document


def _installed_profile_compat_facts(path: Path | None = None) -> dict[str, str]:
    """Read compatibility facts from the installed profile document, best effort.

    Returns any of ``platform_family``/``profile``/``architecture`` the
    document states as bounded identifiers, else ``{}``. Absent or unusable
    documents contribute nothing: this source is only a fallback for facts
    the release-identity authority does not carry, and enforcement stays in
    :meth:`SystemIdentity.assert_compatible` (unknown facts refuse).
    """
    candidate = Path(path) if path is not None else installed_image_profile_path()
    try:
        if candidate.is_symlink():
            return {}
        raw_bytes = candidate.read_bytes()
    except OSError:
        return {}
    if len(raw_bytes) > MAX_INSTALLED_IDENTITY_BYTES:
        return {}
    try:
        document = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {}
    if not isinstance(document, dict):
        return {}
    facts: dict[str, str] = {}

    def _nested(section: object, key: str) -> object:
        if not isinstance(section, dict):
            return None
        return section.get(key)

    candidates = (
        ("platform_family", _nested(document.get("platform"), "family"), 64),
        ("profile", _nested(document.get("profile"), "id"), 96),
        ("architecture", _nested(document.get("base"), "architecture"), 32),
    )
    for name, value, maximum in candidates:
        if (
            isinstance(value, str)
            and value
            and len(value) <= maximum
            and _IDENTIFIER.fullmatch(value)
        ):
            facts[name] = value
    return facts


def resolve_installed_system_identity(
    *,
    layout_record_path: Path | None = None,
    release_identity_path: Path | None = None,
    image_profile_path: Path | None = None,
) -> SystemIdentity:
    """Resolve the updater identity from the installed release authority.

    Precedence per fact: the image-owned ``release-identity.json`` first;
    then the authoritative installed layout record (platform family, install
    profile) and the installed profile document (architecture, profile,
    platform family); then the test-only ``GREIA_SYSTEM_*`` environment;
    finally ``"unknown"`` (which refuses compatibility). A corrupt primary
    authority fails closed; unusable fallback sources simply contribute
    nothing, while the backend still enforces layout authority at stage time.
    """
    release = load_installed_release_identity(release_identity_path)
    layout: "_LayoutRecord | None"
    try:
        if layout_record_path is not None:
            layout = load_installed_layout_record(Path(layout_record_path))
        else:
            layout = load_installed_layout_record()
    except UpdateLayoutError:
        layout = None
    profile_facts = _installed_profile_compat_facts(image_profile_path)

    def _first(*values: object) -> str:
        for value in values:
            if isinstance(value, str) and value:
                return value
        return "unknown"

    release_text = (
        {key: value for key, value in release.items() if isinstance(value, str)}
        if release is not None
        else {}
    )
    board_raw = (
        release_text.get("board")
        or os.environ.get(UPDATE_SYSTEM_BOARD_ENV, "").strip()
    )
    return SystemIdentity(
        version=_first(
            release_text.get("version"),
            os.environ.get(UPDATE_SYSTEM_VERSION_ENV, "").strip(),
        ),
        platform_family=_first(
            release_text.get("platform_family"),
            getattr(layout, "platform_family", None),
            profile_facts.get("platform_family"),
            os.environ.get(UPDATE_SYSTEM_PLATFORM_ENV, "").strip(),
        ),
        architecture=_first(
            release_text.get("architecture"),
            profile_facts.get("architecture"),
            os.environ.get(UPDATE_SYSTEM_ARCH_ENV, "").strip(),
        ),
        profile=_first(
            release_text.get("profile"),
            getattr(layout, "install_profile", None),
            profile_facts.get("profile"),
            os.environ.get(UPDATE_SYSTEM_PROFILE_ENV, "").strip(),
        ),
        board=board_raw or None,
    )


def _assert_persist_preflight(installed: object, manifest: UpdateManifest) -> int:
    """Coerce the PERSIST preflight seam and enforce the readable range.

    Accepts the installed schema as an int or as canonical marker bytes
    (see ``persistent_layout.emit_persist_schema_marker``). Failures raise
    :class:`UpdateCompatibilityError` with a compatibility/migration message
    so callers report data compatibility, never a generic staging error.
    """
    from .persistent_layout import (
        PersistentLayoutError,
        assert_persist_schema_compatible,
        parse_persist_schema_marker,
    )

    try:
        if isinstance(installed, bool):
            raise PersistentLayoutError("installed PERSIST schema must be an integer")
        if isinstance(installed, int):
            schema = installed
        elif isinstance(installed, (bytes, bytearray)):
            if not installed:
                raise PersistentLayoutError(
                    "installed PERSIST schema marker is not authoritative"
                )
            schema = parse_persist_schema_marker(bytes(installed))
        else:
            raise PersistentLayoutError(
                "installed PERSIST schema marker is not authoritative"
            )
        return assert_persist_schema_compatible(schema, manifest)
    except (PersistentLayoutError, UpdateBundleError) as exc:
        raise UpdateCompatibilityError(str(exc)) from exc


def inactive_slot_for(record: "_LayoutRecord") -> str | None:
    """Return the one slot that is neither active nor accepted.

    Returns None for single-root layouts (no second slot exists). Raises
    :class:`SystemUpdateError` when an A/B layout has no inactive slot, so
    the service can never stage into a live slot.
    """
    if record.system_b is None:
        return None
    live = {
        slot
        for slot in (record.boot_control.active_slot, record.accepted_slot)
        if slot in ("A", "B")
    }
    for slot in ("A", "B"):
        if slot not in live:
            return slot
    raise SystemUpdateError(
        "refusing to stage into the active slot: no inactive slot is available"
    )


def _default_slot_profile_policy(record: "_LayoutRecord") -> object:
    """Derive finalizer policy from layout plus verified shared mounts."""
    from .slot_writer import SlotProfilePolicy
    from .fstab import read_fstab_uuid_for_mount
    from .update_activation import (
        BOOT_CONTROL_MOUNTPOINT,
        GREIA_OS_STATE_MOUNTPOINT,
        PERSIST_MOUNTPOINT,
        RuntimeMountProbe,
    )

    persist_uuid = record.persist.filesystem_uuid
    mounts = RuntimeMountProbe()
    if not mounts.mounted_uuid_matches(
        PERSIST_MOUNTPOINT, persist_uuid, expected_mount_root="/"
    ) or not mounts.mounted_uuid_matches(
        GREIA_OS_STATE_MOUNTPOINT,
        persist_uuid,
        expected_mount_root="/greia/namespaces/parent-credentials",
    ):
        raise SystemUpdateError(
            "expected PERSIST filesystem and Greia state bind are not mounted"
        )
    try:
        boot_uuid = read_fstab_uuid_for_mount(Path("/etc/fstab"), "/boot")
    except ValueError as exc:
        raise SystemUpdateError("shared boot-control UUID is unavailable") from exc
    if not mounts.mounted_uuid_matches(
        BOOT_CONTROL_MOUNTPOINT, boot_uuid, expected_mount_root="/"
    ):
        raise SystemUpdateError(
            "shared boot-control filesystem is not mounted from its installed UUID"
        )

    return SlotProfilePolicy(
        layout_id=record.layout_id,
        system_slot_bytes=record.slot_bytes,
        boot_backend=record.boot_backend,
        persist_filesystem_uuid=persist_uuid,
        boot_control_filesystem_uuid=boot_uuid,
    )


def _bind_release_facts_to_policy(policy: object, manifest: UpdateManifest) -> object:
    """Bind the v3 release compatibility facts onto a profile policy.

    The v3 manifest is authoritative for ``architecture``/
    ``platform_family``/``profile``/``version``; layout facts
    (``layout_id``/slot bytes/boot backend) stay exactly as the caller's
    policy factory derived them. A plain non-``SlotProfilePolicy`` object
    from a custom factory is returned unchanged so test/harness seams keep
    their type.
    """
    from .slot_writer import SlotProfilePolicy

    if not isinstance(policy, SlotProfilePolicy):
        return policy
    return SlotProfilePolicy(
        layout_id=policy.layout_id,
        system_slot_bytes=policy.system_slot_bytes,
        boot_backend=policy.boot_backend,
        persist_filesystem_uuid=policy.persist_filesystem_uuid,
        boot_control_filesystem_uuid=policy.boot_control_filesystem_uuid,
        architecture=manifest.architecture,
        platform_family=manifest.platform_family,
        profile=manifest.profile,
        version=manifest.version,
    )


@dataclass(frozen=True, slots=True)
class UpdateSlotSeams:
    """Injectable destination seams for privileged update staging.

    Every factory is destination-scoped: the service never passes the active
    or accepted slot here (``DestinationSlot.resolve_from_layout`` re-proves
    that first). Unset factories fail closed at stage time with
    :class:`UpdateBackendUnavailable`, so a minimally composed service
    reports unavailable instead of guessing at destination access.
    ``installed_contract_factory`` is the PERSIST-side preflight: it returns
    the installed PERSIST schema marker bytes (see
    ``persistent_layout.emit_persist_schema_marker``) so staging can prove
    the current schema falls within the candidate's readable range
    (previously accepted slot keeps reading shared state) before any
    inactive-slot write. An int schema is also accepted for harness
    convenience and coerced through the same marker path.
    ``support_stage_cleanup`` closes the production context's current
    stage-owned candidate-support stage; the backend calls it in a
    ``finally`` so one stage's temp root is removed on success and on
    every failure path. Test/harness seams leave it unset (no stage).
    ``support_pool_factory`` returns the staged verified hardware-support
    pool (or ``None``) so staging can derive the selected-set installed
    capacity bound for exactly the resolved firmware/microcode; without a
    pool only an empty selection binds zero, anything selected refuses.

    An empty ``UpdateSlotSeams()`` stays a deliberate fail-closed degraded
    construction (direct ``SlotBackedSystemUpdateBackend`` default). It is
    never the installed A/B default: :func:`build_live_update_service`
    composes :func:`build_production_update_seams` when the caller supplies
    no explicit seams, while explicit seams remain a test/harness feature.
    """

    slot_store_factory: Callable[[object], object] | None = None
    filesystem_factory: Callable[[], object] | None = None
    package_installer_factory: Callable[[], object] | None = None
    inventory_factory: Callable[[], object] | None = None
    support_set_factory: Callable[[InspectedUpdateBundle], object] | None = None
    profile_policy_factory: Callable[[object], object] | None = None
    selection_factory: Callable[[object, str], object | None] | None = None
    installed_contract_factory: Callable[[], bytes] | None = None
    support_stage_cleanup: Callable[[], None] | None = None
    support_pool_factory: Callable[[InspectedUpdateBundle], object | None] | None = None


class SlotBackedSystemUpdateBackend:
    """Privileged staging/arm/confirm over the common slot/journal seams.

    Reuses :class:`SlotWriter`, :class:`SlotFinalizer` and
    :class:`BootTransactionJournal` as shared libraries: compatibility stays in
    :class:`SystemUpdateService` (structure, integrity, compatibility),
    while this backend owns the inactive slot, the destination seams, the
    journal and the boot-backend one-shot. Single-root layouts and missing
    records stay unavailable; the active/accepted slot is never writable
    through this object.
    """

    def __init__(
        self,
        state_dir: Path,
        *,
        layout_record_path: Path | None = None,
        seams: UpdateSlotSeams | None = None,
        boot_backend: object | None = None,
        journal_dir: Path | None = None,
    ) -> None:
        self.state_dir = Path(state_dir)
        configured_journal = os.environ.get(BOOT_JOURNAL_DIR_ENV, "").strip()
        if journal_dir is not None:
            self.journal_dir = Path(journal_dir)
        elif configured_journal:
            self.journal_dir = Path(configured_journal)
        elif self.state_dir == Path(UPDATE_STATE_DIR_DEFAULT):
            self.journal_dir = BOOT_JOURNAL_DIR_DEFAULT
        else:
            # Isolated fixtures use their temporary update-state tree unless
            # they explicitly inject the installed shared PERSIST journal.
            self.journal_dir = self.state_dir / "system-updates" / UPDATE_JOURNAL_DIR_NAME
        self.layout_record_path = (
            Path(layout_record_path)
            if layout_record_path is not None
            else installed_layout_record_path()
        )
        self.seams = seams if seams is not None else UpdateSlotSeams()
        self.boot_backend = boot_backend
        self._last_staged: dict[str, object] = {}

    @property
    def available(self) -> bool:
        try:
            record = load_installed_layout_record(self.layout_record_path)
        except UpdateLayoutError:
            return False
        return record is not None and record.system_b is not None

    def status_payload(self) -> dict[str, object]:
        try:
            record = load_installed_layout_record(self.layout_record_path)
        except UpdateLayoutError as exc:
            return {"available": False, "reason": str(exc)}
        if record is None or record.system_b is None:
            return {
                "available": False,
                "reason": "A/B system-slot backend is not configured",
            }
        payload: dict[str, object] = {"available": True}
        payload.update(self._last_staged)
        try:
            journal = self._load_journal()
        except SystemUpdateError:
            return payload
        if journal is not None:
            payload["journal_state"] = journal.state.value
            payload["candidate_slot"] = journal.candidate_slot
            payload["release_id"] = journal.release_id
        return payload

    def _selected_support_installed_bytes(
        self,
        bundle: InspectedUpdateBundle,
        firmware: tuple[str, ...],
        microcode: tuple[str, ...],
    ) -> int:
        """Verified installed-size bound for exactly the selected sets.

        Resolves the staged pool through the ``support_pool_factory`` seam
        (same open stage the support set came from; no second extraction)
        and sums its verified per-package sizes over the union of the
        selected dependency closures. Without a staged pool only an empty
        selection binds zero bytes; anything selected refuses fail-closed
        instead of falling back to the whole-pool total.
        """
        pool = None
        if self.seams.support_pool_factory is not None:
            try:
                pool = self.seams.support_pool_factory(bundle)
            except UpdateBackendUnavailable:
                raise
            except Exception as exc:
                raise UpdateBackendUnavailable(
                    f"release support pool is unavailable: {exc}"
                ) from exc
        if pool is None:
            if firmware or microcode:
                raise SystemUpdateError(
                    "support pool is unavailable for the selected capacity bound"
                )
            return 0
        try:
            bound = pool.selected_installed_bytes(firmware, microcode)
        except AttributeError as exc:
            raise SystemUpdateError(
                "staged support pool cannot prove a selected capacity bound"
            ) from exc
        except Exception as exc:
            raise SystemUpdateError(
                f"selected support capacity bound is not authoritative: {exc}"
            ) from exc
        if isinstance(bound, bool) or not isinstance(bound, int) or bound < 0:
            raise SystemUpdateError(
                "selected support capacity bound is not authoritative"
            )
        return bound

    def stage(self, bundle: InspectedUpdateBundle) -> None:
        """Stage the v3 candidate into the inactive slot (ADR 0036 §4/§8).

        Compatibility (architecture/platform/profile/board) is established by
        :class:`SystemUpdateService` before this call; this method enforces
        the PERSIST readability range and destination capacity plus the
        release-bound support binding before any destination contact, then
        streams zstd decompression through the shared ``SlotWriter`` (raw
        byte-count proof, fsync/readback, no uncompressed temp file) and
        records the shared journal with the non-security release identity.
        There is no signature verification and no anti-rollback sequence
        requirement. Any refusal raises before the first destination mutation.
        """
        from .boot_transaction import BootJournalError, BootTransactionError, BootTransactionJournal
        from .slot_writer import (
            DestinationSlot,
            SlotFinalizeError,
            SlotFinalizer,
            SlotWriteError,
            SlotWriter,
            VerifiedReleaseMember,
            open_zstd_decompressed_stream,
        )

        try:
            record = self._require_ab_record()
            accepted = record.accepted_slot or record.boot_control.active_slot
            if accepted not in ("A", "B"):
                raise UpdateBackendUnavailable(
                    "update backend has no accepted slot to update from"
                )
            inactive = inactive_slot_for(record)
            if inactive is None:  # pragma: no cover - guarded by _require_ab_record
                raise UpdateBackendUnavailable(
                    "A/B system-slot backend is not configured"
                )
            destination = DestinationSlot.resolve_from_layout(record, inactive)
            member = VerifiedReleaseMember.from_manifest(bundle.manifest)
            # Fail fast before any destination contact: an already-active
            # transaction must be reconciled or confirmed first, and a
            # foreign support set never reaches the slot seam.
            self._refuse_active_transaction()
            support = self._require_seam("release support set", self.seams.support_set_factory)
            support_value = support(bundle)
            if getattr(support_value, "support_digest", None) != member.hardware_support_sha256:
                raise SystemUpdateError(
                    "support set is not the release-bound support member"
                )
            if getattr(support_value, "support_size", None) != member.hardware_support_size:
                raise SystemUpdateError(
                    "support set size is not the release-bound member size"
                )
            # PERSIST readability preflight (integer schema range, ADR 0036 §6)
            # before any inactive-slot store is addressed.
            installed_marker = self._require_seam(
                "installed PERSIST schema",
                self.seams.installed_contract_factory,
            )()
            try:
                _assert_persist_preflight(installed_marker, bundle.manifest)
            except SystemUpdateError:
                raise
            except Exception as exc:
                raise SystemUpdateError(
                    f"PERSIST compatibility preflight refused: {exc}"
                ) from exc
            # Inventory attestation, policy/filesystem/installer seams and
            # hardware selection resolve before any destination contact and
            # before the capacity proof, so the support term below covers
            # exactly the firmware/microcode this staging will install.
            inventory = self._require_seam(
                "hardware inventory attestation", self.seams.inventory_factory
            )()
            policy_factory = (
                self.seams.profile_policy_factory or _default_slot_profile_policy
            )
            policy = _bind_release_facts_to_policy(
                policy_factory(record), bundle.manifest
            )
            filesystem = self._require_seam("slot filesystem", self.seams.filesystem_factory)()
            package_installer = self._require_seam(
                "slot package installer", self.seams.package_installer_factory
            )()
            selection = None
            firmware: tuple[str, ...] = ()
            microcode: tuple[str, ...] = ()
            if self.seams.selection_factory is not None:
                selection = self.seams.selection_factory(
                    support_value, str(getattr(inventory, "token", ""))
                )
                if selection is not None:
                    firmware = tuple(selection.firmware)
                    microcode = tuple(selection.microcode)
            # Destination capacity preflight before the first destination
            # mutation: the single-owner finalized-slot capacity bound (T02:
            # ``greia_installer.layout.require_finalized_slot_capacity``,
            # the same bound ``SlotWriter`` enforces at write time and the
            # finalizer re-checks) refuses an over-full support-carrying
            # candidate before the first destination mutation. The support
            # term is the verified selected-set bound for exactly the
            # firmware/microcode resolved above — never the whole-pool
            # total, which reserves every candidate the release merely
            # carries. No second formula lives here.
            selected_installed = self._selected_support_installed_bytes(
                bundle, firmware, microcode
            )
            try:
                from greia_installer.layout import (
                    LayoutError,
                    require_finalized_slot_capacity,
                )

                require_finalized_slot_capacity(
                    slot_bytes=destination.slot_capacity_bytes,
                    base_bytes=member.payload_uncompressed_bytes,
                    minimum_slot_bytes=member.minimum_slot_bytes,
                    support_installed_bytes=selected_installed,
                )
            except LayoutError as exc:
                raise SystemUpdateError(
                    f"destination slot capacity preflight refused: {exc}"
                ) from exc
            writer = SlotWriter()
            # The backend owns the store lifetime: it is closed on every path
            # once the verified range is written, so loop files and later
            # partition handles are never leaked across operations.
            storage: object = None  # type: ignore[assignment]
            try:
                storage = self._require_seam(
                    "inactive-slot store", self.seams.slot_store_factory
                )(destination)
                with zipfile.ZipFile(bundle.path, "r") as archive:
                    with archive.open(PAYLOAD_NAME, "r") as compressed:
                        try:
                            decompressed = open_zstd_decompressed_stream(compressed)
                        except (SlotWriteError, SlotFinalizeError) as exc:
                            raise SystemUpdateError(
                                f"payload decompression refused: {exc}"
                            ) from exc
                        try:
                            verified = writer.write(
                                member=member,
                                destination=destination,
                                source=decompressed,
                                storage=storage,
                                support_installed_bytes=selected_installed,
                            )
                        except (SlotWriteError, SlotFinalizeError) as exc:
                            if isinstance(exc, SystemUpdateError):
                                raise
                            raise SystemUpdateError(
                                f"update staging failed fail-closed: {exc}"
                            ) from exc
                        finally:
                            closer = getattr(decompressed, "close", None)
                            if callable(closer):
                                try:
                                    closer()
                                except Exception:
                                    pass
            finally:
                closer = getattr(storage, "close", None)
                if callable(closer):
                    try:
                        closer()
                    except OSError:
                        pass
            receipt = SlotFinalizer().finalize(
                write=verified,
                destination=destination,
                filesystem=filesystem,
                package_installer=package_installer,
                inventory=inventory,
                support=support_value,
                profile_policy=policy,
                firmware_packages=firmware,
                microcode_packages=microcode,
                selection=selection,
                support_installed_bytes=selected_installed,
            )
            BootTransactionJournal.begin_update(
                self.journal_dir,
                layout_id=record.layout_id,
                boot_backend=record.boot_backend,
                release_id=receipt.release_id,
                candidate_slot=inactive,
                accepted_slot=accepted,
            )
            self._last_staged = {
                "candidate_slot": inactive,
                "release_id": receipt.release_id,
            }
        except (SlotWriteError, SlotFinalizeError, BootTransactionError, BootJournalError) as exc:
            if isinstance(exc, SystemUpdateError):
                raise
            raise SystemUpdateError(f"update staging failed fail-closed: {exc}") from exc
        finally:
            # One stage owns one support stage: the temp root is removed on
            # success and on every failure path (selection failure,
            # installation failure, capacity refusal). Test/harness seams
            # leave the hook unset. Cleanup never masks the stage outcome.
            closer = getattr(self.seams, "support_stage_cleanup", None)
            if callable(closer):
                try:
                    closer()
                except Exception:
                    pass

    def arm(self) -> dict[str, object]:
        """Arm the staged candidate one-shot (SCHEDULE phase)."""
        from .boot_transaction import (
            BootTransactionError,
            BootTransactionJournal,
            BootTransactionState,
        )

        try:
            journal = self._require_staged_journal()
            if journal.state is not BootTransactionState.UPDATE_STAGED:
                raise SystemUpdateError(
                    f"update transaction is {journal.state.value}, not staged"
                )
            backend = self._require_boot_backend()
            backend.arm_one_shot(journal.candidate_slot)
            journal.record(
                BootTransactionState.ONE_SHOT_ARMED,
                "candidate one-shot armed by the update service",
            )
        except BootTransactionError as exc:
            raise SystemUpdateError(f"update arm failed fail-closed: {exc}") from exc
        return {"armed": True, "slot": journal.candidate_slot}

    def confirm_boot_health(self) -> dict[str, object]:
        """Commit or roll back from the authoritative boot observation.

        A health commit additionally advances the trusted layout authority
        to the candidate (accepted slot/release follow the journal), so the
        next sequenced update resolves the other inactive slot. The
        advancement is idempotent: an already-converged record is returned
        unchanged, and a record that drifted unexpectedly fails closed.
        """
        from .boot_transaction import (
            BootTransactionError,
            BootTransactionJournal,
            BootTransactionState,
        )

        try:
            journal = self._require_staged_journal()
            if journal.is_terminal:
                if journal.state is BootTransactionState.ACCEPTED:
                    self._advance_layout_authority(journal)
                return {
                    "confirmed": journal.state is BootTransactionState.ACCEPTED,
                    "state": journal.state.value,
                    "booted_slot": None,
                }
            backend = self._require_boot_backend()
            observed = backend.observe_booted_slot()
            decision = journal.reconcile(observed)
            if decision.transition is not None:
                journal.record(decision.transition, _bounded_note(decision.explanation))
            if (
                journal.state is BootTransactionState.CANDIDATE_BOOTING
                and observed == journal.candidate_slot
            ):
                backend.commit_accepted(journal.candidate_slot)
                # v3 carries no anti-rollback sequence file: acceptance follows
                # the journal/layout release identity only (T02).
                journal.record(
                    BootTransactionState.ACCEPTED,
                    "candidate boot confirmed healthy; release accepted",
                )
                self._advance_layout_authority(journal)
        except BootTransactionError as exc:
            raise SystemUpdateError(f"update confirm failed fail-closed: {exc}") from exc
        return {
            "confirmed": journal.state is BootTransactionState.ACCEPTED,
            "state": journal.state.value,
            "booted_slot": observed,
        }

    def reconcile(self) -> dict[str, object]:
        """Crash-reconcile the shared journal (A8-FAULTS harness seam)."""
        from .boot_transaction import BootTransactionError, BootTransactionJournal

        try:
            journal = self._require_staged_journal()
            observed: str | None = None
            if self.boot_backend is not None:
                observed = self.boot_backend.observe_booted_slot()
            decision = journal.reconcile(observed)
            if decision.transition is not None:
                journal.record(decision.transition, _bounded_note(decision.explanation))
        except BootTransactionError as exc:
            raise SystemUpdateError(
                f"update reconcile failed fail-closed: {exc}"
            ) from exc
        return {
            "reconciled": True,
            "state": journal.state.value,
            "booted_slot": observed,
            "explanation": decision.explanation,
        }

    def _require_ab_record(self) -> "_LayoutRecord":
        record = load_installed_layout_record(self.layout_record_path)
        if record is None or record.system_b is None:
            raise UpdateBackendUnavailable(
                "A/B system-slot backend is not configured"
            )
        return record

    def _require_seam(self, name: str, factory: Callable[..., object] | None) -> Callable[..., object]:
        if factory is None:
            raise UpdateBackendUnavailable(
                f"inactive-slot destination seam is not configured: {name}"
            )
        return factory

    def _require_boot_backend(self) -> object:
        if self.boot_backend is None:
            raise UpdateBackendUnavailable("boot backend is not wired")
        return self.boot_backend

    def _load_journal(self) -> "_Journal | None":
        from .boot_transaction import (
            JOURNAL_FILE_NAME,
            BootJournalError,
            BootTransactionJournal,
        )

        candidate = Path(self.journal_dir) / JOURNAL_FILE_NAME
        if candidate.is_symlink():
            raise SystemUpdateError("update journal must not be a symlink")
        if not candidate.is_file():
            return None
        try:
            return BootTransactionJournal.load(self.journal_dir)
        except BootJournalError as exc:
            raise SystemUpdateError(
                f"update journal is not authoritative: {exc}"
            ) from exc
        except OSError as exc:
            raise SystemUpdateError("update journal is unreadable") from exc

    def _require_staged_journal(self) -> "_Journal":
        journal = self._load_journal()
        if journal is None:
            raise SystemUpdateError("no staged update transaction")
        return journal

    def _refuse_active_transaction(self) -> None:
        journal = self._load_journal()
        if journal is not None and not journal.is_terminal:
            raise SystemUpdateError(
                "an update transaction is already active; "
                "reconcile or confirm it before staging"
            )

    def _advance_layout_authority(self, journal: "_Journal") -> None:
        """Advance the trusted layout record to a health-committed journal."""
        advance_layout_authority_for_acceptance(
            self.layout_record_path,
            candidate_slot=journal.candidate_slot,
            accepted_slot=journal.accepted_slot,
            release_id=journal.release_id,
        )


def advance_layout_authority_for_acceptance(
    layout_record_path: Path,
    *,
    candidate_slot: str,
    accepted_slot: str,
    release_id: str,
) -> "_LayoutRecord":
    """Advance the trusted A/B layout authority after a health commit.

    Step 8B.4 sequenced updates (A→B→A) require this: the next stage
    resolves its inactive slot from the record, so without advancement the
    second update would re-target the just-accepted slot instead of the
    other one. The rewrite is atomic (write-temp/fsync/rename, owner-only
    mode) and idempotent: when the record already accepts this candidate
    release it is returned unchanged. Any unexpected authority drift fails
    closed without touching the record.
    """
    from dataclasses import replace as _replace

    from .persistent_layout import InstalledLayoutRecord, PersistentLayoutError

    if candidate_slot not in ("A", "B") or accepted_slot not in ("A", "B"):
        raise SystemUpdateError("layout advancement requires semantic slots A/B")
    if candidate_slot == accepted_slot:
        raise SystemUpdateError(
            "layout advancement requires a candidate distinct from accepted"
        )
    try:
        record = load_installed_layout_record(Path(layout_record_path))
    except UpdateLayoutError as exc:
        raise SystemUpdateError(
            f"layout authority is not authoritative: {exc}"
        ) from exc
    if record is None or record.system_b is None:
        raise SystemUpdateError("layout advancement requires an A/B layout authority")
    if record.accepted_slot == candidate_slot:
        if record.accepted_release_id != release_id:
            raise SystemUpdateError(
                "layout authority already accepts a different release "
                "for this slot; refusing to advance"
            )
        if record.boot_control.active_slot != candidate_slot:
            raise SystemUpdateError(
                "layout authority accepted slot disagrees with boot control; "
                "refusing to advance"
            )
        return record
    if record.accepted_slot != accepted_slot:
        raise SystemUpdateError(
            "layout authority moved under the accepted transaction; "
            "refusing to advance"
        )
    advanced = _replace(
        record,
        accepted_slot=candidate_slot,
        accepted_release_id=release_id,
        boot_control=_replace(record.boot_control, active_slot=candidate_slot),
    )
    try:
        InstalledLayoutRecord.from_dict(advanced.as_dict())
    except PersistentLayoutError as exc:
        raise SystemUpdateError(
            f"advanced layout authority is not authoritative: {exc}"
        ) from exc
    try:
        advanced.write_to(Path(layout_record_path))
    except OSError as exc:
        raise SystemUpdateError(
            f"layout authority advancement failed: {exc}"
        ) from exc
    try:
        reloaded = load_installed_layout_record(Path(layout_record_path))
    except UpdateLayoutError as exc:
        raise SystemUpdateError(
            f"advanced layout authority is unreadable: {exc}"
        ) from exc
    if reloaded is None:
        raise SystemUpdateError("advanced layout authority is missing")
    return reloaded


def _bounded_note(note: str, maximum: int = 512) -> str:
    raw = note if isinstance(note, str) and note else "update journal transition"
    encoded = raw.encode("utf-8")[:maximum].decode("utf-8", "ignore")
    return encoded or "update journal transition"


@dataclass(frozen=True, slots=True)
class UpdateCandidateSummary:
    """Bounded public facts for the internally resolved inbox candidate.

    v3 carries no provenance: integrity (digests) is verified at inspection,
    and only the non-security release identity plus the bundle digest are
    reported. Shares the v3-minimal shape with
    ``update_privileged.CurrentCandidateSummary`` (``present``/``release_id``/
    ``bundle_sha256``); both are owned by their module and carry no release
    sequence, signer, or signature-verification fact.
    """

    present: bool
    release_id: str = ""
    bundle_sha256: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.present, bool):
            raise SystemUpdateError("candidate presence must be a boolean")
        if len(self.release_id) > 96:
            raise SystemUpdateError("candidate release_id exceeds Greia bound")
        if self.bundle_sha256 and (
            len(self.bundle_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.bundle_sha256)
        ):
            raise SystemUpdateError("candidate bundle digest is outside Greia bounds")


@dataclass
class SystemUpdateServiceAuthority:
    """Privileged operation owner behind the socket-activated endpoint.

    Implements the ``UpdatePrivilegedAuthority`` seam structurally: every
    method resolves the current inbox candidate, the trusted layout and the
    journal internally. Request bytes carry no paths, slots, digests,
    devices, URLs or commands.
    """

    state_dir: Path
    identity: SystemIdentity
    backend: SystemUpdateBackend | None = None
    service: SystemUpdateService = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "state_dir", Path(self.state_dir))
        if self.backend is None:
            object.__setattr__(
                self, "backend", SlotBackedSystemUpdateBackend(self.state_dir)
            )
        object.__setattr__(
            self,
            "service",
            SystemUpdateService(
                self.state_dir,
                self.identity,
                self.backend,
            ),
        )

    def candidate_summary(self) -> UpdateCandidateSummary:
        try:
            path = self._current_bundle_path()
            manifest = _read_candidate_manifest_summary(path)
        except (SystemUpdateError, OSError, zipfile.BadZipFile):
            return UpdateCandidateSummary(present=False)
        return UpdateCandidateSummary(
            present=True,
            release_id=manifest.release_id,
        )

    def layout_summary(self) -> dict[str, object]:
        try:
            record = load_installed_layout_record(
                self._backend_layout_path(),
            )
        except UpdateLayoutError:
            record = None
        if record is None or record.system_b is None:
            return {
                "single_root": True,
                "slots": ["A"],
                "active_slot": None,
                "accepted_slot": None,
            }
        return {
            "single_root": False,
            "slots": ["A", "B"],
            "active_slot": record.boot_control.active_slot,
            "accepted_slot": record.accepted_slot,
        }

    def verify_current_candidate(self) -> UpdateCandidateSummary:
        path = self._current_bundle_path()
        inspected, _decision = self.service.verify_for_activation(path)
        return UpdateCandidateSummary(
            present=True,
            release_id=inspected.manifest.release_id,
            bundle_sha256=sha256_file(path),
        )

    def stage_current_candidate(self) -> dict[str, object]:
        path = self._current_bundle_path()
        inspected, decision = self.service.verify_for_activation(path)
        staged = self.service.stage(path)
        detail: dict[str, object] = {
            "staged": True,
            "decision": decision,
            "release_id": staged.manifest.release_id,
        }
        _ = inspected
        detail.update(self.service.backend.status_payload())
        return detail

    def arm_current_candidate(self) -> dict[str, object]:
        return self.service.arm()

    def confirm_boot_health(self) -> dict[str, object]:
        return self.service.confirm_boot_health()

    def reconcile(self) -> dict[str, object]:
        return self.service.reconcile()

    def status_payload(self) -> dict[str, object]:
        from .update_activation import InstalledUpdateActivation

        return InstalledUpdateActivation(self).status_payload()

    def request_restart(self) -> dict[str, object]:
        from .update_activation import InstalledUpdateActivation

        return InstalledUpdateActivation(self).request_restart()

    def _backend_layout_path(self) -> Path | None:
        backend = self.backend
        path = getattr(backend, "layout_record_path", None)
        return Path(path) if path is not None else None

    def _current_bundle_path(self) -> Path:
        """Resolve only the fixed inbox candidate, independent of status data."""
        inbox = SystemUpdateInbox(self.state_dir)
        candidate = inbox.candidate_path
        try:
            base = inbox.inbox_dir.resolve(strict=True)
            info = candidate.lstat()
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(base)
        except (OSError, ValueError) as exc:
            raise SystemUpdateError("update candidate is not an inbox file") from exc
        if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise SystemUpdateError("update candidate is not a regular inbox file")
        if info.st_size <= 0 or info.st_size > MAX_BUNDLE_BYTES:
            raise SystemUpdateError("update candidate size is outside Greia bounds")
        return resolved


def _read_candidate_manifest_summary(path: Path) -> UpdateManifest:
    """Read bounded candidate identity for status without streaming payloads.

    This is only a fast availability summary. Activation still goes through
    ``inspect_update_bundle`` which verifies every declared member digest and
    package invariant before any slot operation.
    """

    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise UpdateBundleError("update bundle is not a regular file")
    size = candidate.stat().st_size
    if size <= 0 or size > MAX_BUNDLE_BYTES:
        raise UpdateBundleError("update bundle size is outside Greia bounds")
    try:
        with zipfile.ZipFile(candidate, "r") as archive:
            names = archive.namelist()
            if names not in (list(BUNDLE_MEMBERS_V3), list(BUNDLE_MEMBERS_V3_WITH_HW)):
                raise UpdateBundleError("update bundle members/order are invalid")
            info = archive.getinfo(MANIFEST_NAME)
            if info.file_size <= 0 or info.file_size > MAX_MANIFEST_BYTES:
                raise UpdateBundleError("manifest exceeds Greia bound")
            raw = archive.read(MANIFEST_NAME)
    except (zipfile.BadZipFile, OSError) as exc:
        raise UpdateBundleError("update bundle is not a valid Greia ZIP artifact") from exc
    try:
        manifest = UpdateManifest.from_json_dict(json.loads(raw.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateBundleError("manifest is not valid JSON") from exc
    if raw != manifest.canonical_bytes():
        raise UpdateBundleError("manifest is not canonical JSON")
    return manifest


# ---------------------------------------------------------------------------
# Socket-activated serving (one framed request per connection)
# ---------------------------------------------------------------------------


def resolve_grubenv_dir() -> Path:
    """Resolve the boot-control directory holding the production grubenv."""
    override = os.environ.get(UPDATE_GRUBENV_DIR_ENV, "").strip()
    return Path(override) if override else Path(UPDATE_GRUBENV_DIR_DEFAULT)


def production_boot_backend() -> object | None:
    """Attach the production one-shot backend when its state exists.

    Returns a ``GrubEnvBackend`` attached to the boot-control ``grubenv``
    block when present and parseable, else None: without boot-control state
    there is nothing to arm, so arm/confirm stay fail-closed unavailable
    instead of guessing at boot control.
    """
    from .boot_transaction import BootTransactionError
    from .grub_ab import GrubAbConfigError, GrubEnvBackend

    try:
        return GrubEnvBackend.attach(resolve_grubenv_dir())
    except (BootTransactionError, GrubAbConfigError, OSError, ValueError):
        return None


def attest_peer_from_connection(connection: socket.socket) -> "PeerCredential":
    """Attest the Unix peer from ``SO_PEERCRED`` (kernel fact, never bytes).

    The uid/pid come from the kernel's socket credential, so a peer cannot
    assert a different identity through request content. Any failure to
    attest fails closed: the connection carries no servable request.
    """
    import struct

    from .privileged_channel import PeerCredential, PrivilegedChannelError

    peer_credibility = getattr(socket, "SO_PEERCRED", None)
    if peer_credibility is None:
        raise PrivilegedChannelError(
            "peer credential is not attestable on this platform"
        )
    try:
        raw = connection.getsockopt(
            socket.SOL_SOCKET,
            peer_credibility,
            struct.calcsize("3i"),
        )
    except OSError as exc:
        raise PrivilegedChannelError(
            f"peer credential is not attestable: {exc}"
        ) from exc
    try:
        _pid, uid, _gid = struct.unpack("3i", raw)
    except struct.error as exc:
        raise PrivilegedChannelError(
            "peer credential is not attestable"
        ) from exc
    return PeerCredential(uid=int(uid))


def handle_update_connection(
    connection: socket.socket,
    *,
    authority: SystemUpdateServiceAuthority,
    peer: "PeerCredential",
    boot_state: str = "update_ready",
) -> None:
    """Answer exactly one framed update request on an accepted connection.

    The protocol owner stays ``greia_platform.update_privileged`` (imported
    here, at the composition edge, because that module imports this one).
    ``peer`` must be a kernel-attested ``PeerCredential`` (see
    :func:`attest_peer_from_connection`): caller-supplied UIDs or identity
    text are rejected before any request byte is read. Any refusal — peer, boot, schema, trust,
    slot, journal — is answered as a bounded REFUSED frame with no
    destination contact on the way out.
    """
    from .privileged_channel import (
        MAX_MESSAGE_BYTES,
        PeerCredential,
        PrivilegedChannelError,
        encode_response,
        new_transaction_id,
    )
    from .update_privileged import UpdatePrivilegedEndpoint, UpdatePrivilegedError

    try:
        from .boot_transaction import BootTransactionError
        from .slot_writer import SlotFinalizeError, SlotWriteError
    except ImportError:  # pragma: no cover - platform seams always present
        BootTransactionError = RuntimeError  # type: ignore[assignment]
        SlotFinalizeError = RuntimeError  # type: ignore[assignment]
        SlotWriteError = RuntimeError  # type: ignore[assignment]

    if not isinstance(peer, PeerCredential):
        response = encode_response(
            new_transaction_id(),
            "ERROR",
            {"status": "REFUSED", "reason": "peer credential must be attested, never asserted"},
        )
        connection.sendall(response)
        try:
            connection.close()
        except OSError:
            pass
        return
    try:
        connection.settimeout(10.0)
        chunks: list[bytes] = []
        received = 0
        while True:
            chunk = connection.recv(4096)
            if not chunk:
                break
            received += len(chunk)
            if received > MAX_MESSAGE_BYTES:
                raise UpdatePrivilegedError("request exceeds Greia bound")
            chunks.append(chunk)
            if chunk.endswith(b"\n"):
                break
        raw = b"".join(chunks)
        try:
            import pwd

            panel_uid = pwd.getpwnam("greiapanel").pw_uid
        except (ImportError, KeyError):
            panel_uid = None
        allowed_uids = (0,) if panel_uid is None or panel_uid == 0 else (0, panel_uid)
        endpoint = UpdatePrivilegedEndpoint(
            authority,  # type: ignore[arg-type]
            allowed_uids=allowed_uids,
            root_uid=0,
            panel_uid=panel_uid,
        )
        response = endpoint.handle_request(raw, peer=peer, boot_state=boot_state)
    except (
        UpdatePrivilegedError,
        SystemUpdateError,
        PrivilegedChannelError,
        SlotWriteError,
        SlotFinalizeError,
        BootTransactionError,
    ) as exc:
        response = encode_response(
            new_transaction_id(), "ERROR", {"status": "REFUSED", "reason": str(exc)[:256]}
        )
    connection.sendall(response)
    try:
        connection.close()
    except OSError:
        pass


# ---------------------------------------------------------------------------
# P3.2 production UpdateSlotSeams (installed A/B default)
# ---------------------------------------------------------------------------
# The factories below are the exact installed updater's destination path:
# every device address derives from the trusted ``InstalledLayoutRecord``
# plus freshly re-observed topology at factory-call time, never from a
# caller path. They reuse the shared primitives owner
# (``greia_platform.block_slots``: authoritative role->device resolution,
# device-backed ``SlotStorage``/``SlotFilesystem``, installer-path package
# reuse) and the shared ``SlotWriter``/``SlotFinalizer`` staging order. No
# second writer, finalizer, device-storage class or loop/file destination
# store is created here: ``LoopbackSlotFile`` stays a test stand-in behind
# explicitly injected seams, never the installed default.
#
# Construction performs no device IO: :func:`build_production_update_seams`
# only binds closures over deployment parameters. Every observation (layout
# record reload, udev PARTUUID map, blkid probes, size/disk re-observation,
# pool load, inventory snapshot) happens inside the factory call, so a
# stale pre-captured topology can never satisfy resolution. Factories fail
# closed with :class:`UpdateBackendUnavailable` when the A/B authority or
# the inactive device is unavailable; inventory/selection mismatches keep
# their ``SlotFinalizeError``/``SystemUpdateError`` shape so ``stage``
# wraps them as staging failures, never as silent skips.
#
# Integration notes (image integration contract):
# - the candidate's own ``hardware-support.tar.zst`` member is the
#   finalization authority (Repair D): it is materialized by
#   ``greia_platform.candidate_support`` into a temp root on the update
#   service's writable area, verified at load (manifest/payload digests,
#   no unmanifested payloads) and converted with the release manifest
#   digest/size, so the support set stays release-bound to the bytes the
#   candidate actually carries. The running image pool (default
#   ``/opt/greia-hardware-support``, same location the installer consumes)
#   remains for running-system purposes only and never satisfies candidate
#   finalization;
# - the installed persistent-state contract is the canonical registry
#   contract (identical bytes the release builder embeds); staging proves
#   the candidate binds it before any inactive-slot write;
# - the hardware inventory is a fresh sysfs snapshot attested complete;
#   an incomplete inventory refuses finalization instead of staging blind.


@dataclass(frozen=True, slots=True)
class _ProductionUpdatePaths:
    """One fresh read of the production seam deployment parameters.

    ``by_partuuid_dir`` is None when undeployed: callers then use the bare
    ``block_slots`` reader whose installed udev default that module owns.
    ``hardware_support_pool`` is the running image's pool for
    running-system purposes only (live/installer use); candidate
    finalization never loads it (see ``candidate_support``).
    """

    dev_root: Path
    by_partuuid_dir: Path | None
    mount_root: Path
    hardware_support_pool: Path
    sysfs_devices: Path


def _production_paths() -> _ProductionUpdatePaths:
    """Read the seam deployment parameters (fresh on every composition)."""
    by_partuuid_override = os.environ.get(UPDATE_BY_PARTUUID_DIR_ENV, "").strip()
    return _ProductionUpdatePaths(
        dev_root=_update_env_path(UPDATE_DEV_ROOT_ENV, UPDATE_DEV_ROOT_DEFAULT),
        by_partuuid_dir=Path(by_partuuid_override) if by_partuuid_override else None,
        mount_root=_update_env_path(UPDATE_MOUNT_ROOT_ENV, UPDATE_MOUNT_ROOT_DEFAULT),
        hardware_support_pool=_update_env_path(
            UPDATE_HARDWARE_SUPPORT_POOL_ENV, UPDATE_HARDWARE_SUPPORT_POOL_DEFAULT
        ),
        sysfs_devices=_update_env_path(
            UPDATE_SYSFS_DEVICES_ENV, UPDATE_SYSFS_DEVICES_DEFAULT
        ),
    )


def _update_env_path(name: str, default: str) -> Path:
    override = os.environ.get(name, "").strip()
    return Path(override) if override else Path(default)


def _candidate_staging_parent(context: _ProductionUpdateContext) -> Path:
    """Greia-owned staging parent for the candidate support materializer.

    The update service's writable area (``state_dir``) owns staging; test
    compositions without one fall back to the layout record's disposable
    parent, never to a shared system temp dir.
    """
    from .candidate_support import staging_parent_for

    if context.state_dir is not None:
        return staging_parent_for(Path(context.state_dir))
    return staging_parent_for(Path(context.layout_record_path).parent)


def _support_stage_identity(bundle: object) -> tuple[str, str | None, int | None, int | None]:
    """Bundle identity a support stage is bound to (restage comparison)."""
    manifest = getattr(bundle, "manifest", None)
    return (
        str(getattr(bundle, "path", "")),
        getattr(manifest, "hardware_support_sha256", None),
        getattr(manifest, "hardware_support_size", None),
        getattr(manifest, "hardware_support_extracted_bytes_bound", None),
    )


def _acquire_support_stage(context: _ProductionUpdateContext, bundle: object) -> object:
    """Return the stage-owned support stage for this bundle (one extraction).

    The first call for a candidate opens exactly one
    ``CandidateSupportStage`` (metadata inspection, PERSIST preflight,
    single streaming extraction, single verified pool load) and keeps it
    on the context so the support-set factory and the lazy package
    installer of the same stage share the identical pool instance. A
    repeat call for the same candidate reuses the open stage without a
    second extraction; a different candidate closes the previous stage
    first so no stale pool survives a restage. A null manifest support
    declaration closes any open stage and returns ``None`` without
    opening a new stage.
    """
    from .candidate_support import CandidateSupportStage

    manifest = getattr(bundle, "manifest", None)
    if manifest is None or getattr(manifest, "hardware_support_sha256", None) is None:
        _close_support_stage(context)
        return None
    identity = _support_stage_identity(bundle)
    current = context.support_stage
    if current is not None and isinstance(current, CandidateSupportStage):
        if not current.closed and current.stage_identity() == identity:
            return current
    _close_support_stage(context)
    stage = CandidateSupportStage.open(
        Path(getattr(bundle, "path")),
        manifest,
        _candidate_staging_parent(context),
    )
    context.support_stage = stage
    return stage


def _close_support_stage(context: _ProductionUpdateContext) -> None:
    """Close and forget the current support stage (cleanup never raises)."""
    stage = context.support_stage
    context.support_stage = None
    if stage is None:
        return
    closer = getattr(stage, "close", None)
    if callable(closer):
        try:
            closer()
        except Exception:
            pass


def _bounded_reason(exc: BaseException, maximum: int = 200) -> str:
    raw = str(exc) if str(exc) else exc.__class__.__name__
    encoded = raw.encode("utf-8")[:maximum].decode("utf-8", "ignore")
    return encoded or exc.__class__.__name__


@dataclass
class _ProductionUpdateContext:
    """Mutable per-service cell shared by one set of production factories.

    Holds no device state at construction. Deployment parameters are
    captured once at composition (same model as the state/key/layout paths
    above); every observation (layout record reload, udev PARTUUID map,
    blkid probes, size/disk re-observation, pool load, inventory snapshot)
    still happens inside each factory call, so a stale pre-captured
    topology can never satisfy resolution. ``filesystem_tracker`` and
    ``mounted`` are populated by the filesystem/package-installer factories
    during a stage so the lazy package installer addresses exactly the
    mounted inactive slot the finalizer owns; they are refreshed on every
    filesystem-factory call, so a restage after rollback cannot reuse a
    stale mountpoint. ``state_dir`` is the update service's writable area
    owning candidate-support staging; ``support_stage`` is the one
    stage-owned ``CandidateSupportStage`` of the current stage (single
    streaming extraction, single verified pool instance shared by the
    support-set factory and the lazy package installer of the same
    stage). A restage with a different candidate closes the previous
    stage first, so no stale pool survives across restages, and the
    backend ``finally`` (via the ``support_stage_cleanup`` seam) closes
    the stage on success and on every failure path.
    """

    layout_record_path: Path
    paths: _ProductionUpdatePaths
    state_dir: Path | None = None
    support_stage: object | None = None
    filesystem_tracker: "_MountTrackingFilesystem | None" = None
    mounted: list[Path] = field(default_factory=list)


def _require_production_ab_record(layout_record_path: Path) -> "_LayoutRecord":
    """Reload the trusted A/B record fresh (fail closed without authority)."""
    try:
        record = load_installed_layout_record(Path(layout_record_path))
    except UpdateLayoutError as exc:
        raise UpdateBackendUnavailable(
            f"inactive-slot destination is unavailable: {exc}"
        ) from exc
    if record is None or record.system_b is None:
        raise UpdateBackendUnavailable(
            "A/B system-slot backend is not configured"
        )
    return record


def _production_primitives(
    record: "_LayoutRecord", paths: _ProductionUpdatePaths
) -> object:
    """Bind the shared primitives to fresh production observers (no IO yet)."""
    from .block_slots import (
        SubprocessBlockFilesystemRunner,
        SharedBlockSlotPrimitives,
        blkid_device_partuuid,
    )

    runner = SubprocessBlockFilesystemRunner()

    def _observe_topology() -> object:
        return _observe_production_topology(
            record,
            dev_root=paths.dev_root,
            by_partuuid_dir=paths.by_partuuid_dir,
            filesystem_runner=runner,
        )

    def _read_map() -> dict[str, str]:
        return _read_production_partuuid_map(paths.by_partuuid_dir)

    return SharedBlockSlotPrimitives(
        record=record,
        observe_topology=_observe_topology,  # type: ignore[arg-type]
        read_partuuid_map=_read_map,
        probe_device_partuuid=blkid_device_partuuid,
        dev_root=paths.dev_root,
        filesystem_runner=runner,
        mount_root=paths.mount_root,
        package_runner=_PlatformCommandAdapter(),
    )


def _read_production_partuuid_map(by_partuuid_dir: Path | None) -> dict[str, str]:
    """Read the live udev PARTUUID map (installed default owned by block_slots)."""
    from .block_slots import default_partuuid_map_reader

    if by_partuuid_dir is None:
        return default_partuuid_map_reader()
    return default_partuuid_map_reader(by_partuuid_dir)


def _observe_production_topology(
    record: "_LayoutRecord",
    *,
    dev_root: Path,
    by_partuuid_dir: Path | None,
    filesystem_runner: object,
) -> object:
    """Re-observe the installed block topology fresh (no caller addresses).

    Reads the live udev PARTUUID map, then probes every layout role device
    back (PARTUUID equality against the trusted record, filesystem UUID,
    size, parent-disk ancestry). Any absence, substitution, ambiguity or
    wrong-disk identity fails closed before a ``BlockTopology`` is returned;
    the shared ``resolve_slot_device`` re-validates the result against the
    record, so topology and resolution cross-check instead of trusting one
    observation.
    """
    try:
        mapping = _read_production_partuuid_map(by_partuuid_dir)
    except Exception as exc:
        raise UpdateBackendUnavailable(
            f"inactive-slot topology is unavailable: {_bounded_reason(exc)}"
        ) from exc
    roles: list[str] = ["system-a"]
    if record.system_b is not None:
        roles.append("system-b")
    roles.append("persist")
    identities = {
        "system-a": record.system_a,
        "system-b": record.system_b,
        "persist": record.persist,
    }
    facts: list[object] = []
    for role in roles:
        identity = identities[role]
        if identity is None:  # pragma: no cover - single-root guarded earlier
            raise UpdateBackendUnavailable(
                "A/B system-slot backend is not configured"
            )
        try:
            facts.append(
                _probe_role_fact(
                    role,
                    identity,
                    mapping=mapping,
                    dev_root=dev_root,
                    filesystem_runner=filesystem_runner,
                    expected_size_bytes=(
                        record.slot_bytes if role in ("system-a", "system-b") else None
                    ),
                )
            )
        except UpdateBackendUnavailable:
            raise
        except Exception as exc:
            raise UpdateBackendUnavailable(
                f"inactive-slot topology for role {role} is unavailable: "
                f"{_bounded_reason(exc)}"
            ) from exc
    try:
        from .persistent_layout import BlockTopology

        return BlockTopology(partitions=tuple(facts))  # type: ignore[arg-type]
    except Exception as exc:
        raise UpdateBackendUnavailable(
            f"inactive-slot topology is not authoritative: {_bounded_reason(exc)}"
        ) from exc


def _probe_role_fact(
    role: str,
    identity: object,
    *,
    mapping: dict[str, str],
    dev_root: Path,
    filesystem_runner: object,
    expected_size_bytes: int | None = None,
) -> object:
    """Probe one layout role back to its partition device (fail closed)."""
    from .block_slots import _normalize_partuuid_best_effort, blkid_device_partuuid
    from .persistent_layout import PartitionFact

    trusted_partuuid = str(getattr(identity, "partuuid"))
    if trusted_partuuid not in mapping:
        raise UpdateBackendUnavailable(
            f"trusted role PARTUUID is absent from the PARTUUID map: {role}"
        )
    kernel_name = mapping[trusted_partuuid]
    if (
        not isinstance(kernel_name, str)
        or not kernel_name
        or "/" in kernel_name
        or kernel_name in (".", "..")
    ):
        raise UpdateBackendUnavailable(
            f"PARTUUID map device name escapes its form: {role}"
        )
    node = Path(dev_root) / kernel_name
    if os.path.islink(node):
        raise UpdateBackendUnavailable(
            f"slot device node may not be a symbolic link: {role}"
        )
    try:
        node_stat = node.stat()
    except OSError as exc:
        raise UpdateBackendUnavailable(
            f"slot device node is not accessible: {role}"
        ) from exc
    if not stat.S_ISBLK(node_stat.st_mode):
        raise UpdateBackendUnavailable(
            f"slot device node must be a block device: {role}"
        )
    probed_partuuid = blkid_device_partuuid(node)
    if _normalize_partuuid_best_effort(probed_partuuid) != trusted_partuuid:
        raise UpdateBackendUnavailable(
            f"device node identity does not match the trusted role PARTUUID: {role}"
        )
    observed_uuid = filesystem_runner.blkid_uuid(node)  # type: ignore[union-attr]
    return PartitionFact.create(
        role=role,
        partuuid=_normalize_partuuid_best_effort(probed_partuuid),
        filesystem_uuid=observed_uuid,
        size_bytes=_block_node_size_bytes(
            node, expected_bytes=expected_size_bytes
        ),
        disk_id=_parent_disk_name(node),
    )


def _blkgetsize64_ioctl_requests(
    pointer_size: int | None = None,
) -> tuple[int, int]:
    """Return the native BLKGETSIZE64 request, then the alternate encoding.

    ``size_t`` is four bytes on i386 and eight on x86_64, which changes the
    ``_IOR`` encoded request. Trying the native width first and the other
    width second keeps one binary usable in both userspace/kernel pairings.
    """
    if pointer_size is None:
        pointer_size = struct.calcsize("P")
    if pointer_size == 4:
        return (_BLKGETSIZE64_IOCTL_32BIT, _BLKGETSIZE64_IOCTL_64BIT)
    return (_BLKGETSIZE64_IOCTL_64BIT, _BLKGETSIZE64_IOCTL_32BIT)


def _require_capacity_in_bounds(node: Path, size: object) -> int:
    if (
        not isinstance(size, int)
        or isinstance(size, bool)
        or size < _MIN_BLOCK_NODE_BYTES
        or size > _MAX_BLOCK_NODE_BYTES
    ):
        raise ValueError(
            f"slot device capacity is outside Greia bounds: {node.name}"
        )
    return size


def _read_ioctl_capacity(node: Path, request: int) -> int:
    import fcntl

    with node.open("rb") as handle:
        raw = fcntl.ioctl(handle.fileno(), request, b"\x00" * 8)
    if not isinstance(raw, (bytes, bytearray)) or len(raw) != 8:
        raise ValueError("ioctl returned a short capacity")
    (size,) = struct.unpack("Q", bytes(raw))
    return _require_capacity_in_bounds(node, int(size))


def _read_sysfs_capacity(node: Path, sysfs_root: Path) -> int:
    name = node.name
    if not isinstance(name, str) or not _BLOCK_NAME.fullmatch(name):
        raise ValueError("device name is outside the sysfs block form")
    path = Path(sysfs_root) / name / "size"
    with path.open("r", encoding="ascii", errors="strict") as handle:
        raw = handle.read(65)
    if len(raw) > 64:
        raise ValueError("sysfs capacity is not bounded")
    value = raw.strip()
    if not value.isdigit():
        raise ValueError("sysfs capacity is not an integer")
    size = int(value) * 512
    return _require_capacity_in_bounds(node, size)


def _read_blockdev_capacity(node: Path, command_runner: object | None) -> int:
    runner = command_runner or _PlatformCommandAdapter(timeout_seconds=30.0)
    result = runner.run(  # type: ignore[union-attr]
        ["blockdev", "--getsize64", "--", str(node)], check=False
    )
    if result.returncode != 0:  # type: ignore[union-attr]
        raise ValueError(
            f"blockdev exited {result.returncode}"  # type: ignore[union-attr]
        )
    lines = result.stdout.strip().splitlines()  # type: ignore[union-attr]
    if len(lines) != 1 or not lines[0].isdigit():
        raise ValueError("blockdev capacity is not an integer")
    return _require_capacity_in_bounds(node, int(lines[0]))


def _block_node_size_bytes(
    node: Path,
    *,
    expected_bytes: int | None = None,
    sysfs_root: Path = _SYSFS_BLOCK_ROOT,
    command_runner: object | None = None,
) -> int:
    """Re-observe a block device capacity (ioctl, sysfs, then blockdev).

    The ioctl request width follows the process pointer size so installed
    i386 images and x86_64 developer hosts both work. The read-only sysfs
    sector count is the primary fallback; ``blockdev`` remains an optional
    last resort. Every method is bounded, and a successful observation is
    still checked against the installed slot capacity (fail closed).
    """
    causes: list[str] = []
    for request in _blkgetsize64_ioctl_requests():
        try:
            size = _read_ioctl_capacity(node, request)
        except Exception as exc:
            causes.append(
                f"ioctl 0x{request:08x}: {_bounded_reason(exc, 80)}"
            )
            continue
        return _require_expected_capacity(node, size, expected_bytes)
    try:
        size = _read_sysfs_capacity(node, sysfs_root)
    except Exception as exc:
        causes.append(f"sysfs: {_bounded_reason(exc, 80)}")
    else:
        return _require_expected_capacity(node, size, expected_bytes)
    try:
        size = _read_blockdev_capacity(node, command_runner)
    except Exception as exc:
        causes.append(f"blockdev: {_bounded_reason(exc, 80)}")
    else:
        return _require_expected_capacity(node, size, expected_bytes)
    detail = "; ".join(causes) if causes else "no capacity method was attempted"
    raise UpdateBackendUnavailable(
        f"slot device capacity is unobservable: {node.name} ({detail})"
    )


def _require_expected_capacity(
    node: Path, size: int, expected_bytes: int | None
) -> int:
    if expected_bytes is not None and size != expected_bytes:
        raise UpdateBackendUnavailable(
            "slot device capacity does not match the installed layout: "
            f"{node.name} (observed {size} bytes, expected {expected_bytes} bytes)"
        )
    return size


def _parent_disk_name(node: Path) -> str:
    """Resolve the parent disk kernel name via ``lsblk`` (never guessed).

    The ancestry comes from the live block layer on every call, so two
    roles on different disks (or a substituted node) fail the layout
    single-disk proof in ``validate_layout_against_topology``. Execution
    flows through the owned platform command runner.
    """
    try:
        result = _PlatformCommandAdapter(timeout_seconds=30.0).run(
            ["lsblk", "--json", "--bytes", "--output", "NAME,PKNAME", "--", str(node)],
            check=False,
        )
    except Exception as exc:
        raise UpdateBackendUnavailable(
            "slot device disk ancestry is unobservable"
        ) from exc
    if result.returncode != 0:  # type: ignore[union-attr]
        raise UpdateBackendUnavailable(
            "slot device disk ancestry is unobservable"
        )
    try:
        document = json.loads(result.stdout)  # type: ignore[union-attr]
        devices = document.get("blockdevices")
        if not isinstance(devices, list) or len(devices) != 1:
            raise ValueError("lsblk ancestry is not authoritative")
        disk = devices[0].get("pkname") or devices[0].get("name")
    except (ValueError, AttributeError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise UpdateBackendUnavailable(
            "slot device disk ancestry is not authoritative"
        ) from exc
    if (
        not isinstance(disk, str)
        or not disk
        or not disk[0].isalnum()
        or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for c in disk)
    ):
        raise UpdateBackendUnavailable(
            "slot device disk ancestry is not authoritative"
        )
    return disk


class _MountTrackingFilesystem:
    """Delegate to the production block filesystem, remembering the mount.

    The finalizer owns the mount lifecycle (it mounts the inactive slot
    internally); the lazy package installer must address exactly that
    mountpoint. This wrapper records the mountpoint returned by
    :meth:`mount` and clears it on :meth:`unmount`, so installer and
    filesystem cannot drift to different targets. It implements no
    filesystem logic itself: every operation delegates to the shared
    ``BlockSlotFilesystem``.
    """

    def __init__(self, inner: object) -> None:
        self._inner = inner
        self._mountpoint: Path | None = None

    @property
    def current_mountpoint(self) -> Path | None:
        return self._mountpoint

    def bind_filesystem_uuid(self, filesystem_uuid: str) -> None:
        self._inner.bind_filesystem_uuid(filesystem_uuid)  # type: ignore[union-attr]

    def expand_to_capacity(self) -> None:
        self._inner.expand_to_capacity()  # type: ignore[union-attr]

    def mount(self) -> Path:
        mountpoint = self._inner.mount()  # type: ignore[union-attr]
        if not isinstance(mountpoint, Path):
            raise UpdateBackendUnavailable("slot mount did not return a path")
        self._mountpoint = mountpoint
        return mountpoint

    def unmount(self) -> None:
        try:
            self._inner.unmount()  # type: ignore[union-attr]
        finally:
            self._mountpoint = None

    def sync(self) -> None:
        self._inner.sync()  # type: ignore[union-attr]

    def write_file(self, relative_path: str, data: bytes) -> None:
        self._inner.write_file(relative_path, data)  # type: ignore[union-attr]

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]:
        return self._inner.missing_files(required)  # type: ignore[union-attr]

    def check_completeness(self) -> None:
        self._inner.check_completeness()  # type: ignore[union-attr]

    def check_health(self) -> None:
        self._inner.check_health()  # type: ignore[union-attr]


@dataclass(frozen=True, slots=True)
class _PlatformCommandAdapter:
    """Adapt the owned platform command runner to the installer protocol.

    All command execution on this path flows through
    ``hardware_enablement.SubprocessCommandRunner`` (argument arrays,
    no shell): this service composition adds no command runner of its own.
    Failures surface as :class:`SlotFinalizeError` so ``stage`` wraps them
    as fail-closed staging failures.
    """

    timeout_seconds: float = 120.0

    def run(self, command: object, *, check: bool = True) -> object:
        from .hardware_enablement import SubprocessCommandRunner

        try:
            result = SubprocessCommandRunner().run(
                list(command),  # type: ignore[arg-type]
                timeout_seconds=self.timeout_seconds,
            )
        except Exception as exc:
            from .slot_writer import SlotFinalizeError

            raise SlotFinalizeError(
                f"slot package command is not executable: {_bounded_reason(exc)}"
            ) from exc
        if check and result.returncode != 0:
            from .slot_writer import SlotFinalizeError

            raise SlotFinalizeError(
                "slot package command failed fail-closed: "
                f"{(result.stderr.strip() or 'command failed')[:200]}"
            )
        return result


class _LazyTargetPackageInstaller:
    """Install into the mounted inactive slot (mountpoint resolved lazily).

    Construction happens before the finalizer mounts the slot, so the
    target cannot be fixed then. At :meth:`install` time (called by the
    finalizer while mounted) the target resolves from the mount-tracking
    filesystem of the same stage, and installation delegates to the
    existing installer path
    (``InstallerSlotPackageInstaller``/``TargetHardwareSupportInstaller``)
    over the stage-owned pool the support-set factory already materialized
    exactly once (Repair T03: the running image pool never satisfies
    candidate finalization, and the candidate member is never
    re-materialized here): no package logic is copied here. Bind mounts
    the installer records are detached before returning so the slot
    unmount never sees a busy target. Stage cleanup stays with the stage
    owner (backend ``finally`` via the ``support_stage_cleanup`` seam),
    never with this installer.
    """

    def __init__(self, context: _ProductionUpdateContext) -> None:
        self._context = context

    def install(
        self, firmware: tuple[str, ...], microcode: tuple[str, ...]
    ) -> tuple[object, ...]:
        from .candidate_support import CandidateSupportStage
        from .slot_writer import SlotFinalizeError

        tracker = self._context.filesystem_tracker
        mountpoint = tracker.current_mountpoint if tracker is not None else None
        if mountpoint is None:
            raise SlotFinalizeError(
                "slot package install requires the mounted inactive slot"
            )
        try:
            from greia_installer.slots import InstallerSlotPackageInstaller

            stage = self._context.support_stage
            if stage is None or not isinstance(stage, CandidateSupportStage):
                if tuple(firmware) or tuple(microcode):
                    raise SlotFinalizeError(
                        "slot package install requires the candidate "
                        "hardware-support member"
                    )
                return ()
            if stage.closed:
                raise SlotFinalizeError(
                    "slot package install requires the staged candidate "
                    "hardware-support member"
                )
            pool = stage.pool
            adapter = InstallerSlotPackageInstaller(
                runner=_PlatformCommandAdapter(),  # type: ignore[arg-type]
                target_root=mountpoint,
                pool=pool,
                mounted=self._context.mounted,
            )
            before = len(self._context.mounted)
            try:
                result = adapter.install(tuple(firmware), tuple(microcode))  # type: ignore[assignment]
            except BaseException as exc:
                failed = self._detach_added_mounts(before)
                if failed:
                    exc.add_note(
                        "update mount cleanup also failed: "
                        + ", ".join(str(path) for path in failed)
                    )
                raise
            failed = self._detach_added_mounts(before)
            if failed:
                raise SlotFinalizeError(
                    "update mount cleanup could not detach: "
                    + ", ".join(str(path) for path in failed)
                )
            return result  # type: ignore[return-value]
        except SlotFinalizeError:
            raise
        except UpdateBackendUnavailable:
            raise
        except Exception as exc:
            raise SlotFinalizeError(
                f"slot package install failed fail-closed: {_bounded_reason(exc)}"
            ) from exc

    def _detach_added_mounts(self, before: int) -> tuple[Path, ...]:
        from greia_installer.hardware_support_install import detach_recorded_mounts

        runner = _PlatformCommandAdapter(timeout_seconds=30.0)
        return detach_recorded_mounts(
            runner, self._context.mounted, before=before  # type: ignore[arg-type]
        )


def build_production_update_seams(
    *,
    layout_record_path: Path | None = None,
    state_dir: Path | None = None,
    persist_root: Path | None = None,
) -> UpdateSlotSeams:
    """Compose the installed A/B production seams (no device IO here).

    Binds all eight destination factories over the trusted layout record
    path plus freshly re-observed topology at every factory call. Safe to
    compose on any machine: with no A/B authority (or no devices) each
    factory fails closed with :class:`UpdateBackendUnavailable` instead of
    addressing a drive. Explicitly injected seams remain available by
    passing them to the backend/service directly. ``state_dir`` owns
    candidate-support staging; without it staging falls back to the layout
    record's disposable parent (never a shared system temp dir).
    """
    record_path = (
        Path(layout_record_path)
        if layout_record_path is not None
        else installed_layout_record_path()
    )
    context = _ProductionUpdateContext(
        layout_record_path=record_path,
        paths=_production_paths(),
        state_dir=Path(state_dir) if state_dir is not None else None,
    )

    def _close_current_stage() -> None:
        _close_support_stage(context)

    return UpdateSlotSeams(
        slot_store_factory=_production_slot_store_factory(context),
        filesystem_factory=_production_filesystem_factory(context),
        package_installer_factory=_production_package_installer_factory(context),
        inventory_factory=_production_inventory_factory(context),
        support_set_factory=_production_support_set_factory(context),
        profile_policy_factory=_production_profile_policy_factory(),
        selection_factory=_production_selection_factory(context),
        installed_contract_factory=_production_installed_contract_factory(
            persist_root=persist_root
        ),
        support_stage_cleanup=_close_current_stage,
        support_pool_factory=_production_support_pool_factory(context),
    )


def _production_slot_store_factory(
    context: _ProductionUpdateContext,
) -> Callable[[object], object]:
    """Inactive-slot raw storage over the freshly resolved device."""

    def _factory(destination: object) -> object:
        semantic = getattr(destination, "semantic_slot", None)
        try:
            record = _require_production_ab_record(context.layout_record_path)
            primitives = _production_primitives(record, context.paths)
            resolved = primitives.resolve(semantic)  # type: ignore[union-attr]
            if resolved.role != getattr(
                destination, "role", resolved.role
            ) or resolved.filesystem_uuid != getattr(
                destination, "role_filesystem_uuid", resolved.filesystem_uuid
            ):
                raise UpdateBackendUnavailable(
                    "resolved inactive-slot device does not match "
                    "the staged destination"
                )
            return primitives.open_storage(resolved)  # type: ignore[union-attr]
        except UpdateBackendUnavailable:
            raise
        except Exception as exc:
            raise UpdateBackendUnavailable(
                f"inactive-slot store is unavailable: {_bounded_reason(exc)}"
            ) from exc

    return _factory


def _production_filesystem_factory(
    context: _ProductionUpdateContext,
) -> Callable[[], object]:
    """Slot filesystem (UUID binding/expansion/mount) for the inactive slot."""

    def _factory() -> object:
        try:
            record = _require_production_ab_record(context.layout_record_path)
            inactive = inactive_slot_for(record)
            if inactive is None:  # pragma: no cover - guarded by AB record
                raise UpdateBackendUnavailable(
                    "A/B system-slot backend is not configured"
                )
            primitives = _production_primitives(record, context.paths)
            resolved = primitives.resolve(inactive)  # type: ignore[union-attr]
            tracker = _MountTrackingFilesystem(
                primitives.open_filesystem(resolved)  # type: ignore[union-attr]
            )
            context.filesystem_tracker = tracker
            return tracker
        except UpdateBackendUnavailable:
            raise
        except SystemUpdateError:
            raise
        except Exception as exc:
            raise UpdateBackendUnavailable(
                f"inactive-slot filesystem is unavailable: {_bounded_reason(exc)}"
            ) from exc

    return _factory


def _production_package_installer_factory(
    context: _ProductionUpdateContext,
) -> Callable[[], object]:
    """Lazy installer addressing the mounted inactive slot of this stage."""

    def _factory() -> object:
        if context.filesystem_tracker is None:
            raise UpdateBackendUnavailable(
                "slot package installer requires the staged slot filesystem"
            )
        return _LazyTargetPackageInstaller(context)

    return _factory


def _production_inventory_factory(
    context: _ProductionUpdateContext,
) -> Callable[[], object]:
    """Hardware inventory attestation from a fresh sysfs snapshot."""

    def _factory() -> object:
        from .hardware_enablement import LinuxSysfsHardwareInventory
        from .slot_writer import SlotFinalizeError, HardwareInventoryAttestation

        try:
            snapshot = LinuxSysfsHardwareInventory(
                sysfs_devices=context.paths.sysfs_devices
            ).snapshot()
        except Exception as exc:
            raise UpdateBackendUnavailable(
                f"hardware inventory is unavailable: {_bounded_reason(exc)}"
            ) from exc
        try:
            return HardwareInventoryAttestation.from_inventory(snapshot)
        except SlotFinalizeError:
            raise
        except Exception as exc:
            raise UpdateBackendUnavailable(
                f"hardware inventory is not attestable: {_bounded_reason(exc)}"
            ) from exc

    return _factory


def _production_support_pool_factory(
    context: _ProductionUpdateContext,
) -> Callable[[object], object | None]:
    """Staged verified pool behind the selected-set capacity bound.

    Returns the same open stage-owned pool the support set converts from
    (repeat acquisition reuses the open stage; no second extraction), or
    ``None`` when the candidate declares no hardware support. Staging
    derives the selected installed bound from this pool instance.
    """

    def _factory(bundle: object) -> object | None:
        stage = _acquire_support_stage(context, bundle)
        if stage is None:
            return None
        return getattr(stage, "pool", None)

    return _factory


def _production_support_set_factory(
    context: _ProductionUpdateContext,
) -> Callable[[object], object]:
    """Release-bound support set from the candidate's own stage-owned pool.

    Repair T03: the exact inspected candidate's ``hardware-support.tar.zst``
    member streams once into one stage-owned ``CandidateSupportStage``
    (digest-verified metadata inspection, PERSIST preflight, single
    streaming extraction, single verified pool load) kept on the context
    for the whole stage. The support set converts from that same pool
    instance with the manifest digest/size — so the digest/size always
    travel alongside the bytes they describe, never alongside the running
    image's unrelated pool — and the lazy package installer of the same
    stage installs from the identical pool without re-materializing. A
    null manifest support declaration is a no-op extracting nothing.
    Cleanup stays with the stage owner (backend ``finally`` via the
    ``support_stage_cleanup`` seam), never with this factory.
    """

    def _factory(bundle: object) -> object:
        try:
            manifest = getattr(bundle, "manifest")
            if getattr(manifest, "hardware_support_sha256", None) is None:
                from .slot_writer import ReleaseSupportSet

                return ReleaseSupportSet(
                    support_digest=None,
                    support_size=None,
                    installed_size_bound=0,
                    provided_firmware=frozenset(),
                    provided_microcode=frozenset(),
                    packages=(),
                )
            from greia_installer.slots import pool_to_support_set

            stage = _acquire_support_stage(context, bundle)
            pool = getattr(stage, "pool", None)
            if pool is None:
                raise UpdateBackendUnavailable(
                    "release support set is unavailable: "
                    "candidate hardware-support did not materialize"
                )
            return pool_to_support_set(
                pool,
                support_digest=manifest.hardware_support_sha256,
                support_size=manifest.hardware_support_size,
            )
        except UpdateBackendUnavailable:
            raise
        except Exception as exc:
            raise UpdateBackendUnavailable(
                f"release support set is unavailable: {_bounded_reason(exc)}"
            ) from exc

    return _factory


def _production_profile_policy_factory() -> Callable[[object], object]:
    """Finalizer profile policy derived from the trusted layout record."""

    def _factory(record: object) -> object:
        return _default_slot_profile_policy(record)  # type: ignore[arg-type]

    return _factory


def _production_selection_factory(
    context: _ProductionUpdateContext,
) -> Callable[[object, str], object | None]:
    """Optional release-bound hardware selection (None when not resolvable)."""

    def _factory(support: object, token: str) -> object | None:
        from .hardware_enablement import (
            CompositeHardwareSupportResolver,
            IsenkramHardwareSupportResolver,
            LinuxKernelModules,
            LinuxSysfsHardwareInventory,
            X86MicrocodeResolver,
        )
        from .slot_writer import resolve_hardware_selection

        if not isinstance(token, str) or not token:
            raise SystemUpdateError(
                "hardware selection requires the attested inventory token"
            )
        try:
            snapshot = LinuxSysfsHardwareInventory(
                sysfs_devices=context.paths.sysfs_devices
            ).snapshot()
        except Exception as exc:
            raise UpdateBackendUnavailable(
                f"hardware selection is unavailable: {_bounded_reason(exc)}"
            ) from exc
        if snapshot.token != token:
            raise SystemUpdateError(
                "hardware inventory changed during staging; refusing selection"
            )
        plan = CompositeHardwareSupportResolver(
            resolvers=(
                IsenkramHardwareSupportResolver(
                    kernel_modules=LinuxKernelModules(
                        sysfs_root=context.paths.sysfs_devices.parent
                    )
                ),
                X86MicrocodeResolver(),
            )
        ).resolve(snapshot)
        if not plan.complete:
            return None
        return resolve_hardware_selection(plan=plan, support=support)  # type: ignore[arg-type]

    return _factory


def _production_installed_contract_factory(
    *, persist_root: Path | None = None
) -> Callable[[], bytes]:
    """Read the canonical marker from the mounted PERSIST filesystem.

    An explicit ``persist_root`` is a disposable-root injection for focused
    source tests. The installed composition reads from the fstab-owned
    ``/run/greia-persist`` mount, never from the ``/var/lib/greia-os`` bind.
    Missing, non-canonical, or unreadable state fails closed before a slot
    destination factory can be contacted.
    """
    from .persistent_layout import (
        PersistentLayoutError,
        persist_schema_marker_path,
        read_persist_schema_marker,
    )
    from .fstab import PERSIST_BOOT_MOUNTPOINT

    marker_path = persist_schema_marker_path(
        Path(persist_root)
        if persist_root is not None
        else Path(PERSIST_BOOT_MOUNTPOINT)
    )

    def _installed_marker_factory() -> bytes:
        try:
            return read_persist_schema_marker(marker_path)
        except PersistentLayoutError as exc:
            raise UpdateBackendUnavailable(
                f"installed PERSIST schema marker is unavailable: {exc}"
            ) from exc

    return _installed_marker_factory


def build_live_update_service(
    *,
    state_dir: Path | None = None,
    layout_record_path: Path | None = None,
    persist_root: Path | None = None,
    boot_backend: object | None = None,
    boot_backend_auto: bool = True,
    seams: UpdateSlotSeams | None = None,
) -> SystemUpdateServiceAuthority:
    """Compose the production authority from Greia-owned environment state.

    Compatibility (release identity) and layout authority resolve from
    Greia-owned state on every composition; the boot one-shot backend
    attaches to the boot-control ``grubenv`` when present (stays unwired
    fail-closed where there is no boot-control state, e.g. single-root
    layouts). With ``seams=None`` (the shipped ``main()`` path) the
    inactive-slot destination factories are the production seams from
    :func:`build_production_update_seams`: the exact installed updater
    stages only the freshly resolved inactive slot, and reports unavailable
    fail-closed where no A/B authority or device exists. Explicitly
    injected seams remain a test/harness feature.
    """

    root = (
        Path(state_dir)
        if state_dir is not None
        else Path(os.environ.get(UPDATE_STATE_DIR_ENV, UPDATE_STATE_DIR_DEFAULT))
    )
    record_path = (
        Path(layout_record_path)
        if layout_record_path is not None
        else installed_layout_record_path()
    )
    identity = resolve_installed_system_identity(
        layout_record_path=record_path,
    )
    resolved_boot_backend = (
        boot_backend
        if boot_backend is not None or not boot_backend_auto
        else production_boot_backend()
    )
    backend = SlotBackedSystemUpdateBackend(
        root,
        layout_record_path=record_path,
        seams=seams
        if seams is not None
        else build_production_update_seams(
            layout_record_path=record_path,
            state_dir=root,
            persist_root=persist_root,
        ),
        boot_backend=resolved_boot_backend,
    )
    return SystemUpdateServiceAuthority(root, identity, backend)


def serve_update_forever(
    listener: socket.socket,
    *,
    authority: SystemUpdateServiceAuthority,
) -> NoReturn:
    """Accept connections until the socket unit stops (systemd owns the fd).

    Every peer is attested from ``SO_PEERCRED`` before serving; connections
    whose kernel credential cannot be attested are closed unserved.
    """
    from .privileged_channel import PrivilegedChannelError

    while True:
        connection, _ = listener.accept()
        try:
            peer = attest_peer_from_connection(connection)
        except PrivilegedChannelError:
            try:
                connection.close()
            except OSError:
                pass
            continue
        handle_update_connection(connection, authority=authority, peer=peer)


def main(argv: list[str] | None = None) -> int:
    """Socket-activated entry for ``greia-system-update.service``.

    With systemd socket activation (``LISTEN_FDS``) the passed file
    descriptor is the listening socket; without one the service exits
    fail-closed instead of opening any socket itself. The production
    authority (compatibility, layout, journal, boot one-shot backend, production
    inactive-slot seams) is composed from Greia-owned state; staging
    reports unavailable rather than guessing at destination access where
    no A/B authority or inactive device exists.
    """
    _ = list(argv or [])
    listen_fds = int(os.environ.get("LISTEN_FDS", "0"))
    if listen_fds < 1:
        raise SystemExit(
            "greia-system-update: no socket-activated file descriptor; "
            "refusing to listen (see greia-system-update.socket)"
        )
    authority = build_live_update_service()
    listener = socket.fromfd(3, socket.AF_UNIX, socket.SOCK_STREAM)
    serve_update_forever(listener, authority=authority)
    return 0  # pragma: no cover - serve_forever never returns


if __name__ == "__main__":  # pragma: no cover - service entry
    raise SystemExit(main())
