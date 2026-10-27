"""Build the one-time code-only receiver bridge from an exact installed base."""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

from .software_update_package import (
    SoftwareUpdatePackageError,
    SoftwareUpdatePackageManifest,
    ensure_software_update_filename,
    inspect_software_update_package,
)


BRIDGE_OVERLAY_PATHS = (
    "src/greia_platform/software_update_package.py",
    "src/greia_platform/software_update_generation.py",
)
ARCHIVE_ROOTS = (
    "src/greia_platform",
    "src/greia_launcher",
    "src/greia_parent",
    "src/greia_installer",
    "runtime",
)


def build_receiver_bridge(
    output_path: Path,
    *,
    base_ref: str,
    repository_root: Path,
    python_source_root: Path,
    version: str,
    release_id: str,
) -> tuple[str, SoftwareUpdatePackageManifest]:
    """Build a Python-only receiver update from a named Git base snapshot.

    The exported base is kept intact except for the two receiver modules which
    introduce JSON language-resource support. No current language data or
    launcher/registry code is overlaid, so the base can receive this ordinary
    v1 Python package before it receives a current complete snapshot.
    """
    repo = Path(repository_root).resolve(strict=True)
    source = Path(python_source_root).resolve(strict=True)
    if not repo.is_dir() or not source.is_dir():
        raise SoftwareUpdatePackageError("bridge repository and Python source roots must be directories")
    # Anchor relative output before the child changes cwd, without resolving
    # the final path component (the writer must still reject output symlinks).
    output = ensure_software_update_filename(Path(output_path)).absolute()
    base_sha = _resolve_commit(repo, base_ref)
    with tempfile.TemporaryDirectory(prefix="greia-update-bridge-") as temporary:
        workspace = Path(temporary)
        archive_path = workspace / "base.tar"
        _archive_base(repo, base_sha, archive_path)
        staged = workspace / "base"
        staged.mkdir()
        _extract_source_archive(archive_path, staged)
        for relative in BRIDGE_OVERLAY_PATHS:
            current = source / relative
            destination = staged / relative
            if current.is_symlink() or not current.is_file():
                raise SoftwareUpdatePackageError(f"bridge overlay source is not a regular file: {relative}")
            if destination.is_symlink() or not destination.is_file():
                raise SoftwareUpdatePackageError(f"base snapshot is missing bridge target: {relative}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(current.read_bytes())
        script = (
            "from pathlib import Path; import sys; "
            "from greia_platform.software_update_package_builder import build_software_update_package; "
            "build_software_update_package(Path(sys.argv[1]), version=sys.argv[2], "
            "release_id=sys.argv[3], python_source_root=Path(sys.argv[4]))"
        )
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(staged / "src")
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        result = _run_bounded(
            [sys.executable, "-c", script, str(output), version, release_id, str(staged)],
            cwd=staged,
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise SoftwareUpdatePackageError(
                "base-compatible bridge builder failed: " + (result.stderr.strip() or result.stdout.strip())
            )
        manifest = inspect_software_update_package(output).manifest
    return base_sha, manifest


def _resolve_commit(repository_root: Path, base_ref: str) -> str:
    if not isinstance(base_ref, str) or not base_ref or base_ref.startswith("-") or "\x00" in base_ref:
        raise SoftwareUpdatePackageError("bridge base ref is invalid")
    result = _run_bounded(
        ["git", "rev-parse", "--verify", f"{base_ref}^{{commit}}"],
        cwd=repository_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )
    commit = result.stdout.strip()
    if result.returncode != 0 or len(commit) not in (40, 64) or any(ch not in "0123456789abcdef" for ch in commit):
        raise SoftwareUpdatePackageError("bridge base ref does not resolve to a Git commit")
    return commit


def _archive_base(repository_root: Path, commit: str, archive_path: Path) -> None:
    result = _run_bounded(
        ["git", "archive", "--format=tar", "--output", str(archive_path), commit, *ARCHIVE_ROOTS],
        cwd=repository_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )
    if result.returncode != 0 or not archive_path.is_file():
        raise SoftwareUpdatePackageError("could not export bridge base source snapshot")


def _run_bounded(arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(arguments, **kwargs)  # type: ignore[arg-type]
    except subprocess.TimeoutExpired as exc:
        raise SoftwareUpdatePackageError("bridge source command exceeded its 60-second bound") from exc


def _extract_source_archive(archive_path: Path, destination: Path) -> None:
    """Extract only regular files/directories under the fixed source roots."""
    allowed = tuple(PurePosixPath(item) for item in ARCHIVE_ROOTS)
    try:
        with tarfile.open(archive_path, "r:") as archive:
            for member in archive:
                name = PurePosixPath(member.name)
                if name.is_absolute() or any(part in {"", ".", ".."} for part in name.parts):
                    raise SoftwareUpdatePackageError("bridge base archive contains an unsafe path")
                is_root_content = any(name == root or root in name.parents for root in allowed)
                is_root_ancestor = member.isdir() and any(root.parts[: len(name.parts)] == name.parts for root in allowed)
                if not is_root_content and not is_root_ancestor:
                    raise SoftwareUpdatePackageError("bridge base archive escaped its source roots")
                target = destination.joinpath(*name.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    stream = archive.extractfile(member)
                    if stream is None:
                        raise SoftwareUpdatePackageError("bridge base archive contains an unreadable file")
                    with stream, target.open("xb") as output:
                        while chunk := stream.read(1024 * 1024):
                            output.write(chunk)
                else:
                    raise SoftwareUpdatePackageError("bridge base archive contains a link or special file")
    except (OSError, tarfile.TarError) as exc:
        raise SoftwareUpdatePackageError("bridge base source archive is unreadable") from exc


__all__ = ["BRIDGE_OVERLAY_PATHS", "build_receiver_bridge"]
