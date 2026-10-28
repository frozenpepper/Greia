"""Fresh v3-release install to SYSTEM_A (Phase 8B Step 8B.3 / X8-INSTALL).

The privileged ``greia-install-transaction`` service calls
:func:`execute_fresh_ab_install` after the narrow PREPARE/EXECUTE protocol
has consumed a single-use nonce and rematerialized every install fact from
Greia-owned service state (see :mod:`greia_installer.transaction_service`).
The installer UI never opens or writes raw disks: requests carry only an
identity digest plus bounded preference scalars, never paths, commands,
URLs, devices or partition numbers.

Flow on a disposable target (loop/QEMU image; D50 forbids Acer repartition
here):

1. verify the deterministic v3 release bundle (manifest v3 member order,
   canonical JSON, per-member digests, platform/family/profile compatibility
   with the service-owned expectation);
2. preflight the finalized-slot capacity bound
   (``max(base, minimum) + support + growth + reserve <= slot``) and prove
   the profile layout plan fits the verified target — both **before** the
   first destructive command;
3. create MBR A/B/PERSIST through the executable ``legacy-bios-ab-v1``
   adapter (argument arrays, ``shell=False`` by the caller's runner);
4. stream the v3 payload (`payload.ext4.zst` decompressed streaming, no
   uncompressed temp file) to ``SYSTEM_A`` only through the shared
   :class:`greia_platform.slot_writer.SlotWriter` (raw byte-count proof +
   readback, single-use write capability);
5. role-bind and finalize ``SYSTEM_A`` through the shared
   :class:`greia_platform.slot_writer.SlotFinalizer` (role UUID restore,
   release-bound support set, deterministic boot artifacts, receipt);
   ``SYSTEM_B`` is formatted empty by the adapter and never receives a
   payload stream or a finalization — no second-slot duplication;
6. initialize PERSIST exactly once (layout authority record bound to the
   finalized-A receipt, versioned namespace schema, transaction root);
7. install BIOS GRUB core/modules on the verified shared boot-control volume,
   then write its fixed two-entry config and ``grubenv`` with default ``A``;
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
from dataclasses import dataclass, replace
from pathlib import Path
from typing import BinaryIO, Callable, Mapping, Sequence

from greia_platform import session04_serial_diag
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
from greia_platform.persistent_layout import (
    InstalledLayoutRecord,
    PersistentNamespaceMap,
)
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
    MANIFEST_NAME,
    MAX_MANIFEST_BYTES,
    MAX_PAYLOAD_BYTES,
    PAYLOAD_NAME,
    SystemUpdateError,
    UpdateBundleError,
    inspect_update_bundle,
)

from .disk import DeviceObservation, DiskProbeError, partition_number_path
from .install_progress import InstallProgressSink
from .layout import (
    LayoutError,
    LayoutPlan,
    PostLayoutIdentityObserver,
    ProfileSizing,
    adapter_for,
    plan_for_profile,
    probe_partition_filesystem_uuid,
    require_finalized_slot_capacity,
    validate_observed_identities_against_plan,
)
from .persist import (
    FreshPersistSpec,
    PERSIST_FILESYSTEM,
    PersistError,
    initialize_fresh_persist,
    mount_verified_ext4_for_write,
    persist_transaction_path,
)


class FreshAbInstallError(RuntimeError):
    """Fresh A/B install refused or failed fail-closed (no partial accept)."""


_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

#: GRUB config and environment are stored on the shared boot-control volume.
GRUB_CONFIG_NAME = "grub.cfg"
GRUB_CONFIG_REL_PATH = "grub/grub.cfg"
#: Branding files copied beside the A/B config on the shared boot-control
#: volume. The GRUB theme is the same canonical white composition used by the
#: single-root appliance path and the early framebuffer cover.
GRUB_THEME_NAME = "greia-theme.txt"
GRUB_LOGO_NAME = "greia-boot-logo.png"
_BOOT_BRANDING_BOUNDS = (
    (GRUB_THEME_NAME, 64 * 1024),
    (GRUB_LOGO_NAME, 2 * 1024 * 1024),
)


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

    ``bundle_path`` is the unsigned deterministic ``.greiaupdate`` v3 release
    artifact (ADR 0036 §3). ``expected_*`` are the installer image's own
    compatibility facts: the manifest must match all three exactly.
    ``install_target_sha256`` is the
    authorized identity digest the privileged protocol rematerialized from a
    fresh probe (never a ``/dev`` path). ``fresh_identities`` is RETIRED
    (POSTR1-P2): production identity observation happens after the
    destructive partition/filesystem effects through the seams'
    ``post_layout_identity_observer``, never from caller-supplied
    pre-layout facts — any non-``None`` value is refused fail-closed so a
    blank target can never be satisfied with controlled identities.
    ``password_hash`` is the stored
    GRUB PBKDF2 token rendered into the fixed boot entries.
    """

    bundle_path: Path
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
    release payload byte stream (default reads the bundle's payload member);
    ``slot_filesystem_factory``/``package_installer_factory`` own the
    destination-slot finalization seam. ``persist_stage_dir`` and
    ``boot_control_dir`` are root-owned mountpoints. The GRUB config and
    environment are written onto the verified boot-control filesystem; the
    first-install journal is written into the canonical shared PERSIST
    transaction root (``/greia/boot-journal``), alongside the update journal.
    ``post_layout_identity_observer`` is the narrow post-layout seam the
    orchestrator invokes as ``observer(target, plan)`` only after
    ``adapter.execute`` has created the partition table and filesystems;
    it is required — production binds the real block observer, tests bind
    recording fakes behind the same seam, and it is never invoked before
    the first destructive command. ``bios_bootloader_installer`` receives
    the rematerialized whole-disk target and verified mounted boot-control
    directory after config/environment writes have been checked; production
    rechecks target identity immediately before installing GRUB.
    """

    partition_runner: PartitionRunner
    slot_storage_factory: Callable[[str], SlotStorage]
    slot_filesystem_factory: Callable[[], SlotFilesystem]
    package_installer_factory: Callable[[], SlotPackageInstaller]
    inventory_token: str
    support_digest: str | None
    support_size: int | None
    support_installed_bound: int
    support_classes: tuple[tuple[str, str, str, str], ...] = ()
    persist_runner: object = None
    persist_stage_dir: Path | None = None
    persist_uuid_factory: Callable[[], uuid.UUID] | None = None
    boot_control_dir: Path | None = None
    #: Live-installer directory carrying the canonical GRUB theme and logo.
    #: Production binds ``/boot/grub``; tests may bind a temp fixture. ``None``
    #: keeps source-only install fakes free of branding files.
    boot_branding_dir: Path | None = None
    firmware_packages: tuple[str, ...] = ()
    microcode_packages: tuple[str, ...] = ()
    payload_stream_factory: Callable[[], BinaryIO] | None = None
    inventory_complete: bool = True
    #: Resolver detection was incomplete and fallback firmware was selected
    #: (display-only note for the completion page).
    hardware_detection_incomplete: bool = False
    #: A Wi-Fi chip needs firmware/driver Greia cannot include (display-only).
    wifi_firmware_unavailable: bool = False
    post_layout_identity_observer: PostLayoutIdentityObserver | None = None
    bios_bootloader_installer: Callable[[DeviceObservation, Path], None] | None = None

    def __post_init__(self) -> None:
        _require_hex64(self.inventory_token, field_name="hardware inventory token")
        if (self.support_digest is None) != (self.support_size is None):
            raise FreshAbInstallError(
                "support digest/size must be present together or absent together"
            )
        if self.support_digest is not None:
            _require_hex64(self.support_digest, field_name="release support digest")
        if self.support_size is not None:
            if (
                isinstance(self.support_size, bool)
                or not isinstance(self.support_size, int)
                or self.support_size < 0
            ):
                raise FreshAbInstallError("support_size must be a non-negative integer")
        for field_name in ("support_installed_bound",):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise FreshAbInstallError(f"{field_name} must be a non-negative integer")
        if self.boot_branding_dir is not None:
            branding = Path(self.boot_branding_dir)
            if not branding.is_absolute() or branding.is_symlink():
                raise FreshAbInstallError(
                    "boot branding directory must be an absolute non-symlink path"
                )
        if self.post_layout_identity_observer is not None and not callable(
            self.post_layout_identity_observer
        ):
            raise FreshAbInstallError(
                "post-layout identity observer must be a callable observer"
            )
        if self.bios_bootloader_installer is not None and not callable(
            self.bios_bootloader_installer
        ):
            raise FreshAbInstallError("BIOS bootloader installer must be callable")


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FreshAbInstallResult:
    """Facts of a completed fresh install (SYSTEM_A finalized, B inactive)."""

    release_id: str
    layout_plan: LayoutPlan
    receipt: FinalizationReceipt
    record: InstalledLayoutRecord
    journal: BootTransactionJournal
    grub_config_text: str
    bytes_written: int


# ---------------------------------------------------------------------------
# Bundle payload stream (live ZIP member stream, bounded working memory)
# ---------------------------------------------------------------------------


class BundlePayloadStream:
    """Live streaming view over the bundle's v3 payload member (D33).

    The owning :class:`zipfile.ZipFile` lifetime spans the whole writer
    consumption: the archive stays open until this stream is closed, so the
    shared :class:`SlotWriter` pulls bounded chunks straight from the ZIP
    member with no full uncompressed ``payload.ext4.zst`` allocation and no
    second extracted copy on disk. Manifest-declared uncompressed size is
    bounded at open time (live ``ZipInfo.file_size`` must equal the
    manifest ``payload.size`` and the optional ``expected_size``); stream
    errors surface as :class:`FreshAbInstallError` (transaction failure).
    Hash/readback ownership stays with ``SlotWriter`` — this object only
    transports bytes. Unbounded ``read()`` (no size) is refused so an
    accidental whole-buffering call fails closed instead of allocating
    payload-scale RAM.
    """

    def __init__(
        self,
        archive: zipfile.ZipFile,
        handle: BinaryIO,
        expected_bytes: int,
    ) -> None:
        self._archive = archive
        self._handle = handle
        self._expected_bytes = expected_bytes
        self._closed = False

    # -- BinaryIO surface used by SlotWriter ---------------------------------
    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return False

    @property
    def closed(self) -> bool:
        return self._closed

    def read(self, size: int = -1) -> bytes:
        if self._closed:
            raise FreshAbInstallError("release payload stream is closed")
        if size is None or not isinstance(size, int) or size < 0:
            raise FreshAbInstallError(
                "unbounded payload read refused; streaming reads must be bounded"
            )
        if size == 0:
            return b""
        try:
            data = self._handle.read(size)
        except FreshAbInstallError:
            raise
        except (zipfile.BadZipFile, OSError) as exc:
            raise FreshAbInstallError(
                f"release payload stream failed: {exc}"
            ) from exc
        except Exception as exc:
            raise FreshAbInstallError(
                f"release payload stream failed: {exc}"
            ) from exc
        if data is None:
            return b""
        if not isinstance(data, (bytes, bytearray)):
            raise FreshAbInstallError("release payload stream must yield bytes")
        return bytes(data)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            try:
                self._handle.close()
            except Exception:
                pass
        finally:
            try:
                self._archive.close()
            except Exception:
                pass

    def __enter__(self) -> "BundlePayloadStream":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def __del__(self) -> None:  # pragma: no cover - deterministic close is explicit
        try:
            self.close()
        except Exception:
            pass


def _manifest_payload_size(archive: zipfile.ZipFile) -> int:
    """Read the manifest-declared payload size from an open bundle (small)."""
    try:
        info = archive.getinfo(MANIFEST_NAME)
    except KeyError as exc:
        raise FreshAbInstallError("release bundle carries no manifest") from exc
    if info.file_size <= 0 or info.file_size > MAX_MANIFEST_BYTES:
        raise FreshAbInstallError("release manifest exceeds Greia bounds")
    try:
        raw = archive.read(MANIFEST_NAME)
    except (zipfile.BadZipFile, OSError) as exc:
        raise FreshAbInstallError(f"release manifest is not readable: {exc}") from exc
    import json as _json

    try:
        document = _json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise FreshAbInstallError(f"release manifest is not valid JSON: {exc}") from exc
    try:
        payload = document["payload"]
        size = payload["size"]
    except (KeyError, TypeError) as exc:
        raise FreshAbInstallError("release manifest payload object is invalid") from exc
    if isinstance(size, bool) or not isinstance(size, int):
        raise FreshAbInstallError("release manifest payload size must be an integer")
    return size


def open_bundle_payload_stream(
    bundle_path: Path, *, expected_size: int | None = None
) -> BinaryIO:
    """Open a live read-only stream over the bundle's v3 payload member.

    The returned stream owns both the ZIP member handle and the archive:
    the archive stays open until the caller closes the stream (the
    orchestrator's ``_closing`` wrapper does this deterministically on both
    success and failure), so :class:`SlotWriter` consumes bounded chunks
    with no whole-payload RAM allocation and no extracted second copy.
    The live ``ZipInfo.file_size`` is bounded against ``MAX_PAYLOAD_BYTES``
    and must equal the manifest-declared ``payload.size`` (plus the optional
    ``expected_size`` from the already-verified release member) before the
    caller writes anything.
    """
    location = Path(bundle_path)
    if location.is_symlink() or not location.is_file():
        raise FreshAbInstallError("release bundle is not a regular file")
    try:
        archive = zipfile.ZipFile(location, "r")
    except (zipfile.BadZipFile, OSError) as exc:
        raise FreshAbInstallError(f"release bundle is not readable: {exc}") from exc
    try:
        try:
            info = archive.getinfo(PAYLOAD_NAME)
        except KeyError as exc:
            raise FreshAbInstallError(
                f"release bundle carries no v3 payload: {exc}"
            ) from exc
        if info.file_size <= 0 or info.file_size > MAX_PAYLOAD_BYTES:
            raise FreshAbInstallError("release payload size is outside Greia bounds")
        declared = _manifest_payload_size(archive)
        if declared <= 0 or declared > MAX_PAYLOAD_BYTES:
            raise FreshAbInstallError("release manifest payload size is outside Greia bounds")
        if info.file_size != declared:
            raise FreshAbInstallError("payload size does not match manifest")
        if expected_size is not None:
            if (
                isinstance(expected_size, bool)
                or not isinstance(expected_size, int)
                or expected_size <= 0
            ):
                raise FreshAbInstallError("expected payload size is outside Greia bounds")
            if info.file_size != expected_size:
                raise FreshAbInstallError(
                    "payload size does not match the verified release member"
                )
        try:
            handle = archive.open(PAYLOAD_NAME, "r")
        except (KeyError, zipfile.BadZipFile, OSError) as exc:
            raise FreshAbInstallError(
                f"release bundle carries no v3 payload: {exc}"
            ) from exc
        return BundlePayloadStream(archive, handle, info.file_size)
    except Exception:
        try:
            archive.close()
        except Exception:
            pass
        raise


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def _s04_diag_stage(name: str) -> None:
    """TEMPORARY Session-04 diagnostic; removed before Session 04 closure.

    Delegates to :mod:`greia_platform.session04_serial_diag`, which owns the
    marker-gated serial emit, so the orchestrator carries no device surface.
    """
    session04_serial_diag.emit_stage(name)


def execute_fresh_ab_install(
    request: FreshAbInstallRequest,
    seams: FreshAbInstallSeams,
    *,
    now_unix: int | None = None,
    progress: InstallProgressSink | None = None,
) -> FreshAbInstallResult:
    """Verify, partition, stream/finalize A, init PERSIST, install GRUB, journal.

    Every refusal raises :class:`FreshAbInstallError` with zero acceptance:
    in particular the finalized-slot capacity preflight, release/
    compatibility/support binding and layout-fit proof all run **before**
    the first destructive partition command, and ``SYSTEM_B`` storage is
    never addressed.

    ``progress`` (optional, display only) receives the parent-visible phase
    at each milestone, and measured byte counts while ``SYSTEM_A`` is
    streamed and read back (see :class:`_ProgressSlotStorage`). It observes
    the transaction; it never changes an order, a check or a bound.
    """
    report = _phase_reporter(progress)
    if not isinstance(request, FreshAbInstallRequest):
        raise FreshAbInstallError("fresh install requires a typed install request")
    if not isinstance(seams, FreshAbInstallSeams):
        raise FreshAbInstallError("fresh install requires typed install seams")
    for field_name in (
        "persist_stage_dir",
        "boot_control_dir",
    ):
        if getattr(seams, field_name) is None:
            raise FreshAbInstallError(f"install seams carry no {field_name}")
    if seams.persist_runner is None:
        raise FreshAbInstallError("install seams carry no PERSIST runner")
    if request.target.device_type != "disk":
        raise FreshAbInstallError("fresh install requires a whole-disk target")

    # -- 1. Verified deterministic v3 release only ---------------------
    report("check")
    try:
        inspected = inspect_update_bundle(request.bundle_path)
    except (UpdateBundleError, SystemUpdateError) as exc:
        raise FreshAbInstallError(f"release bundle is not a verified Greia release: {exc}") from exc
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
        raise FreshAbInstallError(f"release facts are not installable: {exc}") from exc
    _s04_diag_stage("inspected")

    # -- Release-bound support set (finalizer re-checks digest binding) -----
    # v3 hardware support is optional: absent manifest facts require absent
    # seam facts (None together), present facts must match exactly.
    if seams.support_digest != member.hardware_support_sha256:
        raise FreshAbInstallError("support set is not the release-bound support member")
    if seams.support_size != member.hardware_support_size:
        raise FreshAbInstallError("support set size is not the release-bound member size")
    # The seams bound is derived post-inventory from the verified pool for
    # exactly the machine-selected firmware/microcode, while the request
    # facts predate inventory (image-authorized whole-pool ceiling). The
    # selected bound must fit inside the authorized ceiling; anything else
    # means the facts and the machine selection disagree about the release
    # support, and the capacity preflight below must not run on either
    # number alone.
    if not isinstance(seams.support_installed_bound, int) or isinstance(
        seams.support_installed_bound, bool
    ):
        raise FreshAbInstallError("support installed-size bound is not authoritative")
    if not isinstance(request.support_installed_bytes, int) or isinstance(
        request.support_installed_bytes, bool
    ):
        raise FreshAbInstallError("request support installed-size bound is not authoritative")
    if seams.support_installed_bound < 0 or request.support_installed_bytes < 0:
        raise FreshAbInstallError("support installed-size bound is not authoritative")
    if seams.support_installed_bound > request.support_installed_bytes:
        raise FreshAbInstallError("support installed-size bound exceeds the authorized release bound")
    _s04_diag_stage("support-bound")
    try:
        support = _support_set_from_seams(seams)
    except SlotFinalizeError as exc:
        raise FreshAbInstallError(f"support set is not installable: {exc}") from exc

    # -- 2. Capacity + layout-fit preflight BEFORE any destructive command --
    # Proved on the machine-selected bound (verified pool + inventory
    # selection), already ceiling-checked against the image-authorized
    # facts above — never on the whole-pool total the release carries.
    try:
        require_finalized_slot_capacity(
            slot_bytes=int(request.sizing.slot_bytes),
            base_bytes=member.payload_uncompressed_bytes,
            minimum_slot_bytes=member.minimum_slot_bytes,
            support_installed_bytes=seams.support_installed_bound,
        )
        plan = plan_for_profile(
            request.sizing, device_size_bytes=int(request.target.size_bytes)
        )
    except (LayoutError, SlotWriteError) as exc:
        raise FreshAbInstallError(f"release does not fit this target: {exc}") from exc
    if plan.boot_backend != request.sizing.boot_backend:
        raise FreshAbInstallError("layout boot backend does not match the profile sizing")
    _s04_diag_stage("capacity-planned")

    # -- Post-layout observer wiring (checked BEFORE destruction) ---------
    # Caller-supplied pre-layout identities are retired: a blank target
    # cannot satisfy them, and trusting them would let a harness fabricate
    # MBR PARTUUID authority. The observer below runs only after
    # ``adapter.execute`` creates the identities.
    if request.fresh_identities is not None:
        raise FreshAbInstallError(
            "fresh install no longer accepts caller-supplied partition "
            "identities; production observation happens after partitioning "
            "through the post-layout identity observer"
        )
    observer = seams.post_layout_identity_observer
    if observer is None or not callable(observer):
        raise FreshAbInstallError(
            "fresh install requires a post-layout identity observer; "
            "minting an independent UUID4 is retired"
        )
    bios_bootloader_installer = seams.bios_bootloader_installer
    if request.sizing.boot_backend == "grub-ab-v1" and (
        bios_bootloader_installer is None
        or not callable(bios_bootloader_installer)
    ):
        raise FreshAbInstallError(
            "fresh BIOS A/B install requires a bootloader installer seam; refusing to erase"
        )
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
            architecture=manifest.architecture,
            platform_family=manifest.platform_family,
            profile=manifest.profile,
            version=manifest.version,
        )
    except (SlotWriteError, SlotFinalizeError) as exc:
        raise FreshAbInstallError(f"install policy facts are not authoritative: {exc}") from exc

    # ARM boot media and tryboot finalization must be executable *before*
    # formatting the child's card. Pi layout commands are source-ready, but
    # live ARM boot/payload and firmware/tryboot staging are not yet wired
    # into this transaction. Until those dependencies are present this check
    # is deliberately before the first destructive effect. NEVER let a Pi
    # request fall through to the x86 GRUB implementation below.
    if request.sizing.boot_backend != "grub-ab-v1":
        raise FreshAbInstallError(
            "Pi installation unavailable: native firmware boot staging and "
            "ARM setup media are not implemented; refusing to erase the card"
        )

    # -- 3. First destructive commands: MBR A/B/PERSIST --------------------
    report("partition")
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
    _s04_diag_stage("partitioned")

    # -- 3b. Observe + bind identities AFTER the layout effects -----------
    # MBR PARTUUID authority is observed from the partitioned target, never
    # minted/predicted: the observer settles/rescans through the block
    # layer (partprobe + udevadm settle + role mkfs already ran inside
    # ``adapter.execute``) and returns the actual disk signature, role
    # PARTUUIDs and filesystem UUIDs. Any observation failure aborts here,
    # before a single SYSTEM_A payload byte is written.
    try:
        raw_observed = observer(request.target, plan)
    except FreshAbInstallError:
        raise
    except LayoutError as exc:
        raise FreshAbInstallError(
            f"post-layout identity observation refused: {exc}"
        ) from exc
    except Exception as exc:
        raise FreshAbInstallError(
            f"post-layout identity observation is not authoritative: {exc}"
        ) from exc
    observed = _bind_post_layout_identities(plan, raw_observed)
    try:
        observed_persist_uuid = str(
            uuid.UUID(str(observed["persist"]["filesystem_uuid"]))
        )
        if seams.persist_uuid_factory is not None:
            try:
                supplied_persist_uuid = str(uuid.UUID(str(seams.persist_uuid_factory())))
            except (ValueError, AttributeError, TypeError) as exc:
                raise FreshAbInstallError(
                    "PERSIST UUID seam is not a valid observed identity"
                ) from exc
            if supplied_persist_uuid != observed_persist_uuid:
                raise FreshAbInstallError(
                    "PERSIST UUID seam disagrees with the post-layout observation"
                )
        boot_control_part = plan.by_role("boot-control")
        if boot_control_part is None or boot_control_part.filesystem != PERSIST_FILESYSTEM:
            raise FreshAbInstallError(
                "layout plan carries no ext4 boot-control partition"
            )
        boot_control_node = partition_number_path(
            request.target.path, boot_control_part.number
        )
        boot_control_uuid = probe_partition_filesystem_uuid(
            seams.persist_runner, boot_control_node  # type: ignore[arg-type]
        )
        observed_uuids = {
            values["filesystem_uuid"] for values in observed.values()
        }
        if boot_control_uuid in observed_uuids:
            raise FreshAbInstallError(
                "boot-control filesystem UUID is cloned from another layout role"
            )
        policy = replace(
            policy,
            persist_filesystem_uuid=observed_persist_uuid,
            boot_control_filesystem_uuid=boot_control_uuid,
        )
    except FreshAbInstallError:
        raise
    except (DiskProbeError, LayoutError) as exc:
        raise FreshAbInstallError(
            f"post-layout boot-control identity is not authoritative: {exc}"
        ) from exc
    except (SlotFinalizeError, ValueError) as exc:
        raise FreshAbInstallError(
            f"post-layout boot-control identity is not authoritative: {exc}"
        ) from exc
    _s04_diag_stage("identities-bound")

    # -- 4./5. Stream + finalize SYSTEM_A only (B never addressed) ---------
    destination_a = DestinationSlot(
        semantic_slot="A",
        role="system-a",
        slot_capacity_bytes=int(request.sizing.slot_bytes),
        active_slot=None,
        accepted_slot=None,
        layout_id=request.sizing.layout_adapter_id,
        role_filesystem_uuid=observed["system-a"]["filesystem_uuid"],
        other_role_filesystem_uuid=observed["system-b"]["filesystem_uuid"],
    )
    try:
        storage = seams.slot_storage_factory("A")
    except (SlotWriteError, FreshAbInstallError) as exc:
        raise FreshAbInstallError(f"SYSTEM_A slot store is not authoritative: {exc}") from exc
    except Exception as exc:
        raise FreshAbInstallError(f"SYSTEM_A slot store is not authoritative: {exc}") from exc
    if progress is not None:
        report("copy")
        storage = _ProgressSlotStorage(
            storage, progress, total_bytes=member.payload_uncompressed_bytes
        )
    writer = SlotWriter()
    stream_factory = seams.payload_stream_factory or (
        lambda: open_bundle_payload_stream(
            request.bundle_path, expected_size=member.payload_size
        )
    )
    try:
        source = stream_factory()
    except FreshAbInstallError:
        raise
    except Exception as exc:
        raise FreshAbInstallError(f"release payload stream is not readable: {exc}") from exc
    try:
        from greia_platform.slot_writer import (
            SlotWriteError as _SlotWriteError,
            open_zstd_decompressed_stream,
        )

        with _closing(source):
            try:
                decompressed = open_zstd_decompressed_stream(source)
            except _SlotWriteError as exc:
                raise FreshAbInstallError(f"payload decompression refused: {exc}") from exc
            try:
                write = writer.write(
                    member=member,
                    destination=destination_a,
                    source=decompressed,
                    storage=storage,
                    support_installed_bytes=seams.support_installed_bound,
                )
            finally:
                closer = getattr(decompressed, "close", None)
                if callable(closer):
                    try:
                        closer()
                    except Exception:
                        pass
    except FreshAbInstallError:
        raise
    except SlotWriteError as exc:
        raise FreshAbInstallError(f"SYSTEM_A streaming refused: {exc}") from exc
    except (zipfile.BadZipFile, OSError) as exc:
        raise FreshAbInstallError(f"SYSTEM_A streaming failed: {exc}") from exc
    except Exception as exc:
        raise FreshAbInstallError(f"SYSTEM_A streaming failed: {exc}") from exc
    _s04_diag_stage("streamed")
    report("setup")
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
            support_installed_bytes=seams.support_installed_bound,
        )
    except (SlotFinalizeError, SlotWriteError) as exc:
        raise FreshAbInstallError(f"SYSTEM_A finalization refused: {exc}") from exc
    if receipt.slot != "A":
        raise FreshAbInstallError("finalization receipt does not bind SYSTEM_A")
    _s04_diag_stage("finalized")

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
        slot_bytes=int(request.sizing.slot_bytes),
        system_a=dict(observed["system-a"]),
        system_b=dict(observed["system-b"]),
        persist_partuuid=observed["persist"]["partuuid"],
    )
    # The layout adapter already created PERSIST and the post-layout
    # observer read back its UUID. Reuse that observed identity exactly;
    # the optional seam is only a consistency assertion for test harnesses.
    persist_uuid_factory = lambda: uuid.UUID(observed_persist_uuid)
    journal_holder: list[BootTransactionJournal] = []

    def _initialize_first_install_journal(
        persist_root: Path,
        _record: InstalledLayoutRecord,
        _namespace_map: PersistentNamespaceMap,
    ) -> None:
        # The installer initializer already created this canonical
        # transaction root on the PERSIST filesystem. It is also the runtime
        # first-install boot-health journal, so do not create a second
        # namespace-backed journal tree beside it.
        journal_dir = persist_transaction_path(persist_root)
        if (
            journal_dir.is_symlink()
            or not journal_dir.is_dir()
            or any(journal_dir.iterdir())
        ):
            raise FreshAbInstallError(
                "canonical first-install journal root is not empty fresh PERSIST state"
            )
        try:
            os.chmod(journal_dir, 0o700)
            journal = BootTransactionJournal.begin_first_install(
                journal_dir,
                layout_id=request.sizing.layout_adapter_id,
                boot_backend=request.sizing.boot_backend,
                release_id=member.release_id,
            )
        except (BootTransactionError, OSError) as exc:
            raise FreshAbInstallError(
                f"first-install journal refused: {exc}"
            ) from exc
        journal_holder.append(journal)

    try:
        persist_result = initialize_fresh_persist(
            target=request.target,
            plan=plan,
            spec=spec,
            mountpoint=Path(seams.persist_stage_dir),
            runner=seams.persist_runner,  # type: ignore[arg-type]
            uuid_factory=persist_uuid_factory,  # type: ignore[arg-type]
            after_initialize=_initialize_first_install_journal,
        )
    except PersistError as exc:
        raise FreshAbInstallError(f"PERSIST initialization refused: {exc}") from exc
    record = persist_result.record
    if record.accepted_slot != "A" or record.boot_control.active_slot != "A":
        raise FreshAbInstallError("layout authority does not boot-accept SYSTEM_A")
    if record.system_b is None:
        raise FreshAbInstallError("A/B layout authority requires the inactive SYSTEM_B identity")
    if len(journal_holder) != 1:
        raise FreshAbInstallError(
            "fresh PERSIST did not produce exactly one first-install journal"
        )
    journal = journal_holder[0]
    _s04_diag_stage("persist-done")

    # -- 7. Stable GRUB backend (fixed entries + grubenv default A) --------
    report("bootloader")
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
        _write_verified_boot_control(
            runner=seams.persist_runner,
            device=boot_control_node,
            filesystem_uuid=boot_control_uuid,
            mountpoint=Path(seams.boot_control_dir),
            grub_text=grub_text,
            branding_dir=seams.boot_branding_dir,
            target=request.target,
            bios_bootloader_installer=bios_bootloader_installer,
        )
    except (BootTransactionError, GrubAbConfigError, OSError) as exc:
        raise FreshAbInstallError(f"boot backend install failed: {exc}") from exc
    _s04_diag_stage("grub-done")

    # -- 8. FIRST_INSTALL_PENDING is already durable on PERSIST (step 6) ---
    if journal.state is not BootTransactionState.FIRST_INSTALL_PENDING:
        raise FreshAbInstallError("first-install journal is not pending acceptance")
    _s04_diag_stage("journal-done")
    report("complete")

    return FreshAbInstallResult(
        release_id=member.release_id,
        layout_plan=plan,
        receipt=receipt,
        record=record,
        journal=journal,
        grub_config_text=grub_text,
        bytes_written=member.payload_uncompressed_bytes,
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
    environment — never from UI request bytes.     ``install`` builds the typed
    :class:`FreshAbInstallRequest` from the revalidated authorization
    (identity digest), the service-held settings snapshot outcome and the
    rematerialized target, then runs :func:`execute_fresh_ab_install`
    through the bound seam factories. Observed partition identities arrive
    per ``EXECUTE`` through the executor's post-layout ``identities_factory``
    observer (invoked by the orchestrator with ``(target, plan)`` only
    after the partition/filesystem effects exist), never from UI request
    bytes and never from a mint.
    """

    bundle_path: Path
    expected_profile_id: str
    expected_platform_family: str
    expected_architecture: str
    sizing: ProfileSizing
    support_installed_bytes: int
    password_hash: str
    developer: bool = False

    def __post_init__(self) -> None:
        _require_regular_file(self.bundle_path, field_name="release bundle")
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
    *,
    identities_factory: (
        Callable[
            [DeviceObservation, LayoutPlan], Mapping[str, Mapping[str, str]]
        ]
        | None
    ) = None,
):
    """Bind service-owned facts into an :attr:`ab_executor` callable.

    ``seams_factory`` receives the rematerialized target and returns the
    fully bound seams (partition/persist runners, slot storage/filesystem,
    staging dirs, journal/backend dirs, support/inventory facts).
    ``identities_factory`` is the post-layout identity observer: the
    orchestrator invokes it as ``observer(target, plan)`` only after
    ``adapter.execute`` has created the partition table and filesystems,
    then binds the result through the T1 validators plus the
    partition-number gate (MBR ``<disk-signature>-<NN>`` via the T1-IDENT
    normalizer, GPT canonical GUIDs). It is required — a missing observer
    refuses fail-closed before any destructive work instead of minting an
    independent UUID4 — and it is never invoked before partitioning. The
    returned executor takes ``(authorization, settings, locale, target)``
    from :meth:`InstallTransactionService.execute_ab_install` and returns
    an install result object; any refusal raises fail-closed.
    """
    if not isinstance(facts, AbExecutorFacts):
        raise FreshAbInstallError("A/B executor requires typed service facts")
    if not callable(seams_factory):
        raise FreshAbInstallError("A/B executor requires a seam factory")
    if identities_factory is not None and not callable(identities_factory):
        raise FreshAbInstallError("A/B executor requires an observed-identity factory")

    def _execute(  # type: ignore[no-untyped-def]
        authorization: object,
        settings: object,
        locale: object,
        target: DeviceObservation,
        progress: InstallProgressSink | None = None,
    ):
        identity = getattr(authorization, "target_identity", "")
        _require_hex64(identity, field_name="install target identity")
        if not isinstance(target, DeviceObservation):
            raise FreshAbInstallError("A/B executor requires a rematerialized target")
        seams = seams_factory(target)
        if not isinstance(seams, FreshAbInstallSeams):
            raise FreshAbInstallError("A/B seam factory returned no install seams")
        observer = identities_factory or seams.post_layout_identity_observer
        if observer is None or not callable(observer):
            raise FreshAbInstallError(
                "A/B executor requires a post-layout identity observer; "
                "minting an independent UUID4 is retired"
            )
        # Bind the post-layout observer without invoking it: the
        # orchestrator calls it only after the partition/filesystem
        # effects exist, never before the first destructive command.
        seams.post_layout_identity_observer = observer  # type: ignore[union-attr]
        request = FreshAbInstallRequest(
            bundle_path=facts.bundle_path,
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
        result = execute_fresh_ab_install(request, seams, progress=progress)
        return _InstallResultShim(
            release_id=result.release_id,
            hardware_detection_incomplete=seams.hardware_detection_incomplete,
            wifi_firmware_unavailable=seams.wifi_firmware_unavailable,
        )

    # Read by InstallTransactionService.execute_ab_install: this executor
    # takes the optional display-only progress sink.
    _execute.accepts_progress = True  # type: ignore[attr-defined]
    return _execute


@dataclass(frozen=True, slots=True)
class _InstallResultShim:
    """Minimal install-result carrying the accepted release identity."""

    release_id: str
    hardware_detection_incomplete: bool = False
    wifi_firmware_unavailable: bool = False


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


def _phase_reporter(progress: InstallProgressSink | None) -> Callable[[str], None]:
    """Milestone reporter that can never raise into the transaction."""

    def report(phase_id: str) -> None:
        if progress is None:
            return
        try:
            progress.phase(phase_id)
        except Exception:  # noqa: BLE001 - display data never stops an install
            pass

    return report


class _ProgressSlotStorage:
    """Byte-counting view of the ``SYSTEM_A`` slot store (display only).

    Forwards the :class:`SlotStorage` protocol unchanged to the real store
    and reports measured progress: bytes written are the ``copy`` phase,
    bytes read back by :class:`SlotWriter`'s integrity readback are the
    ``verify`` phase, both against the manifest's uncompressed size. The
    reporter rate-limits; this object only counts. A reporting failure is
    swallowed so it can never turn into a write or readback failure.
    """

    def __init__(self, inner: SlotStorage, progress: InstallProgressSink, *, total_bytes: int) -> None:
        self._inner = inner
        self._progress = progress
        self._total = max(1, int(total_bytes))
        self._written = 0
        self._read = 0

    @property
    def capacity_bytes(self) -> int:
        return self._inner.capacity_bytes

    def write_at(self, offset: int, data: bytes) -> None:
        self._inner.write_at(offset, data)
        self._written = min(self._total, self._written + len(data))
        self._report("copy", self._written)

    def read_at(self, offset: int, length: int) -> bytes:
        data = self._inner.read_at(offset, length)
        self._read = min(self._total, self._read + len(data))
        self._report("verify", self._read)
        return data

    def flush(self) -> None:
        self._inner.flush()

    def _report(self, phase_id: str, done: int) -> None:
        try:
            self._progress.phase(phase_id, done_bytes=done, total_bytes=self._total)
        except Exception:  # noqa: BLE001 - display data never stops an install
            pass


def _bind_post_layout_identities(
    plan: LayoutPlan,
    raw: Mapping[str, Mapping[str, str]],
) -> dict[str, dict[str, str]]:
    """Bind observer-returned post-layout identities to the validated plan.

    Thin orchestrator wrapper over
    :func:`greia_installer.layout.validate_observed_identities_against_plan`:
    the T1 typed validators (``normalize_partuuid_for_scheme``,
    ``split_mbr_partuuid``, cross-disk/uniqueness checks) plus the
    adapter-declared partition-number binding are owned there, so a minted
    UUID4 labeled as an MBR PARTUUID, a cross-disk mix, a swapped
    partition number, or any cloned identity is refused here — after
    partitioning, before any ``SYSTEM_A`` payload byte. Failures surface
    as :class:`FreshAbInstallError` (orchestrator authority).
    """
    try:
        return validate_observed_identities_against_plan(
            plan=plan, identities=raw
        )
    except LayoutError as exc:
        raise FreshAbInstallError(
            f"observed layout identities are not authoritative: {exc}"
        ) from exc


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
    grub_directory = location / "grub"
    if grub_directory.is_symlink():
        raise FreshAbInstallError("boot-control GRUB directory may not be a symbolic link")
    try:
        grub_directory.mkdir(mode=0o755, exist_ok=True)
    except OSError as exc:
        raise FreshAbInstallError(f"boot-control GRUB directory is not writable: {exc}") from exc
    if not grub_directory.is_dir():
        raise FreshAbInstallError("boot-control GRUB path is not a directory")
    target = location / GRUB_CONFIG_REL_PATH
    if target.is_symlink():
        raise FreshAbInstallError("installed GRUB config may not be a symbolic link")
    payload = text.encode("utf-8")
    if not payload or len(payload) > 256 * 1024:
        raise FreshAbInstallError("installed GRUB config exceeds Greia bounds")
    import tempfile as _tempfile

    descriptor, temporary_name = _tempfile.mkstemp(
        prefix=".grub.cfg.", dir=str(target.parent)
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o644)
        os.replace(temporary_name, target)
        try:
            descriptor_dir = os.open(str(target.parent), os.O_RDONLY | os.O_DIRECTORY)
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


def _atomic_write_boot_control_file(target: Path, payload: bytes) -> None:
    """Write one boot-control asset atomically with verified readback."""
    import tempfile as _tempfile

    if target.is_symlink():
        raise FreshAbInstallError(f"boot-control asset may not be a symlink: {target.name}")
    descriptor, temporary_name = _tempfile.mkstemp(
        prefix=f".{target.name}.", dir=str(target.parent)
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o644)
        os.replace(temporary_name, target)
        try:
            descriptor_dir = os.open(str(target.parent), os.O_RDONLY | os.O_DIRECTORY)
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
            raise FreshAbInstallError(
                f"boot-control asset re-read mismatch: {target.name}"
            )
    except OSError as exc:
        raise FreshAbInstallError(
            f"boot-control asset is not readable: {target.name}: {exc}"
        ) from exc


def _copy_boot_branding(branding_dir: Path, grub_dir: Path) -> None:
    """Copy the canonical GRUB theme and logo onto the boot-control volume.

    The A/B entries live on the shared boot-control partition, not in either
    system slot. GRUB can only show the branded frame when the theme and its
    image are present beside ``grub.cfg``. Source files are the live-installer
    canonical copies; every file is bounded, regular (never a symlink) and
    read back after an atomic write.
    """
    source_dir = Path(branding_dir)
    if (
        not source_dir.is_absolute()
        or source_dir.is_symlink()
        or not source_dir.is_dir()
    ):
        raise FreshAbInstallError("boot branding source is not an absolute directory")
    destination = Path(grub_dir)
    if destination.is_symlink() or not destination.is_dir():
        raise FreshAbInstallError("boot-control GRUB directory is unusable")
    for name, limit in _BOOT_BRANDING_BOUNDS:
        source = source_dir / name
        if source.is_symlink() or not source.is_file():
            raise FreshAbInstallError(f"boot branding file is missing or unsafe: {name}")
        try:
            payload = source.read_bytes()
        except OSError as exc:
            raise FreshAbInstallError(f"boot branding file is unreadable: {name}: {exc}") from exc
        if not payload or len(payload) > limit:
            raise FreshAbInstallError(f"boot branding file is outside Greia bounds: {name}")
        _atomic_write_boot_control_file(destination / name, payload)


def _write_verified_boot_control(
    *,
    runner: object,
    device: Path,
    filesystem_uuid: str,
    mountpoint: Path,
    grub_text: str,
    branding_dir: Path | None = None,
    target: DeviceObservation,
    bios_bootloader_installer: Callable[[DeviceObservation, Path], None] | None,
) -> None:
    """Write GRUB state only through the plan-derived verified ext4 role."""
    if not mountpoint.is_absolute() or mountpoint.is_symlink():
        raise FreshAbInstallError("boot-control mountpoint is not authoritative")
    try:
        mountpoint.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise FreshAbInstallError(f"boot-control mountpoint cannot be created: {exc}") from exc
    if not mountpoint.is_dir() or any(mountpoint.iterdir()):
        raise FreshAbInstallError("boot-control staging mountpoint must be empty")
    try:
        observed_uuid = probe_partition_filesystem_uuid(runner, device)  # type: ignore[arg-type]
    except LayoutError as exc:
        raise FreshAbInstallError(
            f"boot-control filesystem identity cannot be rechecked: {exc}"
        ) from exc
    if observed_uuid != filesystem_uuid:
        raise FreshAbInstallError(
            "boot-control filesystem changed after layout observation"
        )

    try:
        with mount_verified_ext4_for_write(
            runner=runner,  # type: ignore[arg-type]
            node=device,
            filesystem_uuid=filesystem_uuid,
            mountpoint=mountpoint,
        ) as mounted:
            _write_boot_control_config(mounted, grub_text)
            if branding_dir is not None:
                _copy_boot_branding(branding_dir, mounted / "grub")
            backend = GrubEnvBackend.initialize(mounted / "grub", default_slot="A")
            if backend.inspect().default_slot != "A":
                raise FreshAbInstallError(
                    "boot-control GRUB environment did not persist default slot A"
                )
            if bios_bootloader_installer is None or not callable(
                bios_bootloader_installer
            ):
                raise FreshAbInstallError(
                    "fresh BIOS A/B install has no bootloader installer"
                )
            # Keep the verified boot-control volume mounted while GRUB writes
            # its BIOS core image and modules beside this config.
            bios_bootloader_installer(target, mounted)
    except PersistError as exc:
        raise FreshAbInstallError(
            f"verified boot-control filesystem refused: {exc}"
        ) from exc


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
    "GRUB_CONFIG_REL_PATH",
    "AbExecutorFacts",
    "BundlePayloadStream",
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
