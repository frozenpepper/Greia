from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .hardware import DisplayMode, HardwareSettings, HardwareSettingsStore


@dataclass(frozen=True, slots=True)
class DisplayProbe:
    """Semantic display facts used to validate bounded parent settings."""

    output_name: str | None
    modes: tuple[DisplayMode, ...]

    @property
    def allowed_mode_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(mode.mode_id for mode in self.modes))


@dataclass(frozen=True, slots=True)
class ApplyResult:
    applied: bool
    display: DisplayProbe
    messages: tuple[str, ...]


class HardwareSessionController(Protocol):
    """Backend-neutral display/input settings controller used by the watcher.

    Implementations translate Greia's bounded HardwareSettings into one concrete
    display/input backend. The generic watcher never selects a backend or knows
    backend-specific commands/property names.
    """

    @property
    def backend_id(self) -> str: ...

    def topology_token(self) -> tuple[str, ...]: ...

    def probe_display(self) -> DisplayProbe: ...

    def apply(self, settings: HardwareSettings) -> ApplyResult: ...


def run_watcher(
    store: HardwareSettingsStore,
    status_path: Path,
    *,
    controller: HardwareSessionController,
    interval_seconds: float = 0.5,
    once: bool = False,
) -> int:
    """Apply desired settings through the explicitly selected backend adapter."""

    backend_id = _backend_id(controller)
    last_settings_token: int | None = None
    last_topology_token: tuple[str, ...] | None = None
    next_topology_probe = 0.0
    retry_at = 0.0
    last_apply_succeeded = False
    while True:
        now = time.monotonic()
        settings_token = store.version_token()
        topology_token = last_topology_token
        if topology_token is None or now >= next_topology_probe:
            topology_token = controller.topology_token()
            next_topology_probe = now + 2.0
        should_apply = (
            settings_token != last_settings_token
            or topology_token != last_topology_token
            or (not last_apply_succeeded and now >= retry_at)
        )
        if should_apply:
            last_settings_token = settings_token
            last_topology_token = topology_token
            settings = store.read()
            display = controller.probe_display()
            try:
                store.validate(settings, allowed_resolutions=display.allowed_mode_ids)
                result = controller.apply(settings)
                last_apply_succeeded = result.applied
                retry_at = now + 2.0
                message = " ".join(result.messages)
                _write_status(
                    status_path,
                    settings,
                    result,
                    message,
                    backend_id=backend_id,
                )
            except Exception as exc:  # keep the child session alive on driver errors
                last_apply_succeeded = False
                retry_at = now + 2.0
                failed = ApplyResult(False, display, (_bounded_error(exc),))
                _write_status(
                    status_path,
                    settings,
                    failed,
                    _bounded_error(exc),
                    backend_id=backend_id,
                )
        if once:
            return 0
        time.sleep(interval_seconds)


def _backend_id(controller: HardwareSessionController) -> str:
    value = controller.backend_id
    if not isinstance(value, str):
        raise TypeError("hardware settings backend_id must be text")
    value = value.strip()
    if not value or len(value) > 64:
        raise ValueError("hardware settings backend_id must contain 1..64 characters")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
    if any(character not in allowed for character in value):
        raise ValueError("hardware settings backend_id contains unsupported characters")
    return value


def _write_status(
    path: Path,
    settings: HardwareSettings,
    result: ApplyResult,
    message: str,
    *,
    backend_id: str,
) -> None:
    payload = {
        "settings": settings.as_json_dict(),
        "applied": result.applied,
        "backend": backend_id,
        "display_output": result.display.output_name,
        "display_modes": [mode.as_json_dict() for mode in result.display.modes],
        "message": message,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o640)
    temporary.replace(path)


def _bounded_error(exc: Exception, maximum: int = 240) -> str:
    text = " ".join(str(exc).split())
    return (text or exc.__class__.__name__)[:maximum]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")),
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path(
            os.environ.get("GREIA_SYSTEM_SETTINGS_DIR", "/var/lib/greia-system-settings")
        ),
    )
    parser.add_argument(
        "--status-path",
        type=Path,
        default=Path("/run/greia-hardware/status.json"),
    )
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> int:
    # Production remains on the explicit legacy-X compatibility adapter during
    # R7. Keeping this import local prevents the generic watcher from acquiring
    # X-specific implementation dependencies while preserving today's boot path.
    from .hal_legacy_x import LegacyXHardwareSessionController

    args = parse_args()
    store = HardwareSettingsStore.load(
        args.root / "runtime" / "hardware-settings.toml",
        args.state_dir,
    )
    return run_watcher(
        store,
        args.status_path,
        controller=LegacyXHardwareSessionController(),
        once=args.once,
    )


if __name__ == "__main__":
    raise SystemExit(main())
