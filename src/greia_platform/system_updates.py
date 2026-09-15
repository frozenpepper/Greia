from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import socket
import stat
import tempfile
import zipfile
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Callable, NoReturn, Protocol


BUNDLE_SUFFIX = ".greiaupdate"
BUNDLE_MEDIA_TYPE = "application/vnd.greia.system-update+zip"
MANIFEST_NAME = "manifest.json"
SIGNATURE_NAME = "manifest.sig"
PAYLOAD_NAME = "payload.bin"
HARDWARE_SUPPORT_NAME = "hardware-support.tar.zst"
PERSISTENT_CONTRACT_NAME = "persistent-state-contract.json"
BUNDLE_MEMBERS_V2 = (
    MANIFEST_NAME,
    SIGNATURE_NAME,
    PAYLOAD_NAME,
    HARDWARE_SUPPORT_NAME,
    PERSISTENT_CONTRACT_NAME,
)
# Historical v1 triple. No shipped v1 bundle was found in the repository
# (assigned-view `find . -name "*.greiaupdate"` is empty); v1 is rejected
# fail-closed with an explicit message, not silently accepted.
BUNDLE_MEMBERS_V1 = (MANIFEST_NAME, SIGNATURE_NAME, PAYLOAD_NAME)
SCHEMA_VERSION = 2
V1_SCHEMA_VERSION = 1
HARDWARE_SUPPORT_SCHEMA_VERSION = 1
PERSISTENT_CONTRACT_SCHEMA_VERSION = 1
MAX_MANIFEST_BYTES = 64 * 1024
MAX_SIGNATURE_BYTES = 16 * 1024
MAX_PAYLOAD_BYTES = 1536 * 1024 * 1024
MAX_HARDWARE_SUPPORT_BYTES = 512 * 1024 * 1024
MAX_PERSISTENT_CONTRACT_BYTES = 64 * 1024
MAX_BUNDLE_BYTES = 2 * 1024 * 1024 * 1024
MIN_INBOX_FREE_BYTES = 128 * 1024 * 1024
_MAX_RELEASE_ID = 96
_MAX_VERSION = 64
_MAX_NOTES = 4096
_MAX_RELEASE_SEQUENCE = 2_147_483_647
_ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
_DETERMINISTIC_ZIP_DATE = (1980, 1, 1, 0, 0, 0)
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
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


class UpdateSignatureError(UpdateBundleError):
    pass


class UpdateSequenceError(UpdateBundleError):
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
    schema_version: int
    release_id: str
    version: str
    release_sequence: int
    platform_family: str
    architecture: str
    profile: str
    signer: str
    payload_sha256: str
    payload_size: int
    payload_filesystem_bytes: int
    payload_minimum_slot_bytes: int
    hardware_support_name: str
    hardware_support_schema_version: int
    hardware_support_sha256: str
    hardware_support_size: int
    persistent_contract_schema_version: int
    persistent_contract_sha256: str
    persistent_contract_size: int
    release_notes: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise UpdateBundleError(
                f"unsupported system-update schema {self.schema_version}"
            )
        _validate_identifier(self.release_id, "release_id", _MAX_RELEASE_ID)
        _validate_text(self.version, "version", _MAX_VERSION)
        _validate_sequence(self.release_sequence)
        _validate_identifier(self.platform_family, "platform_family", 64)
        _validate_identifier(self.architecture, "architecture", 32)
        _validate_identifier(self.profile, "profile", 96)
        _validate_identifier(self.signer, "signer", 96)
        if not re.fullmatch(r"[0-9a-f]{64}", self.payload_sha256):
            raise UpdateBundleError("payload_sha256 must be lower-case SHA-256 hex")
        if self.payload_size <= 0 or self.payload_size > MAX_PAYLOAD_BYTES:
            raise UpdateBundleError("payload_size is outside Greia bounds")
        if self.payload_filesystem_bytes <= 0 or self.payload_filesystem_bytes > MAX_PAYLOAD_BYTES:
            raise UpdateBundleError("payload filesystem_bytes is outside Greia bounds")
        if self.payload_size != self.payload_filesystem_bytes:
            raise UpdateBundleError("payload size must equal relocatable filesystem bytes")
        if (
            self.payload_minimum_slot_bytes < self.payload_filesystem_bytes
            or self.payload_minimum_slot_bytes <= 0
            or self.payload_minimum_slot_bytes > MAX_BUNDLE_BYTES
        ):
            raise UpdateBundleError("payload minimum_slot_bytes must cover the filesystem image")
        if self.hardware_support_name != HARDWARE_SUPPORT_NAME:
            raise UpdateBundleError("hardware-support member name is invalid")
        if self.hardware_support_schema_version != HARDWARE_SUPPORT_SCHEMA_VERSION:
            raise UpdateBundleError("hardware-support schema is unsupported")
        if not re.fullmatch(r"[0-9a-f]{64}", self.hardware_support_sha256):
            raise UpdateBundleError("hardware-support sha256 must be lower-case SHA-256 hex")
        if (
            self.hardware_support_size <= 0
            or self.hardware_support_size > MAX_HARDWARE_SUPPORT_BYTES
        ):
            raise UpdateBundleError("hardware-support size is outside Greia bounds")
        if self.persistent_contract_schema_version != PERSISTENT_CONTRACT_SCHEMA_VERSION:
            raise UpdateBundleError("persistent-state contract schema is unsupported")
        if not re.fullmatch(r"[0-9a-f]{64}", self.persistent_contract_sha256):
            raise UpdateBundleError("persistent-state contract digest must be lower-case SHA-256 hex")
        if (
            self.persistent_contract_size <= 0
            or self.persistent_contract_size > MAX_PERSISTENT_CONTRACT_BYTES
        ):
            raise UpdateBundleError("persistent-state contract size is outside Greia bounds")
        if not isinstance(self.release_notes, str) or len(self.release_notes) > _MAX_NOTES:
            raise UpdateBundleError("release_notes exceeds Greia bound")

    def as_json_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "release_id": self.release_id,
            "version": self.version,
            "release_sequence": self.release_sequence,
            "platform_family": self.platform_family,
            "architecture": self.architecture,
            "profile": self.profile,
            "signer": self.signer,
            "payload": {
                "name": PAYLOAD_NAME,
                "sha256": self.payload_sha256,
                "size": self.payload_size,
                "kind": "system-slot-image",
                "filesystem_bytes": self.payload_filesystem_bytes,
                "minimum_slot_bytes": self.payload_minimum_slot_bytes,
            },
            "hardware_support": {
                "name": self.hardware_support_name,
                "schema_version": self.hardware_support_schema_version,
                "sha256": self.hardware_support_sha256,
                "size": self.hardware_support_size,
            },
            "persistent_state_contract": {
                "name": PERSISTENT_CONTRACT_NAME,
                "schema_version": self.persistent_contract_schema_version,
                "sha256": self.persistent_contract_sha256,
                "size": self.persistent_contract_size,
            },
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
            "release_sequence",
            "platform_family",
            "architecture",
            "profile",
            "signer",
            "payload",
            "hardware_support",
            "persistent_state_contract",
            "release_notes",
        }
        if set(raw) != expected:
            raise UpdateBundleError("manifest has unknown or missing top-level fields")
        if raw.get("schema_version") == V1_SCHEMA_VERSION:
            raise UpdateBundleError(
                "v1 system-update bundle is not accepted: no shipped v1 bundle "
                "exists in the repository; rebuild the release as schema v2"
            )
        payload = raw.get("payload")
        if not isinstance(payload, dict) or set(payload) != {
            "name",
            "sha256",
            "size",
            "kind",
            "filesystem_bytes",
            "minimum_slot_bytes",
        }:
            raise UpdateBundleError("manifest payload object is invalid")
        if payload.get("name") != PAYLOAD_NAME or payload.get("kind") != "system-slot-image":
            raise UpdateBundleError("unsupported system-update payload contract")
        hardware = raw.get("hardware_support")
        if not isinstance(hardware, dict) or set(hardware) != {
            "name",
            "schema_version",
            "sha256",
            "size",
        }:
            raise UpdateBundleError("manifest hardware-support object is invalid")
        contract = raw.get("persistent_state_contract")
        if not isinstance(contract, dict) or set(contract) != {
            "name",
            "schema_version",
            "sha256",
            "size",
        }:
            raise UpdateBundleError("manifest persistent-state contract object is invalid")
        values = {
            "schema_version": raw.get("schema_version"),
            "release_id": raw.get("release_id"),
            "version": raw.get("version"),
            "release_sequence": raw.get("release_sequence"),
            "platform_family": raw.get("platform_family"),
            "architecture": raw.get("architecture"),
            "profile": raw.get("profile"),
            "signer": raw.get("signer"),
            "payload_sha256": payload.get("sha256"),
            "payload_size": payload.get("size"),
            "payload_filesystem_bytes": payload.get("filesystem_bytes"),
            "payload_minimum_slot_bytes": payload.get("minimum_slot_bytes"),
            "hardware_support_name": hardware.get("name"),
            "hardware_support_schema_version": hardware.get("schema_version"),
            "hardware_support_sha256": hardware.get("sha256"),
            "hardware_support_size": hardware.get("size"),
            "persistent_contract_schema_version": contract.get("schema_version"),
            "persistent_contract_sha256": contract.get("sha256"),
            "persistent_contract_size": contract.get("size"),
            "release_notes": raw.get("release_notes"),
        }
        if isinstance(values["schema_version"], bool) or not isinstance(values["schema_version"], int):
            raise UpdateBundleError("schema_version must be an integer")
        if isinstance(values["release_sequence"], bool) or not isinstance(
            values["release_sequence"], int
        ):
            raise UpdateBundleError("release_sequence must be an integer")
        for int_key in (
            "payload_size",
            "payload_filesystem_bytes",
            "payload_minimum_slot_bytes",
            "hardware_support_schema_version",
            "hardware_support_size",
            "persistent_contract_schema_version",
            "persistent_contract_size",
        ):
            if isinstance(values[int_key], bool) or not isinstance(values[int_key], int):
                raise UpdateBundleError(f"{int_key} must be an integer")
        for key in (
            "release_id",
            "version",
            "platform_family",
            "architecture",
            "profile",
            "signer",
            "payload_sha256",
            "hardware_support_name",
            "hardware_support_sha256",
            "persistent_contract_sha256",
            "release_notes",
        ):
            if not isinstance(values[key], str):
                raise UpdateBundleError(f"{key} must be text")
        return cls(**values)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class SignatureEnvelope:
    schema_version: int
    algorithm: str
    signer: str
    signature: bytes

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise UpdateSignatureError("unsupported signature schema")
        if self.algorithm != "ed25519":
            raise UpdateSignatureError("only ed25519 signatures are supported")
        _validate_identifier(self.signer, "signature signer", 96)
        if len(self.signature) != 64:
            raise UpdateSignatureError("invalid Ed25519 signature length")

    def as_json_bytes(self) -> bytes:
        return canonical_json(
            {
                "schema_version": self.schema_version,
                "algorithm": self.algorithm,
                "signer": self.signer,
                "signature": base64.b64encode(self.signature).decode("ascii"),
            }
        )

    @classmethod
    def from_json_bytes(cls, raw: bytes) -> "SignatureEnvelope":
        if len(raw) > MAX_SIGNATURE_BYTES:
            raise UpdateSignatureError("signature envelope exceeds Greia bound")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UpdateSignatureError("signature envelope is not valid JSON") from exc
        if not isinstance(value, dict) or set(value) != {
            "schema_version",
            "algorithm",
            "signer",
            "signature",
        }:
            raise UpdateSignatureError("signature envelope fields are invalid")
        schema_version = value.get("schema_version")
        algorithm = value.get("algorithm")
        signer = value.get("signer")
        encoded_signature = value.get("signature")
        if isinstance(schema_version, bool) or not isinstance(schema_version, int):
            raise UpdateSignatureError("signature schema_version must be an integer")
        if schema_version == V1_SCHEMA_VERSION:
            raise UpdateSignatureError("v1 signatures are not accepted; rebuild as schema v2")
        if not isinstance(algorithm, str) or not isinstance(signer, str):
            raise UpdateSignatureError("signature algorithm/signer must be text")
        if not isinstance(encoded_signature, str):
            raise UpdateSignatureError("signature must be base64 text")
        try:
            signature = base64.b64decode(encoded_signature, validate=True)
        except ValueError as exc:
            raise UpdateSignatureError("signature is not valid base64") from exc
        return cls(
            schema_version=schema_version,
            algorithm=algorithm,
            signer=signer,
            signature=signature,
        )


@dataclass(frozen=True, slots=True)
class InspectedUpdateBundle:
    path: Path
    manifest: UpdateManifest
    signature: SignatureEnvelope

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


def decide_release_sequence(candidate_sequence: int, accepted_sequence: int) -> str:
    """Classify a signed candidate against the accepted sequence.

    Display version strings are never a security boundary; only the signed
    monotonic integer decides. Returns "update" / "no-update" / "rejected".
    """

    _validate_sequence(candidate_sequence)
    if isinstance(accepted_sequence, bool) or not isinstance(accepted_sequence, int):
        raise UpdateSequenceError("accepted release_sequence must be an integer")
    if accepted_sequence < 0 or accepted_sequence > _MAX_RELEASE_SEQUENCE:
        raise UpdateSequenceError("accepted release_sequence is outside Greia bounds")
    if candidate_sequence > accepted_sequence:
        return "update"
    if candidate_sequence == accepted_sequence:
        return "no-update"
    return "rejected"


def authorize_release_sequence(candidate_sequence: int, accepted_sequence: int) -> str:
    """Enforce anti-rollback: lower sequences are rejected even when signed."""

    decision = decide_release_sequence(candidate_sequence, accepted_sequence)
    if decision == "rejected":
        raise UpdateSequenceError(
            f"release_sequence {candidate_sequence} is older than accepted {accepted_sequence}"
        )
    return decision


def read_accepted_sequence(state_dir: Path) -> int:
    path = Path(state_dir) / "system-updates" / "accepted.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return 0
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateBundleError("accepted release state is unreadable") from exc
    if not isinstance(raw, dict):
        raise UpdateBundleError("accepted release state is invalid")
    sequence = raw.get("release_sequence", 0)
    if isinstance(sequence, bool) or not isinstance(sequence, int):
        raise UpdateBundleError("accepted release_sequence must be an integer")
    if sequence < 0 or sequence > _MAX_RELEASE_SEQUENCE:
        raise UpdateBundleError("accepted release_sequence is outside Greia bounds")
    return sequence


def write_accepted_sequence(state_dir: Path, sequence: int) -> None:
    _validate_sequence(sequence, allow_zero=True)
    _atomic_json(
        Path(state_dir) / "system-updates" / "accepted.json",
        {"schema_version": 1, "release_sequence": sequence},
    )


class SystemUpdateInbox:
    """Unprivileged single-candidate inbox for Parent-delivered update bytes.

    Receiving a bundle is not activation authority. This layer validates archive
    structure and payload integrity, stores the selected candidate by content
    digest and removes older untrusted inbox candidates. Network receivers can
    stage directly inside this inbox and publish the same inode content-addressably
    so a large update never needs a second full-size local copy. Cryptographic
    trust and inactive-slot activation are re-established by the privileged
    SystemUpdateService before any system write.
    """

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = Path(state_dir)
        self.inbox_dir = self.state_dir / "system-updates" / "inbox"
        self.status_path = self.state_dir / "system-updates" / "status.json"

    def create_receive_staging(self, incoming_size: int) -> Path:
        """Create one private same-filesystem staging file for streamed input."""

        if isinstance(incoming_size, bool) or incoming_size <= 0 or incoming_size > MAX_BUNDLE_BYTES:
            raise UpdateBundleError("incoming update size is outside Greia bounds")
        self._prepare_inbox()
        self._assert_receive_capacity(incoming_size)
        descriptor, raw_path = tempfile.mkstemp(
            prefix=".incoming-",
            suffix=".tmp",
            dir=self.inbox_dir,
        )
        os.close(descriptor)
        staging = Path(raw_path)
        os.chmod(staging, 0o600)
        return staging

    def receive_staged(self, staged_path: Path) -> InspectedUpdateBundle:
        """Validate and publish a Greia-owned inbox staging file without copying."""

        staged = Path(staged_path)
        self._prepare_inbox(clean_temporaries=False)
        self._require_owned_staging(staged)
        inspected = inspect_update_bundle(staged)
        source_digest = sha256_file(staged)
        destination = self.inbox_dir / (
            f"{inspected.manifest.release_id}-{source_digest}{BUNDLE_SUFFIX}"
        )
        if destination.exists():
            if not destination.is_file() or sha256_file(destination) != source_digest:
                raise UpdateBundleError("content-addressed update inbox collision")
        else:
            try:
                os.link(staged, destination)
            except FileExistsError:
                if not destination.is_file() or sha256_file(destination) != source_digest:
                    raise UpdateBundleError("content-addressed update inbox collision")
            os.chmod(destination, 0o600)
        self._prune_other_candidates(destination)
        self._record_received(inspected, destination, source_digest)
        return InspectedUpdateBundle(destination, inspected.manifest, inspected.signature)

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
            return {
                "state": UpdateState.IDLE.value,
                "queued": None,
                "signature_verified": False,
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
                "not enough free space to receive update while preserving Greia reserve"
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
        if not staged.name.startswith(".incoming-") or not staged.name.endswith(".tmp"):
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
            "signature_verified": False,
            "activation_available": False,
        }
        _atomic_json(self.status_path, payload)

    def _remove_stale_temporaries(self) -> None:
        try:
            for candidate in self.inbox_dir.glob(".incoming-*.tmp"):
                candidate.unlink(missing_ok=True)
        except OSError as exc:
            raise UpdateBundleError("unable to clean stale update inbox temporary") from exc

    def _prune_other_candidates(self, keep: Path) -> None:
        try:
            for candidate in self.inbox_dir.glob(f"*{BUNDLE_SUFFIX}"):
                if candidate != keep:
                    candidate.unlink(missing_ok=True)
        except OSError as exc:
            raise UpdateBundleError("unable to bound update inbox candidates") from exc


class SystemUpdateService:
    """Privileged trust/compatibility/backend coordinator for queued bundles."""

    def __init__(
        self,
        state_dir: Path,
        trusted_key_dir: Path,
        identity: SystemIdentity,
        backend: SystemUpdateBackend | None = None,
        accepted_sequence: int = 0,
    ) -> None:
        self.state_dir = Path(state_dir)
        self.trusted_key_dir = Path(trusted_key_dir)
        self.identity = identity
        self.backend = backend or UnavailableSystemUpdateBackend()
        if isinstance(accepted_sequence, bool) or not isinstance(accepted_sequence, int):
            raise UpdateSequenceError("accepted release_sequence must be an integer")
        if accepted_sequence < 0 or accepted_sequence > _MAX_RELEASE_SEQUENCE:
            raise UpdateSequenceError("accepted release_sequence is outside Greia bounds")
        self.accepted_sequence = accepted_sequence

    def verify(self, bundle_path: Path) -> InspectedUpdateBundle:
        inspected = inspect_update_bundle(bundle_path)
        verify_update_signature(inspected, self.trusted_key_dir)
        self.identity.assert_compatible(inspected.manifest)
        return inspected

    def verify_for_activation(
        self, bundle_path: Path, accepted_sequence: int | None = None
    ) -> tuple[InspectedUpdateBundle, str]:
        """Verify trust/compatibility and classify the signed sequence.

        Returns (inspected, decision) where decision is "update" or "no-update".
        Older correctly signed candidates raise UpdateSequenceError. Display
        version strings are never compared as a security boundary.
        """

        inspected = self.verify(bundle_path)
        accepted = self.accepted_sequence if accepted_sequence is None else accepted_sequence
        decision = authorize_release_sequence(
            inspected.manifest.release_sequence, accepted
        )
        return inspected, decision

    def stage(
        self, bundle_path: Path, accepted_sequence: int | None = None
    ) -> InspectedUpdateBundle:
        accepted = self.accepted_sequence if accepted_sequence is None else accepted_sequence
        inspected, decision = self.verify_for_activation(bundle_path, accepted)
        if decision == "no-update":
            return inspected
        if not self.backend.available:
            raise UpdateBackendUnavailable(
                str(self.backend.status_payload().get("reason", "update backend unavailable"))
            )
        self.backend.stage(inspected)
        return inspected

    def status_payload(self) -> dict[str, object]:
        return {
            "identity": {
                "version": self.identity.version,
                "platform_family": self.identity.platform_family,
                "architecture": self.identity.architecture,
                "profile": self.identity.profile,
            },
            "activation": self.backend.status_payload(),
            "accepted_release_sequence": self.accepted_sequence,
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
    hardware_support_path: Path,
    persistent_contract_path: Path,
    output_path: Path,
    version: str,
    release_id: str,
    release_sequence: int,
    platform_family: str,
    architecture: str,
    profile: str,
    signer: str,
    private_key_path: Path,
    minimum_slot_bytes: int | None = None,
    release_notes: str = "",
) -> UpdateManifest:
    payload_path = Path(payload_path)
    hardware_support_path = Path(hardware_support_path)
    persistent_contract_path = Path(persistent_contract_path)
    output_path = Path(output_path)
    for path, label in (
        (payload_path, "payload"),
        (hardware_support_path, "hardware-support"),
        (persistent_contract_path, "persistent-state contract"),
    ):
        if path.is_symlink() or not path.is_file():
            raise UpdateBundleError(f"{label} is not a regular file")
    payload_size = payload_path.stat().st_size
    hardware_size = hardware_support_path.stat().st_size
    contract_size = persistent_contract_path.stat().st_size
    if payload_size <= 0 or payload_size > MAX_PAYLOAD_BYTES:
        raise UpdateBundleError("payload size is outside Greia bounds")
    if hardware_size <= 0 or hardware_size > MAX_HARDWARE_SUPPORT_BYTES:
        raise UpdateBundleError("hardware-support size is outside Greia bounds")
    if contract_size <= 0 or contract_size > MAX_PERSISTENT_CONTRACT_BYTES:
        raise UpdateBundleError("persistent-state contract size is outside Greia bounds")
    _assert_relocatable_payload(payload_path)
    _assert_hardware_support_magic(hardware_support_path)
    contract_raw = persistent_contract_path.read_bytes()
    verify_persistent_state_contract_bytes(contract_raw)
    minimum = minimum_slot_bytes if minimum_slot_bytes is not None else payload_size
    if isinstance(minimum, bool) or not isinstance(minimum, int):
        raise UpdateBundleError("minimum_slot_bytes must be an integer")
    manifest = UpdateManifest(
        schema_version=SCHEMA_VERSION,
        release_id=release_id,
        version=version,
        release_sequence=release_sequence,
        platform_family=platform_family,
        architecture=architecture,
        profile=profile,
        signer=signer,
        payload_sha256=sha256_file(payload_path),
        payload_size=payload_size,
        payload_filesystem_bytes=payload_size,
        payload_minimum_slot_bytes=minimum,
        hardware_support_name=HARDWARE_SUPPORT_NAME,
        hardware_support_schema_version=HARDWARE_SUPPORT_SCHEMA_VERSION,
        hardware_support_sha256=sha256_file(hardware_support_path),
        hardware_support_size=hardware_size,
        persistent_contract_schema_version=PERSISTENT_CONTRACT_SCHEMA_VERSION,
        persistent_contract_sha256=hashlib.sha256(contract_raw).hexdigest(),
        persistent_contract_size=contract_size,
        release_notes=release_notes,
    )
    private = Path(private_key_path)
    if private.is_symlink() or not private.is_file():
        raise UpdateSignatureError(
            "release signing key is missing; refusing to build "
            "(missing production key is a hard build failure)"
        )
    signature = SignatureEnvelope(
        schema_version=SCHEMA_VERSION,
        algorithm="ed25519",
        signer=signer,
        signature=_sign_ed25519(private, manifest.canonical_bytes()),
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
            _writestr_deterministic(
                archive, SIGNATURE_NAME, signature.as_json_bytes(), compress=True
            )
            _write_file_deterministic(archive, PAYLOAD_NAME, payload_path, compress=False)
            _write_file_deterministic(
                archive, HARDWARE_SUPPORT_NAME, hardware_support_path, compress=False
            )
            _write_file_deterministic(
                archive,
                PERSISTENT_CONTRACT_NAME,
                persistent_contract_path,
                compress=True,
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
    if path.stat().st_size <= 0 or path.stat().st_size > MAX_BUNDLE_BYTES:
        raise UpdateBundleError("update bundle size is outside Greia bounds")
    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if names == list(BUNDLE_MEMBERS_V1):
                raise UpdateBundleError(
                    "v1 system-update bundle is not accepted: no shipped v1 bundle "
                    "exists in the repository; rebuild the release as schema v2"
                )
            if names != list(BUNDLE_MEMBERS_V2):
                raise UpdateBundleError("update bundle members/order are invalid")
            _reject_unsafe_members(infos)
            manifest_info, signature_info, payload_info, hw_info, contract_info = infos
            if manifest_info.file_size <= 0 or manifest_info.file_size > MAX_MANIFEST_BYTES:
                raise UpdateBundleError("manifest exceeds Greia bound")
            if signature_info.file_size <= 0 or signature_info.file_size > MAX_SIGNATURE_BYTES:
                raise UpdateBundleError("signature envelope exceeds Greia bound")
            if payload_info.file_size <= 0 or payload_info.file_size > MAX_PAYLOAD_BYTES:
                raise UpdateBundleError("payload exceeds Greia bound")
            if hw_info.file_size <= 0 or hw_info.file_size > MAX_HARDWARE_SUPPORT_BYTES:
                raise UpdateBundleError("hardware-support exceeds Greia bound")
            if (
                contract_info.file_size <= 0
                or contract_info.file_size > MAX_PERSISTENT_CONTRACT_BYTES
            ):
                raise UpdateBundleError("persistent-state contract exceeds Greia bound")
            manifest_raw = archive.read(MANIFEST_NAME)
            try:
                manifest_json = json.loads(manifest_raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise UpdateBundleError("manifest is not valid JSON") from exc
            manifest = UpdateManifest.from_json_dict(manifest_json)
            if manifest_raw != manifest.canonical_bytes():
                raise UpdateBundleError("manifest is not canonical JSON")
            signature = SignatureEnvelope.from_json_bytes(archive.read(SIGNATURE_NAME))
            if signature.signer != manifest.signer:
                raise UpdateSignatureError("manifest/signature signer mismatch")
            if payload_info.file_size != manifest.payload_size:
                raise UpdateBundleError("payload size does not match signed manifest")
            if hw_info.file_size != manifest.hardware_support_size:
                raise UpdateBundleError("hardware-support size does not match signed manifest")
            if contract_info.file_size != manifest.persistent_contract_size:
                raise UpdateBundleError(
                    "persistent-state contract size does not match signed manifest"
                )
            contract_raw = archive.read(PERSISTENT_CONTRACT_NAME)
            verify_persistent_state_contract_bytes(contract_raw)
            if hashlib.sha256(contract_raw).hexdigest() != manifest.persistent_contract_sha256:
                raise UpdateBundleError(
                    "persistent-state contract digest does not match signed manifest"
                )
            _verify_member_digest(archive, PAYLOAD_NAME, manifest.payload_sha256)
            _verify_member_digest(
                archive, HARDWARE_SUPPORT_NAME, manifest.hardware_support_sha256
            )
            _assert_member_relocatable(archive, payload_info)
            _assert_member_zstd_magic(archive, hw_info)
    except (zipfile.BadZipFile, OSError) as exc:
        if isinstance(exc, UpdateBundleError | UpdateSignatureError):
            raise
        raise UpdateBundleError("update bundle is not a valid Greia ZIP artifact") from exc
    return InspectedUpdateBundle(path, manifest, signature)


def verify_update_signature(bundle: InspectedUpdateBundle, trusted_key_dir: Path) -> None:
    key_path = Path(trusted_key_dir) / f"{bundle.manifest.signer}.pem"
    if not key_path.is_file():
        raise UpdateSignatureError(
            f"no trusted system-update key for signer {bundle.manifest.signer}"
        )
    _verify_ed25519(key_path, bundle.manifest.canonical_bytes(), bundle.signature.signature)


def generate_ed25519_keypair(private_key_path: Path, public_key_path: Path) -> None:
    Ed25519PrivateKey, _, serialization = _cryptography_ed25519()
    private = Ed25519PrivateKey.generate()
    private_bytes = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    for path in (Path(private_key_path), Path(public_key_path)):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise UpdateSignatureError(f"refusing to overwrite key: {path}")
    Path(private_key_path).write_bytes(private_bytes)
    os.chmod(private_key_path, 0o600)
    Path(public_key_path).write_bytes(public_bytes)
    os.chmod(public_key_path, 0o644)


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


def _sign_ed25519(private_key_path: Path, data: bytes) -> bytes:
    Ed25519PrivateKey, _, serialization = _cryptography_ed25519()
    try:
        private = serialization.load_pem_private_key(
            Path(private_key_path).read_bytes(), password=None
        )
    except (OSError, ValueError, TypeError) as exc:
        raise UpdateSignatureError("unable to load Ed25519 private key") from exc
    if not isinstance(private, Ed25519PrivateKey):
        raise UpdateSignatureError("private key is not Ed25519")
    return private.sign(data)


def _verify_ed25519(public_key_path: Path, data: bytes, signature: bytes) -> None:
    _, Ed25519PublicKey, serialization = _cryptography_ed25519()
    try:
        public = serialization.load_pem_public_key(Path(public_key_path).read_bytes())
    except (OSError, ValueError, TypeError) as exc:
        raise UpdateSignatureError("unable to load trusted Ed25519 public key") from exc
    if not isinstance(public, Ed25519PublicKey):
        raise UpdateSignatureError("trusted key is not Ed25519")
    try:
        public.verify(signature, data)
    except Exception as exc:  # cryptography exposes InvalidSignature across versions
        raise UpdateSignatureError("system-update signature verification failed") from exc


def _cryptography_ed25519():
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )
    except ImportError as exc:
        raise UpdateSignatureError(
            "Ed25519 system-update signing/verification requires python3-cryptography"
        ) from exc
    return Ed25519PrivateKey, Ed25519PublicKey, serialization


def _validate_identifier(value: str, name: str, maximum: int) -> None:
    if not isinstance(value, str) or not value or len(value) > maximum or not _IDENTIFIER.fullmatch(value):
        raise UpdateBundleError(f"{name} must be a bounded ASCII identifier")


def _validate_text(value: str, name: str, maximum: int) -> None:
    if not isinstance(value, str) or not value or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise UpdateBundleError(f"{name} must be bounded printable text")


def _validate_sequence(value: int, *, allow_zero: bool = False) -> None:
    minimum = 0 if allow_zero else 1
    if isinstance(value, bool) or not isinstance(value, int):
        raise UpdateBundleError("release_sequence must be an integer")
    if value < minimum or value > _MAX_RELEASE_SEQUENCE:
        raise UpdateBundleError("release_sequence is outside Greia bounds")


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
        raise UpdateBundleError(f"{name} digest does not match signed manifest")


def _assert_relocatable_payload(path: Path) -> None:
    with Path(path).open("rb") as handle:
        header = handle.read(1024)
    if len(header) >= 512 and header[510:512] == b"\x55\xaa":
        raise UpdateBundleError("payload must be a relocatable image without an MBR")
    if len(header) >= 520 and header[512:520] == b"EFI PART":
        raise UpdateBundleError("payload must be a relocatable image without a GPT")


def _assert_member_relocatable(
    archive: zipfile.ZipFile, info: zipfile.ZipInfo
) -> None:
    with archive.open(info.filename, "r") as handle:
        header = handle.read(1024)
    if len(header) >= 512 and header[510:512] == b"\x55\xaa":
        raise UpdateBundleError("payload must be a relocatable image without an MBR")
    if len(header) >= 520 and header[512:520] == b"EFI PART":
        raise UpdateBundleError("payload must be a relocatable image without a GPT")


def _assert_hardware_support_magic(path: Path) -> None:
    with Path(path).open("rb") as handle:
        magic = handle.read(4)
    if magic != _ZSTD_MAGIC:
        raise UpdateBundleError("hardware-support must be zstd-compressed tar (.tar.zst)")


def _assert_member_zstd_magic(
    archive: zipfile.ZipFile, info: zipfile.ZipInfo
) -> None:
    with archive.open(info.filename, "r") as handle:
        magic = handle.read(4)
    if magic != _ZSTD_MAGIC:
        raise UpdateBundleError("hardware-support must be zstd-compressed tar (.tar.zst)")


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
#   inbox candidate -> SystemUpdateService trust -> SlotBackedSystemUpdateBackend
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

#: Journal directory name under ``state_dir / "system-updates"``. The same
#: ``BootTransactionJournal`` record the A8-FAULTS harness and later
#: boot-health work reconcile, so crash recovery sees exactly one record.
UPDATE_JOURNAL_DIR_NAME = "journal"

#: Peer UIDs authorized for the update socket service. Root only: the Parent
#: control plane stays unprivileged and reaches the privileged side solely
#: through the inbox candidate it stages. Mirrors
#: ``update_privileged.UPDATE_PRIVILEGED_ALLOWED_UIDS`` without importing that
#: module (it imports this one).
UPDATE_SERVICE_ALLOWED_UIDS = (0,)

#: Environment overrides for the socket-activated composition root. Defaults
#: bind the installed-system authorities; nothing here names a partition
#: device or a raw command.
UPDATE_STATE_DIR_ENV = "GREIA_UPDATE_STATE_DIR"
UPDATE_STATE_DIR_DEFAULT = "/var/lib/greia-os"
UPDATE_TRUSTED_KEY_DIR_ENV = "GREIA_UPDATE_TRUSTED_KEY_DIR"
UPDATE_TRUSTED_KEY_DIR_DEFAULT = "/etc/greia-os/system-update-keys"
INSTALLED_LAYOUT_RECORD_ENV = "GREIA_INSTALLED_LAYOUT_RECORD"
INSTALLED_LAYOUT_RECORD_DEFAULT = "/etc/greia-os/installed-layout.json"
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
    sequence = document.get("release_sequence")
    if (
        isinstance(sequence, bool)
        or not isinstance(sequence, int)
        or sequence < 0
        or sequence > _MAX_RELEASE_SEQUENCE
    ):
        raise UpdateLayoutError("installed release identity release_sequence is invalid")
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
    )


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
    """Derive the finalizer profile policy from the trusted layout record."""
    from .slot_writer import SlotProfilePolicy

    return SlotProfilePolicy(
        layout_id=record.layout_id,
        system_slot_bytes=record.slot_bytes,
        boot_backend=record.boot_backend,
    )


def _bind_release_facts_to_policy(policy: object, manifest: UpdateManifest) -> object:
    """Bind the signed release compatibility facts onto a profile policy.

    The signed manifest is authoritative for ``architecture``/
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
    the installed persistent-state contract bytes so staging can prove the
    candidate binds them (previously accepted slot keeps reading shared
    state) before any inactive-slot write.

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


class SlotBackedSystemUpdateBackend:
    """Privileged staging/arm/confirm over the common slot/journal seams.

    Reuses :class:`SlotWriter`, :class:`SlotFinalizer` and
    :class:`BootTransactionJournal` as shared libraries: trust stays in
    :class:`SystemUpdateService` (signature, compatibility, anti-rollback),
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
    ) -> None:
        self.state_dir = Path(state_dir)
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
            payload["release_sequence"] = journal.release_sequence
        return payload

    def stage(self, bundle: InspectedUpdateBundle) -> None:
        """Verify-then-write the inbox candidate into the inactive slot.

        Trust (signature/compatibility/sequence) is established by
        :class:`SystemUpdateService` before this call; this method re-binds
        the signed digest at the byte layer (``SlotWriter`` readback),
        refuses live slots and single-root layouts, then records the shared
        journal. Any refusal raises before the first destination mutation.
        """
        from .boot_transaction import BootJournalError, BootTransactionError, BootTransactionJournal
        from .slot_writer import (
            DestinationSlot,
            SlotFinalizeError,
            SlotFinalizer,
            SlotWriteError,
            SlotWriter,
            VerifiedReleaseMember,
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
            # Persistent-state contract preflight while pending: the
            # candidate must bind the installed contract bytes (same
            # namespaces/digest), so the previously accepted slot still
            # reads shared PERSIST state after update and rollback. This
            # runs before any inactive-slot store is addressed.
            installed_contract = self._require_seam(
                "installed persistent-state contract",
                self.seams.installed_contract_factory,
            )()
            if (
                not isinstance(installed_contract, (bytes, bytearray))
                or not installed_contract
            ):
                raise SystemUpdateError(
                    "installed persistent-state contract is not authoritative"
                )
            try:
                from .persistent_layout import assert_persistent_contract_accepted

                assert_persistent_contract_accepted(
                    bytes(installed_contract), bundle.manifest
                )
            except SystemUpdateError:
                raise
            except Exception as exc:
                raise SystemUpdateError(
                    f"persistent-state contract preflight refused: {exc}"
                ) from exc
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
                    with archive.open(PAYLOAD_NAME, "r") as source:
                        verified = writer.write(
                            member=member,
                            destination=destination,
                            source=source,
                            storage=storage,
                            support_installed_bytes=int(
                                getattr(support_value, "installed_size_bound", 0)
                            ),
                        )
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
            )
            BootTransactionJournal.begin_update(
                self.journal_dir,
                layout_id=record.layout_id,
                boot_backend=record.boot_backend,
                release_id=receipt.release_id,
                release_sequence=receipt.release_sequence,
                candidate_slot=inactive,
                accepted_slot=accepted,
            )
            self._last_staged = {
                "candidate_slot": inactive,
                "release_id": receipt.release_id,
                "release_sequence": receipt.release_sequence,
            }
        except (SlotWriteError, SlotFinalizeError, BootTransactionError, BootJournalError) as exc:
            if isinstance(exc, SystemUpdateError):
                raise
            raise SystemUpdateError(f"update staging failed fail-closed: {exc}") from exc

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
                write_accepted_sequence(self.state_dir, journal.release_sequence)
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
            release_sequence=journal.release_sequence,
        )


def advance_layout_authority_for_acceptance(
    layout_record_path: Path,
    *,
    candidate_slot: str,
    accepted_slot: str,
    release_id: str,
    release_sequence: int,
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
        if (
            record.accepted_release_id != release_id
            or record.accepted_release_sequence != release_sequence
        ):
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
        accepted_release_sequence=release_sequence,
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

    Structural twin of ``update_privileged.CurrentCandidateSummary`` (same
    attribute names, so the socket endpoint renders it without this module
    importing the protocol owner); the service resolves it internally and
    requests never carry selectors.
    """

    present: bool
    release_id: str = ""
    release_sequence: int = 0
    bundle_sha256: str = ""
    signature_verified: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.present, bool):
            raise SystemUpdateError("candidate presence must be a boolean")
        if len(self.release_id) > 96:
            raise SystemUpdateError("candidate release_id exceeds Greia bound")
        if (
            isinstance(self.release_sequence, bool)
            or not isinstance(self.release_sequence, int)
            or self.release_sequence < 0
        ):
            raise SystemUpdateError(
                "candidate release_sequence is outside Greia bounds"
            )
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
    trusted_key_dir: Path
    identity: SystemIdentity
    backend: SystemUpdateBackend | None = None
    accepted_sequence: int | None = None
    service: SystemUpdateService = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "state_dir", Path(self.state_dir))
        object.__setattr__(self, "trusted_key_dir", Path(self.trusted_key_dir))
        if self.backend is None:
            object.__setattr__(
                self, "backend", SlotBackedSystemUpdateBackend(self.state_dir)
            )
        pinned = self.accepted_sequence is not None
        object.__setattr__(self, "_accepted_sequence_pinned", pinned)
        if self.accepted_sequence is None:
            object.__setattr__(
                self, "accepted_sequence", read_accepted_sequence(self.state_dir)
            )
        object.__setattr__(
            self,
            "service",
            SystemUpdateService(
                self.state_dir,
                self.trusted_key_dir,
                self.identity,
                self.backend,
                accepted_sequence=int(self.accepted_sequence),
            ),
        )

    def candidate_summary(self) -> UpdateCandidateSummary:
        try:
            path = self._current_bundle_path()
            status = self._status_record()
        except SystemUpdateError:
            return UpdateCandidateSummary(present=False)
        if not path.is_file():
            return UpdateCandidateSummary(present=False)
        release = status.get("release")
        if not isinstance(release, dict):
            return UpdateCandidateSummary(present=False)
        sequence = release.get("release_sequence", 0)
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            return UpdateCandidateSummary(present=False)
        digest = status.get("bundle_sha256", "")
        if not isinstance(digest, str) or (digest and not re.fullmatch(r"[0-9a-f]{64}", digest)):
            return UpdateCandidateSummary(present=False)
        release_id = release.get("release_id", "")
        if not isinstance(release_id, str) or len(release_id) > 96:
            return UpdateCandidateSummary(present=False)
        verified = status.get("signature_verified", False)
        return UpdateCandidateSummary(
            present=True,
            release_id=release_id,
            release_sequence=sequence,
            bundle_sha256=digest,
            signature_verified=verified is True,
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
        self._refresh_accepted_sequence()
        path = self._current_bundle_path()
        inspected, _decision = self.service.verify_for_activation(path)
        return UpdateCandidateSummary(
            present=True,
            release_id=inspected.manifest.release_id,
            release_sequence=inspected.manifest.release_sequence,
            bundle_sha256=sha256_file(path),
            signature_verified=True,
        )

    def stage_current_candidate(self) -> dict[str, object]:
        self._refresh_accepted_sequence()
        path = self._current_bundle_path()
        inspected, decision = self.service.verify_for_activation(path)
        if decision == "no-update":
            return {
                "staged": False,
                "decision": "no-update",
                "release_id": inspected.manifest.release_id,
                "release_sequence": inspected.manifest.release_sequence,
            }
        staged = self.service.stage(path)
        detail: dict[str, object] = {
            "staged": True,
            "decision": "update",
            "release_id": staged.manifest.release_id,
            "release_sequence": staged.manifest.release_sequence,
        }
        detail.update(self.service.backend.status_payload())
        return detail

    def arm_current_candidate(self) -> dict[str, object]:
        return self.service.arm()

    def confirm_boot_health(self) -> dict[str, object]:
        return self.service.confirm_boot_health()

    def reconcile(self) -> dict[str, object]:
        return self.service.reconcile()

    def _backend_layout_path(self) -> Path | None:
        backend = self.backend
        path = getattr(backend, "layout_record_path", None)
        return Path(path) if path is not None else None

    def _refresh_accepted_sequence(self) -> None:
        """Re-read the accepted sequence unless explicitly pinned.

        The health commit persists a new accepted sequence to disk; a
        long-lived (socket-activated) authority must observe it, otherwise
        an equal-sequence replay would classify as "update" instead of
        "no-update" and a rolled-back sequence could stage again.
        Explicitly constructed sequences (tests) stay pinned.
        """
        if getattr(self, "_accepted_sequence_pinned", False):
            return
        self.service.accepted_sequence = read_accepted_sequence(self.state_dir)

    def _status_record(self) -> dict[str, object]:
        inbox = SystemUpdateInbox(self.state_dir)
        try:
            raw = json.loads(inbox.status_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SystemUpdateError("no current update candidate in the inbox") from exc
        if not isinstance(raw, dict):
            raise SystemUpdateError("update status state is invalid")
        return raw

    def _current_bundle_path(self) -> Path:
        """Resolve the inbox candidate internally (never from request bytes)."""
        status = self._status_record()
        raw_path = status.get("bundle_path")
        if not isinstance(raw_path, str) or not raw_path:
            raise SystemUpdateError("no current update candidate in the inbox")
        inbox = SystemUpdateInbox(self.state_dir)
        try:
            base = inbox.inbox_dir.resolve(strict=True)
            candidate = Path(raw_path)
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(base)
            info = resolved.lstat()
        except (OSError, ValueError) as exc:
            raise SystemUpdateError("update candidate is not an inbox file") from exc
        if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise SystemUpdateError("update candidate is not a regular inbox file")
        if info.st_size <= 0 or info.st_size > MAX_BUNDLE_BYTES:
            raise SystemUpdateError("update candidate size is outside Greia bounds")
        return resolved


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
        endpoint = UpdatePrivilegedEndpoint(authority)  # type: ignore[arg-type]
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
# Trust notes (image integration contract):
# - the hardware-support pool is Greia-owned image state (default
#   ``/opt/greia-hardware-support``, same location the installer consumes);
#   it is verified at every load (manifest/payload digests, no
#   unmanifested payloads) and converted with the signed manifest
#   digest/size, so the support set stays release-bound;
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
    stale mountpoint.
    """

    layout_record_path: Path
    paths: _ProductionUpdatePaths
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
        size_bytes=_block_node_size_bytes(node),
        disk_id=_parent_disk_name(node),
    )


def _block_node_size_bytes(node: Path) -> int:
    """Re-observe a block device capacity (ioctl first, binary fallback)."""
    try:
        import fcntl
        import struct

        with node.open("rb") as handle:
            raw = fcntl.ioctl(handle.fileno(), 0x80081272, b"\x00" * 8)
        (size,) = struct.unpack("Q", raw)
        if size <= 0:
            raise UpdateBackendUnavailable(
                f"slot device capacity is outside Greia bounds: {node.name}"
            )
        return int(size)
    except UpdateBackendUnavailable:
        raise
    except Exception:
        pass
    try:
        result = _PlatformCommandAdapter(timeout_seconds=30.0).run(
            ["blockdev", "--getsize64", "--", str(node)], check=False
        )
    except Exception as exc:
        raise UpdateBackendUnavailable(
            f"slot device capacity is unobservable: {node.name}"
        ) from exc
    if result.returncode != 0:  # type: ignore[union-attr]
        raise UpdateBackendUnavailable(
            f"slot device capacity is unobservable: {node.name}"
        )
    try:
        size = int(result.stdout.strip().splitlines()[0])  # type: ignore[union-attr]
    except (IndexError, ValueError) as exc:
        raise UpdateBackendUnavailable(
            f"slot device capacity is not authoritative: {node.name}"
        ) from exc
    if size <= 0:
        raise UpdateBackendUnavailable(
            f"slot device capacity is outside Greia bounds: {node.name}"
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
    filesystem of the same stage, the verified pool reloads fresh, and
    installation delegates to the existing installer path
    (``InstallerSlotPackageInstaller``/``TargetHardwareSupportInstaller``):
    no package logic is copied here. Bind mounts the installer records are
    detached before returning so the slot unmount never sees a busy target.
    """

    def __init__(self, context: _ProductionUpdateContext) -> None:
        self._context = context

    def install(
        self, firmware: tuple[str, ...], microcode: tuple[str, ...]
    ) -> tuple[object, ...]:
        from .slot_writer import SlotFinalizeError

        tracker = self._context.filesystem_tracker
        mountpoint = tracker.current_mountpoint if tracker is not None else None
        if mountpoint is None:
            raise SlotFinalizeError(
                "slot package install requires the mounted inactive slot"
            )
        try:
            from greia_installer.hardware_support import VerifiedHardwareSupportPool
            from greia_installer.slots import InstallerSlotPackageInstaller

            pool = VerifiedHardwareSupportPool.load(
                self._context.paths.hardware_support_pool
            )
            adapter = InstallerSlotPackageInstaller(
                runner=_PlatformCommandAdapter(),  # type: ignore[arg-type]
                target_root=mountpoint,
                pool=pool,
                mounted=self._context.mounted,
            )
            before = len(self._context.mounted)
            try:
                return adapter.install(tuple(firmware), tuple(microcode))  # type: ignore[return-value]
            finally:
                self._detach_added_mounts(before)
        except SlotFinalizeError:
            raise
        except UpdateBackendUnavailable:
            raise
        except Exception as exc:
            raise SlotFinalizeError(
                f"slot package install failed fail-closed: {_bounded_reason(exc)}"
            ) from exc

    def _detach_added_mounts(self, before: int) -> None:
        runner = _PlatformCommandAdapter(timeout_seconds=30.0)
        added = self._context.mounted[before:]
        for mountpoint in reversed(added):
            try:
                runner.run(["umount", "--", str(mountpoint)], check=False)
            except Exception:
                pass
        del self._context.mounted[before:]


def build_production_update_seams(
    *, layout_record_path: Path | None = None
) -> UpdateSlotSeams:
    """Compose the installed A/B production seams (no device IO here).

    Binds all eight destination factories over the trusted layout record
    path plus freshly re-observed topology at every factory call. Safe to
    compose on any machine: with no A/B authority (or no devices) each
    factory fails closed with :class:`UpdateBackendUnavailable` instead of
    addressing a drive. Explicitly injected seams remain available by
    passing them to the backend/service directly.
    """
    context = _ProductionUpdateContext(
        layout_record_path=(
            Path(layout_record_path)
            if layout_record_path is not None
            else installed_layout_record_path()
        ),
        paths=_production_paths(),
    )
    return UpdateSlotSeams(
        slot_store_factory=_production_slot_store_factory(context),
        filesystem_factory=_production_filesystem_factory(context),
        package_installer_factory=_production_package_installer_factory(context),
        inventory_factory=_production_inventory_factory(context),
        support_set_factory=_production_support_set_factory(context),
        profile_policy_factory=_production_profile_policy_factory(),
        selection_factory=_production_selection_factory(context),
        installed_contract_factory=_production_installed_contract_factory(),
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


def _production_support_set_factory(
    context: _ProductionUpdateContext,
) -> Callable[[object], object]:
    """Release-bound support set from the verified image pool + manifest."""

    def _factory(bundle: object) -> object:
        try:
            from greia_installer.hardware_support import VerifiedHardwareSupportPool
            from greia_installer.slots import pool_to_support_set

            manifest = getattr(bundle, "manifest")
            pool = VerifiedHardwareSupportPool.load(
                context.paths.hardware_support_pool
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
                IsenkramHardwareSupportResolver(),
                X86MicrocodeResolver(),
            )
        ).resolve(snapshot)
        if not plan.complete:
            return None
        return resolve_hardware_selection(plan=plan, support=support)  # type: ignore[arg-type]

    return _factory


def _production_installed_contract_factory() -> Callable[[], bytes]:
    """Installed persistent-state contract (canonical registry bytes)."""

    def _factory() -> bytes:
        return build_persistent_state_contract_bytes()

    return _factory


def build_live_update_service(
    *,
    state_dir: Path | None = None,
    trusted_key_dir: Path | None = None,
    layout_record_path: Path | None = None,
    boot_backend: object | None = None,
    boot_backend_auto: bool = True,
    seams: UpdateSlotSeams | None = None,
) -> SystemUpdateServiceAuthority:
    """Compose the production authority from Greia-owned environment state.

    Trust (keys), compatibility (release identity) and layout authority
    resolve from Greia-owned state on every composition; the boot one-shot
    backend attaches to the boot-control ``grubenv`` when present (stays
    unwired fail-closed where there is no boot-control state, e.g.
    single-root layouts). With ``seams=None`` (the shipped ``main()``
    path) the inactive-slot destination factories are the production
    seams from :func:`build_production_update_seams`: the exact installed
    updater stages only the freshly resolved inactive slot, and reports
    unavailable fail-closed where no A/B authority or device exists.
    Explicitly injected seams remain a test/harness feature.
    """
    root = (
        Path(state_dir)
        if state_dir is not None
        else Path(os.environ.get(UPDATE_STATE_DIR_ENV, UPDATE_STATE_DIR_DEFAULT))
    )
    keys = (
        Path(trusted_key_dir)
        if trusted_key_dir is not None
        else Path(
            os.environ.get(UPDATE_TRUSTED_KEY_DIR_ENV, UPDATE_TRUSTED_KEY_DIR_DEFAULT)
        )
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
        else build_production_update_seams(layout_record_path=record_path),
        boot_backend=resolved_boot_backend,
    )
    return SystemUpdateServiceAuthority(root, keys, identity, backend)


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
    authority (trust, layout, journal, boot one-shot backend, production
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
