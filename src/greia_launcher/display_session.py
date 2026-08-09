from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import PurePath
from types import MappingProxyType
from typing import Mapping, Protocol


class DisplaySessionError(RuntimeError):
    """Raised when Greia cannot preserve shell/Activity display ownership."""


class DisplaySessionPhase(str, Enum):
    SHELL = "shell"
    PREPARING_ACTIVITY = "preparing_activity"
    ACTIVITY_PREPARED = "activity_prepared"
    PRESENTING_ACTIVITY = "presenting_activity"
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

    Device-node authority is deliberately not representable here. The object
    contains only the endpoint/environment facts required to connect a child
    surface to the selected Greia display backend.
    """

    kind: DisplayTransportKind
    sdl_video_driver: str
    display: str | None = None
    xauthority: str | None = None
    wayland_display: str | None = None
    xdg_runtime_dir: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, DisplayTransportKind):
            raise TypeError("display transport kind must be a DisplayTransportKind")
        _require_simple_token(self.sdl_video_driver, "SDL video driver")

        if self.kind is DisplayTransportKind.LEGACY_X11:
            if self.sdl_video_driver != "x11":
                raise ValueError("legacy X11 transport must request SDL x11")
            _require_endpoint(self.display, "X11 display")
            _require_absolute_path(self.xauthority, "Xauthority path")
            if self.wayland_display is not None or self.xdg_runtime_dir is not None:
                raise ValueError("legacy X11 transport cannot carry Wayland authority")
        elif self.kind is DisplayTransportKind.WAYLAND:
            if self.sdl_video_driver != "wayland":
                raise ValueError("Wayland transport must request SDL wayland")
            _require_endpoint(self.wayland_display, "Wayland display")
            _require_absolute_path(self.xdg_runtime_dir, "XDG runtime directory")
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
class DisplaySessionLease:
    """Launcher-internal ownership token for one prepared display session.

    The lease is never sent to Activity code. Coordinator callbacks require the
    exact lease object returned by `prepare_activity`, which makes stale
    callbacks from an older generation fail closed even if a session ID were
    accidentally reused.
    """

    session_id: str
    generation: int
    transport: DisplayTransport


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

    @property
    def transport_kind(self) -> DisplayTransportKind: ...

    def prepare_activity(self, session_id: str) -> DisplayTransport: ...

    def present_activity(self, session_id: str) -> None: ...

    def restore_shell(self, session_id: str) -> None: ...


class DisplaySessionCoordinator:
    """Runtime-neutral shell <-> Activity surface ownership state machine.

    The coordinator does not launch Activities. It owns only the display-side
    transition contract around an Activity lifecycle. Every prepared session
    must either become visible or converge through the same shell-restore path.
    """

    def __init__(self, backend: DisplaySessionBackend):
        backend_id = backend.backend_id
        if not isinstance(backend_id, str):
            raise TypeError("display backend_id must be text")
        backend_id = backend_id.strip()
        _require_simple_token(backend_id, "display backend_id")
        transport_kind = backend.transport_kind
        if not isinstance(transport_kind, DisplayTransportKind):
            raise TypeError("display backend transport_kind must be a DisplayTransportKind")

        self._backend = backend
        self._backend_id = backend_id
        self._transport_kind = transport_kind
        self._phase = DisplaySessionPhase.SHELL
        self._session_id: str | None = None
        self._transport: DisplayTransport | None = None
        self._lease: DisplaySessionLease | None = None
        self._generation = 0
        self._failure: str | None = None

    @property
    def backend_id(self) -> str:
        return self._backend_id

    @property
    def transport_kind(self) -> DisplayTransportKind:
        return self._transport_kind

    @property
    def snapshot(self) -> DisplaySessionSnapshot:
        return DisplaySessionSnapshot(
            phase=self._phase,
            session_id=self._session_id,
            transport=self._transport,
            generation=self._generation,
            failure=self._failure,
        )

    def prepare_activity(self, session_id: str) -> DisplaySessionLease:
        session_id = _validate_session_id(session_id)
        self._require_phase(DisplaySessionPhase.SHELL)
        self._phase = DisplaySessionPhase.PREPARING_ACTIVITY
        self._session_id = session_id
        self._transport = None
        self._lease = None
        self._failure = None

        try:
            transport = self._backend.prepare_activity(session_id)
            if not isinstance(transport, DisplayTransport):
                raise TypeError("display backend returned an invalid transport")
            if transport.kind is not self._transport_kind:
                raise TypeError(
                    f"display backend {self._backend_id!r} returned "
                    f"{transport.kind.value}, expected {self._transport_kind.value}"
                )
        except Exception as exc:
            self._recover_failed_prepare(session_id, exc)
            raise DisplaySessionError(
                f"display backend {self._backend_id!r} could not prepare Activity surface"
            ) from exc

        generation = self._generation + 1
        lease = DisplaySessionLease(
            session_id=session_id,
            generation=generation,
            transport=transport,
        )
        self._generation = generation
        self._transport = transport
        self._lease = lease
        self._phase = DisplaySessionPhase.ACTIVITY_PREPARED
        return lease

    def activity_ready(self, lease: DisplaySessionLease) -> None:
        self._require_lease(lease)
        self._require_phase(DisplaySessionPhase.ACTIVITY_PREPARED)
        session_id = lease.session_id
        self._phase = DisplaySessionPhase.PRESENTING_ACTIVITY
        try:
            self._backend.present_activity(session_id)
        except Exception as exc:
            try:
                self._restore_shell(session_id, primary=("present", exc))
            except DisplaySessionError as restore_exc:
                raise restore_exc from exc
            raise DisplaySessionError(
                f"display backend {self._backend_id!r} could not present Activity surface"
            ) from exc
        self._phase = DisplaySessionPhase.ACTIVITY_VISIBLE

    def activity_ended(self, lease: DisplaySessionLease) -> None:
        self._require_lease(lease)
        if self._phase not in {
            DisplaySessionPhase.ACTIVITY_PREPARED,
            DisplaySessionPhase.ACTIVITY_VISIBLE,
        }:
            raise DisplaySessionError(
                f"cannot end Activity display session while phase is {self._phase.value}"
            )
        self._restore_shell(lease.session_id)

    def abort_activity(self, lease: DisplaySessionLease) -> None:
        """Recover after child launch/READY failure or forced Activity return."""

        self._require_lease(lease)
        if self._phase not in {
            DisplaySessionPhase.ACTIVITY_PREPARED,
            DisplaySessionPhase.ACTIVITY_VISIBLE,
        }:
            raise DisplaySessionError(
                f"cannot abort Activity display session while phase is {self._phase.value}"
            )
        self._restore_shell(lease.session_id)

    def _restore_shell(
        self,
        session_id: str,
        *,
        primary: tuple[str, Exception] | None = None,
    ) -> None:
        self._phase = DisplaySessionPhase.RECOVERING_SHELL
        try:
            self._backend.restore_shell(session_id)
        except Exception as exc:
            self._phase = DisplaySessionPhase.FAILED
            self._failure = _failure_detail(primary, ("restore", exc))
            raise DisplaySessionError(
                f"display backend {self._backend_id!r} failed to restore the Greia shell"
            ) from exc
        self._clear_to_shell()

    def _recover_failed_prepare(self, session_id: str, cause: Exception) -> None:
        self._phase = DisplaySessionPhase.RECOVERING_SHELL
        try:
            self._backend.restore_shell(session_id)
        except Exception as restore_exc:
            self._phase = DisplaySessionPhase.FAILED
            self._failure = _failure_detail(
                ("prepare", cause),
                ("restore", restore_exc),
            )
            raise DisplaySessionError(
                f"display backend {self._backend_id!r} failed during prepare and shell recovery"
            ) from restore_exc
        self._clear_to_shell()

    def _clear_to_shell(self) -> None:
        self._phase = DisplaySessionPhase.SHELL
        self._session_id = None
        self._transport = None
        self._lease = None
        self._failure = None

    def _require_phase(self, expected: DisplaySessionPhase) -> None:
        if self._phase is not expected:
            raise DisplaySessionError(
                f"display session phase is {self._phase.value}, expected {expected.value}"
            )

    def _require_lease(self, lease: DisplaySessionLease) -> None:
        if not isinstance(lease, DisplaySessionLease):
            raise TypeError("display session callback requires a DisplaySessionLease")
        if self._lease is not lease:
            raise DisplaySessionError(
                "display session lease is stale or does not own the active Activity surface"
            )
        if self._session_id != lease.session_id or self._generation != lease.generation:
            raise DisplaySessionError(
                "display session lease does not match active Activity generation"
            )


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


def _require_endpoint(value: str | None, label: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{label} is required")
    if not value or len(value) > 255:
        raise ValueError(f"{label} must contain 1..255 characters")
    if any(ord(character) < 0x20 or character.isspace() for character in value):
        raise ValueError(f"{label} contains whitespace/control characters")
    if "\x00" in value:
        raise ValueError(f"{label} contains a NUL character")


def _require_absolute_path(value: str | None, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} is required")
    if len(value) > 4096:
        raise ValueError(f"{label} is too long")
    if "\x00" in value or any(ord(character) < 0x20 for character in value):
        raise ValueError(f"{label} contains control characters")
    if not PurePath(value).is_absolute():
        raise ValueError(f"{label} must be absolute")


def _bounded_error(exc: Exception, maximum: int = 180) -> str:
    text = " ".join(str(exc).split())
    return text[:maximum] if text else exc.__class__.__name__


def _failure_detail(
    *failures: tuple[str, Exception] | None,
    maximum: int = 240,
) -> str:
    parts = [
        f"{label}={_bounded_error(exc)}"
        for failure in failures
        if failure is not None
        for label, exc in (failure,)
    ]
    return "; ".join(parts)[:maximum]
