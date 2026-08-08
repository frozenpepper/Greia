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
    memory = _read_meminfo()
    disk = os.statvfs(storage_path)
    return SystemHealth(
        uptime_seconds=int(_read_uptime()),
        memory_total_bytes=memory.get("MemTotal", 0) * 1024,
        memory_available_bytes=memory.get("MemAvailable", memory.get("MemFree", 0)) * 1024,
        disk_total_bytes=disk.f_blocks * disk.f_frsize,
        disk_free_bytes=disk.f_bavail * disk.f_frsize,
        runtime_api_version=runtime_api_version,
        activities=(
            tuple(item.activity_id for item in registry.discover())
            if registry is not None
            else ()
        ),
    )


def _read_meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            name, raw = line.split(":", 1)
            number = raw.strip().split()[0]
            values[name] = int(number)
    except (OSError, ValueError, IndexError):
        pass
    return values


def _read_uptime() -> float:
    try:
        return float(Path("/proc/uptime").read_text(encoding="ascii").split()[0])
    except (OSError, ValueError, IndexError):
        return time.monotonic()
