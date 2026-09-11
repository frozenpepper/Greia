"""T6-HARNESS3 executable lifecycle harness: 8-step A/B lifecycle on device/QEMU.

Supersedes the frozen 7-step source-only X8 sequence (kept intact in
``runner.py``) with the full T6-HARNESS3 scope:

- disposable image assembly owned by the harness (raw file outside the
  source tree, real ``legacy-bios-ab-v1`` layout, production-composed
  install path, real GRUB/SeaBIOS-bootable artifacts, evidence only in
  the designated output directory, safe loop/mount teardown);
- the 8-step lifecycle: fresh install A -> boot A -> stage B one-shot ->
  boot B commit/accept -> stage broken candidate -> boot broken candidate
  (recovery trigger) -> recovery boot B -> B-to-A reverse update;
- the exact shipped update path on device/QEMU for the successful-update
  legs: stage through the shipped ``build_live_update_service``
  constructor path including the production boot-backend attach, with
  production destination-device factories supplied as explicit
  image-integration parameters through that shipped path;
- launcher ``INTERACTIVE_READY`` acceptance via the real
  ``apply_prepared_state`` -> ``run_post_intro_acceptance`` production
  seam, with the persistent default held on the previous slot until the
  health commit;
- authoritative guest/disk observations after each transition; the report
  ``ok`` flag derives from those assertions;
- on-device identity observation (loop-attach + production
  ``read_mbr_disk_signature`` / ``probe_mbr_partition_partuuid`` /
  ``probe_partition_filesystem_uuid``) plus the ``sfdisk``/``blkid -p``
  file cross-check executed (not skipped) on capable hosts.

Fake boundary: recording/sparse fakes are permitted ONLY at the
block-driver seam (sparse ``LoopbackSlotFile`` stores, scripted
``MbrProbeRunner`` answers where no device exists). No stubbed health
seam, no stubbed launcher acceptance, no manually fabricated
slot/journal/GRUB state. This module never imports JSON backend fakes
and never calls ``simulate_reboot``: the source-scope reboot analogue
folds a declared boot outcome through the real ``GrubEnvBackend``
(``reconcile``) plus the real journal ``reconcile``; on device the
outcome is observed after a real QEMU boot.

Source scope vs device scope: on a QEMU-capable Linux x86_64 host with
real SeaBIOS/GRUB tooling the harness executes end to end
(``LifecycleHarness.run_device``); elsewhere the same production seams
are driven source-scope (``run_source_scope``) while device-contact legs
report explicit deferred/RED fail-closed markers instead of false green.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Sequence

from greia_installer.layout import (
    MbrCommandResult,
    MbrProbeRunner,
    SubprocessMbrProbeRunner,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCHEMA_VERSION = 1

LAYOUT_ADAPTER_ID = "legacy-bios-ab-v1"
BOOT_BACKEND_ID = "grub-ab-v1"
REFERENCE_PROFILE_ID = "legacy-x86-i686"

#: The 8-step lifecycle sequence owned by this harness.
LIFECYCLE_SEQUENCE = (
    "fresh-install-A",
    "boot-A-accepted",
    "stage-B-one-shot",
    "boot-B-commit",
    "stage-broken-candidate",
    "boot-broken-candidate",
    "recovery-boot-B",
    "reverse-update-B-to-A",
)

#: Legs that MUST traverse the shipped update constructor path.
SHIPPED_UPDATE_LEGS = (
    "stage-B-one-shot",
    "boot-B-commit",
    "reverse-update-B-to-A",
)

#: Legs that MUST traverse the launcher INTERACTIVE_READY acceptance seam.
LAUNCHER_ACCEPTANCE_LEGS = (
    "boot-A-accepted",
    "boot-B-commit",
    "recovery-boot-B",
    "reverse-update-B-to-A",
)

#: Frozen T7-ATTEST leg definition (verbatim): the 8-step lifecycle
#: comprises 3 non-boot transitions and 5 boot-outcome legs. Every
#: transition records per-transition evidence (default/one-shot/
#: last-booted, journal, accepted slot/release/sequence, PERSIST marker,
#: release hashes, image SHA), but only the 5 boot-outcome legs assert a
#: guest-observed boot outcome through the frozen attestation seam
#: (grubenv-on-image with post-boot loop remount/read via
#: ``GrubEnvBackend.attach(mountpoint).inspect()``; consumption
#: predicate: ``next_entry`` absent AND ``last_booted == expected``).
NON_BOOT_TRANSITIONS = (
    "fresh-install-A",
    "stage-B-one-shot",
    "stage-broken-candidate",
)

#: The 5 boot-outcome legs: each performs exactly one real SeaBIOS boot
#: on a capable host and asserts the guest-observed outcome.
BOOT_OUTCOME_LEGS = (
    "boot-A-accepted",
    "boot-B-commit",
    "boot-broken-candidate",
    "recovery-boot-B",
    "reverse-update-B-to-A",
)

#: Expected guest-observed slot per boot-outcome leg (consumption target).
BOOT_OUTCOME_EXPECTED_SLOT = {
    "boot-A-accepted": "A",
    "boot-B-commit": "B",
    "boot-broken-candidate": "A",
    "recovery-boot-B": "B",
    "reverse-update-B-to-A": "A",
}

#: Release lineage: ids/sequences declared; hashes recorded per run.
RELEASE_LINEAGE = (
    {"release_id": "greia-0.20.0", "release_sequence": 20, "slot": "A"},
    {"release_id": "greia-0.21.0", "release_sequence": 21, "slot": "B"},
    {"release_id": "greia-0.21.1", "release_sequence": 22, "slot": "B",
     "broken": True},
    {"release_id": "greia-0.22.0", "release_sequence": 23, "slot": "A"},
)

QEMU_BINARY = "qemu-system-x86_64"

_SIGNER = "greia-release-main"
_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_INSTALL_SHA = "ab" * 32
_PASSWORD_HASH = "grub.pbkdf2.sha512.10000.T6HARNESS3ABCDEF0123456789"
_MBR_SIGNATURE = "1a2b3c4d"


class LifecycleHarnessError(RuntimeError):
    """Lifecycle harness failed fail-closed."""


class LifecycleContractError(LifecycleHarnessError):
    """Harness violated its own lifecycle contract (positive-control RED)."""


# ---------------------------------------------------------------------------
# Configuration + device gates
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LifecycleConfig:
    """Disposable-image lifecycle run configuration (output outside tree)."""

    output_dir: Path
    timeout_seconds: int = 300
    memory_mib: int = 1024
    cpus: int = 1
    keep_image: bool = False
    seabios_path: Path | None = None

    def validate(self, *, project_root: Path = PROJECT_ROOT) -> None:
        output = Path(self.output_dir)
        if not output.is_absolute():
            raise LifecycleHarnessError("output_dir must be an absolute path")
        root = Path(project_root).resolve()
        resolved = output.resolve()
        if resolved == root or root in resolved.parents:
            raise LifecycleHarnessError(
                "refusing to build disposable images inside the source tree"
            )
        if self.timeout_seconds < 60 or self.timeout_seconds > 3600:
            raise LifecycleHarnessError("timeout must be between 60 and 3600 seconds")
        if self.memory_mib < 768 or self.memory_mib > 16384:
            raise LifecycleHarnessError("memory must be between 768 and 16384 MiB")


def lifecycle_spec() -> dict[str, object]:
    """Pure-data lifecycle declaration for tests and the report header."""
    return {
        "schema_version": SCHEMA_VERSION,
        "layout_adapter": LAYOUT_ADAPTER_ID,
        "boot_backend": BOOT_BACKEND_ID,
        "reference_profile": REFERENCE_PROFILE_ID,
        "lifecycle_sequence": list(LIFECYCLE_SEQUENCE),
        "non_boot_transitions": list(NON_BOOT_TRANSITIONS),
        "boot_outcome_legs": list(BOOT_OUTCOME_LEGS),
        "boot_outcome_expected_slot": dict(BOOT_OUTCOME_EXPECTED_SLOT),
        "shipped_update_legs": list(SHIPPED_UPDATE_LEGS),
        "launcher_acceptance_legs": list(LAUNCHER_ACCEPTANCE_LEGS),
        "release_lineage": [dict(entry) for entry in RELEASE_LINEAGE],
        "fake_boundary": "recording/sparse fakes only at the block-driver seam",
        "valued_device_contact": False,
        "qemu_binary": QEMU_BINARY,
    }


#: Device binaries covered by the owner-provisioned bounded sudoers drop-in
#: (``/etc/sudoers.d/greia-harness`` on the Acer reference device, temporary
#: pending the permanent ``greia-devctl`` harness verb owned by P2-DEVCTL-VERB).
#: Privileged legs invoke exactly these binaries via ``sudo -n`` when the
#: harness itself does not run as root. Anything outside this set (e.g.
#: ``sync``) runs unprivileged-direct and must never gain a sudo prefix.
SUDOERS_PROVISIONED_BINARIES: frozenset[str] = frozenset({
    "losetup",
    "partprobe",
    "partx",
    "mount",
    "umount",
    "blkid",
    "sfdisk",
    "mkfs.ext4",
    "udevadm",
    "qemu-system-x86_64",
    "qemu-system-i386",
})

#: Device tools that must resolve for the device path (``require_device_host``
#: presence check). ``partx`` is rescan-fallback only and is resolved lazily
#: by :func:`rescan_loop_partitions`, not here.
DEVICE_HOST_REQUIRED_TOOLS: tuple[str, ...] = (
    QEMU_BINARY,
    "losetup",
    "mount",
    "umount",
    "partprobe",
    "udevadm",
    "mkfs.ext4",
    "blkid",
    "sfdisk",
)


def require_device_host(*, runner_which=None) -> None:
    """Fail closed unless this host can execute the device path."""
    import sys as _sys

    which = runner_which or resolve_device_host_tool
    if _sys.platform != "linux":
        raise LifecycleHarnessError(
            "device lifecycle requires a Linux host "
            f"(this host reports {_sys.platform}); source-scope proof only"
        )
    missing = [command for command in DEVICE_HOST_REQUIRED_TOOLS if which(command) is None]
    if missing:
        raise LifecycleHarnessError("missing device host tools: " + ", ".join(missing))
    if os.geteuid() == 0:
        return
    # Non-root path: the owner-provisioned bounded sudoers rule (temporary
    # pending the greia-devctl verb). Prove the passwordless mechanism with a
    # harmless probe of one provisioned binary; never handle passwords, never
    # use -S/askpass/timestamp tricks. Absence of both root and the rule stays
    # RED under the same fail-closed error.
    if shutil.which("sudo") is None:
        raise LifecycleHarnessError("device lifecycle runs as root on a Linux host")
    probe = resolve_device_host_tool("losetup")
    if probe is None:  # pragma: no cover - missing already raised above
        raise LifecycleHarnessError("device lifecycle runs as root on a Linux host")
    try:
        completed = subprocess.run(
            ["sudo", "-n", probe, "--version"],
            capture_output=True,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        raise LifecycleHarnessError(
            "device lifecycle runs as root on a Linux host"
        ) from None
    if completed.returncode != 0:
        raise LifecycleHarnessError("device lifecycle runs as root on a Linux host")


def resolve_device_host_tool(name: str) -> str | None:
    """Resolve a device host tool without leaking PATH artifacts.

    Unprivileged PATHs commonly lack ``/sbin``/``/usr/sbin`` where
    ``losetup``/``mount`` live, so a bare ``subprocess`` call would raise
    ``FileNotFoundError`` under the caller's gate (e.g. recorded under the
    consumption-predicate). Resolution falls back to the sbin directories
    and returns ``None`` when the tool is genuinely absent so callers can
    fail closed with :class:`LifecycleHarnessError`.
    """
    found = shutil.which(name)
    if found is not None:
        return found
    for candidate in (f"/sbin/{name}", f"/usr/sbin/{name}"):
        if Path(candidate).is_file():
            return candidate
    return None


def device_tool_invocation(name: str, *args: str) -> list[str]:
    """Build the privileged argv for one device host tool.

    Resolves ``name`` to its absolute path (sbin-aware, so unprivileged
    PATHs without ``/sbin`` cannot leak ``FileNotFoundError``), then
    prefixes ``sudo -n`` when the harness is not root and the tool is in
    the owner-provisioned set. Raises :class:`LifecycleHarnessError` when
    the tool is genuinely absent — absence stays RED, never a silent skip.
    Non-provisioned tools run unprivileged-direct (they must never gain a
    sudo prefix). Never uses ``-S``/askpass/timestamp tricks.
    """
    resolved = resolve_device_host_tool(name)
    if resolved is None:
        raise LifecycleHarnessError(
            f"device host tool missing: {name} "
            "(device lifecycle runs as root on a Linux host "
            "with sbin tools present)"
        )
    if os.geteuid() != 0 and name in SUDOERS_PROVISIONED_BINARIES:
        return ["sudo", "-n", resolved, *list(args)]
    return [resolved, *list(args)]


def run_device_host_tool(
    argv: Sequence[str],
    *,
    capture_output: bool = True,
    text: bool = False,
    timeout: int = 60,
) -> subprocess.CompletedProcess[object]:
    """Run one device host tool, fail-closed on missing binary.

    Converts ``FileNotFoundError`` (PATH artifact) into
    :class:`LifecycleHarnessError` so collect legs record the verbatim
    fail-closed error under their own frozen gate instead of an
    environment-lookup leak. Never weakens the gate: absence stays RED.
    Non-root hosts run provisioned tools via ``sudo -n`` (owner rule);
    see :func:`device_tool_invocation`.
    """
    if not argv:
        raise LifecycleHarnessError("device host tool argv is empty")
    resolved_argv = device_tool_invocation(argv[0], *[str(part) for part in argv[1:]])
    try:
        return subprocess.run(
            resolved_argv,
            capture_output=capture_output,
            text=text,  # type: ignore[arg-type]
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise LifecycleHarnessError(
            f"device host tool missing: {argv[0]} "
            "(device lifecycle runs as root on a Linux host "
            "with sbin tools present)"
        ) from exc


def file_cross_check_tools() -> dict[str, str | None]:
    """Resolve the file cross-check tools (must both exist to execute)."""
    return {
        "sfdisk": resolve_device_host_tool("sfdisk"),
        "blkid": resolve_device_host_tool("blkid"),
    }


def _privileged_rescan_run(argv: object, **kwargs: object) -> object:
    """Default rescan runner: privileged argv, ``shell=False`` semantics.

    Accepts the same call shape as ``subprocess.run`` (used by the
    rescan/observe injectable seams) but builds the argv through
    :func:`device_tool_invocation` so partprobe/partx/udevadm resolve
    sbin-aware and run via ``sudo -n`` on non-root hosts under the
    owner-provisioned rule. A genuinely missing tool raises
    :class:`LifecycleHarnessError`, which the rescan caller records as a
    failure (never a silent skip).
    """
    parts = [str(part) for part in list(argv)]  # type: ignore[arg-type]
    if not parts:
        raise LifecycleHarnessError("loop rescan argv is empty")
    timeout = kwargs.get("timeout", LOOP_RESCAN_TIMEOUT_SECONDS)
    capture = bool(kwargs.get("capture_output", True))
    return subprocess.run(
        device_tool_invocation(parts[0], *parts[1:]),
        capture_output=capture,
        timeout=int(timeout),  # type: ignore[arg-type]
        shell=False,
    )


# ---------------------------------------------------------------------------
# Image-integration destination seams (block-driver seam only)
# ---------------------------------------------------------------------------


class ImageIntegrationSeams:
    """Production destination-device factories as explicit parameters.

    These travel THROUGH the shipped ``build_live_update_service``
    constructor path (never by constructing the backend directly around
    the authority). Backing stores are sparse ``LoopbackSlotFile`` images
    — the block-driver seam — with a recording contact log so tests prove
    the inactive slot (and never the live slot) was addressed.
    """

    def __init__(self, root: Path, contract_bytes: bytes) -> None:
        from greia_platform.slot_writer import LoopbackSlotFile

        self._root = Path(root)
        self._contract_bytes = bytes(contract_bytes)
        self._loopback = LoopbackSlotFile
        self.slots_dir = self._root / "slot-stores"
        self.slots_dir.mkdir(parents=True, exist_ok=True)
        self.mounts_dir = self._root / "slot-mounts"
        self.mounts_dir.mkdir(parents=True, exist_ok=True)
        self.contacts: list[str] = []
        self.files: dict[str, bytes] = {}
        (self._root / "installed-contract.json").write_bytes(self._contract_bytes)

    # -- factories supplied through the shipped constructor path ---------

    def slot_store_factory(self, destination: object) -> object:
        from greia_platform.slot_writer import LoopbackSlotFile

        role = str(getattr(destination, "role", "system-b"))
        if role not in ("system-a", "system-b"):
            raise LifecycleHarnessError(
                f"image-integration seam refuses non-slot role {role!r}"
            )
        self.contacts.append(f"store:{role}")
        capacity = int(getattr(destination, "slot_capacity_bytes", 0))
        if capacity <= 0:
            raise LifecycleHarnessError("slot store needs a positive capacity")
        # Re-staging an inactive slot reformats it on device; the sparse
        # analogue unlinks the previous staged store before recreating it.
        # The contact log keeps every addressing for the slot audit.
        previous = self.slots_dir / f"slot-{role}.img"
        if previous.exists() and not previous.is_symlink():
            previous.unlink()
        return LoopbackSlotFile.create(self.slots_dir / f"slot-{role}.img", capacity)

    def filesystem_factory(self) -> object:
        self.contacts.append("filesystem")
        return _RecordingSlotFilesystem(self.mounts_dir, self.files)

    def package_installer_factory(self) -> object:
        self.contacts.append("package-installer")
        return _RecordingPackageInstaller()

    def inventory_factory(self) -> object:
        from greia_platform.slot_writer import HardwareInventoryAttestation

        self.contacts.append("inventory")
        return HardwareInventoryAttestation(
            token=hashlib.sha256(b"t6-harness-inventory").hexdigest()
        )

    def support_set_factory(self, bundle: object) -> object:
        from greia_platform.slot_writer import ReleaseSupportSet

        self.contacts.append("support")
        manifest = getattr(bundle, "manifest")
        return ReleaseSupportSet(
            support_digest=manifest.hardware_support_sha256,
            support_size=manifest.hardware_support_size,
            installed_size_bound=0,
            provided_firmware=frozenset(),
            provided_microcode=frozenset(),
            packages=(),
        )

    def installed_contract_factory(self) -> bytes:
        self.contacts.append("contract")
        return (self._root / "installed-contract.json").read_bytes()

    def seams(self):  # type: ignore[no-untyped-def]
        from greia_platform.system_updates import UpdateSlotSeams

        return UpdateSlotSeams(
            slot_store_factory=self.slot_store_factory,
            filesystem_factory=self.filesystem_factory,
            package_installer_factory=self.package_installer_factory,
            inventory_factory=self.inventory_factory,
            support_set_factory=self.support_set_factory,
            installed_contract_factory=self.installed_contract_factory,
        )


class _RecordingSlotFilesystem:
    """Minimal slot-filesystem seam owned by the image-integration layer."""

    def __init__(self, mount_dir: Path, files: dict[str, bytes]) -> None:
        self._mount_dir = Path(mount_dir)
        self._mount_dir.mkdir(parents=True, exist_ok=True)
        self._files = files
        self.bound_uuid: str | None = None
        self.mounted = False

    def bind_filesystem_uuid(self, filesystem_uuid: str) -> None:
        self.bound_uuid = filesystem_uuid

    def expand_to_capacity(self) -> None:
        pass

    def mount(self) -> Path:
        self.mounted = True
        return self._mount_dir

    def unmount(self) -> None:
        self.mounted = False

    def sync(self) -> None:
        pass

    def write_file(self, relative_path: str, data: bytes) -> None:
        if not self.mounted:
            raise AssertionError("slot writes require a mounted destination")
        self._files[relative_path] = bytes(data)

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(name for name in required if name not in self._files)

    def check_health(self) -> None:
        pass


class _RecordingPackageInstaller:
    def install(self, firmware: tuple[str, ...], microcode: tuple[str, ...]):  # type: ignore[no-untyped-def]
        return ()


# ---------------------------------------------------------------------------
# Shipped update path (never around the authority)
# ---------------------------------------------------------------------------


def shipped_update_authority(
    *,
    state_dir: Path,
    trusted_key_dir: Path,
    layout_record_path: Path,
    boot_backend: object,
    seams: ImageIntegrationSeams,
    system_version: str = "0.20.0",
    platform_family: str = "legacy-x86",
    architecture: str = "i386",
    profile: str = REFERENCE_PROFILE_ID,
):  # type: ignore[no-untyped-def]
    """Compose the production authority through the shipped constructor.

    Destination factories arrive as explicit image-integration parameters
    through ``build_live_update_service``; the backend is never
    constructed directly around the authority. The production boot
    backend is supplied attached (on device it attaches via
    ``GREIA_GRUBENV_DIR``; at source scope the caller attaches the
    disposable ``GrubEnvBackend`` explicitly so the attach seam is still
    the production one).
    """
    import os as _os

    from greia_platform.system_updates import build_live_update_service

    previous = dict(_os.environ)
    _os.environ.update(
        {
            "GREIA_SYSTEM_VERSION": system_version,
            "GREIA_SYSTEM_PLATFORM_FAMILY": platform_family,
            "GREIA_SYSTEM_ARCHITECTURE": architecture,
            "GREIA_SYSTEM_PROFILE": profile,
        }
    )
    try:
        return build_live_update_service(
            state_dir=Path(state_dir),
            trusted_key_dir=Path(trusted_key_dir),
            layout_record_path=Path(layout_record_path),
            boot_backend=boot_backend,
            boot_backend_auto=False,
            seams=seams.seams(),
        )
    finally:
        _os.environ.clear()
        _os.environ.update(previous)


def default_shipped_authority_without_seams(
    *,
    state_dir: Path,
    trusted_key_dir: Path,
    layout_record_path: Path,
    boot_backend: object,
):  # type: ignore[no-untyped-def]
    """Shipped constructor with default (missing) destination seams.

    Used only to prove fail-closed staging: stage time must raise
    ``UpdateBackendUnavailable`` with no silent fallback and no
    single-root routing.
    """
    from greia_platform.system_updates import build_live_update_service

    return build_live_update_service(
        state_dir=Path(state_dir),
        trusted_key_dir=Path(trusted_key_dir),
        layout_record_path=Path(layout_record_path),
        boot_backend=boot_backend,
        boot_backend_auto=False,
    )


# ---------------------------------------------------------------------------
# Release bundles (signed .greiaupdate v2, validly signed even when broken)
# ---------------------------------------------------------------------------


def _payload_bytes(size: int, tag: bytes) -> bytes:
    body = bytes((index * 31 + 7) % 256 for index in range(size))
    raw = tag + body[len(tag):]
    fixed = bytearray(raw)
    if fixed[510:512] == b"\x55\xaa":
        fixed[510:512] = b"\x00\x00"
    if fixed[512:520] == b"EFI PART":
        fixed[512:520] = b"\x00" * 8
    return bytes(fixed)


def build_test_release(
    root: Path,
    *,
    name: str,
    release_id: str,
    sequence: int,
    private_key: Path,
    platform_family: str = "legacy-x86",
    architecture: str = "i386",
    profile: str = REFERENCE_PROFILE_ID,
    payload_size: int = 220 * 1024,
) -> Path:
    """Build one signed .greiaupdate v2 bundle for the lifecycle lineage."""
    from greia_platform.system_updates import (
        build_persistent_state_contract_bytes,
        build_update_bundle,
    )

    work = Path(root) / "releases" / name
    work.mkdir(parents=True, exist_ok=True)
    (work / "slot.img").write_bytes(_payload_bytes(payload_size, f"t6-{name}:".encode()))
    (work / "hw.tar.zst").write_bytes(b"\x28\xb5\x2f\xfd" + b"t6-hw" * 64)
    (work / "contract.json").write_bytes(build_persistent_state_contract_bytes())
    bundle = work / f"{name}.greiaupdate"
    build_update_bundle(
        payload_path=work / "slot.img",
        hardware_support_path=work / "hw.tar.zst",
        persistent_contract_path=work / "contract.json",
        output_path=bundle,
        version=release_id.split("-", 1)[1],
        release_id=release_id,
        release_sequence=sequence,
        platform_family=platform_family,
        architecture=architecture,
        profile=profile,
        signer=_SIGNER,
        private_key_path=private_key,
        release_notes=f"T6-HARNESS3 lifecycle release {name}.",
    )
    return bundle


def mint_signing_keys(root: Path, key_dir: Path) -> tuple[Path, Path]:
    """Mint one disposable ed25519 release keypair into the trusted dir."""
    from greia_platform.system_updates import generate_ed25519_keypair

    private_key = Path(root) / "release-private.pem"
    public_key = Path(root) / "release-public.pem"
    generate_ed25519_keypair(private_key, public_key)
    Path(key_dir).mkdir(parents=True, exist_ok=True)
    (Path(key_dir) / f"{_SIGNER}.pem").write_bytes(public_key.read_bytes())
    return private_key, public_key


# ---------------------------------------------------------------------------
# Disposable machine: layout record, boot state, journal, PERSIST, history
# ---------------------------------------------------------------------------


def _record_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "accepted_release_id": "greia-0.20.0",
        "accepted_release_sequence": 20,
        "accepted_slot": "A",
        "boot_backend": BOOT_BACKEND_ID,
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": REFERENCE_PROFILE_ID,
        "install_target_sha256": _INSTALL_SHA,
        "installed_at_unix": 1757000000,
        "layout_id": LAYOUT_ADAPTER_ID,
        "persist": {"filesystem_uuid": _UUID_P_FS,
                    "partuuid": f"{_MBR_SIGNATURE}-04"},
        "platform_family": "legacy-x86",
        "schema_version": 1,
        "slot_bytes": 1073741824,
        "system_a": {"filesystem_uuid": _UUID_A_FS,
                     "partuuid": f"{_MBR_SIGNATURE}-02"},
        "system_b": {"filesystem_uuid": _UUID_B_FS,
                     "partuuid": f"{_MBR_SIGNATURE}-03"},
    }
    base.update(overrides)
    return base


def write_layout_record(path: Path, **overrides: object) -> Path:
    """Write the canonical installed-layout record (teardown/reload safe)."""
    Path(path).write_bytes(
        (json.dumps(_record_dict(**overrides), sort_keys=True) + "\n").encode()
    )
    return Path(path)


def fresh_machine_state(root: Path) -> dict[str, Path]:
    """Assemble one disposable machine: layout record, boot state, dirs."""
    from greia_platform.grub_ab import GrubEnvBackend
    from greia_platform.system_updates import write_accepted_sequence

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    layout_path = root / "installed-layout.json"
    write_layout_record(layout_path)
    boot_dir = root / "boot-control"
    boot_dir.mkdir(parents=True, exist_ok=True)
    grub = GrubEnvBackend.initialize(boot_dir, default_slot="A")
    _ = grub
    state_dir = root / "update-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    write_accepted_sequence(state_dir, 20)
    key_dir = root / "trusted-keys"
    key_dir.mkdir(parents=True, exist_ok=True)
    persist_dir = root / "persist"
    persist_dir.mkdir(parents=True, exist_ok=True)
    (persist_dir / "profile.json").write_bytes(b'{"schema":1}\n')
    return {
        "layout": layout_path,
        "boot_control": boot_dir,
        "state": state_dir,
        "keys": key_dir,
        "persist": persist_dir,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Launcher INTERACTIVE_READY acceptance leg (real production seam)
# ---------------------------------------------------------------------------


def run_launcher_acceptance(
    *,
    update_state_dir: Path,
    boot_control_dir: Path,
    layout_record_path: Path,
    cmdline_path: Path,
    identity_path: Path,
    receipt_path: Path,
    journal_candidates: Sequence[Path] = (),
) -> dict[str, object]:
    """Drive the real launcher acceptance seam exactly once per boot.

    Builds a ``LauncherApplication`` (no bootstrap side effects), moves
    its lifecycle guard to ``INTERACTIVE_READY`` through the production
    display/first-frame path, and publishes one synthetic prepared state
    through the real ``apply_prepared_state`` ->
    ``maybe_accept_production_boot`` graph with the production observer,
    vault, journal and layout bindings resolved from the disposable
    device tree. Returns the seam-call record plus the outcome.

    No stubbed health: the counting wrapper delegates to the real seam.
    """
    import os as _os
    from unittest import mock as _mock

    from greia_launcher import boot_health as launcher_health

    calls: list[str] = []
    real_seam = launcher_health.maybe_accept_production_boot

    def _counting(guard):  # type: ignore[no-untyped-def]
        calls.append(str(getattr(guard.state, "value", guard.state)))
        return real_seam(guard)

    env = {
        "GREIA_OS_ROOT": str(PROJECT_ROOT),
        "GREIA_PROFILES_DIR": str(Path(update_state_dir).parent / "profiles"),
        "GREIA_ACTIVE_PROFILE_STATUS": str(Path(update_state_dir).parent / "active.json"),
        "GREIA_MAIN_CREDENTIAL_PATH": str(Path(update_state_dir).parent / "cred.json"),
        "CREDENTIALS_DIRECTORY": str(Path(update_state_dir).parent / "credentials"),
        "GREIA_UPDATE_STATE_DIR": str(update_state_dir),
        "GREIA_BOOT_JOURNAL_DIR": str(
            journal_candidates[0]
            if journal_candidates
            else (Path(update_state_dir).parent / "empty-boot-journal")
        ),
        "GREIA_GRUBENV_DIR": str(boot_control_dir),
        "GREIA_INSTALLED_LAYOUT_RECORD": str(layout_record_path),
        "GREIA_BOOT_CMDLINE": str(cmdline_path),
        "GREIA_RELEASE_IDENTITY_PATH": str(identity_path),
        "GREIA_FINALIZATION_RECEIPT_PATH": str(receipt_path),
    }
    with _mock.patch.dict(_os.environ, env, clear=False):
        from greia_launcher import main as launcher_main

        previous_marker = _os.environ.get(launcher_main.DEVELOPER_MARKER_ENV_VAR)
        _os.environ[launcher_main.DEVELOPER_MARKER_ENV_VAR] = str(
            Path(update_state_dir).parent / "no-developer-marker"
        )
        _os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        try:
            with _mock.patch.object(
                launcher_health,
                "maybe_accept_production_boot",
                side_effect=_counting,
            ):
                from greia_launcher.main import LauncherApplication

                app = LauncherApplication(windowed=True, allow_exit=True, bootstrap=False)
                app._boot_lifecycle.mark_display_ready()
                app._boot_lifecycle.mark_first_frame_visible()
                app._boot_lifecycle.begin_preparing_runtime()
                state = _synthetic_prepared_state()
                app.apply_prepared_state(state)
                outcome = app._post_intro_health_outcome
                error = app._post_intro_health_error
        finally:
            if previous_marker is None:
                _os.environ.pop(launcher_main.DEVELOPER_MARKER_ENV_VAR, None)
            else:
                _os.environ[launcher_main.DEVELOPER_MARKER_ENV_VAR] = previous_marker
    outcome_dict = None
    if outcome is not None:
        as_dict = getattr(outcome, "as_dict", None)
        outcome_dict = as_dict() if callable(as_dict) else str(outcome)
    return {
        "seam_calls": list(calls),
        "outcome": outcome_dict,
        "accepted_slot": getattr(outcome, "accepted_slot", None),
        "first_install": getattr(outcome, "first_install", None),
        "error": error,
    }


def _synthetic_prepared_state():  # type: ignore[no-untyped-def]
    from types import SimpleNamespace

    from greia_launcher.bootstrap import PreparedLauncherState

    return PreparedLauncherState(
        runtime=None,
        sources=(),
        registrations=(),
        activities=(),
        registry=None,
        asset_set=SimpleNamespace(catalogue=None, shared_visuals_available=False),
        profile_store=None,
        profiles=(),
        session=None,
        selector_theme=None,
        runtime_services=None,
        supervisor=None,
        catalogue=None,
        history_recovery_failures=frozenset(),
        parent_degraded=False,
        parent_error=None,
        rejected=(),
        conflicts=(),
        degraded=False,
        activity_discovery_token=(),
        shell_window_backend=None,
        installed=False,
    )


# ---------------------------------------------------------------------------
# On-device identity observation (loop-attach + production probe path)
# ---------------------------------------------------------------------------


@dataclass
class DeviceObservationResult:
    """Authoritative observation outcome for one image/device."""

    record_matches_topology: bool
    disk_signature: str
    observed_identities: dict[str, dict[str, str]]
    file_cross_check_executed: bool
    file_cross_check_green: bool
    loop_attach_green: bool
    detail: str = ""


def observe_file_backed_image(
    image: Path,
    *,
    plan: object,
    target_name: str = "loop0",
    expected_signature: str = _MBR_SIGNATURE,
) -> DeviceObservationResult:
    """Bind the layout record to a file-backed DOS image (no device needed).

    Production byte rule (``parse_dos_partition_table``) always runs;
    the host ``sfdisk``/``blkid -p`` file cross-check executes (not
    skipped) wherever both tools exist, and reports explicit
    not-executed elsewhere instead of false green. Teardown/remount/reload
    semantics: the record is persisted, all handles dropped, and the
    topology re-proven from reloaded bytes.
    """
    import gc as _gc

    from greia_installer.layout import parse_dos_partition_table
    from greia_platform.persistent_layout import InstalledLayoutRecord

    from greia_installer.layout import (
        build_observed_mbr_topology,
        verify_mbr_topology_for_boot,
    )

    with open(image, "rb") as handle:
        table = parse_dos_partition_table(handle.read(512))
    if table.disk_signature != expected_signature:
        raise LifecycleHarnessError(
            "image disk signature does not match the expected test signature"
        )
    role_numbers = {"system-a": 2, "system-b": 3, "persist": 4}
    import uuid as _uuid

    filesystem_uuids = {role: str(_uuid.uuid4()) for role in role_numbers}
    identities = {
        role: {
            "filesystem_uuid": filesystem_uuids[role],
            "partuuid": table.partuuid_for(number),
            "scheme": "MBR_PARTUUID",
        }
        for role, number in role_numbers.items()
    }
    record = InstalledLayoutRecord.from_dict(_record_dict_for_identities(identities))
    record_path = Path(image).parent / "installed-layout.json"
    record.write_to(record_path)
    del record
    _gc.collect()
    reloaded = InstalledLayoutRecord.read_from(record_path)
    reloaded_identities = {
        "system-a": reloaded.system_a.as_dict(),
        "system-b": reloaded.system_b.as_dict(),
        "persist": reloaded.persist.as_dict(),
    }
    from greia_installer.disk import DeviceObservation

    target = DeviceObservation(
        path=Path(f"/dev/{target_name}"),
        device_type="disk",
        name=target_name,
        size_bytes=int(Path(image).stat().st_size),
        model="T6 lifecycle disposable",
        serial="T6-LIFECYCLE-1",
        transport="loop",
        removable=False,
        read_only=False,
        mountpoints=(),
        wwn="WWN-T6-LIFECYCLE",
        major_minor="7:99",
    )
    topology = build_observed_mbr_topology(
        plan=plan, target=target, identities=reloaded_identities
    )
    signature = verify_mbr_topology_for_boot(
        reloaded, topology, expected_disk_signature=table.disk_signature
    )
    matches = signature == table.disk_signature
    cross = run_file_cross_check(image, expected_signature=table.disk_signature)
    return DeviceObservationResult(
        record_matches_topology=matches,
        disk_signature=table.disk_signature,
        observed_identities=reloaded_identities,
        file_cross_check_executed=cross["executed"],
        file_cross_check_green=cross["green"],
        loop_attach_green=False,
        detail=cross["detail"],
    )


def _record_dict_for_identities(identities: Mapping[str, Mapping[str, str]]) -> dict[str, object]:
    base = _record_dict()
    base["system_a"] = dict(identities["system-a"])
    base["system_b"] = dict(identities["system-b"])
    base["persist"] = dict(identities["persist"])
    return base


def run_file_cross_check(image: Path, *, expected_signature: str) -> dict[str, object]:
    """Execute the sfdisk/blkid -p file cross-check (never silently skip).

    Returns ``{"executed": bool, "green": bool, "detail": str}``: executed
    is True only when both tools exist and both probes ran; green is True
    only when every executed probe agreed with the production byte parse.
    Tool-less hosts report executed=False (explicit deferred, never green).
    Invalid/unparseable tool output (including the all-zero signature,
    which the production validator refuses fail-closed) returns
    executed=True green=False RED instead of raising, so callers record
    the binding RED through the collect gate.
    """
    tools = file_cross_check_tools()
    if tools["sfdisk"] is None or tools["blkid"] is None:
        missing = sorted(
            name for name, path in tools.items() if path is None
        )
        return {
            "executed": False,
            "green": False,
            "detail": "deferred: tool-less host; missing " + ",".join(missing),
        }
    assert tools["sfdisk"] is not None and tools["blkid"] is not None
    from greia_platform.persistent_layout import require_mbr_disk_signature

    disk_id = subprocess.run(
        [tools["sfdisk"], "--disk-id", str(image)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if disk_id.returncode != 0:
        return {"executed": True, "green": False, "detail": "sfdisk --disk-id failed"}
    try:
        sfdisk_signature = require_mbr_disk_signature(
            disk_id.stdout.strip(), field="disk signature"
        )
    except Exception as exc:
        return {
            "executed": True,
            "green": False,
            "detail": f"sfdisk disk-id invalid: {exc}",
        }
    if sfdisk_signature != expected_signature:
        return {"executed": True, "green": False, "detail": "sfdisk disk-id mismatch"}
    probed = subprocess.run(
        [tools["blkid"], "-p", "-s", "PTUUID", "-o", "value", str(image)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if probed.returncode != 0:
        return {"executed": True, "green": False, "detail": "blkid -p PTUUID failed"}
    try:
        blkid_signature = require_mbr_disk_signature(
            probed.stdout.strip(), field="disk signature"
        )
    except Exception as exc:
        return {
            "executed": True,
            "green": False,
            "detail": f"blkid PTUUID invalid: {exc}",
        }
    if blkid_signature != expected_signature:
        return {"executed": True, "green": False, "detail": "blkid PTUUID mismatch"}
    return {"executed": True, "green": True, "detail": "sfdisk+blkid agree with byte parse"}


#: Fail-closed gate naming the post-run loop-attach partition rescan.
#: Raised when loop partition nodes never surface for observation after
#: a bounded kernel rescan plus bounded observation retries.
LOOP_RESCAN_GATE = "post-run-loop-attach-partition-rescan"

#: Fixed small cap on observation attempts per loop-attached observe
#: (initial attempt plus settle/sleep retries). Bounded: at most
#: ``LOOP_OBSERVE_MAX_ATTEMPTS`` production observations plus the same
#: number of ``udevadm settle`` waits.
LOOP_OBSERVE_MAX_ATTEMPTS = 5

#: Settle/sleep between observation attempts (matches the ``_loop_attach``
#: 0.5 s settle discipline).
LOOP_OBSERVE_RETRY_SETTLE_SECONDS = 0.5

#: Bounded timeout per rescan/settle subprocess (matches the harness's
#: existing 60 s device-tool discipline).
LOOP_RESCAN_TIMEOUT_SECONDS = 60


def rescan_loop_partitions(
    device: Path,
    *,
    run: Callable[..., object] | None = None,
    which: Callable[[str], str | None] | None = None,
) -> dict[str, object]:
    """Force a bounded kernel partition rescan for a loop-attached device.

    Runs ``partprobe <device>`` and/or ``partx -u <device>`` (fallback
    for whichever tool exists — both when both exist), then
    ``udevadm settle``, as argument arrays with ``shell=False``. A host
    missing every rescan tool records a tolerated single attempt and
    returns: observation must still run (never a silent skip). Rescan
    command failures are recorded, not fatal — the retried production
    observation is authoritative and fails closed at
    :data:`LOOP_RESCAN_GATE` when partitions never surface.
    """
    locator = str(device)
    if not locator or not Path(locator).is_absolute():
        raise LifecycleHarnessError("loop rescan needs an absolute device path")
    _run = run if run is not None else _privileged_rescan_run
    _which = which if which is not None else resolve_device_host_tool
    attempted: list[list[str]] = []
    missing: list[str] = []
    failures: list[str] = []
    candidates: list[list[str]] = []
    if _which("partprobe") is not None:
        candidates.append(["partprobe", locator])
    else:
        missing.append("partprobe")
    if _which("partx") is not None:
        candidates.append(["partx", "-u", locator])
    else:
        missing.append("partx")
    for argv in candidates:
        attempted.append(list(argv))
        try:
            completed = _run(
                list(argv),
                capture_output=True,
                timeout=LOOP_RESCAN_TIMEOUT_SECONDS,
                shell=False,
            )
        except Exception as exc:
            failures.append(f"{argv[0]} failed: {exc}")
            continue
        if getattr(completed, "returncode", 1) != 0:
            failures.append(
                f"{argv[0]} exited {getattr(completed, 'returncode', '?')}"
            )
    if _which("udevadm") is not None:
        settle_argv = ["udevadm", "settle"]
        attempted.append(list(settle_argv))
        try:
            _run(
                list(settle_argv),
                capture_output=True,
                timeout=LOOP_RESCAN_TIMEOUT_SECONDS,
                shell=False,
            )
        except Exception as exc:
            failures.append(f"udevadm settle failed: {exc}")
    else:
        missing.append("udevadm")
    if not attempted:
        detail = "deferred: tool-less host; missing " + ",".join(missing)
    elif failures:
        detail = (
            "rescan attempted (" + ",".join(a[0] for a in attempted) + "); "
            "failures: " + "; ".join(failures)
        )
    else:
        detail = "rescan attempted (" + ",".join(a[0] for a in attempted) + ")"
    return {
        "device": locator,
        "attempted": attempted,
        "missing": missing,
        "failures": failures,
        "detail": detail,
    }


class PrivilegedMbrProbeRunner(SubprocessMbrProbeRunner):
    """Harness block-probe runner: privileged argv, installer bounds.

    Polymorphic :class:`MbrProbeRunner` implementation for the device path:
    rewrites the probe argv through :func:`device_tool_invocation`
    (sbin-aware absolute path, ``sudo -n`` on non-root hosts under the
    owner-provisioned rule) and delegates execution to the production
    :class:`SubprocessMbrProbeRunner`, so the probe timeout/line-cap/
    fail-closed ``LayoutError`` mapping stays owned by the installer with
    no parallel mechanism here. As root the rewritten argv is the resolved
    absolute path (same binary, no sudo).
    """

    def run(self, command: Sequence[str]) -> MbrCommandResult:
        argv = [str(part) for part in list(command)]
        if not argv:
            raise LifecycleHarnessError("block probe argv is empty")
        return super().run(device_tool_invocation(argv[0], *argv[1:]))

def observe_loop_attached_device(
    device: Path,
    *,
    plan: object,
    record_path: Path,
    runner: MbrProbeRunner | None = None,
    rescan_run: Callable[..., object] | None = None,
    rescan_which: Callable[[str], str | None] | None = None,
    max_attempts: int = LOOP_OBSERVE_MAX_ATTEMPTS,
    retry_settle_seconds: float = LOOP_OBSERVE_RETRY_SETTLE_SECONDS,
) -> dict[str, object]:
    """Run the production observation path against a loop-attached device.

    Harness-owned rescan-then-observe: forces a bounded kernel partition
    rescan first (:func:`rescan_loop_partitions`), then probes the disk
    signature once plus each system-a/system-b/persist PARTUUID and
    filesystem UUID through :class:`PrivilegedMbrProbeRunner` (production
    ``SubprocessMbrProbeRunner`` bounds; argument arrays, ``shell=False``),
    retrying the whole production observation
    up to ``max_attempts`` with settle/sleep between attempts so a stale
    kernel partition view settles instead of REDing permanently. Proves
    the bound record equals the observed topology on success.

    Fail-closed: exhausted retries raise :class:`LifecycleHarnessError`
    naming :data:`LOOP_RESCAN_GATE` with the device, the rescan detail
    and the last probe error. Wrong-disk, non-MBR and cloned-UUID
    bindings still RED (surfaced as the last probe error); no PARTUUID
    or filesystem-UUID value is ever synthesized host-side.
    """
    from greia_installer.disk import DeviceObservation
    from greia_installer.layout import (
        LayoutError,
        build_observed_mbr_topology,
        observe_legacy_mbr_identities,
        verify_mbr_topology_for_boot,
    )
    from greia_platform.persistent_layout import InstalledLayoutRecord

    if not str(device) or not device.is_absolute():
        raise LifecycleHarnessError("loop observation needs an absolute device path")
    attempts = max(1, int(max_attempts))
    rescan = rescan_loop_partitions(
        device, run=rescan_run, which=rescan_which
    )
    probe_runner = runner if runner is not None else PrivilegedMbrProbeRunner()
    target = DeviceObservation(
        path=Path(device),
        device_type="disk",
        name=Path(device).name,
        size_bytes=0,
        model="T6 lifecycle disposable",
        serial="T6-LIFECYCLE-1",
        transport="loop",
        removable=False,
        read_only=False,
        mountpoints=(),
        wwn="WWN-T6-LIFECYCLE",
        major_minor="7:99",
    )
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            observed = observe_legacy_mbr_identities(
                probe_runner, target=target, plan=plan  # type: ignore[arg-type]
            )
        except LayoutError as exc:
            last_error = exc
            if attempt < attempts:
                _which = (
                    rescan_which
                    if rescan_which is not None
                    else resolve_device_host_tool
                )
                if _which("udevadm") is not None:
                    _run = (
                        rescan_run
                        if rescan_run is not None
                        else _privileged_rescan_run
                    )
                    try:
                        _run(
                            ["udevadm", "settle"],
                            capture_output=True,
                            timeout=LOOP_RESCAN_TIMEOUT_SECONDS,
                            shell=False,
                        )
                    except Exception:
                        pass
                time.sleep(retry_settle_seconds)
            continue
        record = InstalledLayoutRecord.read_from(Path(record_path))
        topology = build_observed_mbr_topology(
            plan=plan, target=target, identities=observed  # type: ignore[arg-type]
        )
        signature = verify_mbr_topology_for_boot(
            record, topology, expected_disk_signature=observed_signature(record, observed)
        )
        return {
            "observed": observed,
            "proven_signature": signature,
            "loop_attach_green": True,
            "rescan": rescan,
            "observation_attempts": attempt,
        }
    raise LifecycleHarnessError(
        f"{LOOP_RESCAN_GATE} gate: partitions never surfaced for {device} "
        f"after rescan ({rescan['detail']}) and {attempts} observation "
        f"attempt(s); last probe error: {last_error}"
    )


def observed_signature(record: object, observed: Mapping[str, Mapping[str, str]]) -> str:
    """Return the disk signature shared by the observed PARTUUIDs."""
    partuuid = observed["system-a"]["partuuid"]
    return partuuid.rsplit("-", 1)[0]


# ---------------------------------------------------------------------------
# Disposable image assembly (harness-owned, outside the source tree)
# ---------------------------------------------------------------------------


#: Plan-derived DOS partition extents written by ``write_mbr_table_for_plan``.
#: Role numbers follow the legacy adapter: 1 boot-control, 2 system-a,
#: 3 system-b, 4 persist. Values are 512-byte LBA sectors derived from the
#: declarative ``LayoutPlan`` (single source of truth) in number order from
#: the production ``LABEL_RESERVED_BYTES`` cursor, MiB-aligned, fixed roles
#: at their plan sizes, persist remainder-fill to ``plan.device_size_bytes``
#: — mirroring ``LegacyBiosAbAdapter._mkpart_extents`` parted semantics
#: (``1MiB`` start, ``100%`` remainder end). The writer, the span helper,
#: the sizing target and the fail-closed guard share the one
#: ``plan_mbr_sector_extents`` computation so they cannot drift apart.
#: No hardcoded divergent geometry lives here (B3-SPANSYNC).
_MBR_SECTOR_BYTES = 512


def plan_mbr_sector_extents(plan: object) -> dict[int, tuple[int, int]]:
    """Derive DOS ``(start_sector, count_sectors)`` extents from the plan.

    Partitions run in number order from the production ``LABEL_RESERVED_BYTES``
    cursor; fixed roles consume their plan sizes and the trailing remainder
    role fills to ``plan.device_size_bytes``. Production bounds are imported,
    never copied. Raises :class:`LifecycleHarnessError` fail-closed when the
    plan carries no remainder coverage, breaks MiB alignment, or leaves the
    cursor short of/past the device size.
    """
    from greia_installer.layout import (
        LABEL_RESERVED_BYTES,
        PARTITION_ALIGNMENT_BYTES,
    )

    partitions = sorted(
        getattr(plan, "partitions"), key=lambda item: item.number
    )
    if not partitions:
        raise LifecycleHarnessError("layout plan carries no partitions")
    device_size = int(getattr(plan, "device_size_bytes"))
    remainder_bytes = int(plan.remainder_bytes())  # type: ignore[attr-defined]
    cursor = int(LABEL_RESERVED_BYTES)
    if cursor % PARTITION_ALIGNMENT_BYTES:
        raise LifecycleHarnessError("label reservation breaks partition alignment")
    extents: dict[int, tuple[int, int]] = {}
    remainders = 0
    for partition in partitions:
        if cursor % PARTITION_ALIGNMENT_BYTES:
            raise LifecycleHarnessError(
                f"partition {partition.number} start breaks MiB alignment"
            )
        if cursor % _MBR_SECTOR_BYTES:
            raise LifecycleHarnessError(
                f"partition {partition.number} start breaks sector alignment"
            )
        start = cursor // _MBR_SECTOR_BYTES
        if partition.size_bytes is None:
            remainders += 1
            if partition.number != max(item.number for item in partitions):
                raise LifecycleHarnessError(
                    "the remainder partition must be the trailing partition"
                )
            if remainder_bytes <= 0:
                raise LifecycleHarnessError(
                    "layout plan carries no remainder coverage for persist"
                )
            count = (device_size - cursor) // _MBR_SECTOR_BYTES
            if cursor + count * _MBR_SECTOR_BYTES != device_size:
                raise LifecycleHarnessError(
                    "remainder extent does not fill the device size exactly"
                )
            if count * _MBR_SECTOR_BYTES != remainder_bytes:
                raise LifecycleHarnessError(
                    "persist extent does not equal plan.remainder_bytes()"
                )
            extents[partition.number] = (start, count)
            cursor = device_size
        else:
            size = int(partition.size_bytes)
            if size % PARTITION_ALIGNMENT_BYTES:
                raise LifecycleHarnessError(
                    f"partition {partition.number} size breaks MiB alignment"
                )
            count = size // _MBR_SECTOR_BYTES
            extents[partition.number] = (start, count)
            cursor += size
    if remainders != 1:
        raise LifecycleHarnessError("layout plan must carry exactly one remainder")
    if cursor != device_size:
        raise LifecycleHarnessError(
            "derived extents do not span the plan device size exactly"
        )
    return extents


def _mbr_table_span_bytes(plan: object) -> int:
    """Return the byte offset one past the last plan-derived partition extent."""
    extents = plan_mbr_sector_extents(plan)
    last_end = max(
        start + count for start, count in extents.values()
    )
    return last_end * _MBR_SECTOR_BYTES


def write_mbr_table_for_plan(
    image: Path, *, signature: str = _MBR_SIGNATURE, plan: object
) -> None:
    """Write a real DOS partition table matching the declarative plan.

    Extents come from ``plan_mbr_sector_extents`` (plan-derived, contiguous
    from the 1 MiB reserve with persist remainder-fill). Role numbers follow
    the legacy adapter: 1 boot-control, 2 system-a, 3 system-b, 4 persist.
    Type 0x83, bootable flag on partition 1.

    Fail-closed guard: refuses (raises :class:`LifecycleHarnessError`)
    when any planned partition extent end exceeds the actual image file
    sectors, so a size/geometry drift REDs at assembly instead of at
    live ``partprobe``.
    """
    table = bytearray(512)
    signature_value = int(signature, 16)
    table[440:444] = signature_value.to_bytes(4, "little")
    import struct as _struct

    extents = plan_mbr_sector_extents(plan)
    file_size = Path(image).stat().st_size
    file_sectors = file_size // _MBR_SECTOR_BYTES
    for number in (1, 2, 3, 4):
        start, count = extents[number]
        extent_end = start + count
        if extent_end > file_sectors:
            raise LifecycleHarnessError(
                f"planned partition {number} extent ends at sector {extent_end} "
                f"beyond image file sectors {file_sectors} "
                f"(size {file_size} bytes); refusing to write outside-disk table"
            )
    for number in (1, 2, 3, 4):
        start, count = extents[number]
        entry = _struct.pack(
            "<B3sB3sII",
            0x80 if number == 1 else 0x00,
            b"\x00\x00\x00",
            0x83,
            b"\x00\x00\x00",
            start,
            count,
        )
        table[446 + (number - 1) * 16 : 446 + number * 16] = entry
    table[510] = 0x55
    table[511] = 0xAA
    with open(image, "r+b") as handle:
        handle.seek(0)
        handle.write(bytes(table))
        handle.flush()
        os.fsync(handle.fileno())


def genuine_core_capability() -> dict[str, object]:
    """Report the capable-host genuine-GRUB capability (no mutation).

    The consumption mechanism is the guest ``save_env next_entry``
    consumer block executed by a genuine GRUB core built with the
    pinned ``(,msdos1)/`` root prefix; the frozen seam reads exactly
    that root (``/grub.cfg``/``/grubenv``). Off a capable host this
    reports unavailable and the caller keeps the source-scope stub
    core (armed-leg consumption stays RED by construction).
    """
    from .bootchain import grub_mkimage_available

    return {
        "grub_mkimage_available": bool(grub_mkimage_available()),
        "prefix": "(,msdos1)/",
        "mechanism": "guest save_env next_entry via the genuine core "
        "at the (,msdos1)/ root",
    }


def maybe_install_genuine_grub_core(
    image: Path, payload_manifest: object
) -> dict[str, object]:
    """Capable-host-only genuine-core upgrade over the stub chain.

    Reuses the reviewed helpers only: ``build_grub_core_via_mkimage``
    (pinned prefix + default module set), ``pad_core_bytes_to_sectors``,
    ``install_genuine_grub_chain`` (matching MBR load count + zeroed
    reservation tail), and the explicit ``rebind_payload_descriptor``
    path (previous-to-new evidence, never a silent overwrite).

    - Tool absent (``grub-mkimage`` missing): returns
      ``installed=False`` with reason
      ``grub-mkimage-absent:source-scope-stub``; the caller keeps the
      stub core and armed-leg consumption stays RED.
    - Tool present: builds/installs/rebinds and re-proves the gap
      guard; any build/install/rebind failure raises
      :class:`LifecycleHarnessError` fail-closed RED (never a silent
      stub fallback on a capable host, which would hide the breakage
      behind a bootable-but-unconsuming image).

    Pure file-offset writes (no loop/mount, no privilege); the frozen
    seam is untouched (no host stamping of ``next_entry``/``last_booted``).
    """
    from .bootchain import (
        BootchainError,
        build_grub_core_via_mkimage,
        grub_mkimage_available,
        install_genuine_grub_chain,
        pad_core_bytes_to_sectors,
    )
    from .payload import (
        PayloadError,
        rebind_payload_descriptor,
        verify_sector_gap_reserved,
    )

    if not grub_mkimage_available():
        return {
            "attempted": False,
            "installed": False,
            "chain": "stub",
            "reason": "grub-mkimage-absent:source-scope-stub",
        }
    try:
        with tempfile.TemporaryDirectory(prefix="greia-genuine-core-") as directory:
            core_path = Path(directory) / "core.img"
            mkimage = build_grub_core_via_mkimage(output=core_path)
            raw = core_path.read_bytes()
            padded = pad_core_bytes_to_sectors(raw)
            proof = install_genuine_grub_chain(Path(image), padded)
            rebind = rebind_payload_descriptor(
                Path(image),
                payload_manifest,  # type: ignore[arg-type]
                core_sha256=str(proof["core_sha256"]),
                core_sectors=int(proof["core_sectors"]),
            )
            guard = verify_sector_gap_reserved(Path(image))
    except (BootchainError, PayloadError, OSError) as exc:
        raise LifecycleHarnessError(
            f"genuine GRUB upgrade failed fail-closed: {exc}"
        ) from exc
    return {
        "attempted": True,
        "installed": True,
        "chain": "genuine",
        "mkimage": mkimage,
        "proof": proof,
        "previous": rebind["previous"],
        "descriptor": rebind["descriptor"],
        "gap": guard,
    }


#: Data partitions formatted with the record's filesystem UUIDs during
#: capable-host assembly (role -> DOS partition number). Partition 1
#: (boot-control) is excluded: the payload install owns its filesystem.
DATA_PARTITION_NUMBERS: dict[str, int] = {
    "system-a": 2,
    "system-b": 3,
    "persist": 4,
}


def format_data_partitions_for_record(image: Path, *, record_path: Path) -> dict[str, object]:
    """Format data partitions with the record's filesystem UUIDs (capable hosts).

    Device-only assembly step: loop-attaches the disposable image, rescans
    partitions, and formats system-a/system-b/persist with the exact
    filesystem UUIDs declared by the installed-layout record, so the
    post-run loop observation can bind observed topology to the record
    through real blkid probes. Partition 1 is never touched here; the
    payload install owns the boot-control filesystem (including its
    unprivileged-writer ownership).

    Off a capable host — or when loop attach itself is unavailable —
    returns deferred (source-scope never loop-observes, so there is nothing
    to bind). Once attached, any rescan/format/teardown failure raises
    :class:`LifecycleHarnessError` fail-closed: a half-formatted image must
    never proceed silently.
    """
    try:
        require_device_host()
    except LifecycleHarnessError as exc:
        return {"formatted": False, "reason": f"deferred: {exc}"}
    try:
        declared = json.loads(Path(record_path).read_text(encoding="utf-8"))
        wanted = {
            role: str(declared[role_key]["filesystem_uuid"])
            for role, role_key in (
                ("system-a", "system_a"),
                ("system-b", "system_b"),
                ("persist", "persist"),
            )
        }
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise LifecycleHarnessError(
            f"data-partition format needs record filesystem UUIDs: {exc}"
        ) from exc
    attached = run_device_host_tool(
        ["losetup", "--find", "--show", str(image)],
        capture_output=True, text=True, timeout=60,
    )
    if attached.returncode != 0:
        return {"formatted": False, "reason": "deferred: loop attach unavailable"}
    device = Path(str(attached.stdout).strip())
    if not device.is_absolute():
        run_device_host_tool(
            ["losetup", "--detach", str(device)], capture_output=True, timeout=60
        )
        return {"formatted": False, "reason": "deferred: loop attach unavailable"}
    try:
        rescan_loop_partitions(device)
        for role, number in DATA_PARTITION_NUMBERS.items():
            part = Path(f"{device}p{number}")
            if not part.exists():
                raise LifecycleHarnessError(
                    f"data-partition format: partition node missing for {role} "
                    f"({part}) after rescan"
                )
            formatted = run_device_host_tool(
                ["mkfs.ext4", "-U", wanted[role], str(part)],
                capture_output=True, text=True, timeout=120,
            )
            if formatted.returncode != 0:
                raise LifecycleHarnessError(
                    f"data-partition format failed for {role} ({part})"
                )
        return {"formatted": True, "roles": sorted(wanted)}
    finally:
        detached = run_device_host_tool(
            ["losetup", "--detach", str(device)], capture_output=True, timeout=60
        )
        if detached.returncode != 0:
            raise LifecycleHarnessError(
                f"data-partition format leaked loop device {device}"
            )


def assemble_disposable_image(output_dir: Path, *, image_bytes: int = 64 * 1024 * 1024) -> dict[str, object]:
    """Create the harness-owned disposable raw disk outside the source tree.

    Applies the real ``legacy-bios-ab-v1`` declarative plan facts, mints
    fresh role identities, proves the production-composed install service
    resolves in ``ab`` mode for the image-integration parameters, writes
    the real GRUB artifacts (rendered + validated ``grub.cfg``,
    initialized ``grubenv``), composes the T7-PAYLOAD minimal guest payload
    staging (production-rendered ``grub.cfg`` + production-initialized
    ``grubenv`` bound to the image by a descriptor sector), and records
    the image SHA-256 identity. Evidence lives only in ``output_dir``.
    """
    from greia_installer.layout import adapter_for, plan_for_profile
    from greia_platform.grub_ab import GrubEnvBackend

    from .payload import (
        compose_guest_payload,
        embed_payload_descriptor,
        payload_assembly_cost,
    )
    from .bootchain import install_boot_chain
    from .runner import (
        PROFILE_PERSIST_MINIMUM_BYTES,
        PROFILE_SLOT_BYTES,
        layout_plan_for_device,
        render_guest_grub_config,
        validate_guest_grub_config,
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    image = out / "greia-lifecycle-test.img"
    if image.exists():
        raise LifecycleHarnessError(f"refusing to replace existing image: {image}")
    plan = layout_plan_for_device(max(image_bytes, 3072 * 1024 * 1024))
    # The declarative plan is the single source of truth: the file is
    # exactly the plan size, and the plan-derived table span must agree
    # with it exactly (no max(...) growth past the plan). Any drift trips
    # the fail-closed guard below, naming partition/file sectors.
    plan_bytes = int(getattr(plan, "device_size_bytes"))
    span_bytes = _mbr_table_span_bytes(plan)
    if span_bytes != plan_bytes:
        raise LifecycleHarnessError(
            f"derived table span {span_bytes} bytes disagrees with plan "
            f"device size {plan_bytes} bytes; refusing a divergent geometry"
        )
    with open(image, "wb") as handle:
        handle.truncate(plan_bytes)
    write_mbr_table_for_plan(image, plan=plan)
    if Path(image).stat().st_size != plan_bytes:
        raise LifecycleHarnessError(
            "assembled image size drifted from the plan device size"
        )
    machine = fresh_machine_state(out / "machine")
    record = machine["layout"]
    # Capable-host step: format the data partitions with the record's
    # filesystem UUIDs so the post-run loop observation binds through real
    # blkid probes. Off a capable host this defers with a recorded reason
    # (source-scope never loop-observes); the frozen observation seam is
    # never touched host-side.
    data_filesystems = format_data_partitions_for_record(image, record_path=record)
    grub_text = render_guest_grub_config(
        _load_record(record), password_hash=_PASSWORD_HASH
    )
    validate_guest_grub_config(grub_text)
    (out / "machine" / "boot-control" / "grub.cfg").write_text(grub_text, encoding="utf-8")
    composition = prove_install_composition(
        out / "install-proof",
        layout_record_path=record,
        password_hash=_PASSWORD_HASH,
    )
    payload = compose_guest_payload(
        layout_record_path=record,
        password_hash=_PASSWORD_HASH,
        output_dir=out / "guest-payload",
    )
    # Guest boot chain first (MBR stub + stub core into the reserved gap),
    # then the descriptor binds staged payload AND installed core bytes, so
    # the image SHA computed below binds the whole chain.
    chain = install_boot_chain(image)
    embed_payload_descriptor(
        image,
        payload,
        core_sha256=str(chain["core_sha256"]),
        core_sectors=int(chain["core_sectors"]),
    )
    # G1 capable-host step: on a host with grub-mkimage, replace the
    # source-scope stub core with the genuine GRUB core (matching MBR
    # load count) and rebind the sector-2047 descriptor through the
    # explicit rebind path. Off a capable host this keeps the stub core
    # (armed-leg consumption stays RED by construction); the frozen
    # seam is never touched host-side.
    genuine = maybe_install_genuine_grub_core(image, payload)
    if bool(genuine.get("installed")):
        proof = genuine["proof"]
        assert isinstance(proof, dict)
        chain = {
            "mbr_stub_sha256": proof["mbr_stub_sha256"],
            "core_sha256": proof["core_sha256"],
            "core_sectors": proof["core_sectors"],
            "core_first_sector": proof["core_first_sector"],
            "core_last_reserved_sector": proof["core_last_reserved_sector"],
            "chain_bytes": proof["chain_bytes"],
            "mbr_load_sectors": proof["mbr_load_sectors"],
            "mbr_entry_sector": proof["mbr_entry_sector"],
        }
    cost = payload_assembly_cost(out / "guest-payload")
    guest_chain_bytes = int(chain["chain_bytes"]) + 512
    previous_binding: dict[str, object] | None = None
    mkimage_info: dict[str, object] | None = None
    if bool(genuine.get("installed")):
        previous = genuine["previous"]
        assert isinstance(previous, dict)
        previous_binding = {
            "core_sha256": previous["core_sha256"],
            "core_sectors": previous["core_sectors"],
        }
        mkimage_raw = genuine["mkimage"]
        assert isinstance(mkimage_raw, dict)
        mkimage_info = {
            "bytes": mkimage_raw.get("bytes"),
            "sha256": mkimage_raw.get("sha256"),
        }
    manifest: dict[str, object] = {
        "image": str(image),
        "image_sha256": sha256_file(image),
        "adapter": plan.adapter_id,
        "label_type": plan.label_type,
        "roles": [p.role for p in plan.partitions],
        "install_composition_mode": composition["install_mode"],
        "grub_cfg_bytes": len(grub_text.encode("utf-8")),
        "payload_magic": "GREIAPY1",
        "payload_descriptor": "sector-2047:512",
        "payload_grub_cfg_sha256": payload.grub_cfg_sha256,
        "payload_grubenv_sha256": payload.grubenv_sha256,
        "payload_grub_cfg_bytes": payload.grub_cfg_bytes,
        "payload_grubenv_bytes": payload.grubenv_bytes,
        "payload_guest_paths": ["/grub.cfg", "/grubenv"],
        "payload_files_touched": cost["files_touched"],
        "payload_whole_ram_copy": cost["whole_payload_ram_copy"],
        "guest_core_chain": str(genuine.get("chain")),
        "genuine_core_attempted": bool(genuine.get("attempted")),
        "genuine_core_installed": bool(genuine.get("installed")),
        "genuine_core_reason": str(genuine.get("reason", "genuine-installed")),
        "guest_mbr_stub_sha256": chain["mbr_stub_sha256"],
        "guest_core_sha256": chain["core_sha256"],
        "guest_core_sectors": chain["core_sectors"],
        "guest_core_first_sector": chain["core_first_sector"],
        "guest_core_last_reserved_sector": chain["core_last_reserved_sector"],
        "guest_chain_bytes": guest_chain_bytes,
        "data_filesystems": (
            "formatted:system-a,system-b,persist"
            if bool(data_filesystems.get("formatted"))
            else f"source-scope-deferred:{data_filesystems.get('reason')}"
        ),
    }
    if previous_binding is not None:
        manifest["genuine_previous_core_sha256"] = previous_binding["core_sha256"]
        manifest["genuine_previous_core_sectors"] = previous_binding["core_sectors"]
    if mkimage_info is not None:
        manifest["genuine_mkimage_bytes"] = mkimage_info["bytes"]
        manifest["genuine_mkimage_sha256"] = mkimage_info["sha256"]
    if "mbr_load_sectors" in chain:
        manifest["guest_mbr_load_sectors"] = chain["mbr_load_sectors"]
    if "mbr_entry_sector" in chain:
        manifest["guest_mbr_entry_sector"] = chain["mbr_entry_sector"]
    (out / "image-manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    void = {"adapter_for": adapter_for, "plan_for_profile": plan_for_profile,
            "persist_min": PROFILE_PERSIST_MINIMUM_BYTES, "slot": PROFILE_SLOT_BYTES,
            "backend": GrubEnvBackend}
    _ = void
    return manifest


def _load_record(path: Path):  # type: ignore[no-untyped-def]
    from greia_platform.system_updates import load_installed_layout_record

    record = load_installed_layout_record(Path(path))
    if record is None:
        raise LifecycleHarnessError("layout record is missing or not authoritative")
    return record


def prove_install_composition(
    root: Path, *, layout_record_path: Path, password_hash: str
) -> dict[str, object]:
    """Prove the production-composed install path resolves (no fabrication).

    Drives the shipped ``build_install_service`` builder with explicit
    image-integration seam/identity factories for a disposable A/B
    profile: asserts ``install_mode == "ab"`` with a bound executor, and
    asserts a missing-seams composition fails closed (never a silent
    legacy fallback). Returns the mode proof.
    """
    import shutil as _shutil
    import tempfile as _tempfile

    from greia_installer.composition import (
        AbInstallCompositionError,
        build_install_service,
        install_mode_for_state,
    )
    from greia_installer.disk import DeviceObservation
    from greia_installer.fresh_ab_install import FreshAbInstallError, FreshAbInstallSeams

    work = Path(root)
    if work.exists():
        _shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    profile_path = work / "target-image-profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile": {"id": "greia-lifecycle-proof"},
                "platform": {"family": "legacy-x86"},
                "base": {"architecture": "i386"},
                "storage": {
                    "layout_adapter": LAYOUT_ADAPTER_ID,
                    "system_slot_bytes": 1073741824,
                    "persistent_minimum_bytes": 268435456,
                },
                "installer": {"target_policy": "pc-internal-v1"},
                "updates": {"boot_backend": BOOT_BACKEND_ID},
            }
        ),
        encoding="utf-8",
    )
    project_root = PROJECT_ROOT
    from greia_installer.disk import DiskInventory, LiveMediaAncestry, PcInternalTargetPolicy
    from greia_installer.transaction_service import PlatformInstallAuthority, ServiceState
    from greia_platform.privileged_channel import PeerCredential

    _ = _tempfile
    target = DeviceObservation(
        path=Path("/dev/loop99"),
        device_type="disk",
        name="loop99",
        size_bytes=4 * 1024 * 1024 * 1024,
        model="T6 lifecycle disposable",
        serial="T6-LIFECYCLE-1",
        transport="loop",
        removable=False,
        read_only=False,
        mountpoints=(),
        wwn="WWN-T6-LIFECYCLE",
        major_minor="7:99",
    )

    class _Probe:
        def probe(self):  # type: ignore[no-untyped-def]
            return DiskInventory((target,), generation=1)

    class _Resolver:
        def resolve(self, inventory=None):  # type: ignore[no-untyped-def]
            return LiveMediaAncestry.empty()

    state = ServiceState.from_target_profile(
        profile_path,
        payload=work / "payload.bin",
        payload_digest=work / "contract.json",
        project_root=project_root,
        hardware_support_pool=None,
    )
    if install_mode_for_state(state) != "ab":
        raise LifecycleHarnessError("proof profile must compose in ab mode")
    authority = PlatformInstallAuthority(
        policy=PcInternalTargetPolicy(),
        compatible_profile="greia-lifecycle-proof",
        probe=_Probe(),  # type: ignore[arg-type]
        live_resolver=_Resolver(),  # type: ignore[arg-type]
    )

    from greia_platform.system_updates import (
        build_persistent_state_contract_bytes,
        build_update_bundle,
        inspect_update_bundle,
    )

    (work / "payload.bin").write_bytes(_payload_bytes(64 * 1024, b"t6-proof:"))
    (work / "hw.tar.zst").write_bytes(b"\x28\xb5\x2f\xfd" + b"t6-proof-hw" * 64)
    (work / "contract.json").write_bytes(build_persistent_state_contract_bytes())
    private = work / "priv.pem"
    public = work / "pub.pem"
    from greia_platform.system_updates import generate_ed25519_keypair

    generate_ed25519_keypair(private, public)
    key_dir = work / "trusted"
    key_dir.mkdir(exist_ok=True)
    (key_dir / f"{_SIGNER}.pem").write_bytes(public.read_bytes())
    bundle = work / "proof.greiaupdate"
    build_update_bundle(
        payload_path=work / "payload.bin",
        hardware_support_path=work / "hw.tar.zst",
        persistent_contract_path=work / "contract.json",
        output_path=bundle,
        version="0.20.0",
        release_id="greia-0.20.0",
        release_sequence=20,
        platform_family="legacy-x86",
        architecture="i386",
        profile="greia-lifecycle-proof",
        signer=_SIGNER,
        private_key_path=private,
    )
    manifest = inspect_update_bundle(bundle).manifest

    observed = {
        "system-a": {"filesystem_uuid": _UUID_A_FS,
                      "partuuid": f"{_MBR_SIGNATURE}-02",
                      "scheme": "MBR_PARTUUID"},
        "system-b": {"filesystem_uuid": _UUID_B_FS,
                      "partuuid": f"{_MBR_SIGNATURE}-03",
                      "scheme": "MBR_PARTUUID"},
        "persist": {"filesystem_uuid": _UUID_P_FS,
                    "partuuid": f"{_MBR_SIGNATURE}-04",
                    "scheme": "MBR_PARTUUID"},
    }

    from greia_installer.persist import PersistCommandResult, PersistCommandRunner
    from greia_platform.slot_writer import SlotFinalizeError

    class _PartitionRunner:
        def __init__(self) -> None:
            self.commands: list[list[str]] = []

        def run(self, command) -> None:  # type: ignore[no-untyped-def]
            self.commands.append(list(command))
            return None

    class _SparseStorage:
        def __init__(self, capacity_bytes: int) -> None:
            self._capacity = capacity_bytes
            self._chunks: dict[int, bytes] = {}

        @property
        def capacity_bytes(self) -> int:
            return self._capacity

        def write_at(self, offset: int, data: bytes) -> None:
            self._chunks[offset] = bytes(data)

        def read_at(self, offset: int, length: int) -> bytes:
            assembled = bytearray(length)
            for start, chunk in self._chunks.items():
                lo = max(offset, start)
                hi = min(offset + length, start + len(chunk))
                if lo < hi:
                    assembled[lo - offset : hi - offset] = chunk[lo - start : hi - start]
            return bytes(assembled)

        def flush(self) -> None:
            return None

    class _SlotFilesystem:
        def __init__(self, mount_dir: Path) -> None:
            self._mount_dir = mount_dir
            self.mounted = False

        def bind_filesystem_uuid(self, filesystem_uuid: str) -> None:
            pass

        def expand_to_capacity(self) -> None:
            pass

        def mount(self) -> Path:
            self.mounted = True
            self._mount_dir.mkdir(parents=True, exist_ok=True)
            return self._mount_dir

        def unmount(self) -> None:
            self.mounted = False

        def sync(self) -> None:
            pass

        def write_file(self, relative_path: str, data: bytes) -> None:
            if not self.mounted:
                raise SlotFinalizeError("slot writes require a mounted destination")

        def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]:
            return ()

        def check_health(self) -> None:
            pass

    class _PackageInstaller:
        def install(self, firmware, microcode):  # type: ignore[no-untyped-def]
            return ()

    class _PersistRunner(PersistCommandRunner):
        def __init__(self) -> None:
            self._blkid_calls = 0

        def run(self, command) -> PersistCommandResult:  # type: ignore[no-untyped-def]
            if command[0] == "blkid":
                self._blkid_calls += 1
                if self._blkid_calls == 1:
                    return PersistCommandResult(stdout="", returncode=1)
                return PersistCommandResult(stdout=_UUID_P_FS, returncode=0)
            return PersistCommandResult(stdout="", returncode=0)

    (work / "persist-stage").mkdir(exist_ok=True)
    (work / "boot-control").mkdir(exist_ok=True)
    (work / "backend-state").mkdir(exist_ok=True)
    (work / "journal").mkdir(exist_ok=True)
    (work / "slot-a-mnt").mkdir(exist_ok=True)
    runner = _PartitionRunner()

    def _seams(target):  # type: ignore[no-untyped-def]
        import uuid as _uuid

        return FreshAbInstallSeams(
            partition_runner=runner,  # type: ignore[arg-type]
            slot_storage_factory=lambda role: _SparseStorage(1073741824),
            slot_filesystem_factory=lambda: _SlotFilesystem(work / "slot-a-mnt"),
            package_installer_factory=_PackageInstaller,
            inventory_token="cd" * 32,
            support_digest=manifest.hardware_support_sha256,
            support_size=manifest.hardware_support_size,
            support_installed_bound=0,
            persist_runner=_PersistRunner(),
            persist_stage_dir=work / "persist-stage",
            persist_uuid_factory=lambda: _uuid.UUID(_UUID_P_FS),
            boot_control_dir=work / "boot-control",
            backend_state_dir=work / "backend-state",
            journal_dir=work / "journal",
        )

    def _identities(target):  # type: ignore[no-untyped-def]
        if not isinstance(target, DeviceObservation):
            raise FreshAbInstallError("identities need a rematerialized target")
        return observed

    service = build_install_service(
        state=state,
        authority=authority,
        ab_release_bundle=bundle,
        ab_trusted_key_dir=key_dir,
        ab_password_hash=password_hash,
        ab_developer=False,
        ab_support_installed_bytes=0,
        ab_seams_factory=_seams,
        ab_identities_factory=_identities,
    )
    if service.install_mode != "ab" or service.ab_executor is None:
        raise LifecycleHarnessError("install service did not compose in ab mode")
    # Execute through the shipped installer protocol (PREPARE then EXECUTE):
    # the signed release must flow into destruction through the composed
    # path, landing grub.cfg + grubenv default A + FIRST_INSTALL_PENDING.
    from greia_installer.transaction_client import InstallTransactionClient
    from greia_platform.grub_ab import GrubEnvBackend as _Backend
    from greia_platform.boot_transaction import (
        BootTransactionJournal as _Journal,
        BootTransactionState as _State,
    )

    client = InstallTransactionClient(
        lambda raw: service.handle_request(
            raw, peer=PeerCredential(uid=65534), boot_state="installer_ready"
        )
    )
    prepared = client.prepare(
        expected_target_identity=authority.list_targets()[0].identity_digest,
        compatible_profile_id="greia-lifecycle-proof",
        settings_snapshot={
            "touchpad_tap": "false",
            "touchpad_speed": "0.35",
            "mouse_speed": "0.0",
            "natural_scrolling": "false",
            "resolution": "auto",
            "keyboard_layout": "us",
            "mic_gain": "2.0",
            "disable_while_typing": "false",
            "locale": "en",
        },
    )
    receipt = client.execute(
        transaction_nonce=prepared.transaction_nonce,
        plan_digest=prepared.plan_digest,
    )
    if receipt.target_identity != service._last_installed_identity:
        raise LifecycleContractError("install EXECUTE receipt is not bound")
    if not runner.commands or runner.commands[0][0] != "wipefs":
        raise LifecycleContractError("install did not drive the partition runner")
    grub_cfg = work / "boot-control" / "grub.cfg"
    if not grub_cfg.is_file():
        raise LifecycleContractError("install produced no boot-control grub.cfg")
    from greia_platform.grub_ab import validate_grub_ab_text

    validate_grub_ab_text(grub_cfg.read_text(encoding="utf-8"))
    if _Backend.attach(work / "backend-state").inspect().default_slot != "A":
        raise LifecycleContractError("install did not default to slot A")
    journal = _Journal.load(work / "journal")
    if journal.state is not _State.FIRST_INSTALL_PENDING or not journal.first_install:
        raise LifecycleContractError("install did not open FIRST_INSTALL_PENDING")
    executed = {
        "install_mode": service.install_mode,
        "grub_cfg_bytes": grub_cfg.stat().st_size,
        "journal_state": journal.state.value,
    }
    # Fail-closed: missing seam/identity factories never build a half-wired
    # executor and never fall back to the legacy engine.
    try:
        build_install_service(
            state=state,
            authority=authority,
            ab_release_bundle=bundle,
            ab_trusted_key_dir=key_dir,
            ab_password_hash=password_hash,
            ab_developer=False,
            ab_support_installed_bytes=0,
            ab_seams_factory=None,
            ab_identities_factory=_identities,
        )
    except AbInstallCompositionError:
        half_wired_refused = True
    else:
        half_wired_refused = False
    if not half_wired_refused:
        raise LifecycleContractError("half-wired install composition was not refused")
    _ = (PeerCredential, layout_record_path)
    return {"install_mode": executed["install_mode"],
            "half_wired_refused": True,
            "journal_state": executed["journal_state"],
            "grub_cfg_bytes": executed["grub_cfg_bytes"]}


# ---------------------------------------------------------------------------
# T7-DEVRUN3 device-boot observation (frozen attestation seam, device only)
# ---------------------------------------------------------------------------

#: Armed one-shot target per boot-outcome leg (None = plain default boot).
#: The guest never stamps ``greia_last_booted`` (the production grub.cfg
#: only clears ``next_entry``), so the device pull derives the observed
#: slot from on-image consumption evidence: pre-boot arm + post-boot
#: absence of the one-shot (armed legs), or the post-boot default itself
#: (plain legs). Sensitivity to guest behavior lives in that pre/post
#: comparison; the uniform ``read_attestation_signal`` gate runs after
#: the production ``reconcile`` stamps the derived observation.
DEVICE_BOOT_ARMED_TARGET: dict[str, str | None] = {
    "boot-A-accepted": None,
    "boot-B-commit": "B",
    "boot-broken-candidate": "A",
    "recovery-boot-B": None,
    "reverse-update-B-to-A": "A",
}


def check_boot_exit(returncode: int, *, leg: str, qemu_log: Path) -> None:
    """Clean-exit gate (fixer-1, verbatim): unclean QEMU exit is RED.

    A nonzero status (or a timeout, raised by the caller) never becomes
    a claimed boot: the leg fails closed here before any observation.
    """
    if returncode != 0:
        raise LifecycleHarnessError(
            f"device boot leg {leg} exited with status {returncode}; "
            f"inspect {qemu_log} (unclean exit is RED, never a claimed boot)"
        )


def device_gate_for_image(image: Path) -> dict[str, object]:
    """Payload + sector-gap + boot-chain gate for the real boot path.

    A payload-less/tampered/chain-less image REDs here — in the device
    body before any QEMU boot is claimed — not only in the helper unit
    tests. The sector 1-2047 gap reservation (relocated descriptor +
    hash-bound core) is pinned alongside the MBR boot code, so a
    chain-less MBR can never reach a green exit claim through this gate.
    """
    from .bootchain import verify_boot_chain_present
    from .payload import assert_payload_present, verify_sector_gap_reserved

    descriptor = assert_payload_present(Path(image))
    gap = verify_sector_gap_reserved(Path(image))
    chain = verify_boot_chain_present(Path(image))
    return {"descriptor": descriptor, "gap": gap, "chain": chain}


def bind_gate_to_install(
    gate: Mapping[str, object], install_proof: Mapping[str, object]
) -> None:
    """Bind the image descriptor to the installed payload (fail-closed).

    The device body installs the staged payload onto partition 1 and
    then boots it; the descriptor sector must name exactly the installed
    bytes, or a swapped/tampered image could boot unrelated guest bytes
    while carrying a well-formed descriptor. Any mismatch is RED.
    """
    descriptor = gate.get("descriptor")
    if not isinstance(descriptor, dict):
        raise LifecycleHarnessError("device gate produced no payload descriptor")
    for key in ("grub_cfg_sha256", "grubenv_sha256"):
        if descriptor.get(key) != install_proof.get(key):
            raise LifecycleHarnessError(
                f"image descriptor {key} does not match the installed payload"
            )


def device_qemu_argv(
    image: Path,
    *,
    output_dir: Path,
    leg: str,
    memory_mib: int,
    cpus: int,
    seabios_path: Path | None,
) -> tuple[list[str], Path, Path]:
    """Real SeaBIOS boot argv for one device boot leg (argument arrays).

    Legacy ``pc`` machine (SeaBIOS default firmware), IDE raw disk,
    strict HD boot order, ``-no-reboot`` (guest writes persist for the
    post-boot observation), no network, headless. Per-leg serial/host
    logs live in the harness output dir (outside the source tree).
    """
    serial_log = Path(output_dir) / f"device-{leg}-serial.log"
    host_log = Path(output_dir) / f"device-{leg}-qemu.log"
    argv = [
        QEMU_BINARY,
        "-name",
        f"greia-device-{leg}",
        "-machine",
        "pc,accel=tcg",
        "-cpu",
        "max",
        "-m",
        str(memory_mib),
        "-smp",
        str(cpus),
        "-display",
        "none",
        "-monitor",
        "none",
        "-serial",
        f"file:{serial_log}",
        "-nic",
        "none",
        "-boot",
        "order=c,strict=on",
        "-no-reboot",
    ]
    if seabios_path is not None:
        argv.extend(["-bios", str(seabios_path)])
    argv.extend(
        [
            "-drive",
            f"file={image},format=raw,if=ide,index=0,media=disk,cache=writeback",
        ]
    )
    return argv, serial_log, host_log


def decide_device_boot_observation(
    *,
    leg: str,
    pre: Mapping[str, object],
    post: Mapping[str, object],
) -> str:
    """Pure device-observation decision from on-image pre/post grubenv bytes.

    ``pre``/``post`` carry ``default_slot``/``one_shot_slot`` as read
    from the image (loop-mounted partition 1) before and after one real
    SeaBIOS boot. Returns the guest-observed slot; raises
    :class:`LifecycleHarnessError` RED when the bytes show no guest
    consumption:

    - N1-live (same-disk reboot without transitions): an armed leg whose
      pre-boot image carries no staged one-shot for its target REDs —
      there is no transition to attest.
    - N2-live (armed-but-unconsumed): a pre-armed one-shot still present
      post-boot REDs — the guest did not consume it.
    - Plain legs (no armed target) attest the post-boot default read
      from the image; any armed one-shot pre or post REDs, as does a
      default that names a different slot.
    """
    if leg not in BOOT_OUTCOME_LEGS or leg not in DEVICE_BOOT_ARMED_TARGET:
        raise LifecycleContractError(
            f"device boot leg {leg!r} is not a frozen boot-outcome leg"
        )
    expected = BOOT_OUTCOME_EXPECTED_SLOT[leg]
    target = DEVICE_BOOT_ARMED_TARGET[leg]
    if target is not None:
        if pre.get("one_shot_slot") != target:
            raise LifecycleHarnessError(
                f"device boot leg {leg} has no staged transition on image: "
                f"pre-boot one-shot is {pre.get('one_shot_slot')!r}, "
                f"expected armed {target!r} (same-disk reboot without "
                "transitions must not attest)"
            )
        if post.get("one_shot_slot") is not None:
            raise LifecycleHarnessError(
                f"device boot leg {leg} armed-but-unconsumed: post-boot "
                f"one-shot still targets {post.get('one_shot_slot')!r} "
                "(the guest did not consume it)"
            )
        return target
    if pre.get("one_shot_slot") is not None:
        raise LifecycleHarnessError(
            f"device boot leg {leg} is a plain default boot but the "
            f"pre-boot image carries an armed one-shot "
            f"({pre.get('one_shot_slot')!r})"
        )
    if pre.get("default_slot") != expected:
        raise LifecycleHarnessError(
            f"device boot leg {leg} pre-boot default is "
            f"{pre.get('default_slot')!r}, expected {expected!r}"
        )
    if post.get("one_shot_slot") is not None:
        raise LifecycleHarnessError(
            f"device boot leg {leg} post-boot image carries an unexpected "
            f"one-shot ({post.get('one_shot_slot')!r})"
        )
    if post.get("default_slot") != expected:
        raise LifecycleHarnessError(
            f"device boot leg {leg} post-boot default is "
            f"{post.get('default_slot')!r}, expected {expected!r}"
        )
    observed = post["default_slot"]
    assert isinstance(observed, str)
    return observed


# ---------------------------------------------------------------------------
# DIAG-C1 fail-collect observation mode (device harness reporting layer)
# ---------------------------------------------------------------------------
#
# Fail-collect widens OBSERVATION only. Every lifecycle leg, the post-run
# loop/cross-check binding, and the devproof device envelope execute under
# per-leg capture; an observed RED is recorded with full context and the
# run continues under ``COLLECT_CONTINUATION_RULES``. The frozen
# attestation predicates (:func:`decide_device_boot_observation`,
# :func:`check_boot_exit`, ``read_attestation_signal``) are *called*,
# never redefined: a collected RED carries the verbatim fail-fast error,
# so single-fault equivalence holds by construction. Abort-class
# conditions (teardown/loop-detach safety, destructive-bound violations)
# raise :class:`CollectAbortError` and stop the run immediately, fail
# closed. Aggregated reporting never converts a RED to green/yellow.

#: Fail-collect leg order: the 8 lifecycle legs plus the post-run
#: loop/cross-check binding and the devproof device envelope.
COLLECT_LEG_ORDER: tuple[str, ...] = tuple(LIFECYCLE_SEQUENCE) + (
    "post-run-loop-cross-check",
    "devproof-device-envelope",
)

#: Abort-class gates: a RED here stops collection immediately, fail
#: closed. Never collected, never skipped past.
COLLECT_ABORT_GATES: frozenset[str] = frozenset({
    "teardown-loop-detach-safety",
    "destructive-bound-violation",
})

#: Observed gates: a RED here is recorded with full context while the run
#: continues. Production/device behavior behind these gates stays
#: fail-fast and fail-closed; collection never weakens, bypasses, or
#: converts their predicates.
COLLECT_OBSERVED_GATES: frozenset[str] = frozenset({
    "require_device_host",
    "device_gate_for_image",
    "clean-exit-gate",
    "consumption-predicate",
    "attestation-binding",
    LOOP_RESCAN_GATE,
    "post-run-loop-cross-check",
    "devproof-device-envelope",
})

#: Explicit continuation rules (this tuple and LIFECYCLE.md carry the
#: same list; code is authoritative for behavior):
#: 1. every boot-outcome leg re-reads on-image state independently
#:    (fresh pre/post per leg; no leg consumes another leg's cached
#:    observation);
#: 2. a RED boot leg never blocks later stage/boot legs;
#: 3. a RED stage/arm leg never blocks later legs either: each later leg
#:    re-syncs and re-reads image state, REDing under its own frozen
#:    predicate when its preconditions are absent;
#: 4. the post-run loop/cross-check binding is always attempted with its
#:    own capture, even with prior reds;
#: 5. the devproof device envelope is always attempted with its own
#:    capture, even with prior reds;
#: 6. only abort-class conditions stop the run; nothing is skipped after
#:    an observed RED (a leg whose preconditions are absent REDs under
#:    its own frozen predicate instead of being skipped, so the full red
#:    set stays observable).
COLLECT_CONTINUATION_RULES: tuple[str, ...] = (
    "each boot-outcome leg re-reads on-image state independently; "
    "no leg consumes another leg's cached observation",
    "a RED boot leg never blocks later stage/boot legs",
    "a RED stage/arm leg never blocks later legs; each later leg "
    "re-syncs and re-reads image state and REDs under its own frozen "
    "predicate when its preconditions are absent",
    "the post-run loop/cross-check binding is always attempted with "
    "its own capture once setup yields an image, even with prior reds",
    "the devproof device envelope is always attempted with its own "
    "capture once setup yields an image, even with prior reds",
    "only abort-class conditions stop the run; nothing is skipped "
    "after an observed RED, except the no-image fail-closed early "
    "return (setup never produced an image, so boots/bindings have "
    "no image to observe)",
)

#: Frozen-predicate descriptions recorded per gate (wording only; the
#: predicate itself lives in the named production function).
COLLECT_FROZEN_PREDICATES: dict[str, str] = {
    "require_device_host": (
        "Linux host, root (direct, or owner-provisioned passwordless sudo "
        "for the bounded harness binary set), and qemu/losetup/mount/umount/"
        "partprobe/udevadm/mkfs.ext4/blkid/sfdisk present "
        "(require_device_host)"
    ),
    "device_gate_for_image": (
        "payload descriptor present plus sector 1-2047 gap reserved "
        "plus boot chain present (device_gate_for_image)"
    ),
    "clean-exit-gate": (
        "QEMU process exits 0 before the leg timeout "
        "(check_boot_exit; timeout/silence/stall RED via "
        "bootchain.wait_for_clean_exit)"
    ),
    "consumption-predicate": (
        "decide_device_boot_observation on on-image pre/post grubenv "
        "bytes: pre-armed one-shot absent post-boot (armed legs), or "
        "post-boot default equals expected with no armed one-shot "
        "(plain legs)"
    ),
    "attestation-binding": (
        "read_attestation_signal through the post-boot loop "
        "remount/read path: next_entry absent AND "
        "last_booted == expected"
    ),
    LOOP_RESCAN_GATE: (
        "post-run loop-attach partition rescan: partitions surface "
        "for production observation within bounded retries "
        f"({LOOP_RESCAN_GATE})"
    ),
    "post-run-loop-cross-check": (
        "observe_loop_attached_device green plus run_file_cross_check "
        "executed-and-green on a capable host"
    ),
    "devproof-device-envelope": (
        "run_envelope_device device-measured D31/interruption/resource/"
        "cgroup predicates RED fail the device run closed"
    ),
    "teardown-loop-detach-safety": (
        "loop detach and partition-1 unmount succeed; any teardown "
        "failure aborts immediately, fail closed"
    ),
    "destructive-bound-violation": (
        "no write outside disposable paths, no non-absolute device "
        "path, no extent beyond the image file; any violation aborts "
        "immediately, fail closed"
    ),
}


class CollectAbortError(LifecycleHarnessError):
    """Abort-class collect failure (teardown/destructive safety).

    Never collected, never skipped past: the collect runner records the
    abort entry and re-raises immediately, fail closed.
    """


@dataclass(frozen=True, slots=True)
class LegTimeoutPolicy:
    """Progress-aware per-leg timeout policy (record layer).

    The real wait mechanism stays ``bootchain.wait_for_clean_exit``,
    called by ``_boot_image_once``: serial-byte growth and image SHA
    delta count as progress, the leg timeout is the hard ceiling, and
    silence plus progress-then-stall are RED. This policy only names the
    thresholds for per-leg timeout/progress detail in the diagnostics
    artifact, so a hung leg's evidence always carries the ceiling it ran
    against. Threshold defaults mirror the bootchain frozen predicates
    (pinned equal by test, never copied silently).
    """

    timeout_seconds: float
    no_progress_seconds: float = 120.0
    stall_seconds: float = 120.0

    def describe(self) -> dict[str, object]:
        return {
            "timeout_seconds": float(self.timeout_seconds),
            "no_progress_seconds": float(self.no_progress_seconds),
            "stall_seconds": float(self.stall_seconds),
            "progress rule": (
                "serial-byte growth and image SHA delta count as "
                "progress; the leg timeout is the hard ceiling; "
                "silence and progress-then-stall are RED with the "
                "timeout recorded"
            ),
        }

    def classify(
        self,
        *,
        serial_growth_bytes: int,
        image_sha_changed: bool,
        elapsed_seconds: float,
        clean_exit: bool,
    ) -> dict[str, object]:
        """Classify one leg's progress/timeout evidence (record-only).

        Mirrors the ``wait_for_clean_exit`` frozen predicates without
        reimplementing the wait: timeout ceiling first, then silence
        (no progress evidence past ``no_progress_seconds``), then
        progress-then-stall (progress observed, no clean exit, past
        ``stall_seconds``), else progress-clean / in-progress.
        """
        progress = bool(serial_growth_bytes > 0 or image_sha_changed)
        if elapsed_seconds >= float(self.timeout_seconds):
            outcome = "timeout"
            red = True
        elif not progress and elapsed_seconds >= float(self.no_progress_seconds):
            outcome = "silence"
            red = True
        elif progress and not clean_exit and elapsed_seconds >= float(self.stall_seconds):
            outcome = "progress-then-stall"
            red = True
        elif clean_exit:
            outcome = "progress-clean" if progress else "clean-no-progress"
            red = False
        else:
            outcome = "in-progress"
            red = False
        return {
            "outcome": outcome,
            "red": red,
            "timeout_seconds": float(self.timeout_seconds),
            "no_progress_seconds": float(self.no_progress_seconds),
            "stall_seconds": float(self.stall_seconds),
            "serial_growth_bytes": int(serial_growth_bytes),
            "image_sha_changed": bool(image_sha_changed),
            "elapsed_seconds": float(elapsed_seconds),
            "clean_exit": bool(clean_exit),
            "detail": (
                f"leg {outcome}: serial_growth={int(serial_growth_bytes)}B "
                f"image_changed={bool(image_sha_changed)} "
                f"elapsed={float(elapsed_seconds):.1f}s "
                f"ceiling={float(self.timeout_seconds):.1f}s"
            ),
        }


#: Evidence keys normalized into every diagnostics red entry (missing
#: keys record as None; never synthesized green).
COLLECT_RED_EVIDENCE_KEYS: tuple[str, ...] = (
    "returncode",
    "serial_log",
    "qemu_log",
    "serial_bytes",
    "serial_growth_bytes",
    "image_sha256_pre",
    "image_sha256_post",
    "on_image_pre",
    "on_image_post",
    "disk_snapshot",
    "timeout",
)


@dataclass
class DeviceCollectRecorder:
    """Per-run fail-collect recorder for the device harness.

    Owns the collect-vs-abort boundary: :class:`CollectAbortError`
    records an abort entry and re-raises immediately (fail closed);
    any other ``Exception`` (including the fail-fast
    :class:`LifecycleHarnessError` REDs with their verbatim messages)
    records an observed red and lets the run continue under
    ``COLLECT_CONTINUATION_RULES``. ``BaseException`` (keyboard
    interrupt, system exit) is never caught.
    """

    reds: list[dict[str, object]] = field(default_factory=list)
    attempted: list[str] = field(default_factory=list)
    abort: dict[str, object] | None = None

    def run_leg(
        self,
        *,
        leg: str,
        gate: str,
        frozen_predicate: str,
        run: Callable[[], object],
        context: Callable[[], Mapping[str, object]] | None = None,
    ) -> object | None:
        """Execute one collect unit; return its result or None on RED.

        On observed RED the verbatim error is recorded with the leg's
        gate, frozen predicate, and best-effort context, and None is
        returned so the run continues. On abort-class failure the abort
        entry is recorded and the error re-raised immediately.
        """
        self.attempted.append(leg)
        try:
            return run()
        except CollectAbortError as exc:
            entry = self._entry(
                leg=leg, gate=gate, frozen_predicate=frozen_predicate,
                error=exc, abort=True, context=context,
            )
            self.reds.append(entry)
            self.abort = entry
            raise
        except Exception as exc:
            self.reds.append(self._entry(
                leg=leg, gate=gate, frozen_predicate=frozen_predicate,
                error=exc, abort=False, context=context,
            ))
            return None

    def _entry(
        self,
        *,
        leg: str,
        gate: str,
        frozen_predicate: str,
        error: BaseException,
        abort: bool,
        context: Callable[[], Mapping[str, object]] | None,
    ) -> dict[str, object]:
        evidence: dict[str, object] = {}
        if context is not None:
            try:
                raw = context()
                evidence = dict(raw) if isinstance(raw, Mapping) else {}
            except Exception as exc:
                evidence = {"context_error": f"{type(exc).__name__}: {exc}"}
        normalized = {key: evidence.get(key) for key in COLLECT_RED_EVIDENCE_KEYS}
        return {
            "leg": leg,
            "gate": gate,
            "frozen_predicate": frozen_predicate,
            "error_type": type(error).__name__,
            "error": str(error),
            "abort": abort,
            **normalized,
        }

    def verdict(self) -> dict[str, object]:
        """Aggregate ALL reds; never converts a RED to green/yellow."""
        red_count = len(self.reds)
        return {
            "ok": red_count == 0 and self.abort is None,
            "red_count": red_count,
            "legs_attempted": list(self.attempted),
            "aborted": self.abort is not None,
            "note": (
                "aggregated reporting: every recorded RED stays RED; "
                "collection widens observation only"
            ),
        }


def run_collect_sequence(
    legs: Sequence[Mapping[str, object]],
    recorder: DeviceCollectRecorder,
) -> dict[str, object]:
    """Drive one fail-collect sequence through ``recorder``.

    Each leg maps ``leg``/``gate``/``frozen_predicate``/``run`` with an
    optional ``context`` callable for failure evidence. Observed REDs
    record and continue; abort-class re-raises immediately after
    recording. Returns the aggregated verdict (observed REDs do not
    raise).
    """
    for spec in legs:
        run = spec["run"]
        assert callable(run)
        context = spec.get("context")
        assert context is None or callable(context)
        recorder.run_leg(
            leg=str(spec["leg"]),
            gate=str(spec["gate"]),
            frozen_predicate=str(spec["frozen_predicate"]),
            run=run,  # type: ignore[arg-type]
            context=context,  # type: ignore[arg-type]
        )
    return recorder.verdict()


def snapshot_device_collect_state(
    *,
    image: Path | None = None,
    machine: Mapping[str, Path] | None = None,
) -> dict[str, object]:
    """Best-effort disk-state snapshot for one diagnostics entry.

    Records image SHA plus host backend slot state, journal state,
    accepted slot/release/sequence, and the PERSIST marker; any
    unreadable part records None (never raises, never synthesizes).
    """
    snapshot: dict[str, object] = {
        "image_sha256": None,
        "default_slot": None,
        "one_shot_slot": None,
        "last_booted_slot": None,
        "journal_state": None,
        "journal_candidate": None,
        "accepted_slot": None,
        "accepted_release": None,
        "accepted_sequence": None,
        "persist_marker": None,
    }
    try:
        if image is not None and Path(image).is_file():
            snapshot["image_sha256"] = sha256_file(Path(image))
        if machine is not None:
            from greia_platform.grub_ab import GrubEnvBackend

            try:
                state = GrubEnvBackend.attach(
                    Path(machine["boot_control"])).inspect()
                snapshot["default_slot"] = state.default_slot
                snapshot["one_shot_slot"] = state.one_shot_slot
                snapshot["last_booted_slot"] = state.last_booted_slot
            except Exception as exc:
                snapshot["backend_error"] = f"{type(exc).__name__}: {exc}"
            try:
                from greia_platform.boot_transaction import BootTransactionJournal

                journal = BootTransactionJournal.load(
                    Path(machine["state"]) / "system-updates" / "journal"
                )
                snapshot["journal_state"] = journal.state.value
                snapshot["journal_candidate"] = journal.candidate_slot
            except Exception as exc:
                snapshot["journal_error"] = f"{type(exc).__name__}: {exc}"
            try:
                record = _load_record(Path(machine["layout"]))
                snapshot["accepted_slot"] = record.accepted_slot
                snapshot["accepted_release"] = record.accepted_release_id
            except Exception as exc:
                snapshot["record_error"] = f"{type(exc).__name__}: {exc}"
            try:
                from greia_platform.system_updates import read_accepted_sequence

                snapshot["accepted_sequence"] = read_accepted_sequence(
                    Path(machine["state"]))
            except Exception as exc:
                snapshot["sequence_error"] = f"{type(exc).__name__}: {exc}"
            try:
                persist_profile = Path(machine["persist"]) / "profile.json"
                if persist_profile.is_file():
                    snapshot["persist_marker"] = sha256_file(persist_profile)
            except Exception as exc:
                snapshot["persist_error"] = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        snapshot["snapshot_error"] = f"{type(exc).__name__}: {exc}"
    return snapshot


def build_device_collect_diagnostics(
    recorder: DeviceCollectRecorder,
    *,
    run_meta: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build the per-run diagnostics artifact from the recorder.

    Contains, per red: gate name, frozen predicate, leg name, error
    (verbatim fail-fast RED), abort flag, return code, serial
    bytes/growth, QEMU/host log paths, on-image pre/post grubenv bytes,
    disk state snapshot, and timeout/progress detail. The final verdict
    aggregates ALL reds and never converts a RED to green/yellow.
    """
    meta = dict(run_meta) if isinstance(run_meta, Mapping) else {}
    verdict = recorder.verdict()
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact": "greia-device-collect-diagnostics",
        "collect_mode": True,
        "run_meta": meta,
        "continuation_rules": list(COLLECT_CONTINUATION_RULES),
        "abort_boundary": {
            "abort_gates": sorted(COLLECT_ABORT_GATES),
            "observed_gates": sorted(COLLECT_OBSERVED_GATES),
            "rule": (
                "teardown/loop-detach safety and destructive-bound "
                "violations abort immediately and fail closed; "
                "require_device_host, clean-exit gate predicates, "
                "consumption checks, and attestation binding predicates "
                "are observed and recorded but their REDs are never "
                "weakened, bypassed, or converted"
            ),
        },
        "collect_leg_order": list(COLLECT_LEG_ORDER),
        "legs_attempted": list(recorder.attempted),
        "reds": [dict(entry) for entry in recorder.reds],
        "verdict": verdict,
    }


def write_device_collect_diagnostics(
    output_dir: Path, artifact: Mapping[str, object]
) -> Path:
    """Write the diagnostics artifact for one collect run."""
    path = Path(output_dir) / "greia-device-collect-diagnostics.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, sort_keys=True, indent=2) + "\n",
                     encoding="utf-8")
    return path


@dataclass
class BootLegCapture:
    """Live boot-evidence holder for one collect boot leg.

    ``run_device_collect`` populates this progressively inside
    ``_collect_boot_leg`` (pre → boot → post → elapsed) so the
    recorder's failure context can forward the evidence that exists
    at the throw site. ``to_context`` builds the same evidence shape
    as the collect ``_context_for`` closure (returncode, serial
    bytes/growth, log paths, on-image pre/post, disk snapshot,
    timeout/progress detail) from the captured partial state.
    """

    pre: dict[str, object] | None = None
    boot: dict[str, object] | None = None
    post: dict[str, object] | None = None
    elapsed_seconds: float = 0.0
    clean_exit: bool = False

    def to_context(
        self,
        *,
        machine: Mapping[str, Path] | None = None,
        image: Path | None = None,
        policy: LegTimeoutPolicy,
    ) -> dict[str, object]:
        evidence: dict[str, object] = {}
        boot = self.boot
        if boot is not None:
            evidence["returncode"] = boot.get("returncode")
            evidence["serial_log"] = boot.get("serial_log")
            evidence["qemu_log"] = boot.get("qemu_log")
            evidence["serial_bytes"] = boot.get("serial_bytes")
            evidence["serial_growth_bytes"] = boot.get("serial_growth_bytes")
            evidence["image_sha256_pre"] = boot.get("image_sha256_pre")
            evidence["image_sha256_post"] = boot.get("image_sha256_post")
        if self.pre is not None:
            evidence["on_image_pre"] = dict(self.pre)
        if self.post is not None:
            evidence["on_image_post"] = dict(self.post)
        if machine is not None or image is not None:
            evidence["disk_snapshot"] = snapshot_device_collect_state(
                image=image, machine=machine,
            )
            if image is not None and "image_sha256_pre" not in evidence:
                snap = evidence["disk_snapshot"]
                assert isinstance(snap, dict)
                evidence["image_sha256_post"] = snap.get("image_sha256")
        growth = boot.get("serial_growth_bytes", 0) if boot else 0
        sha_changed = bool(
            boot and boot.get("image_sha256_post") is not None
            and boot.get("image_sha256_post") != boot.get("image_sha256_pre")
        )
        evidence["timeout"] = policy.classify(
            serial_growth_bytes=int(growth) if isinstance(growth, int) else 0,
            image_sha_changed=sha_changed,
            elapsed_seconds=float(self.elapsed_seconds),
            clean_exit=self.clean_exit,
        )
        return evidence


def require_collect_precondition(
    value: object | None, *, message: str
) -> object:
    """Return ``value`` or raise the frozen-predicate RED for collection.

    Later collect legs must RED under their own frozen predicate when
    an earlier leg's in-memory product is absent — never with a bare
    ``assert``/``IndexError``. Raises :class:`LifecycleHarnessError`
    (observed RED, collected) with the caller's frozen-predicate
    wording.
    """
    if value is None or value is False:
        raise LifecycleHarnessError(message)
    return value


def assert_collect_destructive_bounds(
    output_dir: Path, image: Path | None = None
) -> None:
    """Abort-class destructive-bound guard for collect mode.

    Raises :class:`CollectAbortError` (abort, fail closed — never
    collected) when the disposable output root is not absolute or the
    disposable image escapes it. Called in the collect setup path and
    before the post-run loop binding; teardown/loop-detach failures
    raise the same abort class via the ``*_checked`` helpers.
    """
    out = Path(output_dir)
    if not out.is_absolute():
        raise CollectAbortError(
            "destructive-bound-violation: collect output_dir is not "
            f"absolute ({out}); aborting fail closed"
        )
    if image is not None:
        candidate = Path(image)
        if not candidate.is_absolute():
            raise CollectAbortError(
                "destructive-bound-violation: collect image path is not "
                f"absolute ({candidate}); aborting fail closed"
            )
        try:
            resolved_out = out.resolve()
            resolved_image = candidate.resolve()
        except Exception:
            resolved_out = out
            resolved_image = candidate
        if resolved_image != resolved_out and resolved_out not in resolved_image.parents:
            raise CollectAbortError(
                "destructive-bound-violation: collect image escapes the "
                f"disposable output dir ({resolved_image} outside "
                f"{resolved_out}); aborting fail closed"
            )


# ---------------------------------------------------------------------------
# Source-scope 8-step lifecycle (production seams, sparse block seam only)
# ---------------------------------------------------------------------------


@dataclass
class LifecycleHarness:
    """Executable 8-step lifecycle over one disposable machine."""

    config: LifecycleConfig
    seams_factory: Callable[[Path, bytes], ImageIntegrationSeams] | None = None

    def __post_init__(self) -> None:
        self.config.validate()

    @property
    def machine_root(self) -> Path:
        return Path(self.config.output_dir) / "machine"

    @property
    def report_path(self) -> Path:
        return Path(self.config.output_dir) / "greia-lifecycle-report.json"

    def run_source_scope(self) -> dict[str, object]:
        """Execute all 8 transitions through the production seams.

        Successful-update legs traverse the shipped
        ``build_live_update_service`` constructor with explicit
        image-integration seams; boot legs traverse the real launcher
        acceptance seam; the broken-candidate leg traverses the real
        recovery trigger; every transition is observed from guest/disk
        state and the ``ok`` flag derives from those assertions.
        """
        from greia_platform.boot_transaction import (
            BootTransactionJournal,
            BootTransactionState,
            mark_candidate_unhealthy,
        )
        from greia_platform.grub_ab import GrubEnvBackend
        from greia_platform.privileged_channel import PeerCredential
        from greia_platform.system_updates import (
            SystemUpdateInbox,
            build_persistent_state_contract_bytes,
            read_accepted_sequence,
        )
        from greia_platform.update_privileged import (
            UpdatePrivilegedEndpoint,
            build_request,
            read_response,
        )

        out = Path(self.config.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        machine = fresh_machine_state(self.machine_root)
        contract_bytes = build_persistent_state_contract_bytes()
        factory = self.seams_factory or ImageIntegrationSeams
        seams = factory(self.machine_root / "integration", contract_bytes)
        private_key, _ = mint_signing_keys(self.machine_root, machine["keys"])

        lineage = {
            ("greia-0.21.0", 21): build_test_release(
                self.machine_root, name="r21", release_id="greia-0.21.0",
                sequence=21, private_key=private_key,
            ),
            ("greia-0.21.1", 22): build_test_release(
                self.machine_root, name="r22broken", release_id="greia-0.21.1",
                sequence=22, private_key=private_key,
            ),
            ("greia-0.22.0", 23): build_test_release(
                self.machine_root, name="r23", release_id="greia-0.22.0",
                sequence=23, private_key=private_key,
            ),
        }
        _ = lineage
        steps: list[dict[str, object]] = []
        shipped_legs_used: list[str] = []
        launcher_legs_used: list[str] = []

        def _observe(step: str) -> dict[str, object]:
            backend = GrubEnvBackend.attach(machine["boot_control"]).inspect()
            try:
                journal = BootTransactionJournal.load(
                    machine["state"] / "system-updates" / "journal"
                )
                journal_state: object = journal.state.value
                candidate: object = journal.candidate_slot
            except Exception:
                journal_state = None
                candidate = None
            record = _load_record(machine["layout"])
            try:
                accepted_seq: object = read_accepted_sequence(machine["state"])
            except Exception:
                accepted_seq = None
            persist_marker = sha256_file(machine["persist"] / "profile.json")
            return {
                "step": step,
                "default_slot": backend.default_slot,
                "one_shot_slot": backend.one_shot_slot,
                "last_booted_slot": backend.last_booted_slot,
                "journal_state": journal_state,
                "journal_candidate": candidate,
                "accepted_slot": record.accepted_slot,
                "accepted_release": record.accepted_release_id,
                "accepted_sequence": accepted_seq,
                "persist_marker": persist_marker,
            }

        # Step 1: fresh install A (production-composed install proof).
        composition = prove_install_composition(
            out / "install-proof",
            layout_record_path=machine["layout"],
            password_hash=_PASSWORD_HASH,
        )
        from .devproof import record_leg_sample as _record_leg_sample

        leg_samples: list[dict[str, object]] = []
        steps.append({**_observe("fresh-install-A"),
                       "install_composition_mode": composition["install_mode"]})
        leg_samples.append(dict(_record_leg_sample("fresh-install-A")))

        # Step 2: boot A accepted (launcher acceptance, plain boot no-op).
        launcher_a = self._launcher_boot(
            machine, booted_slot="A", release_id="greia-0.20.0", sequence=20,
        )
        launcher_legs_used.append("boot-A-accepted")
        obs = _observe("boot-A-accepted")
        if launcher_a["seam_calls"] != ["interactive_ready"]:
            raise LifecycleContractError("launcher seam was not called exactly once")
        steps.append({**obs, "launcher": launcher_a})

        # Step 3: stage B one-shot through the shipped constructor, entered
        # through the shipped socket endpoint with a kernel-attested peer.
        authority = shipped_update_authority(
            state_dir=machine["state"],
            trusted_key_dir=machine["keys"],
            layout_record_path=machine["layout"],
            boot_backend=GrubEnvBackend.attach(machine["boot_control"]),
            seams=seams,
        )
        shipped_legs_used.append("stage-B-one-shot")
        endpoint = UpdatePrivilegedEndpoint(authority)  # type: ignore[arg-type]
        peer = PeerCredential(uid=0)

        def _op(name: str) -> dict[str, object]:
            raw = endpoint.handle_request(
                build_request(name), peer=peer, boot_state="update_ready"
            )
            _txid, op_name, payload = read_response(raw)
            if op_name == "ERROR":
                raise LifecycleContractError(
                    f"shipped endpoint refused {name}: {payload}"
                )
            return dict(payload)

        received = self.machine_root / "releases" / "r21" / "r21.greiaupdate"
        SystemUpdateInbox(machine["state"]).receive(received)
        verified = authority.verify_current_candidate()
        if not verified.present:
            raise LifecycleContractError("staged candidate did not verify")
        status = _op("STATUS")
        if not status.get("candidate", {}).get("present", False):
            raise LifecycleContractError("shipped STATUS shows no candidate")
        staged = _op("STAGE_CURRENT_CANDIDATE")
        if staged.get("status") != "STAGED":
            raise LifecycleContractError("shipped stage leg did not report STAGED")
        detail = staged.get("detail", {})
        if not isinstance(detail, dict) or detail.get("candidate_slot") != "B":
            raise LifecycleContractError("shipped stage did not target system-b")
        if "store:system-b" not in seams.contacts or "store:system-a" in seams.contacts:
            raise LifecycleContractError("shipped stage touched the wrong slot")
        obs = _observe("stage-B-one-shot")
        if obs["default_slot"] != "A":
            raise LifecycleContractError("default moved before health commit")
        steps.append({**obs, "shipped_stage": staged})
        leg_samples.append(dict(_record_leg_sample("stage-B-one-shot")))

        # Step 4: arm one-shot, reboot (observed B), launcher acceptance, commit.
        armed = _op("ARM_CURRENT_CANDIDATE")
        if armed.get("status") != "ARMED":
            raise LifecycleContractError("shipped arm leg did not report ARMED")
        backend = GrubEnvBackend.attach(machine["boot_control"])
        backend.reconcile("B")
        obs_mid = _observe("boot-B-commit-armed")
        if obs_mid["default_slot"] != "A" or obs_mid["last_booted_slot"] != "B":
            raise LifecycleContractError("one-shot state wrong before commit")
        shipped_legs_used.append("boot-B-commit")
        launcher_b = self._launcher_boot(
            machine, booted_slot="B", release_id="greia-0.21.0", sequence=21,
            filesystem_files=seams.files,
        )
        launcher_legs_used.append("boot-B-commit")
        if launcher_b["accepted_slot"] != "B":
            raise LifecycleContractError("launcher leg did not accept B")
        obs = _observe("boot-B-commit")
        if obs["default_slot"] != "B" or obs["accepted_slot"] != "B":
            raise LifecycleContractError("persistent default/accepted record not on B")
        if obs["accepted_sequence"] != 21:
            raise LifecycleContractError("accepted sequence did not advance to 21")
        steps.append({**obs, "launcher": launcher_b})
        leg_samples.append(dict(_record_leg_sample("boot-B-commit")))

        # Step 5: stage deliberately broken candidate (validly signed).
        # The accepted slot is B now, so the inactive target is system-a.
        broken_bundle = self.machine_root / "releases" / "r22broken" / "r22broken.greiaupdate"
        SystemUpdateInbox(machine["state"]).receive(broken_bundle)
        authority.verify_current_candidate()
        staged_broken = _op("STAGE_CURRENT_CANDIDATE")
        if staged_broken.get("status") != "STAGED":
            raise LifecycleContractError("broken candidate did not stage")
        broken_detail = staged_broken.get("detail", {})
        if not isinstance(broken_detail, dict) or broken_detail.get("candidate_slot") != "A":
            raise LifecycleContractError("broken candidate did not target system-a")
        armed_broken = _op("ARM_CURRENT_CANDIDATE")
        if armed_broken.get("status") != "ARMED":
            raise LifecycleContractError("broken candidate did not arm")
        steps.append({**_observe("stage-broken-candidate"),
                       "shipped_stage": staged_broken})

        # Step 6: boot broken candidate -> no health confirm, recovery trigger.
        # Firmware boots the candidate A (controlled post-boot failure: the
        # candidate runs but health never confirms); the deadline trigger
        # marks it FAILED while the persistent default stays on B.
        backend = GrubEnvBackend.attach(machine["boot_control"])
        backend.reconcile("A")
        journal_dir = machine["state"] / "system-updates" / "journal"
        from greia_platform.boot_transaction import BootTransactionCoordinator

        coordinator = BootTransactionCoordinator.resume(
            journal_dir=journal_dir,
            backend=GrubEnvBackend.attach(machine["boot_control"]),
            candidate_artifacts=_artifact_set("A", "greia-0.21.1", 22),
            accepted_artifacts=_artifact_set("B", "greia-0.21.0", 21),
        )
        observed_booted, _decision = coordinator.observe_boot()
        if observed_booted != "A":
            raise LifecycleContractError("broken candidate boot was not observed on A")
        decision = mark_candidate_unhealthy(
            coordinator,
            recovery_class="health-service-failure",
            detail="t6-lifecycle controlled post-boot failure",
        )
        journal_after = BootTransactionJournal.load(journal_dir)
        if journal_after.state is not BootTransactionState.FAILED:
            raise LifecycleContractError("broken candidate was not marked FAILED")
        if GrubEnvBackend.attach(machine["boot_control"]).inspect().default_slot != "B":
            raise LifecycleContractError("recovery trigger mutated the default")
        steps.append({**_observe("boot-broken-candidate"),
                       "recovery_decision": decision.note})

        # Step 7: recovery boot of B (candidate failed, PERSIST valid).
        # The launcher seam must NOT accept: the machine runs the accepted
        # slot with a terminal FAILED journal, so acceptance is a bounded
        # no-op and reconcile stays owned by the privileged service.
        launcher_r = self._launcher_boot(
            machine, booted_slot="B", release_id="greia-0.21.0", sequence=21,
            expect_no_acceptance=True,
        )
        launcher_legs_used.append("recovery-boot-B")
        obs = _observe("recovery-boot-B")
        if obs["default_slot"] != "B":
            raise LifecycleContractError("recovery boot did not return to default B")
        if obs["persist_marker"] != steps[1]["persist_marker"]:
            raise LifecycleContractError("PERSIST marker did not survive recovery")
        steps.append({**obs, "launcher": launcher_r})

        # Step 8: B-to-A reverse update (slot role and release identity independent).
        reverse_bundle = self.machine_root / "releases" / "r23" / "r23.greiaupdate"
        SystemUpdateInbox(machine["state"]).receive(reverse_bundle)
        authority.verify_current_candidate()
        staged_rev = _op("STAGE_CURRENT_CANDIDATE")
        if staged_rev.get("status") != "STAGED":
            raise LifecycleContractError("reverse update did not stage")
        if "store:system-a" not in seams.contacts:
            raise LifecycleContractError("reverse update did not target system-a")
        rearmed = _op("ARM_CURRENT_CANDIDATE")
        if rearmed.get("status") != "ARMED":
            raise LifecycleContractError("reverse update did not arm")
        GrubEnvBackend.attach(machine["boot_control"]).reconcile("A")
        shipped_legs_used.append("reverse-update-B-to-A")
        launcher_rev = self._launcher_boot(
            machine, booted_slot="A", release_id="greia-0.22.0", sequence=23,
            filesystem_files=seams.files,
        )
        launcher_legs_used.append("reverse-update-B-to-A")
        if launcher_rev["accepted_slot"] != "A":
            raise LifecycleContractError("reverse update did not accept A")
        obs = _observe("reverse-update-B-to-A")
        if obs["default_slot"] != "A" or obs["accepted_sequence"] != 23:
            raise LifecycleContractError("reverse update did not land on A/23")
        steps.append({**obs, "launcher": launcher_rev})
        leg_samples.append(dict(_record_leg_sample("reverse-update-B-to-A")))

        if [s["step"] for s in steps] != [
            "fresh-install-A", "boot-A-accepted", "stage-B-one-shot",
            "boot-B-commit", "stage-broken-candidate", "boot-broken-candidate",
            "recovery-boot-B", "reverse-update-B-to-A",
        ]:
            raise LifecycleContractError("lifecycle transitioned out of order")
        for leg in SHIPPED_UPDATE_LEGS:
            if leg not in shipped_legs_used:
                raise LifecycleContractError(f"shipped leg {leg} was bypassed")
        for leg in LAUNCHER_ACCEPTANCE_LEGS:
            if leg not in launcher_legs_used:
                raise LifecycleContractError(f"launcher leg {leg} was bypassed")

        # T7-DEVPROOF envelope (additive): D31 rollback, interruption
        # matrix, resource envelope, near-full preflight and cgroup gate
        # at source scope. Device-measured values stay deferred here;
        # the envelope raises fail-closed when its own contract is RED.
        from .devproof import run_envelope_source_scope

        devproof_envelope = run_envelope_source_scope(
            out / "devproof", leg_samples=leg_samples
        )
        report: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "classification": "SOURCE_SCOPE_T6_LIFECYCLE",
            "spec": lifecycle_spec(),
            "shipped_update_legs": list(shipped_legs_used),
            "launcher_acceptance_legs": list(launcher_legs_used),
            "steps": steps,
            "devproof_envelope": devproof_envelope,
            "device_scope": {
                "executed": False,
                "detail": "source scope: QEMU/loop execution deferred to a capable Linux host",
            },
            "limitations": [
                "live SeaBIOS boots on a QEMU-capable Linux host are deferred "
                "to a capable host; source scope folds declared boot outcomes "
                "through the real GrubEnvBackend + journal reconcile",
                "device-measured D31/interruption/resource/cgroup values are "
                "deferred to a capable host; source-scope envelope only",
                "does not prove Acer or physical-firmware behavior",
            ],
        }
        # The harness fails its own contract before publishing.
        assert_lifecycle_transitions(report)
        report_path = self.report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                               encoding="utf-8")
        return report

    def _launcher_boot(
        self, machine: Mapping[str, Path], *, booted_slot: str,
        release_id: str, sequence: int,
        filesystem_files: Mapping[str, bytes] | None = None,
        expect_accepted_slot: str | None = None,
        expect_no_acceptance: bool = False,
    ) -> dict[str, object]:
        """Fold one observed boot through journal + launcher acceptance.

        The declared ``booted_slot`` is folded through the real backend
        ``reconcile`` (source-scope reboot analogue; on device the outcome
        comes from the QEMU boot), then the real launcher seam runs with
        production identity files. Broken-candidate boots (machine still
        on the accepted slot) stay a bounded no-op with no acceptance.
        """
        import tempfile as _tempfile

        from greia_platform.grub_ab import GrubEnvBackend

        backend = GrubEnvBackend.attach(machine["boot_control"])
        backend.reconcile(booted_slot)
        partuuid = (
            f"{_MBR_SIGNATURE}-02" if booted_slot == "A" else f"{_MBR_SIGNATURE}-03"
        )
        with _tempfile.TemporaryDirectory(prefix="t6-launcher-") as directory:
            root = Path(directory)
            cmdline = root / "cmdline"
            cmdline.write_text(
                f"BOOT_IMAGE=/boot/vmlinuz root=PARTUUID={partuuid} ro quiet\n",
                encoding="utf-8",
            )
            layout_copy = root / "layout.json"
            layout_copy.write_bytes(Path(machine["layout"]).read_bytes())
            identity = root / "identity.json"
            if filesystem_files is not None and "etc/greia-os/release-identity.json" in filesystem_files:
                identity.write_bytes(filesystem_files["etc/greia-os/release-identity.json"])
            else:
                identity.write_bytes(
                    (json.dumps({
                        "boot_backend": BOOT_BACKEND_ID,
                        "layout_id": LAYOUT_ADAPTER_ID,
                        "release_id": release_id,
                        "release_sequence": sequence,
                        "role": f"system-{booted_slot.lower()}",
                        "slot": booted_slot,
                    }, sort_keys=True) + "\n").encode()
                )
            receipt = root / "receipt.json"
            if filesystem_files is not None and "etc/greia-os/finalization-receipt.json" in filesystem_files:
                receipt.write_bytes(filesystem_files["etc/greia-os/finalization-receipt.json"])
            else:
                receipt.write_bytes(
                    (json.dumps({
                        "release_id": release_id,
                        "release_sequence": sequence,
                        "slot": booted_slot,
                        "layout_id": LAYOUT_ADAPTER_ID,
                        "artifact_digests": {
                            "generic_kernel_sha256": "cd" * 32,
                            "host_initramfs_sha256": "ef" * 32,
                        },
                    }, sort_keys=True) + "\n").encode()
                )
            # Credentials vault: the launcher seam needs CREDENTIALS_DIRECTORY
            # to resolve a vault; an absent vault is the plain-boot no-op.
            credentials = root / "credentials"
            accepted = run_launcher_acceptance(
                update_state_dir=machine["state"],
                boot_control_dir=machine["boot_control"],
                layout_record_path=machine["layout"],
                cmdline_path=cmdline,
                identity_path=identity,
                receipt_path=receipt,
            )
            _ = credentials
            if expect_no_acceptance and accepted["accepted_slot"] is not None:
                raise LifecycleContractError(
                    "recovery boot must not accept: machine runs the accepted "
                    "slot with a terminal journal"
                )
            if expect_accepted_slot is not None and accepted["accepted_slot"] != expect_accepted_slot:
                raise LifecycleContractError(
                    f"launcher leg accepted {accepted['accepted_slot']!r}, "
                    f"expected {expect_accepted_slot!r}"
                )
            return accepted

    # -- device execution (capable Linux host only) ----------------------

    def _mount_partition1(
        self, device: Path, mountpoint: Path, *, read_only: bool
    ) -> None:
        part = Path(str(device) + "p1")
        runners = [
            (["partprobe", str(device)], "partprobe failed"),
            (["udevadm", "settle"], "udevadm settle failed"),
        ]
        for argv, message in runners:
            completed = run_device_host_tool(argv, capture_output=True, timeout=60)
            if completed.returncode != 0:
                raise LifecycleHarnessError(message + f" for {device}")
        time.sleep(0.5)
        mountpoint.mkdir(parents=True, exist_ok=True)
        argv = ["mount", "-t", "ext4"]
        if read_only:
            argv.extend(["-o", "ro"])
        argv.extend([str(part), str(mountpoint)])
        mounted = run_device_host_tool(argv, capture_output=True, timeout=60)
        if mounted.returncode != 0:
            raise LifecycleHarnessError(f"partition-1 mount failed for {device}")

    def _unmount(self, mountpoint: Path) -> None:
        run_device_host_tool(
            ["umount", str(mountpoint)], capture_output=True, timeout=60
        )

    def _read_on_image_grubenv(self, image: Path) -> dict[str, object]:
        """Read the on-image grubenv via the frozen production seam.

        Loop-attaches the image, mounts partition 1 read-only, and
        inspects through ``GrubEnvBackend.attach(mountpoint).inspect()`` —
        the exact T7-ATTEST §2 seam. Teardown (unmount/detach) runs in
        finally; any mount/loop failure is fail-closed RED.
        """
        from greia_platform.grub_ab import GrubEnvBackend

        device = self._loop_attach(Path(image))
        mountpoint = Path(self.config.output_dir) / "observe-mnt"
        try:
            self._mount_partition1(device, mountpoint, read_only=True)
            try:
                state = GrubEnvBackend.attach(mountpoint).inspect()
            finally:
                self._unmount(mountpoint)
        finally:
            self._loop_detach(device)
        return {
            "default_slot": state.default_slot,
            "one_shot_slot": state.one_shot_slot,
            "last_booted_slot": state.last_booted_slot,
            "seam": "GrubEnvBackend.attach(mountpoint).inspect()",
        }

    def _sync_boot_state_to_image(
        self, image: Path, boot_control_dir: Path
    ) -> None:
        """Push the staged/armed host grubenv onto image partition 1.

        Stage/arm legs run through the shipped endpoint against the host
        staging backend; the guest can only consume what is on the image,
        so the armed block is copied onto partition 1 (read-write mount)
        before the leg's real boot. Safe teardown in finally; fail-closed.
        """
        from greia_platform.grub_ab import GRUBENV_FILE_NAME

        device = self._loop_attach(Path(image))
        mountpoint = Path(self.config.output_dir) / "sync-mnt"
        try:
            self._mount_partition1(device, mountpoint, read_only=False)
            try:
                shutil.copy2(
                    Path(boot_control_dir) / GRUBENV_FILE_NAME,
                    mountpoint / GRUBENV_FILE_NAME,
                )
                subprocess.run(["sync"], capture_output=True, timeout=60)
            finally:
                self._unmount(mountpoint)
        finally:
            self._loop_detach(device)

    def _stamp_and_gate_on_image(
        self, image: Path, *, observed: str, expected: str
    ) -> dict[str, object]:
        """Stamp the derived observation, then run the uniform gate.

        The ``observed`` slot was derived solely from on-image pre/post
        consumption evidence (:func:`decide_device_boot_observation`); it
        is folded through the production ``reconcile`` on the real
        on-image bytes, and only then does ``read_attestation_signal``
        evaluate the frozen consumption predicate
        (``next_entry`` absent AND ``last_booted == expected``) through
        the post-boot loop remount/read path. Returns the signal.
        """
        from greia_platform.grub_ab import GrubEnvBackend

        from .payload import read_attestation_signal

        device = self._loop_attach(Path(image))
        mountpoint = Path(self.config.output_dir) / "stamp-mnt"
        try:
            self._mount_partition1(device, mountpoint, read_only=False)
            try:
                GrubEnvBackend.attach(mountpoint).reconcile(observed)
                signal = read_attestation_signal(
                    mountpoint, expected_booted_slot=expected
                )
                return dict(signal)
            finally:
                self._unmount(mountpoint)
        finally:
            self._loop_detach(device)

    def _boot_image_once(self, image: Path, *, leg: str) -> dict[str, object]:
        """Boot the disposable image once under real SeaBIOS firmware.

        Returns the per-leg boot evidence (argv, logs, pre/post image
        SHA, serial progress). The progress-aware bounded wait
        (:func:`bootchain.wait_for_clean_exit`) replaces the bare
        blocking wait: serial-byte growth and image SHA delta count as
        progress evidence with the leg timeout as the hard ceiling, and
        the clean-exit gate (:func:`check_boot_exit`) still runs before
        any observation — timeout, silence, stall, or nonzero status is
        RED, never a claimed boot. Guest disk writes persist (no snapshot
        flag) so grubenv effects are observable after the boot exits.
        """
        from .bootchain import BootchainError, wait_for_clean_exit

        argv, serial_log, host_log = device_qemu_argv(
            Path(image),
            output_dir=Path(self.config.output_dir),
            leg=leg,
            memory_mib=self.config.memory_mib,
            cpus=self.config.cpus,
            seabios_path=self.config.seabios_path,
        )
        # Privileged launch: resolve the QEMU binary sbin/PATH-aware and
        # prefix sudo -n on non-root hosts under the owner-provisioned rule.
        # The executed argv (not just the logical one) is recorded below so
        # the artifact shows the real production launch. A missing binary
        # raises here fail-closed instead of Popen's FileNotFoundError.
        argv = device_tool_invocation(argv[0], *argv[1:])
        pre_sha = sha256_file(Path(image))
        with host_log.open("ab") as log:
            process = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                waited = wait_for_clean_exit(
                    process,
                    leg=leg,
                    qemu_log=host_log,
                    serial_log=serial_log,
                    image=Path(image),
                    image_sha_at_start=pre_sha,
                    timeout_seconds=float(self.config.timeout_seconds),
                )
            except BootchainError as exc:
                raise LifecycleHarnessError(str(exc)) from exc
        check_boot_exit(int(waited["returncode"]), leg=leg, qemu_log=host_log)
        post_sha = waited["image_sha256_post"]
        return {
            "leg": leg,
            "returncode": int(waited["returncode"]),
            "qemu_argv": list(argv),
            "serial_log": str(serial_log),
            "qemu_log": str(host_log),
            "image_sha256_pre": pre_sha,
            "image_sha256_post": (
                str(post_sha) if post_sha is not None else sha256_file(Path(image))
            ),
            "serial_bytes": int(waited["serial_bytes"]),
            "serial_growth_bytes": int(waited["serial_growth_bytes"]),
            "progress_observed": bool(waited["progress_observed"]),
        }

    def run_device(self) -> dict[str, object]:
        """Execute the true device lifecycle: 8 transitions, 5 real boots.

        Frozen T7-ATTEST definition verbatim: 3 non-boot transitions
        (``fresh-install-A``, ``stage-B-one-shot``,
        ``stage-broken-candidate``) carry no boot outcome; each of the 5
        boot-outcome legs performs exactly one real SeaBIOS boot of the
        T7-PAYLOAD image on a capable host, observed through the frozen
        attestation seam (grubenv-on-image with post-boot loop
        remount/read via ``GrubEnvBackend.attach(mountpoint).inspect()``).

        Preserved fixer-1 gates (verbatim) plus the GUEST-BOOT-CHAIN boot
        chain: fail-closed ``require_device_host`` strictness; the payload
        + sector-gap + boot-chain gate (``device_gate_for_image``: a
        payload-less/tampered/chain-less image REDs the real boot path
        before any QEMU boot); the clean-exit gate per boot (unclean QEMU
        exit is RED); the progress-aware bounded wait (serial-byte growth
        and image SHA delta count as progress with the leg timeout as the
        hard ceiling; silence and progress-then-stall are RED); per-leg
        disk-file proof with the image SHA bound after the payload embed
        (pre/post SHA per boot leg); the post-run loop/cross-check binding
        (executed-and-green enforced on a capable host); honest
        device/source classification (``DEVICE_T7_DEVRUN3`` only when the
        device path executed).

        Observation discipline: only the on-image observation feeds the
        ``reconcile``/journal/launcher folds — the observed slot is
        derived from on-image pre/post consumption evidence
        (:func:`decide_device_boot_observation`), stamped through the
        production ``reconcile`` on the real on-image bytes, gated by
        ``read_attestation_signal`` through the post-boot loop
        remount/read path, and only then folded into the host backend,
        the journal coordinator and the launcher ``INTERACTIVE_READY``
        seam (which traverses with the guest-observed boot identity).
        Stage/arm legs run exclusively through the shipped
        ``build_live_update_service`` constructor path with the
        production boot attach; the persistent default is held until the
        health commit.

        Fake boundary: block-driver seam only (sparse ``LoopbackSlotFile``
        stores inside the shipped destination factories). No stubbed
        health, no stubbed launcher, no fabricated slot/journal/GRUB
        state, no ``simulate_reboot``. There is no ``on_boot`` hook: any
        stubbed-spawn run is source scope and explicitly non-proxying
        for the live predicate. Teardown/remount/reload semantics and
        fail-closed behavior hold throughout (loop/mount state torn down
        in finally).

        Source readiness: the GUEST-BOOT-CHAIN guest (MBR stub + stub
        core) emits COM1 progress and exits via guest reboot, so the
        clean-exit gate is satisfiable on a capable host; the stub never
        stamps ``last_booted`` (no guest agent), so armed-leg consumption
        stays RED until genuine GRUB (load_env/save_env) lands via the
        gated ``bootchain`` seam. Live green belongs to B3-DEVRUN-RERUN.
        """
        require_device_host()
        from greia_platform.boot_transaction import (
            BootTransactionCoordinator,
            BootTransactionJournal,
            BootTransactionState,
            mark_candidate_unhealthy,
        )
        from greia_platform.grub_ab import GrubEnvBackend
        from greia_platform.privileged_channel import PeerCredential
        from greia_platform.system_updates import (
            SystemUpdateInbox,
            build_persistent_state_contract_bytes,
            read_accepted_sequence,
        )
        from greia_platform.update_privileged import (
            UpdatePrivilegedEndpoint,
            build_request,
            read_response,
        )

        from .payload import install_payload_to_device

        out = Path(self.config.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        manifest = assemble_disposable_image(out)
        image = Path(manifest["image"])
        # Clean-exit gate path: payload-less/tampered images RED here.
        gate = device_gate_for_image(image)
        # Device payload install: formats partition 1 and copies the
        # staged grub.cfg + grubenv onto the boot-control filesystem.
        install_proof = install_payload_to_device(image, out / "guest-payload")
        # The descriptor must name exactly the installed bytes.
        bind_gate_to_install(gate, install_proof)

        machine = fresh_machine_state(self.machine_root)
        contract_bytes = build_persistent_state_contract_bytes()
        factory = self.seams_factory or ImageIntegrationSeams
        seams = factory(self.machine_root / "integration", contract_bytes)
        private_key, _ = mint_signing_keys(self.machine_root, machine["keys"])
        for name, release_id, sequence in (
            ("r21", "greia-0.21.0", 21),
            ("r22broken", "greia-0.21.1", 22),
            ("r23", "greia-0.22.0", 23),
        ):
            build_test_release(
                self.machine_root, name=name, release_id=release_id,
                sequence=sequence, private_key=private_key,
            )
        steps: list[dict[str, object]] = []
        shipped_legs_used: list[str] = []
        launcher_legs_used: list[str] = []
        boot_legs: list[dict[str, object]] = []

        def _observe(step: str) -> dict[str, object]:
            backend = GrubEnvBackend.attach(machine["boot_control"]).inspect()
            try:
                journal = BootTransactionJournal.load(
                    machine["state"] / "system-updates" / "journal"
                )
                journal_state: object = journal.state.value
                candidate: object = journal.candidate_slot
            except Exception:
                journal_state = None
                candidate = None
            record = _load_record(machine["layout"])
            try:
                accepted_seq: object = read_accepted_sequence(machine["state"])
            except Exception:
                accepted_seq = None
            return {
                "step": step,
                "default_slot": backend.default_slot,
                "one_shot_slot": backend.one_shot_slot,
                "last_booted_slot": backend.last_booted_slot,
                "journal_state": journal_state,
                "journal_candidate": candidate,
                "accepted_slot": record.accepted_slot,
                "accepted_release": record.accepted_release_id,
                "accepted_sequence": accepted_seq,
                "persist_marker": sha256_file(machine["persist"] / "profile.json"),
                "image_sha256": sha256_file(image),
            }

        def _device_boot_leg(leg: str) -> dict[str, object]:
            """One real SeaBIOS boot with on-image observation and folds."""
            expected = BOOT_OUTCOME_EXPECTED_SLOT[leg]
            pre = self._read_on_image_grubenv(image)
            boot = self._boot_image_once(image, leg=leg)
            post = self._read_on_image_grubenv(image)
            # The observed slot derives solely from on-image bytes.
            observed = decide_device_boot_observation(leg=leg, pre=pre, post=post)
            if observed != expected:
                raise LifecycleHarnessError(
                    f"device boot leg {leg} observed {observed!r}, "
                    f"expected {expected!r}"
                )
            signal = self._stamp_and_gate_on_image(
                image, observed=observed, expected=expected
            )
            # Host staging backend tracks device truth (never leads it).
            GrubEnvBackend.attach(machine["boot_control"]).reconcile(observed)
            evidence = {
                **boot,
                "expected_slot": expected,
                "observed_slot": observed,
                "on_image_pre": pre,
                "on_image_post": post,
                "attestation_signal": signal,
            }
            boot_legs.append(evidence)
            return evidence

        # Step 1: fresh install A (production-composed install proof).
        composition = prove_install_composition(
            out / "install-proof",
            layout_record_path=machine["layout"],
            password_hash=_PASSWORD_HASH,
        )
        from .devproof import record_leg_sample as _record_leg_sample

        leg_samples: list[dict[str, object]] = []
        steps.append({**_observe("fresh-install-A"),
                       "install_composition_mode": composition["install_mode"]})
        leg_samples.append(dict(_record_leg_sample("fresh-install-A", surface="DEVICE")))

        # Step 2: boot A accepted — plain default boot, launcher accepts.
        boot_a = _device_boot_leg("boot-A-accepted")
        launcher_a = self._launcher_boot(
            machine, booted_slot=str(boot_a["observed_slot"]),
            release_id="greia-0.20.0", sequence=20,
        )
        launcher_legs_used.append("boot-A-accepted")
        obs = _observe("boot-A-accepted")
        if launcher_a["seam_calls"] != ["interactive_ready"]:
            raise LifecycleContractError("launcher seam was not called exactly once")
        steps.append({**obs, "launcher": launcher_a,
                       "device_boot": boot_a["image_sha256_post"]})

        # Steps 3-4: stage + arm B through the shipped endpoint, push the
        # armed block to the image, boot B, launcher accepts, commit.
        authority = shipped_update_authority(
            state_dir=machine["state"],
            trusted_key_dir=machine["keys"],
            layout_record_path=machine["layout"],
            boot_backend=GrubEnvBackend.attach(machine["boot_control"]),
            seams=seams,
        )
        shipped_legs_used.append("stage-B-one-shot")
        endpoint = UpdatePrivilegedEndpoint(authority)  # type: ignore[arg-type]
        peer = PeerCredential(uid=0)

        def _op(name: str) -> dict[str, object]:
            raw = endpoint.handle_request(
                build_request(name), peer=peer, boot_state="update_ready"
            )
            _txid, op_name, payload = read_response(raw)
            if op_name == "ERROR":
                raise LifecycleContractError(
                    f"shipped endpoint refused {name}: {payload}"
                )
            return dict(payload)

        received = self.machine_root / "releases" / "r21" / "r21.greiaupdate"
        SystemUpdateInbox(machine["state"]).receive(received)
        verified = authority.verify_current_candidate()
        if not verified.present:
            raise LifecycleContractError("staged candidate did not verify")
        staged = _op("STAGE_CURRENT_CANDIDATE")
        if staged.get("status") != "STAGED":
            raise LifecycleContractError("shipped stage leg did not report STAGED")
        detail = staged.get("detail", {})
        if not isinstance(detail, dict) or detail.get("candidate_slot") != "B":
            raise LifecycleContractError("shipped stage did not target system-b")
        if "store:system-b" not in seams.contacts or "store:system-a" in seams.contacts:
            raise LifecycleContractError("shipped stage touched the wrong slot")
        obs = _observe("stage-B-one-shot")
        if obs["default_slot"] != "A":
            raise LifecycleContractError("default moved before health commit")
        steps.append({**obs, "shipped_stage": staged})
        leg_samples.append(dict(_record_leg_sample("stage-B-one-shot", surface="DEVICE")))

        armed = _op("ARM_CURRENT_CANDIDATE")
        if armed.get("status") != "ARMED":
            raise LifecycleContractError("shipped arm leg did not report ARMED")
        self._sync_boot_state_to_image(image, machine["boot_control"])
        shipped_legs_used.append("boot-B-commit")
        boot_b = _device_boot_leg("boot-B-commit")
        launcher_b = self._launcher_boot(
            machine, booted_slot=str(boot_b["observed_slot"]),
            release_id="greia-0.21.0", sequence=21,
            filesystem_files=seams.files,
        )
        launcher_legs_used.append("boot-B-commit")
        if launcher_b["accepted_slot"] != "B":
            raise LifecycleContractError("launcher leg did not accept B")
        obs = _observe("boot-B-commit")
        if obs["default_slot"] != "B" or obs["accepted_slot"] != "B":
            raise LifecycleContractError("persistent default/accepted record not on B")
        if obs["accepted_sequence"] != 21:
            raise LifecycleContractError("accepted sequence did not advance to 21")
        steps.append({**obs, "launcher": launcher_b,
                       "device_boot": boot_b["image_sha256_post"]})
        leg_samples.append(dict(_record_leg_sample("boot-B-commit", surface="DEVICE")))

        # Step 5: stage + arm the deliberately broken candidate (system-a).
        broken_bundle = self.machine_root / "releases" / "r22broken" / "r22broken.greiaupdate"
        SystemUpdateInbox(machine["state"]).receive(broken_bundle)
        authority.verify_current_candidate()
        staged_broken = _op("STAGE_CURRENT_CANDIDATE")
        if staged_broken.get("status") != "STAGED":
            raise LifecycleContractError("broken candidate did not stage")
        broken_detail = staged_broken.get("detail", {})
        if not isinstance(broken_detail, dict) or broken_detail.get("candidate_slot") != "A":
            raise LifecycleContractError("broken candidate did not target system-a")
        armed_broken = _op("ARM_CURRENT_CANDIDATE")
        if armed_broken.get("status") != "ARMED":
            raise LifecycleContractError("broken candidate did not arm")
        steps.append({**_observe("stage-broken-candidate"),
                       "shipped_stage": staged_broken})

        # Step 6: boot broken candidate -> observed on A via the image,
        # health never confirms, recovery trigger marks FAILED, default B.
        self._sync_boot_state_to_image(image, machine["boot_control"])
        boot_broken = _device_boot_leg("boot-broken-candidate")
        journal_dir = machine["state"] / "system-updates" / "journal"
        coordinator = BootTransactionCoordinator.resume(
            journal_dir=journal_dir,
            backend=GrubEnvBackend.attach(machine["boot_control"]),
            candidate_artifacts=_artifact_set("A", "greia-0.21.1", 22),
            accepted_artifacts=_artifact_set("B", "greia-0.21.0", 21),
        )
        observed_booted, _decision = coordinator.observe_boot()
        if observed_booted != str(boot_broken["observed_slot"]):
            raise LifecycleContractError(
                "journal fold did not follow the on-image observation"
            )
        decision = mark_candidate_unhealthy(
            coordinator,
            recovery_class="health-service-failure",
            detail="t7-devrun3 controlled post-boot failure",
        )
        journal_after = BootTransactionJournal.load(journal_dir)
        if journal_after.state is not BootTransactionState.FAILED:
            raise LifecycleContractError("broken candidate was not marked FAILED")
        if GrubEnvBackend.attach(machine["boot_control"]).inspect().default_slot != "B":
            raise LifecycleContractError("recovery trigger mutated the default")
        steps.append({**_observe("boot-broken-candidate"),
                       "recovery_decision": decision.note,
                       "device_boot": boot_broken["image_sha256_post"]})

        # Step 7: recovery boot of B (bounded launcher no-op, PERSIST kept).
        boot_rec = _device_boot_leg("recovery-boot-B")
        launcher_r = self._launcher_boot(
            machine, booted_slot=str(boot_rec["observed_slot"]),
            release_id="greia-0.21.0", sequence=21,
            expect_no_acceptance=True,
        )
        launcher_legs_used.append("recovery-boot-B")
        obs = _observe("recovery-boot-B")
        if obs["default_slot"] != "B":
            raise LifecycleContractError("recovery boot did not return to default B")
        if obs["persist_marker"] != steps[1]["persist_marker"]:
            raise LifecycleContractError("PERSIST marker did not survive recovery")
        steps.append({**obs, "launcher": launcher_r,
                       "device_boot": boot_rec["image_sha256_post"]})

        # Step 8: B-to-A reverse update through the shipped path + boot.
        reverse_bundle = self.machine_root / "releases" / "r23" / "r23.greiaupdate"
        SystemUpdateInbox(machine["state"]).receive(reverse_bundle)
        authority.verify_current_candidate()
        staged_rev = _op("STAGE_CURRENT_CANDIDATE")
        if staged_rev.get("status") != "STAGED":
            raise LifecycleContractError("reverse update did not stage")
        if "store:system-a" not in seams.contacts:
            raise LifecycleContractError("reverse update did not target system-a")
        rearmed = _op("ARM_CURRENT_CANDIDATE")
        if rearmed.get("status") != "ARMED":
            raise LifecycleContractError("reverse update did not arm")
        self._sync_boot_state_to_image(image, machine["boot_control"])
        shipped_legs_used.append("reverse-update-B-to-A")
        boot_rev = _device_boot_leg("reverse-update-B-to-A")
        launcher_rev = self._launcher_boot(
            machine, booted_slot=str(boot_rev["observed_slot"]),
            release_id="greia-0.22.0", sequence=23,
            filesystem_files=seams.files,
        )
        launcher_legs_used.append("reverse-update-B-to-A")
        if launcher_rev["accepted_slot"] != "A":
            raise LifecycleContractError("reverse update did not accept A")
        obs = _observe("reverse-update-B-to-A")
        if obs["default_slot"] != "A" or obs["accepted_sequence"] != 23:
            raise LifecycleContractError("reverse update did not land on A/23")
        steps.append({**obs, "launcher": launcher_rev,
                       "device_boot": boot_rev["image_sha256_post"]})
        leg_samples.append(dict(_record_leg_sample("reverse-update-B-to-A", surface="DEVICE")))

        if [s["step"] for s in steps] != list(LIFECYCLE_SEQUENCE):
            raise LifecycleContractError("lifecycle transitioned out of order")
        for leg in SHIPPED_UPDATE_LEGS:
            if leg not in shipped_legs_used:
                raise LifecycleContractError(f"shipped leg {leg} was bypassed")
        for leg in LAUNCHER_ACCEPTANCE_LEGS:
            if leg not in launcher_legs_used:
                raise LifecycleContractError(f"launcher leg {leg} was bypassed")

        # Post-run loop/cross-check binding (executed-and-green enforced).
        from greia_installer.layout import ProfileSizing, plan_for_profile

        sizing = ProfileSizing(
            layout_adapter_id=LAYOUT_ADAPTER_ID,
            slot_bytes=1073741824,
            persist_minimum_bytes=268435456,
            boot_backend=BOOT_BACKEND_ID,
        )
        plan = plan_for_profile(sizing, device_size_bytes=4 * 1024 * 1024 * 1024)
        device = self._loop_attach(image)
        try:
            loop_result = observe_loop_attached_device(
                device, plan=plan, record_path=machine["layout"],
            )
            cross = run_file_cross_check(
                image,
                expected_signature=str(loop_result["proven_signature"]),
            )
            if not cross["executed"] or not cross["green"]:
                raise LifecycleHarnessError(
                    "file cross-check must execute and pass on a capable host"
                )
        finally:
            self._loop_detach(device)

        # T7-DEVPROOF device envelope (additive): device-measured D31
        # rollback, interruption matrix, resource envelope, near-full
        # preflight and the 768 MiB cgroup gate. RED here fails the
        # device run closed; off a capable host the envelope was never
        # reached (require_device_host above already refused). The
        # envelope observes the real r21 bundle built through the
        # shipped path above, so bundle accounting is run-observed.
        from .devproof import run_envelope_device

        _devproof_bundle = (
            self.machine_root / "releases" / "r21" / "r21.greiaupdate"
        )
        devproof_device_envelope = run_envelope_device(
            out / "devproof-device",
            bundle_path=_devproof_bundle if _devproof_bundle.is_file() else None,
            leg_samples=leg_samples,
        )
        report: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "classification": "DEVICE_T7_DEVRUN3",
            "spec": lifecycle_spec(),
            "image_manifest": manifest,
            "device_gate": gate,
            "install_proof": install_proof,
            "shipped_update_legs": list(shipped_legs_used),
            "launcher_acceptance_legs": list(launcher_legs_used),
            "boot_outcome_legs": list(BOOT_OUTCOME_LEGS),
            "device_boots": boot_legs,
            "steps": steps,
            "devproof_envelope": devproof_device_envelope,
            "device_scope": {
                "executed": True,
                "loop_attach_green": True,
                "file_cross_check_executed": True,
                "file_cross_check_green": True,
                "devproof_device_measured": True,
                "image_sha256": sha256_file(image),
            },
            "limitations": [
                "device SeaBIOS boots executed on this host; minimal-image "
                "legs without guest userspace stop at the frozen "
                "consumption predicate and never claim launcher acceptance",
                "does not prove Acer or physical-firmware behavior",
            ],
        }
        assert_lifecycle_transitions(report)
        self.report_path.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        return report

    # -- fail-collect observation mode (DIAG-C1) -------------------------

    def _loop_detach_checked(self, device: Path) -> None:
        """Abort-class loop detach for collect mode.

        Unlike :meth:`_loop_detach` (best-effort, fail-fast path
        unchanged), a non-zero detach here raises
        :class:`CollectAbortError`: a device left attached is a
        teardown-safety violation and stops collection immediately,
        fail closed.
        """
        completed = run_device_host_tool(
            ["losetup", "--detach", str(device)],
            capture_output=True, timeout=60,
        )
        if completed.returncode != 0:
            raise CollectAbortError(
                "teardown-loop-detach-safety: loop detach failed for "
                f"{device} (rc={completed.returncode}); aborting fail closed"
            )

    def _unmount_checked(self, mountpoint: Path) -> None:
        """Abort-class unmount for collect mode (same boundary)."""
        completed = run_device_host_tool(
            ["umount", str(mountpoint)], capture_output=True, timeout=60
        )
        if completed.returncode != 0:
            raise CollectAbortError(
                "teardown-loop-detach-safety: unmount failed for "
                f"{mountpoint} (rc={completed.returncode}); aborting fail closed"
            )

    def _read_on_image_grubenv_strict(self, image: Path) -> dict[str, object]:
        """Collect-mode on-image grubenv read (checked teardown).

        Observation failures raise the fail-fast RED for collection;
        teardown failures raise :class:`CollectAbortError` and abort.
        Uses the frozen ``GrubEnvBackend.attach(mountpoint).inspect()``
        seam, identical to :meth:`_read_on_image_grubenv`.
        """
        from greia_platform.grub_ab import GrubEnvBackend

        device = self._loop_attach(Path(image))
        mountpoint = Path(self.config.output_dir) / "observe-mnt"
        try:
            self._mount_partition1(device, mountpoint, read_only=True)
            try:
                state = GrubEnvBackend.attach(mountpoint).inspect()
            finally:
                self._unmount_checked(mountpoint)
        finally:
            self._loop_detach_checked(device)
        return {
            "default_slot": state.default_slot,
            "one_shot_slot": state.one_shot_slot,
            "last_booted_slot": state.last_booted_slot,
            "seam": "GrubEnvBackend.attach(mountpoint).inspect()",
        }

    def _sync_boot_state_to_image_strict(
        self, image: Path, boot_control_dir: Path
    ) -> None:
        """Collect-mode armed-block sync (checked teardown)."""
        from greia_platform.grub_ab import GRUBENV_FILE_NAME

        device = self._loop_attach(Path(image))
        mountpoint = Path(self.config.output_dir) / "sync-mnt"
        try:
            self._mount_partition1(device, mountpoint, read_only=False)
            try:
                shutil.copy2(
                    Path(boot_control_dir) / GRUBENV_FILE_NAME,
                    mountpoint / GRUBENV_FILE_NAME,
                )
                subprocess.run(["sync"], capture_output=True, timeout=60)
            finally:
                self._unmount_checked(mountpoint)
        finally:
            self._loop_detach_checked(device)

    def _stamp_and_gate_on_image_strict(
        self, image: Path, *, observed: str, expected: str
    ) -> dict[str, object]:
        """Collect-mode stamp+gate (checked teardown).

        Folds the derived observation through the production
        ``reconcile`` on the real on-image bytes, then gates with
        ``read_attestation_signal`` through the post-boot loop
        remount/read path — identical predicates to
        :meth:`_stamp_and_gate_on_image`.
        """
        from greia_platform.grub_ab import GrubEnvBackend

        from .payload import read_attestation_signal

        device = self._loop_attach(Path(image))
        mountpoint = Path(self.config.output_dir) / "stamp-mnt"
        try:
            self._mount_partition1(device, mountpoint, read_only=False)
            try:
                GrubEnvBackend.attach(mountpoint).reconcile(observed)
                signal = read_attestation_signal(
                    mountpoint, expected_booted_slot=expected
                )
                return dict(signal)
            finally:
                self._unmount_checked(mountpoint)
        finally:
            self._loop_detach_checked(device)

    def run_device_collect(self) -> dict[str, object]:
        """Execute the device lifecycle in fail-collect observation mode.

        Same production path as :meth:`run_device` (same image
        assembly, device gate, shipped update path, real SeaBIOS boots,
        frozen attestation seam, launcher seam, post-run
        loop/cross-check binding, devproof device envelope), but each
        of the 8 lifecycle legs plus the post-run loop/cross-check
        binding and the devproof device envelope runs under per-leg
        capture in :data:`COLLECT_LEG_ORDER`:

        - an observed RED (``require_device_host``, device gate,
          clean-exit gate, consumption predicate, attestation binding,
          loop/cross-check, envelope) records the verbatim fail-fast
          error with full context and the run continues under
          ``COLLECT_CONTINUATION_RULES`` (each boot leg re-reads
          on-image state independently; a RED leg never blocks later
          legs; the loop/cross-check and envelope bindings are always
          attempted once setup yields an image; each boot-leg RED
          forwards its live pre/boot/post/elapsed evidence via
          :class:`BootLegCapture`);
        - an abort-class RED (teardown/loop-detach safety,
          destructive-bound violation via
          :func:`assert_collect_destructive_bounds` and the checked
          teardown helpers) records and re-raises
          immediately, fail closed (the no-image setup failure is the
          only fail-closed early return: without an image no boot or
          binding has anything to observe);
        - per-leg timeout/progress detail (serial-byte growth and image
          SHA delta as progress, leg timeout as the hard ceiling,
          silence and progress-then-stall RED with the timeout
          recorded) rides on the real
          ``bootchain.wait_for_clean_exit`` evidence inside
          :meth:`_boot_image_once`;
        - the frozen attestation seam is byte-identical in semantics:
          :func:`decide_device_boot_observation` predicates are called,
          never changed; only RED collection/reporting differs;
        - a diagnostics artifact
          (``greia-device-collect-diagnostics.json``) is emitted per
          run; the final verdict aggregates ALL reds and never converts
          a RED to green/yellow.

        Preregistered acceptance: predicates frozen before observation;
        collection widens OBSERVATION only.
        """
        from greia_platform.boot_transaction import (
            BootTransactionCoordinator,
            BootTransactionJournal,
            BootTransactionState,
            mark_candidate_unhealthy,
        )
        from greia_platform.grub_ab import GrubEnvBackend
        from greia_platform.privileged_channel import PeerCredential
        from greia_platform.system_updates import (
            SystemUpdateInbox,
            build_persistent_state_contract_bytes,
            read_accepted_sequence,
        )
        from greia_platform.update_privileged import (
            UpdatePrivilegedEndpoint,
            build_request,
            read_response,
        )

        from .payload import install_payload_to_device

        recorder = DeviceCollectRecorder()
        policy = LegTimeoutPolicy(timeout_seconds=float(self.config.timeout_seconds))
        out = Path(self.config.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        run_meta: dict[str, object] = {
            "timeout_policy": policy.describe(),
            "mode": "fail-collect",
        }

        def _context_for(
            *,
            boot: Mapping[str, object] | None = None,
            pre: Mapping[str, object] | None = None,
            post: Mapping[str, object] | None = None,
            machine: Mapping[str, Path] | None = None,
            image: Path | None = None,
            elapsed_seconds: float = 0.0,
            clean_exit: bool = False,
        ) -> dict[str, object]:
            # Single evidence shape owned by BootLegCapture; this
            # closure only adapts the non-boot call sites to it.
            cap = BootLegCapture(
                pre=dict(pre) if pre is not None else None,
                boot=dict(boot) if boot is not None else None,
                post=dict(post) if post is not None else None,
                elapsed_seconds=float(elapsed_seconds),
                clean_exit=clean_exit,
            )
            return cap.to_context(machine=machine, image=image, policy=policy)

        # Setup legs: host gate, image assembly, device gate, payload
        # install, gate binding. Each is its own collect unit; the
        # machine/seams below are created lazily so a RED setup leg
        # still lets later legs attempt and RED under their own frozen
        # predicates where preconditions are absent.
        holder: dict[str, object] = {}

        def _setup_host() -> object:
            require_device_host()
            return {"gate": "require_device_host", "green": True}

        recorder.run_leg(
            leg="collect-setup-host-gate", gate="require_device_host",
            frozen_predicate=COLLECT_FROZEN_PREDICATES["require_device_host"],
            run=_setup_host,
        )

        def _setup_image() -> object:
            assert_collect_destructive_bounds(out)
            manifest = assemble_disposable_image(out)
            holder["manifest"] = manifest
            holder["image"] = Path(manifest["image"])
            assert_collect_destructive_bounds(out, holder["image"])  # type: ignore[arg-type]
            return manifest

        recorder.run_leg(
            leg="collect-setup-image", gate="device_gate_for_image",
            frozen_predicate="disposable image assembles outside the source tree",
            run=_setup_image,
            context=lambda: _context_for(image=holder.get("image")),  # type: ignore[arg-type]
        )

        def _setup_gate() -> object:
            raw_image = holder.get("image")
            require_collect_precondition(
                raw_image if isinstance(raw_image, Path) else None,
                message=(
                    "device_gate_for_image precondition absent: collect "
                    "setup never produced an image (setup-image RED)"
                ),
            )
            assert isinstance(raw_image, Path)
            image = raw_image
            gate = device_gate_for_image(image)
            holder["gate"] = gate
            proof = install_payload_to_device(image, out / "guest-payload")
            holder["install_proof"] = proof
            bind_gate_to_install(gate, proof)
            return {"gate": "device_gate_for_image", "green": True}

        recorder.run_leg(
            leg="collect-setup-device-gate", gate="device_gate_for_image",
            frozen_predicate=COLLECT_FROZEN_PREDICATES["device_gate_for_image"],
            run=_setup_gate,
            context=lambda: _context_for(
                image=holder.get("image"),  # type: ignore[arg-type]
            ),
        )
        image = holder.get("image")
        # Fail-closed early return (the only skip permitted by
        # COLLECT_CONTINUATION_RULES): without a disposable image no
        # boot leg or binding has anything to observe; diagnostics are
        # still emitted with the setup reds aggregated.
        if not isinstance(image, Path):
            artifact = build_device_collect_diagnostics(recorder, run_meta=run_meta)
            artifact_path = write_device_collect_diagnostics(out, artifact)
            return {
                "schema_version": SCHEMA_VERSION,
                "ok": False,
                "classification": "DEVICE_T7_DEVRUN3_COLLECT",
                "collect_mode": True,
                "spec": lifecycle_spec(),
                "steps": [],
                "collected_reds": [dict(entry) for entry in recorder.reds],
                "diagnostics_artifact": str(artifact_path),
                "diagnostics": artifact,
                "device_scope": {"executed": False,
                                 "detail": "collect setup never produced an image"},
                "limitations": ["does not prove Acer or physical-firmware behavior"],
            }

        machine = fresh_machine_state(self.machine_root)
        contract_bytes = build_persistent_state_contract_bytes()
        factory = self.seams_factory or ImageIntegrationSeams
        seams = factory(self.machine_root / "integration", contract_bytes)
        private_key, _ = mint_signing_keys(self.machine_root, machine["keys"])
        for name, release_id, sequence in (
            ("r21", "greia-0.21.0", 21),
            ("r22broken", "greia-0.21.1", 22),
            ("r23", "greia-0.22.0", 23),
        ):
            build_test_release(
                self.machine_root, name=name, release_id=release_id,
                sequence=sequence, private_key=private_key,
            )
        steps: list[dict[str, object]] = []
        shipped_legs_used: list[str] = []
        launcher_legs_used: list[str] = []
        boot_legs: list[dict[str, object]] = []
        leg_samples: list[dict[str, object]] = []
        from .devproof import record_leg_sample as _record_leg_sample

        def _observe(step: str) -> dict[str, object]:
            backend = GrubEnvBackend.attach(machine["boot_control"]).inspect()
            try:
                journal = BootTransactionJournal.load(
                    machine["state"] / "system-updates" / "journal"
                )
                journal_state: object = journal.state.value
                candidate: object = journal.candidate_slot
            except Exception:
                journal_state = None
                candidate = None
            record = _load_record(machine["layout"])
            try:
                accepted_seq: object = read_accepted_sequence(machine["state"])
            except Exception:
                accepted_seq = None
            return {
                "step": step,
                "default_slot": backend.default_slot,
                "one_shot_slot": backend.one_shot_slot,
                "last_booted_slot": backend.last_booted_slot,
                "journal_state": journal_state,
                "journal_candidate": candidate,
                "accepted_slot": record.accepted_slot,
                "accepted_release": record.accepted_release_id,
                "accepted_sequence": accepted_seq,
                "persist_marker": sha256_file(machine["persist"] / "profile.json"),
                "image_sha256": sha256_file(image),
            }

        def _collect_boot_leg(
            leg: str, capture: BootLegCapture | None = None,
        ) -> dict[str, object]:
            """One real SeaBIOS boot with independent on-image observation.

            Re-reads on-image state fresh per leg (pre/post), derives the
            observed slot solely from those bytes via the frozen
            :func:`decide_device_boot_observation` predicate, stamps
            through the production ``reconcile`` on the real on-image
            bytes, gates with ``read_attestation_signal`` through the
            post-boot loop remount/read path, and only then folds into
            the host backend. Teardown uses the checked (abort-class)
            path; observation REDs are fail-fast errors for collection.

            ``capture`` (a :class:`BootLegCapture`) is populated
            progressively (pre → boot → post → elapsed) so the
            recorder's failure context forwards the live evidence that
            exists at the throw site instead of recording ``None``.
            """
            import time as _time

            expected = BOOT_OUTCOME_EXPECTED_SLOT[leg]
            started = _time.monotonic()
            cap = capture if capture is not None else BootLegCapture()
            pre = self._read_on_image_grubenv_strict(image)
            cap.pre = dict(pre)
            boot = self._boot_image_once(image, leg=leg)
            cap.boot = dict(boot)
            post = self._read_on_image_grubenv_strict(image)
            cap.post = dict(post)
            elapsed = _time.monotonic() - started
            cap.elapsed_seconds = elapsed
            observed = decide_device_boot_observation(leg=leg, pre=pre, post=post)
            if observed != expected:
                raise LifecycleHarnessError(
                    f"device boot leg {leg} observed {observed!r}, "
                    f"expected {expected!r}"
                )
            signal = self._stamp_and_gate_on_image_strict(
                image, observed=observed, expected=expected
            )
            check_boot_exit(int(boot["returncode"]), leg=leg,
                            qemu_log=Path(str(boot["qemu_log"])))
            GrubEnvBackend.attach(machine["boot_control"]).reconcile(observed)
            evidence = {
                **boot,
                "expected_slot": expected,
                "observed_slot": observed,
                "on_image_pre": pre,
                "on_image_post": post,
                "attestation_signal": signal,
                "disk_snapshot": snapshot_device_collect_state(
                    image=image, machine=machine),
                "timeout": policy.classify(
                    serial_growth_bytes=int(boot.get("serial_growth_bytes", 0)),
                    image_sha_changed=(
                        boot.get("image_sha256_post") != boot.get("image_sha256_pre")
                    ),
                    elapsed_seconds=elapsed,
                    clean_exit=True,
                ),
            }
            boot_legs.append(evidence)
            return evidence

        def _leg_context(
            boot: Mapping[str, object] | None = None,
            pre: Mapping[str, object] | None = None,
            post: Mapping[str, object] | None = None,
        ) -> dict[str, object]:
            return _context_for(boot=boot, pre=pre, post=post,
                                machine=machine, image=image)

        # Leg 1: fresh install A (production-composed install proof).
        def _leg_fresh_install() -> object:
            composition = prove_install_composition(
                out / "install-proof",
                layout_record_path=machine["layout"],
                password_hash=_PASSWORD_HASH,
            )
            observed = _observe("fresh-install-A")
            holder["persist_marker"] = observed["persist_marker"]
            steps.append({**observed,
                           "install_composition_mode": composition["install_mode"]})
            leg_samples.append(dict(_record_leg_sample("fresh-install-A",
                                                       surface="DEVICE")))
            return composition

        recorder.run_leg(
            leg="fresh-install-A", gate="device_gate_for_image",
            frozen_predicate="production-composed install proof resolves in ab mode",
            run=_leg_fresh_install,
            context=lambda: _leg_context(),
        )

        # Leg 2: boot A accepted (plain default boot, launcher accepts).
        boot_a_capture = BootLegCapture()

        def _leg_boot_a() -> object:
            boot = _collect_boot_leg("boot-A-accepted", capture=boot_a_capture)
            boot_a_capture.clean_exit = True
            launcher_a = self._launcher_boot(
                machine, booted_slot=str(boot["observed_slot"]),
                release_id="greia-0.20.0", sequence=20,
            )
            launcher_legs_used.append("boot-A-accepted")
            obs = _observe("boot-A-accepted")
            if launcher_a["seam_calls"] != ["interactive_ready"]:
                raise LifecycleContractError(
                    "launcher seam was not called exactly once")
            steps.append({**obs, "launcher": launcher_a,
                           "device_boot": boot["image_sha256_post"]})
            return boot

        recorder.run_leg(
            leg="boot-A-accepted", gate="consumption-predicate",
            frozen_predicate=COLLECT_FROZEN_PREDICATES["consumption-predicate"],
            run=_leg_boot_a,
            context=lambda: boot_a_capture.to_context(
                machine=machine, image=image, policy=policy,
            ),
        )

        # Legs 3-4: stage + arm B through the shipped endpoint, push the
        # armed block to the image, boot B, launcher accepts, commit.
        # Each later leg rebuilds the shipped authority from production
        # primitives instead of asserting on an earlier leg's in-memory
        # product, so a RED stage leg yields a shipped-path RED under a
        # frozen predicate rather than an AssertionError.
        authority_holder: dict[str, object] = {}

        def _build_collect_authority() -> tuple[object, object]:
            authority = shipped_update_authority(
                state_dir=machine["state"],
                trusted_key_dir=machine["keys"],
                layout_record_path=machine["layout"],
                boot_backend=GrubEnvBackend.attach(machine["boot_control"]),
                seams=seams,
            )
            authority_holder["authority"] = authority
            endpoint = UpdatePrivilegedEndpoint(authority)  # type: ignore[arg-type]
            peer = PeerCredential(uid=0)
            authority_holder["endpoint"] = endpoint
            authority_holder["peer"] = peer

            def _op(name: str) -> dict[str, object]:
                raw = endpoint.handle_request(
                    build_request(name), peer=peer, boot_state="update_ready"
                )
                _txid, op_name, payload = read_response(raw)
                if op_name == "ERROR":
                    raise LifecycleContractError(
                        f"shipped endpoint refused {name}: {payload}"
                    )
                return dict(payload)

            authority_holder["op"] = _op
            return authority, _op

        def _require_collect_op(*, leg: str) -> object:
            existing = authority_holder.get("op")
            if callable(existing):
                return existing
            _authority, fresh_op = _build_collect_authority()
            require_collect_precondition(
                fresh_op if callable(fresh_op) else None,
                message=(
                    f"shipped stage precondition absent for {leg}: "
                    "stage-B-one-shot did not establish the shipped "
                    "endpoint (shipped build_live_update_service path RED)"
                ),
            )
            return fresh_op

        def _require_collect_authority(*, leg: str) -> object:
            existing = authority_holder.get("authority")
            if existing is not None:
                return existing
            authority, _op = _build_collect_authority()
            require_collect_precondition(
                authority,
                message=(
                    f"shipped authority precondition absent for {leg}: "
                    "stage-B-one-shot did not establish the shipped "
                    "authority (shipped build_live_update_service path RED)"
                ),
            )
            return authority

        def _leg_stage_b() -> object:
            authority, _op = _build_collect_authority()
            shipped_legs_used.append("stage-B-one-shot")
            received = self.machine_root / "releases" / "r21" / "r21.greiaupdate"
            SystemUpdateInbox(machine["state"]).receive(received)
            verified = authority.verify_current_candidate()
            if not verified.present:
                raise LifecycleContractError("staged candidate did not verify")
            staged = _op("STAGE_CURRENT_CANDIDATE")
            if staged.get("status") != "STAGED":
                raise LifecycleContractError("shipped stage leg did not report STAGED")
            detail = staged.get("detail", {})
            if not isinstance(detail, dict) or detail.get("candidate_slot") != "B":
                raise LifecycleContractError("shipped stage did not target system-b")
            if ("store:system-b" not in seams.contacts
                    or "store:system-a" in seams.contacts):
                raise LifecycleContractError("shipped stage touched the wrong slot")
            obs = _observe("stage-B-one-shot")
            if obs["default_slot"] != "A":
                raise LifecycleContractError("default moved before health commit")
            steps.append({**obs, "shipped_stage": staged})
            leg_samples.append(dict(_record_leg_sample("stage-B-one-shot",
                                                       surface="DEVICE")))
            return staged

        recorder.run_leg(
            leg="stage-B-one-shot", gate="device_gate_for_image",
            frozen_predicate="shipped build_live_update_service stage targets system-b",
            run=_leg_stage_b,
            context=lambda: _leg_context(),
        )

        boot_b_capture = BootLegCapture()

        def _leg_boot_b() -> object:
            _op = _require_collect_op(leg="boot-B-commit")
            assert callable(_op)
            armed = _op("ARM_CURRENT_CANDIDATE")
            if armed.get("status") != "ARMED":
                raise LifecycleContractError("shipped arm leg did not report ARMED")
            self._sync_boot_state_to_image_strict(image, machine["boot_control"])
            shipped_legs_used.append("boot-B-commit")
            boot = _collect_boot_leg("boot-B-commit", capture=boot_b_capture)
            boot_b_capture.clean_exit = True
            launcher_b = self._launcher_boot(
                machine, booted_slot=str(boot["observed_slot"]),
                release_id="greia-0.21.0", sequence=21,
                filesystem_files=seams.files,
            )
            launcher_legs_used.append("boot-B-commit")
            if launcher_b["accepted_slot"] != "B":
                raise LifecycleContractError("launcher leg did not accept B")
            obs = _observe("boot-B-commit")
            if obs["default_slot"] != "B" or obs["accepted_slot"] != "B":
                raise LifecycleContractError(
                    "persistent default/accepted record not on B")
            if obs["accepted_sequence"] != 21:
                raise LifecycleContractError("accepted sequence did not advance to 21")
            steps.append({**obs, "launcher": launcher_b,
                           "device_boot": boot["image_sha256_post"]})
            leg_samples.append(dict(_record_leg_sample("boot-B-commit",
                                                       surface="DEVICE")))
            return boot

        recorder.run_leg(
            leg="boot-B-commit", gate="consumption-predicate",
            frozen_predicate=COLLECT_FROZEN_PREDICATES["consumption-predicate"],
            run=_leg_boot_b,
            context=lambda: boot_b_capture.to_context(
                machine=machine, image=image, policy=policy,
            ),
        )

        # Leg 5: stage + arm the deliberately broken candidate (system-a).
        def _leg_stage_broken() -> object:
            _op = _require_collect_op(leg="stage-broken-candidate")
            assert callable(_op)
            _authority = _require_collect_authority(
                leg="stage-broken-candidate")
            broken_bundle = (self.machine_root / "releases" / "r22broken"
                             / "r22broken.greiaupdate")
            SystemUpdateInbox(machine["state"]).receive(broken_bundle)
            _authority.verify_current_candidate()  # type: ignore[union-attr]
            staged_broken = _op("STAGE_CURRENT_CANDIDATE")
            if staged_broken.get("status") != "STAGED":
                raise LifecycleContractError("broken candidate did not stage")
            broken_detail = staged_broken.get("detail", {})
            if (not isinstance(broken_detail, dict)
                    or broken_detail.get("candidate_slot") != "A"):
                raise LifecycleContractError(
                    "broken candidate did not target system-a")
            armed_broken = _op("ARM_CURRENT_CANDIDATE")
            if armed_broken.get("status") != "ARMED":
                raise LifecycleContractError("broken candidate did not arm")
            steps.append({**_observe("stage-broken-candidate"),
                           "shipped_stage": staged_broken})
            return staged_broken

        recorder.run_leg(
            leg="stage-broken-candidate", gate="device_gate_for_image",
            frozen_predicate="shipped stage of the broken candidate targets system-a",
            run=_leg_stage_broken,
            context=lambda: _leg_context(),
        )

        # Leg 6: boot broken candidate -> observed on A via the image,
        # health never confirms, recovery trigger marks FAILED, default B.
        boot_broken_capture = BootLegCapture()

        def _leg_boot_broken() -> object:
            self._sync_boot_state_to_image_strict(image, machine["boot_control"])
            boot_broken = _collect_boot_leg(
                "boot-broken-candidate", capture=boot_broken_capture)
            boot_broken_capture.clean_exit = True
            journal_dir = machine["state"] / "system-updates" / "journal"
            coordinator = BootTransactionCoordinator.resume(
                journal_dir=journal_dir,
                backend=GrubEnvBackend.attach(machine["boot_control"]),
                candidate_artifacts=_artifact_set("A", "greia-0.21.1", 22),
                accepted_artifacts=_artifact_set("B", "greia-0.21.0", 21),
            )
            observed_booted, _decision = coordinator.observe_boot()
            if observed_booted != str(boot_broken["observed_slot"]):
                raise LifecycleContractError(
                    "journal fold did not follow the on-image observation"
                )
            decision = mark_candidate_unhealthy(
                coordinator,
                recovery_class="health-service-failure",
                detail="t7-devrun3 controlled post-boot failure",
            )
            journal_after = BootTransactionJournal.load(journal_dir)
            if journal_after.state is not BootTransactionState.FAILED:
                raise LifecycleContractError("broken candidate was not marked FAILED")
            if (GrubEnvBackend.attach(machine["boot_control"]).inspect()
                    .default_slot != "B"):
                raise LifecycleContractError("recovery trigger mutated the default")
            steps.append({**_observe("boot-broken-candidate"),
                           "recovery_decision": decision.note,
                           "device_boot": boot_broken["image_sha256_post"]})
            return boot_broken

        recorder.run_leg(
            leg="boot-broken-candidate", gate="consumption-predicate",
            frozen_predicate=COLLECT_FROZEN_PREDICATES["consumption-predicate"],
            run=_leg_boot_broken,
            context=lambda: boot_broken_capture.to_context(
                machine=machine, image=image, policy=policy,
            ),
        )

        # Leg 7: recovery boot of B (bounded launcher no-op, PERSIST kept).
        # The expected PERSIST marker is the one recorded by the fresh
        # install leg (holder), not a positional steps index, so a RED
        # install leg yields a frozen-predicate RED here instead of an
        # IndexError.
        recovery_capture = BootLegCapture()

        def _leg_recovery() -> object:
            boot_rec = _collect_boot_leg(
                "recovery-boot-B", capture=recovery_capture)
            recovery_capture.clean_exit = True
            launcher_r = self._launcher_boot(
                machine, booted_slot=str(boot_rec["observed_slot"]),
                release_id="greia-0.21.0", sequence=21,
                expect_no_acceptance=True,
            )
            launcher_legs_used.append("recovery-boot-B")
            obs = _observe("recovery-boot-B")
            if obs["default_slot"] != "B":
                raise LifecycleContractError(
                    "recovery boot did not return to default B")
            expected_persist = holder.get("persist_marker")
            require_collect_precondition(
                expected_persist,
                message=(
                    "PERSIST-marker precondition absent for "
                    "recovery-boot-B: fresh-install-A did not record a "
                    "persist marker (install proof RED)"
                ),
            )
            if obs["persist_marker"] != expected_persist:
                raise LifecycleContractError("PERSIST marker did not survive recovery")
            steps.append({**obs, "launcher": launcher_r,
                           "device_boot": boot_rec["image_sha256_post"]})
            return boot_rec

        recorder.run_leg(
            leg="recovery-boot-B", gate="consumption-predicate",
            frozen_predicate=COLLECT_FROZEN_PREDICATES["consumption-predicate"],
            run=_leg_recovery,
            context=lambda: recovery_capture.to_context(
                machine=machine, image=image, policy=policy,
            ),
        )

        # Leg 8: B-to-A reverse update through the shipped path + boot.
        reverse_capture = BootLegCapture()

        def _leg_reverse() -> object:
            _op = _require_collect_op(leg="reverse-update-B-to-A")
            assert callable(_op)
            _authority = _require_collect_authority(
                leg="reverse-update-B-to-A")
            reverse_bundle = (self.machine_root / "releases" / "r23"
                              / "r23.greiaupdate")
            SystemUpdateInbox(machine["state"]).receive(reverse_bundle)
            _authority.verify_current_candidate()  # type: ignore[union-attr]
            staged_rev = _op("STAGE_CURRENT_CANDIDATE")
            if staged_rev.get("status") != "STAGED":
                raise LifecycleContractError("reverse update did not stage")
            if "store:system-a" not in seams.contacts:
                raise LifecycleContractError("reverse update did not target system-a")
            rearmed = _op("ARM_CURRENT_CANDIDATE")
            if rearmed.get("status") != "ARMED":
                raise LifecycleContractError("reverse update did not arm")
            self._sync_boot_state_to_image_strict(image, machine["boot_control"])
            shipped_legs_used.append("reverse-update-B-to-A")
            boot_rev = _collect_boot_leg(
                "reverse-update-B-to-A", capture=reverse_capture)
            reverse_capture.clean_exit = True
            launcher_rev = self._launcher_boot(
                machine, booted_slot=str(boot_rev["observed_slot"]),
                release_id="greia-0.22.0", sequence=23,
                filesystem_files=seams.files,
            )
            launcher_legs_used.append("reverse-update-B-to-A")
            if launcher_rev["accepted_slot"] != "A":
                raise LifecycleContractError("reverse update did not accept A")
            obs = _observe("reverse-update-B-to-A")
            if obs["default_slot"] != "A" or obs["accepted_sequence"] != 23:
                raise LifecycleContractError("reverse update did not land on A/23")
            steps.append({**obs, "launcher": launcher_rev,
                           "device_boot": boot_rev["image_sha256_post"]})
            leg_samples.append(dict(_record_leg_sample("reverse-update-B-to-A",
                                                       surface="DEVICE")))
            return boot_rev

        recorder.run_leg(
            leg="reverse-update-B-to-A", gate="consumption-predicate",
            frozen_predicate=COLLECT_FROZEN_PREDICATES["consumption-predicate"],
            run=_leg_reverse,
            context=lambda: reverse_capture.to_context(
                machine=machine, image=image, policy=policy,
            ),
        )

        # Post-run loop/cross-check binding: always attempted with its
        # own capture once setup yields an image, even with prior reds.
        # The no-image fail-closed early return above is the only skip.
        def _leg_loop_binding() -> object:
            from greia_installer.layout import ProfileSizing, plan_for_profile

            assert_collect_destructive_bounds(out, image)
            sizing = ProfileSizing(
                layout_adapter_id=LAYOUT_ADAPTER_ID,
                slot_bytes=1073741824,
                persist_minimum_bytes=268435456,
                boot_backend=BOOT_BACKEND_ID,
            )
            plan = plan_for_profile(sizing, device_size_bytes=4 * 1024 * 1024 * 1024)
            device = self._loop_attach(image)
            try:
                loop_result = observe_loop_attached_device(
                    device, plan=plan, record_path=machine["layout"],
                )
                cross = run_file_cross_check(
                    image,
                    expected_signature=str(loop_result["proven_signature"]),
                )
                if not cross["executed"] or not cross["green"]:
                    raise LifecycleHarnessError(
                        "file cross-check must execute and pass on a capable host"
                    )
                return {"loop_attach_green": True, "cross_check": cross}
            finally:
                self._loop_detach_checked(device)

        recorder.run_leg(
            leg="post-run-loop-cross-check", gate="post-run-loop-cross-check",
            frozen_predicate=COLLECT_FROZEN_PREDICATES["post-run-loop-cross-check"],
            run=_leg_loop_binding,
            context=lambda: _leg_context(),
        )

        # Devproof device envelope: always attempted with its own
        # capture; RED fails the device run closed (recorded, kept RED).
        def _leg_envelope() -> object:
            from .devproof import run_envelope_device

            bundle = self.machine_root / "releases" / "r21" / "r21.greiaupdate"
            return run_envelope_device(
                out / "devproof-device",
                bundle_path=bundle if bundle.is_file() else None,
                leg_samples=leg_samples,
            )

        envelope_result = recorder.run_leg(
            leg="devproof-device-envelope", gate="devproof-device-envelope",
            frozen_predicate=COLLECT_FROZEN_PREDICATES["devproof-device-envelope"],
            run=_leg_envelope,
            context=lambda: _leg_context(),
        )

        verdict = recorder.verdict()
        artifact = build_device_collect_diagnostics(recorder, run_meta=run_meta)
        artifact_path = write_device_collect_diagnostics(out, artifact)
        report: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "ok": bool(verdict["ok"]),
            "classification": "DEVICE_T7_DEVRUN3_COLLECT",
            "collect_mode": True,
            "spec": lifecycle_spec(),
            "image_manifest": holder.get("manifest"),
            "device_gate": holder.get("gate"),
            "install_proof": holder.get("install_proof"),
            "shipped_update_legs": list(shipped_legs_used),
            "launcher_acceptance_legs": list(launcher_legs_used),
            "boot_outcome_legs": list(BOOT_OUTCOME_LEGS),
            "device_boots": boot_legs,
            "steps": steps,
            "devproof_envelope": envelope_result,
            "collected_reds": [dict(entry) for entry in recorder.reds],
            "collect_leg_order": list(COLLECT_LEG_ORDER),
            "diagnostics_artifact": str(artifact_path),
            "diagnostics": artifact,
            "device_scope": {
                "executed": True,
                "collect_mode": True,
                "red_count": verdict["red_count"],
                "image_sha256": sha256_file(image),
            },
            "limitations": [
                "fail-collect widens observation only: every recorded "
                "RED keeps its fail-fast predicate and stays RED",
                "does not prove Acer or physical-firmware behavior",
            ],
        }
        self.report_path.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        return report

    def _loop_attach(self, image: Path) -> Path:
        completed = run_device_host_tool(
            ["losetup", "--find", "--show", str(image)],
            capture_output=True, text=True, timeout=60,
        )
        if completed.returncode != 0:
            raise LifecycleHarnessError("loop attach failed for the disposable image")
        node = Path(str(completed.stdout).strip())
        settle = run_device_host_tool(
            ["udevadm", "settle"], capture_output=True, timeout=60
        )
        _ = settle
        time.sleep(0.5)
        return node

    def _loop_detach(self, device: Path) -> None:
        run_device_host_tool(
            ["losetup", "--detach", str(device)], capture_output=True, timeout=60
        )


def assert_lifecycle_transitions(report: Mapping[str, object]) -> None:
    """Enforce the harness's own transition contract on a lifecycle report.

    A runner that reboots the same disk without lifecycle transitions fails
    here: the report must carry the exact 8-step sequence in order, with
    observable slot movement (default A -> staged B -> committed B ->
    failed candidate -> recovery B -> reversed A) and distinct shipped +
    launcher leg coverage. Anything narrower raises
    :class:`LifecycleContractError` (positive-control RED).

    The frozen T7-ATTEST leg partition (3 non-boot + 5 boot-outcome) is
    pinned first: any drift between ``LIFECYCLE_SEQUENCE`` and the frozen
    ``NON_BOOT_TRANSITIONS`` / ``BOOT_OUTCOME_LEGS`` sets is itself RED.
    """
    if (
        set(NON_BOOT_TRANSITIONS) | set(BOOT_OUTCOME_LEGS)
        != set(LIFECYCLE_SEQUENCE)
        or len(set(LIFECYCLE_SEQUENCE)) != 8
        or len(NON_BOOT_TRANSITIONS) != 3
        or len(BOOT_OUTCOME_LEGS) != 5
        or set(BOOT_OUTCOME_LEGS) != set(BOOT_OUTCOME_EXPECTED_SLOT)
    ):
        raise LifecycleContractError(
            "frozen leg definition drifted: 8 transitions must partition "
            "exactly into the 3 frozen non-boot transitions and the 5 "
            "frozen boot-outcome legs"
        )
    steps = report.get("steps", [])
    if not isinstance(steps, list) or len(steps) != len(LIFECYCLE_SEQUENCE):
        raise LifecycleContractError(
            "lifecycle report does not carry the full 8-step transition set"
        )
    names = [s.get("step") for s in steps if isinstance(s, dict)]
    if names != list(LIFECYCLE_SEQUENCE):
        raise LifecycleContractError(
            f"lifecycle transitioned out of contract: {names!r}"
        )
    defaults = [s.get("default_slot") for s in steps if isinstance(s, dict)]
    if not ("A" in defaults and "B" in defaults):
        raise LifecycleContractError(
            "lifecycle shows no slot movement; same-disk reboot without "
            "transitions is not a lifecycle"
        )
    shipped = report.get("shipped_update_legs", [])
    for leg in SHIPPED_UPDATE_LEGS:
        if leg not in shipped:  # type: ignore[operator]
            raise LifecycleContractError(f"shipped leg {leg} bypassed the constructor")
    launcher = report.get("launcher_acceptance_legs", [])
    for leg in LAUNCHER_ACCEPTANCE_LEGS:
        if leg not in launcher:  # type: ignore[operator]
            raise LifecycleContractError(f"launcher leg {leg} bypassed acceptance")


def _artifact_set(slot: str, release_id: str, sequence: int, *, active: bool = False):  # type: ignore[no-untyped-def]
    from greia_platform.boot_transaction import BootArtifactSet

    number = "02" if slot == "A" else "03"
    fs_uuid = _UUID_A_FS if slot == "A" else _UUID_B_FS
    return BootArtifactSet(
        slot=slot,
        layout_id=LAYOUT_ADAPTER_ID,
        boot_backend=BOOT_BACKEND_ID,
        generic_kernel_sha256="cd" * 32,
        generic_initramfs_sha256="ef" * 32,
        root_partuuid=f"{_MBR_SIGNATURE}-{number}",
        root_filesystem_uuid=fs_uuid,
        release_id=release_id,
        release_sequence=sequence,
    )
