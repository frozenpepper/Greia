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


def require_device_host(*, runner_which=None) -> None:
    """Fail closed unless this host can execute the device path."""
    import sys as _sys

    which = runner_which or shutil.which
    if _sys.platform != "linux":
        raise LifecycleHarnessError(
            "device lifecycle requires a Linux host "
            f"(this host reports {_sys.platform}); source-scope proof only"
        )
    if os.geteuid() != 0:
        raise LifecycleHarnessError("device lifecycle runs as root on a Linux host")
    missing = [
        command
        for command in (
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
        if which(command) is None
    ]
    if missing:
        raise LifecycleHarnessError("missing device host tools: " + ", ".join(missing))


def file_cross_check_tools() -> dict[str, str | None]:
    """Resolve the file cross-check tools (must both exist to execute)."""
    return {"sfdisk": shutil.which("sfdisk"), "blkid": shutil.which("blkid")}


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
    if (
        require_mbr_disk_signature(disk_id.stdout.strip(), field="disk signature")
        != expected_signature
    ):
        return {"executed": True, "green": False, "detail": "sfdisk disk-id mismatch"}
    probed = subprocess.run(
        [tools["blkid"], "-p", "-s", "PTUUID", "-o", "value", str(image)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if probed.returncode != 0:
        return {"executed": True, "green": False, "detail": "blkid -p PTUUID failed"}
    if (
        require_mbr_disk_signature(probed.stdout.strip(), field="disk signature")
        != expected_signature
    ):
        return {"executed": True, "green": False, "detail": "blkid PTUUID mismatch"}
    return {"executed": True, "green": True, "detail": "sfdisk+blkid agree with byte parse"}


def observe_loop_attached_device(
    device: Path, *, plan: object, record_path: Path
) -> dict[str, object]:
    """Run the production observation path against a loop-attached device.

    Device scope only: probes the disk signature once plus each
    system-a/system-b/persist PARTUUID and filesystem UUID through
    ``SubprocessMbrProbeRunner`` (argument arrays, ``shell=False``), then
    proves the bound record equals the observed topology. Raises
    fail-closed on any mismatch; returns the observed identities plus the
    proven signature on success.
    """
    from greia_installer.disk import DeviceObservation
    from greia_installer.layout import (
        SubprocessMbrProbeRunner,
        build_observed_mbr_topology,
        observe_legacy_mbr_identities,
        verify_mbr_topology_for_boot,
    )
    from greia_platform.persistent_layout import InstalledLayoutRecord

    if not str(device) or not device.is_absolute():
        raise LifecycleHarnessError("loop observation needs an absolute device path")
    runner = SubprocessMbrProbeRunner()
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
    observed = observe_legacy_mbr_identities(runner, target=target, plan=plan)
    record = InstalledLayoutRecord.read_from(Path(record_path))
    topology = build_observed_mbr_topology(plan=plan, target=target, identities=observed)
    signature = verify_mbr_topology_for_boot(
        record, topology, expected_disk_signature=observed_signature(record, observed)
    )
    return {
        "observed": observed,
        "proven_signature": signature,
        "loop_attach_green": True,
    }


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
    embed_payload_descriptor(image, payload)
    cost = payload_assembly_cost(out / "guest-payload")
    manifest = {
        "image": str(image),
        "image_sha256": sha256_file(image),
        "adapter": plan.adapter_id,
        "label_type": plan.label_type,
        "roles": [p.role for p in plan.partitions],
        "install_composition_mode": composition["install_mode"],
        "grub_cfg_bytes": len(grub_text.encode("utf-8")),
        "payload_magic": "GREIAPY1",
        "payload_descriptor": "sector-1:512",
        "payload_grub_cfg_sha256": payload.grub_cfg_sha256,
        "payload_grubenv_sha256": payload.grubenv_sha256,
        "payload_grub_cfg_bytes": payload.grub_cfg_bytes,
        "payload_grubenv_bytes": payload.grubenv_bytes,
        "payload_guest_paths": ["/grub.cfg", "/grubenv"],
        "payload_files_touched": cost["files_touched"],
        "payload_whole_ram_copy": cost["whole_payload_ram_copy"],
    }
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
    """Payload + sector-gap gate for the real boot path (fail-closed).

    A payload-less/tampered image REDs here — in the device body before
    any QEMU boot is claimed — not only in the helper unit tests. The
    sector 1-2047 gap reservation is pinned alongside so a future GRUB
    ``core.img`` embed cannot silently clobber the descriptor.
    """
    from .payload import assert_payload_present, verify_sector_gap_reserved

    descriptor = assert_payload_present(Path(image))
    gap = verify_sector_gap_reserved(Path(image))
    return {"descriptor": descriptor, "gap": gap}


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
            completed = subprocess.run(argv, capture_output=True, timeout=60)
            if completed.returncode != 0:
                raise LifecycleHarnessError(message + f" for {device}")
        time.sleep(0.5)
        mountpoint.mkdir(parents=True, exist_ok=True)
        argv = ["mount", "-t", "ext4"]
        if read_only:
            argv.extend(["-o", "ro"])
        argv.extend([str(part), str(mountpoint)])
        mounted = subprocess.run(argv, capture_output=True, timeout=60)
        if mounted.returncode != 0:
            raise LifecycleHarnessError(f"partition-1 mount failed for {device}")

    def _unmount(self, mountpoint: Path) -> None:
        subprocess.run(["umount", str(mountpoint)], capture_output=True, timeout=60)

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
        SHA). The clean-exit gate (:func:`check_boot_exit`) runs before
        any observation: timeout or nonzero status is RED, never a
        claimed boot. Guest disk writes persist (no snapshot flag) so
        grubenv effects are observable after the boot exits.
        """
        argv, serial_log, host_log = device_qemu_argv(
            Path(image),
            output_dir=Path(self.config.output_dir),
            leg=leg,
            memory_mib=self.config.memory_mib,
            cpus=self.config.cpus,
            seabios_path=self.config.seabios_path,
        )
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
                returncode = process.wait(timeout=self.config.timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                import signal as _signal

                try:
                    os.killpg(process.pid, _signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, _signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        pass
                    process.wait()
                raise LifecycleHarnessError(
                    f"device boot leg {leg} exceeded timeout; "
                    f"inspect {host_log} (unclean exit is RED)"
                ) from exc
        check_boot_exit(returncode, leg=leg, qemu_log=host_log)
        return {
            "leg": leg,
            "returncode": returncode,
            "qemu_argv": list(argv),
            "serial_log": str(serial_log),
            "qemu_log": str(host_log),
            "image_sha256_pre": pre_sha,
            "image_sha256_post": sha256_file(Path(image)),
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

        Preserved fixer-1 gates (verbatim): fail-closed
        ``require_device_host`` strictness; the payload + sector-gap gate
        (``device_gate_for_image``: a payload-less/tampered image REDs the
        real boot path before any QEMU boot); the clean-exit gate per
        boot (unclean QEMU exit is RED); per-leg disk-file proof with the
        image SHA bound after the payload embed (pre/post SHA per boot
        leg); the post-run loop/cross-check binding (executed-and-green
        enforced on a capable host); honest device/source classification
        (``DEVICE_T7_DEVRUN3`` only when the device path executed).

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

        Source readiness only: with the T7-PAYLOAD minimal image (no
        guest userspace/kernel yet) a capable host reaches the clean-exit
        gate RED fail-closed; live green belongs to T7-DEVRUN-LIVE2.
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

    def _loop_attach(self, image: Path) -> Path:
        completed = subprocess.run(
            ["losetup", "--find", "--show", str(image)],
            capture_output=True, text=True, timeout=60,
        )
        if completed.returncode != 0:
            raise LifecycleHarnessError("loop attach failed for the disposable image")
        node = Path(completed.stdout.strip())
        settle = subprocess.run(["udevadm", "settle"], capture_output=True, timeout=60)
        _ = settle
        time.sleep(0.5)
        return node

    def _loop_detach(self, device: Path) -> None:
        subprocess.run(["losetup", "--detach", str(device)], capture_output=True, timeout=60)


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
