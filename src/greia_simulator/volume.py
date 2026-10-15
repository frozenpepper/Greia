"""Synthetic child-data volume for the developer Simulator.

The real Shell composes the production ``VolumeBudget`` (75% used / 512 MiB
free) against the filesystem holding durable child data. On a developer
workstation that filesystem is the host disk, which is usually far fuller than
a family appliance, so the production policy would refuse every child-data
write and make the Simulator unusable. The Simulator therefore injects the same
policy over a *modelled* device volume: a fixed synthetic size, a fixed OS
baseline, plus the real bytes stored under the simulator workspace's child-data
root. Production composition is unchanged.
"""

from __future__ import annotations

import os
from pathlib import Path

from greia_platform.creation_capacity import VolumeBudget, VolumeUsage

# Close to the Acer Aspire One reference floor (about 7 GB storage).
DEFAULT_SIMULATED_VOLUME_BYTES = 8 * 1024**3
# Modelled immutable OS/Activity payload already occupying the volume.
DEFAULT_SIMULATED_OS_BASELINE_BYTES = 1024**3


class SimulatedVolumeProbe:
    """``VolumeBudget`` probe: ``used`` = OS baseline + bytes under ``data_root``."""

    def __init__(
        self,
        data_root: Path,
        *,
        total_bytes: int = DEFAULT_SIMULATED_VOLUME_BYTES,
        os_baseline_bytes: int = DEFAULT_SIMULATED_OS_BASELINE_BYTES,
    ) -> None:
        if total_bytes <= 0:
            raise ValueError("simulated volume size must be positive")
        if not 0 <= os_baseline_bytes < total_bytes:
            raise ValueError("simulated OS baseline must fit inside the volume")
        self._data_root = data_root
        self._total_bytes = total_bytes
        self._os_baseline_bytes = os_baseline_bytes

    def __call__(self, managed_root: Path) -> VolumeUsage:
        del managed_root  # one synthetic volume holds every child-data root
        used = min(
            self._total_bytes,
            self._os_baseline_bytes + _tree_bytes(self._data_root),
        )
        return VolumeUsage(self._total_bytes, used, self._total_bytes - used)


def simulated_volume_budget(
    data_root: Path,
    *,
    total_bytes: int = DEFAULT_SIMULATED_VOLUME_BYTES,
    os_baseline_bytes: int = DEFAULT_SIMULATED_OS_BASELINE_BYTES,
) -> VolumeBudget:
    """Production policy over the synthetic device volume."""

    return VolumeBudget(
        probe=SimulatedVolumeProbe(
            data_root,
            total_bytes=total_bytes,
            os_baseline_bytes=os_baseline_bytes,
        )
    )


def _tree_bytes(root: Path) -> int:
    """Sum regular-file sizes below ``root`` without following symlinks."""

    total = 0
    pending = [str(root)]
    while pending:
        try:
            with os.scandir(pending.pop()) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            pending.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total


__all__ = [
    "DEFAULT_SIMULATED_OS_BASELINE_BYTES",
    "DEFAULT_SIMULATED_VOLUME_BYTES",
    "SimulatedVolumeProbe",
    "simulated_volume_budget",
]
