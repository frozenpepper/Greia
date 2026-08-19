"""Simulator-only runtime variation below the canonical Greia composition seam."""

from __future__ import annotations

from pathlib import Path
import sys

from greia_launcher.runtime_adapter import (
    PythonRuntimeAdapter,
    RuntimeCommand,
)
from greia_platform.activities import ActivityManifest

from .device import SimulatedDeviceProfile


class SimulatorPythonRuntimeAdapter(PythonRuntimeAdapter):
    """Canonical Python runtime command wrapped by one trusted display bootstrap.

    Permission, storage, history, lifecycle and device-capability composition are
    intentionally not owned here. ``GreiaChildShell`` supplies this adapter to
    the normal launcher composition together with a synthetic HAL.
    """

    def __init__(
        self,
        device: SimulatedDeviceProfile,
        python_executable: Path | None = None,
        **kwargs,
    ) -> None:
        super().__init__(python_executable or Path(sys.executable), **kwargs)
        self._device = device
        self._bootstrap = Path(__file__).with_name("python_activity.py").resolve(strict=True)

    @property
    def bootstrap_path(self) -> Path:
        return self._bootstrap

    def command_for(self, manifest: ActivityManifest) -> RuntimeCommand:
        canonical = super().command_for(manifest)
        interpreter = canonical.command[0]
        return RuntimeCommand(
            command=(
                interpreter,
                str(self._bootstrap),
                "--viewport",
                self._device.viewport,
                str(manifest.launch_path),
            ),
            cwd=canonical.cwd,
            environment=canonical.environment,
        )


__all__ = ["SimulatorPythonRuntimeAdapter"]
