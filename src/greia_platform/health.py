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
