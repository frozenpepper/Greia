from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
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
SCHEMA_VERSION = 1
MAX_MANIFEST_BYTES = 64 * 1024
MAX_SIGNATURE_BYTES = 16 * 1024
MAX_PAYLOAD_BYTES = 1536 * 1024 * 1024
MAX_BUNDLE_BYTES = 2 * 1024 * 1024 * 1024
MIN_INBOX_FREE_BYTES = 128 * 1024 * 1024
_MAX_RELEASE_ID = 96
_MAX_VERSION = 64
_MAX_NOTES = 4096
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class SystemUpdateError(RuntimeError):
    pass


class UpdateBundleError(SystemUpdateError):
    pass


class UpdateSignatureError(UpdateBundleError):
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
    platform_family: str
    architecture: str
    profile: str
    signer: str
    payload_sha256: str
    payload_size: int
    release_notes: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise UpdateBundleError(
                f"unsupported system-update schema {self.schema_version}"
            )
        _validate_identifier(self.release_id, "release_id", _MAX_RELEASE_ID)
        _validate_text(self.version, "version", _MAX_VERSION)
        _validate_identifier(self.platform_family, "platform_family", 64)
        _validate_identifier(self.architecture, "architecture", 32)
        _validate_identifier(self.profile, "profile", 96)
        _validate_identifier(self.signer, "signer", 96)
        if not re.fullmatch(r"[0-9a-f]{64}", self.payload_sha256):
            raise UpdateBundleError("payload_sha256 must be lower-case SHA-256 hex")
        if self.payload_size <= 0 or self.payload_size > MAX_PAYLOAD_BYTES:
            raise UpdateBundleError("payload_size is outside Greia bounds")
        if not isinstance(self.release_notes, str) or len(self.release_notes) > _MAX_NOTES:
            raise UpdateBundleError("release_notes exceeds Greia bound")

    def as_json_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "release_id": self.release_id,
            "version": self.version,
            "platform_family": self.platform_family,
            "architecture": self.architecture,
            "profile": self.profile,
            "signer": self.signer,
            "payload": {
                "name": PAYLOAD_NAME,
                "sha256": self.payload_sha256,
                "size": self.payload_size,
                "kind": "system-slot-image",
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
            "platform_family",
            "architecture",
            "profile",
            "signer",
            "payload",
            "release_notes",
        }
        if set(raw) != expected:
            raise UpdateBundleError("manifest has unknown or missing top-level fields")
        payload = raw.get("payload")
        if not isinstance(payload, dict) or set(payload) != {"name", "sha256", "size", "kind"}:
            raise UpdateBundleError("manifest payload object is invalid")
        if payload.get("name") != PAYLOAD_NAME or payload.get("kind") != "system-slot-image":
            raise UpdateBundleError("unsupported system-update payload contract")
        values = {
            "schema_version": raw.get("schema_version"),
            "release_id": raw.get("release_id"),
            "version": raw.get("version"),
            "platform_family": raw.get("platform_family"),
            "architecture": raw.get("architecture"),
            "profile": raw.get("profile"),
            "signer": raw.get("signer"),
            "payload_sha256": payload.get("sha256"),
            "payload_size": payload.get("size"),
            "release_notes": raw.get("release_notes"),
        }
        if isinstance(values["schema_version"], bool) or not isinstance(values["schema_version"], int):
            raise UpdateBundleError("schema_version must be an integer")
        if isinstance(values["payload_size"], bool) or not isinstance(values["payload_size"], int):
            raise UpdateBundleError("payload size must be an integer")
        for key in (
            "release_id",
            "version",
            "platform_family",
            "architecture",
            "profile",
            "signer",
            "payload_sha256",
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


class SystemUpdateInbox:
    """Unprivileged single-candidate inbox for Parent-delivered update bytes.

    Receiving a bundle is not activation authority. This layer validates archive
    structure and payload integrity, stores the selected candidate by content
    digest and removes older untrusted inbox candidates. Cryptographic trust and
    inactive-slot activation are re-established by the privileged
    SystemUpdateService before any system write.
    """

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = Path(state_dir)
        self.inbox_dir = self.state_dir / "system-updates" / "inbox"
        self.status_path = self.state_dir / "system-updates" / "status.json"

    def receive(self, bundle_path: Path) -> InspectedUpdateBundle:
        inspected = inspect_update_bundle(bundle_path)
        source_digest = sha256_file(bundle_path)
        incoming_size = bundle_path.stat().st_size
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.inbox_dir, 0o700)
        self._remove_stale_temporaries()
        destination = self.inbox_dir / (
            f"{inspected.manifest.release_id}-{source_digest}{BUNDLE_SUFFIX}"
        )
        if destination.exists():
            if not destination.is_file() or sha256_file(destination) != source_digest:
                raise UpdateBundleError("content-addressed update inbox collision")
        else:
            free_bytes = shutil.disk_usage(self.inbox_dir).free
            if free_bytes < incoming_size + MIN_INBOX_FREE_BYTES:
                raise UpdateBundleError(
                    "not enough free space to receive update while preserving Greia reserve"
                )
            temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
            try:
                with bundle_path.open("rb") as source, temporary.open("xb") as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
                os.chmod(temporary, 0o600)
                if sha256_file(temporary) != source_digest:
                    raise UpdateBundleError("queued update copy digest mismatch")
                try:
                    # Hard-link publication is atomic and never replaces an
                    # existing content-addressed artifact. HTTPServer is
                    # single-threaded today, but this also fails closed if a
                    # future producer races the same digest into the inbox.
                    os.link(temporary, destination)
                except FileExistsError:
                    if not destination.is_file() or sha256_file(destination) != source_digest:
                        raise UpdateBundleError("content-addressed update inbox collision")
                os.chmod(destination, 0o600)
            finally:
                temporary.unlink(missing_ok=True)
        self._prune_other_candidates(destination)
        payload = {
            "state": UpdateState.RECEIVED.value,
            "release": inspected.manifest.as_json_dict(),
            "bundle_path": str(destination),
            "bundle_sha256": source_digest,
            "signature_verified": False,
            "activation_available": False,
        }
        _atomic_json(self.status_path, payload)
        return InspectedUpdateBundle(destination, inspected.manifest, inspected.signature)

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

    def _remove_stale_temporaries(self) -> None:
        try:
            for candidate in self.inbox_dir.glob(".*.tmp"):
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
    ) -> None:
        self.state_dir = Path(state_dir)
        self.trusted_key_dir = Path(trusted_key_dir)
        self.identity = identity
        self.backend = backend or UnavailableSystemUpdateBackend()

    def verify(self, bundle_path: Path) -> InspectedUpdateBundle:
        inspected = inspect_update_bundle(bundle_path)
        verify_update_signature(inspected, self.trusted_key_dir)
        self.identity.assert_compatible(inspected.manifest)
        return inspected

    def stage(self, bundle_path: Path) -> InspectedUpdateBundle:
        inspected = self.verify(bundle_path)
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
        }


def build_update_bundle(
    *,
    payload_path: Path,
    output_path: Path,
    version: str,
    release_id: str,
    platform_family: str,
    architecture: str,
    profile: str,
    signer: str,
    private_key_path: Path,
    release_notes: str = "",
) -> UpdateManifest:
    payload_path = Path(payload_path)
    output_path = Path(output_path)
    if not payload_path.is_file():
        raise UpdateBundleError("payload is not a regular file")
    payload_size = payload_path.stat().st_size
    if payload_size <= 0 or payload_size > MAX_PAYLOAD_BYTES:
        raise UpdateBundleError("payload size is outside Greia bounds")
    manifest = UpdateManifest(
        schema_version=SCHEMA_VERSION,
        release_id=release_id,
        version=version,
        platform_family=platform_family,
        architecture=architecture,
        profile=profile,
        signer=signer,
        payload_sha256=sha256_file(payload_path),
        payload_size=payload_size,
        release_notes=release_notes,
    )
    signature = SignatureEnvelope(
        schema_version=SCHEMA_VERSION,
        algorithm="ed25519",
        signer=signer,
        signature=_sign_ed25519(private_key_path, manifest.canonical_bytes()),
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
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
            allowZip64=True,
        ) as archive:
            archive.writestr(MANIFEST_NAME, manifest.canonical_bytes())
            archive.writestr(SIGNATURE_NAME, signature.as_json_bytes())
            archive.write(payload_path, PAYLOAD_NAME)
        if temporary.stat().st_size > MAX_BUNDLE_BYTES:
            raise UpdateBundleError("generated update bundle exceeds Greia bound")
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return manifest


def inspect_update_bundle(path: Path) -> InspectedUpdateBundle:
    path = Path(path)
    if not path.is_file():
        raise UpdateBundleError("update bundle is not a regular file")
    if path.stat().st_size <= 0 or path.stat().st_size > MAX_BUNDLE_BYTES:
        raise UpdateBundleError("update bundle size is outside Greia bounds")
    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if names != [MANIFEST_NAME, SIGNATURE_NAME, PAYLOAD_NAME]:
                raise UpdateBundleError("update bundle members/order are invalid")
            for info in infos:
                if info.is_dir() or "/" in info.filename or "\\" in info.filename:
                    raise UpdateBundleError("update bundle contains an unsafe member")
                if info.flag_bits & 0x1:
                    raise UpdateBundleError("encrypted ZIP members are not supported")
            manifest_info, signature_info, payload_info = infos
            if manifest_info.file_size > MAX_MANIFEST_BYTES:
                raise UpdateBundleError("manifest exceeds Greia bound")
            if signature_info.file_size > MAX_SIGNATURE_BYTES:
                raise UpdateBundleError("signature envelope exceeds Greia bound")
            if payload_info.file_size <= 0 or payload_info.file_size > MAX_PAYLOAD_BYTES:
                raise UpdateBundleError("payload exceeds Greia bound")
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
            digest = hashlib.sha256()
            with archive.open(PAYLOAD_NAME, "r") as payload:
                while True:
                    chunk = payload.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
            if digest.hexdigest() != manifest.payload_sha256:
                raise UpdateBundleError("payload digest does not match signed manifest")
    except (zipfile.BadZipFile, OSError) as exc:
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
