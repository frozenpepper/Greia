"""Trusted bridge between a live Activity picker request and Greia's Shell UI.

The Activity transport never sees this host. It owns the exact-session native
modal lease, the profile-bound CreationLibrary, the shared Gallery Screen, and
restoration of Activity focus after one child selection or cancellation.
"""
from __future__ import annotations

from typing import Any

from greia_platform.creation_audio_pygame import PygameRecordingPreview
from greia_platform.creation_gallery import CreationsGalleryController, GalleryMode
from greia_platform.creation_gallery_screen import CreationsGalleryScreen
from greia_platform.creations import CreationLibrary
from greia_platform.ui_core import UiEventResult

from .lifecycle import ActivitySession, ActivitySessionState
from .shell_window import ShellActivityModalLease


class CreationPickerHostError(RuntimeError):
    """Trusted picker could not preserve Activity/display ownership."""


class ActivityCreationPickerHost:
    """One live Activity session's optional trusted Creations picker presenter."""

    def __init__(
        self,
        *,
        supervisor: Any,
        shell_window_backend: Any,
        session: ActivitySession,
        profile: Any,
        typography: Any,
        locale: str,
    ) -> None:
        self._supervisor = supervisor
        self._shell_window_backend = shell_window_backend
        self._session = session
        self._profile = profile
        self._typography = typography
        self._locale = locale
        self._lease: ShellActivityModalLease | None = None
        self._screen: CreationsGalleryScreen | None = None
        self._request_id: str | None = None
        self._prepared = False
        self._closed = False

    @property
    def prepared(self) -> bool:
        return self._prepared and self._lease is not None and not self._closed

    @property
    def visible(self) -> bool:
        return self._screen is not None and not self._closed

    def prepare(self, pygame: Any) -> bool:
        """Prove exact native Activity ownership before enabling requests."""
        if self._closed:
            return False
        if self.prepared:
            return True
        if (
            self._session.state is not ActivitySessionState.RUNNING
            or self._session.process is None
            or not isinstance(self._session.process.pid, int)
            or self._session.process.pid <= 0
        ):
            return False
        prepare = getattr(self._shell_window_backend, "prepare_activity_modal", None)
        if not callable(prepare):
            return False
        lease = prepare(
            pygame,
            session_id=self._session.session_id,
            activity_pid=self._session.process.pid,
        )
        if not isinstance(lease, ShellActivityModalLease):
            return False
        try:
            self._supervisor.enable_creation_picker(self._session)
        except Exception as exc:
            self._shell_window_backend.abandon_activity_modal(lease)
            raise CreationPickerHostError(
                "creation picker broker could not bind trusted presenter"
            ) from exc
        self._lease = lease
        self._prepared = True
        return True

    def service(self, pygame: Any, events: tuple[object, ...]) -> bool:
        """Process one Shell poll; return True only when a Shell frame was drawn."""
        if not self.prepared:
            return False
        if self._session.state is not ActivitySessionState.RUNNING:
            return False

        opened = False
        if self._screen is None:
            request = self._supervisor.pending_creation_selection(self._session)
            if request is None:
                return False
            self._open(pygame, request)
            opened = True
            # Never deliver input collected while the Activity still visibly
            # owned the screen to the newly raised picker.
            events = ()

        screen = self._screen
        if screen is None:
            return False

        dirty = opened
        for event in events:
            outcome = screen.handle_event(event)
            if outcome is not UiEventResult.IGNORED:
                dirty = True
            if outcome is UiEventResult.REQUEST_CLOSE:
                selected = screen.controller.selected_handle is not None
                self._close_visible(pygame, selected=selected)
                return False

        if screen.needs_frame():
            dirty = True
        if not dirty:
            return False
        surface = pygame.display.get_surface()
        if surface is None:
            raise CreationPickerHostError("Greia Shell has no drawable modal surface")
        screen.draw(surface)
        return True

    def _open(self, pygame: Any, request: Any) -> None:
        lease = self._lease
        if lease is None:
            raise CreationPickerHostError("creation picker has no native modal lease")
        request_id = getattr(request, "request_id", None)
        media_types = getattr(request, "media_types", ())
        roles = getattr(request, "roles", ())
        if not isinstance(request_id, str) or not request_id:
            raise CreationPickerHostError("creation picker received an invalid request")
        try:
            library = CreationLibrary(self._profile.creations_dir)
            controller = CreationsGalleryController(
                library,
                mode=GalleryMode.PICKER,
                media_types=frozenset(media_types),
                roles=frozenset(roles) if roles else None,
                on_pick=lambda creation_id: self._supervisor.complete_creation_selection(
                    self._session, request_id, creation_id
                ),
                audio_player=PygameRecordingPreview(),
            )
            screen = CreationsGalleryScreen(
                controller,
                typography=self._typography,
                locale=self._locale,
            )
        except Exception as exc:
            try:
                self._supervisor.cancel_creation_selection(
                    self._session, request_id
                )
            except Exception:
                pass
            raise CreationPickerHostError(
                "creation picker could not construct trusted child view"
            ) from exc

        if not self._shell_window_backend.show_activity_modal(lease):
            screen.on_exit()
            try:
                self._supervisor.cancel_creation_selection(
                    self._session, request_id
                )
            except Exception:
                pass
            raise CreationPickerHostError(
                "trusted Shell modal could not cover the Activity"
            )

        ensure_chrome = getattr(
            self._supervisor, "ensure_system_chrome_visible", None
        )
        if callable(ensure_chrome) and not ensure_chrome(self._session):
            screen.on_exit()
            self._shell_window_backend.dismiss_activity_modal(lease)
            try:
                self._supervisor.cancel_creation_selection(
                    self._session, request_id
                )
            except Exception:
                pass
            raise CreationPickerHostError(
                "mandatory Home chrome could not remain above the picker"
            )

        self._screen = screen
        self._request_id = request_id
        try:
            pygame.mouse.set_visible(True)
        except Exception:
            pass

    def _close_visible(self, pygame: Any, *, selected: bool) -> None:
        screen = self._screen
        request_id = self._request_id
        lease = self._lease
        self._screen = None
        self._request_id = None
        if screen is not None:
            screen.on_exit()
        if not selected and request_id is not None:
            try:
                self._supervisor.cancel_creation_selection(
                    self._session, request_id
                )
            except Exception as exc:
                raise CreationPickerHostError(
                    "creation picker cancellation was not accepted"
                ) from exc
        if lease is None or not self._shell_window_backend.dismiss_activity_modal(lease):
            raise CreationPickerHostError("Activity focus could not be restored")
        ensure_chrome = getattr(
            self._supervisor, "ensure_system_chrome_visible", None
        )
        if callable(ensure_chrome) and not ensure_chrome(self._session):
            raise CreationPickerHostError(
                "mandatory Home chrome could not be restored"
            )
        try:
            pygame.mouse.set_visible(False)
            pygame.event.clear()
        except Exception:
            pass

    def shutdown(self, pygame: Any, *, activity_alive: bool) -> bool:
        """Cancel/revoke UI authority and release every modal/audio resource."""
        if self._closed:
            return True
        self._closed = True
        screen = self._screen
        request_id = self._request_id
        selected = (
            screen is not None
            and screen.controller.selected_handle is not None
        )
        was_visible = screen is not None
        self._screen = None
        self._request_id = None
        clean = True
        if screen is not None:
            screen.on_exit()
        if request_id is not None and not selected:
            try:
                self._supervisor.cancel_creation_selection(
                    self._session, request_id
                )
            except Exception:
                clean = False
        try:
            self._supervisor.disable_creation_picker(self._session)
        except Exception:
            clean = False
        lease = self._lease
        if lease is not None:
            if activity_alive and was_visible:
                try:
                    clean = bool(
                        self._shell_window_backend.dismiss_activity_modal(lease)
                    ) and clean
                except Exception:
                    clean = False
            try:
                self._shell_window_backend.abandon_activity_modal(lease)
            except Exception:
                clean = False
        self._lease = None
        self._prepared = False
        try:
            pygame.mouse.set_visible(False)
            pygame.event.clear()
        except Exception:
            pass
        return clean


__all__ = ["ActivityCreationPickerHost", "CreationPickerHostError"]
