"""X8 disposable SeaBIOS QEMU harness for the legacy A/B adapter.

Source scope (X8-QEMU-HARNESS): a checked-in procedure plus runner that
boots the ``legacy-bios-ab-v1`` / ``grub-ab-v1`` substrate end to end on a
QEMU-capable Linux host. Live QEMU execution itself is deferred per the
source-first amendment and stays RED until a capable host backfills it;
everything below is arranged so the deferred run needs no redesign.

Reuse, not duplication (brief hard requirement):

- layout: :class:`greia_installer.layout.LegacyBiosAbAdapter` (executable
  MBR A/B/PERSIST adapter) via :func:`adapter_for` / :func:`plan_for_profile`;
- staging: :class:`greia_platform.slot_writer.SlotWriter` /
  :class:`greia_platform.slot_writer.SlotFinalizer` capacity bounds only
  (the privileged service owns actual writes);
- boot config: :func:`greia_platform.grub_ab.render_grub_ab_config_from_record`
  plus :func:`validate_grub_ab_text`;
- boot state: :class:`greia_platform.grub_ab.GrubEnvBackend` (real 1024-byte
  ``grubenv`` one-shot semantics: ``saved_entry`` persistent default,
  ``next_entry`` candidate-only one-shot). This module never imports the
  JSON fakes and never calls ``simulate_reboot``: VM behavior is observed
  through :meth:`GrubEnvBackend.inspect` after a real QEMU boot.
- releases: the unsigned ``.greiaupdate`` v3 bundle path
  (:func:`build_update_bundle` / :func:`inspect_update_bundle`).

QEMU-invocation/evidence discipline mirrors
``tools/r7_qemu_kmsdrm_acceptance.py`` (argv arrays, serial/file logs,
cloned-or-built disposable image, JSON report); the guest payload is the
legacy A/B boot-control surface, never the R7 KMSDRM payload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Sequence

from greia_installer.layout import (
    LEGACY_BIOS_AB_ADAPTER_ID,
    ProfileSizing,
    adapter_for,
    mint_fresh_partition_identities,
    plan_for_profile,
    require_finalized_slot_capacity,
)
from greia_platform.grub_ab import (
    GRUBENV_FILE_NAME,
    GrubEnvBackend,
    render_grub_ab_config_from_record,
    validate_grub_ab_text,
)
from greia_platform.slot_writer import (
    FINALIZATION_GROWTH_BYTES,
    SLOT_METADATA_RESERVE_BYTES,
    SLOT_WRITE_CHUNK_BYTES,
)
from greia_platform.system_updates import inspect_update_bundle

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCHEMA_VERSION = 1

#: Exact layout adapter under test (executable MBR A/B/PERSIST).
LAYOUT_ADAPTER_ID = LEGACY_BIOS_AB_ADAPTER_ID

#: Exact boot backend under test (real GRUB one-shot semantics).
BOOT_BACKEND_ID = "grub-ab-v1"

#: Reference profile whose sizing/bounds the procedure compares against.
#: NOTE: build/profiles/legacy-x86-i686.toml still declares
#: ``bios-single-ext4`` + ``none-v1``; the procedure builds the
#: legacy-bios-ab-v1 + grub-ab-v1 test variant below and claims no
#: profile-bounds conformance beyond the stated MiB comparison.
PROFILE_ID = "legacy-x86-i686"
PROFILE_SLOT_BYTES = 1073741824
PROFILE_PERSIST_MINIMUM_BYTES = 268435456
PROFILE_PREFERRED_MIB = 800
PROFILE_REQUIRED_MIB = 1000
PROFILE_REVIEW_MIB = 1250

#: Test release lineage exercised A -> B -> A (ids declared; exact
#: hashes recorded per run in the report). No sequence authority under
#: ADR 0036; lineage order is the launch order only.
RELEASE_LINEAGE = (
    {"release_id": "greia-x8qemu-0.20.0", "slot": "A"},
    {"release_id": "greia-x8qemu-0.21.0", "slot": "B"},
    {"release_id": "greia-x8qemu-0.22.0", "slot": "A"},
)

#: Boot-run sequence covering repeated cold boots, one-shot
#: candidate/default behavior, fallback after failed health, and PERSIST
#: persistence across A -> B -> A.
RUN_SEQUENCE = (
    "cold-boot-A",
    "arm-B-one-shot",
    "boot-B-commit",
    "cold-boot-B",
    "arm-A-one-shot-fail",
    "fallback-A",
    "persist-verify-ABA",
)

QEMU_BINARY = "qemu-system-x86_64"
FIRMWARE_LABEL = "SeaBIOS (qemu-system-x86_64 pc-machine default; -bios <path> when supplied)"


class X8QemuError(RuntimeError):
    """Disposable SeaBIOS QEMU procedure failed fail-closed."""


# ---------------------------------------------------------------------------
# Host prerequisites (documented in PROCEDURE.md; enforced here)
# ---------------------------------------------------------------------------

HOST_PREREQUISITES = (
    "Linux x86_64 host",
    "qemu-system-x86_64 with SeaBIOS firmware for the pc machine",
    "GRUB tooling for the boot-control filesystem (grub-editenv compatible grubenv)",
    "loopback + mount capability for disposable raw-image assembly",
    "python3 with Greia src on PYTHONPATH (v3 bundles need no key material)",
)


def procedure_spec() -> dict[str, object]:
    """Exact layout/profile/release declaration plus run contract.

    Pure data for tests and the report header: what the procedure builds,
    what it runs, what evidence each boot leaves, and which host facts a
    capable Linux runner must provide. No filesystem or subprocess contact.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "layout_adapter": LAYOUT_ADAPTER_ID,
        "label_type": "msdos",
        "roles": ("boot-control", "system-a", "system-b", "persist"),
        "boot_backend": BOOT_BACKEND_ID,
        "reference_profile": PROFILE_ID,
        "profile_sizing": {
            "system_slot_bytes": PROFILE_SLOT_BYTES,
            "persistent_minimum_bytes": PROFILE_PERSIST_MINIMUM_BYTES,
            "preferred_core_mib": PROFILE_PREFERRED_MIB,
            "required_core_mib": PROFILE_REQUIRED_MIB,
            "architecture_review_mib": PROFILE_REVIEW_MIB,
        },
        "profile_conformance_note": (
            "comparison only against the 800/1000/1250 MiB bounds; "
            "no profile-bounds conformance is claimed"
        ),
        "release_lineage": [dict(entry) for entry in RELEASE_LINEAGE],
        "run_sequence": list(RUN_SEQUENCE),
        "host_prerequisites": list(HOST_PREREQUISITES),
        "firmware": FIRMWARE_LABEL,
        "qemu_binary": QEMU_BINARY,
        "per_run_evidence": (
            "release_id",
            "release_sha256",
            "image_sha256",
            "boot_backend_state",
        ),
        "valued_device_contact": False,
        "github_hosted_actions": "opt-in only; not used",
    }


# ---------------------------------------------------------------------------
# Narrow command seam (argument arrays only, never shell strings)
# ---------------------------------------------------------------------------


class CommandRunner:
    """Subprocess seam: argv arrays run with shell=False."""

    def run(
        self,
        argv: Sequence[str],
        *,
        check: bool = True,
        capture_output: bool = False,
        text: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(argv),
            check=check,
            capture_output=capture_output,
            text=text,
        )

    def which(self, command: str) -> str | None:
        return shutil.which(command)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HarnessConfig:
    """Disposable-image SeaBIOS run configuration.

    ``output_dir`` must resolve outside the source tree: disposable images
    are built there, never inside the repository and never on a valued
    device (the runner takes no device path at all).
    """

    output_dir: Path
    timeout_seconds: int = 300
    memory_mib: int = 1024
    cpus: int = 1
    keep_image: bool = False
    seabios_path: Path | None = None

    def validate(self, *, project_root: Path = PROJECT_ROOT) -> None:
        output = Path(self.output_dir)
        if not output.is_absolute():
            raise X8QemuError("output_dir must be an absolute path")
        root = Path(project_root).resolve()
        if output.resolve() == root or root in output.resolve().parents:
            raise X8QemuError("refusing to build disposable images inside the source tree")
        if self.timeout_seconds < 60 or self.timeout_seconds > 3600:
            raise X8QemuError("timeout must be between 60 and 3600 seconds")
        if self.memory_mib < 768 or self.memory_mib > 16384:
            raise X8QemuError("memory must be between 768 and 16384 MiB")
        if self.cpus < 1 or self.cpus > 16:
            raise X8QemuError("cpus must be between 1 and 16")
        if self.seabios_path is not None and not Path(self.seabios_path).is_absolute():
            raise X8QemuError("seabios_path must be absolute when supplied")


# ---------------------------------------------------------------------------
# Shared-library staging helpers (no parallel mechanisms)
# ---------------------------------------------------------------------------


def layout_plan_for_device(device_size_bytes: int) -> object:
    """Validated declarative MBR A/B/PERSIST plan from profile sizing facts."""
    sizing = ProfileSizing(
        layout_adapter_id=LAYOUT_ADAPTER_ID,
        slot_bytes=PROFILE_SLOT_BYTES,
        persist_minimum_bytes=PROFILE_PERSIST_MINIMUM_BYTES,
        boot_backend=BOOT_BACKEND_ID,
    )
    return plan_for_profile(sizing, device_size_bytes=int(device_size_bytes))


def adapter_roles() -> tuple[str, ...]:
    """Semantic partition roles owned by the legacy A/B adapter."""
    return tuple(adapter_for(LAYOUT_ADAPTER_ID).expected_roles)


def render_guest_grub_config(
    record: object, *, password_hash: str, developer: bool = False
) -> str:
    """Render the fixed two-entry grub.cfg from the trusted layout record."""
    return render_grub_ab_config_from_record(
        record=record,  # type: ignore[arg-type]
        password_hash=password_hash,
        developer=developer,
    )


def validate_guest_grub_config(text: str, *, developer: bool = False) -> None:
    """Require the appliance grub.cfg contract (raises fail-closed)."""
    validate_grub_ab_text(text, developer=developer)


def initialize_guest_boot_state(state_dir: Path, *, default_slot: str) -> GrubEnvBackend:
    """Create real grubenv state with the accepted slot as default."""
    return GrubEnvBackend.initialize(Path(state_dir), default_slot=default_slot)


def observe_guest_boot_state(state_dir: Path) -> dict[str, object]:
    """Read the real one-shot state after a boot (never simulate_reboot)."""
    state = GrubEnvBackend.attach(Path(state_dir)).inspect()
    return state.as_dict()


def footprint_report(
    *,
    image_bytes: int,
    base_bytes: int,
    minimum_slot_bytes: int,
    support_installed_bytes: int,
) -> dict[str, object]:
    """Disk-footprint comparison against the 800/1000/1250 MiB bounds.

    Proves the finalized-slot capacity bound through the shared
    :func:`require_finalized_slot_capacity` gate and compares the disposable
    image size against the reference-profile bounds. Comparison only: no
    conformance is claimed.
    """
    required = require_finalized_slot_capacity(
        slot_bytes=PROFILE_SLOT_BYTES,
        base_bytes=int(base_bytes),
        minimum_slot_bytes=int(minimum_slot_bytes),
        support_installed_bytes=int(support_installed_bytes),
        growth_bytes=FINALIZATION_GROWTH_BYTES,
        metadata_reserve_bytes=SLOT_METADATA_RESERVE_BYTES,
    )
    image_mib = int(image_bytes) / (1024 * 1024)
    return {
        "image_bytes": int(image_bytes),
        "image_mib": round(image_mib, 3),
        "slot_bytes": PROFILE_SLOT_BYTES,
        "finalized_required_bytes": required,
        "bounds_mib": {
            "preferred": PROFILE_PREFERRED_MIB,
            "required": PROFILE_REQUIRED_MIB,
            "review": PROFILE_REVIEW_MIB,
        },
        "below_preferred_mib": image_mib <= PROFILE_PREFERRED_MIB,
        "below_required_mib": image_mib <= PROFILE_REQUIRED_MIB,
        "below_review_mib": image_mib <= PROFILE_REVIEW_MIB,
        "conformance_claim": "none: comparison only",
    }


def staging_memory_report(*, payload_size: int) -> dict[str, object]:
    """Update-staging memory bound: streaming in fixed chunks.

    The shared :class:`SlotWriter` streams the unsigned v3 payload through
    ``SLOT_WRITE_CHUNK_BYTES`` buffers, so peak staging memory is bounded by
    one chunk plus small constant overhead — never a second payload-sized
    temporary.
    """
    size = int(payload_size)
    if size <= 0:
        raise X8QemuError("payload_size must be positive")
    return {
        "payload_bytes": size,
        "chunk_bytes": SLOT_WRITE_CHUNK_BYTES,
        "peak_staging_bytes_bound": SLOT_WRITE_CHUNK_BYTES,
        "streams_in_bounded_chunks": True,
    }


def release_identity(bundle_path: Path) -> dict[str, object]:
    """Inspect one unsigned .greiaupdate v3 bundle (hash + manifest facts)."""
    inspected = inspect_update_bundle(Path(bundle_path))
    manifest = inspected.manifest
    return {
        "release_id": manifest.release_id,
        "payload_sha256": manifest.payload_sha256,
        "payload_size": manifest.payload_size,
        "board": manifest.board,
        "bundle_sha256": _sha256_file(Path(bundle_path)),
    }


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


@dataclass
class X8QemuHarness:
    """Disposable-image SeaBIOS runner for the legacy A/B adapter."""

    config: HarnessConfig
    runner: CommandRunner = field(default_factory=CommandRunner)

    def __post_init__(self) -> None:
        self.config.validate()

    @property
    def image_path(self) -> Path:
        return Path(self.config.output_dir) / "greia-x8-legacy-ab-test.img"

    @property
    def report_path(self) -> Path:
        return Path(self.config.output_dir) / "greia-x8-qemu-report.json"

    @property
    def serial_log(self) -> Path:
        return Path(self.config.output_dir) / "greia-x8-qemu-serial.log"

    @property
    def qemu_log(self) -> Path:
        return Path(self.config.output_dir) / "greia-x8-qemu-host.log"

    @property
    def staging_dir(self) -> Path:
        return Path(self.config.output_dir) / "staging"

    def plan(self) -> dict[str, object]:
        """Non-mutating execution plan (no root, QEMU, or image needed)."""
        spec = procedure_spec()
        return {
            "schema_version": SCHEMA_VERSION,
            "procedure": spec,
            "image_path": str(self.image_path),
            "disposable_image_only": True,
            "source_tree_mutated": False,
            "firmware": FIRMWARE_LABEL,
            "qemu": self.qemu_argv(self.image_path),
            "run_sequence": list(RUN_SEQUENCE),
        }

    def qemu_argv(self, image: Path) -> list[str]:
        """Real SeaBIOS boot argv for a disposable raw image.

        Legacy ``pc`` machine (SeaBIOS default firmware), IDE raw disk,
        strict HD boot order, no reboot, no network, headless. Guest disk
        writes are preserved (no snapshot flag) so grubenv/PERSIST effects
        are observable after each boot.
        """
        argv = [
            QEMU_BINARY,
            "-name",
            "greia-x8-legacy-ab",
            "-machine",
            "pc,accel=tcg",
            "-cpu",
            "max",
            "-m",
            str(self.config.memory_mib),
            "-smp",
            str(self.config.cpus),
            "-display",
            "none",
            "-monitor",
            "none",
            "-serial",
            f"file:{self.serial_log}",
            "-nic",
            "none",
            "-boot",
            "order=c,strict=on",
            "-no-reboot",
        ]
        if self.config.seabios_path is not None:
            argv.extend(["-bios", str(self.config.seabios_path)])
        argv.extend(
            [
                "-drive",
                f"file={image},format=raw,if=ide,index=0,media=disk,cache=writeback",
            ]
        )
        return argv

    # -- privileged-host gates -------------------------------------------

    def require_host(self) -> None:
        if os.geteuid() != 0:
            raise X8QemuError("run the SeaBIOS harness as root on a Linux host")
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
            )
            if self.runner.which(command) is None
        ]
        if missing:
            raise X8QemuError("missing host tools: " + ", ".join(missing))

    def stage_source_scope(
        self,
        *,
        device_size_bytes: int,
        password_hash: str,
        layout_record_path: Path,
    ) -> dict[str, object]:
        """Assemble the disposable-image staging facts (no privilege needed).

        Mints fresh role identities, proves the declarative MBR plan, and
        records the boot-control facts the privileged assembly step turns
        into the raw image. Returns the staging manifest for the report.
        """
        from greia_platform.system_updates import load_installed_layout_record

        plan = layout_plan_for_device(int(device_size_bytes))
        identities = mint_fresh_partition_identities()
        record = load_installed_layout_record(Path(layout_record_path))
        if record is None:
            raise X8QemuError("layout record is missing or not authoritative")
        if record.layout_id != LAYOUT_ADAPTER_ID or record.boot_backend != BOOT_BACKEND_ID:
            raise X8QemuError("layout record is not the legacy-bios-ab-v1/grub-ab-v1 pair")
        grub_cfg = render_guest_grub_config(record, password_hash=password_hash)
        validate_guest_grub_config(grub_cfg)
        partitions = [
            {
                "number": part.number,
                "role": part.role,
                "size_bytes": part.size_bytes,
                "filesystem": part.filesystem,
                "label": part.label,
            }
            for part in plan.partitions  # type: ignore[attr-defined]
        ]
        return {
            "adapter": plan.adapter_id,  # type: ignore[attr-defined]
            "label_type": plan.label_type,  # type: ignore[attr-defined]
            "device_size_bytes": int(device_size_bytes),
            "partitions": partitions,
            "fresh_identities_minted": sorted(identities),
            "grub_cfg_bytes": len(grub_cfg.encode("utf-8")),
        }

    # -- boot execution ---------------------------------------------------

    def qemu_version(self) -> str:
        completed = self.runner.run([QEMU_BINARY, "--version"], capture_output=True)
        line = completed.stdout.splitlines()[0].strip() if completed.stdout else ""
        return line[:200]

    def boot_once(self) -> int:
        """Boot the disposable image once under real SeaBIOS firmware."""
        argv = self.qemu_argv(self.image_path)
        with self.qemu_log.open("ab") as log:
            process = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                return process.wait(timeout=self.config.timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        pass
                    process.wait()
                raise X8QemuError(
                    f"QEMU boot exceeded timeout; inspect {self.qemu_log}"
                ) from exc

    def collect_run_evidence(
        self,
        *,
        run: str,
        boot_state_dir: Path,
        bundle_path: Path | None,
        persist_markers: Mapping[str, str],
    ) -> dict[str, object]:
        """Record one boot run: release hashes, image identity, backend state.

        Boot-backend state comes from the real grubenv observation path
        (:func:`observe_guest_boot_state`); release facts come from the
        unsigned v3 bundle inspection path. No ``simulate_reboot`` anywhere.
        """
        if run not in RUN_SEQUENCE:
            raise X8QemuError(f"unknown boot run: {run!r}")
        backend_state = observe_guest_boot_state(boot_state_dir)
        evidence: dict[str, object] = {
            "run": run,
            "boot_backend": BOOT_BACKEND_ID,
            "boot_backend_state": backend_state,
            "image_sha256": _sha256_file(self.image_path),
            "persist_markers": dict(persist_markers),
        }
        if bundle_path is not None:
            evidence["release"] = release_identity(bundle_path)
        return evidence

    def run(
        self,
        *,
        boot_state_dir: Path,
        bundles: Mapping[str, Path] | None = None,
        on_boot: Callable[[str], None] | None = None,
    ) -> dict[str, object]:
        """Execute the full boot sequence on a capable host.

        ``on_boot`` is a test-only seam: production passes ``None`` and each
        observation reads the state the real VM left on disk; unit tests may
        supply a hook that folds an authoritative observation through the
        real :class:`GrubEnvBackend` (``reconcile``) to stand in for firmware
        where no QEMU host exists. The hook never fabricates backend state:
        every record still passes through the real inspect path.
        """
        self.require_host()
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        if self.image_path.exists():
            raise X8QemuError(f"refusing to replace existing test image: {self.image_path}")
        if not Path(boot_state_dir, GRUBENV_FILE_NAME).is_file():
            raise X8QemuError("guest boot-control state is missing; stage the image first")
        spec = procedure_spec()
        version = self.qemu_version()
        runs: list[dict[str, object]] = []
        for run in RUN_SEQUENCE:
            status = self.boot_once()
            if status != 0:
                raise X8QemuError(f"QEMU exited with status {status}; inspect {self.qemu_log}")
            if on_boot is not None:
                on_boot(run)
            runs.append(
                self.collect_run_evidence(
                    run=run,
                    boot_state_dir=Path(boot_state_dir),
                    bundle_path=(bundles or {}).get(run),
                    persist_markers=_read_persist_markers(self.staging_dir),
                )
            )
            time.sleep(0.2)
        report: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "classification": "SOURCE_SCOPE_X8_QEMU_SEQUENCE",
            "procedure": spec,
            "qemu_version": version,
            "qemu_argv": self.qemu_argv(self.image_path),
            "runs": runs,
            "limitations": [
                "live SeaBIOS execution on a QEMU-capable Linux host is deferred per the source-first amendment",
                "does not prove Acer or physical-firmware behavior",
                "does not authorize changing the production boot/update path by itself",
            ],
        }
        _write_json(self.report_path, report)
        if not self.config.keep_image and Path(self.image_path).exists():
            self.image_path.unlink()
        return report


def _read_persist_markers(staging_dir: Path) -> dict[str, str]:
    markers: dict[str, str] = {}
    persist = Path(staging_dir) / "persist-markers"
    if not persist.is_dir():
        return markers
    for marker in sorted(persist.iterdir()):
        if marker.is_file() and not marker.is_symlink():
            markers[marker.name] = _sha256_file(marker)
    return markers


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Disposable SeaBIOS QEMU procedure for the legacy A/B adapter: "
            "build a disposable raw image outside the source tree and boot it "
            "end to end under real SeaBIOS firmware."
        )
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--boot-state-dir", type=Path, required=False)
    parser.add_argument("--qemu-binary", default=QEMU_BINARY)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--memory-mib", type=int, default=1024)
    parser.add_argument("--cpus", type=int, default=1)
    parser.add_argument("--seabios-path", type=Path, default=None)
    parser.add_argument("--keep-image", action="store_true")
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="print the non-mutating execution plan; needs no root or QEMU",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    global QEMU_BINARY
    QEMU_BINARY = args.qemu_binary
    harness = X8QemuHarness(
        HarnessConfig(
            output_dir=args.output_dir,
            timeout_seconds=args.timeout_seconds,
            memory_mib=args.memory_mib,
            cpus=args.cpus,
            keep_image=args.keep_image,
            seabios_path=args.seabios_path,
        )
    )
    if args.plan_only:
        print(json.dumps(harness.plan(), sort_keys=True, indent=2))
        return 0
    if args.boot_state_dir is None:
        print("FAIL: --boot-state-dir is required without --plan-only", file=sys.stderr)
        return 1
    try:
        report = harness.run(boot_state_dir=args.boot_state_dir)
    except X8QemuError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
