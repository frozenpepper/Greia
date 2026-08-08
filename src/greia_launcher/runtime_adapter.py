from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from greia_platform.activities import ActivityManifest


PRODUCTION_ROOT = Path("/opt/greia-os")


@dataclass(frozen=True, slots=True)
class RuntimeCommand:
    command: tuple[str, ...]
    cwd: Path


@dataclass(frozen=True, slots=True)
class RuntimeLifecycleSupport:
    """Optional lifecycle features exposed by one runtime family.

    READY/STOP/TERMINATE are universal Greia lifecycle primitives. Pause and
    checkpoint are explicitly optional so the platform never assumes a runtime
    can suspend or serialize execution merely because another runtime can.
    """

    pause: bool = False
    checkpoint: bool = False


class RuntimeLaunchAdapter(Protocol):
    """Minimal R2 runtime seam.

    Runtime adapters provide only the runtime-specific child command here.
    Activity authority, sandboxing, lifecycle, storage, sessions and progression
    remain Greia platform concerns. R6 deliberately expands this protocol when a
    second runtime needs validation/SDK/surface integration.
    """

    runtime_type: str
    lifecycle_support: RuntimeLifecycleSupport

    def command_for(self, manifest: ActivityManifest) -> RuntimeCommand: ...


class PythonRuntimeAdapter:
    runtime_type = "python"
    lifecycle_support = RuntimeLifecycleSupport()

    def __init__(self, python_executable: Path | None = None):
        self._python_executable = python_executable

    def command_for(self, manifest: ActivityManifest) -> RuntimeCommand:
        return RuntimeCommand(
            command=(str(self.resolve_interpreter()), str(manifest.launch_path)),
            cwd=manifest.root,
        )

    def resolve_interpreter(self) -> Path:
        if self._python_executable is not None:
            return self._python_executable
        configured = os.environ.get("GREIA_CHILD_PYTHON")
        if configured:
            return Path(configured)
        installed_root = Path(
            os.environ.get("GREIA_OS_ROOT", str(PRODUCTION_ROOT))
        ).resolve()
        system_python = Path("/usr/bin/python3")
        if installed_root == PRODUCTION_ROOT and system_python.exists():
            return system_python
        return Path(sys.executable)
