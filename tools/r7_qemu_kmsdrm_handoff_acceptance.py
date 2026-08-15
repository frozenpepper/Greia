#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from r7_qemu_kmsdrm_acceptance import (
    CommandRunner,
    HarnessConfig,
    MountedRawImage,
    QemuKMSDRMAcceptanceError,
    QemuKMSDRMAcceptanceHarness,
    TEST_RUNNER,
    _read_json,
    _write_json,
    _write_text,
)


SCHEMA_VERSION = 1
GUEST_HANDOFF_ROOT = Path("/var/lib/greia-r7-qemu-kmsdrm-handoff")
GUEST_HANDOFF_SUMMARY = GUEST_HANDOFF_ROOT / "summary.json"
GUEST_HANDOFF_RESULT = Path("/var/lib/greia-kmsdrm-handoff-acceptance/result.json")
HANDOFF_SERVICE = "greia-kmsdrm-handoff-acceptance.service"


class QemuKMSDRMHandoffError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class HandoffHarnessConfig:
    source_image: Path
    output_dir: Path
    qemu_binary: str = "qemu-system-x86_64"
    timeout_seconds: int = 240
    memory_mib: int = 2048
    cpus: int = 2
    keep_test_image: bool = False

    def baseline(self) -> HarnessConfig:
        return HarnessConfig(
            source_image=self.source_image,
            output_dir=self.output_dir,
            qemu_binary=self.qemu_binary,
            timeout_seconds=self.timeout_seconds,
            memory_mib=self.memory_mib,
            cpus=self.cpus,
            keep_test_image=True,
        )


class QemuKMSDRMSerialHandoffHarness:
    """Layer R7-D serial ownership evidence over the existing active QEMU proof.

    The first boot is the existing production-image KMSDRM acceptance. Only
    after that passes do we mutate the already-disposable clone's test runner
    and boot it again for shell -> child -> shell ownership recovery. The source
    production image is never mounted or modified by this wrapper.
    """

    def __init__(
        self,
        config: HandoffHarnessConfig,
        *,
        runner: CommandRunner | None = None,
    ):
        self.config = config
        self.runner = runner or CommandRunner()
        self.baseline = QemuKMSDRMAcceptanceHarness(
            config.baseline(), runner=self.runner
        )

    @property
    def report_path(self) -> Path:
        return self.config.output_dir / "greia-r7-qemu-kmsdrm-handoff-report.json"

    @property
    def serial_log(self) -> Path:
        return self.config.output_dir / "greia-r7-qemu-handoff-serial.log"

    @property
    def qemu_log(self) -> Path:
        return self.config.output_dir / "greia-r7-qemu-handoff-host.log"

    def plan(self) -> dict[str, object]:
        baseline = self.baseline.plan()
        return {
            "schema_version": SCHEMA_VERSION,
            "source_image": baseline["source_image"],
            "test_image": baseline["test_image"],
            "source_image_mutated": False,
            "boots": [
                {
                    "purpose": "baseline-active-kmsdrm",
                    "guest_unit": baseline["guest_unit"],
                },
                {
                    "purpose": "serial-shell-child-shell-handoff",
                    "guest_unit": baseline["guest_unit"],
                    "service": HANDOFF_SERVICE,
                    "required_evidence": [
                        str(GUEST_HANDOFF_SUMMARY),
                        str(GUEST_HANDOFF_RESULT),
                    ],
                },
            ],
            "production_launcher_changed": False,
        }

    def run(self) -> dict[str, object]:
        baseline_report = self.baseline.run()
        success = False
        try:
            self._prepare_second_boot()
            qemu_status = self._boot_second_qemu()
            if qemu_status != 0:
                raise QemuKMSDRMHandoffError(
                    f"serial handoff QEMU boot exited with status {qemu_status}"
                )
            summary, handoff = self._read_handoff_evidence()
            validate_handoff_evidence(summary, handoff)

            report = {
                "schema_version": SCHEMA_VERSION,
                "ok": True,
                "classification": "SERIAL_QEMU_KMSDRM_HANDOFF_PASS",
                "source_image": baseline_report["source_image"],
                "source_image_sha256": baseline_report["source_image_sha256"],
                "test_image": str(self.baseline.test_image.resolve()),
                "baseline": baseline_report,
                "handoff_summary": summary,
                "handoff": handoff,
                "limitations": [
                    "proves serial KMSDRM ownership release/reacquisition in a QEMU virtio GPU guest",
                    "proves shell reacquisition after both clean and abrupt child-process exit",
                    "does not prove Activity sandbox input routing, Web runtime surfaces, or physical Acer/Pi scanout",
                    "does not authorize serial DRM ownership as the production Greia session design",
                ],
            }
            _write_json(self.report_path, report)
            success = True
            return report
        finally:
            if success and not self.config.keep_test_image:
                self.baseline.test_image.unlink(missing_ok=True)

    def _prepare_second_boot(self) -> None:
        mountpoint = self.config.output_dir / "mounted-handoff-image"
        with MountedRawImage(
            self.baseline.test_image,
            mountpoint,
            read_only=False,
            runner=self.runner,
        ) as root:
            service = root / "etc/systemd/system" / HANDOFF_SERVICE
            if not service.is_file():
                raise QemuKMSDRMHandoffError(
                    f"finished image is missing serial handoff service: {HANDOFF_SERVICE}"
                )
            runner_path = root / TEST_RUNNER.lstrip("/")
            _write_text(runner_path, handoff_guest_runner_text(), mode=0o755)
            evidence = root / GUEST_HANDOFF_ROOT.relative_to("/")
            evidence.mkdir(parents=True, exist_ok=True)
            os.chmod(evidence, 0o755)

    def _boot_second_qemu(self) -> int:
        argv = list(self.baseline.qemu_argv(self.baseline.test_image))
        try:
            serial_index = argv.index("-serial") + 1
        except ValueError as exc:  # pragma: no cover - baseline contract regression
            raise QemuKMSDRMHandoffError(
                "baseline QEMU argv has no serial output"
            ) from exc
        argv[serial_index] = f"file:{self.serial_log}"

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
                raise QemuKMSDRMHandoffError(
                    f"serial handoff QEMU boot exceeded timeout; inspect {self.qemu_log}"
                ) from exc

    def _read_handoff_evidence(
        self,
    ) -> tuple[Mapping[str, object], Mapping[str, object]]:
        mountpoint = self.config.output_dir / "mounted-handoff-evidence"
        with MountedRawImage(
            self.baseline.test_image,
            mountpoint,
            read_only=True,
            runner=self.runner,
        ) as root:
            return (
                _read_json(root / GUEST_HANDOFF_SUMMARY.relative_to("/")),
                _read_json(root / GUEST_HANDOFF_RESULT.relative_to("/")),
            )


def handoff_guest_runner_text() -> str:
    return r'''#!/bin/sh
set -u

evidence=/var/lib/greia-r7-qemu-kmsdrm-handoff
summary="$evidence/summary.json"
handoff=/var/lib/greia-kmsdrm-handoff-acceptance/result.json
service=greia-kmsdrm-handoff-acceptance.service
phase=boot
status=1
service_status=not-run
mkdir -p "$evidence"

power_off() {
  trap - EXIT HUP INT TERM
  sync
  systemctl poweroff --no-block >/dev/null 2>&1 || /sbin/poweroff -f >/dev/null 2>&1 || true
}

write_summary() {
  active_vt="$(cat /sys/class/tty/tty0/active 2>/dev/null || true)"
  GREIA_R7_PHASE="$phase" GREIA_R7_STATUS="$status" GREIA_R7_SERVICE_STATUS="$service_status" GREIA_R7_ACTIVE_VT="$active_vt" \
    PYTHONPATH=/opt/greia-os/src python3 - "$summary" <<'PY'
import json
import os
import sys
from pathlib import Path

payload = {
    "schema_version": 1,
    "ok": os.environ.get("GREIA_R7_STATUS") == "0",
    "phase": os.environ.get("GREIA_R7_PHASE", "unknown")[:80],
    "service_status": os.environ.get("GREIA_R7_SERVICE_STATUS", "unknown")[:40],
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

phase=serial-handoff
rm -f -- "$handoff"
systemctl reset-failed "$service" >/dev/null 2>&1 || true
set +e
systemctl start "$service"
service_status="$?"
set -e
[ "$service_status" -eq 0 ] || exit 1
[ -r "$handoff" ] || exit 1

python3 - "$handoff" <<'PY' || exit 1
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if payload.get("schema_version") != 1 or payload.get("ok") is not True:
    raise SystemExit("serial handoff report did not pass")
if payload.get("requested_video_driver") != "kmsdrm":
    raise SystemExit("serial handoff did not request kmsdrm")
recovery = payload.get("recovery", {})
if recovery.get("clean_child_reacquired") is not True:
    raise SystemExit("shell did not reacquire after clean child")
if recovery.get("crash_child_reacquired") is not True:
    raise SystemExit("shell did not reacquire after crashed child")
for key in ("shell_initial", "shell_after_clean", "shell_after_crash"):
    if payload.get(key, {}).get("actual_video_driver") != "kmsdrm":
        raise SystemExit(f"{key} did not use kmsdrm")
if payload.get("clean_child", {}).get("return_code") != 0:
    raise SystemExit("clean child did not exit normally")
if payload.get("clean_child", {}).get("result", {}).get("actual_video_driver") != "kmsdrm":
    raise SystemExit("clean child did not acquire kmsdrm")
if payload.get("crash_child", {}).get("return_code") != 23:
    raise SystemExit("crash child did not use intentional abrupt exit")
crash = payload.get("crash_child", {}).get("result", {})
if crash.get("actual_video_driver") != "kmsdrm" or crash.get("intentional_abrupt_exit") is not True:
    raise SystemExit("crash child did not prove abrupt kmsdrm ownership")
PY

phase=complete
status=0
exit 0
'''


def validate_handoff_evidence(
    summary: Mapping[str, object], handoff: Mapping[str, object]
) -> None:
    if summary.get("schema_version") != 1 or summary.get("ok") is not True:
        raise QemuKMSDRMHandoffError("serial handoff guest summary did not pass")
    if summary.get("phase") != "complete":
        raise QemuKMSDRMHandoffError("serial handoff guest did not reach complete phase")
    if summary.get("service_status") != "0":
        raise QemuKMSDRMHandoffError("serial handoff service did not exit successfully")
    if summary.get("active_vt") != "tty1":
        raise QemuKMSDRMHandoffError("serial handoff did not run on tty1")
    if summary.get("launcher_masked") is not True:
        raise QemuKMSDRMHandoffError("normal launcher was not masked in disposable clone")

    if handoff.get("schema_version") != 1 or handoff.get("ok") is not True:
        raise QemuKMSDRMHandoffError("serial KMSDRM handoff report did not pass")
    if handoff.get("requested_video_driver") != "kmsdrm":
        raise QemuKMSDRMHandoffError("serial handoff did not request kmsdrm")

    recovery = handoff.get("recovery")
    if not isinstance(recovery, Mapping):
        raise QemuKMSDRMHandoffError("serial handoff has no recovery evidence")
    if recovery.get("clean_child_reacquired") is not True:
        raise QemuKMSDRMHandoffError("shell did not reacquire after clean child")
    if recovery.get("crash_child_reacquired") is not True:
        raise QemuKMSDRMHandoffError("shell did not reacquire after crashed child")

    shell_hashes: set[str] = set()
    for key in ("shell_initial", "shell_after_clean", "shell_after_crash"):
        phase = handoff.get(key)
        if not isinstance(phase, Mapping):
            raise QemuKMSDRMHandoffError(f"serial handoff is missing {key}")
        if phase.get("actual_video_driver") != "kmsdrm":
            raise QemuKMSDRMHandoffError(f"{key} did not use kmsdrm")
        _validate_surface(phase.get("surface"), key)
        digest = phase.get("frame_sha256")
        _validate_digest(digest, key)
        shell_hashes.add(str(digest))
    if len(shell_hashes) < 2:
        raise QemuKMSDRMHandoffError("shell phases do not contain distinct frame hashes")

    clean = handoff.get("clean_child")
    if not isinstance(clean, Mapping) or clean.get("return_code") != 0:
        raise QemuKMSDRMHandoffError("clean child handoff evidence is invalid")
    clean_result = clean.get("result")
    if (
        not isinstance(clean_result, Mapping)
        or clean_result.get("ok") is not True
        or clean_result.get("actual_video_driver") != "kmsdrm"
    ):
        raise QemuKMSDRMHandoffError("clean child did not prove kmsdrm acquisition")

    crash = handoff.get("crash_child")
    if not isinstance(crash, Mapping) or crash.get("return_code") != 23:
        raise QemuKMSDRMHandoffError("crash child handoff evidence is invalid")
    crash_result = crash.get("result")
    if (
        not isinstance(crash_result, Mapping)
        or crash_result.get("ok") is not True
        or crash_result.get("actual_video_driver") != "kmsdrm"
        or crash_result.get("intentional_abrupt_exit") is not True
    ):
        raise QemuKMSDRMHandoffError("crash child did not prove abrupt kmsdrm ownership")
    _validate_surface(crash_result.get("surface"), "crash_child")
    _validate_digest(crash_result.get("frame_sha256"), "crash_child")


def _validate_surface(value: object, label: str) -> None:
    if not isinstance(value, Mapping):
        raise QemuKMSDRMHandoffError(f"{label} has no surface metadata")
    for key in ("width", "height"):
        dimension = value.get(key)
        if (
            not isinstance(dimension, int)
            or isinstance(dimension, bool)
            or dimension <= 0
            or dimension > 32_768
        ):
            raise QemuKMSDRMHandoffError(f"{label} has invalid surface dimensions")


def _validate_digest(value: object, label: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise QemuKMSDRMHandoffError(f"{label} has malformed frame hash")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run baseline active KMSDRM evidence and then serial shell/child "
            "ownership recovery in the same disposable production-image clone."
        )
    )
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--qemu-binary", default="qemu-system-x86_64")
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--memory-mib", type=int, default=2048)
    parser.add_argument("--cpus", type=int, default=2)
    parser.add_argument("--keep-test-image", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    harness = QemuKMSDRMSerialHandoffHarness(
        HandoffHarnessConfig(
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
    except (QemuKMSDRMAcceptanceError, QemuKMSDRMHandoffError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
