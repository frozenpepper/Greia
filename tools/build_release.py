#!/usr/bin/env python3
"""Deterministic Greia release builder (L7-RELEASE, R0/R1 source gate).

Builds the v2 release inputs without partition/boot writes:
- persistent-state-contract.json (deterministic canonical JSON);
- hardware-support.tar.zst (deterministic tar.zst from a verified pool);
- payload.bin (deterministic relocatable slot image from a staging dir);
- read-only payload verification (header + required Greia paths).

No privileged operations, no network, no key generation. Missing production
keys are a hard failure in the bundle step (see system_updates).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from greia_installer.hardware_support import VerifiedHardwareSupportPool
from greia_platform.system_updates import (
    MAX_HARDWARE_SUPPORT_BYTES,
    MAX_PAYLOAD_BYTES,
    build_persistent_state_contract_bytes,
    verify_persistent_state_contract_bytes,
)

PAYLOAD_MAGIC = b"GREIA-SLOT-V1\n"
PAYLOAD_HEADER_SIZE = 4096
PAYLOAD_MIN_HEADROOM = 1024 * 1024
REQUIRED_PAYLOAD_PATHS = (
    "etc/greia-os/build-info",
    "opt/greia-os/src",
    "boot/vmlinuz-generic",
    "boot/initrd-generic",
)
_ALLOWED_POOL_TOP = frozenset({"manifest.json", "Packages", "Packages.gz"})


class ReleaseBuildError(RuntimeError):
    pass


def build_persistent_contract(output: Path) -> bytes:
    raw = build_persistent_state_contract_bytes()
    verify_persistent_state_contract_bytes(raw)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ReleaseBuildError(f"output already exists: {output}")
    output.write_bytes(raw)
    os.chmod(output, 0o644)
    return raw


def _pool_layout(pool_root: Path) -> tuple[Path, list[Path]]:
    root = pool_root.resolve()
    manifest = root / "manifest.json"
    if manifest.is_symlink() or not manifest.is_file():
        raise ReleaseBuildError("hardware-support pool manifest is missing or unsafe")
    pool_dir = root / "pool"
    if pool_dir.is_symlink() or not pool_dir.is_dir():
        raise ReleaseBuildError("hardware-support pool directory is invalid")
    debs = sorted(pool_dir.glob("*.deb"))
    return root, debs


def _assert_no_hooks(root: Path) -> None:
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ReleaseBuildError(f"hardware-support pool symlink is forbidden: {path.name}")
        if path.is_file():
            if path.suffix in {".sh", ".hook"}:
                raise ReleaseBuildError(f"unexpected executable hook: {path.name}")
            try:
                mode = path.stat().st_mode
            except OSError as exc:
                raise ReleaseBuildError("unable to stat pool member") from exc
            if mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                raise ReleaseBuildError(f"unexpected executable bit: {path.name}")
    top_files = {p.name for p in root.iterdir() if p.is_file() or p.is_symlink()}
    unexpected = top_files - _ALLOWED_POOL_TOP
    if unexpected:
        raise ReleaseBuildError(f"unexpected pool top-level files: {sorted(unexpected)}")


def build_hardware_support_set(
    pool_root: Path, output: Path, *, max_bytes: int = MAX_HARDWARE_SUPPORT_BYTES
) -> dict[str, object]:
    pool = VerifiedHardwareSupportPool.load(pool_root)
    if pool.total_bytes > max_bytes:
        raise ReleaseBuildError("hardware-support pool exceeds release byte bound")
    root, debs = _pool_layout(pool_root)
    _assert_no_hooks(root)
    members: list[Path] = [root / "manifest.json", root / "Packages", root / "Packages.gz"]
    members.extend(debs)
    for member in members:
        if member.is_symlink() or not member.is_file():
            raise ReleaseBuildError(f"hardware-support member is missing: {member.name}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ReleaseBuildError(f"output already exists: {output}")
    zstd = shutil.which("zstd")
    if zstd is None:
        raise ReleaseBuildError("zstd is required to build hardware-support.tar.zst")
    with tempfile.NamedTemporaryFile(prefix=".hwset.", suffix=".tar", delete=False) as handle:
        tar_tmp = Path(handle.name)
    try:
        with tar_tmp.open("wb") as raw:
            with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for member in sorted(members, key=lambda p: p.relative_to(root).as_posix()):
                    arcname = member.relative_to(root).as_posix()
                    info = tar.gettarinfo(str(member), arcname=arcname)
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    if info.isdir():
                        info.mode = 0o755
                    elif info.isfile():
                        info.mode = 0o644
                    else:
                        raise ReleaseBuildError(f"unsupported pool member type: {arcname}")
                    if info.issym() or info.islnk():
                        raise ReleaseBuildError(f"symlink archive member forbidden: {arcname}")
                    with member.open("rb") as src:
                        tar.addfile(info, src)
        completed = subprocess.run(
            [zstd, "-19", "-c", "--rm", str(tar_tmp)],
            check=False,
            capture_output=True,
            timeout=120,
            shell=False,
        )
        if completed.returncode != 0:
            raise ReleaseBuildError("zstd compression of hardware-support set failed")
        if not completed.stdout.startswith(b"\x28\xb5\x2f\xfd"):
            raise ReleaseBuildError("hardware-support compressor did not emit zstd bytes")
        with tempfile.NamedTemporaryFile(
            prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False
        ) as handle:
            tmp_out = Path(handle.name)
        try:
            tmp_out.write_bytes(completed.stdout)
            os.chmod(tmp_out, 0o644)
            if tmp_out.stat().st_size > max_bytes:
                raise ReleaseBuildError("hardware-support.tar.zst exceeds release byte bound")
            tmp_out.replace(output)
        finally:
            tmp_out.unlink(missing_ok=True)
    finally:
        tar_tmp.unlink(missing_ok=True)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {
        "output": str(output),
        "size": output.stat().st_size,
        "sha256": digest,
        "pool_suite": pool.suite,
        "pool_architecture": pool.architecture,
        "pool_total_bytes": pool.total_bytes,
    }


def _deterministic_tar_bytes(staging: Path) -> bytes:
    staging = staging.resolve()
    if not staging.is_dir():
        raise ReleaseBuildError("payload staging dir is missing")
    buffer = io.BytesIO()
    entries: list[Path] = []
    for path in sorted(staging.rglob("*"), key=lambda p: p.relative_to(staging).as_posix()):
        entries.append(path)
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for path in entries:
            arcname = path.relative_to(staging).as_posix()
            if path.is_symlink():
                raise ReleaseBuildError(f"payload staging symlink forbidden: {arcname}")
            info = tar.gettarinfo(str(path), arcname=arcname)
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = 0
            if info.isdir():
                info.mode = 0o755
                tar.addfile(info)
            elif info.isfile():
                info.mode = 0o644 if path.suffix != ".bin" else 0o644
                with path.open("rb") as src:
                    tar.addfile(info, src)
            else:
                raise ReleaseBuildError(f"unsupported staging member: {arcname}")
    return buffer.getvalue()


def _payload_header(*, profile_id: str, release_id: str, release_sequence: int) -> bytes:
    record = {
        "magic": "GREIA-SLOT-V1",
        "profile": profile_id,
        "release_id": release_id,
        "release_sequence": release_sequence,
    }
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(encoded) + 1 > PAYLOAD_HEADER_SIZE:
        raise ReleaseBuildError("release identity header does not fit")
    header = PAYLOAD_MAGIC + encoded + b"\n"
    header = header.ljust(PAYLOAD_HEADER_SIZE, b"\x00")
    if header[510:512] == b"\x55\xaa" or header[512:520] == b"EFI PART":
        raise ReleaseBuildError("payload header collides with partition magic")
    return header


def build_release_payload(
    *,
    staging_dir: Path,
    kernel_path: Path,
    initramfs_path: Path,
    output: Path,
    profile_id: str,
    release_id: str,
    release_sequence: int,
    filesystem_bytes: int,
    minimum_slot_bytes: int,
) -> dict[str, object]:
    staging = Path(staging_dir).resolve()
    kernel = Path(kernel_path)
    initramfs = Path(initramfs_path)
    for path, label in ((kernel, "kernel"), (initramfs, "initramfs")):
        if path.is_symlink() or not path.is_file():
            raise ReleaseBuildError(f"generic {label} input is not a regular file")
    if filesystem_bytes <= 0 or filesystem_bytes > MAX_PAYLOAD_BYTES:
        raise ReleaseBuildError("filesystem_bytes is outside Greia bounds")
    if minimum_slot_bytes < filesystem_bytes or minimum_slot_bytes > 2 * 1024 * 1024 * 1024:
        raise ReleaseBuildError("minimum_slot_bytes must cover filesystem_bytes")
    # Seed generic kernel/initramfs + release identity deterministically.
    boot_dir = staging / "boot"
    etc_dir = staging / "etc" / "greia-os"
    boot_dir.mkdir(parents=True, exist_ok=True)
    etc_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(kernel, boot_dir / "vmlinuz-generic")
    shutil.copyfile(initramfs, boot_dir / "initrd-generic")
    identity = {
        "profile": profile_id,
        "release_id": release_id,
        "release_sequence": release_sequence,
    }
    (etc_dir / "release-identity.json").write_text(
        json.dumps(identity, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    for required in REQUIRED_PAYLOAD_PATHS:
        candidate = staging / required
        if required.endswith("src"):
            if not candidate.is_dir():
                raise ReleaseBuildError(f"staging is missing required path: {required}")
        elif not candidate.is_file():
            raise ReleaseBuildError(f"staging is missing required path: {required}")
    body = _deterministic_tar_bytes(staging)
    header = _payload_header(
        profile_id=profile_id, release_id=release_id, release_sequence=release_sequence
    )
    if len(header) + len(body) + PAYLOAD_MIN_HEADROOM > filesystem_bytes:
        raise ReleaseBuildError("staging does not leave finalization headroom in filesystem_bytes")
    image = header + body
    image = image.ljust(filesystem_bytes, b"\x00")
    if image[510:512] == b"\x55\xaa" or image[512:520] == b"EFI PART":
        raise ReleaseBuildError("payload must stay relocatable without partition magic")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ReleaseBuildError(f"output already exists: {output}")
    output.write_bytes(image)
    os.chmod(output, 0o644)
    return {
        "output": str(output),
        "filesystem_bytes": filesystem_bytes,
        "minimum_slot_bytes": minimum_slot_bytes,
        "sha256": hashlib.sha256(image).hexdigest(),
    }


def verify_release_payload(payload: Path) -> dict[str, object]:
    path = Path(payload)
    if path.is_symlink() or not path.is_file():
        raise ReleaseBuildError("payload is not a regular file")
    with path.open("rb") as handle:
        header = handle.read(PAYLOAD_HEADER_SIZE)
        head_check = handle.read(1024)
    if not header.startswith(PAYLOAD_MAGIC):
        raise ReleaseBuildError("payload magic is invalid")
    if header[510:512] == b"\x55\xaa" or header[512:520] == b"EFI PART":
        raise ReleaseBuildError("payload carries a partition table; must be relocatable")
    # Read-only member listing of the deterministic tar body. Trailing zero
    # padding after the tar end-of-archive markers is expected (finalization
    # headroom) and is ignored by the tar reader; do not strip terminators.
    with path.open("rb") as handle:
        handle.seek(PAYLOAD_HEADER_SIZE)
        raw = handle.read()
    if not raw or not raw.strip(b"\x00"):
        raise ReleaseBuildError("payload body is empty")
    try:
        members: set[str] = set()
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r") as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    raise ReleaseBuildError("payload body symlink is forbidden")
                if member.name.startswith("/") or ".." in Path(member.name).parts:
                    raise ReleaseBuildError("payload body member is unsafe")
                members.add(member.name)
    except (tarfile.TarError, OSError) as exc:
        raise ReleaseBuildError("payload body is not a readable deterministic image") from exc
    missing = [p for p in REQUIRED_PAYLOAD_PATHS if not any(m == p or m.startswith(p.rstrip("src") if p.endswith("src") else p) for m in members)]
    # Directory prefix match for opt/greia-os/src (tar contains files beneath it).
    still_missing: list[str] = []
    for required in REQUIRED_PAYLOAD_PATHS:
        if required in members:
            continue
        if required == "opt/greia-os/src":
            if any(m.startswith("opt/greia-os/src/") for m in members):
                continue
        still_missing.append(required)
    if still_missing:
        raise ReleaseBuildError(f"payload is missing required Greia paths: {still_missing}")
    return {"payload": str(path), "size": path.stat().st_size, "members": len(members)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    contract = sub.add_parser("build-persistent-contract")
    contract.add_argument("--output", type=Path, required=True)
    hwset = sub.add_parser("build-hardware-support")
    hwset.add_argument("--pool-root", type=Path, required=True)
    hwset.add_argument("--output", type=Path, required=True)
    hwset.add_argument("--max-bytes", type=int, default=MAX_HARDWARE_SUPPORT_BYTES)
    payload = sub.add_parser("build-payload")
    payload.add_argument("--staging-dir", type=Path, required=True)
    payload.add_argument("--kernel", type=Path, required=True)
    payload.add_argument("--initramfs", type=Path, required=True)
    payload.add_argument("--output", type=Path, required=True)
    payload.add_argument("--profile-id", required=True)
    payload.add_argument("--release-id", required=True)
    payload.add_argument("--release-sequence", type=int, required=True)
    payload.add_argument("--filesystem-bytes", type=int, required=True)
    payload.add_argument("--minimum-slot-bytes", type=int, required=True)
    verify = sub.add_parser("verify-payload")
    verify.add_argument("--payload", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "build-persistent-contract":
            build_persistent_contract(args.output)
            print(json.dumps({"output": str(args.output)}, indent=2))
        elif args.command == "build-hardware-support":
            print(json.dumps(build_hardware_support_set(args.pool_root, args.output, max_bytes=args.max_bytes), indent=2))
        elif args.command == "build-payload":
            print(
                json.dumps(
                    build_release_payload(
                        staging_dir=args.staging_dir,
                        kernel_path=args.kernel,
                        initramfs_path=args.initramfs,
                        output=args.output,
                        profile_id=args.profile_id,
                        release_id=args.release_id,
                        release_sequence=args.release_sequence,
                        filesystem_bytes=args.filesystem_bytes,
                        minimum_slot_bytes=args.minimum_slot_bytes,
                    ),
                    indent=2,
                )
            )
        elif args.command == "verify-payload":
            print(json.dumps(verify_release_payload(args.payload), indent=2))
        else:  # pragma: no cover
            raise ReleaseBuildError(f"unknown command: {args.command}")
    except ReleaseBuildError as exc:
        print(f"build-release: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
