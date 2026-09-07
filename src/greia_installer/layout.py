"""Typed destructive-layout adapters and common plan validation (A8-LAYOUT).

Phase 8A Step 8A.1: the common destructive substrate on loop/disposable
media. Each adapter returns a declarative :class:`LayoutPlan` carrying
semantic roles, sizes, alignments, filesystem types, flags and expected
identities; :func:`validate_layout_plan` proves feasibility before any
platform-specific partition command runs.

Adapter identities are the canonical source-owned ``storage.layout_adapter``
ids (``tools/build_profile.py``, mirrored by
``greia_platform.persistent_layout``): ``legacy-bios-ab-v1`` (executable
here), ``modern-gpt-ab-v1`` and ``pi-mbr-tryboot-ab-v1`` (registered
role-model skeletons; full execution deferred to Phases 8C/8D). The brief's
``modern-uefi-ab-v1`` / ``pi-tryboot-ab-v1`` shorthands denote these same
canonical adapters. No parallel vocabulary is introduced.

No arbitrary shell/path authority:

- partition commands are argument arrays run with ``shell=False`` by the
  caller's runner; this module never builds a shell string;
- the plan carries no device paths and no partition numbers from outside:
  numbers are the adapter's declarative order, and the device locator is
  taken only from the verified :class:`DeviceObservation` passed to
  :meth:`LayoutAdapter.execute`;
- target eligibility stays with the typed ``InstallTargetPolicy`` and the
  live-media ancestry resolver in :mod:`greia_installer.disk`; this module
  re-checks only plan fit against the verified target.

Interaction surfaces: ``system-a`` / ``system-b`` roles match
``greia_platform.slot_writer.DestinationSlot`` and
``PARTITION_ROLES`` in ``greia_platform.persistent_layout`` (A8-SLOTWRITE
slot targets); the trailing ``persist`` remainder role matches the PERSIST
namespace authority (A8-PERSIST init).

Phase 8B Step 8B.1 (X8-LAYOUT) adds the installer-owned profile seam on top
of the 8A adapters: :class:`ProfileSizing` carries the release-profile
``storage``/``updates`` facts (``system_slot_bytes``,
``persistent_minimum_bytes``, layout adapter, boot backend) so sizes come
only from profile data; :func:`plan_for_profile` resolves the adapter and
returns the validated plan; :func:`require_finalized_slot_capacity` rejects
undersized profiles with the finalizer capacity bound
(base + support-set installed-size bound + boot-artifact growth bound +
metadata/reserve <= slot capacity); :func:`mint_fresh_partition_identities`
mints the distinct role-owned PARTUUID/filesystem-UUID pairs recorded in
layout authority (never cloned template UUIDs). ``BOOT_CONTROL`` stays
outside the layout record by design: it owns stable GRUB
configuration/environment outside both replaceable A/B roots and is never
rewritten by slot updates, while the record tracks exactly the
``system-a`` / ``system-b`` / ``persist`` roles.
"""

from __future__ import annotations

import re
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Sequence

from greia_platform.persistent_layout import (
    MAX_SYSTEM_SLOT_BYTES,
    MIN_PERSIST_BYTES,
    MIN_SYSTEM_SLOT_BYTES,
)
from greia_platform.slot_writer import (
    FINALIZATION_GROWTH_BYTES,
    SLOT_METADATA_RESERVE_BYTES,
)

from .disk import DeviceObservation, DiskProbeError, partition_number_path


class LayoutError(RuntimeError):
    """Layout plan validation or adapter execution failed fail-closed."""


MIB = 1024 * 1024

#: Every partition start and every fixed size is 1 MiB aligned.
PARTITION_ALIGNMENT_BYTES = MIB

#: Bytes reserved before the first partition. On ``msdos`` this preserves the
#: >=1 MiB GRUB embedding space required by the legacy installed-disk format
#: (setup-media architecture sect. 9); GPT headers fit the same reservation.
LABEL_RESERVED_BYTES = MIB

#: Highest partition number an adapter may declare (GPT bound; msdos paths
#: stay far below it).
MAX_PARTITION_NUMBER = 128

#: Filesystems an adapter may declare. ``none`` covers raw partitions such as
#: the GPT BIOS Boot partition that carry no filesystem at all.
ALLOWED_FILESYSTEMS = frozenset({"ext4", "fat32", "none"})

#: Partition-table flag names an adapter may declare (parted vocabulary).
ALLOWED_FLAGS = frozenset({"boot", "esp", "bios_grub"})

#: Partition-table kinds an adapter may declare.
ALLOWED_LABEL_TYPES = frozenset({"msdos", "gpt"})

#: Canonical layout-adapter ids (owned by tools/build_profile.py; mirrored
#: here instead of re-parsing build profiles at install time).
LEGACY_BIOS_AB_ADAPTER_ID = "legacy-bios-ab-v1"
MODERN_GPT_AB_ADAPTER_ID = "modern-gpt-ab-v1"
PI_MBR_TRYBOOT_AB_ADAPTER_ID = "pi-mbr-tryboot-ab-v1"
KNOWN_LAYOUT_ADAPTER_IDS = frozenset(
    {
        LEGACY_BIOS_AB_ADAPTER_ID,
        MODERN_GPT_AB_ADAPTER_ID,
        PI_MBR_TRYBOOT_AB_ADAPTER_ID,
    }
)

#: Slot roles whose size must equal the release profile ``slot_bytes``.
SLOT_ROLES = frozenset({"system-a", "system-b"})

#: The fill-remainder partition must carry this role in every adapter.
REMAINDER_ROLE = "persist"

_ROLE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
_LABEL_RE = re.compile(r"^[A-Z0-9_]{1,16}$")
_SHELL_METACHARACTERS = (";", "&", "|", "$", "`", "(", ")", "<", ">", "\n")


def _require_role(value: object) -> str:
    if not isinstance(value, str) or not _ROLE_RE.fullmatch(value):
        raise LayoutError(f"partition role is outside Greia bounds: {value!r}")
    return value


def _require_label(value: object, *, filesystem: str) -> str:
    if filesystem == "none":
        if value != "":
            raise LayoutError("raw partitions carry no filesystem label")
        return ""
    if not isinstance(value, str) or not _LABEL_RE.fullmatch(value):
        raise LayoutError(
            "filesystem label must be 1-16 chars of A-Z, 0-9, underscore"
        )
    return value


def _require_mib_multiple(value: int, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise LayoutError(f"{field_name} must be a positive integer")
    if value % PARTITION_ALIGNMENT_BYTES:
        raise LayoutError(f"{field_name} must be 1 MiB aligned")
    return value


@dataclass(frozen=True, slots=True)
class PlannedPartition:
    """One declarative partition: fixed size or the trailing remainder.

    ``size_bytes=None`` marks the fill-remainder partition; common validation
    requires exactly one, carrying the ``persist`` role with the highest
    partition number. ``number`` is the adapter's declarative order, never an
    external input.
    """

    number: int
    role: str
    size_bytes: int | None
    filesystem: str
    label: str = ""
    flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.number, bool) or not isinstance(self.number, int):
            raise LayoutError("partition number must be an integer")
        if not 1 <= self.number <= MAX_PARTITION_NUMBER:
            raise LayoutError("partition number is outside Greia bounds")
        object.__setattr__(self, "role", _require_role(self.role))
        if self.filesystem not in ALLOWED_FILESYSTEMS:
            raise LayoutError(f"unknown filesystem: {self.filesystem!r}")
        object.__setattr__(
            self, "label", _require_label(self.label, filesystem=self.filesystem)
        )
        if not isinstance(self.flags, tuple) or any(
            not isinstance(item, str) for item in self.flags
        ):
            raise LayoutError("partition flags must be a tuple of text")
        unknown = sorted(set(self.flags) - ALLOWED_FLAGS)
        if unknown:
            raise LayoutError(
                "unknown partition flags: " + ", ".join(unknown)
            )
        if len(set(self.flags)) != len(self.flags):
            raise LayoutError("partition flags carry duplicates")
        if self.size_bytes is not None:
            _require_mib_multiple(self.size_bytes, field_name="partition size_bytes")


@dataclass(frozen=True, slots=True)
class LayoutPlan:
    """Declarative, validated partition layout for one target device size.

    Carries no device paths, no shell text and no caller-supplied partition
    numbers. ``device_size_bytes`` is the capacity the plan was proven
    against; :meth:`LayoutAdapter.execute` re-proves fit against the
    verified target before running anything.
    """

    adapter_id: str
    label_type: str
    device_size_bytes: int
    slot_bytes: int
    persist_minimum_bytes: int
    boot_backend: str
    partitions: tuple[PlannedPartition, ...]

    def __post_init__(self) -> None:
        validate_layout_plan(self)

    def by_role(self, role: str) -> PlannedPartition | None:
        for partition in self.partitions:
            if partition.role == role:
                return partition
        return None

    def fixed_bytes(self) -> int:
        return sum(
            partition.size_bytes
            for partition in self.partitions
            if partition.size_bytes is not None
        )

    def remainder_bytes(self) -> int:
        return int(self.device_size_bytes) - LABEL_RESERVED_BYTES - self.fixed_bytes()


def validate_layout_plan(plan: LayoutPlan) -> None:
    """Prove plan feasibility; raise :class:`LayoutError` fail-closed.

    Checks adapter registration, label type, slot/PERSIST bounds, role-model
    fit (exact expected role set per adapter), uniqueness, alignment,
    slot-size binding for ``system-a``/``system-b``, trailing-``persist``
    remainder coverage, and device fit. Runs both at plan construction and
    again immediately before any partition command executes.
    """
    if plan.adapter_id not in KNOWN_LAYOUT_ADAPTER_IDS:
        raise LayoutError(f"unknown layout adapter: {plan.adapter_id!r}")
    if plan.label_type not in ALLOWED_LABEL_TYPES:
        raise LayoutError(f"unknown partition-table type: {plan.label_type!r}")
    if (
        isinstance(plan.device_size_bytes, bool)
        or not isinstance(plan.device_size_bytes, int)
        or plan.device_size_bytes <= 0
    ):
        raise LayoutError("device_size_bytes must be a positive integer")
    if not MIN_SYSTEM_SLOT_BYTES <= int(plan.slot_bytes) <= MAX_SYSTEM_SLOT_BYTES:
        raise LayoutError("slot_bytes is outside the Greia slot bound")
    if (
        isinstance(plan.persist_minimum_bytes, bool)
        or not isinstance(plan.persist_minimum_bytes, int)
        or int(plan.persist_minimum_bytes) < MIN_PERSIST_BYTES
    ):
        raise LayoutError("persist_minimum_bytes is below the Greia PERSIST floor")
    if not isinstance(plan.boot_backend, str) or not plan.boot_backend:
        raise LayoutError("boot_backend must be non-empty text")
    expected_backend = _ADAPTER_BOOT_BACKENDS.get(plan.adapter_id)
    if expected_backend is not None and plan.boot_backend != expected_backend:
        raise LayoutError("boot_backend does not match the layout adapter")
    if not plan.partitions:
        raise LayoutError("layout plan carries no partitions")
    numbers = [partition.number for partition in plan.partitions]
    if len(set(numbers)) != len(numbers):
        raise LayoutError("layout plan carries duplicate partition numbers")
    roles = [partition.role for partition in plan.partitions]
    if len(set(roles)) != len(roles):
        raise LayoutError("layout plan carries duplicate semantic roles")
    expected_roles = _ADAPTER_ROLES.get(plan.adapter_id)
    if expected_roles is not None and set(roles) != set(expected_roles):
        raise LayoutError(
            f"layout roles {sorted(roles)} do not match adapter "
            f"{plan.adapter_id!r} role model {sorted(expected_roles)}"
        )
    remainders = [
        partition for partition in plan.partitions if partition.size_bytes is None
    ]
    if len(remainders) != 1:
        raise LayoutError("layout plan must carry exactly one remainder partition")
    remainder = remainders[0]
    if remainder.role != REMAINDER_ROLE:
        raise LayoutError("the remainder partition must carry the persist role")
    if remainder.number != max(numbers):
        raise LayoutError("the remainder partition must be the trailing partition")
    for partition in plan.partitions:
        if partition.role in SLOT_ROLES and partition.size_bytes != int(plan.slot_bytes):
            raise LayoutError(
                f"slot role {partition.role!r} must equal the profile slot_bytes"
            )
    fixed = sum(
        partition.size_bytes
        for partition in plan.partitions
        if partition.size_bytes is not None
    )
    if LABEL_RESERVED_BYTES + fixed + int(plan.persist_minimum_bytes) > int(
        plan.device_size_bytes
    ):
        raise LayoutError(
            "layout plan does not fit the device: reserved + fixed partitions "
            "+ PERSIST minimum exceeds device_size_bytes"
        )


class PartitionCommandRunner:
    """Narrow runner seam: argument arrays only, never shell strings."""

    def run(self, command: Sequence[str]) -> object: ...  # pragma: no cover


def _check_command(argv: tuple[str, ...]) -> tuple[str, ...]:
    """Reject shell-string-shaped commands before they can reach a runner."""
    if not argv or any(not isinstance(word, str) or not word for word in argv):
        raise LayoutError("partition commands must be non-empty text arrays")
    for word in argv:
        for marker in _SHELL_METACHARACTERS:
            if marker in word:
                raise LayoutError(
                    "partition commands must not carry shell metacharacters"
                )
    return argv


class LayoutAdapter(ABC):
    """Polymorphic destructive-layout seam behind the canonical adapter ids."""

    @property
    @abstractmethod
    def adapter_id(self) -> str: ...

    @property
    @abstractmethod
    def label_type(self) -> str: ...

    @property
    @abstractmethod
    def boot_backend(self) -> str: ...

    @property
    @abstractmethod
    def expected_roles(self) -> tuple[str, ...]: ...

    @abstractmethod
    def plan(
        self,
        *,
        device_size_bytes: int,
        slot_bytes: int,
        persist_minimum_bytes: int,
    ) -> LayoutPlan:
        """Return the validated declarative plan for a device capacity."""

    @abstractmethod
    def build_commands(
        self, plan: LayoutPlan, target: DeviceObservation
    ) -> tuple[tuple[str, ...], ...]:
        """Return the ordered partition/filesystem argument arrays.

        The device locator comes only from the verified ``target``
        observation; the plan contributes sizes, roles, filesystems, flags
        and labels, never paths.
        """

    def execute(
        self,
        runner: PartitionCommandRunner,
        *,
        target: DeviceObservation,
        plan: LayoutPlan,
    ) -> tuple[tuple[str, ...], ...]:
        """Re-validate, re-prove device fit, then run the adapter commands."""
        if plan.adapter_id != self.adapter_id:
            raise LayoutError("layout plan does not belong to this adapter")
        if target.device_type != "disk":
            raise LayoutError("layout execution requires a whole-disk target")
        validate_layout_plan(plan)
        if int(target.size_bytes) < int(plan.device_size_bytes):
            raise LayoutError(
                "verified target is smaller than the proven plan capacity"
            )
        resized = LayoutPlan(
            adapter_id=plan.adapter_id,
            label_type=plan.label_type,
            device_size_bytes=int(target.size_bytes),
            slot_bytes=int(plan.slot_bytes),
            persist_minimum_bytes=int(plan.persist_minimum_bytes),
            boot_backend=plan.boot_backend,
            partitions=plan.partitions,
        )
        commands = self.build_commands(resized, target)
        for argv in commands:
            runner.run(list(argv))
        return commands

    def _mkpart_extents(
        self, plan: LayoutPlan
    ) -> list[tuple[PlannedPartition, int, int | None]]:
        """Return ``(partition, start_mib, end_mib_or_None)`` in number order."""
        ordered = sorted(plan.partitions, key=lambda item: item.number)
        cursor = LABEL_RESERVED_BYTES
        if cursor % PARTITION_ALIGNMENT_BYTES:
            raise LayoutError("label reservation breaks partition alignment")
        extents: list[tuple[PlannedPartition, int, int | None]] = []
        for partition in ordered:
            if cursor % PARTITION_ALIGNMENT_BYTES:
                raise LayoutError("partition start breaks alignment")
            start_mib = cursor // MIB
            if partition.size_bytes is None:
                extents.append((partition, start_mib, None))
            else:
                cursor += int(partition.size_bytes)
                extents.append((partition, start_mib, cursor // MIB))
        return extents


class LegacyBiosAbAdapter(LayoutAdapter):
    """Executable MBR A/B adapter (setup-media architecture sect. 9).

    ``MBR + >=1 MiB GRUB embedding space`` followed by boot-control,
    system-A, system-B and the PERSIST remainder. BOOT_CONTROL owns stable
    GRUB configuration/environment outside both replaceable system slots.
    """

    #: Boot-control filesystem size; keeps total fixed overhead
    #: (1 MiB reserve + 32 MiB) inside the 64 MiB profile layout headroom.
    BOOT_CONTROL_BYTES = 32 * MIB

    @property
    def adapter_id(self) -> str:
        return LEGACY_BIOS_AB_ADAPTER_ID

    @property
    def label_type(self) -> str:
        return "msdos"

    @property
    def boot_backend(self) -> str:
        return "grub-ab-v1"

    @property
    def expected_roles(self) -> tuple[str, ...]:
        return ("boot-control", "system-a", "system-b", "persist")

    def plan(
        self,
        *,
        device_size_bytes: int,
        slot_bytes: int,
        persist_minimum_bytes: int,
    ) -> LayoutPlan:
        _require_mib_multiple(int(slot_bytes), field_name="slot_bytes")
        return LayoutPlan(
            adapter_id=self.adapter_id,
            label_type=self.label_type,
            device_size_bytes=int(device_size_bytes),
            slot_bytes=int(slot_bytes),
            persist_minimum_bytes=int(persist_minimum_bytes),
            boot_backend=self.boot_backend,
            partitions=(
                PlannedPartition(
                    number=1,
                    role="boot-control",
                    size_bytes=self.BOOT_CONTROL_BYTES,
                    filesystem="ext4",
                    label="GREIA_BOOT",
                    flags=("boot",),
                ),
                PlannedPartition(
                    number=2,
                    role="system-a",
                    size_bytes=int(slot_bytes),
                    filesystem="ext4",
                    label="GREIA_SYS_A",
                ),
                PlannedPartition(
                    number=3,
                    role="system-b",
                    size_bytes=int(slot_bytes),
                    filesystem="ext4",
                    label="GREIA_SYS_B",
                ),
                PlannedPartition(
                    number=4,
                    role="persist",
                    size_bytes=None,
                    filesystem="ext4",
                    label="GREIA_PERSIST",
                ),
            ),
        )

    def build_commands(
        self, plan: LayoutPlan, target: DeviceObservation
    ) -> tuple[tuple[str, ...], ...]:
        if plan.adapter_id != self.adapter_id:
            raise LayoutError("layout plan does not belong to this adapter")
        validate_layout_plan(plan)
        device = str(target.path)
        if not device or not target.path.is_absolute():
            raise LayoutError("verified target carries no absolute device locator")
        commands: list[tuple[str, ...]] = [
            _check_command(("wipefs", "--all", "--force", device)),
            _check_command(("parted", "--script", device, "mklabel", "msdos")),
        ]
        for partition, start_mib, end_mib in self._mkpart_extents(plan):
            end = f"{end_mib}MiB" if end_mib is not None else "100%"
            commands.append(
                _check_command(
                    (
                        "parted",
                        "--script",
                        device,
                        "mkpart",
                        "primary",
                        partition.filesystem,
                        f"{start_mib}MiB",
                        end,
                    )
                )
            )
        commands.append(
            _check_command(("parted", "--script", device, "set", "1", "boot", "on"))
        )
        commands.append(_check_command(("partprobe", device)))
        commands.append(_check_command(("udevadm", "settle")))
        for partition in sorted(plan.partitions, key=lambda item: item.number):
            if partition.filesystem != "ext4":
                raise LayoutError("legacy adapter formats ext4 only")
            try:
                node = partition_number_path(target.path, partition.number)
            except DiskProbeError as exc:
                raise LayoutError(str(exc)) from exc
            commands.append(
                _check_command(
                    (
                        "mkfs.ext4",
                        "-F",
                        "-m",
                        "1",
                        "-L",
                        partition.label,
                        str(node),
                    )
                )
            )
        return tuple(commands)


class _DeferredExecutionAdapter(LayoutAdapter):
    """Shared skeleton base: role-model plans validate, execution waits."""

    deferred_phase: str = ""

    def build_commands(
        self, plan: LayoutPlan, target: DeviceObservation
    ) -> tuple[tuple[str, ...], ...]:
        if plan.adapter_id != self.adapter_id:
            raise LayoutError("layout plan does not belong to this adapter")
        raise LayoutError(
            f"adapter {self.adapter_id!r} execution is deferred to "
            f"{self.deferred_phase}; role-model plans only"
        )


class ModernGptAbAdapter(_DeferredExecutionAdapter):
    """GPT A/B role model (setup-media architecture sect. 10).

    BIOS Boot permits deliberate BIOS fallback; ESP owns the signed UEFI
    chain; stable GRUB config/environment stays outside replaceable A/B
    roots. Sizes are provisional role-model facts tightened by on-device
    measurement in Phase 8C, never loosened by guessing.
    """

    deferred_phase = "Phase 8C"

    BIOS_BOOT_BYTES = 1 * MIB
    ESP_BYTES = 128 * MIB
    BOOT_CONTROL_BYTES = 64 * MIB

    @property
    def adapter_id(self) -> str:
        return MODERN_GPT_AB_ADAPTER_ID

    @property
    def label_type(self) -> str:
        return "gpt"

    @property
    def boot_backend(self) -> str:
        return "grub-ab-v1"

    @property
    def expected_roles(self) -> tuple[str, ...]:
        return (
            "bios-boot",
            "esp",
            "boot-control",
            "system-a",
            "system-b",
            "persist",
        )

    def plan(
        self,
        *,
        device_size_bytes: int,
        slot_bytes: int,
        persist_minimum_bytes: int,
    ) -> LayoutPlan:
        _require_mib_multiple(int(slot_bytes), field_name="slot_bytes")
        return LayoutPlan(
            adapter_id=self.adapter_id,
            label_type=self.label_type,
            device_size_bytes=int(device_size_bytes),
            slot_bytes=int(slot_bytes),
            persist_minimum_bytes=int(persist_minimum_bytes),
            boot_backend=self.boot_backend,
            partitions=(
                PlannedPartition(
                    number=1,
                    role="bios-boot",
                    size_bytes=self.BIOS_BOOT_BYTES,
                    filesystem="none",
                    flags=("bios_grub",),
                ),
                PlannedPartition(
                    number=2,
                    role="esp",
                    size_bytes=self.ESP_BYTES,
                    filesystem="fat32",
                    label="GREIA_ESP",
                    flags=("esp",),
                ),
                PlannedPartition(
                    number=3,
                    role="boot-control",
                    size_bytes=self.BOOT_CONTROL_BYTES,
                    filesystem="ext4",
                    label="GREIA_BOOT",
                ),
                PlannedPartition(
                    number=4,
                    role="system-a",
                    size_bytes=int(slot_bytes),
                    filesystem="ext4",
                    label="GREIA_SYS_A",
                ),
                PlannedPartition(
                    number=5,
                    role="system-b",
                    size_bytes=int(slot_bytes),
                    filesystem="ext4",
                    label="GREIA_SYS_B",
                ),
                PlannedPartition(
                    number=6,
                    role="persist",
                    size_bytes=None,
                    filesystem="ext4",
                    label="GREIA_PERSIST",
                ),
            ),
        )


class PiMbrTrybootAbAdapter(_DeferredExecutionAdapter):
    """Pi MBR/tryboot A/B role model (setup-media architecture sect. 11).

    Native firmware A/B semantics: FAT boot-control plus staged BOOT_A/BOOT_B
    beside ext4 system slots and the PERSIST remainder. Number 4 is reserved
    for the extended container (emitted with the execution path in Phase
    8D); logical roles 5-7 validate sequentially against it.
    """

    deferred_phase = "Phase 8D"

    BOOT_BYTES = 64 * MIB

    @property
    def adapter_id(self) -> str:
        return PI_MBR_TRYBOOT_AB_ADAPTER_ID

    @property
    def label_type(self) -> str:
        return "msdos"

    @property
    def boot_backend(self) -> str:
        return "pi-tryboot-ab-v1"

    @property
    def expected_roles(self) -> tuple[str, ...]:
        return (
            "pi-boot-control",
            "pi-boot-a",
            "pi-boot-b",
            "system-a",
            "system-b",
            "persist",
        )

    def plan(
        self,
        *,
        device_size_bytes: int,
        slot_bytes: int,
        persist_minimum_bytes: int,
    ) -> LayoutPlan:
        _require_mib_multiple(int(slot_bytes), field_name="slot_bytes")
        return LayoutPlan(
            adapter_id=self.adapter_id,
            label_type=self.label_type,
            device_size_bytes=int(device_size_bytes),
            slot_bytes=int(slot_bytes),
            persist_minimum_bytes=int(persist_minimum_bytes),
            boot_backend=self.boot_backend,
            partitions=(
                PlannedPartition(
                    number=1,
                    role="pi-boot-control",
                    size_bytes=self.BOOT_BYTES,
                    filesystem="fat32",
                    label="GREIA_PBOOT",
                    flags=("boot",),
                ),
                PlannedPartition(
                    number=2,
                    role="pi-boot-a",
                    size_bytes=self.BOOT_BYTES,
                    filesystem="fat32",
                    label="GREIA_BOOTA",
                ),
                PlannedPartition(
                    number=3,
                    role="pi-boot-b",
                    size_bytes=self.BOOT_BYTES,
                    filesystem="fat32",
                    label="GREIA_BOOTB",
                ),
                PlannedPartition(
                    number=5,
                    role="system-a",
                    size_bytes=int(slot_bytes),
                    filesystem="ext4",
                    label="GREIA_SYS_A",
                ),
                PlannedPartition(
                    number=6,
                    role="system-b",
                    size_bytes=int(slot_bytes),
                    filesystem="ext4",
                    label="GREIA_SYS_B",
                ),
                PlannedPartition(
                    number=7,
                    role="persist",
                    size_bytes=None,
                    filesystem="ext4",
                    label="GREIA_PERSIST",
                ),
            ),
        )


#: Expected semantic role set per canonical adapter id (common validation).
_ADAPTER_ROLES: dict[str, tuple[str, ...]] = {
    LEGACY_BIOS_AB_ADAPTER_ID: ("boot-control", "system-a", "system-b", "persist"),
    MODERN_GPT_AB_ADAPTER_ID: (
        "bios-boot",
        "esp",
        "boot-control",
        "system-a",
        "system-b",
        "persist",
    ),
    PI_MBR_TRYBOOT_AB_ADAPTER_ID: (
        "pi-boot-control",
        "pi-boot-a",
        "pi-boot-b",
        "system-a",
        "system-b",
        "persist",
    ),
}

#: Expected boot backend per canonical adapter id (common validation).
_ADAPTER_BOOT_BACKENDS: dict[str, str] = {
    LEGACY_BIOS_AB_ADAPTER_ID: "grub-ab-v1",
    MODERN_GPT_AB_ADAPTER_ID: "grub-ab-v1",
    PI_MBR_TRYBOOT_AB_ADAPTER_ID: "pi-tryboot-ab-v1",
}


#: Registered adapters keyed by canonical layout-adapter id.
LAYOUT_ADAPTERS: dict[str, LayoutAdapter] = {
    LEGACY_BIOS_AB_ADAPTER_ID: LegacyBiosAbAdapter(),
    MODERN_GPT_AB_ADAPTER_ID: ModernGptAbAdapter(),
    PI_MBR_TRYBOOT_AB_ADAPTER_ID: PiMbrTrybootAbAdapter(),
}


def adapter_for(adapter_id: str) -> LayoutAdapter:
    """Return the registered adapter; unknown ids fail closed (no guessing)."""
    try:
        return LAYOUT_ADAPTERS[adapter_id]
    except (KeyError, TypeError) as exc:
        raise LayoutError(
            "unknown layout adapter "
            f"{adapter_id!r}; expected one of: "
            + ", ".join(sorted(LAYOUT_ADAPTERS))
        ) from exc


# ---------------------------------------------------------------------------
# Phase 8B Step 8B.1 profile seam (X8-LAYOUT): profile-owned sizing,
# finalized-slot capacity gate and fresh layout-authority identities.
# ---------------------------------------------------------------------------


def _require_positive_int(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise LayoutError(f"{field_name} must be a positive integer")
    return value


def _require_nonnegative_int(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LayoutError(f"{field_name} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class ProfileSizing:
    """Profile-owned sizing facts for one install (installer seam).

    Carries exactly the release-profile ``storage``/``updates`` facts the
    layout adapter consumes: the canonical layout-adapter id, the profile
    ``system_slot_bytes`` / ``persistent_minimum_bytes`` and the profile
    ``updates.boot_backend``. Numeric slot/PERSIST bounds stay enforced once
    at :class:`LayoutPlan` construction; this dataclass only proves the
    profile facts are well-typed, adapter-registered and backend-bound, so
    X8-GRUB/X8-INSTALL/X8-UPDATE share one typed entry point instead of
    threading raw profile integers.
    """

    layout_adapter_id: str
    slot_bytes: int
    persist_minimum_bytes: int
    boot_backend: str

    def __post_init__(self) -> None:
        if self.layout_adapter_id not in KNOWN_LAYOUT_ADAPTER_IDS:
            raise LayoutError(
                f"unknown layout adapter: {self.layout_adapter_id!r}"
            )
        _require_positive_int(self.slot_bytes, field_name="profile slot_bytes")
        _require_positive_int(
            self.persist_minimum_bytes, field_name="profile persist_minimum_bytes"
        )
        if not isinstance(self.boot_backend, str) or not self.boot_backend:
            raise LayoutError("profile boot_backend must be non-empty text")
        expected_backend = _ADAPTER_BOOT_BACKENDS.get(self.layout_adapter_id)
        if expected_backend is not None and self.boot_backend != expected_backend:
            raise LayoutError("profile boot_backend does not match the layout adapter")


def plan_for_profile(
    sizing: ProfileSizing, *, device_size_bytes: int
) -> LayoutPlan:
    """Return the validated declarative plan for profile-owned sizes.

    Sizes come only from the profile ``sizing`` facts; ``device_size_bytes``
    is the verified target capacity the plan is proven against. Unknown
    adapters and backend mismatches fail closed with no commands issued.
    """
    if not isinstance(sizing, ProfileSizing):
        raise LayoutError("layout planning requires profile-owned sizing facts")
    capacity = _require_positive_int(
        device_size_bytes, field_name="device_size_bytes"
    )
    adapter = adapter_for(sizing.layout_adapter_id)
    if sizing.boot_backend != adapter.boot_backend:
        raise LayoutError("profile boot_backend does not match the layout adapter")
    return adapter.plan(
        device_size_bytes=capacity,
        slot_bytes=int(sizing.slot_bytes),
        persist_minimum_bytes=int(sizing.persist_minimum_bytes),
    )


def require_finalized_slot_capacity(
    *,
    slot_bytes: int,
    base_bytes: int,
    minimum_slot_bytes: int,
    support_installed_bytes: int,
    growth_bytes: int = FINALIZATION_GROWTH_BYTES,
    metadata_reserve_bytes: int = SLOT_METADATA_RESERVE_BYTES,
) -> int:
    """Reject an undersized profile slot with the finalizer capacity bound.

    Proves ``max(base bytes, manifest minimum) + support-set installed-size
    bound + boot-artifact growth bound + metadata/reserve <= slot capacity``
    — the same bound :class:`greia_platform.slot_writer.SlotWriter` enforces
    at write time and :class:`greia_platform.slot_writer.SlotFinalizer`
    re-checks at finalization, applied here at install-plan time so an
    undersized profile fails before any destructive command runs. Growth and
    reserve defaults are the platform-owned bounds (imported, never copied);
    callers pass release-measured facts for the rest. Returns the required
    bytes so callers and tests can assert headroom explicitly.
    """
    capacity = _require_positive_int(slot_bytes, field_name="profile slot_bytes")
    base = _require_positive_int(base_bytes, field_name="release base_bytes")
    minimum = _require_positive_int(
        minimum_slot_bytes, field_name="release minimum_slot_bytes"
    )
    support = _require_nonnegative_int(
        support_installed_bytes, field_name="support installed-size bound"
    )
    growth = _require_nonnegative_int(
        growth_bytes, field_name="boot-artifact growth bound"
    )
    reserve = _require_nonnegative_int(
        metadata_reserve_bytes, field_name="metadata/reserve bound"
    )
    required = max(base, minimum) + support + growth + reserve
    if required > capacity:
        raise LayoutError(
            "profile slot_bytes is below the finalized-slot capacity bound: "
            f"required {required} bytes exceeds slot capacity {capacity} bytes"
        )
    return required


#: Layout-authority roles minted fresh at install time. ``boot-control`` is
#: deliberately absent: it owns stable GRUB configuration/environment outside
#: both replaceable A/B roots and is never rewritten by slot updates, so it
#: carries no layout-record identity; the record tracks exactly the
#: ``system-a`` / ``system-b`` / ``persist`` roles (see
#: ``greia_platform.persistent_layout.PARTITION_ROLES``). Its filesystem UUID
#: is still never cloned: the adapter formats it with a fresh ``mkfs`` UUID.
FRESH_IDENTITY_ROLES = ("system-a", "system-b", "persist")


def _fresh_uuid_text(uuid_factory: Callable[[], uuid.UUID], *, field_name: str) -> str:
    try:
        candidate = uuid_factory()
    except Exception as exc:
        raise LayoutError(
            "layout identity generator is outside Greia bounds"
        ) from exc
    try:
        parsed = uuid.UUID(str(candidate))
    except (ValueError, AttributeError) as exc:
        raise LayoutError(
            f"layout identity {field_name} is not a valid UUID"
        ) from exc
    text = str(parsed)
    if text != text.lower():
        raise LayoutError(
            f"layout identity {field_name} must be canonical lowercase UUID text"
        )
    return text


def mint_fresh_partition_identities(
    *, uuid_factory: Callable[[], uuid.UUID] = uuid.uuid4
) -> dict[str, dict[str, str]]:
    """Mint fresh distinct PARTUUID/filesystem-UUID pairs for layout authority.

    Returns one ``{"partuuid", "filesystem_uuid"}`` mapping per record-tracked
    role (``system-a``, ``system-b``, ``persist``) in the exact shape
    :class:`greia_platform.persistent_layout.PartitionIdentity` consumes.
    Every UUID comes from the factory (never from a release-builder template
    or a cloned peer), all six are proven distinct, and any factory failure
    or collision fails closed. X8-INSTALL threads these into the fresh
    ``InstalledLayoutRecord`` (via ``FreshPersistSpec``) and the slot
    destinations whose finalizer restores exactly the role UUIDs.
    """
    minted: dict[str, dict[str, str]] = {}
    for role in FRESH_IDENTITY_ROLES:
        minted[role] = {
            "partuuid": _fresh_uuid_text(
                uuid_factory, field_name=f"{role}.partuuid"
            ),
            "filesystem_uuid": _fresh_uuid_text(
                uuid_factory, field_name=f"{role}.filesystem_uuid"
            ),
        }
    seen = [
        minted[role][key]
        for role in FRESH_IDENTITY_ROLES
        for key in ("partuuid", "filesystem_uuid")
    ]
    if len(set(seen)) != len(seen):
        raise LayoutError(
            "fresh layout partition identities must be unique across roles"
        )
    return minted


__all__ = [
    "MIB",
    "PARTITION_ALIGNMENT_BYTES",
    "LABEL_RESERVED_BYTES",
    "ALLOWED_FILESYSTEMS",
    "ALLOWED_FLAGS",
    "KNOWN_LAYOUT_ADAPTER_IDS",
    "FRESH_IDENTITY_ROLES",
    "LAYOUT_ADAPTERS",
    "LEGACY_BIOS_AB_ADAPTER_ID",
    "MODERN_GPT_AB_ADAPTER_ID",
    "PI_MBR_TRYBOOT_AB_ADAPTER_ID",
    "LayoutAdapter",
    "LayoutError",
    "LayoutPlan",
    "LegacyBiosAbAdapter",
    "ModernGptAbAdapter",
    "PartitionCommandRunner",
    "PiMbrTrybootAbAdapter",
    "PlannedPartition",
    "ProfileSizing",
    "adapter_for",
    "mint_fresh_partition_identities",
    "plan_for_profile",
    "require_finalized_slot_capacity",
    "validate_layout_plan",
]
