"""Child-Shell host for the one-time first-boot profile setup.

``FirstProfileSetupMixin`` adds one Shell mode, ``first_profile``, entered at
interactive readiness only when ``ProfileStore.first_profile_setup()`` reports
the untouched placeholder of a brand-new device (zero real child profiles).
Every later boot - and any device where a Parent has created or renamed a
child - shows the ordinary profile picker (AGENTS.md contract 16).

Authority stays where it was:

* the profile is written only by ``ProfileStore.complete_first_profile`` (the
  same platform store the Shell already owns for the placeholder); no Parent
  credential is involved because nothing exists yet to protect, and adding
  *more* children stays Parent-gated in the Parent panel/API;
* finishing lands on Home through the normal ``_activate_profile`` path - an
  explicit creation by the person at the device, never a silent resume;
* speech uses the Shell's single spoken-label channel (``ShellMixerLease``),
  prerecorded only, with ``locale -> base -> English -> silence`` fallback.

Any failure inside the wizard degrades to the ordinary picker (fail-soft).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import time
from typing import Any

from greia_platform.profiles import ProfileError
from greia_platform.system_language import SystemLanguageStore

from .first_profile_copy import FIRST_PROFILE_LOCALES, copy_locale, first_profile_clip
from .first_profile_wizard import FirstProfileStep, FirstProfileWizard


LOGGER = logging.getLogger(__name__)

FIRST_PROFILE_MODE = "first_profile"


def resolve_first_profile_locale() -> str:
    """Language for the setup wizard: explicit launch context, then device.

    Explicit ``GREIA_PROFILE_LOCALE``/``GREIA_DEVICE_LOCALE`` (simulator, test
    harnesses) win; on an installed Greia the persisted device language - the
    installer's choice until a parent changes it - is used. Unknown values fall
    back to the wizard's own base-language/English resolution.
    """

    for variable in ("GREIA_PROFILE_LOCALE", "GREIA_DEVICE_LOCALE"):
        explicit = (os.environ.get(variable) or "").strip()
        if explicit:
            return copy_locale(explicit)
    try:
        return copy_locale(SystemLanguageStore.from_environment().read().locale)
    except Exception:  # noqa: BLE001 - language lookup must never block setup
        return "en"


class ShellFirstProfileVoice:
    """Play wizard cues on the Shell's spoken-label player (fail-silent)."""

    def __init__(self, root: Path, player: Any, locale: str, pygame_module: Any) -> None:
        self._root = Path(root)
        self._player = player
        self._locale = locale
        self._pygame = pygame_module
        self._serial = 0

    def say(self, cue_id: str) -> bool:
        clip = first_profile_clip(self._root, cue_id, self._locale)
        if clip is None or self._player is None:
            return False
        # A fresh identity per request lets "replay" speak the same cue again;
        # the player still interrupts the previous line (one voice at a time).
        self._serial += 1
        try:
            return bool(self._player.announce(f"first_boot:{cue_id}:{self._serial}", clip, self._pygame))
        except Exception:  # noqa: BLE001 - optional speech
            return False

    def busy(self) -> bool:
        try:
            return bool(self._player is not None and self._player.is_busy())
        except Exception:  # noqa: BLE001
            return False


class FirstProfileSetupMixin:
    """Host the first-boot setup Screen inside the child Shell lifecycle."""

    def _first_profile_setup_enabled(self) -> bool:
        """Typed variation hook (a host that must never run setup returns False)."""

        return True

    # ------------------------------------------------------------ lifecycle
    def apply_prepared_state(self, state: Any) -> Any:
        result = super().apply_prepared_state(state)  # type: ignore[misc]
        self._begin_first_profile_setup_if_pending()
        return result

    def _begin_first_profile_setup_if_pending(self) -> bool:
        self._first_profile_screen = None
        self._first_profile_wizard = None
        if not self._first_profile_setup_enabled():
            return False
        store = getattr(self, "profile_store", None)
        if store is None:
            return False
        try:
            placeholder = store.first_profile_setup()
        except Exception:  # noqa: BLE001 - never block the picker
            return False
        if placeholder is None:
            return False
        self._first_profile_locale = resolve_first_profile_locale()
        self._mode = FIRST_PROFILE_MODE
        return True

    @property
    def first_profile_setup_active(self) -> bool:
        return getattr(self, "_mode", None) == FIRST_PROFILE_MODE

    def _first_profile_ensure_screen(self, pygame: Any) -> Any:
        screen = getattr(self, "_first_profile_screen", None)
        if screen is not None:
            return screen
        from .first_profile_screen import FirstProfileScreen

        spoken = getattr(self, "_spoken_labels", None)
        root = spoken.root if spoken is not None else Path(
            os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")
        )
        locale = getattr(self, "_first_profile_locale", None) or resolve_first_profile_locale()
        voice = ShellFirstProfileVoice(
            root, spoken.player if spoken is not None else None, locale, pygame
        )
        self._first_profile_voice = voice
        wizard = FirstProfileWizard(self.profile_store.policy, voice=voice)
        self._first_profile_wizard = wizard
        screen = FirstProfileScreen(
            wizard,
            typography=self._typography,
            commit=self._first_profile_commit,
            locale=locale,
            text_transform=self._child_display_text,
            avatar_icon=lambda avatar_id, size: self._load_icon(avatar_id, size, pygame),
            pose=self._first_profile_pose,
            backdrop=self._first_profile_backdrop,
            visual_resolver=self._first_profile_visual_resolver(),
            voice_busy=voice.busy,
        )
        self._first_profile_screen = screen
        screen.on_enter()
        return screen

    def _first_profile_commit(self, name: str, avatar_id: str, age: int | None) -> Any:
        return self.profile_store.complete_first_profile(name, avatar_id, approximate_age=age)

    def _first_profile_visual_resolver(self) -> Any:
        cache = getattr(self, "_visual_cache", None)
        catalogue = getattr(cache, "catalogue", None)
        if catalogue is None:
            return None

        def resolve(asset_id: str, variant: str) -> Path:
            return catalogue.get_visual(asset_id).path_for(variant)

        return resolve

    def _first_profile_pose(self, pose: str, size: int) -> Any:
        cache = getattr(self, "_visual_cache", None)
        if cache is None:
            return None
        return cache.get("character.leo", variant=pose, size=(size, size))

    def _first_profile_backdrop(self, size: tuple[int, int]) -> Any:
        """Opaque storybook meadow (same scene as the profile picker)."""

        import pygame

        if getattr(self, "_visual_cache", None) is None:
            return None
        surface = pygame.Surface(size)
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        theme = self.theme_controller.theme
        surface.fill(theme.background)
        draw = getattr(self, "_draw_shell_scene_backdrop", None)
        if draw is None:
            return None
        draw(surface, pygame, theme=theme)
        if getattr(self, "_shared_scene_disabled", False):
            return None
        return surface

    def _close_first_profile_setup(self, pygame: Any | None = None) -> None:
        screen = getattr(self, "_first_profile_screen", None)
        if screen is not None:
            screen.on_exit()
        self._first_profile_screen = None
        self._first_profile_wizard = None
        self._first_profile_voice = None
        if pygame is not None:
            try:
                pygame.key.stop_text_input()
            except Exception:  # noqa: BLE001
                pass
        if self.first_profile_setup_active:
            self._mode = "profiles"
            self._cached_profiles_key = None

    def _abandon_first_profile_setup(self, pygame: Any | None, exc: BaseException) -> None:
        LOGGER.warning("first-profile setup failed; showing the profile picker: %s", exc)
        self._close_first_profile_setup(pygame)

    def _finish_first_profile_setup(self, pygame: Any) -> None:
        wizard = getattr(self, "_first_profile_wizard", None)
        created = wizard.completed_profile if wizard is not None else None
        self._close_first_profile_setup(pygame)
        if created is None:
            return
        try:
            self.profiles = self.profile_store.list_profiles()
            match = next(p for p in self.profiles if p.profile_id == created.profile_id)
        except (ProfileError, StopIteration):
            return
        self._profile_selected = self.profiles.index(match)
        # Explicit creation by the person at the device: enter Home with it.
        self._activate_profile(match, pygame)

    def _sync_first_profile_text_input(self, pygame: Any) -> None:
        screen = getattr(self, "_first_profile_screen", None)
        try:
            if screen is not None and screen.wants_text_input:
                pygame.key.start_text_input()
            else:
                pygame.key.stop_text_input()
        except Exception:  # noqa: BLE001
            pass

    # --------------------------------------------------------------- hooks
    def _draw(self, screen: Any, pygame: Any) -> None:
        if not self.first_profile_setup_active:
            super()._draw(screen, pygame)  # type: ignore[misc]
            return
        self._targets.clear()
        try:
            view = self._first_profile_ensure_screen(pygame)
            view.draw(screen)
        except Exception as exc:  # noqa: BLE001 - fail soft to the picker
            self._abandon_first_profile_setup(pygame, exc)
            super()._draw(screen, pygame)  # type: ignore[misc]
            return
        self._sync_first_profile_text_input(pygame)
        self._draw_pointer(screen, pygame)

    def _handle_key(self, key: int, pygame: Any) -> bool:
        if not self.first_profile_setup_active:
            return super()._handle_key(key, pygame)  # type: ignore[misc]
        from greia_platform.ui_core import UiEventResult

        try:
            view = self._first_profile_ensure_screen(pygame)
            result = view.key(key)
        except Exception as exc:  # noqa: BLE001
            self._abandon_first_profile_setup(pygame, exc)
            return True
        if result is UiEventResult.REQUEST_CLOSE:
            self._finish_first_profile_setup(pygame)
        else:
            self._sync_first_profile_text_input(pygame)
        return True

    def _handle_click(self, position: tuple[int, int], pygame: Any) -> None:
        if not self.first_profile_setup_active:
            super()._handle_click(position, pygame)  # type: ignore[misc]
            return
        from greia_platform.ui_core import UiEventResult

        try:
            view = self._first_profile_ensure_screen(pygame)
            result = view.click(position)
        except Exception as exc:  # noqa: BLE001
            self._abandon_first_profile_setup(pygame, exc)
            return
        if result is UiEventResult.REQUEST_CLOSE:
            self._finish_first_profile_setup(pygame)
        else:
            self._sync_first_profile_text_input(pygame)

    def _handle_shell_text_input(self, text: str) -> bool:
        if not self.first_profile_setup_active:
            return super()._handle_shell_text_input(text)  # type: ignore[misc]
        screen = getattr(self, "_first_profile_screen", None)
        if screen is None:
            return False
        try:
            return bool(screen.text(text))
        except Exception:  # noqa: BLE001
            return False

    def _apply_coalesced_motion(self, position: tuple[int, int] | None) -> bool:
        if not self.first_profile_setup_active:
            return super()._apply_coalesced_motion(position)  # type: ignore[misc]
        if position is None:
            return False
        self._pointer_position = position
        screen = getattr(self, "_first_profile_screen", None)
        moved = True  # the synthetic pointer itself must be repainted
        if screen is not None:
            try:
                screen.pointer_move(position)
            except Exception:  # noqa: BLE001
                pass
        return moved

    def _present_ambient_frame(self, screen: Any, pygame: Any, now: float) -> bool:
        if not self.first_profile_setup_active:
            return super()._present_ambient_frame(screen, pygame, now)  # type: ignore[misc]
        view = getattr(self, "_first_profile_screen", None)
        if view is None:
            return False
        try:
            if view.celebration_done(now):
                self._finish_first_profile_setup(pygame)
                self._draw(screen, pygame)
                pygame.display.flip()
                return True
            if not view.needs_frame(now):
                return False
            self._draw(screen, pygame)
            pygame.display.flip()
            return True
        except Exception as exc:  # noqa: BLE001
            self._abandon_first_profile_setup(pygame, exc)
            return False

    def _ambient_wait_seconds(self, now: float) -> float | None:
        if not self.first_profile_setup_active:
            return super()._ambient_wait_seconds(now)  # type: ignore[misc]
        wizard = getattr(self, "_first_profile_wizard", None)
        if wizard is not None and wizard.step is FirstProfileStep.CELEBRATE:
            return 1.0 / 12.0
        return None

    def _rescan_profiles(self) -> bool:
        changed = super()._rescan_profiles()  # type: ignore[misc]
        if not self.first_profile_setup_active:
            return changed
        wizard = getattr(self, "_first_profile_wizard", None)
        if wizard is not None and wizard.finished:
            return changed
        try:
            pending = self.profile_store.first_profile_setup() is not None
        except Exception:  # noqa: BLE001
            pending = False
        if not pending:
            # A Parent created/renamed a child meanwhile: setup is over.
            import pygame

            self._close_first_profile_setup(pygame)
            return True
        return changed


__all__ = [
    "FIRST_PROFILE_LOCALES",
    "FIRST_PROFILE_MODE",
    "FirstProfileSetupMixin",
    "ShellFirstProfileVoice",
    "resolve_first_profile_locale",
]
