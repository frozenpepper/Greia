#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

try:  # Direct script execution.
    from r7_compositor_package_probe import (
        CANDIDATES,
        CompositorPackageProbe,
        ProbeConfig as PackageProbeConfig,
    )
    from r7_qemu_kmsdrm_acceptance import CommandRunner, MountedRawImage
    from r7_qemu_kmsdrm_handoff_acceptance import (
        HandoffHarnessConfig,
        QemuKMSDRMSerialHandoffHarness,
    )
except ImportError:  # Import as tools.r7_local_evidence in tests.
    from .r7_compositor_package_probe import (
        CANDIDATES,
        CompositorPackageProbe,
        ProbeConfig as PackageProbeConfig,
    )
    from .r7_qemu_kmsdrm_acceptance import CommandRunner, MountedRawImage
    from .r7_qemu_kmsdrm_handoff_acceptance import (
        HandoffHarnessConfig,
        QemuKMSDRMSerialHandoffHarness,
    )


SCHEMA_VERSION = 1
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = PROJECT_ROOT / "build" / "build-image.sh"
DEFAULT_BRANCH = "r7-direct-graphics"
DEFAULT_PROFILE = "modern-amd64"

_BASE_HOST_COMMANDS = (
    "git",
    "make",
    "python3",
    "debootstrap",
    "parted",
    "partx",
    "blockdev",
    "losetup",
    "mkfs.ext4",
    "blkid",
    "grub-install",
    "grub-script-check",
    "grub-mkpasswd-pbkdf2",
    "chroot",
    "mount",
    "umount",
    "mountpoint",
    "findmnt",
    "udevadm",
    "rsync",
)


class LocalEvidenceError(RuntimeError):
    """Raised when local R7 evidence cannot preserve its safety contract."""


@dataclass(frozen=True, slots=True)
class LocalEvidenceConfig:
    run_root: Path
    repository_root: Path = PROJECT_ROOT
    required_branch: str = DEFAULT_BRANCH
    profile: str = DEFAULT_PROFILE
    qemu_binary: str = "qemu-system-x86_64"
    qemu_timeout_seconds: int = 240
    keep_qemu_image: bool = False

    def validate(self) -> None:
        repo = self.repository_root.resolve()
        run_root = self.run_root.resolve()
        if not repo.is_dir():
            raise LocalEvidenceError(f"repository root is missing: {repo}")
        if run_root == repo or run_root.is_relative_to(repo):
            raise LocalEvidenceError("run root must be outside the repository")
        if self.qemu_timeout_seconds < 30 or self.qemu_timeout_seconds > 1800:
            raise LocalEvidenceError("QEMU timeout must be between 30 and 1800 seconds")
        if not self.required_branch or any(ch.isspace() for ch in self.required_branch):
            raise LocalEvidenceError("required branch must be a bounded non-whitespace name")


class LocalR7EvidenceOrchestrator:
    """Execute the existing R7 evidence implementations on a controlled Linux host.

    This class is deliberately an orchestrator, not another acceptance implementation.
    It calls the production image builder, passive in-image probe, compositor package
    probe, and active+serial QEMU harness already owned by R7. It never installs host
    packages, never mutates the source production image, and never commits evidence.
    """

    def __init__(
        self,
        config: LocalEvidenceConfig,
        *,
        runner: CommandRunner | None = None,
    ) -> None:
        config.validate()
        self.config = config
        self.runner = runner or CommandRunner()

    @property
    def run_root(self) -> Path:
        return self.config.run_root.resolve()

    @property
    def image_dir(self) -> Path:
        return self.run_root / "image"

    @property
    def package_dir(self) -> Path:
        return self.run_root / "packages"

    @property
    def qemu_dir(self) -> Path:
        return self.run_root / "qemu"

    @property
    def evidence_dir(self) -> Path:
        return self.run_root / "evidence"

    @property
    def log_dir(self) -> Path:
        return self.run_root / "logs"

    @property
    def mount_dir(self) -> Path:
        return self.run_root / "mount"

    @property
    def image_path(self) -> Path:
        return self.image_dir / f"greia-os-{self.config.profile}.img"

    def plan(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "hosted_execution": False,
            "github_actions_used": False,
            "repository_root": str(self.config.repository_root.resolve()),
            "run_root": str(self.run_root),
            "required_branch": self.config.required_branch,
            "profile": self.config.profile,
            "source_image_mutated": False,
            "host_packages_installed_by_tool": False,
            "existing_implementations": {
                "builder": str(BUILD_SCRIPT.relative_to(PROJECT_ROOT)),
                "package_probe": "tools/r7_compositor_package_probe.py",
                "qemu_handoff": "tools/r7_qemu_kmsdrm_handoff_acceptance.py",
                "passive_probe": "greia_platform.direct_graphics_probe",
            },
            "package_candidates": list(CANDIDATES),
            "steps": [
                "preflight-and-source-verify",
                "build-production-image",
                "passive-installed-image-probe",
                "measure-fixed-package-candidates",
                "active-and-serial-qemu-if-kmsdrm-compiled",
                "source-and-image-integrity-reconfirm",
                "write-local-evidence-summary",
            ],
        }

    def run(self) -> dict[str, object]:
        self._require_linux_root()
        self._require_host_tools(_BASE_HOST_COMMANDS)
        source_sha = self._preflight_source()
        self._create_run_root()
        self._write_json(self.evidence_dir / "plan.json", self.plan())
        self._write_text(self.evidence_dir / "source-sha.txt", source_sha + "\n")

        try:
            self._run_source_verify("00-make-verify-prebuild.log")
            self._assert_source_unchanged(source_sha)
            image_sha = self._build_production_image()
            passive = self._probe_installed_image(image_sha)
            package_reports = self._measure_packages(image_sha)
            qemu_report = self._run_qemu_if_applicable(passive, image_sha)
            self._run_source_verify("90-make-verify-postbuild.log")
            self._assert_source_unchanged(source_sha)
            self._assert_source_image_intact(image_sha)
            report = self._summary(
                source_sha=source_sha,
                image_sha=image_sha,
                passive=passive,
                package_reports=package_reports,
                qemu_report=qemu_report,
            )
            self._write_json(self.evidence_dir / "r7-local-evidence-summary.json", report)
            return report
        except Exception as exc:
            failure = {
                "schema_version": SCHEMA_VERSION,
                "ok": False,
                "source_sha": source_sha,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "first_failure_is_authoritative_for_this_attempt": True,
                "do_not_rerun_active_qemu_in_same_attempt": True,
            }
            self._write_json(self.evidence_dir / "failure.json", failure)
            raise

    def _preflight_source(self) -> str:
        repo = self.config.repository_root.resolve()
        if self.run_root.exists():
            raise LocalEvidenceError(
                f"refusing to reuse existing evidence root: {self.run_root}"
            )
        branch = self._git("branch", "--show-current")
        if branch != self.config.required_branch:
            raise LocalEvidenceError(
                f"expected branch {self.config.required_branch!r}, found {branch!r}"
            )
        status = self._git("status", "--porcelain")
        if status:
            raise LocalEvidenceError("repository must be clean before evidence execution")
        source_sha = self._git("rev-parse", "--verify", "HEAD")
        if len(source_sha) != 40 or any(ch not in "0123456789abcdef" for ch in source_sha):
            raise LocalEvidenceError("git returned an invalid source commit identity")
        if not BUILD_SCRIPT.is_file():
            raise LocalEvidenceError(f"production builder is missing: {BUILD_SCRIPT}")
        return source_sha

    def _create_run_root(self) -> None:
        for path in (
            self.image_dir,
            self.package_dir,
            self.qemu_dir,
            self.evidence_dir,
            self.log_dir,
            self.mount_dir,
        ):
            path.mkdir(parents=True, exist_ok=False)

    def _run_source_verify(self, log_name: str) -> None:
        env = dict(os.environ)
        env.update(
            {
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
            }
        )
        status = self._run_logged(
            ["make", "verify"],
            self.log_dir / log_name,
            cwd=self.config.repository_root,
            env=env,
        )
        if status != 0:
            raise LocalEvidenceError(f"make verify failed with status {status}")

    def _build_production_image(self) -> str:
        status = self._run_logged(
            [str(BUILD_SCRIPT), self.config.profile, str(self.image_dir)],
            self.log_dir / "10-build.log",
            cwd=self.config.repository_root,
        )
        self._write_text(self.evidence_dir / "build-status.txt", f"{status}\n")
        if status != 0:
            raise LocalEvidenceError(f"production image builder failed with status {status}")
        required = (
            self.image_path,
            self.image_dir / f"greia-os-{self.config.profile}-footprint.txt",
            self.image_dir / f"greia-os-{self.config.profile}-image-profile.json",
        )
        for path in required:
            if not path.is_file() or path.stat().st_size == 0:
                raise LocalEvidenceError(f"production builder output is missing: {path}")
        self._assert_no_image_loop_association()
        image_sha = self._sha256(self.image_path)
        self._write_text(
            self.evidence_dir / "production-image.sha256",
            f"{image_sha}  {self.image_path.name}\n",
        )
        shutil.copy2(
            self.image_dir / f"greia-os-{self.config.profile}-footprint.txt",
            self.evidence_dir / "production-footprint.txt",
        )
        shutil.copy2(
            self.image_dir / f"greia-os-{self.config.profile}-image-profile.json",
            self.evidence_dir / "production-image-profile.json",
        )
        return image_sha

    def _probe_installed_image(self, image_sha: str) -> dict[str, object]:
        with MountedRawImage(
            self.image_path,
            self.mount_dir,
            read_only=True,
            runner=self.runner,
        ) as root:
            completed = self.runner.run(
                [
                    "chroot",
                    str(root),
                    "/usr/bin/env",
                    "PYGAME_HIDE_SUPPORT_PROMPT=1",
                    "PYTHONPATH=/opt/greia-os/src",
                    "PYTHONNOUSERSITE=1",
                    "PYTHONDONTWRITEBYTECODE=1",
                    "python3",
                    "-m",
                    "greia_platform.direct_graphics_probe",
                ],
                capture_output=True,
            )
            try:
                passive = json.loads(completed.stdout)
            except json.JSONDecodeError as exc:
                raise LocalEvidenceError("passive installed-image probe returned invalid JSON") from exc
            validate_passive_probe(passive)
            self._write_json(self.evidence_dir / "direct-graphics-probe.json", passive)

            packages = self.runner.run(
                [
                    "chroot",
                    str(root),
                    "dpkg-query",
                    "-W",
                    "-f=${Package}\\t${Version}\\t${Architecture}\\n",
                    "libsdl2-2.0-0",
                    "python3-pygame",
                    "libdrm2",
                    "libgbm1",
                    "libegl1",
                    "plymouth",
                    "plymouth-label",
                    "e2fsprogs",
                ],
                capture_output=True,
            )
            self._write_text(self.evidence_dir / "graphics-packages.tsv", packages.stdout)
            manifest = root / "etc/greia-os/base-system-manifest"
            if not manifest.is_file():
                raise LocalEvidenceError("finished image is missing base-system-manifest")
            shutil.copy2(manifest, self.evidence_dir / "base-system-manifest.txt")

        self._assert_source_image_intact(image_sha)
        return passive

    def _measure_packages(self, image_sha: str) -> dict[str, Mapping[str, object]]:
        reports: dict[str, Mapping[str, object]] = {}
        for candidate in CANDIDATES:
            probe = CompositorPackageProbe(
                PackageProbeConfig(
                    source_image=self.image_path,
                    output_dir=self.package_dir,
                    candidate=candidate,
                ),
                runner=self.runner,
            )
            report = probe.run()
            validate_package_report(report, candidate=candidate, image_sha=image_sha)
            reports[candidate] = report
            self._write_json(
                self.evidence_dir / f"{candidate}-package-probe.json",
                report,
            )
            self._assert_source_image_intact(image_sha)
        return reports

    def _run_qemu_if_applicable(
        self,
        passive: Mapping[str, object],
        image_sha: str,
    ) -> Mapping[str, object] | None:
        sdl = passive.get("sdl")
        if not isinstance(sdl, Mapping):
            raise LocalEvidenceError("passive evidence has no SDL mapping")
        kmsdrm_compiled = sdl.get("kmsdrm_compiled")
        if kmsdrm_compiled is False:
            self._write_text(
                self.evidence_dir / "qemu-status.txt",
                "not-run-kmsdrm-not-compiled\n",
            )
            return None
        if kmsdrm_compiled is not True:
            raise LocalEvidenceError("passive KMSDRM classification is not boolean")
        self._require_host_tools((self.config.qemu_binary,))
        harness = QemuKMSDRMSerialHandoffHarness(
            HandoffHarnessConfig(
                source_image=self.image_path,
                output_dir=self.qemu_dir,
                qemu_binary=self.config.qemu_binary,
                timeout_seconds=self.config.qemu_timeout_seconds,
                keep_test_image=self.config.keep_qemu_image,
            ),
            runner=self.runner,
        )
        report = harness.run()
        if report.get("classification") != "SERIAL_QEMU_KMSDRM_HANDOFF_PASS":
            raise LocalEvidenceError("serial QEMU harness did not return its exact PASS classification")
        if report.get("source_image_sha256") != image_sha:
            raise LocalEvidenceError("serial QEMU evidence source image identity mismatch")
        self._write_json(self.evidence_dir / "qemu-kmsdrm-handoff-report.json", report)
        baseline = report.get("baseline")
        if isinstance(baseline, Mapping):
            self._write_json(self.evidence_dir / "qemu-kmsdrm-report.json", baseline)
        self._write_text(
            self.evidence_dir / "qemu-status.txt",
            "active-and-serial-handoff-qemu-pass\n",
        )
        self._assert_source_image_intact(image_sha)
        return report

    def _summary(
        self,
        *,
        source_sha: str,
        image_sha: str,
        passive: Mapping[str, object],
        package_reports: Mapping[str, Mapping[str, object]],
        qemu_report: Mapping[str, object] | None,
    ) -> dict[str, object]:
        sdl = passive["sdl"]
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "hosted_execution": False,
            "github_actions_used": False,
            "source_sha": source_sha,
            "source_image": str(self.image_path),
            "source_image_sha256": image_sha,
            "source_image_mutated": False,
            "sdl_video_drivers": sdl["video_drivers"],
            "kmsdrm_compiled": sdl["kmsdrm_compiled"],
            "package_probe_classifications": {
                candidate: report.get("classification")
                for candidate, report in package_reports.items()
            },
            "qemu_classification": (
                None if qemu_report is None else qemu_report.get("classification")
            ),
            "active_seat_input_evidence_complete": False,
            "physical_legacy_intel_acer_evidence_complete": False,
            "production_session_changed": False,
            "limitations": [
                "local orchestration reuses existing R7 evidence implementations",
                "no GitHub-hosted runner or GitHub Actions execution is used",
                "active seat/input evidence remains a separate R7 requirement",
                "physical legacy Intel/Acer acceptance remains mandatory before migration",
            ],
        }

    def _assert_source_unchanged(self, source_sha: str) -> None:
        if self._git("rev-parse", "HEAD") != source_sha:
            raise LocalEvidenceError("source commit changed during evidence execution")
        if self._git("status", "--porcelain"):
            raise LocalEvidenceError("repository became dirty during evidence execution")

    def _assert_source_image_intact(self, image_sha: str) -> None:
        self._assert_no_image_loop_association()
        if self._sha256(self.image_path) != image_sha:
            raise LocalEvidenceError("source production image SHA-256 changed")

    def _assert_no_image_loop_association(self) -> None:
        completed = self.runner.run(
            ["losetup", "-j", str(self.image_path)],
            check=False,
            capture_output=True,
        )
        if completed.stdout.strip():
            self._write_text(
                self.evidence_dir / "unexpected-loop-association.txt",
                completed.stdout,
            )
            raise LocalEvidenceError("production image has a surviving loop association")

    def _git(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=self.config.repository_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    def _run_logged(
        self,
        argv: Sequence[str],
        log_path: Path,
        *,
        cwd: Path,
        env: Mapping[str, str] | None = None,
    ) -> int:
        with log_path.open("w", encoding="utf-8") as log:
            completed = subprocess.run(
                list(argv),
                cwd=cwd,
                env=None if env is None else dict(env),
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
        return completed.returncode

    @staticmethod
    def _require_linux_root() -> None:
        if platform.system() != "Linux":
            raise LocalEvidenceError("R7 image/QEMU evidence requires a Linux host")
        if os.geteuid() != 0:
            raise LocalEvidenceError(
                "run this evidence orchestrator as root on a controlled/disposable Linux checkout"
            )

    @staticmethod
    def _require_host_tools(commands: Sequence[str]) -> None:
        missing = [command for command in commands if shutil.which(command) is None]
        if missing:
            raise LocalEvidenceError(
                "missing host commands; install prerequisites manually: " + ", ".join(missing)
            )

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _write_text(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    @classmethod
    def _write_json(cls, path: Path, payload: Mapping[str, object]) -> None:
        cls._write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def validate_passive_probe(payload: Mapping[str, object]) -> None:
    if payload.get("schema_version") != 1 or payload.get("passive") is not True:
        raise LocalEvidenceError("invalid passive direct-graphics evidence header")
    assessment = payload.get("assessment")
    sdl = payload.get("sdl")
    if not isinstance(assessment, Mapping) or not isinstance(sdl, Mapping):
        raise LocalEvidenceError("passive evidence is missing assessment/SDL mappings")
    if assessment.get("active_kmsdrm_test_required") is not True:
        raise LocalEvidenceError("passive evidence unexpectedly waives active KMSDRM")
    if assessment.get("active_seat_input_test_required") is not True:
        raise LocalEvidenceError("passive evidence unexpectedly waives active seat/input testing")
    if not isinstance(sdl.get("video_drivers"), list):
        raise LocalEvidenceError("passive SDL video-driver inventory is malformed")
    if not isinstance(sdl.get("kmsdrm_compiled"), bool):
        raise LocalEvidenceError("passive KMSDRM compiled result must be boolean")


def validate_package_report(
    payload: Mapping[str, object],
    *,
    candidate: str,
    image_sha: str,
) -> None:
    if payload.get("schema_version") != 1 or payload.get("ok") is not True:
        raise LocalEvidenceError(f"{candidate} package probe did not PASS its own contract")
    if payload.get("candidate") != candidate:
        raise LocalEvidenceError(f"{candidate} package probe identity mismatch")
    if payload.get("source_image_sha256") != image_sha:
        raise LocalEvidenceError(f"{candidate} package probe source-image mismatch")
    if payload.get("source_image_sha256_after") != image_sha:
        raise LocalEvidenceError(f"{candidate} package probe changed source-image identity")
    for key in (
        "source_image_mutated",
        "host_devices_exposed",
        "host_sysfs_exposed",
        "host_run_exposed",
        "boot_or_service_changes",
    ):
        if payload.get(key) is not False:
            raise LocalEvidenceError(f"{candidate} package probe unsafe flag: {key}")
    apt_policy = payload.get("apt_policy")
    if apt_policy != {
        "install_recommends": False,
        "upgrades_allowed": False,
        "removals_allowed": False,
    }:
        raise LocalEvidenceError(f"{candidate} package probe APT policy changed")
    packages = payload.get("packages")
    if not isinstance(packages, Mapping):
        raise LocalEvidenceError(f"{candidate} package report has no package mapping")
    if packages.get("removed") != [] or packages.get("upgraded_or_changed") != []:
        raise LocalEvidenceError(f"{candidate} package probe changed baseline packages")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the existing Greia R7 evidence chain on a local Linux host without GitHub Actions."
    )
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--required-branch", default=DEFAULT_BRANCH)
    parser.add_argument("--qemu-binary", default="qemu-system-x86_64")
    parser.add_argument("--qemu-timeout-seconds", type=int, default=240)
    parser.add_argument("--keep-qemu-image", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    orchestrator = LocalR7EvidenceOrchestrator(
        LocalEvidenceConfig(
            run_root=args.run_root,
            required_branch=args.required_branch,
            qemu_binary=args.qemu_binary,
            qemu_timeout_seconds=args.qemu_timeout_seconds,
            keep_qemu_image=args.keep_qemu_image,
        )
    )
    if args.plan_only:
        print(json.dumps(orchestrator.plan(), indent=2, sort_keys=True))
        return 0
    try:
        report = orchestrator.run()
    except LocalEvidenceError as exc:
        print(f"R7 local evidence failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
