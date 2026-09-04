"""Python boot-marker helper for launcher first-frame instrumentation.

Single owner of the ``GREIA_BOOT event=<name> monotonic_ns=<int>`` stdout
line shape consumed by downstream boot-timing parsing. All launcher-side
boot markers must go through :func:`emit_boot_marker`; no other module may
duplicate the ``print`` shape.
"""

from __future__ import annotations

import time


def emit_boot_marker(event: str) -> None:
    """Emit one boot-marker line to stdout."""
    print(f"GREIA_BOOT event={event} monotonic_ns={time.monotonic_ns()}", flush=True)
