"""Fresh signed-release install to SYSTEM_A (Phase 8B Step 8B.3 / X8-INSTALL).

The privileged ``greia-install-transaction`` service calls
:func:`execute_fresh_ab_install` after the narrow PREPARE/EXECUTE protocol
has consumed a single-use nonce and rematerialized every install fact from
Greia-owned service state (see :mod:`greia_installer.transaction_service`).
The installer UI never opens or writes raw disks: requests carry only an
identity digest plus bounded preference scalars, never paths, commands,
URLs, devices or partition numbers.

Flow on a disposable target (loop/QEMU image; D50 forbids Acer repartition
here):

1. verify the deterministic signed release bundle (manifest v2 member order,
   canonical JSON, per-member digests, Ed25519 signature against the trusted
   key dir, platform/family/profile compatibility with the service-owned
   expectation);
2. preflight the finalized-slot capacity bound
   (``max(base, minimum) + support + growth + reserve <= slot``) and prove
   the profile layout plan fits the verified target — both **before** the
   first destructive command;
3. create MBR A/B/PERSIST through the executable ``legacy-bios-ab-v1``
   adapter (argument arrays, ``shell=False`` by the caller's runner);
4. stream the signed payload to ``SYSTEM_A`` only through the shared
   :class:`greia_platform.slot_writer.SlotWriter` (stream + readback digest,
   single-use write capability);
5. role-bind and finalize ``SYSTEM_A`` through the shared
   :class:`greia_platform.slot_writer.SlotFinalizer` (role UUID restore,
   release-bound support set, deterministic boot artifacts, receipt);
   ``SYSTEM_B`` is formatted empty by the adapter and never receives a
   payload stream or a finalization — no second-slot duplication;
6. initialize PERSIST exactly once (layout authority record bound to the
   finalized-A receipt, versioned namespace schema, transaction root);
7. install the stable GRUB backend (fixed two-entry config rendered from the
   trusted layout record plus ``grubenv`` with default ``A``);
8. write ``FIRST_INSTALL_PENDING`` through
   :class:`greia_platform.boot_transaction.BootTransactionJournal`.

Acceptance is **not** part of the install: :func:`accept_first_install`
health-commits slot A only after an observed boot of A, and production
callers invoke it solely from the trusted post-intro interactive-health
handler (the same ``BOOT_HEALTHY`` one-use post-intro capability the
updater uses; first-install pending is not A/B rollback). Failed or missing
health leaves the persistent default ``A`` in place and routes through
``mark_failed``.

No child-process spawning, no shell and no device nodes live in this
module: every block command is an argument array executed by an injected
runner seam, every staging directory is an injected absolute path, and
every hardware fact (support set, inventory attestation, profile policy)
arrives as a typed value. Unit tests drive the whole flow on fakes with
zero disk contact.
"""

from __future__ import annotations

import os
import re
import time
import uuid
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Callable, Mapping, Sequence

from greia_platform.boot_transaction import (
    BootArtifactSet,
    BootTransactionBackend,
    BootTransactionCoordinator,
    BootTransactionError,
    BootTransactionJournal,
    BootTransactionState,
)
from greia_platform.grub_ab import (
    GrubAbConfigError,
    GrubEnvBackend,
    render_grub_ab_config_from_record,
    validate_grub_ab_text,
)
from greia_platform.persistent_layout import InstalledLayoutRecord
from greia_platform.slot_writer import (
    DestinationSlot,
    FinalizationReceipt,
    SlotFinalizer,
    SlotFilesystem,
    SlotPackageInstaller,
    SlotStorage,
    SlotWriteError,
    SlotFinalizeError,
    SlotWriter,
    VerifiedReleaseMember,
)
from greia_platform.system_updates import (
    PAYLOAD_NAME,
    SystemUpdateError,
    UpdateBundleError,
    UpdateSignatureError,
    inspect_update_bundle,
    verify_update_signature,
)

from .disk import DeviceObservation
from .layout import (
    LayoutError,
    LayoutPlan,
    ProfileSizing,
    adapter_for,
    mint_fresh_partition_identities,
    plan_for_profile,
    require_finalized_slot_capacity,
)
from .persist import (
    FreshPersistSpec,
    PersistError,
    initialize_fresh_persist,
)


class FreshAbInstallError(RuntimeError):
    """Fresh A/B install refused or failed fail-closed (no partial accept)."""


_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

#: File name of the installed GRUB configuration on the boot-control volume.
GRUB_CONFIG_NAME = "grub.cfg"


def _require_hex64(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not _HEX64_RE.fullmatch(value):
        raise FreshAbInstallError(f"{field_name} must be lowercase SHA-256 hex")
    return value


def _require_regular_file(value: object, *, field_name: str) -> Path:
    location = Path(value) if isinstance(value, (Path, str)) else None
    if location is None or not location.is_absolute():
        raise FreshAbInstallError(f"{field_name} must be an absolute path")
    if location.is_symlink() or not location.is_file():
        raise FreshAbInstallError(f"{field_name} is not a regular file")
    return location


# ---------------------------------------------------------------------------
# Typed request
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FreshAbInstallRequest:
    """Service-owned fresh-install facts (never UI/Parent bytes).

    ``bundle_path`` is the signed deterministic ``.greiaupdate`` v2 release
    artifact; ``trusted_key_dir`` holds the release signer public keys.
    ``expected_*`` are the installer image's own compatibility facts: the
    manifest must match all three exactly. ``install_target_sha256`` is the
    authorized identity digest the privileged protocol rematerialized from a
    fresh probe (never a ``/dev`` path). ``fresh_identities`` carries the
    minted role-owned PARTUUID/filesystem-UUID pairs (see
    :func:`mint_fresh_partition_identities`); when ``None`` the orchestrator
    mints them. ``password_hash`` is the stored GRUB PBKDF2 token rendered
    into the fixed boot entries.
    """

    bundle_path: Path
    trusted_key_dir: Path
    expected_profile_id: str
    expected_platform_family: str
    expected_architecture: str
    sizing: ProfileSizing
    target: DeviceObservation
    support_installed_bytes: int
    install_target_sha256: str
    password_hash: str
    developer: bool = False
    installed_at_unix: int = 0
    fresh_identities: Mapping[str, Mapping[str, str]] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "bundle_path", _require_regular_file(self.bundle_path, field_name="release bundle")
        )
        key_dir = Path(self.trusted_key_dir) if isinstance(self.trusted_key_dir, (Path, str)) else None
        if key_dir is None or not key_dir.is_absolute() or key_dir.is_symlink() or not key_dir.is_dir():
            raise FreshAbInstallError("trusted key dir must be an absolute real directory")
        object.__setattr__(self, "trusted_key_dir", key_dir)
        for field_name in (
            "expected_profile_id",
            "expected_platform_family",
            "expected_architecture",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value or len(value) > 96:
                raise FreshAbInstallError(f"{field_name} is outside Greia bounds")
        if not isinstance(self.sizing, ProfileSizing):
            raise FreshAbInstallError("install requires profile-owned sizing facts")
        if not isinstance(self.target, DeviceObservation):
            raise FreshAbInstallError("install requires a verified whole-disk target")
        if (
            isinstance(self.support_installed_bytes, bool)
            or not isinstance(self.support_installed_bytes, int)
            or self.support_installed_bytes < 0
        ):
            raise FreshAbInstallError("support installed-size bound must be a non-negative integer")
        _require_hex64(self.install_target_sha256, field_name="install target identity")
        if not isinstance(self.password_hash, str) or not self.password_hash:
            raise FreshAbInstallError("GRUB password hash must be non-empty text")
        if not isinstance(self.developer, bool):
            raise FreshAbInstallError("developer must be a boolean")
        if (
            isinstance(self.installed_at_unix, bool)
            or not isinstance(self.installed_at_unix, int)
            or self.installed_at_unix < 0
        ):
            raise FreshAbInstallError("installed_at_unix must be a non-negative integer")


# ---------------------------------------------------------------------------
# Injected seams (production runners or zero-disk-contact fakes)
# ---------------------------------------------------------------------------


class PartitionRunner:
    """Narrow seam: run one partition argument array (``shell=False``)."""

    def run(self, command: Sequence[str]) -> object: ...  # pragma: no cover


@dataclass
class FreshAbInstallSeams:
    """Every destructive/filesystem effect the orchestrator may cause.

    ``slot_storage_factory`` is called exactly once with ``"A"`` — the
    orchestrator never addresses ``SYSTEM_B`` storage, so a second-slot
    duplication is inexpressible here. ``payload_stream_factory`` opens the
    signed payload byte stream (default reads the bundle's payload member);
    ``slot_filesystem_factory``/``package_installer_factory`` own the
    destination-slot finalization seam. ``persist_stage_dir`` must be an
    existing empty directory; ``boot_control_dir``/``backend_state_dir``/
    ``journal_dir`` receive the installed GRUB config, the ``grubenv`` block
    and the ``FIRST_INSTALL_PENDING`` journal.
    """

    partition_runner: PartitionRunner
    slot_storage_factory: Callable[[str], SlotStorage]
    slot_filesystem_factory: Callable[[], SlotFilesystem]
    package_installer_factory: Callable[[], SlotPackageInstaller]
    inventory_token: str
    support_digest: str
    support_size: int
    support_installed_bound: int
    support_classes: tuple[tuple[str, str, str, str], ...] = ()
    persist_runner: object = None
    persist_stage_dir: Path | None = None
    persist_uuid_factory: Callable[[], uuid.UUID] | None = None
    boot_control_dir: Path | None = None
    backend_state_dir: Path | None = None
    journal_dir: Path | None = None
    firmware_packages: tuple[str, ...] = ()
    microcode_packages: tuple[str, ...] = ()
    payload_stream_factory: Callable[[], BinaryIO] | None = None
    inventory_complete: bool = True

    def __post_init__(self) -> None:
        _require_hex64(self.inventory_token, field_name="hardware inventory token")
        _require_hex64(self.support_digest, field_name="release support digest")
        for field_name in ("support_size", "support_installed_bound"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise FreshAbInstallError(f"{field_name} must be a non-negative integer")


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FreshAbInstallResult:
    """Facts of a completed fresh install (SYSTEM_A finalized, B inactive)."""

    release_id: str
    release_sequence: int
    layout_plan: LayoutPlan
    receipt: FinalizationReceipt
    record: InstalledLayoutRecord
    journal: BootTransactionJournal
    grub_config_text: str
    bytes_written: int


# ---------------------------------------------------------------------------
# Bundle payload stream (read-only ZIP member access, no shell)
# ---------------------------------------------------------------------------


def open_bundle_payload_stream(bundle_path: Path) -> BinaryIO:
    """Open a read-only stream over the bundle's signed payload member."""
    location = Path(bundle_path)
    try:
        archive = zipfile.ZipFile(location, "r")
    except (zipfile.BadZipFile, OSError) as exc:
        raise FreshAbInstallError(f"release bundle is not readable: {exc}") from exc
    try:
        data = archive.read(PAYLOAD_NAME)
    except (KeyError, zipfile.BadZipFile, OSError) as exc:
        raise FreshAbInstallError(f"release bundle carries no signed payload: {exc}") from exc
    finally:
        try:
            archive.close()
        except OSError:
            pass
    return BytesIO(data)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def execute_fresh_ab_install(
    request: FreshAbInstallRequest,
    seams: FreshAbInstallSeams,
    *,
    now_unix: int | None = None,
) -> FreshAbInstallResult:
    """Verify, partition, stream/finalize A, init PERSIST, install GRUB, journal.

    Every refusal raises :class:`FreshAbInstallError` with zero acceptance:
    in particular the finalized-slot capacity preflight, release/signature/
    compatibility/support binding and layout-fit proof all run **before**
    the first destructive partition command, and ``SYSTEM_B`` storage is
    never addressed.
    """
    if not isinstance(request, FreshAbInstallRequest):
        raise FreshAbInstallError("fresh install requires a typed install request")
    if not isinstance(seams, FreshAbInstallSeams):
        raise FreshAbInstallError("fresh install requires typed install seams")
    for field_name in (
        "persist_stage_dir",
        "boot_control_dir",
        "backend_state_dir",
        "journal_dir",
    ):
        if getattr(seams, field_name) is None:
            raise FreshAbInstallError(f"install seams carry no {field_name}")
    if seams.persist_runner is None:
        raise FreshAbInstallError("install seams carry no PERSIST runner")
    if request.target.device_type != "disk":
        raise FreshAbInstallError("fresh install requires a whole-disk target")

    # -- 1. Verified deterministic signed release only ---------------------
    try:
        inspected = inspect_update_bundle(request.bundle_path)
    except (UpdateBundleError, UpdateSignatureError, SystemUpdateError) as exc:
        raise FreshAbInstallError(f"release bundle is not a verified Greia release: {exc}") from exc
    try:
        verify_update_signature(inspected, request.trusted_key_dir)
    except (UpdateSignatureError, UpdateBundleError, SystemUpdateError, OSError) as exc:
        raise FreshAbInstallError(f"release signature is not trusted: {exc}") from exc
    manifest = inspected.manifest
    if manifest.profile != request.expected_profile_id:
        raise FreshAbInstallError("release profile does not match this installer image")
    if manifest.platform_family != request.expected_platform_family:
        raise FreshAbInstallError("release platform family does not match this installer image")
    if manifest.architecture != request.expected_architecture:
        raise FreshAbInstallError("release architecture does not match this installer image")
    try:
        member = VerifiedReleaseMember.from_manifest(manifest)
    except SlotWriteError as exc:
        raise FreshAbInstallError(f"signed release facts are not installable: {exc}") from exc

    # -- Release-bound support set (finalizer re-checks digest binding) -----
    if seams.support_digest != member.hardware_support_sha256:
        raise FreshAbInstallError("support set is not the release-bound support member")
    if seams.support_size != member.hardware_support_size:
        raise FreshAbInstallError("support set size is not the release-bound member size")
    if seams.support_installed_bound != request.support_installed_bytes:
        raise FreshAbInstallError("support installed-size bound skews the capacity preflight")
    try:
        support = _support_set_from_seams(seams)
    except SlotFinalizeError as exc:
        raise FreshAbInstallError(f"support set is not installable: {exc}") from exc

    # -- 2. Capacity + layout-fit preflight BEFORE any destructive command --
    try:
        require_finalized_slot_capacity(
            slot_bytes=int(request.sizing.slot_bytes),
            base_bytes=member.payload_size,
            minimum_slot_bytes=member.minimum_slot_bytes,
            support_installed_bytes=request.support_installed_bytes,
        )
        plan = plan_for_profile(
            request.sizing, device_size_bytes=int(request.target.size_bytes)
        )
    except (LayoutError, SlotWriteError) as exc:
        raise FreshAbInstallError(f"release does not fit this target: {exc}") from exc
    if plan.boot_backend != request.sizing.boot_backend:
        raise FreshAbInstallError("layout boot backend does not match the profile sizing")

    # -- Fresh role-owned identities (never cloned template UUIDs) ---------
    minted = _fresh_identities(request)
    try:
        from greia_platform.slot_writer import (
            HardwareInventoryAttestation,
            SlotProfilePolicy,
        )

        inventory = HardwareInventoryAttestation(token=seams.inventory_token)
        if not seams.inventory_complete:
            raise FreshAbInstallError("hardware inventory is incomplete; refusing finalization")
        policy = SlotProfilePolicy(
            layout_id=request.sizing.layout_adapter_id,
            system_slot_bytes=int(request.sizing.slot_bytes),
            boot_backend=request.sizing.boot_backend,
        )
    except (SlotWriteError, SlotFinalizeError) as exc:
        raise FreshAbInstallError(f"install policy facts are not authoritative: {exc}") from exc

    # -- 3. First destructive commands: MBR A/B/PERSIST --------------------
    try:
        adapter = adapter_for(request.sizing.layout_adapter_id)
    except LayoutError as exc:
        raise FreshAbInstallError(f"release layout adapter is unknown: {exc}") from exc
    if adapter.boot_backend != request.sizing.boot_backend:
        raise FreshAbInstallError("release boot backend does not match the layout adapter")
    try:
        adapter.execute(seams.partition_runner, target=request.target, plan=plan)  # type: ignore[arg-type]
    except LayoutError as exc:
        raise FreshAbInstallError(f"disk partitioning failed fail-closed: {exc}") from exc
    except Exception as exc:
        raise FreshAbInstallError(f"disk partitioning failed fail-closed: {exc}") from exc

    # -- 4./5. Stream + finalize SYSTEM_A only (B never addressed) ---------
    destination_a = DestinationSlot(
        semantic_slot="A",
        role="system-a",
        slot_capacity_bytes=int(request.sizing.slot_bytes),
        active_slot=None,
        accepted_slot=None,
        layout_id=request.sizing.layout_adapter_id,
        role_filesystem_uuid=minted["system-a"]["filesystem_uuid"],
        other_role_filesystem_uuid=minted["system-b"]["filesystem_uuid"],
    )
    try:
        storage = seams.slot_storage_factory("A")
    except (SlotWriteError, FreshAbInstallError) as exc:
        raise FreshAbInstallError(f"SYSTEM_A slot store is not authoritative: {exc}") from exc
    except Exception as exc:
        raise FreshAbInstallError(f"SYSTEM_A slot store is not authoritative: {exc}") from exc
    writer = SlotWriter()
    stream_factory = seams.payload_stream_factory or (lambda: open_bundle_payload_stream(request.bundle_path))
    try:
        source = stream_factory()
    except FreshAbInstallError:
        raise
    except Exception as exc:
        raise FreshAbInstallError(f"release payload stream is not readable: {exc}") from exc
    try:
        with _closing(source):
            write = writer.write(
                member=member,
                destination=destination_a,
                source=source,
                storage=storage,
                support_installed_bytes=seams.support_installed_bound,
            )
    except SlotWriteError as exc:
        raise FreshAbInstallError(f"SYSTEM_A streaming refused: {exc}") from exc
    try:
        filesystem = seams.slot_filesystem_factory()
        package_installer = seams.package_installer_factory()
    except Exception as exc:
        raise FreshAbInstallError(f"SYSTEM_A finalization seam failed: {exc}") from exc
    finalizer = SlotFinalizer()
    try:
        receipt = finalizer.finalize(
            write=write,
            destination=destination_a,
            filesystem=filesystem,
            package_installer=package_installer,
            inventory=inventory,
            support=support,
            profile_policy=policy,
            firmware_packages=tuple(seams.firmware_packages),
            microcode_packages=tuple(seams.microcode_packages),
        )
    except (SlotFinalizeError, SlotWriteError) as exc:
        raise FreshAbInstallError(f"SYSTEM_A finalization refused: {exc}") from exc
    if receipt.slot != "A":
        raise FreshAbInstallError("finalization receipt does not bind SYSTEM_A")

    # -- 6. PERSIST exactly once (layout authority bound to receipt A) ------
    installed_at = request.installed_at_unix or (now_unix if now_unix is not None else int(time.time()))
    if isinstance(installed_at, bool) or installed_at < 0:
        raise FreshAbInstallError("installed_at_unix is not a valid timestamp")
    spec = FreshPersistSpec(
        platform_family=manifest.platform_family,
        install_profile=request.expected_profile_id,
        install_target_sha256=request.install_target_sha256,
        installed_at_unix=int(installed_at),
        boot_active_slot="A",
        accepted_slot="A",
        accepted_release_id=member.release_id,
        accepted_release_sequence=member.release_sequence,
        slot_bytes=int(request.sizing.slot_bytes),
        system_a=dict(minted["system-a"]),
        system_b=dict(minted["system-b"]),
        persist_partuuid=minted["persist"]["partuuid"],
    )
    persist_uuid_factory = seams.persist_uuid_factory or (
        lambda: uuid.UUID(minted["persist"]["filesystem_uuid"])
    )
    try:
        persist_result = initialize_fresh_persist(
            target=request.target,
            plan=plan,
            spec=spec,
            mountpoint=Path(seams.persist_stage_dir),
            runner=seams.persist_runner,  # type: ignore[arg-type]
            uuid_factory=persist_uuid_factory,  # type: ignore[arg-type]
        )
    except PersistError as exc:
        raise FreshAbInstallError(f"PERSIST initialization refused: {exc}") from exc
    record = persist_result.record
    if record.accepted_slot != "A" or record.boot_control.active_slot != "A":
        raise FreshAbInstallError("layout authority does not boot-accept SYSTEM_A")
    if record.system_b is None:
        raise FreshAbInstallError("A/B layout authority requires the inactive SYSTEM_B identity")

    # -- 7. Stable GRUB backend (fixed entries + grubenv default A) --------
    try:
        grub_text = render_grub_ab_config_from_record(
            record=record,
            password_hash=request.password_hash,
            developer=request.developer,
        )
        validate_grub_ab_text(grub_text, developer=request.developer)
    except (GrubAbConfigError, Exception) as exc:
        raise FreshAbInstallError(f"stable GRUB entries refused: {exc}") from exc
    try:
        _write_boot_control_config(Path(seams.boot_control_dir), grub_text)
        GrubEnvBackend.initialize(Path(seams.backend_state_dir), default_slot="A")
    except (BootTransactionError, GrubAbConfigError, OSError) as exc:
        raise FreshAbInstallError(f"boot backend install failed: {exc}") from exc

    # -- 8. FIRST_INSTALL_PENDING (acceptance owns the commit, not this) ----
    try:
        journal = BootTransactionJournal.begin_first_install(
            Path(seams.journal_dir),
            layout_id=request.sizing.layout_adapter_id,
            boot_backend=request.sizing.boot_backend,
            release_id=member.release_id,
            release_sequence=member.release_sequence,
        )
    except (BootTransactionError, OSError) as exc:
        raise FreshAbInstallError(f"first-install journal refused: {exc}") from exc
    if journal.state is not BootTransactionState.FIRST_INSTALL_PENDING:
        raise FreshAbInstallError("first-install journal is not pending acceptance")

    return FreshAbInstallResult(
        release_id=member.release_id,
        release_sequence=member.release_sequence,
        layout_plan=plan,
        receipt=receipt,
        record=record,
        journal=journal,
        grub_config_text=grub_text,
        bytes_written=member.payload_size,
    )


# ---------------------------------------------------------------------------
# Health-gated acceptance (trusted post-intro predicate owns the call)
# ---------------------------------------------------------------------------


def accept_first_install(
    *,
    journal_dir: Path,
    backend: BootTransactionBackend,
    artifact_a: BootArtifactSet,
) -> BootTransactionJournal:
    """Health-commit a pending first install after an observed boot of A.

    Production callers invoke this solely from the trusted post-intro
    interactive-health handler (one-use ``BOOT_HEALTHY`` capability after
    the full intro and ``INTERACTIVE_READY``): the coordinator refuses the
    commit unless the journal is pending, the machine observably booted the
    candidate slot ``A``, and no untrusted Activity launch has been allowed.
    Failed health must call ``coordinator.mark_failed`` instead — the
    persistent default ``A`` then stays in place and the failure is bounded
    evidence, never a rollback (first install has nothing to roll back to).
    """
    location = Path(journal_dir)
    try:
        coordinator = BootTransactionCoordinator.begin_first_install(
            journal_dir=location, backend=backend, artifact_a=artifact_a
        )
    except BootTransactionError as exc:
        # A pending journal already exists: re-attach instead of double-open.
        try:
            coordinator = BootTransactionCoordinator.resume(
                journal_dir=location,
                backend=backend,
                candidate_artifacts=artifact_a,
                accepted_artifacts=artifact_a,
            )
        except BootTransactionError:
            raise FreshAbInstallError(
                f"first-install acceptance refused: {exc}"
            ) from exc
    if coordinator.journal.state is not BootTransactionState.FIRST_INSTALL_PENDING:
        raise FreshAbInstallError("first-install journal is not pending acceptance")
    try:
        observed, _ = coordinator.observe_boot()
    except BootTransactionError as exc:
        raise FreshAbInstallError(f"first-install has no authoritative boot of A: {exc}") from exc
    if observed != "A":
        raise FreshAbInstallError("first-install acceptance requires the booted slot to be A")
    try:
        coordinator.commit()
    except BootTransactionError as exc:
        raise FreshAbInstallError(f"first-install health commit refused: {exc}") from exc
    if coordinator.journal.state is not BootTransactionState.ACCEPTED:
        raise FreshAbInstallError("first-install journal did not reach ACCEPTED")
    return coordinator.journal


# ---------------------------------------------------------------------------
# Privileged-service executor factory (narrow protocol → orchestrator)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AbExecutorFacts:
    """Service-owned facts the A/B executor rematerializes per EXECUTE.

    Every value comes from the installer image / privileged service
    environment — never from UI request bytes. ``install`` builds the typed
    :class:`FreshAbInstallRequest` from the revalidated authorization
    (identity digest), the service-held settings snapshot outcome and the
    rematerialized target, then runs :func:`execute_fresh_ab_install`
    through the bound seam factories.
    """

    bundle_path: Path
    trusted_key_dir: Path
    expected_profile_id: str
    expected_platform_family: str
    expected_architecture: str
    sizing: ProfileSizing
    support_installed_bytes: int
    password_hash: str
    developer: bool = False

    def __post_init__(self) -> None:
        _require_regular_file(self.bundle_path, field_name="release bundle")
        key_dir = Path(self.trusted_key_dir)
        if not key_dir.is_absolute() or key_dir.is_symlink() or not key_dir.is_dir():
            raise FreshAbInstallError("trusted key dir must be an absolute real directory")
        for field_name in (
            "expected_profile_id",
            "expected_platform_family",
            "expected_architecture",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value or len(value) > 96:
                raise FreshAbInstallError(f"{field_name} is outside Greia bounds")
        if not isinstance(self.sizing, ProfileSizing):
            raise FreshAbInstallError("install requires profile-owned sizing facts")
        if (
            isinstance(self.support_installed_bytes, bool)
            or not isinstance(self.support_installed_bytes, int)
            or self.support_installed_bytes < 0
        ):
            raise FreshAbInstallError("support installed-size bound must be a non-negative integer")
        if not isinstance(self.password_hash, str) or not self.password_hash:
            raise FreshAbInstallError("GRUB password hash must be non-empty text")


def build_ab_executor(
    facts: AbExecutorFacts,
    seams_factory: Callable[[DeviceObservation], FreshAbInstallSeams],
):
    """Bind service-owned facts into an :attr:`ab_executor` callable.

    ``seams_factory`` receives the rematerialized target and returns the
    fully bound seams (partition/persist runners, slot storage/filesystem,
    staging dirs, journal/backend dirs, support/inventory facts). The
    returned executor takes ``(authorization, settings, locale, target)``
    from :meth:`InstallTransactionService.execute_ab_install` and returns
    an install result object; any refusal raises fail-closed.
    """
    if not isinstance(facts, AbExecutorFacts):
        raise FreshAbInstallError("A/B executor requires typed service facts")
    if not callable(seams_factory):
        raise FreshAbInstallError("A/B executor requires a seam factory")

    def _execute(authorization: object, settings: object, locale: object, target: DeviceObservation):  # type: ignore[no-untyped-def]
        identity = getattr(authorization, "target_identity", "")
        _require_hex64(identity, field_name="install target identity")
        if not isinstance(target, DeviceObservation):
            raise FreshAbInstallError("A/B executor requires a rematerialized target")
        seams = seams_factory(target)
        if not isinstance(seams, FreshAbInstallSeams):
            raise FreshAbInstallError("A/B seam factory returned no install seams")
        request = FreshAbInstallRequest(
            bundle_path=facts.bundle_path,
            trusted_key_dir=facts.trusted_key_dir,
            expected_profile_id=facts.expected_profile_id,
            expected_platform_family=facts.expected_platform_family,
            expected_architecture=facts.expected_architecture,
            sizing=facts.sizing,
            target=target,
            support_installed_bytes=facts.support_installed_bytes,
            install_target_sha256=identity,
            password_hash=facts.password_hash,
            developer=facts.developer,
        )
        result = execute_fresh_ab_install(request, seams)
        return _InstallResultShim(
            release_id=result.release_id,
            release_sequence=result.release_sequence,
        )

    return _execute


@dataclass(frozen=True, slots=True)
class _InstallResultShim:
    """Minimal install-result carrying the accepted release identity."""

    release_id: str
    release_sequence: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _support_set_from_seams(seams: FreshAbInstallSeams):  # -> ReleaseSupportSet
    from greia_platform.slot_writer import InstalledPackage, ReleaseSupportSet

    records: list[InstalledPackage] = []
    firmware_names = frozenset(seams.firmware_packages)
    microcode_names = frozenset(seams.microcode_packages)
    if firmware_names & microcode_names:
        raise FreshAbInstallError("support firmware/microcode classes overlap")
    for name, version, architecture, digest in seams.support_classes:
        if name in firmware_names:
            kind = "firmware"
        elif name in microcode_names:
            kind = "microcode"
        else:
            raise FreshAbInstallError(
                f"support class {name!r} is in neither firmware nor microcode"
            )
        records.append(
            InstalledPackage(
                name=name,
                version=version,
                architecture=architecture,
                sha256=digest,
                kind=kind,
            )
        )
    known = {name for name, _v, _a, _d in seams.support_classes}
    if not firmware_names <= known or not microcode_names <= known:
        raise FreshAbInstallError("support package selection references unmanifested packages")
    provided_firmware = frozenset(
        name for name, _v, _a, _d in seams.support_classes if name in firmware_names
    )
    provided_microcode = frozenset(
        name for name, _v, _a, _d in seams.support_classes if name in microcode_names
    )
    return ReleaseSupportSet(
        support_digest=seams.support_digest,
        support_size=seams.support_size,
        installed_size_bound=seams.support_installed_bound,
        provided_firmware=provided_firmware,
        provided_microcode=provided_microcode,
        packages=tuple(sorted(records, key=lambda item: item.name)),
    )


def _fresh_identities(request: FreshAbInstallRequest) -> dict[str, dict[str, str]]:
    if request.fresh_identities is None:
        try:
            return mint_fresh_partition_identities()
        except LayoutError as exc:
            raise FreshAbInstallError(f"layout identities are not authoritative: {exc}") from exc
    try:
        minted = {
            role: dict(values) for role, values in dict(request.fresh_identities).items()
        }
    except (TypeError, ValueError, AttributeError) as exc:
        raise FreshAbInstallError(f"layout identities are not authoritative: {exc}") from exc
    if set(minted) != {"system-a", "system-b", "persist"}:
        raise FreshAbInstallError("layout identities must cover system-a/system-b/persist")
    seen: list[str] = []
    for role in ("system-a", "system-b", "persist"):
        entry = minted[role]
        if set(entry) != {"partuuid", "filesystem_uuid"}:
            raise FreshAbInstallError(f"layout identity {role} must hold partuuid/filesystem_uuid")
        for key in ("partuuid", "filesystem_uuid"):
            try:
                normalized = str(uuid.UUID(str(entry[key])))
            except (ValueError, AttributeError) as exc:
                raise FreshAbInstallError(
                    f"layout identity {role}.{key} is not a valid UUID"
                ) from exc
            if normalized != normalized.lower():
                raise FreshAbInstallError(f"layout identity {role}.{key} must be canonical lowercase")
            minted[role][key] = normalized
            seen.append(normalized)
    if len(set(seen)) != len(seen):
        raise FreshAbInstallError("layout partition identities must be unique across roles")
    return minted


def _write_boot_control_config(boot_control_dir: Path, text: str) -> None:
    location = Path(boot_control_dir)
    if not location.is_absolute():
        raise FreshAbInstallError("boot-control dir must be an absolute path")
    if os.path.islink(location):
        raise FreshAbInstallError("boot-control dir may not be a symbolic link")
    try:
        location.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise FreshAbInstallError(f"boot-control dir is not writable: {exc}") from exc
    target = location / GRUB_CONFIG_NAME
    if target.is_symlink():
        raise FreshAbInstallError("installed GRUB config may not be a symbolic link")
    payload = text.encode("utf-8")
    if not payload or len(payload) > 256 * 1024:
        raise FreshAbInstallError("installed GRUB config exceeds Greia bounds")
    import tempfile as _tempfile

    descriptor, temporary_name = _tempfile.mkstemp(
        prefix=".grub.cfg.", dir=str(location)
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o644)
        os.replace(temporary_name, target)
        try:
            descriptor_dir = os.open(str(location), os.O_RDONLY | os.O_DIRECTORY)
        except OSError:
            descriptor_dir = None
        if descriptor_dir is not None:
            try:
                os.fsync(descriptor_dir)
            finally:
                os.close(descriptor_dir)
    finally:
        try:
            Path(temporary_name).unlink(missing_ok=True)
        except OSError:
            pass
    try:
        if target.read_bytes() != payload:
            raise FreshAbInstallError("installed GRUB config re-read mismatch")
    except OSError as exc:
        raise FreshAbInstallError(f"installed GRUB config is not readable: {exc}") from exc


class _closing:
    """Close a binary stream after the writer consumed it (no-op on fakes)."""

    def __init__(self, stream: BinaryIO) -> None:
        self._stream = stream

    def __enter__(self) -> BinaryIO:
        return self._stream

    def __exit__(self, *exc: object) -> None:
        try:
            close = getattr(self._stream, "close", None)
            if callable(close):
                close()
        except Exception:
            pass


__all__ = [
    "GRUB_CONFIG_NAME",
    "AbExecutorFacts",
    "FreshAbInstallError",
    "FreshAbInstallRequest",
    "FreshAbInstallResult",
    "FreshAbInstallSeams",
    "PartitionRunner",
    "accept_first_install",
    "build_ab_executor",
    "execute_fresh_ab_install",
    "open_bundle_payload_stream",
]
