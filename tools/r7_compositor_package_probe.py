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

from r7_qemu_kmsdrm_acceptance import CommandRunner, MountedRawImage, SAFE_CLEANUP

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
_PRIVATE_DEVICES: tuple[tuple[str, str, str, str], ...] = (
    ("null", "c", "1", "3"),
    ("zero", "c", "1", "5"),
    ("full", "c", "1", "7"),
    ("random", "c", "1", "8"),
    ("urandom", "c", "1", "9"),
)
_BOOT_STATE_PATHS = (
    "etc/systemd/system",
    "etc/default/grub",
    "etc/default/grub.d",
    "boot/grub",
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
class ResolvConfBackup:
    kind: str
    payload: bytes | str | None
    mode: int | None = None


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
    """Provide a private minimal /dev plus fresh procfs to trusted Debian APT/dpkg.

    Host /dev, /sys and /run are deliberately not exposed. The private /dev is
    a short-lived tmpfs containing only pseudo devices required by ordinary
    noninteractive package scripts.
    """

    def __init__(self, root: Path, *, runner: CommandRunner):
        self.root = root
        self.runner = runner
        self._mounted: list[Path] = []

    def __enter__(self) -> None:
        dev = self.root / "dev"
        proc = self.root / "proc"
        dev.mkdir(parents=True, exist_ok=True)
        proc.mkdir(parents=True, exist_ok=True)
        try:
            self.runner.run(
                [
                    "mount",
                    "-t",
                    "tmpfs",
                    "-o",
                    "mode=0755,nosuid,noexec,size=64k",
                    "greia-r7-dev",
                    str(dev),
                ]
            )
            self._mounted.append(dev)
            for name, kind, major, minor in _PRIVATE_DEVICES:
                node = dev / name
                self.runner.run(["mknod", "-m", "0666", str(node), kind, major, minor])
            self.runner.run(["mount", "-t", "proc", "proc", str(proc)])
            self._mounted.append(proc)
            self.runner.run(["ln", "-s", "/proc/self/fd", str(dev / "fd")])
            self.runner.run(["ln", "-s", "/proc/self/fd/0", str(dev / "stdin")])
            self.runner.run(["ln", "-s", "/proc/self/fd/1", str(dev / "stdout")])
            self.runner.run(["ln", "-s", "/proc/self/fd/2", str(dev / "stderr")])
        except Exception:
            cleanup_error = self._cleanup()
            if cleanup_error is not None:
                raise CompositorPackageProbeError(
                    "private chroot runtime setup failed and cleanup was incomplete"
                ) from cleanup_error
            raise
        return None

    def __exit__(self, exc_type, exc, traceback) -> bool:
        cleanup_error = self._cleanup()
        if cleanup_error is not None:
            detail = (
                "private chroot runtime cleanup failed while handling another failure"
                if exc is not None
                else "private chroot runtime cleanup failed"
            )
            raise CompositorPackageProbeError(detail) from cleanup_error
        return False

    def _cleanup(self) -> Exception | None:
        if not self._mounted:
            return None
        paths = " ".join(shlex.quote(str(path)) for path in reversed(self._mounted))
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
    """Measure compositor/reference package closure in a disposable image clone."""

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
            "chroot_runtime": {
                "private_minimal_dev": True,
                "fresh_procfs": True,
                "host_devices_exposed": False,
                "host_sysfs_exposed": False,
                "host_run_exposed": False,
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
        test_image = self.test_image.resolve()
        if test_image.exists():
            raise CompositorPackageProbeError(f"refusing to replace existing test image: {test_image}")
        if source == test_image:
            raise CompositorPackageProbeError("source and test images must differ")

        source_sha_before = _sha256_file(source)
        report: dict[str, object] | None = None
        primary_error: BaseException | None = None
        clone_created = False
        try:
            self._clone_source_image(source)
            clone_created = True
            report = self._measure_clone(source, source_sha_before)
        except BaseException as exc:
            primary_error = exc
        finally:
            source_sha_after = _sha256_file(source)
            cleanup_error: BaseException | None = None
            if clone_created and not self.config.keep_test_image:
                try:
                    test_image.unlink(missing_ok=True)
                except BaseException as exc:  # pragma: no cover - filesystem failure
                    cleanup_error = exc

            if source_sha_after != source_sha_before:
                raise CompositorPackageProbeError(
                    "source image hash changed during disposable package measurement"
                ) from primary_error
            if cleanup_error is not None:
                raise CompositorPackageProbeError(
                    "disposable package-probe image cleanup failed"
                ) from cleanup_error

        if primary_error is not None:
            raise primary_error
        if report is None:  # pragma: no cover - defensive invariant
            raise CompositorPackageProbeError("package probe produced no report")

        report["source_image_sha256_after"] = source_sha_before
        report["source_image_mutated"] = False
        _write_json(self.report_path, report)
        return report

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
            boot_state_before = _boot_state_signature(root)
            resolver_backup = _prepare_clone_for_apt(root)

            try:
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
                    missing_requested = [
                        package for package in self.candidate_packages if package not in current
                    ]
                    if missing_requested:
                        raise CompositorPackageProbeError(
                            "candidate transaction completed without requested packages: "
                            + ", ".join(missing_requested)
                        )
                    downloaded_bytes = sum(
                        path.stat().st_size
                        for path in (root / "var/cache/apt/archives").glob("*.deb")
                        if path.is_file()
                    )
                    self._clean_apt(root)
            finally:
                _remove_probe_mutations(root, resolver_backup)

            _truncate_measurement_logs(root)
            boot_state_after = _boot_state_signature(root)
            if boot_state_after != boot_state_before:
                raise CompositorPackageProbeError(
                    "candidate transaction changed protected boot/service state"
                )

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

            added_records = [current[name] for name in package_delta["added"]]
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
                "chroot_runtime": {
                    "private_minimal_dev": True,
                    "fresh_procfs": True,
                    "host_devices_exposed": False,
                    "host_sysfs_exposed": False,
                    "host_run_exposed": False,
                },
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
                    "measures incremental package/filesystem closure relative to the current Xorg production image",
                    "candidate is not enabled or booted",
                    "fixed Debian APT/dpkg package code is trusted; this chroot is not an arbitrary-code sandbox",
                    "does not measure compositor RSS, latency, scanout, input routing, or crash recovery",
                    "does not authorize adding the candidate to a production Greia package set",
                ],
            }

    def _install_candidate(self, root: Path) -> str:
        acquire = (
            "-o",
            "Acquire::Retries=3",
            "-o",
            "Acquire::http::Timeout=20",
            "-o",
            "Acquire::https::Timeout=20",
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
            "mknod",
            "ln",
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
            raise CompositorPackageProbeError(f"duplicate package in manifest: {name}")
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
    changed: list[object] = []
    for name in sorted(baseline_names & current_names):
        before = baseline[name]
        after = current[name]
        if before.version != after.version or before.architecture != after.architecture:
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


def _capture_resolv_conf(root: Path) -> ResolvConfBackup:
    resolv = root / "etc/resolv.conf"
    if resolv.is_symlink():
        return ResolvConfBackup("symlink", os.readlink(resolv))
    if not resolv.exists():
        return ResolvConfBackup("missing", None)
    if not resolv.is_file():
        raise CompositorPackageProbeError(
            "production image resolv.conf is neither a file nor a symlink"
        )
    data = resolv.read_bytes()
    if len(data) > 64 * 1024:
        raise CompositorPackageProbeError(
            "production image resolv.conf is unexpectedly large"
        )
    return ResolvConfBackup("file", data, resolv.stat().st_mode & 0o777)


def _prepare_clone_for_apt(root: Path) -> ResolvConfBackup:
    policy = root / "usr/sbin/policy-rc.d"
    if policy.exists() or policy.is_symlink():
        raise CompositorPackageProbeError(
            "production image unexpectedly already contains /usr/sbin/policy-rc.d"
        )

    backup = _capture_resolv_conf(root)
    try:
        host_resolv = Path("/etc/resolv.conf")
        content = host_resolv.read_bytes()
        if not content or len(content) > 64 * 1024:
            raise CompositorPackageProbeError(
                "host resolv.conf is empty or unexpectedly large"
            )

        resolv = root / "etc/resolv.conf"
        if resolv.exists() or resolv.is_symlink():
            resolv.unlink()
        resolv.write_bytes(content)
        os.chmod(resolv, 0o644)

        policy.parent.mkdir(parents=True, exist_ok=True)
        policy.write_text("#!/bin/sh\nexit 101\n", encoding="ascii")
        os.chmod(policy, 0o755)
        return backup
    except Exception:
        policy.unlink(missing_ok=True)
        _restore_resolv_conf(root, backup)
        raise


def _remove_probe_mutations(root: Path, backup: ResolvConfBackup) -> None:
    policy = root / "usr/sbin/policy-rc.d"
    policy.unlink(missing_ok=True)
    _restore_resolv_conf(root, backup)


def _restore_resolv_conf(root: Path, backup: ResolvConfBackup) -> None:
    resolv = root / "etc/resolv.conf"
    if resolv.exists() or resolv.is_symlink():
        resolv.unlink()
    if backup.kind == "missing":
        return
    if backup.kind == "symlink":
        if not isinstance(backup.payload, str):
            raise CompositorPackageProbeError("invalid resolver symlink backup")
        resolv.symlink_to(backup.payload)
        return
    if backup.kind == "file":
        if not isinstance(backup.payload, bytes) or backup.mode is None:
            raise CompositorPackageProbeError("invalid resolver file backup")
        resolv.write_bytes(backup.payload)
        os.chmod(resolv, backup.mode)
        return
    raise CompositorPackageProbeError(f"invalid resolver backup kind: {backup.kind!r}")


def _truncate_measurement_logs(root: Path) -> None:
    log_root = root / "var/log"
    if not log_root.exists():
        return
    for path in log_root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            with path.open("wb"):
                pass


def _tree_signature(root: Path) -> tuple[tuple[str, str, str], ...]:
    if not root.exists():
        return ()
    if root.is_symlink():
        return (("", "symlink", os.readlink(root)),)
    if root.is_file():
        return (("", "file", _sha256_file(root)),)

    records: list[tuple[str, str, str]] = []
    for path in sorted(root.rglob("*"), key=lambda item: str(item.relative_to(root))):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            records.append((relative, "symlink", os.readlink(path)))
        elif path.is_dir():
            records.append((relative, "directory", ""))
        elif path.is_file():
            records.append((relative, "file", _sha256_file(path)))
        else:
            records.append((relative, "other", ""))
    return tuple(records)


def _boot_state_signature(root: Path) -> tuple[tuple[str, tuple[tuple[str, str, str], ...]], ...]:
    return tuple(
        (relative, _tree_signature(root / relative))
        for relative in _BOOT_STATE_PATHS
    )


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
