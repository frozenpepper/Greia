#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from r7_qemu_kmsdrm_acceptance import (
    CommandRunner,
    MountedRawImage,
    SAFE_CLEANUP,
)


SCHEMA_VERSION = 1

CANDIDATES: Mapping[str, tuple[str, ...]] = {
    "cage": ("cage",),
    "weston": ("weston",),
    "wlroots-runtime": ("libwlroots-0.18",),
}

_X_SERVER_PACKAGES = frozenset({"xwayland", "xserver-xorg-core"})
_DESKTOP_RISK_PACKAGES = frozenset(
    {
        "gnome-shell",
        "gnome-session",
        "plasma-workspace",
        "plasma-desktop",
        "xfce4-session",
        "lxqt-session",
        "mate-session-manager",
        "xterm",
        "gnome-terminal",
        "konsole",
        "foot",
        "alacritty",
    }
)


class CompositorPackageProbeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PackageRecord:
    name: str
    version: str
    architecture: str
    installed_size_kib: int

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "architecture": self.architecture,
            "installed_size_kib": self.installed_size_kib,
        }


@dataclass(frozen=True, slots=True)
class ProbeConfig:
    source_image: Path
    output_dir: Path
    candidate: str
    keep_test_image: bool = False

    def validate(self) -> None:
        if self.candidate not in CANDIDATES:
            raise CompositorPackageProbeError(
                f"unknown candidate {self.candidate!r}; choose from {', '.join(sorted(CANDIDATES))}"
            )


class ChrootRuntimeMounts(AbstractContextManager[None]):
    """Provide the minimum virtual filesystems required for APT/dpkg in a clone."""

    def __init__(self, root: Path, *, runner: CommandRunner):
        self.root = root
        self.runner = runner
        self._mounted: list[Path] = []

    def __enter__(self) -> None:
        for name in ("dev", "proc", "sys", "run"):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        try:
            self._rbind(Path("/dev"), self.root / "dev")
            self.runner.run(["mount", "-t", "proc", "proc", str(self.root / "proc")])
            self._mounted.append(self.root / "proc")
            self._rbind(Path("/sys"), self.root / "sys")
            self._rbind(Path("/run"), self.root / "run")
        except Exception:
            cleanup_error = self._cleanup()
            if cleanup_error is not None:
                raise CompositorPackageProbeError(
                    "chroot runtime mount setup failed and cleanup was incomplete"
                ) from cleanup_error
            raise
        return None

    def __exit__(self, exc_type, exc, traceback) -> bool:
        cleanup_error = self._cleanup()
        if cleanup_error is not None:
            detail = (
                "chroot runtime cleanup failed while handling another failure"
                if exc is not None
                else "chroot runtime cleanup failed"
            )
            raise CompositorPackageProbeError(detail) from cleanup_error
        return False

    def _rbind(self, source: Path, target: Path) -> None:
        self.runner.run(["mount", "--rbind", str(source), str(target)])
        self._mounted.append(target)
        self.runner.run(["mount", "--make-rslave", str(target)])

    def _cleanup(self) -> Exception | None:
        if not self._mounted:
            return None
        paths = " ".join(shlex.quote(str(path)) for path in self._mounted)
        command = (
            f"source {shlex.quote(str(SAFE_CLEANUP))}; "
            f"safe_unmount_paths {paths}"
        )
        try:
            self.runner.run(["bash", "-c", command])
        except Exception as exc:  # pragma: no cover - privileged failure path
            return exc
        self._mounted.clear()
        return None


class CompositorPackageProbe:
    """Measure candidate package closure in a disposable production-image clone.

    This tool does not enable a compositor, change production package sets, or
    boot the clone. It only performs a bounded APT transaction with
    --no-install-recommends, --no-upgrade, and --no-remove, then reports the
    exact package/filesystem delta after cleaning APT state again.
    """

    def __init__(self, config: ProbeConfig, *, runner: CommandRunner | None = None):
        config.validate()
        self.config = config
        self.runner = runner or CommandRunner()

    @property
    def candidate_packages(self) -> tuple[str, ...]:
        return CANDIDATES[self.config.candidate]

    @property
    def test_image(self) -> Path:
        return self.config.output_dir / f"greia-r7-{self.config.candidate}-package-probe.img"

    @property
    def report_path(self) -> Path:
        return self.config.output_dir / f"greia-r7-{self.config.candidate}-package-probe.json"

    @property
    def apt_log_path(self) -> Path:
        return self.config.output_dir / f"greia-r7-{self.config.candidate}-apt.log"

    def plan(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "source_image": str(self.config.source_image.resolve()),
            "test_image": str(self.test_image.resolve()),
            "source_image_mutated": False,
            "candidate": self.config.candidate,
            "packages": list(self.candidate_packages),
            "apt_policy": {
                "install_recommends": False,
                "upgrades_allowed": False,
                "removals_allowed": False,
            },
            "boot_or_service_changes": False,
        }

    def run(self) -> dict[str, object]:
        self._require_privileged_host()
        self._require_tools()
        source = self.config.source_image.resolve()
        if not source.is_file() or source.stat().st_size <= 0:
            raise CompositorPackageProbeError(f"source image is missing or empty: {source}")
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        if self.test_image.exists():
            raise CompositorPackageProbeError(
                f"refusing to replace existing test image: {self.test_image}"
            )
        if source == self.test_image.resolve():
            raise CompositorPackageProbeError("source and test images must differ")

        source_sha_before = _sha256_file(source)
        self._clone_source_image(source)
        success = False
        try:
            report = self._measure_clone(source, source_sha_before)
            source_sha_after = _sha256_file(source)
            if source_sha_after != source_sha_before:
                raise CompositorPackageProbeError(
                    "source image hash changed during disposable package measurement"
                )
            report["source_image_sha256_after"] = source_sha_after
            report["source_image_mutated"] = False
            _write_json(self.report_path, report)
            success = True
            return report
        finally:
            if success and not self.config.keep_test_image:
                self.test_image.unlink(missing_ok=True)

    def _measure_clone(self, source: Path, source_sha: str) -> dict[str, object]:
        mountpoint = self.config.output_dir / f"mounted-{self.config.candidate}-probe"
        with MountedRawImage(
            self.test_image, mountpoint, read_only=False, runner=self.runner
        ) as root:
            baseline_manifest_path = root / "etc/greia-os/package-manifest.tsv"
            if not baseline_manifest_path.is_file():
                raise CompositorPackageProbeError(
                    "production image has no authoritative package manifest"
                )
            baseline = parse_package_manifest(
                baseline_manifest_path.read_text(encoding="utf-8")
            )
            baseline_file_bytes = _du_bytes(root, self.runner)
            baseline_fs_bytes = _filesystem_used_bytes(root, self.runner)
            _prepare_clone_for_apt(root)

            with ChrootRuntimeMounts(root, runner=self.runner):
                apt_log = self._install_candidate(root)
                current_text = self.runner.run(
                    [
                        "chroot",
                        str(root),
                        "dpkg-query",
                        "-W",
                        "-f=${Package}\\t${Version}\\t${Architecture}\\t${Installed-Size}\\n",
                    ],
                    capture_output=True,
                ).stdout
                current = parse_package_manifest(current_text)
                downloaded_bytes = sum(
                    path.stat().st_size
                    for path in (root / "var/cache/apt/archives").glob("*.deb")
                    if path.is_file()
                )
                self._clean_apt(root)

            _remove_probe_mutations(root)
            final_file_bytes = _du_bytes(root, self.runner)
            final_fs_bytes = _filesystem_used_bytes(root, self.runner)
            self.apt_log_path.write_text(apt_log, encoding="utf-8")

            package_delta = compare_package_manifests(baseline, current)
            if package_delta["removed"]:
                raise CompositorPackageProbeError(
                    "candidate transaction removed baseline packages despite --no-remove"
                )
            if package_delta["upgraded_or_changed"]:
                raise CompositorPackageProbeError(
                    "candidate transaction changed baseline package versions despite --no-upgrade"
                )

            added_records = [
                current[name]
                for name in package_delta["added"]
            ]
            introduced_names = {record.name for record in added_records}
            x_components = sorted(
                name
                for name in introduced_names
                if name in _X_SERVER_PACKAGES or name.startswith("xserver-xorg-")
            )
            desktop_risks = sorted(introduced_names & _DESKTOP_RISK_PACKAGES)
            classification = (
                "MEASURED_WITH_X_SERVER_COMPONENTS"
                if x_components
                else "MEASURED_NO_X_SERVER_COMPONENTS"
            )

            return {
                "schema_version": SCHEMA_VERSION,
                "ok": True,
                "classification": classification,
                "candidate": self.config.candidate,
                "requested_packages": list(self.candidate_packages),
                "source_image": str(source),
                "source_image_sha256": source_sha,
                "test_image": str(self.test_image.resolve()),
                "boot_or_service_changes": False,
                "apt_policy": {
                    "install_recommends": False,
                    "upgrades_allowed": False,
                    "removals_allowed": False,
                },
                "packages": {
                    "baseline_count": len(baseline),
                    "final_count": len(current),
                    "added": [record.as_dict() for record in added_records],
                    "added_count": len(added_records),
                    "added_installed_size_kib": sum(
                        record.installed_size_kib for record in added_records
                    ),
                    "upgraded_or_changed": package_delta["upgraded_or_changed"],
                    "removed": package_delta["removed"],
                    "downloaded_deb_bytes": downloaded_bytes,
                    "x_server_components": x_components,
                    "desktop_risk_components": desktop_risks,
                },
                "filesystem": {
                    "baseline_file_bytes": baseline_file_bytes,
                    "final_file_bytes": final_file_bytes,
                    "file_delta_bytes": final_file_bytes - baseline_file_bytes,
                    "baseline_used_bytes": baseline_fs_bytes,
                    "final_used_bytes": final_fs_bytes,
                    "used_delta_bytes": final_fs_bytes - baseline_fs_bytes,
                },
                "limitations": [
                    "measures package and filesystem closure only; candidate is not enabled or booted",
                    "does not measure compositor RSS, latency, scanout, input routing, or crash recovery",
                    "does not authorize adding the candidate to a production Greia package set",
                ],
            }

    def _install_candidate(self, root: Path) -> str:
        acquire = (
            "-o", "Acquire::Retries=3",
            "-o", "Acquire::http::Timeout=20",
            "-o", "Acquire::https::Timeout=20",
        )
        update = self.runner.run(
            [
                "chroot",
                str(root),
                "/usr/bin/env",
                "DEBIAN_FRONTEND=noninteractive",
                "LC_ALL=C",
                "apt-get",
                *acquire,
                "update",
            ],
            capture_output=True,
        )
        install = self.runner.run(
            [
                "chroot",
                str(root),
                "/usr/bin/env",
                "DEBIAN_FRONTEND=noninteractive",
                "LC_ALL=C",
                "apt-get",
                *acquire,
                "-o",
                "Dpkg::Options::=--force-confold",
                "install",
                "-y",
                "--no-install-recommends",
                "--no-upgrade",
                "--no-remove",
                *self.candidate_packages,
            ],
            capture_output=True,
        )
        return (
            "=== apt-get update ===\n"
            + update.stdout
            + update.stderr
            + "\n=== apt-get install ===\n"
            + install.stdout
            + install.stderr
        )

    def _clean_apt(self, root: Path) -> None:
        self.runner.run(["chroot", str(root), "apt-get", "clean"])
        for directory, pattern in (
            (root / "var/lib/apt/lists", "*"),
            (root / "var/cache/apt/archives", "*.deb"),
        ):
            if not directory.exists():
                continue
            for path in directory.glob(pattern):
                if path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path)
                else:
                    path.unlink(missing_ok=True)

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
        if (
            not self.test_image.is_file()
            or self.test_image.stat().st_size != source.stat().st_size
        ):
            raise CompositorPackageProbeError("disposable image clone is incomplete")

    @staticmethod
    def _require_privileged_host() -> None:
        if os.geteuid() != 0:
            raise CompositorPackageProbeError("run compositor package measurement as root")

    def _require_tools(self) -> None:
        if not SAFE_CLEANUP.is_file():
            raise CompositorPackageProbeError(
                f"missing Greia cleanup helper: {SAFE_CLEANUP}"
            )
        required = (
            "cp",
            "chroot",
            "losetup",
            "mount",
            "umount",
            "findmnt",
            "bash",
            "partx",
            "blockdev",
            "udevadm",
            "du",
            "df",
        )
        missing = [command for command in required if shutil.which(command) is None]
        if missing:
            raise CompositorPackageProbeError(
                "missing host tools: " + ", ".join(missing)
            )


def parse_package_manifest(text: str) -> dict[str, PackageRecord]:
    records: dict[str, PackageRecord] = {}
    for line_number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        parts = raw.split("\t")
        if len(parts) != 4:
            raise CompositorPackageProbeError(
                f"invalid package manifest line {line_number}: expected 4 fields"
            )
        name, version, architecture, size_text = parts
        if not name or not version or not architecture:
            raise CompositorPackageProbeError(
                f"invalid package manifest line {line_number}: empty identity field"
            )
        if name in records:
            raise CompositorPackageProbeError(
                f"duplicate package in manifest: {name}"
            )
        try:
            size = int(size_text)
        except ValueError as exc:
            raise CompositorPackageProbeError(
                f"invalid installed size for package {name}"
            ) from exc
        if size < 0:
            raise CompositorPackageProbeError(
                f"negative installed size for package {name}"
            )
        records[name] = PackageRecord(name, version, architecture, size)
    if not records:
        raise CompositorPackageProbeError("package manifest is empty")
    return records


def compare_package_manifests(
    baseline: Mapping[str, PackageRecord], current: Mapping[str, PackageRecord]
) -> dict[str, list[object]]:
    baseline_names = set(baseline)
    current_names = set(current)
    added = sorted(current_names - baseline_names)
    removed = sorted(baseline_names - current_names)
    changed = []
    for name in sorted(baseline_names & current_names):
        before = baseline[name]
        after = current[name]
        if (
            before.version != after.version
            or before.architecture != after.architecture
        ):
            changed.append(
                {
                    "name": name,
                    "before_version": before.version,
                    "after_version": after.version,
                    "before_architecture": before.architecture,
                    "after_architecture": after.architecture,
                }
            )
    return {
        "added": added,
        "removed": removed,
        "upgraded_or_changed": changed,
    }


def _prepare_clone_for_apt(root: Path) -> None:
    resolv = root / "etc/resolv.conf"
    host_resolv = Path("/etc/resolv.conf")
    try:
        content = host_resolv.read_bytes()
    except OSError as exc:
        raise CompositorPackageProbeError("host resolv.conf is unreadable") from exc
    if not content or len(content) > 64 * 1024:
        raise CompositorPackageProbeError("host resolv.conf is empty or unexpectedly large")
    if resolv.exists() or resolv.is_symlink():
        resolv.unlink()
    resolv.write_bytes(content)
    os.chmod(resolv, 0o644)

    policy = root / "usr/sbin/policy-rc.d"
    if policy.exists() or policy.is_symlink():
        raise CompositorPackageProbeError(
            "production image unexpectedly already contains /usr/sbin/policy-rc.d"
        )
    policy.write_text("#!/bin/sh\nexit 101\n", encoding="ascii")
    os.chmod(policy, 0o755)


def _remove_probe_mutations(root: Path) -> None:
    (root / "usr/sbin/policy-rc.d").unlink(missing_ok=True)
    # resolv.conf is disposable-clone plumbing. Removing it avoids counting the
    # host resolver contents as compositor package cost; the clone is never booted.
    (root / "etc/resolv.conf").unlink(missing_ok=True)


def _du_bytes(root: Path, runner: CommandRunner) -> int:
    output = runner.run(
        ["du", "-sx", "--block-size=1", str(root)], capture_output=True
    ).stdout.split()[0]
    return _parse_nonnegative_int(output, "du byte count")


def _filesystem_used_bytes(root: Path, runner: CommandRunner) -> int:
    output = runner.run(
        ["df", "-B1", "--output=used", str(root)], capture_output=True
    ).stdout.splitlines()
    if len(output) < 2:
        raise CompositorPackageProbeError("could not parse filesystem-used bytes")
    return _parse_nonnegative_int(output[-1].strip(), "filesystem-used bytes")


def _parse_nonnegative_int(text: str, label: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise CompositorPackageProbeError(f"invalid {label}: {text!r}") from exc
    if value < 0:
        raise CompositorPackageProbeError(f"negative {label}")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o644)
    temporary.replace(path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Measure compositor/reference package closure in a disposable clone "
            "of an exact Greia production image without enabling or booting it."
        )
    )
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--candidate", choices=sorted(CANDIDATES), required=True)
    parser.add_argument("--keep-test-image", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    probe = CompositorPackageProbe(
        ProbeConfig(
            source_image=args.image,
            output_dir=args.output_dir,
            candidate=args.candidate,
            keep_test_image=args.keep_test_image,
        )
    )
    if args.plan_only:
        print(json.dumps(probe.plan(), sort_keys=True, indent=2))
        return 0
    try:
        report = probe.run()
    except (CompositorPackageProbeError, subprocess.CalledProcessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
