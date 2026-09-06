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
    parser.add_argument(
        "--preframe",
        action="store_true",
        help=(
            "Apply only the visual prerequisites (display mode + brightness) "
            "synchronously and exit. Never starts the ongoing watcher."
        ),
    )
    parser.add_argument(
        "--wait-for-first-frame",
        type=Path,
        default=None,
        help=(
            "Block the ongoing watcher until first-frame readiness is "
            "signalled through the given FIFO (deterministic gate, no "
            "polling). Fail-open when the FIFO is absent."
        ),
    )
    return parser.parse_args()


def run_visual_preframe(
    hardware_store: HardwareSettingsStore,
    system_store: SystemControlSettingsStore,
    *,
    hardware_controller: LegacyXHardwareSessionController | None = None,
    system_backend: LegacyXSystemControlBackend | None = None,
) -> int:
    """Apply the synchronous pre-frame visual prerequisites and exit.

    Only the P5-HW-MEASURE minimum visual-prerequisite set runs here: the
    display-mode apply (with its read probes) and the brightness apply
    (sysfs preferred, xrandr-gamma fallback). Keyboard, microphone gain,
    pointer enumeration, output volume, status-file pointer summary, media-key
    grabs and all re-apply loops stay in the deferred watcher behind
    first-frame readiness. Always returns 0 and never raises: the preframe
    must never fail boot; the deferred watcher re-applies everything anyway.
    """

    try:
        controller = hardware_controller or LegacyXHardwareSessionController()
        backend = system_backend or LegacyXSystemControlBackend()
        controller.apply_display_mode(hardware_store.read())
        backend.apply_brightness_percent(system_store.read().brightness_percent)
    except Exception:
        pass
    return 0


def wait_for_first_frame(fifo_path: Path) -> None:
    """Block until the first-frame readiness callback releases the gate.

    The launcher-owned ``release-boot-cover`` helper (invoked after the first
    complete flip on every child-shell path) opens the FIFO for writing,
    which releases this blocking read-side open deterministically — no
    sleep, no polling, no timer. Fail-open: a missing FIFO (developer
    invocation without the session gate) or ``GREIA_SKIP_BOOT_HANDOFF=1``
    (the same opt-out the launcher honors) proceeds immediately, and any
    other wait error proceeds rather than stranding the watcher.
    """

    if os.environ.get("GREIA_SKIP_BOOT_HANDOFF") == "1":
        return
    try:
        fd = os.open(fifo_path, os.O_RDONLY)
    except OSError:
        return
    try:
        pass
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


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

    if args.preframe:
        return run_visual_preframe(
            hardware_store,
            system_store,
            hardware_controller=hardware_controller,
            system_backend=system_backend,
        )

    if args.wait_for_first_frame is not None:
        wait_for_first_frame(args.wait_for_first_frame)

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
