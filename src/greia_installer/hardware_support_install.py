from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from .hardware_support import VerifiedHardwareSupportPool


class HardwareSupportInstallError(RuntimeError):
    pass


class HardwareSupportCommandRunner(Protocol):
    def run(self, command: Sequence[str], *, check: bool = True): ...


def detach_recorded_mounts(
    runner: HardwareSupportCommandRunner,
    mounted: list[Path],
    *,
    before: int = 0,
) -> tuple[Path, ...]:
    """Recursively detach the minimal roots added after before.

    Recursive bind mounts carry nested mounts such as dev/pts, and the support
    pool itself is nested below the recorded run bind. Cleanup therefore
    collapses the recorded slice to its minimal roots and recursively unmounts
    only those exact targets. Failed roots and their descendants remain tracked
    so callers cannot erase evidence or falsely report a clean slot.
    """
    added = list(mounted[before:])

    def _below(path: Path, parent: Path) -> bool:
        if path == parent:
            return False
        try:
            path.relative_to(parent)
        except ValueError:
            return False
        return True

    roots = [
        path
        for path in added
        if not any(_below(path, candidate) for candidate in added)
    ]
    failed_roots: list[Path] = []
    for mountpoint in reversed(roots):
        try:
            result = runner.run(
                ["umount", "--recursive", "--", str(mountpoint)], check=False
            )
        except Exception:
            failed_roots.append(mountpoint)
            continue
        if result is not None and getattr(result, "returncode", 0) != 0:
            failed_roots.append(mountpoint)

    if failed_roots:
        mounted[before:] = [
            path
            for path in added
            if any(path == root or _below(path, root) for root in failed_roots)
        ]
    else:
        del mounted[before:]
    return tuple(failed_roots)


#: RAM-backed scratch for the offline APT/dpkg transaction. ``mkinitramfs``
#: unpacks a large temporary module/firmware tree before compressing it; on
#: the 1,664 MiB Acer A/B slot that tree plus the apt archive cache can fill
#: the nearly-full target and abort ``update-initramfs`` with ENOSPC. Keep
#: these transient bytes out of the target slot; only the final compressed
#: initrd belongs there.
INSTALL_SCRATCH_REL_PATH = "run/greia-installer-scratch"
INSTALL_SCRATCH_TMPFS_OPTIONS = "size=256M,mode=1777"


def mount_install_scratch(
    root: Path, runner: HardwareSupportCommandRunner, mounted: list[Path]
) -> Path:
    """Mount a bounded RAM scratch area inside the target's already-mounted /run."""

    scratch = root / INSTALL_SCRATCH_REL_PATH
    scratch.mkdir(parents=True, exist_ok=True)
    runner.run(
        [
            "mount",
            "-t",
            "tmpfs",
            "-o",
            INSTALL_SCRATCH_TMPFS_OPTIONS,
            "tmpfs",
            str(scratch),
        ]
    )
    mounted.append(scratch)
    (scratch / "tmp").mkdir(mode=0o1777, exist_ok=True)
    (scratch / "apt").mkdir(mode=0o755, exist_ok=True)
    return scratch


def mount_chroot_filesystems(
    root: Path, runner: HardwareSupportCommandRunner, mounted: list[Path]
) -> None:
    """Mount the minimal Linux filesystems required by apt in a target chroot."""
    for name in ("dev", "proc", "sys", "run"):
        target = root / name
        target.mkdir(parents=True, exist_ok=True)
        if target in mounted:
            continue
        if name in {"dev", "sys", "run"}:
            runner.run(["mount", "--rbind", f"/{name}", str(target)])
            mounted.append(target)
            runner.run(["mount", "--make-rslave", str(target)])
        else:
            runner.run(["mount", "-t", "proc", "proc", str(target)])
            mounted.append(target)


@dataclass(slots=True)
class TargetHardwareSupportInstaller:
    """Install a verified machine-specific support plan into one mounted target.

    The caller owns the target/chroot lifecycle. The support pool is bind-mounted
    read-only into the target and appended to ``mounted`` immediately so the
    caller's existing reverse-order cleanup can always detach it.
    """

    runner: HardwareSupportCommandRunner

    def install(
        self,
        *,
        target_root: Path,
        pool: VerifiedHardwareSupportPool,
        packages: Sequence[str],
        mounted: list[Path],
    ) -> tuple[str, ...]:
        requested = pool.require_candidates(packages)
        if not requested:
            return ()

        mount_chroot_filesystems(target_root, self.runner, mounted)
        mount_install_scratch(target_root, self.runner, mounted)
        scratch_tmp = f"/{INSTALL_SCRATCH_REL_PATH}/tmp"
        scratch_apt = f"/{INSTALL_SCRATCH_REL_PATH}/apt"
        mountpoint = target_root / "run/greia-hardware-support"
        mountpoint.mkdir(parents=True, exist_ok=True)
        self.runner.run(["mount", "--bind", str(pool.root), str(mountpoint)])
        mounted.append(mountpoint)
        self.runner.run(["mount", "-o", "remount,bind,ro", str(mountpoint)])

        source = target_root / "run/greia-hardware-support.list"
        source.write_text(pool.apt_source_line + "\n", encoding="ascii")
        source.chmod(0o644)
        options = (
            "-o",
            "Dir::Etc::sourcelist=/run/greia-hardware-support.list",
            "-o",
            "Dir::Etc::sourceparts=-",
            "-o",
            f"Dir::Cache::archives={scratch_apt}",
            "-o",
            "APT::Get::List-Cleanup=0",
            "-o",
            "Acquire::Languages=none",
        )
        try:
            self.runner.run(
                ["chroot", str(target_root), "apt-get", *options, "update"]
            )
            self.runner.run(
                [
                    "chroot",
                    str(target_root),
                    "/usr/bin/env",
                    "DEBIAN_FRONTEND=noninteractive",
                    f"TMPDIR={scratch_tmp}",
                    "apt-get",
                    *options,
                    "install",
                    "-y",
                    "--no-install-recommends",
                    *requested,
                ]
            )
            self.runner.run(["chroot", str(target_root), "apt-get", "clean"])
        finally:
            source.unlink(missing_ok=True)
        return requested
