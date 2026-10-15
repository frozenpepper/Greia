"""TEMPORARY Session-04 serial diagnostic channel.

Writes one stage line to the guest serial console iff the test-only marker
``/run/greia-x8-debug`` exists. The marker is touched only by the product-mode
QEMU test control runner; production images never create it.

This is the single owner of that device path so that the slot writer and the
fresh install orchestrator stay free of any raw device surface (their source
hygiene tests forbid it). Delete this module, and the two thin
``_s04_diag_stage`` callers, when Session 04 closes.
"""

from __future__ import annotations

import os

_MARKER = "/run/greia-x8-debug"
_SERIAL_CONSOLE = "/dev/ttyS0"


def emit_stage(line: str) -> None:
    """Best-effort, marker-gated, one-line serial emit; never raises."""

    try:
        if not os.path.exists(_MARKER):
            return
        with open(_SERIAL_CONSOLE, "a") as handle:
            handle.write(f"s04-svc: {line}\n")
    except OSError:
        pass
