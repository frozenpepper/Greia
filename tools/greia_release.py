#!/usr/bin/env python3
"""Owner-facing Greia release orchestration.

Session 03 turns the existing low-level composition/payload/bundle tools into
one normal release command.  This module does not reimplement composition,
ext4 production, hardware-support packing or .greiaupdate validation: those
remain owned by their existing tools and libraries.

Normal owner flow::

    sudo python3 tools/greia_release.py build --version <VERSION> --output <DIR>

Session 03 intentionally emits only the currently-real Acer update bundle.
The final output directory/schema is already the multi-platform schema from the
active lifecycle plan; universal Setup media and additional target profiles are
added by later sessions without changing the owner-facing entry point.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
SRC_ROOT = PROJECT_ROOT / "src"
for _path in (str(TOOLS_ROOT), str(SRC_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from build_profile import BuildProfile, BuildProfileError  # noqa: E402
from greia_installer.layout import (  # noqa: E402
    LayoutError,
    ProfileSizing,
    minimum_device_bytes_for_profile,
)
from greia_platform.persistent_layout import PERSIST_SCHEMA_CURRENT  # noqa: E402

REPORT_SCHEMA_VERSION = 1
DEFAULT_PROFILE_IDS = ("acer-aspire-one-i386-ab",)
_VERSION_RE = re.compile(r"^[0-9][0-9A-Za-z._+-]{0,63}$")
_HASH_CHUNK_BYTES = 1024 * 1024

# Session 03 build-host contract.  Individual low-level tools still perform
# their own narrower probes; doctor is the owner-facing aggregate.
_REQUIRED_BUILD_COMMANDS = (
    "bash",
    "python3",
    "git",
    "debootstrap",
    "chroot",
    "mount",
    "umount",
    "mountpoint",
    "findmnt",
    "udevadm",
    "rsync",
    "dpkg-deb",
    "readelf",
    "mkfs.ext4",
    "e2fsck",
    "resize2fs",
    "debugfs",
    "zstd",
)


class ReleaseCliError(RuntimeError):
    """Owner-facing release orchestration failure."""


@dataclass(frozen=True, slots=True)
class CommandResult:
    stdout: str
    stderr: str
    returncode: int


class ReleaseCommandRunner(Protocol):
    def run(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str] | None = None,
        log_path: Path | None = None,
        capture: bool = False,
        interactive: bool = False,
    ) -> CommandResult: ...  # pragma: no cover


@dataclass(frozen=True, slots=True)
class SubprocessReleaseCommandRunner:
    """Real process seam.

    Long-running composition commands stream output to one build log instead of
    buffering debootstrap/chroot output in Python.  Small machine-readable
    helper commands opt into capture=True.
    """

    def run(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str] | None = None,
        log_path: Path | None = None,
        capture: bool = False,
        interactive: bool = False,
    ) -> CommandResult:
        argv = [str(item) for item in command]
        child_env = dict(os.environ)
        if env is not None:
            child_env.update({str(key): str(value) for key, value in env.items()})
        try:
            if capture:
                completed = subprocess.run(
                    argv,
                    cwd=str(cwd),
                    env=child_env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                    shell=False,
                )
                return CommandResult(
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                    returncode=completed.returncode,
                )

            if interactive:
                if log_path is not None:
                    raise ReleaseCliError(
                        "interactive release command cannot redirect to a build log"
                    )
                completed = subprocess.run(
                    argv,
                    cwd=str(cwd),
                    env=child_env,
                    stdin=None,
                    stdout=None,
                    stderr=None,
                    text=True,
                    check=False,
                    shell=False,
                )
                return CommandResult(
                    stdout="", stderr="", returncode=completed.returncode
                )

            if log_path is None:
                raise ReleaseCliError("non-captured release command requires a log path")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as log:
                log.write("\n$ " + " ".join(argv) + "\n")
                log.flush()
                completed = subprocess.run(
                    argv,
                    cwd=str(cwd),
                    env=child_env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                    shell=False,
                )
            return CommandResult(stdout="", stderr="", returncode=completed.returncode)
        except OSError as exc:
            raise ReleaseCliError(
                f"release command could not start ({argv[0] if argv else '?'}): {exc}"
            ) from exc


@dataclass(frozen=True, slots=True)
class ReleasePaths:
    output_parent: Path
    release_root: Path
    updates_dir: Path
    intermediate_dir: Path
    cache_dir: Path
    work_parent: Path

    @classmethod
    def for_release(cls, output_parent: Path, version: str) -> "ReleasePaths":
        parent = Path(output_parent).expanduser().resolve()
        release_root = parent / f"greia-{version}"
        return cls(
            output_parent=parent,
            release_root=release_root,
            updates_dir=release_root / "updates",
            intermediate_dir=release_root / "intermediate",
            cache_dir=parent / ".greia-cache",
            work_parent=parent / ".greia-work",
        )


@dataclass(frozen=True, slots=True)
class ProfilePlan:
    profile_id: str
    profile_path: Path
    platform_family: str
    architecture: str
    board: str | None
    suite: str
    build_image_bytes: int
    system_slot_bytes: int
    persistent_minimum_bytes: int
    minimum_device_bytes: int


def _profile_path(profile_id: str) -> Path:
    path = PROJECT_ROOT / "build" / "profiles" / f"{profile_id}.toml"
    if not path.is_file():
        raise ReleaseCliError(f"release profile is missing: {path}")
    return path.resolve()


def _load_profile_plan(profile_id: str) -> tuple[BuildProfile, ProfilePlan]:
    path = _profile_path(profile_id)
    try:
        profile = BuildProfile.load(path)
        # Resolve both package scopes now so missing package-set files fail
        # before any root composition begins.
        package_root = PROJECT_ROOT / "build" / "package-sets"
        profile.resolve_packages(package_root, "target")
        profile.resolve_packages(package_root, "installer")
        profile.check_phase0_builder_support("target")
        profile.check_phase0_builder_support("installer")
    except (BuildProfileError, LayoutError) as exc:
        raise ReleaseCliError(f"release profile is invalid: {exc}") from exc
    board = None if profile.platform.board == "none" else profile.platform.board
    minimum = minimum_device_bytes_for_profile(
        ProfileSizing(
            layout_adapter_id=profile.storage.layout_adapter,
            slot_bytes=profile.storage.system_slot_bytes,
            persist_minimum_bytes=profile.storage.persistent_minimum_bytes,
            boot_backend=profile.updates.boot_backend,
        )
    )
    plan = ProfilePlan(
        profile_id=profile.identity.profile_id,
        profile_path=path,
        platform_family=profile.platform.family,
        architecture=profile.base.architecture,
        board=board,
        suite=profile.base.suite,
        build_image_bytes=profile.image.size_mib * 1024 * 1024,
        system_slot_bytes=profile.storage.system_slot_bytes,
        persistent_minimum_bytes=profile.storage.persistent_minimum_bytes,
        minimum_device_bytes=minimum,
    )
    return profile, plan


def _validate_version(version: str) -> str:
    if not isinstance(version, str) or not _VERSION_RE.fullmatch(version):
        raise ReleaseCliError(
            "version must start with a digit and contain only letters, digits, . _ + -"
        )
    version_file = PROJECT_ROOT / "VERSION"
    try:
        repository_version = version_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ReleaseCliError(f"cannot read repository VERSION: {exc}") from exc
    if version != repository_version:
        raise ReleaseCliError(
            f"requested version {version!r} does not match repository VERSION "
            f"{repository_version!r}; update VERSION first so root metadata and "
            "release bundle cannot disagree"
        )
    return version


def _tree_bytes(root: Path) -> int:
    total = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(dirpath)
        # Never traverse symlink directories.
        dirnames[:] = [
            name for name in dirnames if not (base / name).is_symlink()
        ]
        for name in filenames:
            path = base / name
            if path.is_symlink():
                continue
            try:
                total += path.stat().st_size
            except OSError as exc:
                raise ReleaseCliError(f"cannot measure build tree {path}: {exc}") from exc
    return total


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as handle:
            while True:
                chunk = handle.read(_HASH_CHUNK_BYTES)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        raise ReleaseCliError(f"cannot hash artifact {path}: {exc}") from exc
    return digest.hexdigest()


def _json_result(result: CommandResult, label: str) -> dict[str, object]:
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        suffix = f": {detail}" if detail else ""
        raise ReleaseCliError(f"{label} failed{suffix}")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ReleaseCliError(f"{label} did not return JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseCliError(f"{label} returned a non-object JSON result")
    return value


def _stable_producer_facts(document: Mapping[str, object]) -> dict[str, object]:
    """Drop low-level scratch output paths before the atomic publish rename."""

    return {
        key: value
        for key, value in document.items()
        if key not in {"output", "receipt_output"}
    }


def _run_checked(
    runner: ReleaseCommandRunner,
    command: Sequence[str],
    *,
    env: Mapping[str, str],
    log_path: Path,
    label: str,
) -> None:
    result = runner.run(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        log_path=log_path,
        capture=False,
    )
    if result.returncode != 0:
        raise ReleaseCliError(
            f"{label} failed with exit {result.returncode}; see {log_path}"
        )


def _run_json(
    runner: ReleaseCommandRunner,
    command: Sequence[str],
    *,
    env: Mapping[str, str],
    label: str,
) -> dict[str, object]:
    result = runner.run(command, cwd=PROJECT_ROOT, env=env, capture=True)
    return _json_result(result, label)


def _discover_boot_pair(target_root: Path) -> tuple[Path, Path]:
    boot = target_root / "boot"
    kernels = sorted(
        path for path in boot.glob("vmlinuz-*")
        if path.is_file() and not path.is_symlink() and path.name != "vmlinuz-generic"
    )
    initramfs = sorted(
        path for path in boot.glob("initrd.img-*")
        if path.is_file() and not path.is_symlink() and path.name != "initrd-generic"
    )
    pairs: list[tuple[Path, Path]] = []
    by_suffix = {path.name.removeprefix("initrd.img-"): path for path in initramfs}
    for kernel in kernels:
        suffix = kernel.name.removeprefix("vmlinuz-")
        candidate = by_suffix.get(suffix)
        if candidate is not None:
            pairs.append((kernel, candidate))
    if len(pairs) != 1:
        raise ReleaseCliError(
            "composed target root must contain exactly one matching "
            "boot/vmlinuz-* + boot/initrd.img-* pair; "
            f"found {len(pairs)}"
        )
    return pairs[0]


def _existing_filesystem_path(path: Path) -> Path:
    """Return path or its nearest existing parent for disk-usage probing."""

    candidate = Path(path).expanduser().resolve()
    while not candidate.exists():
        parent = candidate.parent
        if parent == candidate:
            raise ReleaseCliError(
                f"cannot find an existing filesystem parent for {path}"
            )
        candidate = parent
    return candidate


def _doctor(
    profile_ids: Sequence[str],
    *,
    system_name: str | None = None,
    machine: str | None = None,
    euid: int | None = None,
    which: Callable[[str], str | None] = shutil.which,
    disk_free_bytes: int | None = None,
    workspace_path: Path = PROJECT_ROOT,
) -> dict[str, object]:
    actual_system = platform.system() if system_name is None else system_name
    actual_machine = platform.machine() if machine is None else machine
    actual_euid = (os.geteuid() if hasattr(os, "geteuid") else -1) if euid is None else euid
    checks: list[dict[str, object]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add(
        "host-os",
        actual_system == "Linux",
        f"required=Linux observed={actual_system}",
    )
    add(
        "host-architecture",
        actual_machine in {"x86_64", "amd64"},
        f"required=x86_64 observed={actual_machine}",
    )
    add(
        "root",
        actual_euid == 0,
        f"required=euid0 observed={actual_euid}",
    )
    missing = [name for name in _REQUIRED_BUILD_COMMANDS if which(name) is None]
    add(
        "commands",
        not missing,
        "all required commands present" if not missing else "missing: " + ", ".join(missing),
    )

    profile_details: list[dict[str, object]] = []
    for profile_id in profile_ids:
        try:
            profile, plan = _load_profile_plan(profile_id)
            profile_details.append(
                {
                    **asdict(plan),
                    "profile_path": str(plan.profile_path),
                    "certification_state": profile.identity.certification_state,
                    "ok": True,
                }
            )
        except (ReleaseCliError, ValueError) as exc:
            profile_details.append(
                {"profile_id": profile_id, "ok": False, "error": str(exc)}
            )
    add(
        "profiles",
        all(bool(item.get("ok")) for item in profile_details),
        f"{sum(bool(item.get('ok')) for item in profile_details)}/{len(profile_details)} valid",
    )

    valid_profiles = [item for item in profile_details if bool(item.get("ok"))]
    if valid_profiles:
        # Conservative build-work floor derived from product/profile facts:
        # installed-layout minimum + two root working copies at the declared
        # build-image ceiling + one full slot image while shrink/compression is
        # in flight. This is a preflight floor, not a final-media-size claim;
        # low-level producers retain their exact allocation/capacity checks.
        required_workspace = max(
            int(item["minimum_device_bytes"])
            + 2 * int(item["build_image_bytes"])
            + int(item["system_slot_bytes"])
            for item in valid_profiles
        )
        measured_at = _existing_filesystem_path(Path(workspace_path))
        free_bytes = (
            shutil.disk_usage(measured_at).free
            if disk_free_bytes is None
            else int(disk_free_bytes)
        )
        add(
            "workspace",
            free_bytes >= required_workspace,
            (
                f"required>={required_workspace} free={free_bytes} "
                f"filesystem={measured_at}"
            ),
        )

    return {
        "schema_version": 1,
        "ok": all(bool(item["ok"]) for item in checks),
        "checks": checks,
        "profiles": profile_details,
    }


def _release_environment(paths: ReleasePaths) -> dict[str, str]:
    paths.cache_dir.mkdir(parents=True, exist_ok=True)
    apt_cache = paths.cache_dir / "apt"
    pool_cache = paths.cache_dir / "pool"
    apt_cache.mkdir(parents=True, exist_ok=True)
    pool_cache.mkdir(parents=True, exist_ok=True)
    return {
        "GREIA_APT_CACHE": str(apt_cache),
        "GREIA_POOL_CACHE": str(pool_cache),
    }


def _build_one_profile(
    *,
    runner: ReleaseCommandRunner,
    plan: ProfilePlan,
    version: str,
    release_id: str,
    work_root: Path,
    publish_root: Path,
    env: Mapping[str, str],
    release_notes_file: Path | None,
) -> dict[str, object]:
    profile_work = work_root / plan.profile_id
    target_root = profile_work / "target-root"
    live_root = profile_work / "live-root"
    target_root.mkdir(parents=True, exist_ok=False)
    live_root.mkdir(parents=True, exist_ok=False)

    log_path = profile_work / "build.log"
    intermediate = publish_root / "intermediate" / plan.profile_id
    updates = publish_root / "updates"
    intermediate.mkdir(parents=True, exist_ok=True)
    updates.mkdir(parents=True, exist_ok=True)

    compose_adapter = PROJECT_ROOT / "build" / "compose-release-profile.sh"
    _run_checked(
        runner,
        [
            "bash",
            str(compose_adapter),
            str(plan.profile_path),
            str(target_root),
            str(live_root),
        ],
        env=env,
        log_path=log_path,
        label=f"{plan.profile_id} release-root composition",
    )

    kernel, initramfs = _discover_boot_pair(target_root)
    target_root_bytes = _tree_bytes(target_root)
    live_root_bytes = _tree_bytes(live_root)

    payload = intermediate / "payload.ext4.zst"
    receipt = intermediate / "payload-receipt.json"
    payload_doc = _run_json(
        runner,
        [
            sys.executable,
            str(PROJECT_ROOT / "tools" / "build_release.py"),
            "build-payload",
            "--staging-dir",
            str(target_root),
            "--kernel",
            str(kernel),
            "--initramfs",
            str(initramfs),
            "--output",
            str(payload),
            "--profile-id",
            plan.profile_id,
            "--release-id",
            release_id,
            # Use the real destination slot as the populate ceiling.  The
            # producer shrinks the ext4 and derives the actual manifest
            # minimum afterwards; no operator-entered size survives.
            "--filesystem-bytes",
            str(plan.system_slot_bytes),
            "--receipt-output",
            str(receipt),
        ],
        env=env,
        label=f"{plan.profile_id} payload build",
    )
    _run_json(
        runner,
        [
            sys.executable,
            str(PROJECT_ROOT / "tools" / "build_release.py"),
            "verify-payload",
            "--payload",
            str(payload),
        ],
        env=env,
        label=f"{plan.profile_id} payload verification",
    )

    target_status = target_root / "var" / "lib" / "dpkg" / "status"
    if target_status.is_symlink() or not target_status.is_file():
        raise ReleaseCliError(
            f"{plan.profile_id} composed target is missing var/lib/dpkg/status"
        )
    pool_root = live_root / "opt" / "greia-hardware-support"
    if not (pool_root / "manifest.json").is_file():
        raise ReleaseCliError(
            f"{plan.profile_id} release composition did not produce hardware support"
        )
    hardware_support = intermediate / "hardware-support.tar.zst"
    hardware_doc = _run_json(
        runner,
        [
            sys.executable,
            str(PROJECT_ROOT / "tools" / "build_release.py"),
            "build-hardware-support",
            "--pool-root",
            str(pool_root),
            "--output",
            str(hardware_support),
        ],
        env=env,
        label=f"{plan.profile_id} hardware-support archive",
    )

    bundle = updates / f"{plan.profile_id}.greiaupdate"
    bundle_command = [
        sys.executable,
        str(PROJECT_ROOT / "tools" / "greia_update.py"),
        "build",
        "--payload",
        str(payload),
        "--payload-receipt",
        str(receipt),
        "--profile-file",
        str(plan.profile_path),
        "--hardware-support",
        str(hardware_support),
        "--version",
        version,
        "--release-id",
        release_id,
        "--persist-read-min",
        str(PERSIST_SCHEMA_CURRENT),
        "--persist-read-max",
        str(PERSIST_SCHEMA_CURRENT),
        "--persist-write",
        str(PERSIST_SCHEMA_CURRENT),
        "--output",
        str(bundle),
    ]
    if release_notes_file is not None:
        bundle_command.extend(["--release-notes-file", str(release_notes_file)])
    bundle_doc = _run_json(
        runner,
        bundle_command,
        env=env,
        label=f"{plan.profile_id} bundle build",
    )

    if not payload.is_file() or not receipt.is_file() or not hardware_support.is_file():
        raise ReleaseCliError(
            f"{plan.profile_id} low-level producer did not emit all intermediate artifacts"
        )
    if not bundle.is_file():
        raise ReleaseCliError(f"{plan.profile_id} bundle output is missing")
    durable_log = intermediate / "build.log"
    if log_path.is_file():
        shutil.copyfile(log_path, durable_log)
        os.chmod(durable_log, 0o644)

    return {
        "profile_id": plan.profile_id,
        "profile_path": str(plan.profile_path.relative_to(PROJECT_ROOT)),
        "platform_family": plan.platform_family,
        "architecture": plan.architecture,
        "board": plan.board,
        "build_image_bytes": plan.build_image_bytes,
        "system_slot_bytes": plan.system_slot_bytes,
        "persistent_minimum_bytes": plan.persistent_minimum_bytes,
        "minimum_device_bytes": plan.minimum_device_bytes,
        "target_root_bytes": target_root_bytes,
        "live_root_bytes": live_root_bytes,
        "payload": {
            "path": str(payload.relative_to(publish_root)),
            "compressed_bytes": payload.stat().st_size,
            "sha256": _sha256_file(payload),
            "producer": _stable_producer_facts(payload_doc),
        },
        "hardware_support": {
            "path": str(hardware_support.relative_to(publish_root)),
            "compressed_bytes": hardware_support.stat().st_size,
            "sha256": _sha256_file(hardware_support),
            "producer": _stable_producer_facts(hardware_doc),
        },
        "bundle": {
            "path": str(bundle.relative_to(publish_root)),
            "bytes": bundle.stat().st_size,
            "sha256": _sha256_file(bundle),
            "manifest": _stable_producer_facts(bundle_doc),
        },
        "build_log": (
            str(durable_log.relative_to(publish_root))
            if durable_log.is_file()
            else None
        ),
    }


def _write_report(path: Path, report: dict[str, object]) -> None:
    encoded = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ReleaseCliError(f"release report already exists: {path}")
    path.write_bytes(encoded)
    os.chmod(path, 0o644)


def _build_release(
    *,
    version: str,
    output_parent: Path,
    profile_ids: Sequence[str],
    runner: ReleaseCommandRunner | None = None,
    keep_work: bool = False,
    release_notes_file: Path | None = None,
    doctor_result: dict[str, object] | None = None,
) -> dict[str, object]:
    version = _validate_version(version)
    if not profile_ids:
        raise ReleaseCliError("release matrix must contain at least one profile")
    active = runner if runner is not None else SubprocessReleaseCommandRunner()
    paths = ReleasePaths.for_release(output_parent, version)
    if paths.release_root.exists():
        raise ReleaseCliError(f"release output already exists: {paths.release_root}")
    paths.output_parent.mkdir(parents=True, exist_ok=True)
    paths.work_parent.mkdir(parents=True, exist_ok=True)

    if release_notes_file is not None:
        notes = Path(release_notes_file).expanduser().resolve()
        if notes.is_symlink() or not notes.is_file():
            raise ReleaseCliError("release notes file is not a regular file")
        release_notes_file = notes
    doctor = (
        _doctor(profile_ids, workspace_path=paths.output_parent)
        if doctor_result is None
        else doctor_result
    )
    if not bool(doctor["ok"]):
        failed = [
            str(item["name"])
            for item in doctor["checks"]  # type: ignore[index]
            if not bool(item["ok"])
        ]
        raise ReleaseCliError(
            "build-host doctor failed: " + ", ".join(failed)
        )

    plans = [_load_profile_plan(profile_id)[1] for profile_id in profile_ids]
    env = _release_environment(paths)
    work_root = Path(
        tempfile.mkdtemp(prefix=f"greia-{version}-", dir=str(paths.work_parent))
    )
    publish_root = work_root / "publish"
    publish_root.mkdir()
    success = False
    try:
        profiles = [
            _build_one_profile(
                runner=active,
                plan=plan,
                version=version,
                release_id=f"greia-{version}",
                work_root=work_root,
                publish_root=publish_root,
                env=env,
                release_notes_file=release_notes_file,
            )
            for plan in plans
        ]
        git_result = active.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            env=env,
            capture=True,
        )
        if git_result.returncode != 0:
            raise ReleaseCliError("cannot resolve release source commit")
        source_commit = git_result.stdout.strip()
        if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
            raise ReleaseCliError("release source commit is not a full git SHA")

        updates_total = _tree_bytes(publish_root / "updates")
        intermediate_total = _tree_bytes(publish_root / "intermediate")
        report: dict[str, object] = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "version": version,
            "release_id": f"greia-{version}",
            "source_commit": source_commit,
            "status": "complete",
            "profiles": profiles,
            "public_artifacts": [
                str(Path("updates") / f"{plan.profile_id}.greiaupdate")
                for plan in plans
            ],
            "setup_image": {
                "status": "deferred",
                "session": 8,
                "reason": "universal Setup image is not a Session 03 output",
            },
            "media_accounting": {
                "updates_total_bytes": updates_total,
                "intermediate_total_bytes": intermediate_total,
                "universal_setup_bytes": None,
            },
        }
        _write_report(publish_root / "release-report.json", report)
        publish_root.replace(paths.release_root)
        success = True
        return {
            **report,
            "output": str(paths.release_root),
        }
    except Exception as exc:
        if isinstance(exc, ReleaseCliError):
            raise ReleaseCliError(f"{exc}; preserved work: {work_root}") from exc
        raise ReleaseCliError(
            f"release build failed: {exc}; preserved work: {work_root}"
        ) from exc
    finally:
        if success and not keep_work:
            shutil.rmtree(work_root, ignore_errors=True)


def _inspect(path: Path, runner: ReleaseCommandRunner) -> dict[str, object]:
    target = Path(path).expanduser().resolve()
    if target.name == "release-report.json":
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ReleaseCliError(f"cannot read release report: {exc}") from exc
        if not isinstance(document, dict) or document.get("schema_version") != REPORT_SCHEMA_VERSION:
            raise ReleaseCliError("unsupported release-report.json schema")
        return document
    if target.suffix == ".greiaupdate":
        return _run_json(
            runner,
            [
                sys.executable,
                str(PROJECT_ROOT / "tools" / "greia_update.py"),
                "inspect",
                str(target),
            ],
            env={},
            label="bundle inspection",
        )
    raise ReleaseCliError("inspect expects release-report.json or a .greiaupdate bundle")


def _write_media(
    *,
    image: Path,
    device: str,
    erase_device: bool,
    expand_root: bool,
    runner: ReleaseCommandRunner,
) -> None:
    if not erase_device:
        raise ReleaseCliError("write-media requires explicit --erase-device")
    source = Path(image).expanduser().resolve()
    if source.is_symlink() or not source.is_file():
        raise ReleaseCliError("write-media image is not a regular file")
    if source.suffix != ".img":
        raise ReleaseCliError(
            "write-media currently accepts a raw .img only; compressed universal "
            "Setup media is added in its owning later session"
        )
    command = [
        "bash",
        str(PROJECT_ROOT / "build" / "write-image.sh"),
        str(source),
        device,
        "--erase-device",
    ]
    if expand_root:
        command.append("--expand-root")
    result = runner.run(
        command,
        cwd=PROJECT_ROOT,
        env={},
        capture=False,
        interactive=True,
    )
    if result.returncode != 0:
        raise ReleaseCliError(f"write-media failed with exit {result.returncode}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="build the complete current release matrix")
    build.add_argument("--version", required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--keep-work", action="store_true")
    build.add_argument("--release-notes-file", type=Path)

    profile = sub.add_parser("build-profile", help="build one release profile")
    profile.add_argument("profile", choices=DEFAULT_PROFILE_IDS)
    profile.add_argument("--version", required=True)
    profile.add_argument("--output", type=Path, required=True)
    profile.add_argument("--keep-work", action="store_true")
    profile.add_argument("--release-notes-file", type=Path)

    doctor = sub.add_parser("doctor", help="check the official build host")
    doctor.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT,
        help="Filesystem that will hold release work/output for space preflight.",
    )
    doctor.add_argument(
        "--profile",
        action="append",
        choices=DEFAULT_PROFILE_IDS,
        dest="profiles",
        help="profile to probe; repeatable (defaults to the current release matrix)",
    )

    inspect = sub.add_parser("inspect", help="inspect a release report or bundle")
    inspect.add_argument("path", type=Path)

    media = sub.add_parser("write-media", help="delegate safe raw-image writing")
    media.add_argument("image", type=Path)
    media.add_argument("device")
    media.add_argument("--erase-device", action="store_true")
    media.add_argument("--expand-root", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    runner = SubprocessReleaseCommandRunner()
    try:
        if args.command == "doctor":
            result = _doctor(
                tuple(args.profiles or DEFAULT_PROFILE_IDS),
                workspace_path=args.output.expanduser().resolve(),
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if bool(result["ok"]) else 2
        if args.command == "build":
            result = _build_release(
                version=args.version,
                output_parent=args.output,
                profile_ids=DEFAULT_PROFILE_IDS,
                runner=runner,
                keep_work=args.keep_work,
                release_notes_file=args.release_notes_file,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if args.command == "build-profile":
            result = _build_release(
                version=args.version,
                output_parent=args.output,
                profile_ids=(args.profile,),
                runner=runner,
                keep_work=args.keep_work,
                release_notes_file=args.release_notes_file,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if args.command == "inspect":
            print(json.dumps(_inspect(args.path, runner), indent=2, sort_keys=True))
            return 0
        if args.command == "write-media":
            _write_media(
                image=args.image,
                device=args.device,
                erase_device=args.erase_device,
                expand_root=args.expand_root,
                runner=runner,
            )
            return 0
    except ReleaseCliError as exc:
        print(f"greia-release: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
