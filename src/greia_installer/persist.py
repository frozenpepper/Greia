"""PERSIST creation/mount orchestration and recovery routing (A8-PERSIST).

Phase 8A Step 8A.2: fresh-install PERSIST creation/mount/exactly-once
initialization plus existing-install mount-and-open with fail-to-recovery
semantics, on loop/disposable media.

What this module owns (and what it does not):

- Fresh path: derive the persist partition node from the verified
  :class:`~greia_installer.disk.DeviceObservation` plus the validated
  :class:`~greia_installer.layout.LayoutPlan` persist role, adopt exactly
  once when the node already carries the adapter-created filesystem whose
  UUID equals the intended (observed) identity — skipping the redundant
  ``mkfs`` — refuse when a different/unexpected filesystem already exists
  there (exactly-once pre-check *before* any destructive command),
  otherwise create the filesystem with the intended identity, prove the
  identity back with ``blkid`` before trusting it,
  mount it at the caller-provided staging mountpoint, run the platform
  exactly-once initialization (layout authority record, versioned namespace
  schema, state contract) plus the orchestration-owned transaction root,
  then unmount. Any failure after ``mkfs`` fails closed: the staging mount
  is detached best-effort and :class:`PersistError` propagates; a partial
  filesystem is never presented as initialized, and the ``blkid`` pre-check
  refuses silent re-initialization over it (operator must repartition via
  A8-LAYOUT).
- Existing path: mount the persist node (read-only verification mount),
  open it through :func:`greia_platform.persistent_layout.open_existing_persist`
  plus the transaction-root presence gate, and route *every* failure
  (mount failure, missing/corrupt record, topology mismatch, swapped
  slots, wrong UUID, symlink, missing namespace/contract/transaction
  root) to :class:`PersistRecoveryRequired`. This path never mints a new
  identity and never calls fresh initialization.
- Slot presentation: materialize the required canonical bind targets from
  the namespace map as directories inside a fresh SYSTEM_A slot root so
  early boot has bind destinations. Boot-time mount policy itself belongs
  to the Phase 8B boot adapter, not this step.

No arbitrary shell/path authority:

- every block command is an argument array run with ``shell=False`` by the
  caller's runner; this module never builds a shell string;
- the persist node is derived only from the verified observation plus the
  adapter-declared persist partition number (never from UI/Parent input or
  a caller-supplied path string);
- the staging mountpoint must be an absolute, existing, non-symlink,
  empty directory; slot-root presentation refuses symlink escapes.

Interaction surfaces: the layout-authority record shape is owned by
``greia_platform.persistent_layout`` (D34); the namespace map and state
contract by the same module (D30/D31). Slot payload writes consume the
``system-a``/``system-b`` roles (A8-SLOTWRITE); release finalization and
the boot transaction journal consume the transaction root (A8-FINALIZE
and later boot services).
"""

from __future__ import annotations

import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from greia_platform.persistent_layout import (
    BOOT_CONTROL_KINDS,
    BlockTopology,
    InstalledLayoutRecord,
    PersistentLayoutError,
    PersistentNamespaceMap,
    PersistRecoveryRequired,
    build_namespace_map,
    fresh_initialize_persist,
    open_existing_persist,
)

from .disk import DeviceObservation, DiskProbeError, partition_number_path
from .layout import LayoutError, LayoutPlan, validate_layout_plan


class PersistError(RuntimeError):
    """PERSIST orchestration failed fail-closed (fresh path or misuse)."""


#: Filesystem created on the persist partition (matches the A8-LAYOUT adapters).
PERSIST_FILESYSTEM = "ext4"

#: Filesystem label written by ``mkfs`` (matches the A8-LAYOUT adapters).
PERSIST_LABEL = "GREIA_PERSIST"

#: Production staging root for installer-owned PERSIST mounts. Callers pass
#: an explicit mountpoint (tests use disposable tmpdirs); this constant
#: documents the platform-owned default staging location.
PERSIST_STAGE_ROOT = Path("/run/greia-install/persist")

#: Orchestration-owned transaction-root directory name inside the PERSIST
#: state root (sibling of ``namespaces/``). Consumed by the boot
#: transaction journal (``BootTransactionJournal``) and release
#: finalization; created exactly once by the fresh path, gated by the
#: existing path. Mode ``0o700``: boot/transaction state, never child data.
PERSIST_TRANSACTION_DIRNAME = "boot-journal"

#: Transaction-root mode: root-only access on device.
PERSIST_TRANSACTION_MODE = 0o700

#: Slot-root presentation directory mode for canonical bind destinations.
SLOT_PRESENTATION_DIR_MODE = 0o755

_SHELL_METACHARACTERS = (";", "&", "|", "$", "`", "(", ")", "<", ">", "\n")


def _check_command(argv: tuple[str, ...]) -> tuple[str, ...]:
    """Reject shell-string-shaped commands before they can reach a runner."""
    if not argv or any(not isinstance(word, str) or not word for word in argv):
        raise PersistError("PERSIST commands must be non-empty text arrays")
    for word in argv:
        for marker in _SHELL_METACHARACTERS:
            if marker in word:
                raise PersistError(
                    "PERSIST commands must not carry shell metacharacters"
                )
    return argv


# ---------------------------------------------------------------------------
# Runner seam
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PersistCommandResult:
    """Narrow completed-command fact: collected output plus exit status."""

    stdout: str
    returncode: int


class PersistCommandRunner:
    """Narrow runner seam: argument arrays only, never shell strings."""

    def run(self, command: Sequence[str]) -> PersistCommandResult: ...  # pragma: no cover


class SubprocessPersistRunner(PersistCommandRunner):
    """Production runner: ``shell=False`` subprocess execution."""

    def run(self, command: Sequence[str]) -> PersistCommandResult:
        completed = subprocess.run(
            list(command),
            check=False,
            shell=False,
            text=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return PersistCommandResult(
            stdout=completed.stdout, returncode=completed.returncode
        )


# ---------------------------------------------------------------------------
# Shared derivation / guards
# ---------------------------------------------------------------------------


def persist_node_for(target: DeviceObservation, plan: LayoutPlan) -> Path:
    """Derive the persist partition node from observation plus plan role.

    The partition number comes only from the adapter-declared ``persist``
    role in the validated plan; the device locator comes only from the
    verified observation. Any other source fails closed with zero commands
    issued.
    """
    try:
        if target.device_type != "disk":
            raise PersistError("PERSIST orchestration requires a whole-disk target")
        if not str(target.path) or not target.path.is_absolute():
            raise PersistError(
                "verified target carries no absolute device locator"
            )
        validate_layout_plan(plan)
        persist_part = plan.by_role("persist")
        if persist_part is None:
            raise PersistError("layout plan carries no persist role")
        return partition_number_path(target.path, persist_part.number)
    except PersistError:
        raise
    except (LayoutError, DiskProbeError) as exc:
        raise PersistError(f"PERSIST target derivation failed: {exc}") from exc


def _require_staging_mountpoint(mountpoint: Path) -> Path:
    """Fail closed unless ``mountpoint`` is a safe empty staging directory."""
    location = Path(mountpoint)
    if not location.is_absolute():
        raise PersistError("PERSIST mountpoint must be an absolute path")
    if os.path.islink(location):
        raise PersistError("PERSIST mountpoint may not be a symbolic link")
    if not location.is_dir():
        raise PersistError("PERSIST mountpoint must be an existing directory")
    try:
        if any(location.iterdir()):
            raise PersistError("PERSIST mountpoint must be an empty staging directory")
    except OSError as exc:
        raise PersistError(f"PERSIST mountpoint is not accessible: {exc}") from exc
    return location


def persist_transaction_path(mountpoint: Path) -> Path:
    """Return the transaction-root path for a mounted PERSIST tree."""
    return Path(mountpoint) / "greia" / PERSIST_TRANSACTION_DIRNAME


def _blkid_filesystem_uuid(
    runner: PersistCommandRunner, node: Path
) -> str | None:
    """Read back the filesystem UUID on ``node``; ``None`` when absent."""
    command = _check_command(
        ("blkid", "-s", "UUID", "-o", "value", "--", str(node))
    )
    result = runner.run(list(command))
    candidate = result.stdout.strip()
    if result.returncode != 0 or not candidate:
        return None
    try:
        return str(uuid.UUID(candidate))
    except (ValueError, AttributeError) as exc:
        raise PersistError(
            "PERSIST filesystem identity is not a valid UUID"
        ) from exc


def _mount_staging(
    runner: PersistCommandRunner, node: Path, mountpoint: Path, *, readonly: bool
) -> None:
    options = "ro,nodev,nosuid" if readonly else "nodev,nosuid"
    command = _check_command(
        ("mount", "-t", PERSIST_FILESYSTEM, "-o", options, str(node), str(mountpoint))
    )
    result = runner.run(list(command))
    if result.returncode != 0:
        raise PersistError(f"PERSIST mount failed: {mountpoint}")


def unmount_persist(mountpoint: Path, runner: PersistCommandRunner) -> None:
    """Detach a staging PERSIST mount; failure is an explicit error."""
    location = Path(mountpoint)
    if not location.is_absolute():
        raise PersistError("PERSIST mountpoint must be an absolute path")
    command = _check_command(("umount", str(location)))
    result = runner.run(list(command))
    if result.returncode != 0:
        raise PersistError(f"PERSIST unmount failed: {location}")


# ---------------------------------------------------------------------------
# Fresh-install path
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FreshPersistSpec:
    """Caller-supplied fresh-install facts (identities plus release binding).

    The persist filesystem UUID is always generated by the orchestration
    (never caller-supplied); the persist PARTUUID comes from post-partition
    probing, and the slot identities plus release binding come from the
    installer transaction. Every value is re-validated through
    :class:`InstalledLayoutRecord` before anything is written.
    """

    platform_family: str
    install_profile: str
    install_target_sha256: str
    installed_at_unix: int
    boot_active_slot: str
    accepted_slot: str | None
    accepted_release_id: str
    slot_bytes: int
    system_a: Mapping[str, str]
    system_b: Mapping[str, str] | None
    persist_partuuid: str


@dataclass(frozen=True, slots=True)
class FreshPersistResult:
    """Facts of a completed fresh PERSIST initialization (now unmounted)."""

    persist_filesystem_uuid: str
    record: InstalledLayoutRecord
    namespace_map: PersistentNamespaceMap
    mountpoint: Path


def initialize_fresh_persist(
    *,
    target: DeviceObservation,
    plan: LayoutPlan,
    spec: FreshPersistSpec,
    mountpoint: Path,
    runner: PersistCommandRunner,
    uuid_factory: Callable[[], uuid.UUID] = uuid.uuid4,
    namespace_map: PersistentNamespaceMap | None = None,
) -> FreshPersistResult:
    """Create, mount and exactly-once initialize PERSIST for a fresh install.

    Fails closed (raising :class:`PersistError`, never recovery routing)
    when a filesystem already exists on the persist node, when the
    generated identity does not read back, or when any initialization step
    is partial. The staging mount is detached on success and best-effort
    detached on failure.

    Adapter reconciliation (POSTR1-P2): the layout adapter creates the
    PERSIST filesystem after partitioning and the post-layout observer
    reads its filesystem UUID, which the orchestrator binds as the
    intended identity via ``uuid_factory``. When the node already carries
    a filesystem whose UUID equals that intended identity, it is adopted
    exactly once — the redundant ``mkfs.ext4`` is skipped — and
    initialization continues with mount plus the exactly-once gates
    below. A different/unexpected UUID still refuses fail-closed, as does
    any pre-existing transaction root or layout-authority record.
    """
    stage = _require_staging_mountpoint(Path(mountpoint))
    node = persist_node_for(target, plan)

    try:
        generated = uuid.UUID(str(uuid_factory()))
    except (ValueError, AttributeError) as exc:
        raise PersistError("PERSIST identity generator is outside Greia bounds") from exc
    intended_uuid = str(generated)

    # Exactly-once pre-check BEFORE any destructive command: an existing
    # filesystem means a previous (possibly partial) initialization or a
    # foreign occupant — unless it is exactly the adapter-created
    # filesystem the observer already bound as the intended identity.
    # Never mkfs over a foreign occupant; the operator repartitions.
    existing_uuid = _blkid_filesystem_uuid(runner, node)
    if existing_uuid is not None and existing_uuid != intended_uuid:
        raise PersistError(
            "fresh PERSIST initialization refused: "
            "a filesystem already exists on the persist partition"
        )
    adopted = existing_uuid is not None

    if adopted:
        filesystem_uuid = existing_uuid
        assert filesystem_uuid is not None
    else:
        filesystem_uuid = intended_uuid

        mkfs = _check_command(
            (
                "mkfs.ext4",
                "-F",
                "-m",
                "1",
                "-L",
                PERSIST_LABEL,
                "-U",
                filesystem_uuid,
                str(node),
            )
        )
        if runner.run(list(mkfs)).returncode != 0:
            raise PersistError("PERSIST filesystem creation failed")

        # Prove the generated identity back before trusting the device: a
        # swapped/wrong node or a failed write must not receive an identity.
        observed = _blkid_filesystem_uuid(runner, node)
        if observed != filesystem_uuid:
            raise PersistError(
                "PERSIST filesystem identity did not read back; "
                "refusing to initialize an unproven device"
            )

    # Validate the full spec before mounting: a bad spec must fail before
    # any mount or initialization work, not after.
    try:
        table = namespace_map if namespace_map is not None else build_namespace_map()
        record = InstalledLayoutRecord.from_dict(
            {
                "accepted_release_id": spec.accepted_release_id,
                "accepted_slot": spec.accepted_slot,
                "boot_backend": plan.boot_backend,
                "boot_control": {
                    "active_slot": spec.boot_active_slot,
                    "kind": BOOT_CONTROL_KINDS[plan.boot_backend],
                },
                "install_profile": spec.install_profile,
                "install_target_sha256": spec.install_target_sha256,
                "installed_at_unix": spec.installed_at_unix,
                "layout_id": plan.adapter_id,
                "persist": {
                    "filesystem_uuid": filesystem_uuid,
                    "partuuid": spec.persist_partuuid,
                },
                "platform_family": spec.platform_family,
                "schema_version": 1,
                "slot_bytes": spec.slot_bytes,
                "system_a": dict(spec.system_a),
                "system_b": (
                    dict(spec.system_b) if spec.system_b is not None else None
                ),
            }
        )
    except KeyError as exc:
        raise PersistError(
            f"fresh PERSIST spec does not match the layout adapter: {exc}"
        ) from exc
    except PersistentLayoutError as exc:
        raise PersistError(
            f"fresh PERSIST spec is not authoritative: {exc}"
        ) from exc

    try:
        _mount_staging(runner, node, stage, readonly=False)
    except PersistError:
        raise

    try:
        try:
            fresh_initialize_persist(stage, record, table)
        except PersistentLayoutError as exc:
            raise PersistError(
                f"fresh PERSIST initialization refused (never re-mint): {exc}"
            ) from exc
        transaction_dir = persist_transaction_path(stage)
        if transaction_dir.is_symlink() or transaction_dir.exists():
            raise PersistError(
                "fresh PERSIST initialization refused: "
                "transaction root already exists"
            )
        try:
            transaction_dir.mkdir(parents=True, exist_ok=False)
            os.chmod(transaction_dir, PERSIST_TRANSACTION_MODE)
        except OSError as exc:
            raise PersistError(
                f"fresh PERSIST transaction root failed: {exc}"
            ) from exc
    except BaseException as exc:
        # Fail closed on partial initialization: detach staging, propagate.
        # The on-partition filesystem now holds partial state; the blkid
        # pre-check above refuses silent re-initialization over it.
        try:
            unmount_persist(stage, runner)
        except PersistError:
            pass
        if isinstance(exc, PersistError):
            raise
        if isinstance(exc, Exception):
            raise PersistError(
                f"fresh PERSIST initialization failed: {exc}"
            ) from exc
        raise
    unmount_persist(stage, runner)
    return FreshPersistResult(
        persist_filesystem_uuid=filesystem_uuid,
        record=record,
        namespace_map=table,
        mountpoint=stage,
    )


# ---------------------------------------------------------------------------
# Existing-install path (recovery routing, never re-initialization)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OpenedPersist:
    """A mounted, proven existing PERSIST tree.

    The staging mount is left attached so boot/finalize consumers can use
    the proven paths; the caller must call :func:`unmount_persist` when
    done. ``record``/``namespace_map`` are the platform-proven authorities.
    """

    record: InstalledLayoutRecord
    namespace_map: PersistentNamespaceMap
    mountpoint: Path


def open_installed_persist(
    *,
    target: DeviceObservation,
    plan: LayoutPlan,
    topology: object,
    mountpoint: Path,
    runner: PersistCommandRunner,
    expect_uid: int | None = None,
) -> OpenedPersist:
    """Mount and prove an existing PERSIST tree; failures enter recovery.

    Raises :class:`PersistRecoveryRequired` (after best-effort detach) for
    mount failure and for every platform rejection (missing/corrupt
    record, topology mismatch, swapped slots, wrong UUID, symlink,
    missing namespace/contract/transaction root). Never initializes.
    """
    stage = _require_staging_mountpoint(Path(mountpoint))
    node = persist_node_for(target, plan)
    if not isinstance(topology, BlockTopology):
        raise PersistError("existing PERSIST open requires observed block topology")

    mount_command = _check_command(
        (
            "mount",
            "-t",
            PERSIST_FILESYSTEM,
            "-o",
            "ro,nodev,nosuid",
            str(node),
            str(stage),
        )
    )
    if runner.run(list(mount_command)).returncode != 0:
        raise PersistRecoveryRequired("PERSIST mount failed: entering recovery")

    try:
        try:
            record, table = open_existing_persist(
                stage, topology, expect_uid=expect_uid
            )
        except PersistRecoveryRequired:
            raise
        except PersistentLayoutError as exc:
            raise PersistRecoveryRequired(
                f"PERSIST state is not authoritative: {exc}"
            ) from exc
        transaction_dir = persist_transaction_path(stage)
        if transaction_dir.is_symlink() or not transaction_dir.is_dir():
            raise PersistRecoveryRequired(
                "PERSIST transaction root is missing: entering recovery"
            )
    except BaseException as exc:
        try:
            unmount_persist(stage, runner)
        except PersistError:
            pass
        if isinstance(exc, PersistRecoveryRequired):
            raise
        if isinstance(exc, Exception):
            raise PersistRecoveryRequired(
                f"PERSIST state cannot be proven: {exc}"
            ) from exc
        raise
    return OpenedPersist(record=record, namespace_map=table, mountpoint=stage)


# ---------------------------------------------------------------------------
# Slot-root canonical-path presentation
# ---------------------------------------------------------------------------


def present_canonical_paths(
    slot_root: Path,
    namespace_map: PersistentNamespaceMap | None = None,
) -> tuple[Path, ...]:
    """Materialize required canonical bind destinations inside a slot root.

    Creates every mount target from the namespace map as a directory (for
    file binds, the parent directory) with presentation mode, refusing
    symlink escapes. Pure filesystem work: no runner, no mounts.
    """
    from greia_platform.persistent_layout import MountKind

    root = Path(slot_root)
    if not root.is_absolute():
        raise PersistError("slot root must be an absolute path")
    if os.path.islink(root) or not root.is_dir():
        raise PersistError("slot root must be an existing real directory")
    table = namespace_map if namespace_map is not None else build_namespace_map()
    base_resolved = root.resolve()
    presented: list[Path] = []
    for mount in table.mount_plan():
        relative = mount.target.lstrip("/")
        if not relative:
            raise PersistError("namespace map carries an unpresentable target")
        candidate = base_resolved.joinpath(relative)
        try:
            candidate.relative_to(base_resolved)
        except ValueError as exc:
            raise PersistError(
                f"canonical path escapes the slot root: {mount.target}"
            ) from exc
        if mount.kind == MountKind.BIND_FILE:
            directory = candidate.parent
        else:
            directory = candidate
        # Walk and create component by component so a planted symlink can
        # never redirect presentation outside the slot root.
        current = base_resolved
        for component in directory.relative_to(base_resolved).parts:
            current = current / component
            if os.path.islink(current):
                raise PersistError(
                    f"canonical path passes a symbolic link: {mount.target}"
                )
            try:
                current.mkdir(mode=SLOT_PRESENTATION_DIR_MODE, exist_ok=True)
            except OSError as exc:
                raise PersistError(
                    f"canonical path cannot be presented: {mount.target}: {exc}"
                ) from exc
            if not current.is_dir() or os.path.islink(current):
                raise PersistError(
                    f"canonical path is not a real directory: {mount.target}"
                )
        try:
            os.chmod(directory, SLOT_PRESENTATION_DIR_MODE)
        except OSError as exc:
            raise PersistError(
                f"canonical path mode failed: {mount.target}: {exc}"
            ) from exc
        presented.append(directory)
    # The layout-authority bind file itself is presented by the boot bind,
    # not pre-created here: only its parent directory is required above.
    return tuple(dict.fromkeys(presented))


__all__ = [
    "PERSIST_FILESYSTEM",
    "PERSIST_LABEL",
    "PERSIST_STAGE_ROOT",
    "PERSIST_TRANSACTION_DIRNAME",
    "PERSIST_TRANSACTION_MODE",
    "SLOT_PRESENTATION_DIR_MODE",
    "FreshPersistResult",
    "FreshPersistSpec",
    "OpenedPersist",
    "PersistCommandResult",
    "PersistCommandRunner",
    "PersistError",
    "PersistRecoveryRequired",
    "SubprocessPersistRunner",
    "initialize_fresh_persist",
    "open_installed_persist",
    "persist_node_for",
    "persist_transaction_path",
    "present_canonical_paths",
    "unmount_persist",
]
