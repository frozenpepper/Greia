"""Typed device observation, durable identity, target policy and live-media ancestry.

Session locators vs durable identity
------------------------------------
A block-device observation separates two fact families (see
``docs/architecture/UNIVERSAL_GREIA_SETUP_MEDIA_ARCHITECTURE.md`` sect. 1.8):

* session locators: ``/dev`` path, ``major:minor``, sysfs path. These address
  a device *right now* and are never destructive authority.
* durable identity facts: WWN / serial / NGUID / EUI where available, MMC CID
  for SD/eMMC where available, capacity, transport/topology facts.

``DeviceObservation`` carries both families as observed. ``DeviceIdentity``
carries only the durable family and is the sole authority for selection
persistence, refresh survival and pre-erase re-verification. ``fingerprint``
and ``identity_digest`` therefore exclude every session locator; the legacy
``BlockDevice`` name is kept as a plain alias of ``DeviceObservation`` so
existing construction sites keep working while new code uses the typed names.

Target policy
-------------
``InstallTargetPolicy`` is the polymorphic eligibility seam. The concrete
policy ids mirror the declarative image-profile authority
(``tools/build_profile.py::_ALLOWED_TARGET_POLICIES``):

* ``pc-internal-v1`` -- ordinary PC whole-disk install: positively eligible
  internal storage only; rejects the setup USB, removable/external media and
  MMC/SD media unless a positively identified built-in host owns it. Both the
  legacy-PC (Acer/i386) and modern-PC (amd64) profiles declare this policy;
  era differences belong to layout/boot adapters downstream, not eligibility.
* ``pi-builtin-microsd-v1`` -- accepts only the positively identified
  built-in microSD host. USB mass-storage install on Pi is a separate
  feature, not an accidental match.

There is no global ``allow_mmc`` switch: the old boolean is removed. Unknown
or ambiguous identity fails closed under every policy.

Legacy ATA fallback
-------------------
Some legacy ATA disks report no WWN/serial/NGUID/EUI/MMC identity at all. A
model+capacity fallback exists but is explicit and evidence-gated: policies
carry ``permit_legacy_ata_fallback=False`` by default and the resulting
identity is marked ``LEGACY_ATA_OBSERVATION_ONLY``. Enabling the flag
requires recorded physical observation evidence for the exact disk class. The
reference-Acer observation batch is DEFERRED (source-first amendment
2026-09-06), so the flag must stay ``False`` until that on-device evidence
exists. No ``/dev`` path or model string is ever hardcoded into policy.

Live-media ancestry
-------------------
``LiveMediaResolver`` proves which whole disk hosts the running setup medium
and is the only live-exclusion authority: labels are hints, never authority.
It reads the embedded ``greia.live_media_id`` (written by
``build/build-installer-image.sh``), finds the live mount source
``major:minor`` in mountinfo, and walks ``/sys/dev/block/<maj:min>`` plus
``/sys/class/block`` to the physical whole-disk ancestor. The whole disk and
all of its descendants are then ineligible for the session. Any ambiguity
means zero eligible targets. When neither a live identifier nor a live mount
is observable the session is provably not live and nothing is excluded.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol, Sequence


class DiskProbeError(RuntimeError):
    pass


EXTERNAL_TRANSPORTS = frozenset({"usb", "ieee1394", "firewire"})
MMC_DEVICE_PREFIX = "/dev/mmcblk"

#: Registered installer target-policy ids. Must stay in sync with the
#: declarative profile authority
#: ``tools/build_profile.py::_ALLOWED_TARGET_POLICIES`` (sync-tested).
PC_INTERNAL_POLICY_ID = "pc-internal-v1"
PI_BUILTIN_MICROSD_POLICY_ID = "pi-builtin-microsd-v1"
POLICY_IDS = frozenset({PC_INTERNAL_POLICY_ID, PI_BUILTIN_MICROSD_POLICY_ID})

#: Default whole-disk minimum for typed policies. Profile-derived layout
#: minimums (A/B + PERSIST + overhead) belong downstream; this floor only
#: preserves the historical single-target sanity bound.
DEFAULT_MINIMUM_BYTES = 4 * 1024**3

#: Embedded live-installer identity written by the media builder.
DEFAULT_LIVE_MEDIA_ID_PATH = Path("/etc/greia-os/live-media-id")
#: Live-medium mount established by the live boot path.
DEFAULT_LIVE_MOUNT_POINTS = ("/run/live/medium",)

_ALLOWED_DISK_DESCENDANT_TYPES = frozenset({"part"})


class IdentityProvenance(Enum):
    """Strength of the durable facts behind a :class:`DeviceIdentity`."""

    STRONG_STABLE = "strong-stable"
    LEGACY_ATA_OBSERVATION_ONLY = "legacy-ata-observation-only"
    UNKNOWN = "unknown"


def _clean(value: object) -> str:
    return str(value or "").strip()


@dataclass(frozen=True, slots=True)
class DeviceObservation:
    """One session-scoped block-device observation.

    ``path``, ``major_minor`` and ``sysfs_path`` are session locators used to
    address the device right now; they never participate in identity.
    ``wwn``/``serial``/``nguid``/``eui``/``mmc_cid`` plus ``size_bytes`` and
    ``transport`` are the durable family. ``mmc_host_built_in`` records a
    positive built-in-host identification (sysfs/host context, owned
    downstream); it defaults to ``False`` so MMC media fails closed.
    """

    name: str
    path: Path
    size_bytes: int
    device_type: str
    model: str
    serial: str
    transport: str
    removable: bool
    read_only: bool
    mountpoints: tuple[Path, ...]
    children: tuple["DeviceObservation", ...] = ()
    wwn: str = ""
    major_minor: str = ""
    hotplug: bool = False
    sysfs_path: str = ""
    nguid: str = ""
    eui: str = ""
    mmc_cid: str = ""
    mmc_host_built_in: bool = False

    @property
    def fingerprint(self) -> str:
        """Durable-identity fingerprint; session locators excluded."""
        return self.device_identity().identity_key

    @property
    def identity_digest(self) -> str:
        return hashlib.sha256(self.fingerprint.encode("utf-8")).hexdigest()

    def device_identity(
        self, *, allow_legacy_ata_fallback: bool = False
    ) -> "DeviceIdentity":
        return DeviceIdentity.from_observation(
            self, allow_legacy_ata_fallback=allow_legacy_ata_fallback
        )

    @property
    def human_size(self) -> str:
        gib = self.size_bytes / (1024**3)
        if gib >= 1:
            return f"{gib:.1f} GiB"
        return f"{self.size_bytes / (1024**2):.0f} MiB"

    @property
    def display_name(self) -> str:
        model = self.model.strip() or self.name
        return f"{model} · {self.human_size}"

    def all_mountpoints(self) -> tuple[Path, ...]:
        collected = list(self.mountpoints)
        for child in self.children:
            collected.extend(child.all_mountpoints())
        return tuple(dict.fromkeys(collected))

    def has_active_storage_stack(self) -> bool:
        for child in self.children:
            if child.device_type.strip().lower() not in _ALLOWED_DISK_DESCENDANT_TYPES:
                return True
            if child.has_active_storage_stack():
                return True
        return False

    def is_install_target_eligible(
        self,
        *,
        minimum_bytes: int = DEFAULT_MINIMUM_BYTES,
    ) -> bool:
        """Session-local pre-check under the default PC policy.

        This is an ergonomic pre-check only, not destructive authority:
        production selection must go through
        :meth:`DiskInventory.install_targets` with a typed policy and resolved
        :class:`LiveMediaAncestry`. The historical ``allow_mmc`` global switch
        is removed; MMC eligibility is typed policy behavior.
        """
        policy = PcInternalTargetPolicy(minimum_bytes=minimum_bytes)
        return policy.evaluate(self).eligible


#: Historical construction name. New code prefers ``DeviceObservation``.
BlockDevice = DeviceObservation


@dataclass(frozen=True, slots=True)
class DeviceIdentity:
    """Durable whole-disk identity: the only selection/destructive authority.

    ``model`` is populated only for the explicit legacy ATA fallback; strong
    identities never depend on human-readable model strings.
    """

    provenance: IdentityProvenance
    size_bytes: int = 0
    transport: str = ""
    wwn: str = ""
    serial: str = ""
    nguid: str = ""
    eui: str = ""
    mmc_cid: str = ""
    model: str = ""

    @classmethod
    def from_observation(
        cls,
        observation: DeviceObservation,
        *,
        allow_legacy_ata_fallback: bool = False,
    ) -> "DeviceIdentity":
        stable = {
            "wwn": _clean(observation.wwn),
            "serial": _clean(observation.serial),
            "nguid": _clean(observation.nguid),
            "eui": _clean(observation.eui),
            "mmc_cid": _clean(observation.mmc_cid),
        }
        size = int(observation.size_bytes)
        transport = _clean(observation.transport).lower()
        if any(stable.values()) and size > 0:
            return cls(
                provenance=IdentityProvenance.STRONG_STABLE,
                size_bytes=size,
                transport=transport,
                wwn=stable["wwn"],
                serial=stable["serial"],
                nguid=stable["nguid"],
                eui=stable["eui"],
                mmc_cid=stable["mmc_cid"],
            )
        # Explicit evidence-gated fallback for legacy ATA disks that report
        # no stable identifier at all. Never enabled by default: the
        # reference-Acer observation batch is deferred, so no policy may set
        # the flag until that on-device evidence is recorded.
        if (
            allow_legacy_ata_fallback
            and _clean(observation.model)
            and size > 0
        ):
            return cls(
                provenance=IdentityProvenance.LEGACY_ATA_OBSERVATION_ONLY,
                size_bytes=size,
                transport=transport,
                model=_clean(observation.model),
            )
        return cls(provenance=IdentityProvenance.UNKNOWN)

    @property
    def is_strong(self) -> bool:
        return self.provenance is IdentityProvenance.STRONG_STABLE

    @property
    def identity_key(self) -> str:
        if self.provenance is IdentityProvenance.STRONG_STABLE:
            parts = (
                "v1",
                "strong",
                f"wwn={self.wwn}",
                f"serial={self.serial}",
                f"nguid={self.nguid}",
                f"eui={self.eui}",
                f"cid={self.mmc_cid}",
                f"size={self.size_bytes}",
                f"tran={self.transport}",
            )
        elif self.provenance is IdentityProvenance.LEGACY_ATA_OBSERVATION_ONLY:
            parts = (
                "v1",
                "legacy-ata",
                f"model={self.model}",
                f"size={self.size_bytes}",
                f"tran={self.transport}",
            )
        else:
            parts = ("v1", "unknown")
        return "|".join(parts)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.identity_key.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    policy_id: str
    eligible: bool
    reason: str


class InstallTargetPolicy(ABC):
    """Polymorphic whole-disk eligibility seam.

    Concrete policies own one registered ``policy_id`` each. Shared
    fail-closed checks live in :meth:`evaluate`; only genuinely differing
    host/storage rules are overridden.
    """

    minimum_bytes: int = DEFAULT_MINIMUM_BYTES
    permit_legacy_ata_fallback: bool = False

    @property
    @abstractmethod
    def policy_id(self) -> str: ...

    @abstractmethod
    def _host_storage_eligible(
        self, observation: DeviceObservation, identity: DeviceIdentity
    ) -> str | None:
        """Return ``None`` when host/storage facts accept, else the reason."""

    def _identity_for(self, observation: DeviceObservation) -> DeviceIdentity:
        return DeviceIdentity.from_observation(
            observation,
            allow_legacy_ata_fallback=self.permit_legacy_ata_fallback,
        )

    def _removable_rejection(self, observation: DeviceObservation) -> str | None:
        if observation.removable or observation.hotplug:
            return "removable/external media is never an install target"
        return None

    def _transport_rejection(self, transport: str) -> str | None:
        if transport in EXTERNAL_TRANSPORTS:
            return (
                f"external transport {transport!r} is never an install target"
            )
        return None

    def evaluate(self, observation: DeviceObservation) -> PolicyDecision:
        pid = self.policy_id
        if observation.device_type != "disk":
            return PolicyDecision(pid, False, "not a whole disk")
        if observation.read_only:
            return PolicyDecision(pid, False, "device is read-only")
        if int(observation.size_bytes) < int(self.minimum_bytes):
            return PolicyDecision(pid, False, "device is below the minimum size")
        removable_reason = self._removable_rejection(observation)
        if removable_reason is not None:
            return PolicyDecision(pid, False, removable_reason)
        transport = _clean(observation.transport).lower()
        transport_reason = self._transport_rejection(transport)
        if transport_reason is not None:
            return PolicyDecision(pid, False, transport_reason)
        if observation.all_mountpoints() or observation.has_active_storage_stack():
            return PolicyDecision(
                pid, False, "device is in use (mounted or has an active storage stack)"
            )
        identity = self._identity_for(observation)
        if identity.provenance is IdentityProvenance.UNKNOWN:
            return PolicyDecision(
                pid,
                False,
                f"unknown/ambiguous device identity fails closed under {pid}",
            )
        host_reason = self._host_storage_eligible(observation, identity)
        if host_reason is not None:
            return PolicyDecision(pid, False, host_reason)
        if identity.provenance is IdentityProvenance.LEGACY_ATA_OBSERVATION_ONLY:
            return PolicyDecision(
                pid,
                True,
                f"eligible via explicit evidence-gated legacy ATA fallback under {pid}",
            )
        return PolicyDecision(pid, True, f"eligible internal target under {pid}")


@dataclass(frozen=True, slots=True)
class PcInternalTargetPolicy(InstallTargetPolicy):
    """Ordinary PC whole-disk rule behind the ``pc-internal-v1`` profile id.

    Both legacy-PC (Acer/i386) and modern-PC (amd64) install profiles declare
    this policy; era differences belong to layout/boot adapters downstream.
    MMC/SD nodes are rejected unless a positively identified built-in host
    owns them, so internal eMMC is never rejected merely for its ``/dev``
    prefix while ordinary card-reader media stays out.
    """

    minimum_bytes: int = DEFAULT_MINIMUM_BYTES
    permit_legacy_ata_fallback: bool = False

    @property
    def policy_id(self) -> str:
        return PC_INTERNAL_POLICY_ID

    def _host_storage_eligible(
        self, observation: DeviceObservation, identity: DeviceIdentity
    ) -> str | None:
        if observation.mmc_host_built_in:
            return None
        transport = _clean(observation.transport).lower()
        if transport == "mmc" or str(observation.path).startswith(MMC_DEVICE_PREFIX):
            return (
                "MMC/SD media is not an ordinary PC install target; "
                "it requires a positively identified built-in host"
            )
        return None


@dataclass(frozen=True, slots=True)
class PiBuiltInMicroSdTargetPolicy(InstallTargetPolicy):
    """Pi rule behind the ``pi-builtin-microsd-v1`` profile id.

    Accepts only the positively identified built-in microSD host. USB
    mass-storage install on Pi is a separate proven capability, not an
    accidental ``/dev/sdX`` match, and is rejected explicitly.
    """

    minimum_bytes: int = DEFAULT_MINIMUM_BYTES
    permit_legacy_ata_fallback: bool = False

    @property
    def policy_id(self) -> str:
        return PI_BUILTIN_MICROSD_POLICY_ID

    def _removable_rejection(self, observation: DeviceObservation) -> str | None:
        # Some built-in MMC hosts report their child SD card as removable or
        # hot-pluggable. This is expected on the Pi, but USB/removable drives
        # remain excluded by the transport+host-topology checks below.
        if observation.mmc_host_built_in and observation.mmc_cid:
            return None
        return super()._removable_rejection(observation)

    def _transport_rejection(self, transport: str) -> str | None:
        if transport in EXTERNAL_TRANSPORTS or transport == "usb":
            return (
                "USB mass-storage install on Pi is a separate feature, "
                "not an automatic target match"
            )
        return None

    def _host_storage_eligible(
        self, observation: DeviceObservation, identity: DeviceIdentity
    ) -> str | None:
        if not observation.mmc_host_built_in or not observation.mmc_cid:
            return "not a positively identified built-in microSD host with CID"
        if _clean(observation.transport).lower() not in {"", "mmc"}:
            return "built-in Pi microSD must have MMC (not external) transport"
        return None


def policy_for_profile_id(
    profile_id: str,
    *,
    minimum_bytes: int = DEFAULT_MINIMUM_BYTES,
) -> InstallTargetPolicy:
    """Return the typed policy for a declarative profile policy id.

    Unknown ids fail closed with :class:`DiskProbeError` instead of guessing.
    """
    if profile_id == PC_INTERNAL_POLICY_ID:
        return PcInternalTargetPolicy(minimum_bytes=minimum_bytes)
    if profile_id == PI_BUILTIN_MICROSD_POLICY_ID:
        return PiBuiltInMicroSdTargetPolicy(minimum_bytes=minimum_bytes)
    raise DiskProbeError(f"unknown installer target policy: {profile_id!r}")


def default_install_target_policy() -> InstallTargetPolicy:
    """Default policy preserving the historical installer behavior.

    The current whole-disk installer flow is the legacy-PC path, which the
    declarative profiles bind to ``pc-internal-v1``. Host-aware policy
    selection from profile compatibility belongs downstream.
    """
    return PcInternalTargetPolicy()


@dataclass(frozen=True, slots=True)
class LiveMediaAncestry:
    """Resolved setup-medium exclusion for one installer session."""

    live_media_id: str = ""
    whole_disk_names: frozenset[str] = frozenset()
    ambiguous: bool = False
    reason: str = "no live-installer context detected"

    @classmethod
    def empty(cls) -> "LiveMediaAncestry":
        return cls()

    @classmethod
    def ambiguous_ancestry(cls, reason: str) -> "LiveMediaAncestry":
        return cls(ambiguous=True, reason=reason)

    @property
    def is_live_context(self) -> bool:
        return bool(self.live_media_id) or bool(self.whole_disk_names)


def _read_live_media_id(path: Path) -> str | None:
    """Read the embedded live identifier; ``None`` when unprovable/invalid."""
    try:
        raw = path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeDecodeError):
        return None
    if not raw:
        return None
    try:
        parsed = uuid.UUID(raw)
    except ValueError:
        return None
    if raw != str(parsed):
        return None
    return raw


def _parse_mountinfo(text: str) -> list[tuple[str, str]]:
    """Parse mountinfo into ``(mountpoint, major:minor)`` pairs."""
    entries: list[tuple[str, str]] = []
    for line in text.splitlines():
        pre, _, _ = line.partition(" - ")
        fields = pre.split()
        if len(fields) < 5:
            continue
        major_minor = fields[2]
        mountpoint = fields[4].replace("\\040", " ").replace("\\011", "\t")
        if ":" not in major_minor:
            continue
        entries.append((mountpoint, major_minor))
    return entries


@dataclass(frozen=True, slots=True)
class LiveMediaResolver:
    """Physical-ancestry resolver for the setup medium (observation only).

    Resolution path: embedded ``greia.live_media_id`` file -> live mount
    source ``major:minor`` from mountinfo -> ``/sys/dev/block/<maj:min>``
    symlink -> ``/sys/class/block`` whole-disk ancestor (partitions carry a
    ``partition`` file; the ancestor is structural, never name-guessed).
    All inputs are injectable paths so unit proof runs on files/fakes with no
    partition/boot writes.
    """

    live_media_id_path: Path = field(
        default_factory=lambda: Path(DEFAULT_LIVE_MEDIA_ID_PATH)
    )
    mountinfo_path: Path = field(default_factory=lambda: Path("/proc/self/mountinfo"))
    sys_dev_block_root: Path = field(default_factory=lambda: Path("/sys/dev/block"))
    sys_class_block_root: Path = field(
        default_factory=lambda: Path("/sys/class/block")
    )
    live_mount_points: tuple[str, ...] = DEFAULT_LIVE_MOUNT_POINTS

    def whole_disk_ancestor(self, major_minor: str) -> str | None:
        """Map a session ``major:minor`` to its whole-disk name via sysfs."""
        cleaned = major_minor.strip()
        halves = cleaned.split(":")
        if len(halves) != 2 or not all(part.isdigit() for part in halves):
            return None
        link = self.sys_dev_block_root / cleaned
        try:
            target = os.path.realpath(os.fspath(link))
        except OSError:
            return None
        block_name = os.path.basename(target.rstrip("/"))
        if not block_name:
            return None
        class_node = self.sys_class_block_root / block_name
        try:
            if not class_node.exists() and not os.path.islink(os.fspath(class_node)):
                return None
        except OSError:
            return None
        try:
            is_partition = (class_node / "partition").is_file()
        except OSError:
            return None
        if not is_partition:
            return block_name
        try:
            parent_target = os.path.realpath(os.fspath(class_node))
        except OSError:
            return None
        ancestor = os.path.basename(os.path.dirname(parent_target.rstrip("/")))
        if not ancestor:
            return None
        try:
            ancestor_node = self.sys_class_block_root / ancestor
            if not ancestor_node.exists() and not os.path.islink(
                os.fspath(ancestor_node)
            ):
                return None
        except OSError:
            return None
        return ancestor

    def resolve(self, inventory: "DiskInventory | None" = None) -> LiveMediaAncestry:
        """Resolve the setup-medium whole-disk ancestor; never raises.

        Unreadable inputs fail closed to ambiguity, except the provably
        non-live combination (no identifier file plus readable mountinfo with
        no live mount), which yields an empty, non-ambiguous exclusion. When
        an inventory is supplied, an ancestor outside its whole-disk names
        (e.g. a device-mapper node) is ambiguous rather than silently missed.
        """
        live_id: str | None
        try:
            live_id = _read_live_media_id(self.live_media_id_path)
            id_file_missing = live_id is None and not self.live_media_id_path.exists()
        except OSError:
            return LiveMediaAncestry.ambiguous_ancestry(
                "embedded live-media identifier is unreadable; failing closed"
            )
        try:
            mountinfo_text = self.mountinfo_path.read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError:
            mountinfo_text = ""
        entries = _parse_mountinfo(mountinfo_text) if mountinfo_text else []
        live_sources = sorted(
            {major_minor for mountpoint, major_minor in entries
             if mountpoint in self.live_mount_points}
        )
        id_present = live_id is not None
        if not id_present and not live_sources:
            if mountinfo_text and id_file_missing:
                return LiveMediaAncestry.empty()
            return LiveMediaAncestry.ambiguous_ancestry(
                "live-installer context cannot be proven nor ruled out; failing closed"
            )
        if not id_present:
            return LiveMediaAncestry.ambiguous_ancestry(
                "live mount is present without an embedded live-media identifier; "
                "failing closed"
            )
        if not live_sources:
            return LiveMediaAncestry.ambiguous_ancestry(
                "embedded live-media identifier is present but no live mount source "
                "resolves; failing closed"
            )
        if len(live_sources) != 1:
            return LiveMediaAncestry.ambiguous_ancestry(
                "multiple distinct live mount sources resolve; failing closed"
            )
        ancestor = self.whole_disk_ancestor(live_sources[0])
        if ancestor is None:
            return LiveMediaAncestry.ambiguous_ancestry(
                "live mount source does not resolve to a whole disk via sysfs; "
                "failing closed"
            )
        if inventory is not None and ancestor not in {
            device.name for device in inventory.devices
        }:
            return LiveMediaAncestry.ambiguous_ancestry(
                f"resolved setup-medium ancestor {ancestor!r} is not a known whole "
                "disk; failing closed"
            )
        assert live_id is not None
        return LiveMediaAncestry(
            live_media_id=live_id,
            whole_disk_names=frozenset({ancestor}),
            ambiguous=False,
            reason=(
                f"setup medium resolves to whole disk {ancestor!r} via "
                f"major:minor {live_sources[0]}"
            ),
        )


@dataclass(frozen=True, slots=True)
class TargetSelection:
    """Identity-keyed target selection surviving inventory refresh.

    The UI must store this (durable identity plus the eligibility facts that
    held at selection time), never a ``/dev`` path, list index or label. A
    prior selection survives :meth:`reselect` only when the identity still
    resolves and every eligibility fact still matches under the same policy.
    """

    identity_key: str
    provenance: IdentityProvenance
    size_bytes: int
    read_only: bool
    removable: bool
    hotplug: bool
    transport: str
    mountpoints: tuple[str, ...]
    has_active_storage_stack: bool
    policy_id: str

    @classmethod
    def from_observation(
        cls, observation: DeviceObservation, policy: InstallTargetPolicy
    ) -> "TargetSelection":
        identity = DeviceIdentity.from_observation(
            observation,
            allow_legacy_ata_fallback=policy.permit_legacy_ata_fallback,
        )
        return cls(
            identity_key=identity.identity_key,
            provenance=identity.provenance,
            size_bytes=int(observation.size_bytes),
            read_only=bool(observation.read_only),
            removable=bool(observation.removable),
            hotplug=bool(observation.hotplug),
            transport=_clean(observation.transport).lower(),
            mountpoints=tuple(sorted(str(path) for path in observation.all_mountpoints())),
            has_active_storage_stack=bool(observation.has_active_storage_stack()),
            policy_id=policy.policy_id,
        )

    def reselect(
        self,
        inventory: "DiskInventory",
        policy: InstallTargetPolicy,
        *,
        excluded: LiveMediaAncestry | None = None,
    ) -> DeviceObservation | None:
        """Return the surviving observation, or ``None`` when invalidated."""
        if self.provenance is IdentityProvenance.UNKNOWN:
            return None
        if policy.policy_id != self.policy_id:
            return None
        if excluded is not None and excluded.ambiguous:
            return None
        candidates = []
        for device in inventory.devices:
            identity = DeviceIdentity.from_observation(
                device,
                allow_legacy_ata_fallback=policy.permit_legacy_ata_fallback,
            )
            if identity.identity_key == self.identity_key:
                candidates.append((device, identity))
        if len(candidates) != 1:
            return None
        device, identity = candidates[0]
        if identity.provenance is not self.provenance:
            return None
        if (
            int(device.size_bytes) != self.size_bytes
            or bool(device.read_only) != self.read_only
            or bool(device.removable) != self.removable
            or bool(device.hotplug) != self.hotplug
            or _clean(device.transport).lower() != self.transport
            or tuple(sorted(str(path) for path in device.all_mountpoints()))
            != self.mountpoints
            or bool(device.has_active_storage_stack())
            != self.has_active_storage_stack
        ):
            return None
        if excluded is not None and device.name in excluded.whole_disk_names:
            return None
        if not policy.evaluate(device).eligible:
            return None
        return device


@dataclass(frozen=True, slots=True)
class DiskInventory:
    """One bounded inventory generation from a single probe."""

    devices: tuple[DeviceObservation, ...]
    generation: int = 0

    def by_path(self, path: Path) -> DeviceObservation | None:
        """Session-locator lookup; never destructive authority on its own."""
        resolved = path.resolve()
        return next(
            (device for device in self.devices if device.path.resolve() == resolved),
            None,
        )

    def by_identity(self, identity: DeviceIdentity) -> DeviceObservation | None:
        """Durable-identity lookup; ``None`` on missing or ambiguous match."""
        if identity.provenance is IdentityProvenance.UNKNOWN:
            return None
        matches = [
            device
            for device in self.devices
            if DeviceIdentity.from_observation(
                device,
                allow_legacy_ata_fallback=(
                    identity.provenance
                    is IdentityProvenance.LEGACY_ATA_OBSERVATION_ONLY
                ),
            ).identity_key
            == identity.identity_key
        ]
        if len(matches) != 1:
            return None
        return matches[0]

    def install_targets(
        self,
        policy: InstallTargetPolicy,
        *,
        excluded: LiveMediaAncestry | None = None,
    ) -> tuple[DeviceObservation, ...]:
        """Eligible whole disks under ``policy`` minus setup-medium ancestry.

        Ambiguous ancestry yields zero targets. Only ``type == "disk"``
        observations can pass via policy; whole-disk exclusion therefore also
        excludes every descendant of the setup medium.
        """
        if excluded is not None and excluded.ambiguous:
            return ()
        forbidden = (
            set(excluded.whole_disk_names)
            if excluded is not None
            else set()
        )
        selected: list[DeviceObservation] = []
        for device in self.devices:
            if device.name in forbidden:
                continue
            if policy.evaluate(device).eligible:
                selected.append(device)
        return tuple(selected)


class CommandRunner(Protocol):
    def run(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]: ...


class SubprocessRunner:
    def run(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(command),
            check=False,
            shell=False,
            text=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )



@dataclass(frozen=True, slots=True)
class PiMmcHostObserver:
    """Positive Pi 400/500 MMC host + card-CID evidence from Linux sysfs.

    The normal lsblk JSON has no MMC CID column in older util-linux and no
    built-in-host property at all. Resolve block ancestry through sysfs and
    require an explicit recognized board model, a platform-owned MMC host
    and the actual card's CID. No device path/number guess authorizes a wipe.
    All filesystem roots are injected so tests never inspect host hardware.
    """

    board_model_path: Path = Path("/proc/device-tree/model")
    class_block_root: Path = Path("/sys/class/block")
    platform_root: Path = Path("/sys/devices/platform")

    def observe(self, name: str) -> tuple[str, bool]:
        if not isinstance(name, str) or re.fullmatch(r"mmcblk[0-9]+", name) is None:
            return "", False
        try:
            model = self.board_model_path.read_bytes().rstrip(bytes((0,))).decode("ascii")
            if not (
                model.startswith("Raspberry Pi 400 Rev ")
                or model.startswith("Raspberry Pi 500 Rev ")
            ):
                return "", False
            platform = self.platform_root.resolve(strict=True)
            node = (self.class_block_root / name).resolve(strict=True)
            parts = node.relative_to(platform).parts
            # Platform MMC controller -> mmc_host -> card -> block device.
            if "mmc_host" not in parts or "block" not in parts:
                return "", False
            if any(part.startswith(("usb", "pci")) for part in parts):
                return "", False
            if parts[-1] != name:
                return "", False
            card_cid = (self.class_block_root / name / "device" / "cid").read_text(
                encoding="ascii"
            ).strip().lower()
            if re.fullmatch(r"[0-9a-f]{32}", card_cid) is None:
                return "", False
            return card_cid, True
        except (OSError, ValueError, UnicodeDecodeError):
            return "", False


class LsblkDiskProbe:
    """lsblk adapter producing :class:`DiskInventory` generations.

    Labels, PARTLABELs and other presentation strings are parsed but never
    consulted: they are not observation fields and cannot affect identity or
    eligibility. Extra stable-identity keys (``nguid``/``eui``/``cid``) pass
    through when a newer lsblk/fake provides them.
    """

    FIELDS = "NAME,PATH,SIZE,TYPE,RM,HOTPLUG,RO,MOUNTPOINTS,MODEL,SERIAL,WWN,MAJ:MIN,TRAN"

    def __init__(
        self, runner: CommandRunner | None = None,
        *,
        mmc_host_observer: PiMmcHostObserver | None = None,
    ):
        self.runner = runner or SubprocessRunner()
        self.mmc_host_observer = mmc_host_observer or PiMmcHostObserver()
        self._generation = 0

    def probe(self) -> DiskInventory:
        completed = self.runner.run(
            ["lsblk", "--json", "--bytes", "--output", self.FIELDS]
        )
        if completed.returncode != 0:
            raise DiskProbeError(completed.stderr.strip() or "lsblk failed")
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise DiskProbeError("lsblk returned invalid JSON") from exc
        raw_devices = payload.get("blockdevices")
        if not isinstance(raw_devices, list):
            raise DiskProbeError("lsblk response has no blockdevices array")
        devices = tuple(
            self._parse_device(item) for item in raw_devices if isinstance(item, dict)
        )
        self._generation += 1
        return DiskInventory(devices, generation=self._generation)

    def _parse_device(self, raw: dict[str, object]) -> DeviceObservation:
        children_raw = raw.get("children")
        children = (
            tuple(
                self._parse_device(item)
                for item in children_raw
                if isinstance(item, dict)
            )
            if isinstance(children_raw, list)
            else ()
        )
        mountpoints_raw = raw.get("mountpoints")
        mountpoints: list[Path] = []
        if isinstance(mountpoints_raw, list):
            for mountpoint in mountpoints_raw:
                if isinstance(mountpoint, str) and mountpoint:
                    mountpoints.append(Path(mountpoint))
        elif isinstance(raw.get("mountpoint"), str) and raw.get("mountpoint"):
            mountpoints.append(Path(str(raw["mountpoint"])))
        try:
            name = str(raw.get("name", ""))
            observed_cid, builtin = self.mmc_host_observer.observe(name)
            return DeviceObservation(
                name=name,
                path=Path(str(raw["path"])),
                size_bytes=int(raw.get("size", 0)),
                device_type=str(raw.get("type", "")),
                model=str(raw.get("model") or ""),
                serial=str(raw.get("serial") or ""),
                transport=str(raw.get("tran") or ""),
                removable=bool(int(raw.get("rm", 0))),
                read_only=bool(int(raw.get("ro", 0))),
                mountpoints=tuple(mountpoints),
                children=children,
                wwn=str(raw.get("wwn") or ""),
                major_minor=str(raw.get("maj:min") or raw.get("maj_min") or ""),
                hotplug=bool(int(raw.get("hotplug", 0))),
                nguid=str(raw.get("nguid") or ""),
                eui=str(raw.get("eui") or ""),
                mmc_cid=observed_cid if builtin else str(raw.get("cid") or raw.get("mmc_cid") or ""),
                mmc_host_built_in=builtin,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DiskProbeError(f"invalid lsblk device record: {exc}") from exc


def partition_number_path(device_path: Path, number: int) -> Path:
    """Derive the kernel partition node for ``number`` on ``device_path``.

    The number always comes from a validated :mod:`greia_installer.layout`
    plan (position in the adapter's declarative partition order), never from
    UI/Parent input. ``/dev/sdX``-style bases take a bare suffix while
    digit-ending bases (``/dev/mmcblk0``, ``/dev/loop0``, ``/dev/nvme0n1``)
    take the ``p`` separator, matching historical ``partition_one_path``.
    """
    if isinstance(number, bool) or not isinstance(number, int):
        raise DiskProbeError("partition number must be an integer")
    if not 1 <= number <= 128:
        raise DiskProbeError("partition number is outside Greia bounds")
    name = str(device_path)
    if not name:
        raise DiskProbeError("device path is empty")
    return Path(f"{name}p{number}" if name[-1:].isdigit() else f"{name}{number}")


def partition_one_path(device_path: Path) -> Path:
    return partition_number_path(device_path, 1)
