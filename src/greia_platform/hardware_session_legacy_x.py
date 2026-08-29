from __future__ import annotations

import argparse
import os
from pathlib import Path

from .hal_legacy_x import LegacyXHardwareSessionController
from .hardware import HardwareSettingsStore
from .hardware_session import run_watcher


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
    """Run Greia hardware settings through the provisional Legacy-X adapter."""

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
