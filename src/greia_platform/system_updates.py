from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


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
_PERSISTENT_NAMESPACES = (
    "parent-credentials",
    "child-profiles",
    "activity-saves",
    "progression-rewards",
    "device-settings",
    "hardware-receipts",
    "update-acceptance-state",
    "layout-authority",
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
