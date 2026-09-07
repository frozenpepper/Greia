"""Python boot-marker helper for launcher first-frame instrumentation.

Single owner of the ``GREIA_BOOT event=<name> monotonic_ns=<int>`` stdout
line shape consumed by downstream boot-timing parsing. All launcher-side
boot markers must go through :func:`emit_boot_marker`; no other module may
duplicate the ``print`` shape.

The helper additionally mirrors every marker line into a bounded fail-soft
spool file. The spool exists because the X-session python path runs below
``xinit`` (``greia-x-session`` -> ``child_shell``), where Verification-9
evidence shows journald receives only the ``ExecStartPre`` shell lines and
loses all ``ExecStart`` output (shell and python alike). ``devctl logs``
appends the spool so the markers stay retrievable without inventing a
parallel logging framework.
"""

from __future__ import annotations

import os
import time
from pathlib import Path


#: Fixed spool path on the volatile runtime root (tmpfs, fresh each boot,
#: writable by the ``greiakid`` launcher). Overridable in tests through
#: ``GREIA_BOOT_MARKERS_SPOOL``.
BOOT_MARKER_SPOOL_DEFAULT = Path("/run/greia-os/boot-markers.log")
#: Hard bounds: at most this many recent lines / bytes are retained.
BOOT_MARKER_SPOOL_MAX_LINES = 500
BOOT_MARKER_SPOOL_MAX_BYTES = 64 * 1024


def spool_path() -> Path:
    """Return the active spool path (test override aware)."""
    override = os.environ.get("GREIA_BOOT_MARKERS_SPOOL")
    if override:
        return Path(override)
    return BOOT_MARKER_SPOOL_DEFAULT


def _append_spool(line: str) -> None:
    """Append one marker line to the spool, enforcing bounds. Never raises."""
    try:
        path = spool_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            return
        try:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError:
            return
        try:
            if path.stat().st_size <= BOOT_MARKER_SPOOL_MAX_BYTES:
                needs_trim = False
                try:
                    with open(path, encoding="utf-8", errors="replace") as handle:
                        for index, _ in enumerate(handle):
                            if index >= BOOT_MARKER_SPOOL_MAX_LINES:
                                needs_trim = True
                                break
                except OSError:
                    return
                if not needs_trim:
                    return
        except OSError:
            return
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        tail = text.splitlines()[-BOOT_MARKER_SPOOL_MAX_LINES:]
        try:
            path.write_text("\n".join(tail) + "\n", encoding="utf-8")
        except OSError:
            pass
    except Exception:  # noqa: BLE001 - marker emission must never fail boot
        pass


def read_spool_text() -> str:
    """Return the current spool content, bounded. Never raises."""
    try:
        path = spool_path()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        lines = text.splitlines()
        if len(lines) > BOOT_MARKER_SPOOL_MAX_LINES:
            lines = lines[-BOOT_MARKER_SPOOL_MAX_LINES:]
        capped = "\n".join(lines)
        raw = capped.encode("utf-8")
        if len(raw) > BOOT_MARKER_SPOOL_MAX_BYTES:
            raw = raw[-BOOT_MARKER_SPOOL_MAX_BYTES:]
            capped = raw.decode("utf-8", errors="replace")
            if "\n" in capped:
                capped = capped.split("\n", 1)[1]
        if capped and not capped.endswith("\n"):
            capped += "\n"
        return capped
    except Exception:  # noqa: BLE001 - retrieval must never fail callers
        return ""


def emit_boot_marker(event: str) -> None:
    """Emit one boot-marker line to stdout and mirror it into the spool."""
    namespace = time.monotonic_ns()
    print(f"GREIA_BOOT event={event} monotonic_ns={namespace}", flush=True)
    _append_spool(f"GREIA_BOOT event={event} monotonic_ns={namespace}")
