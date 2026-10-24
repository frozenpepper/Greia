"""Installed layout model, durable-path audit and PERSIST namespace map.

L7-PERSIST (R0/R1 source scope): pure data model plus read-only validation.
No partition, mount, filesystem or boot writes live here; slot writers and
boot transactions belong to L7-SLOTS/L7-BOOT.

Partition identity is adapter-specific and observed (TAKEOVER-1 T1.1, D51):
``PARTUUID`` is not globally "a UUID object". Each layout adapter owns
parsing/normalization behind one semantic interface
(:class:`PartitionIdentity` with a ``scheme`` of ``GPT_GUID`` or
``MBR_PARTUUID``). MBR PARTUUIDs are the Linux ``<disk-signature>-<partno>``
form (e.g. ``1234abcd-02``), never a minted UUID4; GPT PARTUUIDs are
canonical lowercase GUIDs. Filesystem UUIDs are always canonical UUIDs.

Authoritative identifier sets (layout adapters, boot backends, platform
families, slot/PERSIST size floors) are owned by ``tools/build_profile.py``
(L7-PROFILES). This module mirrors them with a sync test instead of
re-parsing build profiles at runtime, so installed-image validation keeps
working when only the installed PERSIST tree is available.

The canonical ``persistent-state-contract.json`` shape (schema, canonical
JSON, bounds) is owned by :mod:`greia_platform.system_updates`; this module
only decides *which* namespaces the audited tree requires and emits bytes
through that authority.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import stat
import tempfile
import uuid
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Mapping

from .system_updates import (
    UpdateManifest,
    build_persistent_state_contract_bytes,
    verify_persistent_state_contract_bytes,
)


class PersistentLayoutError(RuntimeError):
    """Installed layout record, audit or namespace map is invalid."""


class PersistRecoveryRequired(PersistentLayoutError):
    """Existing install cannot prove its PERSIST state: fail into recovery.

    Raised instead of minting blank child identity when the layout record is
    missing, corrupt, mis-owned, non-canonical, or contradicted by block
    topology. Callers must route to recovery, never to fresh initialization.
    """


# ---------------------------------------------------------------------------
# Authority mirrors (owned by tools/build_profile.py — see sync test)
# ---------------------------------------------------------------------------

#: Strict schema version of ``installed-layout.json``.
LAYOUT_RECORD_SCHEMA_VERSION = 1

#: File name of the root-owned machine-readable layout record on PERSIST.
LAYOUT_RECORD_NAME = "installed-layout.json"

#: Canonical contract file name (matches system_updates.PERSISTENT_CONTRACT_NAME).
CONTRACT_NAME = "persistent-state-contract.json"

#: Readability/migration marker consumed by the installed update service.
PERSIST_SCHEMA_MARKER_NAME = "persist-schema.json"

#: Layout record must be readable only by its owner (root on device).
LAYOUT_RECORD_MODE = 0o600

#: State directory name at the PERSIST filesystem root.
PERSIST_STATE_DIRNAME = "greia"

#: Namespace directory name holding one empty domain directory per namespace.
PERSIST_NAMESPACES_DIRNAME = "namespaces"

#: Upper bound for a stored layout record (records are small by construction).
MAX_LAYOUT_RECORD_BYTES = 16 * 1024

#: Layout adapters bound by L7-PROFILES (tools/build_profile.py).
ALLOWED_LAYOUT_ADAPTERS = frozenset(
    {
        "bios-single-ext4",
        "legacy-bios-ab-v1",
        "modern-gpt-ab-v1",
        "pi-mbr-tryboot-ab-v1",
    }
)

#: A/B layouts carry two system slots; anything else is single-root.
AB_LAYOUT_ADAPTERS = frozenset(
    {
        "legacy-bios-ab-v1",
        "modern-gpt-ab-v1",
        "pi-mbr-tryboot-ab-v1",
    }
)

#: Pi layouts share one ancestry/backend family.
PI_LAYOUT_ADAPTERS = frozenset({"pi-mbr-tryboot-ab-v1"})

#: Boot backends bound by L7-PROFILES (tools/build_profile.py).
ALLOWED_BOOT_BACKENDS = frozenset({"grub-ab-v1", "pi-tryboot-ab-v1", "none-v1"})

#: Platform families bound by L7-PROFILES (tools/build_profile.py).
ALLOWED_PLATFORM_FAMILIES = frozenset(
    {"legacy-x86", "standard-x86-64", "arm64", "developer-vm"}
)

#: Boot-control role kinds keyed by boot backend.
BOOT_CONTROL_KINDS = {
    "none-v1": "none-v1",
    "grub-ab-v1": "grub-env-v1",
    "pi-tryboot-ab-v1": "pi-tryboot-v1",
}

#: Slot-size source bounds from L7-PROFILES (tools/build_profile.py).
MIN_SYSTEM_SLOT_BYTES = 1024 * 1024 * 1024
MAX_SYSTEM_SLOT_BYTES = 2 * 1024 * 1024 * 1024

#: PERSIST floor source bound from L7-PROFILES (tools/build_profile.py).
MIN_PERSIST_BYTES = 256 * 1024 * 1024

#: Partition roles addressable by a layout record.
PARTITION_ROLES = ("system-a", "system-b", "persist")


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _canonical_bytes(value: Mapping[str, object]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _require_canonical_uuid(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise PersistentLayoutError(f"{field} must be text")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise PersistentLayoutError(f"{field} is not a valid UUID") from exc
    if parsed.hex != value.replace("-", "").lower() or str(parsed) != value.lower():
        raise PersistentLayoutError(f"{field} must be canonical lowercase UUID text")
    return str(parsed)


# ---------------------------------------------------------------------------
# Adapter-specific partition-identity schemes (TAKEOVER-1 T1.1, D51)
# ---------------------------------------------------------------------------

#: Partition-identity scheme bound by each layout adapter. GPT layouts use
#: GUID PARTUUIDs (canonical UUID text); MBR layouts use the Linux
#: ``<disk-signature>-<partition-number>`` form, never a minted UUID4.
PARTITION_SCHEME_GPT_GUID = "GPT_GUID"
PARTITION_SCHEME_MBR_PARTUUID = "MBR_PARTUUID"
PARTITION_SCHEMES = frozenset({PARTITION_SCHEME_GPT_GUID, PARTITION_SCHEME_MBR_PARTUUID})

#: Expected identity scheme per layout adapter id. Pi MBR layouts share the
#: MBR form; their own extended-partition observation rules arrive with the
#: Phase 8D execution path behind the same semantic interface.
LAYOUT_PARTITION_SCHEMES: dict[str, str] = {
    "bios-single-ext4": PARTITION_SCHEME_MBR_PARTUUID,
    "legacy-bios-ab-v1": PARTITION_SCHEME_MBR_PARTUUID,
    "modern-gpt-ab-v1": PARTITION_SCHEME_GPT_GUID,
    "pi-mbr-tryboot-ab-v1": PARTITION_SCHEME_MBR_PARTUUID,
}

#: MBR disk signatures are 8 lowercase hex digits (the DOS disk identifier).
_MBR_SIGNATURE_RE = re.compile(r"^[0-9a-f]{8}$")

#: Highest MBR partition number the normalizer accepts (matches the
#: installer ``partition_number_path`` bound; msdos paths stay far below it).
MAX_MBR_PARTITION_NUMBER = 128


def normalize_mbr_partuuid(value: object, *, field: str) -> str:
    """Normalize an MBR PARTUUID to ``<signature>-<NN>`` (fail closed).

    Accepts the Linux ``blkid``/``/dev/disk/by-partuuid`` spellings:
    lowercase or uppercase 8-hex signature, partition number with or
    without a leading zero (``-2`` and ``-02`` both mean partition 2).
    A canonical UUID4 (or any non-MBR text) is rejected: minting an
    independent UUID4 and labeling it an MBR PARTUUID is never valid.
    """
    if not isinstance(value, str):
        raise PersistentLayoutError(f"{field} must be text")
    text = value.strip()
    if "-" not in text:
        raise PersistentLayoutError(
            f"{field} is not an MBR PARTUUID (expected <disk-signature>-<partno>)"
        )
    signature_text, separator, number_text = text.rpartition("-")
    if not separator or not signature_text or not number_text:
        raise PersistentLayoutError(
            f"{field} is not an MBR PARTUUID (expected <disk-signature>-<partno>)"
        )
    signature = signature_text.lower()
    if signature.startswith("0x"):
        signature = signature[2:]
    if not _MBR_SIGNATURE_RE.fullmatch(signature):
        raise PersistentLayoutError(
            f"{field} carries an invalid MBR disk signature (expected 8 hex digits)"
        )
    if not number_text.isascii() or not number_text.isdigit():
        raise PersistentLayoutError(
            f"{field} carries an invalid MBR partition number"
        )
    number = int(number_text, 10)
    if not 1 <= number <= MAX_MBR_PARTITION_NUMBER:
        raise PersistentLayoutError(
            f"{field} carries an MBR partition number outside Greia bounds"
        )
    return f"{signature}-{number:02d}"


def split_mbr_partuuid(value: str) -> tuple[str, int]:
    """Split a normalized MBR PARTUUID into ``(disk_signature, number)``."""
    normalized = normalize_mbr_partuuid(value, field="partuuid")
    signature, _, number_text = normalized.rpartition("-")
    return signature, int(number_text, 10)


def require_mbr_disk_signature(value: object, *, field: str) -> str:
    """Normalize an MBR disk identifier to 8 lowercase hex digits.

    Accepts the ``blkid PTUUID`` / ``sfdisk disk identifier`` spellings
    (optional ``0x`` prefix, either case). The all-zero signature fails
    closed: it proves no authority minted/assigned a disk identity.
    """
    if not isinstance(value, str):
        raise PersistentLayoutError(f"{field} must be text")
    text = value.strip().lower()
    if text.startswith("0x"):
        text = text[2:]
    if not _MBR_SIGNATURE_RE.fullmatch(text):
        raise PersistentLayoutError(
            f"{field} is not an MBR disk signature (expected 8 hex digits)"
        )
    if text == "00000000":
        raise PersistentLayoutError(f"{field} carries no disk identity")
    return text


def normalize_partuuid_for_scheme(scheme: str, value: object, *, field: str) -> str:
    """Normalize a PARTUUID with the parser owned by ``scheme``."""
    if scheme == PARTITION_SCHEME_MBR_PARTUUID:
        return normalize_mbr_partuuid(value, field=field)
    if scheme == PARTITION_SCHEME_GPT_GUID:
        return _require_canonical_uuid(value, field=field)
    raise PersistentLayoutError(f"{field} carries an unknown identity scheme: {scheme!r}")


def infer_partuuid_scheme(value: object) -> str:
    """Infer the identity scheme from a PARTUUID value's shape (read-only).

    Used only for scheme-less legacy records (PROVISIONAL compat, see
    :class:`PartitionIdentity`); new authority always carries an explicit
    scheme. UUID-shaped values infer ``GPT_GUID``; MBR-shaped values infer
    ``MBR_PARTUUID``; anything else fails closed.
    """
    if isinstance(value, str):
        try:
            normalize_mbr_partuuid(value, field="partuuid")
        except PersistentLayoutError:
            pass
        else:
            return PARTITION_SCHEME_MBR_PARTUUID
        try:
            _require_canonical_uuid(value, field="partuuid")
        except PersistentLayoutError:
            pass
        else:
            return PARTITION_SCHEME_GPT_GUID
    raise PersistentLayoutError("partuuid matches no known identity scheme")


def _require_hex_digest(value: object, *, field: str, length: int = 64) -> str:
    if not isinstance(value, str) or len(value) != length:
        raise PersistentLayoutError(f"{field} must be {length} hex characters")
    try:
        bytes.fromhex(value)
    except ValueError as exc:
        raise PersistentLayoutError(f"{field} must be lowercase hex") from exc
    if value != value.lower():
        raise PersistentLayoutError(f"{field} must be lowercase hex")
    return value


def _require_identifier(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise PersistentLayoutError(f"{field} must be non-empty text")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    if not value[0].isalnum() or any(c not in allowed for c in value):
        raise PersistentLayoutError(f"{field} is not a safe identifier")
    return value


def _atomic_write_file(path: Path, payload: bytes, *, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Installed layout record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PartitionIdentity:
    """One partition bound by scheme, PARTUUID plus filesystem UUID.

    ``scheme`` is ``GPT_GUID`` or ``MBR_PARTUUID`` (per-adapter parsers;
    MBR values are the observed ``<disk-signature>-<partno>`` form, never
    a minted UUID4). ``filesystem_uuid`` is always a canonical UUID.

    Scheme-less ``{"partuuid", "filesystem_uuid"}`` mappings still parse
    (PROVISIONAL compat for the pre-T1.1 orchestrator path, which T3-INSTALL
    rewires to observed identities): the scheme is inferred from the value
    shape and the identity re-emits without a scheme, so legacy records
    round-trip byte-identically. New MBR authority must always carry an
    explicit scheme so the layout binding below can prove no UUID4 is
    labeled an MBR PARTUUID.
    """

    scheme: str
    partuuid: str
    filesystem_uuid: str
    scheme_explicit: bool = True

    @classmethod
    def from_dict(cls, raw: object, *, field: str) -> "PartitionIdentity":
        if not isinstance(raw, dict):
            raise PersistentLayoutError(f"{field} must hold a partition identity")
        keys = set(raw)
        if keys == {"partuuid", "filesystem_uuid"}:
            partuuid_raw = raw["partuuid"]
            scheme = infer_partuuid_scheme(partuuid_raw)
            return cls(
                scheme=scheme,
                partuuid=normalize_partuuid_for_scheme(
                    scheme, partuuid_raw, field=f"{field}.partuuid"
                ),
                filesystem_uuid=_require_canonical_uuid(
                    raw["filesystem_uuid"], field=f"{field}.filesystem_uuid"
                ),
                scheme_explicit=False,
            )
        if keys != {"scheme", "partuuid", "filesystem_uuid"}:
            raise PersistentLayoutError(
                f"{field} must hold scheme/partuuid/filesystem_uuid"
            )
        scheme = raw["scheme"]
        if scheme not in PARTITION_SCHEMES:
            raise PersistentLayoutError(f"{field}.scheme is unknown: {scheme!r}")
        assert isinstance(scheme, str)
        return cls(
            scheme=scheme,
            partuuid=normalize_partuuid_for_scheme(
                scheme, raw["partuuid"], field=f"{field}.partuuid"
            ),
            filesystem_uuid=_require_canonical_uuid(
                raw["filesystem_uuid"], field=f"{field}.filesystem_uuid"
            ),
            scheme_explicit=True,
        )

    def as_dict(self) -> dict[str, str]:
        if self.scheme_explicit:
            return {
                "filesystem_uuid": self.filesystem_uuid,
                "partuuid": self.partuuid,
                "scheme": self.scheme,
            }
        return {"filesystem_uuid": self.filesystem_uuid, "partuuid": self.partuuid}

    @property
    def disk_signature(self) -> str | None:
        """MBR disk signature, or ``None`` for GPT identities."""
        if self.scheme != PARTITION_SCHEME_MBR_PARTUUID:
            return None
        signature, _ = split_mbr_partuuid(self.partuuid)
        return signature


@dataclass(frozen=True, slots=True)
class BootControl:
    """Boot-control roles: which selector family owns the active slot."""

    kind: str
    active_slot: str | None

    @classmethod
    def from_dict(cls, raw: object) -> "BootControl":
        if not isinstance(raw, dict) or set(raw) != {"active_slot", "kind"}:
            raise PersistentLayoutError("boot_control must hold kind/active_slot")
        kind = raw["kind"]
        if kind not in ("none-v1", "grub-env-v1", "pi-tryboot-v1"):
            raise PersistentLayoutError("boot_control.kind is unknown")
        active_slot = raw["active_slot"]
        if active_slot is not None and active_slot not in ("A", "B"):
            raise PersistentLayoutError("boot_control.active_slot must be A, B or null")
        return cls(kind=kind, active_slot=active_slot)

    def as_dict(self) -> dict[str, object]:
        return {"active_slot": self.active_slot, "kind": self.kind}


def _require_record_scheme_binding(
    layout_id: str, identities: tuple[tuple[str, PartitionIdentity], ...]
) -> None:
    """Prove scheme-explicit identities match the layout adapter (T1.1).

    Identities carrying an explicit ``scheme`` must equal the adapter's
    expected scheme, and every MBR identity set must share one disk
    signature: a mixed signature or a UUID4 labeled as an MBR PARTUUID
    fails closed here, before any boot configuration can commit to it.

    Scheme-less legacy mappings (``scheme_explicit=False``) infer their
    scheme from the value shape and stay parseable as PROVISIONAL compat
    for the pre-T1.1 orchestrator path, which T3-INSTALL rewires to
    observed identities.
    """
    expected = LAYOUT_PARTITION_SCHEMES.get(layout_id)
    if expected is None:
        raise PersistentLayoutError(f"unknown layout_id: {layout_id!r}")
    for role, identity in identities:
        if identity.scheme_explicit and identity.scheme != expected:
            if (
                identity.scheme == PARTITION_SCHEME_GPT_GUID
                and expected == PARTITION_SCHEME_MBR_PARTUUID
            ):
                raise PersistentLayoutError(
                    f"{role} carries a GUID where layout {layout_id!r} requires "
                    "an observed MBR PARTUUID: refusing a fabricated MBR identity"
                )
            raise PersistentLayoutError(
                f"{role} scheme {identity.scheme!r} does not match layout "
                f"{layout_id!r} (expected {expected!r})"
            )
    mbr_signatures = {
        split_mbr_partuuid(identity.partuuid)[0]
        for _, identity in identities
        if identity.scheme == PARTITION_SCHEME_MBR_PARTUUID
    }
    if len(mbr_signatures) > 1:
        raise PersistentLayoutError(
            "layout MBR PARTUUIDs span multiple disk signatures: "
            "refusing a cross-disk identity binding"
        )


_LAYOUT_RECORD_FIELDS = frozenset(
    {
        "accepted_release_id",
        "accepted_slot",
        "boot_backend",
        "boot_control",
        "install_profile",
        "install_target_sha256",
        "installed_at_unix",
        "layout_id",
        "persist",
        "platform_family",
        "schema_version",
        "slot_bytes",
        "system_a",
        "system_b",
    }
)


@dataclass(frozen=True, slots=True)
class InstalledLayoutRecord:
    """Machine-readable installed-layout authority kept on PERSIST.

    ``/dev/sdX`` transport names are never authority and are rejected on
    parse; Parent-controlled fields are rejected by the strict field set.
    """

    schema_version: int
    layout_id: str
    platform_family: str
    boot_backend: str
    install_profile: str
    install_target_sha256: str
    installed_at_unix: int
    boot_control: BootControl
    system_a: PartitionIdentity
    system_b: PartitionIdentity | None
    persist: PartitionIdentity
    slot_bytes: int
    accepted_slot: str | None
    accepted_release_id: str

    @classmethod
    def from_dict(cls, raw: object) -> "InstalledLayoutRecord":
        if not isinstance(raw, dict):
            raise PersistentLayoutError("layout record must be a JSON object")
        unknown = set(raw) - _LAYOUT_RECORD_FIELDS
        if unknown:
            raise PersistentLayoutError(
                "layout record carries non-authoritative fields: "
                + ", ".join(sorted(str(key) for key in unknown))
            )
        missing = _LAYOUT_RECORD_FIELDS - set(raw)
        if missing:
            raise PersistentLayoutError(
                "layout record is missing fields: " + ", ".join(sorted(missing))
            )
        schema_version = raw["schema_version"]
        if schema_version != LAYOUT_RECORD_SCHEMA_VERSION:
            raise PersistentLayoutError("layout record schema is unsupported")
        layout_id = raw["layout_id"]
        if layout_id not in ALLOWED_LAYOUT_ADAPTERS:
            raise PersistentLayoutError(f"unknown layout_id: {layout_id!r}")
        platform_family = raw["platform_family"]
        if platform_family not in ALLOWED_PLATFORM_FAMILIES:
            raise PersistentLayoutError(f"unknown platform_family: {platform_family!r}")
        if (layout_id in PI_LAYOUT_ADAPTERS) != (platform_family == "arm64"):
            raise PersistentLayoutError("platform_family does not match layout_id ancestry")
        boot_backend = raw["boot_backend"]
        if boot_backend not in ALLOWED_BOOT_BACKENDS:
            raise PersistentLayoutError(f"unknown boot_backend: {boot_backend!r}")
        is_ab = layout_id in AB_LAYOUT_ADAPTERS
        if is_ab:
            expected_backend = (
                "pi-tryboot-ab-v1" if layout_id in PI_LAYOUT_ADAPTERS else "grub-ab-v1"
            )
            if boot_backend != expected_backend:
                raise PersistentLayoutError("boot_backend does not match layout_id")
        elif boot_backend != "none-v1":
            raise PersistentLayoutError("single-root layout requires boot_backend none-v1")
        boot_control = BootControl.from_dict(raw["boot_control"])
        if boot_control.kind != BOOT_CONTROL_KINDS[boot_backend]:
            raise PersistentLayoutError("boot_control.kind does not match boot_backend")
        if (boot_control.active_slot is None) == is_ab:
            raise PersistentLayoutError(
                "boot_control.active_slot must be set exactly for A/B layouts"
            )
        accepted_slot = raw["accepted_slot"]
        if accepted_slot is not None and accepted_slot not in ("A", "B"):
            raise PersistentLayoutError("accepted_slot must be A, B or null")
        if (accepted_slot is None) == is_ab:
            raise PersistentLayoutError(
                "accepted_slot must be set exactly for A/B layouts"
            )
        slot_bytes = raw["slot_bytes"]
        if (
            not isinstance(slot_bytes, int)
            or isinstance(slot_bytes, bool)
            or not MIN_SYSTEM_SLOT_BYTES <= slot_bytes <= MAX_SYSTEM_SLOT_BYTES
        ):
            raise PersistentLayoutError("slot_bytes is outside the Greia slot bound")
        system_a = PartitionIdentity.from_dict(raw["system_a"], field="system_a")
        system_b_raw = raw["system_b"]
        if is_ab:
            if system_b_raw is None:
                raise PersistentLayoutError("A/B layout requires system_b")
            system_b = PartitionIdentity.from_dict(system_b_raw, field="system_b")
        else:
            if system_b_raw is not None:
                raise PersistentLayoutError("single-root layout must carry system_b null")
            system_b = None
        persist = PartitionIdentity.from_dict(raw["persist"], field="persist")
        identities = (
            system_a.partuuid,
            system_a.filesystem_uuid,
            persist.partuuid,
            persist.filesystem_uuid,
        )
        if system_b is not None:
            identities += (system_b.partuuid, system_b.filesystem_uuid)
        if len(set(identities)) != len(identities):
            raise PersistentLayoutError("layout partition identities must be unique")
        _require_record_scheme_binding(
            layout_id,
            tuple(
                (role, identity)
                for role, identity in (
                    ("system_a", system_a),
                    *((("system_b", system_b),) if system_b is not None else ()),
                    ("persist", persist),
                )
            ),
        )
        installed_at_unix = raw["installed_at_unix"]
        if (
            not isinstance(installed_at_unix, int)
            or isinstance(installed_at_unix, bool)
            or installed_at_unix < 0
            or installed_at_unix > (1 << 40)
        ):
            raise PersistentLayoutError("installed_at_unix is not a valid timestamp")
        return cls(
            schema_version=LAYOUT_RECORD_SCHEMA_VERSION,
            layout_id=layout_id,
            platform_family=_require_identifier(
                platform_family, field="platform_family"
            ),
            boot_backend=boot_backend,
            install_profile=_require_identifier(
                raw["install_profile"], field="install_profile"
            ),
            install_target_sha256=_require_hex_digest(
                raw["install_target_sha256"], field="install_target_sha256"
            ),
            installed_at_unix=installed_at_unix,
            boot_control=boot_control,
            system_a=system_a,
            system_b=system_b,
            persist=persist,
            slot_bytes=slot_bytes,
            accepted_slot=accepted_slot,
            accepted_release_id=_require_identifier(
                raw["accepted_release_id"], field="accepted_release_id"
            ),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted_release_id": self.accepted_release_id,
            "accepted_slot": self.accepted_slot,
            "boot_backend": self.boot_backend,
            "boot_control": self.boot_control.as_dict(),
            "install_profile": self.install_profile,
            "install_target_sha256": self.install_target_sha256,
            "installed_at_unix": self.installed_at_unix,
            "layout_id": self.layout_id,
            "persist": self.persist.as_dict(),
            "platform_family": self.platform_family,
            "schema_version": self.schema_version,
            "slot_bytes": self.slot_bytes,
            "system_a": self.system_a.as_dict(),
            "system_b": self.system_b.as_dict() if self.system_b is not None else None,
        }

    def canonical_bytes(self) -> bytes:
        return _canonical_bytes(self.as_dict())

    def write_to(self, path: Path) -> None:
        """Atomically write with fsync, then enforce owner-only mode."""
        _atomic_write_file(Path(path), self.canonical_bytes(), mode=LAYOUT_RECORD_MODE)

    @classmethod
    def read_from(cls, path: Path, *, expect_uid: int | None = None) -> "InstalledLayoutRecord":
        """Fail-closed read: symlink/regular/mode/owner/canonical/schema gates.

        Ownership defaults to the current effective UID (root on device);
        pass ``expect_uid=0`` explicitly from production callers.
        """
        location = Path(path)
        try:
            if location.is_symlink():
                raise PersistentLayoutError("layout record may not be a symbolic link")
            status = location.stat()
        except OSError as exc:
            raise PersistentLayoutError(f"layout record is not accessible: {exc}") from exc
        import stat as _stat

        if not _stat.S_ISREG(status.st_mode):
            raise PersistentLayoutError("layout record must be a regular file")
        if status.st_size <= 0 or status.st_size > MAX_LAYOUT_RECORD_BYTES:
            raise PersistentLayoutError("layout record size is outside Greia bounds")
        if _stat.S_IMODE(status.st_mode) != LAYOUT_RECORD_MODE:
            raise PersistentLayoutError("layout record must be owner-only mode 0600")
        wanted_uid = os.geteuid() if expect_uid is None else expect_uid
        if status.st_uid != wanted_uid:
            raise PersistentLayoutError("layout record ownership is not authoritative")
        try:
            raw_bytes = location.read_bytes()
        except OSError as exc:
            raise PersistentLayoutError("layout record is unreadable") from exc
        try:
            raw = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PersistentLayoutError("layout record is not valid JSON") from exc
        record = cls.from_dict(raw)
        if raw_bytes != record.canonical_bytes():
            raise PersistentLayoutError("layout record is not canonical JSON")
        return record


# ---------------------------------------------------------------------------
# Block topology (read-only facts; R0/R1 perform no partition/boot writes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PartitionFact:
    """One observed partition: identities plus transport facts, never authority."""

    role: str
    scheme: str
    partuuid: str
    filesystem_uuid: str
    size_bytes: int
    disk_id: str

    @classmethod
    def create(
        cls,
        *,
        role: str,
        partuuid: str,
        filesystem_uuid: str,
        size_bytes: int,
        disk_id: str,
        scheme: str | None = None,
    ) -> "PartitionFact":
        if role not in PARTITION_ROLES:
            raise PersistentLayoutError(f"unknown partition role: {role!r}")
        for field, value in (("partuuid", partuuid), ("filesystem_uuid", filesystem_uuid)):
            if not isinstance(value, str) or value.startswith("/dev/"):
                raise PersistentLayoutError(
                    f"topology {field} must be an identity, never a device path"
                )
        if scheme is None:
            scheme = infer_partuuid_scheme(partuuid)
        if scheme not in PARTITION_SCHEMES:
            raise PersistentLayoutError(f"topology scheme is unknown: {scheme!r}")
        if (
            not isinstance(size_bytes, int)
            or isinstance(size_bytes, bool)
            or size_bytes <= 0
        ):
            raise PersistentLayoutError("topology size_bytes must be a positive integer")
        return cls(
            role=role,
            scheme=scheme,
            partuuid=normalize_partuuid_for_scheme(
                scheme, partuuid, field="partuuid"
            ),
            filesystem_uuid=_require_canonical_uuid(
                filesystem_uuid, field="filesystem_uuid"
            ),
            size_bytes=size_bytes,
            disk_id=_require_identifier(disk_id, field="disk_id"),
        )

    @property
    def disk_signature(self) -> str | None:
        """MBR disk signature, or ``None`` for GPT facts."""
        if self.scheme != PARTITION_SCHEME_MBR_PARTUUID:
            return None
        signature, _ = split_mbr_partuuid(self.partuuid)
        return signature


@dataclass(frozen=True, slots=True)
class BlockTopology:
    """Observed block facts presented for validation (no writes)."""

    partitions: tuple[PartitionFact, ...]

    def __post_init__(self) -> None:
        roles = [fact.role for fact in self.partitions]
        if len(set(roles)) != len(roles):
            raise PersistentLayoutError("block topology carries duplicate roles")
        identities: list[str] = []
        for fact in self.partitions:
            identities.extend((fact.partuuid, fact.filesystem_uuid))
        if len(set(identities)) != len(identities):
            raise PersistentLayoutError("block topology carries duplicate identities")

    def by_role(self, role: str) -> PartitionFact | None:
        for fact in self.partitions:
            if fact.role == role:
                return fact
        return None


def read_partuuid_map(by_partuuid_dir: Path) -> dict[str, str]:
    """Read-only PARTUUID -> kernel device name map from udev symlinks.

    Symlink *targets* are transport only (``../../sda3``); the returned keys
    (PARTUUIDs, GPT GUID or MBR ``<signature>-<partno>`` form) are the
    identities the layout record binds.
    """
    root = Path(by_partuuid_dir)
    try:
        entries = list(root.iterdir())
    except OSError as exc:
        raise PersistentLayoutError(f"PARTUUID directory is unreadable: {exc}") from exc
    mapping: dict[str, str] = {}
    for entry in entries:
        if not entry.is_symlink():
            raise PersistentLayoutError("PARTUUID directory must hold only symlinks")
        scheme = infer_partuuid_scheme(entry.name)
        partuuid = normalize_partuuid_for_scheme(scheme, entry.name, field="partuuid")
        if partuuid in mapping:
            raise PersistentLayoutError("PARTUUID directory carries duplicate identities")
        mapping[partuuid] = Path(os.readlink(entry)).name
    if not mapping:
        raise PersistentLayoutError("PARTUUID directory holds no identities")
    return mapping


def require_mbr_topology_binding(
    record: InstalledLayoutRecord, topology: BlockTopology
) -> str:
    """Prove an MBR record binds one observed disk signature (T1.1).

    Every record identity and every topology fact for the layout must carry
    the ``MBR_PARTUUID`` scheme and share a single disk signature; the
    record and topology signatures must be equal. Returns the proven disk
    signature. GPT layouts fail closed here (wrong entry point); legacy
    scheme-less provisional records fail closed as well — callers must
    supply scheme-explicit observed identities.
    """
    expected = LAYOUT_PARTITION_SCHEMES.get(record.layout_id)
    if expected != PARTITION_SCHEME_MBR_PARTUUID:
        raise PersistentLayoutError(
            f"MBR topology binding requires an MBR layout, not {record.layout_id!r}"
        )
    record_identities = [record.system_a, record.persist]
    if record.system_b is not None:
        record_identities.append(record.system_b)
    for identity in record_identities:
        if identity.scheme != PARTITION_SCHEME_MBR_PARTUUID:
            raise PersistentLayoutError(
                "MBR layout record carries a non-MBR identity: "
                "refusing a fabricated MBR binding"
            )
    for fact in topology.partitions:
        if fact.scheme != PARTITION_SCHEME_MBR_PARTUUID:
            raise PersistentLayoutError(
                f"topology role {fact.role!r} carries a non-MBR identity: "
                "refusing a fabricated MBR binding"
            )
    record_signatures = {split_mbr_partuuid(item.partuuid)[0] for item in record_identities}
    if len(record_signatures) != 1:
        raise PersistentLayoutError(
            "layout MBR PARTUUIDs span multiple disk signatures: "
            "refusing a cross-disk identity binding"
        )
    topology_signatures = {
        split_mbr_partuuid(fact.partuuid)[0] for fact in topology.partitions
    }
    if len(topology_signatures) != 1:
        raise PersistentLayoutError(
            "observed MBR PARTUUIDs span multiple disk signatures: "
            "refusing a cross-disk topology"
        )
    (record_signature,) = sorted(record_signatures)
    (topology_signature,) = sorted(topology_signatures)
    if record_signature != topology_signature:
        raise PersistentLayoutError(
            "observed MBR disk signature does not match the layout record: "
            "refusing a wrong-disk binding"
        )
    return record_signature


def validate_layout_against_topology(
    record: InstalledLayoutRecord, topology: BlockTopology
) -> None:
    """Fail closed unless observed topology matches the installed record."""
    is_ab = record.layout_id in AB_LAYOUT_ADAPTERS
    expected_roles = ("system-a", "system-b", "persist") if is_ab else ("system-a", "persist")
    for role in expected_roles:
        if topology.by_role(role) is None:
            raise PersistentLayoutError(f"topology is missing partition role: {role}")
    for fact in topology.partitions:
        if fact.role not in expected_roles:
            raise PersistentLayoutError(
                f"topology carries unexpected partition role: {fact.role}"
            )
    # Scheme agreement per role: an observed GPT fact can never satisfy an
    # MBR record identity and vice versa (UUID4-as-MBR fails closed here).
    role_identities: dict[str, PartitionIdentity] = {"system_a": record.system_a}
    if record.system_b is not None:
        role_identities["system_b"] = record.system_b
    role_identities["persist"] = record.persist
    for fact in topology.partitions:
        identity = role_identities[fact.role.replace("-", "_")]
        if fact.scheme != identity.scheme:
            raise PersistentLayoutError(
                f"topology role {fact.role!r} scheme {fact.scheme!r} does not match "
                f"the layout record scheme {identity.scheme!r}"
            )
    # MBR disk-signature agreement: every bound identity must live on the
    # one observed disk. Wrong-disk topologies fail closed here.
    mbr_record_signatures = {
        split_mbr_partuuid(item.partuuid)[0]
        for item in role_identities.values()
        if item.scheme == PARTITION_SCHEME_MBR_PARTUUID
    }
    mbr_topology_signatures = {
        split_mbr_partuuid(fact.partuuid)[0]
        for fact in topology.partitions
        if fact.scheme == PARTITION_SCHEME_MBR_PARTUUID
    }
    if mbr_record_signatures and len(mbr_record_signatures) != 1:
        raise PersistentLayoutError(
            "layout MBR PARTUUIDs span multiple disk signatures: "
            "refusing a cross-disk identity binding"
        )
    if mbr_topology_signatures and len(mbr_topology_signatures) != 1:
        raise PersistentLayoutError(
            "observed MBR PARTUUIDs span multiple disk signatures: "
            "refusing a cross-disk topology"
        )
    if (
        len(mbr_record_signatures) == 1
        and len(mbr_topology_signatures) == 1
        and mbr_record_signatures != mbr_topology_signatures
    ):
        raise PersistentLayoutError(
            "observed MBR disk signature does not match the layout record: "
            "refusing a wrong-disk binding"
        )
    fact_a = topology.by_role("system-a")
    assert fact_a is not None
    if is_ab:
        fact_b = topology.by_role("system-b")
        assert fact_b is not None
        assert record.system_b is not None
        if (
            fact_a.partuuid == record.system_b.partuuid
            and fact_b.partuuid == record.system_a.partuuid
        ):
            raise PersistentLayoutError("system slots are swapped relative to the record")
        if fact_b.partuuid != record.system_b.partuuid:
            raise PersistentLayoutError("system-b PARTUUID does not match the record")
        if fact_b.filesystem_uuid != record.system_b.filesystem_uuid:
            raise PersistentLayoutError(
                "system-b filesystem UUID does not match the record"
            )
        if fact_b.size_bytes != record.slot_bytes:
            raise PersistentLayoutError("system-b capacity changed relative to the record")
    if fact_a.partuuid != record.system_a.partuuid:
        raise PersistentLayoutError("system-a PARTUUID does not match the record")
    if fact_a.filesystem_uuid != record.system_a.filesystem_uuid:
        raise PersistentLayoutError("system-a filesystem UUID does not match the record")
    if fact_a.size_bytes != record.slot_bytes:
        raise PersistentLayoutError("system-a capacity changed relative to the record")
    fact_persist = topology.by_role("persist")
    assert fact_persist is not None
    if fact_persist.partuuid != record.persist.partuuid:
        raise PersistentLayoutError("PERSIST PARTUUID does not match the record")
    if fact_persist.filesystem_uuid != record.persist.filesystem_uuid:
        raise PersistentLayoutError("PERSIST filesystem UUID does not match the record")
    if fact_persist.size_bytes < MIN_PERSIST_BYTES:
        raise PersistentLayoutError("PERSIST capacity is below the Greia floor")
    disks = {fact.disk_id for fact in topology.partitions}
    if len(disks) != 1:
        raise PersistentLayoutError(
            "installed partitions span unexpected ancestry (must share one disk)"
        )


# ---------------------------------------------------------------------------
# Durable-path audit
# ---------------------------------------------------------------------------


class Durability(StrEnum):
    PERSISTENT_SHARED = "PERSISTENT_SHARED"
    SLOT_LOCAL = "SLOT_LOCAL"
    VOLATILE = "VOLATILE"
    BACKUP_ONLY = "BACKUP_ONLY"


class MountKind(StrEnum):
    BIND_DIR = "bind-dir"
    BIND_FILE = "bind-file"
    INHERIT = "inherit"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class DurablePathEntry:
    """One audited durable path.

    ``mount`` is ``BIND_DIR``/``BIND_FILE`` for entries that own a PERSIST
    bind, ``INHERIT`` for paths covered by an ancestor bind (nested profile
    content, restore-only copies, co-located state), and ``NONE`` for paths
    that are never mounted from PERSIST.
    """

    path: str
    durability: Durability
    namespace: str | None
    mount: MountKind
    order: int | None
    rationale: str


#: Canonical PERSIST namespace order. Deterministic mount order follows the
#: ``order`` of the owning bind entries; this tuple fixes contract emission.
PERSISTENT_NAMESPACE_ORDER: tuple[str, ...] = (
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

#: Layout-authority directory bind: must sort before every other mount so
#: readers see the installed record before trusting other shared state.
LAYOUT_BIND_ORDER = 5


# Evidence anchors (current source): tmpfiles durable roots in
# build/overlay/etc/tmpfiles.d/greia-os.conf; first-boot marker + machine-id
# in build/overlay/usr/local/lib/greia-os/first-boot; installer slot writes in
# src/greia_installer/engine.py; profile/storage/progression authorities in
# src/greia_platform/{profiles,storage,history,achievements}.py; Parent state
# defaults in src/greia_parent/server.py + api_server.py; update inbox/status
# in src/greia_platform/system_updates.py; device settings in
# src/greia_platform/{hardware,system_controls,audio} + system_language.py;
# network state in src/greia_platform/wifi.py + src/greia_installer/wifi.py;
# developer state in src/greia_platform/developer_control.py; volatile
# runtime roots in src/greia_launcher/{event_broker,storage_broker,supervisor}.py.
DURABLE_PATH_AUDIT: tuple[DurablePathEntry, ...] = (
    # -- PERSISTENT_SHARED with an owned bind (deterministic mount order) --
    DurablePathEntry(
        path="/etc/greia-os/layout",
        durability=Durability.PERSISTENT_SHARED,
        namespace="layout-authority",
        mount=MountKind.BIND_DIR,
        order=LAYOUT_BIND_ORDER,
        rationale="Root-owned layout-authority directory from PERSIST; a directory "
        "bind keeps atomic record replacement visible to both slots.",
    ),
    DurablePathEntry(
        path="/etc/greia-os/layout/installed-layout.json",
        durability=Durability.PERSISTENT_SHARED,
        namespace="layout-authority",
        mount=MountKind.INHERIT,
        order=None,
        rationale="Installed layout record is written atomically inside the shared "
        "layout-authority directory bind.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-profiles",
        durability=Durability.PERSISTENT_SHARED,
        namespace="child-profiles",
        mount=MountKind.BIND_DIR,
        order=10,
        rationale="Profile registry, per-profile customization, Activity data "
        "roots and nested usage-limits.json; explicit per-child identity must "
        "survive slot switches.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-system-settings",
        durability=Durability.PERSISTENT_SHARED,
        namespace="device-settings",
        mount=MountKind.BIND_DIR,
        order=20,
        rationale="Parent-owned hardware/display/pointer/audio/language desired "
        "state (settings.json, language.json, audio/system-controls stores); "
        "typed platform policy, never shell injection.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-os",
        durability=Durability.PERSISTENT_SHARED,
        namespace="parent-credentials",
        mount=MountKind.BIND_DIR,
        order=30,
        rationale="ParentServer state_dir: parent-devices.json, main-credential "
        "and pairing token. Co-located update status, activity packages and "
        "first-boot markers ride this bind as named INHERIT entries below; "
        "this bounded exception never generalizes to all of /var.",
    ),
    DurablePathEntry(
        path="/var/lib/iwd",
        durability=Durability.PERSISTENT_SHARED,
        namespace="network-state",
        mount=MountKind.BIND_DIR,
        order=40,
        rationale="iwd known-network state (mode 0700); provisioned Wi-Fi from "
        "install must survive slot switches without re-entry.",
    ),
    DurablePathEntry(
        path="/etc/machine-id",
        durability=Durability.PERSISTENT_SHARED,
        namespace="machine-identity",
        mount=MountKind.BIND_FILE,
        order=50,
        rationale="First-boot-generated stable machine identity (installer "
        "ships it empty); slot switches must not fork device identity.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-developer",
        durability=Durability.PERSISTENT_SHARED,
        namespace="developer-state",
        mount=MountKind.BIND_DIR,
        order=60,
        rationale="Developer-image deployments and staging; empty on release "
        "images but the bind exists so dev tooling never falls back to slot "
        "paths. Never trusted on release profiles.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-admin/greia-dev-upload",
        durability=Durability.PERSISTENT_SHARED,
        namespace="developer-state",
        mount=MountKind.BIND_DIR,
        order=61,
        rationale="Bounded developer upload inbox (dev images only); separate "
        "bind because it is not nested under greia-developer.",
    ),
    # -- PERSISTENT_SHARED riding an ancestor bind (no second mount) --
    DurablePathEntry(
        path="/var/lib/greia-profiles/data/*/storage",
        durability=Durability.PERSISTENT_SHARED,
        namespace="activity-saves",
        mount=MountKind.INHERIT,
        order=None,
        rationale="Per-(profile, Activity) durable namespaces owned by "
        "ActivityStorageService; persist via the profiles bind.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-profiles/data/*/progress",
        durability=Durability.PERSISTENT_SHARED,
        namespace="progression-rewards",
        mount=MountKind.INHERIT,
        order=None,
        rationale="Platform-owned history/achievement state under "
        "ProfileContext.progress_dir; Activities report facts, never mutate "
        "global progression directly.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-os/system-updates/status.json",
        durability=Durability.PERSISTENT_SHARED,
        namespace="update-acceptance-state",
        mount=MountKind.INHERIT,
        order=None,
        rationale="Update service status; rides the greia-os bind so status "
        "survives the reboot into a new slot.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-os/system-updates/inbox",
        durability=Durability.PERSISTENT_SHARED,
        namespace="update-acceptance-state",
        mount=MountKind.INHERIT,
        order=None,
        rationale="Bounded content-addressed staging bytes; re-fetchable, so "
        "loss would be safe, but persistence across the update reboot is "
        "harmless and keeps single-download flows working.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-os/activity-packages",
        durability=Durability.PERSISTENT_SHARED,
        namespace="activity-activation",
        mount=MountKind.INHERIT,
        order=None,
        rationale="Installed third-party inventory: generations, active "
        "pointer, install receipts. Built-in Activities stay read-only under "
        "/opt/greia-os/activities; this is activation state, not payload.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-os/initialized",
        durability=Durability.PERSISTENT_SHARED,
        namespace="update-acceptance-state",
        mount=MountKind.INHERIT,
        order=None,
        rationale="First-boot completion marker; must persist so first boot "
        "never re-runs account/permission repair on later boots.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-os/migrations",
        durability=Durability.PERSISTENT_SHARED,
        namespace="update-acceptance-state",
        mount=MountKind.INHERIT,
        order=None,
        rationale="Versioned one-shot field-repair markers (e.g. "
        "b2-audio-groups-v1); exactly-once semantics require persistence.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-os/hardware-receipts",
        durability=Durability.PERSISTENT_SHARED,
        namespace="hardware-receipts",
        mount=MountKind.INHERIT,
        order=None,
        rationale="Reserved domain for per-device hardware enablement "
        "receipts; current installer records package names slot-locally in "
        "install-record.json, future receipts land here.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-os/diagnostics",
        durability=Durability.PERSISTENT_SHARED,
        namespace="bounded-logs",
        mount=MountKind.INHERIT,
        order=None,
        rationale="Reserved bounded on-device log/evidence staging consumed "
        "by greia-collect-runtime-audit; always size-bounded, never a raw "
        "filesystem dump.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-os/diagnostics/boot-history.json",
        durability=Durability.PERSISTENT_SHARED,
        namespace="bounded-logs",
        mount=MountKind.INHERIT,
        order=None,
        rationale="T5-EVID bounded reboot-surviving boot/lifecycle ring "
        "(current/previous summary, 64 KiB source-enforced cap owned by "
        "greia_platform.boot_transaction); coarse milestones and terminal "
        "events only, never animation frames, input events or journal text. "
        "Listed before the greia-os catch-all so the bounded-logs role is exact.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-profiles/profiles.backup.json",
        durability=Durability.BACKUP_ONLY,
        namespace="child-profiles",
        mount=MountKind.INHERIT,
        order=None,
        rationale="Registry restore copy read only when profiles.json is "
        "corrupt; rides the profiles bind but is never live-mounted. Listed "
        "before the profile-tree catch-all so the restore-only role is exact.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-profiles/data/*/.storage-rollbacks",
        durability=Durability.BACKUP_ONLY,
        namespace="activity-saves",
        mount=MountKind.INHERIT,
        order=None,
        rationale="Bounded pre-migration storage snapshots; restore-only, "
        "pruned by ActivityStorageService policy. Listed before the "
        "profile-tree catch-all so the restore-only role is exact.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-developer/backups",
        durability=Durability.BACKUP_ONLY,
        namespace="developer-state",
        mount=MountKind.INHERIT,
        order=None,
        rationale="Original built-in Activity backups for developer replace/ "
        "restore flows; restore-only, dev images only.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-profiles/*",
        durability=Durability.PERSISTENT_SHARED,
        namespace="child-profiles",
        mount=MountKind.INHERIT,
        order=None,
        rationale="Catch-all for direct profile-tree files (profiles.json, "
        "usage-limits.json, locks): everything under the profiles bind "
        "persists with it. Listed after the specific nested domains above.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-os/*",
        durability=Durability.PERSISTENT_SHARED,
        namespace="parent-credentials",
        mount=MountKind.INHERIT,
        order=None,
        rationale="Catch-all for direct ParentServer state files "
        "(parent-devices.json, main-credential.json, pairing token) riding "
        "the greia-os bind. Listed after the specific nested domains above.",
    ),
    # -- SLOT_LOCAL: slot-baked, reinstalled with the slot, never bound --
    DurablePathEntry(
        path="/opt/greia-os",
        durability=Durability.SLOT_LOCAL,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="The slot payload itself (read-only composition); it IS a "
        "slot, not state carried across slots.",
    ),
    DurablePathEntry(
        path="/etc/greia-os/install-record.json",
        durability=Durability.SLOT_LOCAL,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Per-slot install evidence (target digest, locale, hardware "
        "settings snapshot); each slot carries the record of its own creation.",
    ),
    DurablePathEntry(
        path="/etc/greia-os/root-filesystem-uuid",
        durability=Durability.SLOT_LOCAL,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Per-slot GRUB root binding; must track the slot it boots.",
    ),
    DurablePathEntry(
        path="/etc/greia-os/grub-recovery.pbkdf2",
        durability=Durability.SLOT_LOCAL,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Per-slot recovery credential verifier; bound to the slot "
        "whose boot chain it unlocks.",
    ),
    DurablePathEntry(
        path="/etc/greia-os/developer-remote",
        durability=Durability.SLOT_LOCAL,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Developer-image marker baked at build/provision time; "
        "release slots simply lack it. Never a runtime state write.",
    ),
    DurablePathEntry(
        path="/etc/greia-os/build-info",
        durability=Durability.SLOT_LOCAL,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Slot build metadata (read-only image composition fact).",
    ),
    DurablePathEntry(
        path="/var/cache/apt",
        durability=Durability.SLOT_LOCAL,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Slot image package caches; re-fetchable, never child data.",
    ),
    # -- VOLATILE: tmpfs or recreated every boot, never on PERSIST --
    DurablePathEntry(
        path="/run/greia-os",
        durability=Durability.VOLATILE,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Active-profile status, broker sockets, one-shot boot "
        "markers; recreated by tmpfiles/systemd every boot.",
    ),
    DurablePathEntry(
        path="/run/greia-os/*",
        durability=Durability.VOLATILE,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Everything under the volatile runtime root shares its "
        "treatment: active-profile.json, event/storage broker sockets, "
        "one-shot markers. Never on PERSIST.",
    ),
    DurablePathEntry(
        path="/run/greia-events",
        durability=Durability.VOLATILE,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Sandbox event broker sockets; per-boot lifecycle only.",
    ),
    DurablePathEntry(
        path="/run/greia-storage",
        durability=Durability.VOLATILE,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Storage broker runtime directories; per-session mounts.",
    ),
    DurablePathEntry(
        path="/run/greia-activity-data",
        durability=Durability.VOLATILE,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Sandbox-visible Activity data staging; brokered per launch.",
    ),
    DurablePathEntry(
        path="/run/greia-customization",
        durability=Durability.VOLATILE,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Sandbox-visible customization staging; brokered per launch.",
    ),
    DurablePathEntry(
        path="/run/greia-audio",
        durability=Durability.VOLATILE,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Audio endpoint/mixer runtime status; re-probed every boot.",
    ),
    DurablePathEntry(
        path="/run/greia-hardware",
        durability=Durability.VOLATILE,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="HAL status snapshots; hardware is re-probed every boot.",
    ),
    DurablePathEntry(
        path="/tmp",
        durability=Durability.VOLATILE,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="tmpfs per installed fstab (64M, noexec); scratch only.",
    ),
    DurablePathEntry(
        path="/var/tmp",
        durability=Durability.VOLATILE,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="tmpfs per installed fstab (32M, noexec); scratch only.",
    ),
    DurablePathEntry(
        path="/var/lib/greia-kid",
        durability=Durability.VOLATILE,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Service HOME for greiakid (caches, runtime files); no "
        "durable child data lives here — profile state is under greia-profiles.",
    ),
    DurablePathEntry(
        path="/media/greia",
        durability=Durability.VOLATILE,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Removable-media mountpoint: untrusted, never autorun, "
        "never a persistence target.",
    ),
    DurablePathEntry(
        path="/var/lib/dbus/machine-id",
        durability=Durability.VOLATILE,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Regenerated/symlinked D-Bus identity; /etc/machine-id is "
        "the authority, this path never is.",
    ),
    DurablePathEntry(
        path="/var/lib/systemd/random-seed",
        durability=Durability.VOLATILE,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Boot entropy carryover; deleted at install, recreated at "
        "runtime, never child or device identity.",
    ),
    # -- BACKUP_ONLY: restore-only copies, never live-mounted or read --
    DurablePathEntry(
        path="/media/greia/*.greiabackup",
        durability=Durability.BACKUP_ONLY,
        namespace=None,
        mount=MountKind.NONE,
        order=None,
        rationale="Logical open-profile backups on removable media; portable "
        "across architectures, never executed in place.",
    ),
)


def find_audit_entry(path: str) -> DurablePathEntry | None:
    """Return the audit entry covering ``path`` (exact or glob match).

    Entries are evaluated in audit order, so specific nested domains win over
    the trailing catch-alls. Patterns also cover paths nested below them
    (``pattern/*``), because everything under a covered directory shares its
    persistence treatment.

    Returns ``None`` for unclassified paths: an unclassified
    identity-affecting path blocks destructive migration instead of being
    guessed.
    """
    for entry in DURABLE_PATH_AUDIT:
        if entry.path == path:
            return entry
        if "*" in entry.path and (
            fnmatch.fnmatchcase(path, entry.path)
            or fnmatch.fnmatchcase(path, entry.path + "/*")
        ):
            return entry
    return None


# ---------------------------------------------------------------------------
# Versioned PersistentNamespaceMap
# ---------------------------------------------------------------------------


#: Schema version of the namespace map itself.
NAMESPACE_MAP_SCHEMA_VERSION = 1

#: Hard bounds for the map (mirrors contract bounds: <=64 namespaces).
MAX_MOUNT_ENTRIES = 32
MAX_MAP_NAMESPACES = 64


@dataclass(frozen=True, slots=True)
class NamespaceMount:
    """One deterministic PERSIST bind: namespace domain -> canonical target."""

    namespace: str
    target: str
    kind: MountKind
    order: int

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "namespace": self.namespace,
            "order": self.order,
            "target": self.target,
        }


@dataclass(frozen=True, slots=True)
class PersistentNamespaceMap:
    """Versioned map from PERSIST namespaces to deterministic bind order."""

    schema_version: int
    namespaces: tuple[str, ...]
    mounts: tuple[NamespaceMount, ...]

    def mount_plan(self) -> tuple[NamespaceMount, ...]:
        """Mounts in deterministic bind order (layout record first)."""
        return tuple(sorted(self.mounts, key=lambda item: item.order))

    def as_dict(self) -> dict[str, object]:
        return {
            "mounts": [item.as_dict() for item in self.mount_plan()],
            "namespaces": list(self.namespaces),
            "schema_version": self.schema_version,
        }


def _check_canonical_target(target: str) -> str:
    if not isinstance(target, str) or not target.startswith("/") or "*" in target:
        raise PersistentLayoutError(f"mount target must be a concrete absolute path")
    normalized = os.path.normpath(target)
    if normalized != target or "/../" in target or target.endswith("/.."):
        raise PersistentLayoutError(f"mount target escapes its canonical form: {target}")
    parts = target.split("/")
    if any(part in (".", "..", "") for part in parts[1:]):
        raise PersistentLayoutError(f"mount target has empty components: {target}")
    if len(target.encode("utf-8")) > 256:
        raise PersistentLayoutError("mount target path is too long")
    return target


def build_namespace_map(
    entries: tuple[DurablePathEntry, ...] = DURABLE_PATH_AUDIT,
) -> PersistentNamespaceMap:
    """Derive the single authoritative map from the durable-path audit."""
    shared = [entry for entry in entries if entry.durability == Durability.PERSISTENT_SHARED]
    for entry in shared:
        if entry.namespace is None:
            raise PersistentLayoutError(f"shared entry lacks a namespace: {entry.path}")
        if entry.namespace not in PERSISTENT_NAMESPACE_ORDER:
            raise PersistentLayoutError(
                f"shared entry uses an unregistered namespace: {entry.namespace}"
            )
    mounted = [entry for entry in shared if entry.mount != MountKind.INHERIT]
    inherited = [entry for entry in shared if entry.mount == MountKind.INHERIT]
    if len(mounted) > MAX_MOUNT_ENTRIES:
        raise PersistentLayoutError("namespace map exceeds the mount bound")
    orders = [entry.order for entry in mounted]
    if any(order is None for order in orders):
        raise PersistentLayoutError("mounted entries require a deterministic order")
    if len(set(orders)) != len(orders):
        raise PersistentLayoutError("mounted entries carry duplicate order values")
    targets = [_check_canonical_target(entry.path) for entry in mounted]
    if len(set(targets)) != len(targets):
        raise PersistentLayoutError("namespace map carries duplicate canonical targets")
    for entry in inherited:
        probe = entry.path[:-1] if entry.path.endswith("*") else entry.path
        probe = os.path.normpath(probe)
        owners = [
            target
            for target in targets
            if probe == target or probe.startswith(target + "/")
        ]
        if len(owners) != 1:
            raise PersistentLayoutError(
                f"inherited entry must nest under exactly one bind: {entry.path}"
            )
    namespaces = tuple(
        name for name in PERSISTENT_NAMESPACE_ORDER if any(e.namespace == name for e in shared)
    )
    if len(namespaces) != len(PERSISTENT_NAMESPACE_ORDER):
        missing = set(PERSISTENT_NAMESPACE_ORDER) - set(namespaces)
        raise PersistentLayoutError(
            "namespace map leaves registered namespaces ungrounded: "
            + ", ".join(sorted(missing))
        )
    if len(namespaces) > MAX_MAP_NAMESPACES:
        raise PersistentLayoutError("namespace map exceeds the namespace bound")
    mounts = tuple(
        NamespaceMount(
            namespace=entry.namespace or "",
            target=target,
            kind=entry.mount,
            order=entry.order or 0,
        )
        for entry, target in sorted(
            zip(mounted, targets), key=lambda pair: pair[0].order or 0
        )
    )
    return PersistentNamespaceMap(
        schema_version=NAMESPACE_MAP_SCHEMA_VERSION,
        namespaces=namespaces,
        mounts=mounts,
    )


def verify_host_mount_targets(namespace_map: PersistentNamespaceMap, root: Path) -> None:
    """Fail closed when a host bind target escapes or passes a symlink.

    ``root`` is the host filesystem root the canonical targets resolve under
    (``/`` on device, a staging tree in tests). No writes are performed.
    """
    base_resolved = Path(root).resolve()
    for mount in namespace_map.mount_plan():
        candidate = base_resolved.joinpath(mount.target.lstrip("/"))
        try:
            candidate.relative_to(base_resolved)
        except ValueError as exc:
            raise PersistentLayoutError(
                f"mount target escapes the host root: {mount.target}"
            ) from exc
        current = base_resolved
        for component in mount.target.strip("/").split("/"):
            current = current / component
            if os.path.islink(current):
                raise PersistentLayoutError(
                    f"mount path passes a symbolic link: {mount.target}"
                )


# ---------------------------------------------------------------------------
# Contract emission + rollback consumption (never a Parent-passed boolean)
# ---------------------------------------------------------------------------


def emit_persistent_state_contract(
    namespace_map: PersistentNamespaceMap,
) -> bytes:
    """Emit the canonical registry contract through the system_updates authority."""
    if tuple(namespace_map.namespaces) != PERSISTENT_NAMESPACE_ORDER:
        raise PersistentLayoutError(
            "contract emission requires the registered namespace order"
        )
    raw = build_persistent_state_contract_bytes(
        namespaces=tuple(namespace_map.namespaces)
    )
    verify_persistent_state_contract_bytes(raw)
    return raw


# ---------------------------------------------------------------------------
# PERSIST schema marker + compatibility (ADR 0036 §6, v3 integer check)
# ---------------------------------------------------------------------------

#: Current installed PERSIST schema written by fresh install (ordinary
#: small marker, conceptually ``{"schema_version": 1}``). Later sessions
#: advance it through the normal migration path; the update path only
#: checks readability, never migrates.
PERSIST_SCHEMA_CURRENT = 1

#: Upper bound for a PERSIST schema integer (mirrors the manifest bound).
MAX_PERSIST_SCHEMA_MARKER = 2_147_483_647

#: Upper bound for a stored schema-marker document (small by construction).
MAX_PERSIST_SCHEMA_MARKER_BYTES = 256


def emit_persist_schema_marker(schema: int) -> bytes:
    """Emit the canonical installed PERSIST schema marker bytes.

    Format owned here and consumed by update staging and later
    preserve-data reinstall work: canonical JSON ``{"schema_version": N}``
    plus newline. ``N`` is a non-negative bounded integer.
    """
    if isinstance(schema, bool) or not isinstance(schema, int):
        raise PersistentLayoutError("PERSIST schema must be an integer")
    if schema < 0 or schema > MAX_PERSIST_SCHEMA_MARKER:
        raise PersistentLayoutError("PERSIST schema is outside Greia bounds")
    return _canonical_bytes({"schema_version": schema})


def parse_persist_schema_marker(raw: bytes | bytearray) -> int:
    """Parse installed PERSIST schema marker bytes fail-closed (read-only)."""
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        raise PersistentLayoutError(
            "installed PERSIST schema marker is not authoritative"
        )
    if len(raw) > MAX_PERSIST_SCHEMA_MARKER_BYTES:
        raise PersistentLayoutError("installed PERSIST schema marker exceeds Greia bound")
    try:
        document = json.loads(bytes(raw).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PersistentLayoutError(
            "installed PERSIST schema marker is not valid JSON"
        ) from exc
    if not isinstance(document, dict) or set(document) != {"schema_version"}:
        raise PersistentLayoutError(
            "installed PERSIST schema marker fields are invalid; "
            "expected canonical {\"schema_version\": N} "
            "(PERSIST compatibility migration required)"
        )
    schema = document.get("schema_version")
    if isinstance(schema, bool) or not isinstance(schema, int):
        raise PersistentLayoutError("installed PERSIST schema must be an integer")
    if schema < 0 or schema > MAX_PERSIST_SCHEMA_MARKER:
        raise PersistentLayoutError("installed PERSIST schema is outside Greia bounds")
    if bytes(raw) != _canonical_bytes(document):
        raise PersistentLayoutError(
            "installed PERSIST schema marker is not canonical JSON"
        )
    return schema


def read_persist_schema_marker(path: Path) -> bytes:
    """Read one bounded, canonical marker from the already-mounted PERSIST.

    The update service must not mount PERSIST itself. Its caller supplies the
    marker's bind-visible path; this helper rejects links and non-regular
    files, bounds the read before parsing, and returns the canonical bytes for
    the manifest compatibility gate.
    """
    candidate = Path(path)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(candidate, flags)
    except FileNotFoundError as exc:
        raise PersistentLayoutError(
            "installed PERSIST schema marker is missing"
        ) from exc
    except OSError as exc:
        raise PersistentLayoutError(
            "installed PERSIST schema marker is unreadable"
        ) from exc

    try:
        try:
            with os.fdopen(descriptor, "rb") as handle:
                descriptor = -1
                if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                    raise PersistentLayoutError(
                        "installed PERSIST schema marker is not a regular file"
                    )
                raw = handle.read(MAX_PERSIST_SCHEMA_MARKER_BYTES + 1)
        except OSError as exc:
            raise PersistentLayoutError(
                "installed PERSIST schema marker is unreadable"
            ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    parse_persist_schema_marker(raw)
    return raw


def assert_persist_schema_compatible(installed_schema: int, manifest: UpdateManifest) -> int:
    """PERSIST readability gate (ADR 0036 §6): current schema must be readable.

    Accepts only when ``manifest.persist_read_schema_min <= installed_schema
    <= manifest.persist_read_schema_max``. Any exclusion fails closed with a
    compatibility/migration message; no caller-supplied boolean participates.
    Returns the installed schema for the caller to record.
    """
    if not isinstance(manifest, UpdateManifest):
        raise PersistentLayoutError(
            "PERSIST compatibility gate requires a v3 release manifest"
        )
    if isinstance(installed_schema, bool) or not isinstance(installed_schema, int):
        raise PersistentLayoutError("installed PERSIST schema must be an integer")
    if installed_schema < 0 or installed_schema > MAX_PERSIST_SCHEMA_MARKER:
        raise PersistentLayoutError("installed PERSIST schema is outside Greia bounds")
    if not (
        manifest.persist_read_schema_min
        <= installed_schema
        <= manifest.persist_read_schema_max
    ):
        raise PersistentLayoutError(
            "candidate release cannot read the installed PERSIST schema "
            f"{installed_schema} (readable "
            f"{manifest.persist_read_schema_min}..{manifest.persist_read_schema_max}); "
            "PERSIST compatibility migration required before update"
        )
    return installed_schema


def assert_persistent_contract_accepted(
    installed_contract_raw: bytes, manifest: UpdateManifest
) -> int:
    """v3 PERSIST compatibility gate (kept name for existing importers).

    ``installed_contract_raw`` is the installed PERSIST schema marker bytes
    (see :func:`emit_persist_schema_marker`), not the legacy whole-contract
    document. The current schema must fall within the candidate's readable
    range; otherwise a compatibility/migration error is raised. Returns the
    installed schema integer.
    """
    if not isinstance(manifest, UpdateManifest):
        raise PersistentLayoutError(
            "PERSIST compatibility gate requires a v3 release manifest"
        )
    installed_schema = parse_persist_schema_marker(installed_contract_raw)
    return assert_persist_schema_compatible(installed_schema, manifest)


# ---------------------------------------------------------------------------
# Fresh initialization vs existing-install recovery
# ---------------------------------------------------------------------------


def _persist_state_root(persist_root: Path) -> Path:
    return Path(persist_root) / PERSIST_STATE_DIRNAME


def persist_record_path(persist_root: Path) -> Path:
    return persist_namespace_root(persist_root, "layout-authority") / LAYOUT_RECORD_NAME


def persist_contract_path(persist_root: Path) -> Path:
    return _persist_state_root(persist_root) / CONTRACT_NAME


def persist_schema_marker_path(persist_root: Path) -> Path:
    """Return the PERSIST-side installed schema marker path."""
    return _persist_state_root(persist_root) / PERSIST_SCHEMA_MARKER_NAME


def persist_namespaces_root(persist_root: Path) -> Path:
    return _persist_state_root(persist_root) / PERSIST_NAMESPACES_DIRNAME


def persist_namespace_root(persist_root: Path, namespace: str) -> Path:
    """Return one registered namespace directory beneath mounted PERSIST."""
    if namespace not in PERSISTENT_NAMESPACE_ORDER:
        raise PersistentLayoutError(f"unregistered PERSIST namespace: {namespace!r}")
    return persist_namespaces_root(Path(persist_root)) / namespace


def persist_mount_source_path(
    persist_root: Path,
    mount: NamespaceMount,
) -> Path:
    """Resolve a canonical bind source from one namespace-map entry.

    Directory binds use their registered namespace root. File binds live
    under their namespace using the canonical target basename.
    """
    if not isinstance(mount, NamespaceMount):
        raise PersistentLayoutError("mount source requires a canonical namespace entry")
    namespace_root = persist_namespace_root(Path(persist_root), mount.namespace)
    if mount.kind == MountKind.BIND_FILE:
        basename = Path(mount.target).name
        if not basename or basename in (".", ".."):
            raise PersistentLayoutError("file bind target has no canonical basename")
        return namespace_root / basename
    if mount.kind == MountKind.BIND_DIR:
        return namespace_root
    raise PersistentLayoutError("namespace map carries a non-bind mount")


def present_canonical_mount_targets(
    slot_root: Path,
    namespace_map: PersistentNamespaceMap | None = None,
    *,
    directory_mode: int = 0o755,
) -> tuple[Path, ...]:
    """Create safe bind destinations, including regular file placeholders.

    A bind mount needs its destination to exist. Directory mounts receive
    the canonical directory tree; file mounts receive an empty regular file
    unless the staged image already supplied one. Symlinks and type conflicts
    fail closed before the slot can be accepted.
    """
    root = Path(slot_root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise PersistentLayoutError("slot root must be an existing absolute real directory")
    if isinstance(directory_mode, bool) or not isinstance(directory_mode, int) or not 0 <= directory_mode <= 0o777:
        raise PersistentLayoutError("bind target directory mode is invalid")
    table = namespace_map if namespace_map is not None else build_namespace_map()
    base = root.resolve()
    presented: list[Path] = []
    for mount in table.mount_plan():
        candidate = base / mount.target.lstrip("/")
        try:
            candidate.relative_to(base)
        except ValueError as exc:
            raise PersistentLayoutError(
                f"canonical bind target escapes slot root: {mount.target}"
            ) from exc
        directory = candidate.parent if mount.kind == MountKind.BIND_FILE else candidate
        current = base
        for component in directory.relative_to(base).parts:
            current = current / component
            if current.is_symlink():
                raise PersistentLayoutError(
                    f"canonical bind path passes a symbolic link: {mount.target}"
                )
            try:
                current.mkdir(mode=directory_mode, exist_ok=True)
            except OSError as exc:
                raise PersistentLayoutError(
                    f"canonical bind path cannot be presented: {mount.target}: {exc}"
                ) from exc
            if not current.is_dir() or current.is_symlink():
                raise PersistentLayoutError(
                    f"canonical bind path is not a real directory: {mount.target}"
                )
        try:
            os.chmod(directory, directory_mode)
            if mount.kind == MountKind.BIND_FILE:
                if candidate.is_symlink():
                    raise PersistentLayoutError(
                        f"canonical file bind target is a symbolic link: {mount.target}"
                    )
                if candidate.exists():
                    if not candidate.is_file():
                        raise PersistentLayoutError(
                            f"canonical file bind target is not a regular file: {mount.target}"
                        )
                else:
                    descriptor = os.open(
                        candidate,
                        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                        0o644,
                    )
                    os.close(descriptor)
        except PersistentLayoutError:
            raise
        except OSError as exc:
            raise PersistentLayoutError(
                f"canonical bind target cannot be created: {mount.target}: {exc}"
            ) from exc
        presented.append(directory)
    return tuple(dict.fromkeys(presented))


#: PERSIST-side file name of the T5-EVID bounded boot-history ring.
#: Mirrors ``greia_platform.boot_transaction.BOOT_HISTORY_FILE_NAME`` without
#: importing it (this module stays importable from installer contexts that
#: never load the boot-transaction backend layer).
PERSIST_BOOT_HISTORY_NAME = "boot-history.json"

#: Running-system bind-visible alias of the boot-history record.
BOOT_HISTORY_RUNTIME_PATH = "/var/lib/greia-os/diagnostics/boot-history.json"

#: Initial hard cap for the structured boot-history ring (mirrors the
#: boot-transaction owner; a sync test proves the two stay equal).
MAX_BOOT_HISTORY_BYTES = 64 * 1024


def persist_boot_history_path(persist_root: Path) -> Path:
    """Return the PERSIST-side boot-history path for a mounted PERSIST tree."""
    return _persist_state_root(Path(persist_root)) / PERSIST_BOOT_HISTORY_NAME


def fresh_initialize_persist(
    persist_root: Path,
    record: InstalledLayoutRecord,
    namespace_map: PersistentNamespaceMap,
) -> Path:
    """Fresh install: mint exactly one empty namespace per registered domain.

    Refuses when a layout record already exists (never re-mints identity over
    an existing install). Namespace directories are created empty with
    owner-only group access; production ownership/permissions are applied by
    the installer, not here.
    """
    root = Path(persist_root)
    record_path = persist_record_path(root)
    if record_path.is_symlink() or record_path.exists():
        raise PersistentLayoutError(
            "fresh initialization refused: layout record already exists"
        )
    schema_marker_path = persist_schema_marker_path(root)
    if schema_marker_path.is_symlink() or schema_marker_path.exists():
        raise PersistentLayoutError(
            "fresh initialization refused: PERSIST schema marker already exists"
        )
    state_root = _persist_state_root(root)
    namespaces_root = persist_namespaces_root(root)
    state_root.mkdir(parents=True, exist_ok=True)
    namespaces_root.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    for namespace in namespace_map.namespaces:
        _require_identifier(namespace, field="namespace")
        target = namespaces_root / namespace
        if target.is_symlink() or target.exists():
            raise PersistentLayoutError(
                f"fresh initialization refused: namespace exists: {namespace}"
            )
        target.mkdir(mode=0o770)
        os.chmod(target, 0o770)
        created.append(namespace)
    for mount in namespace_map.mount_plan():
        if mount.kind != MountKind.BIND_FILE or mount.namespace == "layout-authority":
            continue
        source = persist_mount_source_path(root, mount)
        try:
            descriptor = os.open(
                source,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o644,
            )
            os.close(descriptor)
        except OSError as exc:
            raise PersistentLayoutError(
                f"fresh PERSIST file-bind source cannot be initialized: {mount.namespace}"
            ) from exc
    if sorted(created) != sorted(namespace_map.namespaces) or len(set(created)) != len(created):
        raise PersistentLayoutError("fresh initialization must mint each namespace once")
    contract_raw = emit_persistent_state_contract(namespace_map)
    _atomic_write_file(persist_contract_path(root), contract_raw, mode=0o644)
    schema_marker_raw = emit_persist_schema_marker(PERSIST_SCHEMA_CURRENT)
    _atomic_write_file(schema_marker_path, schema_marker_raw, mode=0o644)
    # The layout record is the fresh-state authority; publish it only after
    # its namespaces and both schema/registry markers are durable.
    record.write_to(record_path)
    return state_root


def open_existing_persist(
    persist_root: Path,
    topology: BlockTopology,
    *,
    expect_uid: int | None = None,
) -> tuple[InstalledLayoutRecord, PersistentNamespaceMap]:
    """Open an existing install: any missing/corrupt state fails to recovery.

    Performs no writes. In particular a missing layout record never mints a
    blank child identity; callers must route :class:`PersistRecoveryRequired`
    to recovery, never to :func:`fresh_initialize_persist`.
    """
    root = Path(persist_root)
    record_path = persist_record_path(root)
    if record_path.is_symlink() or not record_path.is_file():
        raise PersistRecoveryRequired("PERSIST layout record is missing")
    try:
        record = InstalledLayoutRecord.read_from(record_path, expect_uid=expect_uid)
    except PersistentLayoutError as exc:
        raise PersistRecoveryRequired(
            f"PERSIST layout record is not authoritative: {exc}"
        ) from exc
    try:
        validate_layout_against_topology(record, topology)
    except PersistentLayoutError as exc:
        raise PersistRecoveryRequired(
            f"PERSIST topology does not match the layout record: {exc}"
        ) from exc
    try:
        namespace_map = build_namespace_map()
    except PersistentLayoutError as exc:  # pragma: no cover - static audit is tested
        raise PersistRecoveryRequired(f"PERSIST namespace map is invalid: {exc}") from exc
    namespaces_root = persist_namespaces_root(root)
    for namespace in namespace_map.namespaces:
        candidate = namespaces_root / namespace
        if candidate.is_symlink() or not candidate.is_dir():
            raise PersistRecoveryRequired(
                f"PERSIST namespace is missing: {namespace}"
            )
    for mount in namespace_map.mount_plan():
        if mount.kind != MountKind.BIND_FILE or mount.namespace == "layout-authority":
            continue
        source = persist_mount_source_path(root, mount)
        if source.is_symlink() or not source.is_file():
            raise PersistRecoveryRequired(
                f"PERSIST file-bind source is missing: {mount.namespace}"
            )
    contract_path = persist_contract_path(root)
    if contract_path.is_symlink() or not contract_path.is_file():
        raise PersistRecoveryRequired("PERSIST state contract is missing")
    try:
        raw = contract_path.read_bytes()
        verify_persistent_state_contract_bytes(raw)
        expected = emit_persistent_state_contract(namespace_map)
        if raw != expected:
            raise PersistRecoveryRequired("PERSIST state contract drifted from the registry")
    except OSError as exc:
        raise PersistRecoveryRequired("PERSIST state contract is unreadable") from exc
    except PersistentLayoutError as exc:
        raise PersistRecoveryRequired(
            f"PERSIST state contract is not authoritative: {exc}"
        ) from exc
    return record, namespace_map
