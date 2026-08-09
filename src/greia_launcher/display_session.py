from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping, Protocol


class DisplaySessionError(RuntimeError):
    """Raised when Greia cannot preserve shell/Activity display ownership."""


class DisplaySessionPhase(str, Enum):
    SHELL = "shell"
    PREPARING_ACTIVITY = "preparing_activity"
    ACTIVITY_PREPARED = "activity_prepared"
    ACTIVITY_VISIBLE = "activity_visible"
    RECOVERING_SHELL = "recovering_shell"
    FAILED = "failed"


class DisplayTransportKind(str, Enum):
    LEGACY_X11 = "legacy_x11"
    WAYLAND = "wayland"
    DIRECT_KMSDRM = "direct_kmsdrm"


@dataclass(frozen=True, slots=True)
class DisplayTransport:
    """Bounded child-facing display transport, never a hardware grant.

    The display/session backend may describe how the child should connect to a
    Greia-owned surface or, for the evidence-only serial candidate, which SDL
    video backend it should request. Device-node authority is deliberately not
    representable here.
    """

    kind: DisplayTransportKind
    sdl_video_driver: str
    display: str | None = None
    xauthority: str | None = None
    wayland_display: str | None = None
    xdg_runtime_dir: str | None = None

    def __post_init__(self) -> None:
        _require_simple_token(self.sdl_video_driver, "SDL video driver")
        if self.kind is DisplayTransportKind.LEGACY_X11:
            if not self.display or not self.xauthority:
                raise ValueError("legacy X11 transport requires display and xauthority")
            if self.wayland_display is not None:
                raise ValueError("legacy X11 transport cannot carry a Wayland display")
        elif self.kind is DisplayTransportKind.WAYLAND:
            if not self.wayland_display or not self.xdg_runtime_dir:
                raise ValueError(
                    "Wayland transport requires wayland_display and xdg_runtime_dir"
                )
            if self.display is not None or self.xauthority is not None:
                raise ValueError("Wayland transport cannot carry X11 authority")
        elif self.kind is DisplayTransportKind.DIRECT_KMSDRM:
            if any(
                value is not None
                for value in (
                    self.display,
                    self.xauthority,
                    self.wayland_display,
                    self.xdg_runtime_dir,
                )
            ):
                raise ValueError(
                    "direct KMSDRM transport cannot carry X11/Wayland endpoints"
                )
            if self.sdl_video_driver != "kmsdrm":
                raise ValueError("direct KMSDRM transport must request SDL kmsdrm")

    def environment(self) -> Mapping[str, str]:
        values = {"SDL_VIDEODRIVER": self.sdl_video_driver}
        if self.display is not None:
            values["DISPLAY"] = self.display
        if self.xauthority is not None:
            values["XAUTHORITY"] = self.xauthority
        if self.wayland_display is not None:
            values["WAYLAND_DISPLAY"] = self.wayland_display
        if self.xdg_runtime_dir is not None:
            values["XDG_RUNTIME_DIR"] = self.xdg_runtime_dir
        return MappingProxyType(values)


@dataclass(frozen=True, slots=True)
class DisplaySessionSnapshot:
    phase: DisplaySessionPhase
    session_id: str | None
    transport: DisplayTransport | None
    generation: int
    failure: str | None = None

    @property
    def shell_available(self) -> bool:
        return self.phase is DisplaySessionPhase.SHELL


class DisplaySessionBackend(Protocol):
    """Backend-specific mechanics below Greia's session ownership contract."""

    @property
    def backend_id(self) -> str: ...

    def prepare_activity(self, session_id: str) -> DisplayTransport: ...

    def present_activity(self, session_id: str) -> None: ...

    def restore_shell(self, session_id: str) -> None: ...


class DisplaySessionCoordinator:
    """Runtime-neutral shell <-> Activity surface ownership state machine.

    The coordinator does not launch Activities and does not own their lifecycle.
    It provides the display-side contract the launcher can compose around the
    existing ActivitySupervisor. Every prepared Activity session must either be
    presented or be recovered back to the shell; launch failure, crash, timeout
    and normal exit all converge on the same restore operation.
    """

    def __init__(self, backend: DisplaySessionBackend):
        backend_id = backend.backend_id.strip()
        if not backend_id:
            raise ValueError("display backend_id must not be empty")
        self._backend = backend
        self._backend_id = backend_id
        self._phase = DisplaySessionPhase.SHELL
        self._session_id: str | None = None
        self._transport: DisplayTransport | None = None
        self._generation = 0
        self._failure: str | None = None

    @property
    def backend_id(self) -> str:
        return self._backend_id

    @property
    def snapshot(self) -> DisplaySessionSnapshot:
        return DisplaySessionSnapshot(
            phase=self._phase,
            session_id=self._session_id,
            transport=self._transport,
            generation=self._generation,
            failure=self._failure,
        )

    def prepare_activity(self, session_id: str) -> DisplayTransport:
        session_id = _validate_session_id(session_id)
        self._require_phase(DisplaySessionPhase.SHELL)
        self._phase = DisplaySessionPhase.PREPARING_ACTIVITY
        self._session_id = session_id
        self._transport = None
        self._failure = None
        try:
            transport = self._backend.prepare_activity(session_id)
            if not isinstance(transport, DisplayTransport):
                raise TypeError("display backend returned an invalid transport")
        except Exception as exc:
            self._recover_failed_prepare(session_id, exc)
            raise DisplaySessionError(
                f"display backend {self._backend_id!r} could not prepare Activity surface"
            ) from exc
        self._transport = transport
        self._phase = DisplaySessionPhase.ACTIVITY_PREPARED
        self._generation += 1
        return transport

    def activity_ready(self, session_id: str) -> None:
        self._require_session(session_id)
        self._require_phase(DisplaySessionPhase.ACTIVITY_PREPARED)
        try:
            self._backend.present_activity(session_id)
        except Exception as exc:
            try:
                self._restore_shell(session_id)
            except DisplaySessionError as restore_exc:
                raise restore_exc from exc
            raise DisplaySessionError(
                f"display backend {self._backend_id!r} could not present Activity surface"
            ) from exc
        self._phase = DisplaySessionPhase.ACTIVITY_VISIBLE

    def activity_ended(self, session_id: str) -> None:
        self._require_session(session_id)
        if self._phase not in {
            DisplaySessionPhase.ACTIVITY_PREPARED,
            DisplaySessionPhase.ACTIVITY_VISIBLE,
        }:
            raise DisplaySessionError(
                f"cannot end Activity display session while phase is {self._phase.value}"
            )
        self._restore_shell(session_id)

    def abort_activity(self, session_id: str) -> None:
        """Recover after child launch/READY failure before normal visibility."""

        self._require_session(session_id)
        if self._phase not in {
            DisplaySessionPhase.ACTIVITY_PREPARED,
            DisplaySessionPhase.ACTIVITY_VISIBLE,
        }:
            raise DisplaySessionError(
                f"cannot abort Activity display session while phase is {self._phase.value}"
            )
        self._restore_shell(session_id)

    def _restore_shell(self, session_id: str) -> None:
        self._phase = DisplaySessionPhase.RECOVERING_SHELL
        try:
            self._backend.restore_shell(session_id)
        except Exception as exc:
            self._phase = DisplaySessionPhase.FAILED
            self._failure = _bounded_error(exc)
            raise DisplaySessionError(
                f"display backend {self._backend_id!r} failed to restore the Greia shell"
            ) from exc
        self._phase = DisplaySessionPhase.SHELL
        self._session_id = None
        self._transport = None
        self._failure = None

    def _recover_failed_prepare(self, session_id: str, cause: Exception) -> None:
        self._phase = DisplaySessionPhase.RECOVERING_SHELL
        try:
            self._backend.restore_shell(session_id)
        except Exception as restore_exc:
            self._phase = DisplaySessionPhase.FAILED
            self._failure = _bounded_error(restore_exc)
            raise DisplaySessionError(
                f"display backend {self._backend_id!r} failed during prepare and shell recovery"
            ) from restore_exc
        self._phase = DisplaySessionPhase.SHELL
        self._session_id = None
        self._transport = None
        self._failure = None

    def _require_phase(self, expected: DisplaySessionPhase) -> None:
        if self._phase is not expected:
            raise DisplaySessionError(
                f"display session phase is {self._phase.value}, expected {expected.value}"
            )

    def _require_session(self, session_id: str) -> None:
        session_id = _validate_session_id(session_id)
        if self._session_id != session_id:
            raise DisplaySessionError("display session identity does not match active Activity")


def _validate_session_id(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("display session ID must be text")
    value = value.strip()
    if not value or len(value) > 128:
        raise ValueError("display session ID must contain 1..128 characters")
    if any(character.isspace() or ord(character) < 0x20 for character in value):
        raise ValueError("display session ID contains whitespace/control characters")
    return value


def _require_simple_token(value: str, label: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be text")
    if not value or len(value) > 64:
        raise ValueError(f"{label} must contain 1..64 characters")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.")
    if any(character not in allowed for character in value):
        raise ValueError(f"{label} contains unsupported characters")


def _bounded_error(exc: Exception, maximum: int = 240) -> str:
    return " ".join(str(exc).split())[:maximum]
