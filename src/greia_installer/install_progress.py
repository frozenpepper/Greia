"""Truthful install progress: phase vocabulary, root reporter, UI frame parser.

The root ``greia-install-transaction`` service runs the whole destructive
install inside one ``EXECUTE`` request. Before this module existed it
answered only at the very end, so the unprivileged UI held its bar at the
last value it had invented itself (10 %) for the entire copy. Progress now
travels over the *same* EXECUTE connection, as extra framed ``PROGRESS``
responses written before the final ``INSTALLED``/``ERROR`` frame:

- **root side** — :class:`ProgressReporter` turns engine milestones and
  measured byte counts into ``PROGRESS`` payloads. It is rate-limited
  (:data:`MIN_FRAME_INTERVAL_SECONDS`, i.e. at most 2 Hz for fraction
  updates; a phase change always passes), keeps the overall fraction
  monotonic and never raises into the install: a broken or slow UI
  connection disables reporting, it never stops a transaction;
- **UI side** — :func:`parse_progress_payload` validates one decoded
  payload into a :class:`ProgressFrame` (known phase, finite bounded
  fractions, bounded byte counts) or raises :class:`ProgressFrameError`.

Nothing here touches a disk, spawns a process or carries authority: a
progress frame is display data only. Requests still carry nonce + digest
alone, and every revalidation stays where it was.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol

#: Operation name of an intermediate progress frame on an EXECUTE connection.
PROGRESS_OP = "PROGRESS"
#: ``status`` carried by every progress payload.
RUNNING_STATUS = "RUNNING"
#: Minimum spacing of fraction-only updates (<= 2 Hz). Phase changes pass.
MIN_FRAME_INTERVAL_SECONDS = 0.5
#: UI-side cap on progress frames delivered per EXECUTE; extra frames are
#: read and discarded (2 Hz over the 30-minute EXECUTE patience is 3,600).
MAX_PROGRESS_FRAMES = 8192
#: Upper bound accepted for a byte count (1 PiB): rejects garbage, not data.
MAX_PROGRESS_BYTES = 1 << 50


class ProgressFrameError(ValueError):
    """A progress payload is outside the Greia progress schema."""


@dataclass(frozen=True, slots=True)
class InstallPhase:
    """One parent-visible install phase and its slice of the overall bar.

    ``label`` is English source copy; the UI translates it at draw time.
    ``start``/``end`` place the phase on the overall bar when the reporter
    has to compute the overall fraction from a measured phase fraction.
    """

    id: str
    label: str
    start: float
    end: float


#: Ordered phase vocabulary shared by the root service and the UI. The
#: ranges are weighted by observed duration on the reference Acer: the
#: payload copy dominates, readback verification is the next longest.
PHASES: tuple[InstallPhase, ...] = (
    InstallPhase("prepare", "Confirming the selected disk", 0.00, 0.04),
    InstallPhase("check", "Checking the installation files", 0.04, 0.10),
    InstallPhase("partition", "Preparing the internal disk", 0.10, 0.16),
    InstallPhase("format", "Creating the Greia OS filesystem", 0.16, 0.20),
    InstallPhase("copy", "Copying the system", 0.20, 0.72),
    InstallPhase("verify", "Checking the installed system", 0.72, 0.84),
    InstallPhase("setup", "Setting up the system", 0.84, 0.94),
    InstallPhase("bootloader", "Making the disk bootable", 0.94, 0.99),
    InstallPhase("complete", "Installation complete", 1.00, 1.00),
)
_PHASE_BY_ID: dict[str, InstallPhase] = {phase.id: phase for phase in PHASES}
PHASE_IDS: frozenset[str] = frozenset(_PHASE_BY_ID)

#: Generic label for a phase id this UI does not know (newer service).
FALLBACK_LABEL = "Installing Greia OS"

#: Legacy single-partition engine stage names → shared phase ids.
_ENGINE_STAGE_PHASE: dict[str, str] = {
    "payload": "check",
    "prepare": "check",
    "erase": "partition",
    "format": "format",
    "copy": "copy",
    "configure": "setup",
    "bootloader": "bootloader",
    "verify": "verify",
    "complete": "complete",
}


def phase_label(phase_id: str) -> str:
    """English source label for ``phase_id`` (generic for unknown ids)."""

    phase = _PHASE_BY_ID.get(phase_id)
    return phase.label if phase is not None else FALLBACK_LABEL


def overall_fraction(phase_id: str, phase_fraction: float | None) -> float:
    """Place a phase fraction on the overall bar (phase start when unknown)."""

    phase = _PHASE_BY_ID.get(phase_id)
    if phase is None:
        return 0.0
    if phase_fraction is None:
        return phase.start
    return phase.start + (phase.end - phase.start) * _unit(phase_fraction)


def _unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(frozen=True, slots=True)
class ProgressFrame:
    """One validated progress update as the UI sees it."""

    phase: str
    fraction: float
    phase_fraction: float | None = None
    done_bytes: int | None = None
    total_bytes: int | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "status": RUNNING_STATUS,
            "phase": self.phase,
            "fraction": round(self.fraction, 4),
            "phase_fraction": (
                None if self.phase_fraction is None else round(self.phase_fraction, 4)
            ),
            "done_bytes": self.done_bytes,
            "total_bytes": self.total_bytes,
        }


_PAYLOAD_KEYS = frozenset(
    {"status", "phase", "fraction", "phase_fraction", "done_bytes", "total_bytes"}
)


def _checked_fraction(value: object, *, field_name: str, optional: bool) -> float | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProgressFrameError(f"progress {field_name} must be a number")
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        raise ProgressFrameError(f"progress {field_name} is outside 0..1")
    return number


def _checked_bytes(value: object, *, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProgressFrameError(f"progress {field_name} must be an integer")
    if value < 0 or value > MAX_PROGRESS_BYTES:
        raise ProgressFrameError(f"progress {field_name} is outside Greia bounds")
    return value


def parse_progress_payload(payload: Mapping[str, object]) -> ProgressFrame:
    """Validate one decoded ``PROGRESS`` payload (UI side, untrusted bytes)."""

    if not isinstance(payload, Mapping) or not set(payload) <= _PAYLOAD_KEYS:
        raise ProgressFrameError("progress payload carries unknown fields")
    if payload.get("status") != RUNNING_STATUS:
        raise ProgressFrameError("progress payload status is not RUNNING")
    phase = payload.get("phase")
    if not isinstance(phase, str) or phase not in PHASE_IDS:
        raise ProgressFrameError("progress phase is unknown")
    fraction = _checked_fraction(payload.get("fraction"), field_name="fraction", optional=False)
    phase_fraction = _checked_fraction(
        payload.get("phase_fraction"), field_name="phase_fraction", optional=True
    )
    done = _checked_bytes(payload.get("done_bytes"), field_name="done_bytes")
    total = _checked_bytes(payload.get("total_bytes"), field_name="total_bytes")
    if (done is None) != (total is None):
        raise ProgressFrameError("progress byte counts must come together")
    if done is not None and total is not None and done > total:
        raise ProgressFrameError("progress done_bytes exceeds total_bytes")
    assert fraction is not None
    return ProgressFrame(phase, fraction, phase_fraction, done, total)


class InstallProgressSink(Protocol):
    """What an install backend may report to (implemented by the reporter)."""

    def phase(
        self,
        phase_id: str,
        *,
        phase_fraction: float | None = None,
        done_bytes: int | None = None,
        total_bytes: int | None = None,
    ) -> None: ...


class ProgressReporter:
    """Root-side, rate-limited, never-raising progress frame producer.

    ``emit`` receives one ``PROGRESS`` payload mapping; the transaction
    service frames and writes it on the EXECUTE connection. A phase change
    is emitted immediately; updates within one phase are coalesced to at
    most one per :data:`MIN_FRAME_INTERVAL_SECONDS` (updates inside the
    interval are dropped and the next one after it carries the latest
    measured value, so the bar never runs ahead of the truth). The
    overall fraction never decreases. Any exception from ``emit`` disables
    the reporter for the rest of the transaction: reporting is a courtesy
    to the UI and must never become a reason an install stops.
    """

    def __init__(
        self,
        emit: Callable[[Mapping[str, object]], None],
        *,
        clock: Callable[[], float] = time.monotonic,
        min_interval: float = MIN_FRAME_INTERVAL_SECONDS,
    ) -> None:
        self._emit = emit
        self._clock = clock
        self._min_interval = float(min_interval)
        self._last_phase: str | None = None
        self._last_emit_at: float | None = None
        self._last_payload: dict[str, object] | None = None
        self._overall = 0.0
        self._broken = False
        self.frames_emitted = 0

    @property
    def disabled(self) -> bool:
        return self._broken

    def phase(
        self,
        phase_id: str,
        *,
        phase_fraction: float | None = None,
        done_bytes: int | None = None,
        total_bytes: int | None = None,
        overall: float | None = None,
    ) -> None:
        """Report the current phase, optionally with measured progress."""

        if self._broken or phase_id not in PHASE_IDS:
            return
        try:
            if phase_fraction is None and done_bytes is not None and total_bytes:
                phase_fraction = done_bytes / total_bytes
            if phase_fraction is not None:
                phase_fraction = _unit(phase_fraction)
            if done_bytes is not None and total_bytes is not None:
                done_bytes = max(0, min(int(done_bytes), int(total_bytes)))
                total_bytes = int(total_bytes)
            else:
                done_bytes = total_bytes = None
            computed = overall_fraction(phase_id, phase_fraction) if overall is None else _unit(overall)
            self._overall = max(self._overall, computed)
            now = self._clock()
            changed_phase = phase_id != self._last_phase
            if not changed_phase and self._last_emit_at is not None:
                if now - self._last_emit_at < self._min_interval:
                    return
            frame = ProgressFrame(phase_id, self._overall, phase_fraction, done_bytes, total_bytes)
            payload = frame.to_payload()
            if not changed_phase and payload == self._last_payload:
                return
            self._last_phase = phase_id
            self._last_emit_at = now
            self._last_payload = payload
            self.frames_emitted += 1
            self._emit(payload)
        except Exception:  # noqa: BLE001 - reporting never stops an install
            self._broken = True

    def engine_progress(self, progress: object) -> None:
        """Adapter for the legacy engine's ``InstallProgress`` callback.

        The legacy engine reports its own overall fraction per stage; that
        value is kept (it already orders the stages) and mapped onto the
        shared phase vocabulary for the label.
        """

        stage = str(getattr(progress, "stage", ""))
        fraction = getattr(progress, "fraction", None)
        if stage == "hardware":
            # Hardware discovery runs before erase; support install after copy.
            phase_id = "setup" if isinstance(fraction, (int, float)) and fraction >= 0.5 else "check"
        else:
            phase_id = _ENGINE_STAGE_PHASE.get(stage, "")
        if not phase_id:
            return
        overall = float(fraction) if isinstance(fraction, (int, float)) else None
        self.phase(phase_id, overall=overall)


__all__ = [
    "FALLBACK_LABEL",
    "InstallPhase",
    "InstallProgressSink",
    "MAX_PROGRESS_BYTES",
    "MAX_PROGRESS_FRAMES",
    "MIN_FRAME_INTERVAL_SECONDS",
    "PHASES",
    "PHASE_IDS",
    "PROGRESS_OP",
    "ProgressFrame",
    "ProgressFrameError",
    "ProgressReporter",
    "RUNNING_STATUS",
    "overall_fraction",
    "parse_progress_payload",
    "phase_label",
]
