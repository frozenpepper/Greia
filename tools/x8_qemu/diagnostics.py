"""Read allowlisted diagnostics from a stopped disposable A/B image.

This command never boots or repairs the image. It attaches a regular image
read-only, mounts only the A, B and PERSIST partitions read-only with ext4
journal replay disabled, copies a small fixed set of files, then attempts
every owned unmount and the exact loop detach.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import platform
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Callable, Mapping

from greia_installer.disk import partition_number_path
from tools.x8_qemu.lifecycle import LifecycleHarnessError


MAX_FILE_BYTES: Mapping[str, int] = {
    "release_identity.json": 64 * 1024,
    "installed-layout.json": 16 * 1024,
    "boot-journal.json": 32 * 1024,
    "status.json": 32 * 1024,
    "phase-result.json": 8 * 1024,
    "service-diagnostics.txt": 64 * 1024,
}

PARTITIONS: tuple[tuple[str, int], ...] = (("A", 2), ("B", 3), ("PERSIST", 4))

ALLOWLIST: Mapping[str, tuple[tuple[str, str], ...]] = {
    "A": (("release_identity.json", "etc/greia-os/release-identity.json"),),
    "B": (("release_identity.json", "etc/greia-os/release-identity.json"),),
    "PERSIST": (
        (
            "installed-layout.json",
            "greia/namespaces/layout-authority/installed-layout.json",
        ),
        ("boot-journal.json", "greia/boot-journal/boot-journal.json"),
        (
            "status.json",
            "greia/namespaces/parent-credentials/system-updates/status.json",
        ),
        (
            "phase-result.json",
            "greia/namespaces/parent-credentials/x8-control/phase-result.json",
        ),
        (
            "service-diagnostics.txt",
            "greia/namespaces/parent-credentials/x8-control/service-diagnostics.txt",
        ),
    ),
}


def _read_allowlisted_file(root: Path, relative_path: str, limit: int) -> dict[str, object]:
    """Read one regular file beneath a mount root without following symlinks."""
    parts = Path(relative_path).parts
    if not parts or Path(relative_path).is_absolute() or any(part in ("", ".", "..") for part in parts):
        return {"status": "refused", "reason": "invalid allowlisted relative path"}

    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    parent_fd = os.open(root, directory_flags | nofollow)
    file_fd: int | None = None
    try:
        for component in parts[:-1]:
            next_fd = os.open(component, directory_flags | nofollow, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        try:
            file_fd = os.open(
                parts[-1], os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | nofollow,
                dir_fd=parent_fd,
            )
        except FileNotFoundError:
            return {"status": "missing"}
        info = os.fstat(file_fd)
        if not stat.S_ISREG(info.st_mode):
            return {"status": "refused", "reason": "allowlisted path is not a regular file"}
        if info.st_size > limit:
            return {
                "status": "oversized",
                "size_bytes": info.st_size,
                "limit_bytes": limit,
            }
        with os.fdopen(file_fd, "rb", closefd=True) as handle:
            file_fd = None
            raw = handle.read(limit + 1)
        if len(raw) > limit:
            return {"status": "oversized", "limit_bytes": limit}
    except FileNotFoundError:
        return {"status": "missing"}
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            return {"status": "refused", "reason": "symlink or non-directory path component"}
        return {"status": "unreadable", "reason": f"{type(exc).__name__}: {exc}"[:500]}
    finally:
        if file_fd is not None:
            os.close(file_fd)
        os.close(parent_fd)

    entry: dict[str, object] = {"status": "ok", "size_bytes": len(raw)}
    if relative_path.endswith(".json"):
        try:
            entry["json"] = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            entry["status"] = "invalid_json"
            entry["reason"] = f"{type(exc).__name__}: {exc}"[:300]
            entry["text_excerpt"] = raw[:2000].decode("utf-8", errors="replace")
    else:
        entry["text"] = raw.decode("utf-8", errors="replace")
    return entry


def _resolve_tools(which=None) -> dict[str, str]:
    from tools.x8_qemu.product import _require_loop_tools

    return _require_loop_tools("losetup", "mount", which=which)


def _run(argv: list[str], *, runner=None, what: str):
    from tools.x8_qemu.product import _run_checked

    return _run_checked(argv, runner=runner, timeout=120, what=what)


def collect_image_diagnostics(
    image_path: Path,
    *,
    runner=None,
    which=None,
    cleanup_fn: Callable[[tuple[Path, ...], str], object] | None = None,
    temp_parent: Path | None = None,
) -> dict[str, object]:
    """Collect fixed-path facts from an offline image; never infer health."""
    image = Path(image_path)
    try:
        info = image.lstat()
    except OSError as exc:
        raise LifecycleHarnessError(f"image is unavailable: {image}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise LifecycleHarnessError(f"image must be a regular non-symlink file: {image}")

    result: dict[str, object] = {
        "schema_version": 1,
        "classification": "DIAGNOSTIC_COLLECTION_ONLY",
        "health_acceptance": "NOT_EVALUATED",
        "image": {"path": str(image.resolve()), "size_bytes": info.st_size},
        "partitions": {},
        "errors": [],
        "cleanup": {"attempted": False, "loop_device": None},
    }
    errors = result["errors"]
    partitions = result["partitions"]
    cleanup = result["cleanup"]
    assert isinstance(errors, list) and isinstance(partitions, dict) and isinstance(cleanup, dict)

    loopdev = ""
    mountpoints: list[Path] = []
    base: Path | None = None
    try:
        tools = _resolve_tools(which)
        temporary = tempfile.mkdtemp(prefix="greia-x8-diagnostics-", dir=temp_parent)
        base = Path(temporary)
        mountpoints = [base / label.lower() for label, _number in PARTITIONS]
        for mountpoint in mountpoints:
            mountpoint.mkdir(mode=0o700)

        try:
            attached = _run(
                [
                    tools["losetup"], "--read-only", "--partscan", "--show",
                    "--find", str(image.resolve()),
                ],
                runner=runner,
                what=f"read-only loop attach for {image}",
            )
            loop_lines = str(getattr(attached, "stdout", "") or "").strip().splitlines()
            loopdev = loop_lines[0].strip() if len(loop_lines) == 1 else ""
            if not re.fullmatch(r"/dev/loop\d+", loopdev):
                raise LifecycleHarnessError(
                    f"read-only loop attach returned an unexpected device node: {loopdev!r}"
                )
            cleanup["loop_device"] = loopdev
        except Exception as exc:
            errors.append({"stage": "loop_attach", "error": f"{type(exc).__name__}: {exc}"[:800]})
            return result

        for (label, number), mountpoint in zip(PARTITIONS, mountpoints):
            device = str(partition_number_path(Path(loopdev), number))
            entry: dict[str, object] = {"partition_number": number, "device": device}
            partitions[label] = entry
            try:
                _run(
                    [
                        tools["mount"], "-t", "ext4", "-o", "ro,noload", "--",
                        device, str(mountpoint),
                    ],
                    runner=runner,
                    what=f"read-only {label} mount",
                )
            except Exception as exc:
                entry["mount"] = "failed"
                entry["mount_error"] = f"{type(exc).__name__}: {exc}"[:800]
                errors.append({"stage": "mount", "partition": label, "error": entry["mount_error"]})
                continue

            entry["mount"] = "ok"
            files: dict[str, object] = {}
            entry["files"] = files
            for name, relative_path in ALLOWLIST[label]:
                files[name] = {
                    "path": relative_path,
                    **_read_allowlisted_file(mountpoint, relative_path, MAX_FILE_BYTES[name]),
                }
    except Exception as exc:
        errors.append({"stage": "collection", "error": f"{type(exc).__name__}: {exc}"[:800]})
    finally:
        cleanup["attempted"] = True
        try:
            if cleanup_fn is None:
                from tools.x8_qemu.product import _cleanup_loop_mounts

                cleaned = _cleanup_loop_mounts(tuple(mountpoints), loopdev, runner=runner)
            else:
                cleaned = cleanup_fn(tuple(mountpoints), loopdev)
            if cleaned is False:
                raise LifecycleHarnessError("owned loop cleanup did not complete")
            if base is not None:
                base.rmdir()
            cleanup["status"] = "ok"
        except Exception as exc:
            cleanup["status"] = "failed"
            cleanup["error"] = f"{type(exc).__name__}: {exc}"[:800]
            errors.append({"stage": "cleanup", "error": cleanup["error"]})
    return result


def _write_result(output_dir: Path, result: dict[str, object]) -> Path:
    """Create one new private output directory and atomically write JSON."""
    output = Path(output_dir)
    if output.exists() and (output.is_symlink() or not output.is_dir()):
        raise LifecycleHarnessError(f"output must be a directory, not a symlink/file: {output}")
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = output / "diagnostics.json"
    if target.exists() or target.is_symlink():
        raise LifecycleHarnessError(f"refusing to overwrite diagnostic output: {target}")
    temporary = output / ".diagnostics.json.tmp"
    payload = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        directory_fd = os.open(output, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path, help="stopped regular raw image")
    parser.add_argument("--output", required=True, type=Path, help="new directory for diagnostics.json")
    args = parser.parse_args(argv)
    if sys.platform != "linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        parser.error("offline image collection requires a Linux x86_64 host")
    if os.geteuid() != 0:
        parser.error("offline image collection requires root on the Linux host")
    try:
        result = collect_image_diagnostics(args.image)
        target = _write_result(args.output, result)
    except LifecycleHarnessError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"diagnostics written: {target}", file=sys.stderr)
    errors = result.get("errors")
    cleanup = result.get("cleanup")
    if errors or (isinstance(cleanup, dict) and cleanup.get("status") != "ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
