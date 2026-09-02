from __future__ import annotations

import argparse
import os
from pathlib import Path
from threading import Event, Thread

from .hal_legacy_x import LegacyXHardwareSessionController
from .hardware import HardwareSettingsStore
from .hardware_session import run_watcher
from .system_controls import SystemControlSettingsStore
from .system_controls_legacy_x import (
    LegacyXSystemControlBackend,
    run_legacy_x_system_controls,
)


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
    """Run all current Legacy-X hardware/session controls in one owner process.

    Generic pointer/display preferences and live system controls intentionally
    share the existing ``greia-hardware`` lifecycle. This avoids a parallel
    privileged daemon while keeping mixer/backlight/XF86 details below the
    backend-neutral platform domains.
    """

    args = parse_args()
    hardware_store = HardwareSettingsStore.load(
        args.root / "runtime" / "hardware-settings.toml",
        args.state_dir,
    )
    system_store = SystemControlSettingsStore(args.state_dir)
    hardware_controller = LegacyXHardwareSessionController()
    system_backend = LegacyXSystemControlBackend()

    if args.once:
        run_watcher(
            hardware_store,
            args.status_path,
            controller=hardware_controller,
            once=True,
        )
        return run_legacy_x_system_controls(
            system_store,
            backend=system_backend,
            once=True,
        )

    stop_event = Event()
    settings_thread = Thread(
        name="greia-hardware-settings",
        target=run_watcher,
        kwargs={
            "store": hardware_store,
            "status_path": args.status_path,
            "controller": hardware_controller,
            "stop_event": stop_event,
        },
    )
    settings_thread.start()
    try:
        return run_legacy_x_system_controls(
            system_store,
            backend=system_backend,
            stop_event=stop_event,
        )
    finally:
        stop_event.set()
        settings_thread.join(timeout=2.0)


if __name__ == "__main__":
    raise SystemExit(main())
