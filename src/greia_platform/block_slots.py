"""Shared production block-device/filesystem primitives for slot staging.

Single production owner of the block/filesystem seam consumed by both the
installer (P2) and the updater (P3). Resolves a trusted layout-role identity
to its actual partition device and provides real block-backed
``SlotStorage``, ``SlotFilesystem`` and ``SlotPackageInstaller``
implementations behind the existing ``greia_platform.slot_writer`` protocols.

Ownership boundaries::

    InstalledLayoutRecord (persistent_layout, trusted authority)
        -> resolve_slot_device (here: fresh topology + udev PARTUUID map
           + device-node identity probe, active/accepted/single-root refusal)
        -> BlockSlotStorage (bounded offset IO over the resolved node)
        -> BlockSlotFilesystem (role UUID binding, expansion, mount/unmount,
           bounded file writes, health, sync)
        -> SharedSlotPackageInstaller (reuses InstallerSlotPackageInstaller /
           TargetHardwareSupportInstaller, no copied package logic)
        -> SlotWriter / SlotFinalizer (slot_writer, shared staging order)

``LoopbackSlotFile`` in ``slot_writer`` stays the R0 loopback stand-in for
tests; this module is the production device path. No second writer or
finalizer is created here.

``boot-control`` carries no layout-record identity (per installer
``FRESH_IDENTITY_ROLES``: only ``system-a``/``system-b``/``persist`` are
record-tracked) and is never bound or cloned by this module: resolution
accepts only the ``system-a``/``system-b`` roles and filesystem binding
requires the destination role's own recorded UUID.

All external commands run with argument arrays and ``shell=False``; no
shell strings, request bytes or raw caller paths cross the construction
surface (:class:`SharedBlockSlotPrimitives`).
"""

from __future__ import annotations

import os
import re
import stat as _stat
import subprocess
import uuid as _uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol, Sequence


class BlockSlotError(RuntimeError):
    """Shared block-primitive resolution, storage or filesystem failure."""


_DEVICE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-+]*$")
_MAX_DEVICE_NAME_BYTES = 64
#: Upper bound for one slot-local file write through the block filesystem.
MAX_SLOT_FILE_BYTES = 8 * 1024 * 1024
#: Upper bound for a slot-local relative path (mirrors slot_writer's 256).
MAX_SLOT_REL_PATH_BYTES = 256

#: Roles this module may resolve. ``boot-control`` is deliberately absent:
#: it owns stable boot configuration outside both replaceable A/B roots and
#: carries no layout-record identity.
RESOLVABLE_SLOT_ROLES = ("system-a", "system-b")
SEMANTIC_TO_ROLE = {"A": "system-a", "B": "system-b"}


def _require_canonical_uuid(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise BlockSlotError(f"{field_name} must be text")
    try:
        parsed = _uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise BlockSlotError(f"{field_name} is not a valid UUID") from exc
    if str(parsed) != value.lower():
        raise BlockSlotError(f"{field_name} must be canonical lowercase UUID text")
    return str(parsed)


def _require_device_name(name: object) -> str:
    if not isinstance(name, str) or not name:
        raise BlockSlotError("PARTUUID map carries an empty device name")
    if len(name.encode("utf-8")) > _MAX_DEVICE_NAME_BYTES:
        raise BlockSlotError("PARTUUID map device name is too long")
    if "/" in name or name in (".", "..") or ".." in name.split("/"):
        raise BlockSlotError("PARTUUID map device name escapes its form")
    if not _DEVICE_NAME_RE.fullmatch(name):
        raise BlockSlotError(f"PARTUUID map device name is not a kernel name: {name!r}")
    return name


def _require_relative_path(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or "*" in value
    ):
        raise BlockSlotError("slot file path is not a bounded relative path")
    normalized = os.path.normpath(value)
    if normalized != value or value.startswith("..") or "/../" in value:
        raise BlockSlotError(f"slot file path escapes its canonical form: {value}")
    if len(value.encode("utf-8")) > MAX_SLOT_REL_PATH_BYTES:
        raise BlockSlotError("slot file path is too long")
    return value


# ---------------------------------------------------------------------------
# Resolution result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ResolvedSlotDevice:
    """A layout role authoritatively bound to its partition device node."""

    semantic_slot: str
    role: str
    device_node: Path
    partuuid: str
    filesystem_uuid: str
    capacity_bytes: int
    disk_id: str
    layout_id: str


# ---------------------------------------------------------------------------
# Injected observation seams (fresh at every call)
# ---------------------------------------------------------------------------


class TopologyObserver(Protocol):
    """Fresh block-topology observation (called at every resolution)."""

    def __call__(self) -> object: ...


class PartuuidMapReader(Protocol):
    """Fresh udev PARTUUID -> kernel device name map."""

    def __call__(self) -> dict[str, str]: ...


class DevicePartuuidProber(Protocol):
    """Identity probe of one device node (blkid PARTUUID)."""

    def __call__(self, device: Path) -> str: ...


def default_partuuid_map_reader(
    by_partuuid_dir: Path = Path("/dev/disk/by-partuuid"),
) -> dict[str, str]:
    """Production udev map reader behind the injectable seam."""
    from .persistent_layout import read_partuuid_map

    return read_partuuid_map(by_partuuid_dir)


def blkid_device_partuuid(device: Path, *, timeout_seconds: float = 10.0) -> str:
    """Probe one device node's PARTUUID via blkid (argument array, no shell)."""
    completed = subprocess.run(
        ["blkid", "-s", "PARTUUID", "-o", "value", "--", str(device)],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        shell=False,
    )
    if completed.returncode != 0:
        raise BlockSlotError(
            f"device PARTUUID probe failed for {device}: "
            f"{completed.stderr.strip() or 'blkid failed'}"
        )
    text = completed.stdout.strip().splitlines()
    if len(text) != 1 or not text[0].strip():
        raise BlockSlotError(f"device PARTUUID probe is ambiguous for {device}")
    # Normalization (GPT/MBR scheme) is owned by persistent_layout; accept the
    # raw probe text here and let the equality check against the trusted
    # normalized PARTUUID decide (callers normalize the trusted side).
    return text[0].strip()


def resolve_slot_device(
    *,
    record: object,
    semantic_slot: str,
    observe_topology: Callable[[], object],
    read_partuuid_map: Callable[[], dict[str, str]],
    probe_device_partuuid: Callable[[Path], str],
    dev_root: Path = Path("/dev"),
) -> ResolvedSlotDevice:
    """Resolve a semantic slot to its partition device node (fail closed).

    Every input is re-observed at call time: ``observe_topology`` and
    ``read_partuuid_map`` are invoked inside this call, so a stale
    pre-captured topology can never satisfy resolution. The trusted role
    PARTUUID from ``InstalledLayoutRecord`` is resolved through the fresh
    udev map, the fresh topology is validated against the record (same
    installed disk/layout, capacity, no swap/ambiguity), and the resolved
    node is probed back (PARTUUID equality) to refuse symlink/device
    substitution and wrong-disk identity. The active slot, the accepted
    slot and single-root layouts are refused via ``DestinationSlot``.
    """
    from .persistent_layout import validate_layout_against_topology
    from .slot_writer import DestinationSlot, SlotWriteError

    if semantic_slot not in ("A", "B"):
        raise BlockSlotError("destination semantic slot must be A or B")
    try:
        destination = DestinationSlot.resolve_from_layout(record, semantic_slot)  # type: ignore[arg-type]
    except SlotWriteError as exc:
        raise BlockSlotError(str(exc)) from exc

    role = SEMANTIC_TO_ROLE[semantic_slot]
    if role not in RESOLVABLE_SLOT_ROLES:
        raise BlockSlotError(f"role is outside the resolvable slot set: {role}")
    identity = (
        record.system_a if semantic_slot == "A" else record.system_b  # type: ignore[union-attr]
    )
    if identity is None:
        raise BlockSlotError("single-root layouts carry no writable A/B slot")
    trusted_partuuid: str = identity.partuuid
    trusted_fs_uuid: str = identity.filesystem_uuid

    # Fresh observation at call time: never accept a caller-cached topology.
    try:
        topology = observe_topology()
    except BlockSlotError:
        raise
    except Exception as exc:
        raise BlockSlotError(f"block topology observation failed: {exc}") from exc
    try:
        validate_layout_against_topology(record, topology)  # type: ignore[arg-type]
    except Exception as exc:
        raise BlockSlotError(str(exc)) from exc

    try:
        mapping = read_partuuid_map()
    except BlockSlotError:
        raise
    except Exception as exc:
        raise BlockSlotError(f"PARTUUID map read failed: {exc}") from exc
    if not isinstance(mapping, dict) or not mapping:
        raise BlockSlotError("PARTUUID map holds no identities")
    # Ambiguous map: two PARTUUIDs claiming the same kernel node.
    seen_nodes = list(mapping.values())
    if len(set(seen_nodes)) != len(seen_nodes):
        raise BlockSlotError("PARTUUID map is ambiguous: two identities share one device")
    if trusted_partuuid not in mapping:
        raise BlockSlotError("trusted role PARTUUID is absent from the PARTUUID map")
    kernel_name = _require_device_name(mapping[trusted_partuuid])

    node = Path(dev_root) / kernel_name
    _require_device_node(node, capacity_bytes=destination.slot_capacity_bytes)

    try:
        observed_partuuid = probe_device_partuuid(node)
    except BlockSlotError:
        raise
    except Exception as exc:
        raise BlockSlotError(f"device PARTUUID probe failed: {exc}") from exc
    # Compare through the layout normalizer so MBR spellings
    # (``-2`` vs ``-02``, case) agree with the trusted normalized form.
    if _normalize_partuuid_best_effort(observed_partuuid) != trusted_partuuid:
        raise BlockSlotError(
            "device node identity does not match the trusted role PARTUUID: "
            "refusing a substituted/wrong-disk device"
        )

    fact = topology.by_role(role)  # type: ignore[union-attr]
    if fact is None:
        raise BlockSlotError(f"fresh topology carries no fact for role: {role}")
    if fact.partuuid != trusted_partuuid:  # pragma: no cover - validated above
        raise BlockSlotError("fresh topology role PARTUUID drifted from the record")
    return ResolvedSlotDevice(
        semantic_slot=semantic_slot,
        role=role,
        device_node=node,
        partuuid=trusted_partuuid,
        filesystem_uuid=trusted_fs_uuid,
        capacity_bytes=destination.slot_capacity_bytes,
        disk_id=fact.disk_id,
        layout_id=record.layout_id,  # type: ignore[union-attr]
    )


def _normalize_partuuid_best_effort(value: str) -> str:
    """Normalize a probed PARTUUID with the layout-owned parser when possible."""
    try:
        from .persistent_layout import (
            PARTITION_SCHEME_MBR_PARTUUID,
            infer_partuuid_scheme,
            normalize_partuuid_for_scheme,
        )

        scheme = infer_partuuid_scheme(value)
        normalized = normalize_partuuid_for_scheme(scheme, value, field="partuuid")
        # MBR spellings normalize to ``<sig>-<NN>``; GPT to canonical UUID.
        if scheme == PARTITION_SCHEME_MBR_PARTUUID:
            return normalized
        return normalized.lower()
    except Exception:
        return value.strip()


def _require_device_node(node: Path, *, capacity_bytes: int) -> None:
    """Refuse symlink substitution and prove the node is a device/file peer."""
    if not isinstance(node, Path):
        raise BlockSlotError("slot device node must be a path")
    try:
        if os.path.islink(node):
            raise BlockSlotError("slot device node may not be a symbolic link")
        status = node.stat()
    except OSError as exc:
        raise BlockSlotError(f"slot device node is not accessible: {exc}") from exc
    if _stat.S_ISLNK(status.st_mode):
        raise BlockSlotError("slot device node may not be a symbolic link")
    if _stat.S_ISDIR(status.st_mode):
        raise BlockSlotError("slot device node must not be a directory")
    is_regular = _stat.S_ISREG(status.st_mode)
    is_block = _stat.S_ISBLK(status.st_mode)
    if not (is_regular or is_block):
        raise BlockSlotError("slot device node must be a block device or regular file")
    if not isinstance(capacity_bytes, int) or capacity_bytes <= 0:
        raise BlockSlotError("slot capacity is outside Greia bounds")
    if is_regular and status.st_size != capacity_bytes:
        raise BlockSlotError("slot device size does not match the layout slot")


# ---------------------------------------------------------------------------
# Production block SlotStorage
# ---------------------------------------------------------------------------


class BlockSlotStorage:
    """Block-device (or regular-file stand-in) bounded byte store.

    Satisfies the ``SlotStorage`` protocol over the resolved partition node.
    Regular files stand in for devices in zero-device tests (size must equal
    the layout capacity); production block devices skip the size gate and
    rely on the topology capacity proof instead.
    """

    def __init__(self, node: Path, capacity_bytes: int) -> None:
        location = Path(node)
        _require_device_node(location, capacity_bytes=capacity_bytes)
        self._path = location
        self._capacity = capacity_bytes
        try:
            self._handle = location.open("r+b")
        except OSError as exc:
            raise BlockSlotError(f"slot device is not writable: {exc}") from exc
        self._closed = False

    @property
    def capacity_bytes(self) -> int:
        return self._capacity

    @property
    def device_node(self) -> Path:
        return self._path

    def _require_open(self) -> None:
        if self._closed:
            raise BlockSlotError("slot store is closed")

    def write_at(self, offset: int, data: bytes) -> None:
        self._require_open()
        if (
            isinstance(offset, bool)
            or not isinstance(offset, int)
            or offset < 0
            or offset + len(data) > self._capacity
        ):
            raise BlockSlotError("slot store write is outside the slot range")
        if not isinstance(data, (bytes, bytearray)) or not data:
            raise BlockSlotError("slot store write must carry bytes")
        self._handle.seek(offset)
        self._handle.write(bytes(data))

    def read_at(self, offset: int, length: int) -> bytes:
        self._require_open()
        if (
            isinstance(offset, bool)
            or not isinstance(offset, int)
            or isinstance(length, bool)
            or not isinstance(length, int)
            or offset < 0
            or length <= 0
            or offset + length > self._capacity
        ):
            raise BlockSlotError("slot store read is outside the slot range")
        self._handle.seek(offset)
        data = self._handle.read(length)
        if len(data) != length:
            raise BlockSlotError("slot store read is short")
        return data

    def flush(self) -> None:
        self._require_open()
        self._handle.flush()
        os.fsync(self._handle.fileno())

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._handle.close()

    def __enter__(self) -> "BlockSlotStorage":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Filesystem runner seam + production block SlotFilesystem
# ---------------------------------------------------------------------------


class BlockFilesystemRunner(Protocol):
    """Privileged filesystem operations behind an injectable seam."""

    def blkid_uuid(self, device: Path) -> str: ...
    def set_uuid(self, device: Path, filesystem_uuid: str) -> None: ...
    def check(self, device: Path) -> None: ...
    def expand(self, device: Path) -> None: ...
    def mount(self, device: Path, mountpoint: Path) -> None: ...
    def unmount(self, mountpoint: Path) -> None: ...
    def sync(self) -> None: ...


@dataclass(frozen=True, slots=True)
class SubprocessBlockFilesystemRunner:
    """Production runner: blkid/tune2fs/e2fsck/resize2fs/mount (no shell)."""

    timeout_seconds: float = 120.0

    def _run(self, command: Sequence[str]) -> str:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            shell=False,
        )
        if completed.returncode != 0:
            detail = (
                completed.stderr.strip()
                or completed.stdout.strip()
                or "command failed"
            )[:200]
            raise BlockSlotError(
                f"filesystem command failed ({' '.join(list(command)[:3])}): "
                f"{detail}"
            )
        return completed.stdout

    def blkid_uuid(self, device: Path) -> str:
        out = self._run(["blkid", "-s", "UUID", "-o", "value", "--", str(device)])
        lines = [line.strip() for line in out.strip().splitlines() if line.strip()]
        if len(lines) != 1:
            raise BlockSlotError(f"filesystem UUID probe is ambiguous for {device}")
        return _require_canonical_uuid(lines[0], field_name="filesystem UUID")

    def set_uuid(self, device: Path, filesystem_uuid: str) -> None:
        expected = _require_canonical_uuid(filesystem_uuid, field_name="filesystem UUID")
        self._run(["tune2fs", "-U", expected, "--", str(device)])

    def check(self, device: Path) -> None:
        self._run(["e2fsck", "-f", "-y", "--", str(device)])

    def expand(self, device: Path) -> None:
        self._run(["resize2fs", "--", str(device)])

    def mount(self, device: Path, mountpoint: Path) -> None:
        self._run(["mount", "--", str(device), str(mountpoint)])

    def unmount(self, mountpoint: Path) -> None:
        self._run(["umount", "--", str(mountpoint)])

    def sync(self) -> None:
        try:
            os.sync()
        except OSError as exc:
            raise BlockSlotError(f"filesystem sync failed: {exc}") from exc


class BlockSlotFilesystem:
    """Production filesystem seam for one resolved destination slot.

    Owns only the destination device: binds its role filesystem UUID
    (never cloned from a template, never the boot-control identity),
    expands it, mounts it, proves slot completeness, performs bounded
    file writes, checks health, then unmounts and syncs. The
    active/accepted slot is never addressable here because construction
    requires a :class:`ResolvedSlotDevice` that already refused live
    slots.
    """

    def __init__(
        self,
        resolved: ResolvedSlotDevice,
        runner: BlockFilesystemRunner,
        mount_root: Path,
    ) -> None:
        if not isinstance(resolved, ResolvedSlotDevice):
            raise BlockSlotError("slot filesystem requires a resolved slot device")
        if resolved.role not in RESOLVABLE_SLOT_ROLES:
            raise BlockSlotError("slot filesystem refuses a non-slot role")
        _require_canonical_uuid(resolved.filesystem_uuid, field_name="role filesystem UUID")
        root = Path(mount_root)
        if str(root) in ("", "."):
            raise BlockSlotError("slot mount root is outside Greia bounds")
        self._resolved = resolved
        self._runner = runner
        self._mount_root = root
        self._mountpoint: Path | None = None

    @property
    def resolved(self) -> ResolvedSlotDevice:
        return self._resolved

    def bind_filesystem_uuid(self, filesystem_uuid: str) -> None:
        expected = _require_canonical_uuid(filesystem_uuid, field_name="filesystem UUID")
        if expected != self._resolved.filesystem_uuid:
            raise BlockSlotError(
                "filesystem UUID binding does not match the resolved role UUID: "
                "refusing a cloned/template identity"
            )
        try:
            self._runner.set_uuid(self._resolved.device_node, expected)
        except BlockSlotError:
            raise
        except Exception as exc:
            raise BlockSlotError(f"filesystem UUID binding failed: {exc}") from exc

    def expand_to_capacity(self) -> None:
        try:
            self._runner.check(self._resolved.device_node)
            self._runner.expand(self._resolved.device_node)
        except BlockSlotError:
            raise
        except Exception as exc:
            raise BlockSlotError(f"filesystem expansion failed: {exc}") from exc

    def mount(self) -> Path:
        if self._mountpoint is not None:
            raise BlockSlotError("slot is already mounted")
        mountpoint = self._mount_root / (
            f"slot-{self._resolved.semantic_slot.lower()}-{os.getpid()}"
        )
        try:
            if os.path.islink(mountpoint):
                raise BlockSlotError("slot mountpoint may not be a symbolic link")
            mountpoint.mkdir(parents=True, exist_ok=True)
            if os.path.islink(mountpoint):
                raise BlockSlotError("slot mountpoint may not be a symbolic link")
            os.chmod(mountpoint, 0o700)
        except OSError as exc:
            raise BlockSlotError(f"slot mountpoint is not usable: {exc}") from exc
        try:
            self._runner.mount(self._resolved.device_node, mountpoint)
        except BlockSlotError:
            raise
        except Exception as exc:
            raise BlockSlotError(f"slot mount failed: {exc}") from exc
        self._mountpoint = mountpoint
        return mountpoint

    def unmount(self) -> None:
        if self._mountpoint is None:
            raise BlockSlotError("slot is not mounted")
        mountpoint = self._mountpoint
        try:
            self._runner.unmount(mountpoint)
        except BlockSlotError:
            raise
        except Exception as exc:
            raise BlockSlotError(f"slot unmount failed: {exc}") from exc
        finally:
            self._mountpoint = None

    def sync(self) -> None:
        try:
            self._runner.sync()
        except BlockSlotError:
            raise
        except Exception as exc:
            raise BlockSlotError(f"filesystem sync failed: {exc}") from exc

    def _require_mounted(self) -> Path:
        if self._mountpoint is None:
            raise BlockSlotError("slot writes require a mounted destination")
        return self._mountpoint

    def write_file(self, relative_path: str, data: bytes) -> None:
        mountpoint = self._require_mounted()
        rel = _require_relative_path(relative_path)
        if not isinstance(data, (bytes, bytearray)):
            raise BlockSlotError("slot file write must carry bytes")
        if not 1 <= len(data) <= MAX_SLOT_FILE_BYTES:
            raise BlockSlotError("slot file write is outside Greia bounds")
        target = mountpoint / rel
        if os.path.islink(target):
            raise BlockSlotError("slot file target may not be a symbolic link")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if os.path.islink(target.parent):
                raise BlockSlotError("slot file parent may not be a symbolic link")
            with target.open("wb") as handle:
                handle.write(bytes(data))
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(target, 0o600)
        except OSError as exc:
            raise BlockSlotError(f"slot file write failed: {exc}") from exc

    def link_file(
        self, source_relative_path: str, target_relative_path: str
    ) -> None:
        """Publish a same-filesystem hardlink for a large boot artifact.

        Boot kernels/initramfs images exceed the metadata ``write_file``
        bound; linking them keeps the slot capacity cost at zero while the
        GRUB-owned stable alias exists.  Both paths stay slot-relative and
        never follow a symlink.
        """

        mountpoint = self._require_mounted()
        source_rel = _require_relative_path(source_relative_path)
        target_rel = _require_relative_path(target_relative_path)
        source = mountpoint / source_rel
        target = mountpoint / target_rel
        if os.path.islink(source) or not source.is_file():
            raise BlockSlotError("slot link source must be a regular file")
        if os.path.islink(target) or target.exists():
            raise BlockSlotError("slot link target already exists")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if os.path.islink(target.parent):
                raise BlockSlotError("slot link parent may not be a symbolic link")
            os.link(source, target, follow_symlinks=False)
        except OSError as exc:
            raise BlockSlotError(f"slot file link failed: {exc}") from exc

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]:
        mountpoint = self._require_mounted()
        missing: list[str] = []
        for name in required:
            rel = _require_relative_path(name)
            if not (mountpoint / rel).is_file() or os.path.islink(mountpoint / rel):
                missing.append(name)
        return tuple(missing)

    def check_completeness(self) -> None:
        """Mounted completeness smoke: real Greia userspace incl. apt/dpkg.

        Single shared implementation via
        ``greia_platform.slot_writer.check_slot_completeness`` on the
        mounted slot root — the same validator the shared
        ``SlotFinalizer`` and the build-time producer call. Bounded to
        the documented required-path set; no traversal, no hashing.
        """
        mountpoint = self._require_mounted()
        try:
            from .slot_writer import check_slot_completeness
        except Exception as exc:
            raise BlockSlotError(
                f"slot completeness validator is unavailable: {exc}"
            ) from exc
        try:
            check_slot_completeness(mountpoint)
        except BlockSlotError:
            raise
        except Exception as exc:
            raise BlockSlotError(str(exc)) from exc

    def check_health(self) -> None:
        """Mounted health gate: node-substitution + UUID binding re-proof.

        Only mount-safe probes run here (``blkid`` is valid on a mounted
        filesystem). The full ``e2fsck`` consistency check belongs to
        :meth:`expand_to_capacity`, which runs pre-mount while the device
        is unmounted — ``e2fsck`` on a mounted filesystem aborts by
        design, so it must never run in this path.
        """
        mountpoint = self._require_mounted()
        _ = mountpoint
        if os.path.islink(self._resolved.device_node):
            raise BlockSlotError("slot device node was substituted while mounted")
        try:
            observed = self._runner.blkid_uuid(self._resolved.device_node)
        except BlockSlotError:
            raise
        except Exception as exc:
            raise BlockSlotError(f"slot health check failed: {exc}") from exc
        if observed != self._resolved.filesystem_uuid:
            raise BlockSlotError(
                "slot filesystem UUID drifted from the resolved role UUID"
            )


# ---------------------------------------------------------------------------
# Production SlotPackageInstaller reusing the installer support path
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SharedSlotPackageInstaller:
    """Shared-protocol installer delegating to the existing installer path.

    No package logic is copied here: every install routes through
    ``InstallerSlotPackageInstaller``/``TargetHardwareSupportInstaller``
    with the already-verified pool. ``target_root`` is the mounted
    destination slot mountpoint owned by :class:`BlockSlotFilesystem`.
    """

    runner: object
    target_root: Path
    pool: object
    mounted: list[Path] = field(default_factory=list)

    def install(
        self,
        firmware: tuple[str, ...],
        microcode: tuple[str, ...],
    ) -> tuple[object, ...]:
        from greia_installer.slots import InstallerSlotPackageInstaller

        adapter = InstallerSlotPackageInstaller(
            runner=self.runner,  # type: ignore[arg-type]
            target_root=Path(self.target_root),
            pool=self.pool,  # type: ignore[arg-type]
            mounted=self.mounted,
        )
        return adapter.install(tuple(firmware), tuple(microcode))  # type: ignore[return-value]


def pool_to_release_support_set(
    pool: object, *, support_digest: str, support_size: int
) -> object:
    """Convert an already-verified pool without copying package logic."""
    from greia_installer.slots import pool_to_support_set

    return pool_to_support_set(
        pool,  # type: ignore[arg-type]
        support_digest=support_digest,
        support_size=support_size,
    )


# ---------------------------------------------------------------------------
# Narrow typed construction surface for P2/P3 seam factories
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SharedBlockSlotPrimitives:
    """One typed bundle the installer/updater seam factories consume.

    Holds only the trusted record plus injected observation seams, the
    device root, the filesystem runner/mount root and the package-command
    runner. No service knowledge, request bytes or raw caller paths live
    here; callers supply the semantic slot (and, for package install, the
    verified pool plus the mounted target) as typed values.
    """

    record: object
    observe_topology: Callable[[], object]
    read_partuuid_map: Callable[[], dict[str, str]]
    probe_device_partuuid: Callable[[Path], str]
    dev_root: Path = Path("/dev")
    filesystem_runner: BlockFilesystemRunner | None = None
    mount_root: Path = Path("/run/greia-slots")
    package_runner: object | None = None

    def resolve(self, semantic_slot: str) -> ResolvedSlotDevice:
        """Freshly resolve one semantic slot (re-observes at call time)."""
        return resolve_slot_device(
            record=self.record,
            semantic_slot=semantic_slot,
            observe_topology=self.observe_topology,  # type: ignore[arg-type]
            read_partuuid_map=self.read_partuuid_map,
            probe_device_partuuid=self.probe_device_partuuid,
            dev_root=Path(self.dev_root),
        )

    def open_storage(self, resolved: ResolvedSlotDevice) -> BlockSlotStorage:
        """Open bounded block IO over a resolved device."""
        if resolved.layout_id != getattr(self.record, "layout_id"):
            raise BlockSlotError("resolved device does not belong to this record")
        return BlockSlotStorage(resolved.device_node, resolved.capacity_bytes)

    def open_filesystem(self, resolved: ResolvedSlotDevice) -> BlockSlotFilesystem:
        """Open the filesystem seam for a resolved device."""
        if self.filesystem_runner is None:
            raise BlockSlotError("block primitives carry no filesystem runner")
        if resolved.layout_id != getattr(self.record, "layout_id"):
            raise BlockSlotError("resolved device does not belong to this record")
        return BlockSlotFilesystem(resolved, self.filesystem_runner, Path(self.mount_root))

    def make_package_installer(
        self,
        *,
        target_root: Path,
        pool: object,
        mounted: list[Path] | None = None,
    ) -> SharedSlotPackageInstaller:
        """Build the reusing package installer for one mounted slot."""
        if self.package_runner is None:
            raise BlockSlotError("block primitives carry no package runner")
        return SharedSlotPackageInstaller(
            runner=self.package_runner,
            target_root=Path(target_root),
            pool=pool,
            mounted=mounted if mounted is not None else [],
        )


__all__ = [
    "BlockSlotError",
    "BlockSlotStorage",
    "BlockSlotFilesystem",
    "BlockFilesystemRunner",
    "SubprocessBlockFilesystemRunner",
    "SharedSlotPackageInstaller",
    "SharedBlockSlotPrimitives",
    "ResolvedSlotDevice",
    "RESOLVABLE_SLOT_ROLES",
    "MAX_SLOT_FILE_BYTES",
    "blkid_device_partuuid",
    "default_partuuid_map_reader",
    "pool_to_release_support_set",
    "resolve_slot_device",
]
