from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from .hardware_support import VerifiedHardwareSupportPool


class HardwareSupportInstallError(RuntimeError):
    pass


class HardwareSupportCommandRunner(Protocol):
    def run(self, command: Sequence[str], *, check: bool = True): ...


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
