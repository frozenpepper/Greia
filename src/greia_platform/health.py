from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .activities import ActivityRegistry


@dataclass(frozen=True, slots=True)
class SystemHealth:
    uptime_seconds: int
    memory_total_bytes: int
    memory_available_bytes: int
    disk_total_bytes: int
    disk_free_bytes: int
    runtime_api_version: str
    activities: tuple[str, ...]

    def as_json_dict(self) -> dict[str, object]:
        return asdict(self)


def collect_health(
    registry: ActivityRegistry | None,
    runtime_api_version: str,
    storage_path: Path = Path("/"),
) -> SystemHealth:
    mem_total, mem_avail = _read_memory()
    disk = os.statvfs(storage_path)
    return SystemHealth(
        uptime_seconds=int(_read_uptime()),
        memory_total_bytes=mem_total,
        memory_available_bytes=mem_avail,
        disk_total_bytes=disk.f_blocks * disk.f_frsize,
        disk_free_bytes=disk.f_bavail * disk.f_frsize,
        runtime_api_version=runtime_api_version,
        activities=(
            tuple(item.activity_id for item in registry.discover())
            if registry is not None
            else ()
        ),
    )


def installed_os_identity(
    build_info: Path = Path("/etc/greia-os/build-info"),
    image_profile: Path = Path("/etc/greia-os/image-profile.json"),
    release_identity: Path = Path("/etc/greia-os/release-identity.json"),
) -> dict[str, object]:
    """Return the installed release identity used by Parent update clients.

    Finalized A/B installations use the updater's canonical release/layout
    resolver. Older single-root images fall back to their build-info and image
    profile records, which are the only identity facts those images contain.
    """
    values: dict[str, str] = {}
    try:
        for line in build_info.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                name, raw = line.split("=", 1)
                values[name.strip()] = raw.strip().strip('"')
    except OSError:
        pass
    release: dict[str, object] | None = None
    installed = None
    identity_error = None
    from .system_updates import (
        UpdateLayoutError,
        load_installed_release_identity,
        resolve_installed_system_identity,
    )

    try:
        release = load_installed_release_identity(release_identity)
        installed = resolve_installed_system_identity(
            release_identity_path=release_identity,
            image_profile_path=image_profile,
        )
    except (OSError, ValueError, UpdateLayoutError) as exc:
        # A present but invalid finalized identity must not be disguised by
        # the weaker build-info fallback.
        identity_error = "installed release identity is unavailable"

    has_release_identity = release is not None

    def _resolved(value: object) -> str | None:
        return value if isinstance(value, str) and value and value != "unknown" else None

    profile = _resolved(getattr(installed, "profile", None))
    platform_family = _resolved(getattr(installed, "platform_family", None))
    architecture = _resolved(getattr(installed, "architecture", None))
    version = _resolved(getattr(installed, "version", None))
    board = _resolved(getattr(installed, "board", None))
    if not has_release_identity and identity_error is None:
        version = version or values.get("GREIA_OS_VERSION")
        profile = profile or values.get("PIP_BUILD_PROFILE")
        platform_family = platform_family or values.get("PIP_PLATFORM_FAMILY")
        # The installed profile manifest remains the compatibility authority
        # when the old build-info record predates finalized release identity.
        try:
            import json

            profile_document = json.loads(image_profile.read_text(encoding="utf-8"))
            base = profile_document.get("base", {}) if isinstance(profile_document, dict) else {}
            if architecture is None and isinstance(base, dict):
                candidate = base.get("architecture")
                architecture = candidate if isinstance(candidate, str) and candidate else None
        except (OSError, ValueError, AttributeError):
            pass
        architecture = architecture or values.get("PIP_BUILD_ARCHITECTURE")

    channel = os.environ.get("GREIA_SYSTEM_UPDATE_CHANNEL", "stable").strip()
    if channel not in {"stable", "dev"}:
        channel = values.get("GREIA_UPDATE_CHANNEL")
    if channel not in {"stable", "dev"}:
        channel = None

    return {
        "version": version,
        "release_id": (
            release.get("release_id")
            if isinstance(release, dict)
            else values.get("GREIA_RELEASE_ID") if identity_error is None else None
        ),
        "profile": profile,
        "platform_family": platform_family,
        "architecture": architecture,
        "board": board or (values.get("GREIA_SYSTEM_BOARD") if identity_error is None else None),
        "channel": channel,
        "current_slot": release.get("slot") if isinstance(release, dict) else None,
        "build_phase": values.get("PIP_BUILD_PHASE"),
        "identity_error": identity_error,
    }


def _read_memory() -> tuple[int, int]:
    # 1. Try Linux /proc/meminfo
    try:
        values: dict[str, int] = {}
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            name, raw = line.split(":", 1)
            number = raw.strip().split()[0]
            values[name] = int(number)
        if "MemTotal" in values:
            total = values["MemTotal"] * 1024
            avail = values.get("MemAvailable", values.get("MemFree", 0)) * 1024
            return total, avail
    except (OSError, ValueError, IndexError):
        pass

    # 2. Try macOS sysconf + vm_stat fallback
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        phys_pages = os.sysconf("SC_PHYS_PAGES")
        total = page_size * phys_pages
        try:
            import subprocess

            out = subprocess.check_output(["vm_stat"], text=True, timeout=2)
            stats: dict[str, int] = {}
            for line in out.splitlines():
                parts = line.strip().split(":")
                if len(parts) == 2:
                    k = parts[0].strip().strip('"')
                    v = parts[1].strip().rstrip(".")
                    if v.isdigit():
                        stats[k] = int(v)
            free_pages = (
                stats.get("Pages free", 0)
                + stats.get("Pages inactive", 0)
                + stats.get("Pages speculative", 0)
            )
            avail = free_pages * page_size
            return total, min(total, avail)
        except Exception:
            return total, total
    except (AttributeError, OSError, ValueError):
        pass

    return 0, 0


def _read_uptime() -> float:
    try:
        return float(Path("/proc/uptime").read_text(encoding="ascii").split()[0])
    except (OSError, ValueError, IndexError):
        return time.monotonic()
