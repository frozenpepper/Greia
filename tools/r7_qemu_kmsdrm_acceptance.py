#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


SCHEMA_VERSION = 1
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAFE_CLEANUP = PROJECT_ROOT / "build" / "lib" / "safe-cleanup.sh"
GUEST_EVIDENCE_DIR = Path("/var/lib/greia-r7-qemu-kmsdrm")
GUEST_SUMMARY = GUEST_EVIDENCE_DIR / "summary.json"
GUEST_PASSIVE = GUEST_EVIDENCE_DIR / "passive-direct-graphics.json"
GUEST_ACTIVE = Path("/var/lib/greia-kmsdrm-acceptance/result.json")
TEST_UNIT = "greia-r7-qemu-kmsdrm.service"
TEST_RUNNER = "/usr/local/sbin/greia-r7-qemu-kmsdrm-boot-test"


class QemuKMSDRMAcceptanceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class HarnessConfig:
    source_image: Path
    output_dir: Path
    qemu_binary: str = "qemu-system-x86_64"
    timeout_seconds: int = 180
    memory_mib: int = 2048
    cpus: int = 2
    keep_test_image: bool = False

    def validate(self) -> None:
        if self.timeout_seconds < 30 or self.timeout_seconds > 1800:
            raise QemuKMSDRMAcceptanceError("timeout must be between 30 and 1800 seconds")
        if self.memory_mib < 768 or self.memory_mib > 16384:
            raise QemuKMSDRMAcceptanceError("memory must be between 768 and 16384 MiB")
        if self.cpus < 1 or self.cpus > 16:
            raise QemuKMSDRMAcceptanceError("cpus must be between 1 and 16")


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    summary: Mapping[str, object]
    passive: Mapping[str, object]
    active: Mapping[str, object]


class CommandRunner:
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


class MountedRawImage(AbstractContextManager[Path]):
    """Mount partition 1 of a raw image and detach it through Greia cleanup policy."""

    def __init__(
        self,
        image: Path,
        mountpoint: Path,
        *,
        read_only: bool,
        runner: CommandRunner,
    ) -> None:
        self.image = image
        self.mountpoint = mountpoint
        self.read_only = read_only
        self.runner = runner
        self.loop_device: str | None = None
        self.mounted = False

    def __enter__(self) -> Path:
        args = ["losetup", "--find", "--show", "--partscan"]
        if self.read_only:
            args.append("--read-only")
        args.append(str(self.image))
        completed = self.runner.run(args, capture_output=True)
        loop = completed.stdout.strip()
        if not loop.startswith("/dev/loop"):
            raise QemuKMSDRMAcceptanceError(f"unexpected loop device: {loop!r}")
        self.loop_device = loop
        try:
            partition = Path(loop + "p1")
            for _ in range(50):
                if partition.exists():
                    break
                time.sleep(0.1)
            if not partition.exists():
                raise QemuKMSDRMAcceptanceError(f"partition did not appear: {partition}")

            self.mountpoint.mkdir(parents=True, exist_ok=True)
            mount_args = ["mount"]
            if self.read_only:
                mount_args.extend(["-o", "ro,noload"])
            mount_args.extend([str(partition), str(self.mountpoint)])
            self.runner.run(mount_args)
            self.mounted = True
            return self.mountpoint
        except Exception:
            cleanup_error = self._cleanup()
            if cleanup_error is not None:
                raise QemuKMSDRMAcceptanceError(
                    "raw-image setup failed and cleanup was incomplete"
                ) from cleanup_error
            raise

    def __exit__(self, exc_type, exc, traceback) -> bool:
        cleanup_error = self._cleanup()
        if cleanup_error is not None:
            detail = (
                "raw-image cleanup failed while handling another failure"
                if exc is not None
                else "raw-image cleanup failed"
            )
            raise QemuKMSDRMAcceptanceError(detail) from cleanup_error
        return False

    def _cleanup(self) -> Exception | None:
        cleanup_error: Exception | None = None
        if self.mounted:
            try:
                self.runner.run(["umount", str(self.mountpoint)])
                self.mounted = False
            except Exception as error:  # pragma: no cover - privileged failure path
                cleanup_error = error
        if self.loop_device:
            command = (
                f"source {shlex.quote(str(SAFE_CLEANUP))}; "
                f"safe_detach_loop {shlex.quote(self.loop_device)}"
            )
            try:
                self.runner.run(["bash", "-c", command])
                self.loop_device = None
            except Exception as error:  # pragma: no cover - privileged failure path
                cleanup_error = cleanup_error or error
        return cleanup_error


class QemuKMSDRMAcceptanceHarness:
    """Run R7 KMSDRM acceptance in a disposable clone of a production image.

    The source image is never mounted or booted. Only its clone is mutated.
    Production X/session configuration is therefore not changed by this tool.
    """

    def __init__(self, config: HarnessConfig, *, runner: CommandRunner | None = None) -> None:
        config.validate()
        self.config = config
        self.runner = runner or CommandRunner()

    @property
    def test_image(self) -> Path:
        return self.config.output_dir / "greia-r7-qemu-kmsdrm-test.img"

    @property
    def report_path(self) -> Path:
        return self.config.output_dir / "greia-r7-qemu-kmsdrm-report.json"

    @property
    def serial_log(self) -> Path:
        return self.config.output_dir / "greia-r7-qemu-serial.log"

    @property
    def qemu_log(self) -> Path:
        return self.config.output_dir / "greia-r7-qemu-host.log"

    def plan(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "source_image": str(self.config.source_image.resolve()),
            "test_image": str(self.test_image.resolve()),
            "source_image_mutated": False,
            "normal_launcher_masked_only_in_clone": True,
            "guest_unit": TEST_UNIT,
            "guest_acceptance_service": "greia-kmsdrm-acceptance.service",
            "qemu": self.qemu_argv(self.test_image),
            "required_evidence": [str(GUEST_SUMMARY), str(GUEST_PASSIVE), str(GUEST_ACTIVE)],
        }

    def run(self) -> dict[str, object]:
        self._require_privileged_host()
        self._require_tools()
        source = self.config.source_image.resolve()
        if not source.is_file() or source.stat().st_size == 0:
            raise QemuKMSDRMAcceptanceError(f"source image is missing or empty: {source}")
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        if self.test_image.exists():
            raise QemuKMSDRMAcceptanceError(
                f"refusing to replace existing test image: {self.test_image}"
            )
        if source == self.test_image.resolve():
            raise QemuKMSDRMAcceptanceError("source and test images must be different paths")

        source_sha256 = _sha256_file(source)
        self._clone_source_image(source)
        success = False
        try:
            self._mutate_disposable_image()
            qemu_version = self._qemu_version()
            qemu_status = self._boot_qemu()
            if qemu_status != 0:
                raise QemuKMSDRMAcceptanceError(
                    f"QEMU exited with status {qemu_status}; inspect {self.qemu_log}"
                )
            evidence = self._read_guest_evidence()
            validate_evidence(evidence)
            report = {
                "schema_version": SCHEMA_VERSION,
                "ok": True,
                "classification": "ACTIVE_QEMU_KMSDRM_PASS",
                "source_image": str(source),
                "source_image_sha256": source_sha256,
                "test_image": str(self.test_image.resolve()),
                "qemu_version": qemu_version,
                "qemu_argv": self.qemu_argv(self.test_image),
                "summary": evidence.summary,
                "passive": evidence.passive,
                "active": evidence.active,
                "limitations": [
                    "proves active SDL/Pygame KMSDRM acquisition against a QEMU virtio GPU",
                    "does not prove Acer or Raspberry Pi physical scanout/input/session behavior",
                    "does not authorize changing the production Greia boot/session path by itself",
                ],
            }
            _write_json(self.report_path, report)
            success = True
            return report
        finally:
            if success and not self.config.keep_test_image:
                self.test_image.unlink(missing_ok=True)

    def qemu_argv(self, image: Path) -> list[str]:
        return [
            self.config.qemu_binary,
            "-name",
            "greia-r7-kmsdrm-acceptance",
            "-machine",
            "pc,accel=tcg",
            "-cpu",
            "max",
            "-m",
            str(self.config.memory_mib),
            "-smp",
            str(self.config.cpus),
            "-vga",
            "none",
            "-device",
            "virtio-vga",
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
            "-drive",
            f"file={image},format=raw,if=ide,index=0,media=disk,cache=writeback",
        ]

    def _require_privileged_host(self) -> None:
        if os.geteuid() != 0:
            raise QemuKMSDRMAcceptanceError("run the active QEMU harness as root")

    def _require_tools(self) -> None:
        if not SAFE_CLEANUP.is_file():
            raise QemuKMSDRMAcceptanceError(f"missing Greia cleanup helper: {SAFE_CLEANUP}")
        required = (
            self.config.qemu_binary,
            "cp",
            "losetup",
            "mount",
            "umount",
            "bash",
            "partx",
            "blockdev",
            "udevadm",
        )
        missing = [command for command in required if shutil.which(command) is None]
        if missing:
            raise QemuKMSDRMAcceptanceError("missing host tools: " + ", ".join(missing))

    def _clone_source_image(self, source: Path) -> None:
        self.runner.run(
            [
                "cp",
                "--reflink=auto",
                "--sparse=always",
                "--",
                str(source),
                str(self.test_image),
            ]
        )
        if not self.test_image.is_file() or self.test_image.stat().st_size != source.stat().st_size:
            raise QemuKMSDRMAcceptanceError("disposable image clone is incomplete")

    def _mutate_disposable_image(self) -> None:
        mountpoint = self.config.output_dir / "mounted-test-image"
        with MountedRawImage(self.test_image, mountpoint, read_only=False, runner=self.runner) as root:
            self._validate_guest_contract(root)
            _write_text(root / TEST_RUNNER.lstrip("/"), guest_runner_text(), mode=0o755)
            unit_path = root / "etc/systemd/system" / TEST_UNIT
            _write_text(unit_path, guest_unit_text(), mode=0o644)

            launcher = root / "etc/systemd/system/greia-launcher.service"
            if launcher.exists() or launcher.is_symlink():
                launcher.unlink()
            launcher.symlink_to("/dev/null")

            wants = root / "etc/systemd/system/multi-user.target.wants"
            wants.mkdir(parents=True, exist_ok=True)
            enabled = wants / TEST_UNIT
            if enabled.exists() or enabled.is_symlink():
                enabled.unlink()
            enabled.symlink_to(f"../{TEST_UNIT}")

            evidence = root / GUEST_EVIDENCE_DIR.relative_to("/")
            evidence.mkdir(parents=True, exist_ok=True)
            os.chmod(evidence, 0o755)

    def _validate_guest_contract(self, root: Path) -> None:
        required = (
            "opt/greia-os/src/greia_platform/kmsdrm_acceptance.py",
            "opt/greia-os/src/greia_platform/direct_graphics_probe.py",
            "etc/systemd/system/greia-kmsdrm-acceptance.service",
            "etc/systemd/system/greia-first-boot.service",
            "usr/bin/python3",
            "usr/bin/chvt",
        )
        missing = [relative for relative in required if not (root / relative).exists()]
        if missing:
            raise QemuKMSDRMAcceptanceError(
                "image does not satisfy R7 guest contract: " + ", ".join(missing)
            )
        acceptance = (root / "etc/systemd/system/greia-kmsdrm-acceptance.service").read_text(
            encoding="utf-8"
        )
        for required_text in (
            "Environment=SDL_VIDEODRIVER=kmsdrm",
            "UnsetEnvironment=DISPLAY WAYLAND_DISPLAY XAUTHORITY",
            "TTYPath=/dev/tty1",
            "--acknowledge-display-takeover",
        ):
            if required_text not in acceptance:
                raise QemuKMSDRMAcceptanceError(
                    f"installed acceptance service is missing contract: {required_text}"
                )

    def _qemu_version(self) -> str:
        completed = self.runner.run(
            [self.config.qemu_binary, "--version"], capture_output=True
        )
        line = completed.stdout.splitlines()[0].strip() if completed.stdout else ""
        return line[:200]

    def _boot_qemu(self) -> int:
        argv = self.qemu_argv(self.test_image)
        with self.qemu_log.open("wb") as log:
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
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                raise QemuKMSDRMAcceptanceError(
                    f"QEMU acceptance exceeded timeout; inspect {self.qemu_log}"
                ) from exc

    def _read_guest_evidence(self) -> EvidenceBundle:
        mountpoint = self.config.output_dir / "mounted-evidence-image"
        with MountedRawImage(self.test_image, mountpoint, read_only=True, runner=self.runner) as root:
            summary = _read_json(root / GUEST_SUMMARY.relative_to("/"))
            passive = _read_json(root / GUEST_PASSIVE.relative_to("/"))
            active = _read_json(root / GUEST_ACTIVE.relative_to("/"))
            return EvidenceBundle(summary=summary, passive=passive, active=active)


def guest_unit_text() -> str:
    return """[Unit]\nDescription=Greia R7 disposable QEMU KMSDRM boot acceptance\nAfter=greia-first-boot.service systemd-logind.service systemd-user-sessions.service\nRequires=greia-first-boot.service\nConflicts=greia-launcher.service\n\n[Service]\nType=oneshot\nExecStart=/usr/local/sbin/greia-r7-qemu-kmsdrm-boot-test\nTimeoutStartSec=60\nStandardOutput=journal\nStandardError=journal\n\n[Install]\nWantedBy=multi-user.target\n"""


def guest_runner_text() -> str:
    return r'''#!/bin/sh
set -u

evidence=/var/lib/greia-r7-qemu-kmsdrm
passive="$evidence/passive-direct-graphics.json"
summary="$evidence/summary.json"
active=/var/lib/greia-kmsdrm-acceptance/result.json
acceptance=greia-kmsdrm-acceptance.service
phase=boot
status=1
acceptance_status=not-run
mkdir -p "$evidence"

power_off() {
  trap - EXIT HUP INT TERM
  sync
  systemctl poweroff --no-block >/dev/null 2>&1 || /sbin/poweroff -f >/dev/null 2>&1 || true
}

write_summary() {
  active_vt="$(cat /sys/class/tty/tty0/active 2>/dev/null || true)"
  GREIA_R7_PHASE="$phase" GREIA_R7_STATUS="$status" GREIA_R7_ACCEPTANCE_STATUS="$acceptance_status" GREIA_R7_ACTIVE_VT="$active_vt" \
    PYTHONPATH=/opt/greia-os/src python3 - "$summary" <<'PY'
import json
import os
import sys
from pathlib import Path

payload = {
    "schema_version": 1,
    "ok": os.environ.get("GREIA_R7_STATUS") == "0",
    "phase": os.environ.get("GREIA_R7_PHASE", "unknown")[:80],
    "acceptance_status": os.environ.get("GREIA_R7_ACCEPTANCE_STATUS", "unknown")[:40],
    "active_vt": os.environ.get("GREIA_R7_ACTIVE_VT", "")[:40],
    "launcher_masked": Path("/etc/systemd/system/greia-launcher.service").is_symlink()
        and Path("/etc/systemd/system/greia-launcher.service").resolve() == Path("/dev/null"),
}
target = Path(sys.argv[1])
temporary = target.with_suffix(".tmp")
temporary.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
temporary.replace(target)
PY
}

finish() {
  set +e
  write_summary || true
  power_off
}
trap finish EXIT HUP INT TERM

phase=activate-vt
chvt 1 || exit 1
vt_ready=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  [ "$(cat /sys/class/tty/tty0/active 2>/dev/null || true)" = tty1 ] && { vt_ready=1; break; }
  sleep 0.1
done
[ "$vt_ready" -eq 1 ] || exit 1

phase=reject-x
for f in /proc/[0-9]*/comm; do
  [ -r "$f" ] || continue
  IFS= read -r name < "$f" || continue
  case "$name" in xinit|Xorg|X) exit 1 ;; esac
done

phase=passive-probe
PYGAME_HIDE_SUPPORT_PROMPT=1 PYTHONPATH=/opt/greia-os/src PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  python3 -m greia_platform.direct_graphics_probe > "$passive" || exit 1
python3 - "$passive" <<'PY' || exit 1
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if payload.get("schema_version") != 1 or payload.get("passive") is not True:
    raise SystemExit("invalid passive probe schema")
if payload.get("sdl", {}).get("kmsdrm_compiled") is not True:
    raise SystemExit("installed SDL does not enumerate kmsdrm")
if not payload.get("drm", {}).get("card_nodes"):
    raise SystemExit("QEMU guest exposes no DRM card node")
if payload.get("assessment", {}).get("kmsdrm_prerequisites_visible") is not True:
    raise SystemExit("KMSDRM prerequisites are not visible in QEMU guest")
PY

phase=active-acceptance
rm -f -- "$active"
systemctl reset-failed "$acceptance" >/dev/null 2>&1 || true
set +e
systemctl start "$acceptance"
acceptance_status="$?"
set -e
[ "$acceptance_status" -eq 0 ] || exit 1
[ -r "$active" ] || exit 1
python3 - "$active" <<'PY' || exit 1
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if payload.get("schema_version") != 1:
    raise SystemExit("invalid active result schema")
if payload.get("ok") is not True:
    raise SystemExit("active KMSDRM acceptance reported failure")
if payload.get("requested_video_driver") != "kmsdrm" or payload.get("actual_video_driver") != "kmsdrm":
    raise SystemExit("SDL did not actively select kmsdrm")
if payload.get("frame_count", 0) < 3 or len(payload.get("frame_sha256", [])) < 3:
    raise SystemExit("active acceptance did not persist rendered frame evidence")
PY

phase=complete
status=0
exit 0
'''


def validate_evidence(bundle: EvidenceBundle) -> None:
    summary = bundle.summary
    passive = bundle.passive
    active = bundle.active
    if summary.get("schema_version") != 1 or summary.get("ok") is not True:
        raise QemuKMSDRMAcceptanceError("guest QEMU summary did not pass")
    if summary.get("phase") != "complete":
        raise QemuKMSDRMAcceptanceError("guest QEMU harness did not reach complete phase")
    if summary.get("active_vt") != "tty1":
        raise QemuKMSDRMAcceptanceError("guest acceptance did not run on tty1")
    if summary.get("launcher_masked") is not True:
        raise QemuKMSDRMAcceptanceError("guest normal launcher was not masked in clone")
    if summary.get("acceptance_status") != "0":
        raise QemuKMSDRMAcceptanceError("guest acceptance service did not exit successfully")

    if passive.get("schema_version") != 1 or passive.get("passive") is not True:
        raise QemuKMSDRMAcceptanceError("invalid passive direct-graphics evidence")
    sdl = passive.get("sdl")
    if not isinstance(sdl, Mapping) or sdl.get("kmsdrm_compiled") is not True:
        raise QemuKMSDRMAcceptanceError("guest SDL does not enumerate kmsdrm")
    drm = passive.get("drm")
    if not isinstance(drm, Mapping) or not drm.get("card_nodes"):
        raise QemuKMSDRMAcceptanceError("guest exposes no DRM card node")
    assessment = passive.get("assessment")
    if not isinstance(assessment, Mapping) or assessment.get("kmsdrm_prerequisites_visible") is not True:
        raise QemuKMSDRMAcceptanceError("guest KMSDRM prerequisites are incomplete")

    if active.get("schema_version") != 1 or active.get("ok") is not True:
        raise QemuKMSDRMAcceptanceError("active KMSDRM result did not pass")
    if active.get("requested_video_driver") != "kmsdrm" or active.get("actual_video_driver") != "kmsdrm":
        raise QemuKMSDRMAcceptanceError("active SDL driver is not kmsdrm")
    frame_count = active.get("frame_count")
    hashes = active.get("frame_sha256")
    if not isinstance(frame_count, int) or isinstance(frame_count, bool) or frame_count < 3:
        raise QemuKMSDRMAcceptanceError("active result has insufficient frame count")
    if not isinstance(hashes, list) or len(hashes) != frame_count or len(set(hashes)) < 2:
        raise QemuKMSDRMAcceptanceError("active result has invalid rendered-frame hashes")
    for digest in hashes:
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise QemuKMSDRMAcceptanceError("active result has malformed frame hash")
    surface = active.get("surface")
    if not isinstance(surface, Mapping):
        raise QemuKMSDRMAcceptanceError("active result has no surface metadata")
    for key in ("width", "height"):
        value = surface.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise QemuKMSDRMAcceptanceError("active result has invalid surface dimensions")


def _read_json(path: Path) -> Mapping[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QemuKMSDRMAcceptanceError(f"missing or invalid guest evidence: {path}") from exc
    if not isinstance(payload, dict):
        raise QemuKMSDRMAcceptanceError(f"guest evidence is not an object: {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _write_text(path: Path, text: str, *, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.chmod(temporary, mode)
    os.replace(temporary, path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Clone a finished Greia amd64 raw image and run the R7 active KMSDRM "
            "acceptance primitive against a headless QEMU virtio GPU."
        )
    )
    parser.add_argument("--image", type=Path, required=True, help="finished production raw image")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--qemu-binary", default="qemu-system-x86_64")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--memory-mib", type=int, default=2048)
    parser.add_argument("--cpus", type=int, default=2)
    parser.add_argument("--keep-test-image", action="store_true")
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="print the non-mutating execution plan; does not require root or QEMU",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    harness = QemuKMSDRMAcceptanceHarness(
        HarnessConfig(
            source_image=args.image,
            output_dir=args.output_dir,
            qemu_binary=args.qemu_binary,
            timeout_seconds=args.timeout_seconds,
            memory_mib=args.memory_mib,
            cpus=args.cpus,
            keep_test_image=args.keep_test_image,
        )
    )
    if args.plan_only:
        print(json.dumps(harness.plan(), sort_keys=True, indent=2))
        return 0
    try:
        report = harness.run()
    except QemuKMSDRMAcceptanceError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
