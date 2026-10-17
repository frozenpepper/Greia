"""Pygame Screen for the first-boot profile setup wizard (ADR 0018 / ADR 0037).

One full-screen ``ui_core.Screen`` renders the renderer-free
:class:`~greia_launcher.first_profile_wizard.FirstProfileWizard`. Controls come
from the shared Activity control kit (``ControlKit``: round/tile buttons, a
pill, focus ring, spatial keyboard/controller focus), art from the shared
catalogue (Leo poses, ``icon.hud.*`` glyphs, ``ui.keycap.space``, the avatar
frame and the profile avatar icons). Nothing here touches profile storage:
the host injects ``commit``.

Atom-floor rendering: everything static for a (step, size) pair - storybook
backdrop, heading pill, Leo, grown-up hint - is composed once into one opaque
display-format surface and replayed with a single fast blit. Kit controls are
cached per state by the painter; cast/avatar art is blitted through RLE copies
(``pygame_blit.PreparedSurfaces``). Only the celebration animates (12 fps,
bounded to a few seconds); every other frame is drawn on input only.
"""

from __future__ import annotations

from collections.abc import Callable
import math
import time
from typing import Any

import pygame

from greia_platform.activity_controls import (
    COCOA,
    INK,
    SURFACE,
    BodyShape,
    ButtonRole,
    ControlKit,
    ControlTheme,
    IconButton,
    KitControl,
    KitPointer,
    PillButton,
    PointerPhase,
)
from greia_platform.input_core import SemanticAction
from greia_platform.pygame_blit import PreparedSurfaces
from greia_platform.typography import FontRole
from greia_platform.ui_core import Screen, UiEventResult

from .first_profile_copy import first_profile_copy
from .first_profile_wizard import FirstProfileStep, FirstProfileWizard, ProfileCommit
from .shared_ui_presentation import draw_caption_pill


AvatarIcon = Callable[[str, int], "pygame.Surface | None"]
PoseProvider = Callable[[str, int], "pygame.Surface | None"]
Backdrop = Callable[[tuple[int, int]], "pygame.Surface | None"]

_BASE_LETTERS = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_SKY = (255, 248, 233)
_SOFT_PANEL = (255, 249, 236, 214)
_ARROW_KEYS = {
    pygame.K_LEFT: SemanticAction.NAV_LEFT,
    pygame.K_RIGHT: SemanticAction.NAV_RIGHT,
    pygame.K_UP: SemanticAction.NAV_UP,
    pygame.K_DOWN: SemanticAction.NAV_DOWN,
}
# Leo's pose per step (shared ``character.leo`` variants).
_STEP_POSE = {
    FirstProfileStep.WELCOME: "pose_wave",
    FirstProfileStep.NAME: "happy",
    FirstProfileStep.AVATAR: "happy",
    FirstProfileStep.AGE: "pose_think",
    FirstProfileStep.CHECK: "pose_point",
    FirstProfileStep.CELEBRATE: "pose_cheer",
}


class FirstProfileScreen(Screen):
    """Full-screen, mouse-first wizard surface with keyboard/controller focus."""

    CELEBRATE_MIN_SECONDS = 3.0
    CELEBRATE_MAX_SECONDS = 6.5
    CELEBRATE_SKIP_AFTER = 0.6
    ANIMATION_INTERVAL = 1.0 / 12.0

    def __init__(
        self,
        wizard: FirstProfileWizard,
        *,
        typography: Any,
        commit: ProfileCommit,
        locale: str | None = None,
        text_transform: Callable[[str], str] | None = None,
        avatar_icon: AvatarIcon | None = None,
        pose: PoseProvider | None = None,
        backdrop: Backdrop | None = None,
        visual_resolver: Callable[[str, str], Any] | None = None,
        voice_busy: Callable[[], bool] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.wizard = wizard
        self.copy = first_profile_copy(locale)
        self._typography = typography
        self._commit = commit
        self._transform = text_transform or (lambda text: text.upper())
        self._avatar_icon = avatar_icon
        self._pose = pose
        self._backdrop = backdrop
        self._voice_busy = voice_busy
        self._clock = clock
        self.kit = ControlKit(typography, ControlTheme(), resolver=visual_resolver)
        self.layer = self.kit.layer(layer_id="greia.first_profile")
        self._prepared = PreparedSurfaces(max_entries=24, max_pixels=1024 * 600 * 2)
        self._letters = _BASE_LETTERS + tuple(
            letter for letter in self.copy.extra_letters if letter not in _BASE_LETTERS
        )
        self._layout_key: tuple | None = None
        self._static: pygame.Surface | None = None
        self._geometry: dict[str, pygame.Rect] = {}
        self._controls: dict[str, KitControl] = {}
        self._celebrate_started: float | None = None
        self._last_animation_frame = 0.0
        self._size: tuple[int, int] | None = None
        self._closed = False
        self.error = False

    # ------------------------------------------------------------------ Screen
    @property
    def surface_id(self) -> str:
        return "greia.first_profile_setup"

    def on_enter(self) -> None:
        self.wizard.start()

    def on_exit(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.kit.clear()
        self._prepared.clear()
        self._static = None
        self._controls.clear()

    @property
    def wants_text_input(self) -> bool:
        """True while the name step owns physical text entry."""

        return not self._closed and self.wizard.step is FirstProfileStep.NAME

    def handle_event(self, event: object) -> UiEventResult:
        """Route one Pygame event (KEYDOWN, TEXTINPUT, mouse) to the wizard."""

        if self._closed:
            return UiEventResult.REQUEST_CLOSE
        kind = getattr(event, "type", None)
        if kind == pygame.KEYDOWN:
            return self.key(int(getattr(event, "key", -1)))
        if kind == pygame.TEXTINPUT:
            return UiEventResult.HANDLED if self.text(str(getattr(event, "text", ""))) else UiEventResult.IGNORED
        if kind == pygame.MOUSEMOTION:
            return UiEventResult.HANDLED if self.pointer_move(getattr(event, "pos", (-1, -1))) else UiEventResult.IGNORED
        if kind == pygame.MOUSEBUTTONUP and getattr(event, "button", 1) == 1:
            return self.click(getattr(event, "pos", (-1, -1)))
        return UiEventResult.IGNORED

    # ------------------------------------------------------------------ input
    def _refresh(self) -> None:
        # Several events can arrive in one frame: re-lay out after a step
        # change so the next event never hits the previous step's controls.
        if self._size is not None and not self._closed:
            self._ensure_layout(self._size)

    def key(self, key: int) -> UiEventResult:
        self._refresh()
        wizard = self.wizard
        if wizard.step is FirstProfileStep.CELEBRATE:
            return self._skip_celebration()
        action = _ARROW_KEYS.get(key)
        if action is not None:
            self.layer.navigate(action)
            return UiEventResult.HANDLED
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER) or key == pygame.K_SPACE:
            if self.layer.focus_visible and self.layer.focused_id is not None:
                target = self._controls.get(self.layer.focused_id)
                if target is not None:
                    target.activate()
                return self._result()
            if key == pygame.K_SPACE and wizard.step is FirstProfileStep.NAME:
                return UiEventResult.HANDLED  # TEXTINPUT types the space.
            self._primary()
            return self._result()
        if key == pygame.K_ESCAPE:
            wizard.back()
            return UiEventResult.HANDLED
        if key == pygame.K_BACKSPACE and wizard.step is FirstProfileStep.NAME:
            wizard.backspace()
            return UiEventResult.HANDLED
        return UiEventResult.IGNORED

    def text(self, text: str) -> bool:
        if self.wizard.step is not FirstProfileStep.NAME or not text:
            return False
        if text == " " and self.layer.focus_visible:
            return False  # Space already activated the focused control.
        changed = self.wizard.type_text(text)
        if changed:
            self.layer.focus(self.layer.focused_id, visible=False)
        return changed

    def pointer_move(self, position: tuple[int, int]) -> bool:
        if self._closed:
            return False
        self._refresh()
        return self.layer.handle_event(KitPointer(PointerPhase.MOVE, tuple(position))) is UiEventResult.HANDLED

    def click(self, position: tuple[int, int]) -> UiEventResult:
        self._refresh()
        if self.wizard.step is FirstProfileStep.CELEBRATE:
            return self._skip_celebration()
        target = self.layer.hit(tuple(position))
        if target is None:
            return UiEventResult.IGNORED
        self.layer.focus(target.control_id if target.focusable else None, visible=False)
        target.activate()
        return self._result()

    def activate(self, control_id: str) -> bool:
        """Activate a control by id (tests and scripted capture)."""

        self._refresh()
        target = self._controls.get(control_id)
        return bool(target is not None and target.activate())

    def control_ids(self) -> tuple[str, ...]:
        return tuple(self._controls)

    def control_rect(self, control_id: str) -> pygame.Rect:
        return self._controls[control_id].rect

    # ------------------------------------------------------------ animation
    def needs_frame(self, now: float | None = None) -> bool:
        """True only while the bounded celebration animation is running."""

        if self._closed or self.wizard.step is not FirstProfileStep.CELEBRATE:
            return False
        now = self._clock() if now is None else now
        return now - self._last_animation_frame >= self.ANIMATION_INTERVAL

    def celebration_done(self, now: float | None = None) -> bool:
        if self.wizard.step is not FirstProfileStep.CELEBRATE:
            return False
        now = self._clock() if now is None else now
        started = self._celebrate_started if self._celebrate_started is not None else now
        elapsed = now - started
        if elapsed >= self.CELEBRATE_MAX_SECONDS:
            return True
        if elapsed < self.CELEBRATE_MIN_SECONDS:
            return False
        busy = False
        if self._voice_busy is not None:
            try:
                busy = bool(self._voice_busy())
            except Exception:  # noqa: BLE001 - optional presentation probe
                busy = False
        return not busy

    # ---------------------------------------------------------------- draw
    def draw(self, target: object) -> None:
        assert isinstance(target, pygame.Surface)
        if self._closed:
            return
        size = target.get_size()
        self._size = size
        self._ensure_layout(size)
        if self._static is not None:
            target.blit(self._static, (0, 0))
        try:
            self._draw_dynamic(target)
        except (pygame.error, ValueError, OSError):
            self.error = True
        self._sync_selection()
        self.layer.draw(target)
        self._last_animation_frame = self._clock()

    # ------------------------------------------------------------ internals
    def _result(self) -> UiEventResult:
        return UiEventResult.HANDLED

    def _primary(self) -> None:
        wizard = self.wizard
        if wizard.step is FirstProfileStep.CHECK:
            self._confirm()
        else:
            wizard.next()

    def _confirm(self) -> None:
        profile = self.wizard.confirm(self._commit)
        if profile is not None:
            self._celebrate_started = self._clock()

    def _skip_celebration(self) -> UiEventResult:
        started = self._celebrate_started
        if started is not None and self._clock() - started < self.CELEBRATE_SKIP_AFTER:
            return UiEventResult.HANDLED
        return UiEventResult.REQUEST_CLOSE

    def _sync_selection(self) -> None:
        wizard = self.wizard
        for control_id, control in self._controls.items():
            if control_id.startswith("avatar:"):
                control.selected = control_id == f"avatar:{wizard.avatar_id}"
            elif control_id.startswith("age:"):
                control.selected = control_id == f"age:{wizard.approximate_age}"

    # -- layout --------------------------------------------------------
    def _ensure_layout(self, size: tuple[int, int]) -> None:
        key = (self.wizard.step, size)
        if key == self._layout_key and self._static is not None:
            return
        previous_focus = self.layer.focused_id if key[0] == (self._layout_key or (None,))[0] else None
        self._layout_key = key
        self._geometry = {}
        controls = self._build_controls(size)
        self._controls = {control.control_id: control for control in controls}
        self.layer.set_targets(controls)
        focus = previous_focus or self._default_focus()
        if focus is not None:
            self.layer.focus(focus, visible=False)
        self.layer.ensure_focus()
        self._static = self._build_static(size)

    def _default_focus(self) -> str | None:
        wizard = self.wizard
        step = wizard.step
        if step is FirstProfileStep.WELCOME:
            return "next"
        if step is FirstProfileStep.NAME:
            return f"key:{self._letters[0]}"
        if step is FirstProfileStep.AVATAR:
            return f"avatar:{wizard.avatar_id}"
        if step is FirstProfileStep.AGE:
            if wizard.approximate_age is not None:
                return f"age:{wizard.approximate_age}"
            return f"age:{wizard.age_choices[0]}" if wizard.age_choices else "skip"
        if step is FirstProfileStep.CHECK:
            return "next"
        return None

    @staticmethod
    def _scale(size: tuple[int, int]) -> float:
        return max(0.45, min(size[0] / 1024.0, size[1] / 600.0))

    def _metrics(self, size: tuple[int, int]) -> dict[str, int]:
        width, height = size
        s = self._scale(size)
        margin = max(8, round(16 * s))
        heading = max(40, round(62 * s))
        bar = max(52, round(84 * s))
        gap = max(5, round(10 * s))
        return {
            "w": width,
            "h": height,
            "m": margin,
            "heading": heading,
            "bar": bar,
            "gap": gap,
            "content_top": margin + heading + gap,
            "bar_top": height - margin - bar,
        }

    def _glyph(self, glyph_id: str, size: int, fallback: str) -> pygame.Surface:
        image = self.kit.glyph(glyph_id, size)
        if image is not None:
            return image
        return self.kit.text_icon(fallback, max(12, size), COCOA)

    def _build_controls(self, size: tuple[int, int]) -> list[KitControl]:
        g = self._metrics(size)
        kit = self.kit
        wizard = self.wizard
        step = wizard.step
        m, bar, gap = g["m"], g["bar"], g["gap"]
        controls: list[KitControl] = []
        if step is FirstProfileStep.CELEBRATE:
            return controls
        icon_px = max(22, round(bar * 0.52))
        # Replay Leo's line: always top-right, same place on every step.
        replay_size = g["heading"]
        controls.append(
            kit.icon_button(
                "replay",
                pygame.Rect(g["w"] - m - replay_size, m, replay_size, replay_size),
                icon=self._glyph("listen", max(18, round(replay_size * 0.55)), "?"),
                on_activate=wizard.replay,
            )
        )
        bar_top = g["bar_top"]
        if step is not FirstProfileStep.WELCOME:
            controls.append(
                kit.icon_button(
                    "back",
                    pygame.Rect(m, bar_top, bar, bar),
                    icon=self._glyph("arrow_left", icon_px, "<"),
                    on_activate=wizard.back,
                )
            )
        if step is FirstProfileStep.WELCOME:
            go = max(bar + 16, round(150 * self._scale(size)))
            right = pygame.Rect(g["w"] // 2, g["content_top"], g["w"] // 2 - m, bar_top - g["content_top"])
            rect = pygame.Rect(0, 0, go, go)
            rect.center = (right.centerx, right.centery + gap)
            controls.append(
                kit.icon_button(
                    "next",
                    rect,
                    icon=self._glyph("go", round(go * 0.5), ">"),
                    role=ButtonRole.PRIMARY,
                    on_activate=wizard.next,
                )
            )
            return controls
        next_icon = "check" if step is FirstProfileStep.CHECK else "arrow_right"
        controls.append(
            kit.icon_button(
                "next",
                pygame.Rect(g["w"] - m - bar, bar_top, bar, bar),
                icon=self._glyph(next_icon, icon_px, ">"),
                role=ButtonRole.PRIMARY,
                on_activate=self._confirm if step is FirstProfileStep.CHECK else wizard.next,
            )
        )
        if step is FirstProfileStep.NAME:
            controls.extend(self._name_controls(g))
        elif step is FirstProfileStep.AVATAR:
            controls.extend(self._avatar_controls(g))
        elif step is FirstProfileStep.AGE:
            controls.extend(self._age_controls(g))
        return controls

    def _name_controls(self, g: dict[str, int]) -> list[KitControl]:
        kit = self.kit
        wizard = self.wizard
        m, gap, bar = g["m"], g["gap"], g["bar"]
        field_h = max(44, round(g["heading"] * 1.2))
        field = pygame.Rect(m + bar + gap, g["content_top"], g["w"] - 2 * (m + bar + gap), field_h)
        self._geometry["field"] = field
        top = field.bottom + gap
        bottom = g["bar_top"] - gap
        letters = self._letters
        columns = 8 if len(letters) <= 32 else 9
        rows = math.ceil(len(letters) / columns)
        key_gap = max(4, round(gap * 0.8))
        cell_w = (g["w"] - 2 * m - (columns - 1) * key_gap) // columns
        cell_h = (bottom - top - (rows - 1) * key_gap) // rows
        key_h = max(28, min(cell_h, cell_w))
        key_w = max(28, min(cell_w, round(key_h * 1.5)))
        grid_w = columns * key_w + (columns - 1) * key_gap
        grid_h = rows * key_h + (rows - 1) * key_gap
        left = (g["w"] - grid_w) // 2
        top += max(0, (bottom - top - grid_h) // 2)
        label_px = max(14, round(key_h * 0.5))
        controls: list[KitControl] = []
        for index, letter in enumerate(letters):
            row, column = divmod(index, columns)
            rect = pygame.Rect(
                left + column * (key_w + key_gap), top + row * (key_h + key_gap), key_w, key_h
            )
            controls.append(
                kit.icon_button(
                    f"key:{letter}",
                    rect,
                    icon=kit.painter.label(letter, label_px, COCOA, role=FontRole.DISPLAY),
                    shape=BodyShape.TILE,
                    on_activate=lambda letter=letter: wizard.type_text(letter),
                )
            )
        # Space + delete sit together in the centre of the bottom bar.
        bar_top = g["bar_top"]
        space_w = max(bar * 2, round(bar * 2.6))
        space_icon = kit.art.fit("ui.keycap.space", max(18, round(bar * 0.5)))
        group_w = space_w + gap + bar
        start = (g["w"] - group_w) // 2
        controls.append(
            PillButton(
                kit.painter,
                "space",
                pygame.Rect(start, bar_top, space_w, bar),
                label="" if space_icon is not None else "_",
                icon=space_icon,
                on_activate=lambda: wizard.type_text(" "),
            )
        )
        controls.append(
            kit.icon_button(
                "delete",
                pygame.Rect(start + space_w + gap, bar_top, bar, bar),
                icon=self._glyph("undo", max(22, round(bar * 0.52)), "<"),
                on_activate=wizard.backspace,
            )
        )
        return controls

    def _tile_grid(
        self,
        g: dict[str, int],
        count: int,
        columns: int,
        *,
        top: int,
        bottom: int,
        max_tile: int,
    ) -> list[pygame.Rect]:
        m, gap = g["m"], g["gap"]
        rows = max(1, math.ceil(count / columns))
        tile = min(
            (g["w"] - 2 * m - (columns - 1) * gap) // columns,
            (bottom - top - (rows - 1) * gap) // rows,
            max_tile,
        )
        tile = max(36, tile)
        grid_w = columns * tile + (columns - 1) * gap
        grid_h = rows * tile + (rows - 1) * gap
        left = (g["w"] - grid_w) // 2
        y0 = top + max(0, (bottom - top - grid_h) // 2)
        rects = []
        for index in range(count):
            row, column = divmod(index, columns)
            rects.append(pygame.Rect(left + column * (tile + gap), y0 + row * (tile + gap), tile, tile))
        return rects

    def _avatar_controls(self, g: dict[str, int]) -> list[KitControl]:
        wizard = self.wizard
        avatars = wizard.avatars
        columns = min(6, max(1, len(avatars))) if len(avatars) > 4 else len(avatars)
        rects = self._tile_grid(
            g,
            len(avatars),
            columns,
            top=g["content_top"] + g["gap"],
            bottom=g["bar_top"] - g["gap"],
            max_tile=round(170 * self._scale((g["w"], g["h"]))),
        )
        controls: list[KitControl] = []
        for avatar_id, rect in zip(avatars, rects):
            icon = self._avatar(avatar_id, round(rect.width * 0.7))
            controls.append(
                self.kit.icon_button(
                    f"avatar:{avatar_id}",
                    rect,
                    icon=icon,
                    shape=BodyShape.TILE,
                    selected=avatar_id == wizard.avatar_id,
                    on_activate=lambda avatar_id=avatar_id: wizard.select_avatar(avatar_id),
                )
            )
        return controls

    def _age_controls(self, g: dict[str, int]) -> list[KitControl]:
        wizard = self.wizard
        kit = self.kit
        skip_h = max(40, round(g["bar"] * 0.8))
        bottom = g["bar_top"] - 2 * g["gap"] - skip_h
        ages = wizard.age_choices
        rects = self._tile_grid(
            g,
            len(ages),
            4,
            top=g["content_top"] + g["gap"],
            bottom=bottom,
            max_tile=round(150 * self._scale((g["w"], g["h"]))),
        )
        controls: list[KitControl] = []
        for age, rect in zip(ages, rects):
            controls.append(
                kit.icon_button(
                    f"age:{age}",
                    rect,
                    icon=kit.painter.label(str(age), max(18, round(rect.height * 0.5)), COCOA),
                    shape=BodyShape.TILE,
                    selected=age == wizard.approximate_age,
                    on_activate=lambda age=age: wizard.select_age(age),
                )
            )
        skip = PillButton(
            kit.painter,
            "skip",
            pygame.Rect(0, 0, 10, skip_h),
            label=self._transform(self.copy.skip),
            on_activate=wizard.skip_age,
        )
        width = min(g["w"] - 2 * g["m"], skip.preferred_width())
        last = rects[-1] if rects else pygame.Rect(0, g["content_top"], 0, 0)
        skip.rect = pygame.Rect((g["w"] - width) // 2, last.bottom + 2 * g["gap"], width, skip_h)
        controls.append(skip)
        return controls

    # -- art -------------------------------------------------------------
    def _avatar(self, avatar_id: str, size: int) -> pygame.Surface | None:
        if self._avatar_icon is None:
            return None
        try:
            return self._avatar_icon(avatar_id, max(16, int(size)))
        except Exception:  # noqa: BLE001 - optional art degrades to an empty tile
            return None

    def _leo(self, pose: str, size: int) -> pygame.Surface | None:
        if self._pose is None or size < 32:
            return None
        try:
            return self._pose(pose, int(size))
        except Exception:  # noqa: BLE001 - optional art
            return None

    def _blit(self, target: pygame.Surface, surface: pygame.Surface | None, rect_or_pos: Any) -> None:
        if surface is None:
            return
        target.blit(self._prepared.for_target(surface, target), rect_or_pos)

    def _label(self, text: str, size: int, *, max_width: int, role: FontRole = FontRole.DISPLAY) -> pygame.Surface:
        return self.kit.painter.label(text, size, COCOA, max_width=max(24, max_width), role=role)

    # -- static composition ------------------------------------------------
    def _new_surface(self, size: tuple[int, int]) -> pygame.Surface:
        surface = pygame.Surface(size)
        if pygame.display.get_init() and pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface

    def _build_static(self, size: tuple[int, int]) -> pygame.Surface:
        g = self._metrics(size)
        surface = self._new_surface(size)
        surface.fill(_SKY)
        backdrop = None
        if self._backdrop is not None:
            try:
                backdrop = self._backdrop(size)
            except Exception:  # noqa: BLE001 - optional storybook scene
                backdrop = None
        if backdrop is not None:
            surface.blit(backdrop, (0, 0))
        step = self.wizard.step
        s = self._scale(size)
        m = g["m"]
        width, height = size
        if step in (FirstProfileStep.NAME, FirstProfileStep.AVATAR, FirstProfileStep.AGE):
            # A soft cream sheet keeps letters and tiles readable over the meadow.
            sheet = pygame.Rect(m // 2, g["content_top"] - g["gap"] // 2, width - m, g["bar_top"] - g["content_top"])
            veil = pygame.Surface(sheet.size, pygame.SRCALPHA)
            pygame.draw.rect(veil, _SOFT_PANEL, veil.get_rect(), border_radius=max(12, round(24 * s)))
            surface.blit(veil, sheet.topleft)
        heading_text = {
            FirstProfileStep.WELCOME: self.copy.welcome,
            FirstProfileStep.NAME: self.copy.ask_name,
            FirstProfileStep.AVATAR: self.copy.ask_avatar,
            FirstProfileStep.AGE: self.copy.ask_age,
            FirstProfileStep.CHECK: self.copy.check,
            FirstProfileStep.CELEBRATE: self.copy.celebrate,
        }[step]
        heading_text = self._transform(heading_text)
        if step in (FirstProfileStep.WELCOME, FirstProfileStep.CHECK, FirstProfileStep.CELEBRATE):
            leo_size = min(round(height * 0.62), round(width * 0.40), round(330 * s) + 40)
            leo_rect = pygame.Rect(m, g["bar_top"] + g["bar"] - leo_size, leo_size, leo_size)
            self._geometry["leo"] = leo_rect
            self._blit_static(surface, self._leo(_STEP_POSE[step], leo_size), leo_rect.topleft)
            slot_left = leo_rect.right + g["gap"] if step is not FirstProfileStep.WELCOME else width // 2
            slot = pygame.Rect(slot_left, m, width - slot_left - m - g["heading"] - g["gap"], g["heading"])
            if step is FirstProfileStep.WELCOME:
                slot = pygame.Rect(width // 2, m + g["gap"], width // 2 - m, round(g["heading"] * 1.3))
            label = self._label(heading_text, round(slot.height * 0.62), max_width=slot.width - slot.height)
            draw_caption_pill(surface, pygame, slot, label, focused=step is FirstProfileStep.CELEBRATE)
        else:
            head = g["heading"]
            leo_rect = pygame.Rect(m, m - max(2, head // 10), round(head * 1.2), round(head * 1.2))
            self._blit_static(surface, self._leo(_STEP_POSE[step], leo_rect.width), leo_rect.topleft)
            slot = pygame.Rect(leo_rect.right + g["gap"], m, width - leo_rect.right - 2 * g["gap"] - m - head, head)
            label = self._label(heading_text, round(head * 0.58), max_width=slot.width - head)
            draw_caption_pill(surface, pygame, slot, label, focused=False)
        if step is FirstProfileStep.WELCOME:
            self._draw_hint(surface, g)
        return surface

    @staticmethod
    def _blit_static(surface: pygame.Surface, art: pygame.Surface | None, position: tuple[int, int]) -> None:
        # Composed once per (step, size) into the opaque static layer.
        if art is not None:
            surface.blit(art, position)

    def _draw_hint(self, surface: pygame.Surface, g: dict[str, int]) -> None:
        width = surface.get_width()
        left = width // 2
        box_w = width // 2 - g["m"]
        size = max(13, round(19 * self._scale(surface.get_size())))
        lines = self._wrap(self.copy.grown_up_hint, size, box_w - 2 * g["gap"])[:3]
        if not lines:
            return
        rendered = [self._typography.render(line, FontRole.BODY, size, COCOA) for line in lines]
        line_h = max(item.get_height() for item in rendered)
        box_h = line_h * len(rendered) + 2 * g["gap"]
        box = pygame.Rect(left, g["bar_top"] + g["bar"] - box_h, box_w, box_h)
        veil = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(veil, _SOFT_PANEL, veil.get_rect(), border_radius=max(8, g["gap"] * 2))
        surface.blit(veil, box.topleft)
        y = box.top + g["gap"]
        for item in rendered:
            surface.blit(item, item.get_rect(midtop=(box.centerx, y)))
            y += line_h

    def _wrap(self, text: str, size: int, max_width: int) -> list[str]:
        font = self._typography.font(FontRole.BODY, size)
        lines: list[str] = []
        current = ""
        for word in text.split():
            candidate = f"{current} {word}".strip()
            if not current or font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    # -- dynamic content ---------------------------------------------------
    def _draw_dynamic(self, target: pygame.Surface) -> None:
        step = self.wizard.step
        if step is FirstProfileStep.NAME:
            self._draw_name_field(target)
        elif step in (FirstProfileStep.CHECK, FirstProfileStep.CELEBRATE):
            self._draw_identity_card(target)
            if step is FirstProfileStep.CELEBRATE:
                self._draw_stars(target)

    def _draw_name_field(self, target: pygame.Surface) -> None:
        field = self._geometry.get("field")
        if field is None:
            return
        radius = field.height // 2
        pygame.draw.rect(target, (106, 81, 71), field.move(0, 3), border_radius=radius)
        pygame.draw.rect(target, SURFACE, field, border_radius=radius)
        pygame.draw.rect(target, INK, field, width=3, border_radius=radius)
        name = self.wizard.display_name
        size = round(field.height * 0.62)
        if name:
            label = self._label(self._transform(name), size, max_width=field.width - field.height)
            rect = label.get_rect(center=field.center)
            target.blit(label, rect)
            caret_x = min(field.right - radius // 2, rect.right + 6)
        else:
            caret_x = field.centerx
        caret_h = round(field.height * 0.56)
        pygame.draw.rect(
            target,
            (255, 160, 40),
            pygame.Rect(caret_x, field.centery - caret_h // 2, max(3, field.height // 16), caret_h),
            border_radius=2,
        )

    def _draw_identity_card(self, target: pygame.Surface) -> None:
        size = target.get_size()
        g = self._metrics(size)
        leo = self._geometry.get("leo", pygame.Rect(g["m"], 0, 0, 0))
        area = pygame.Rect(leo.right + g["gap"], g["content_top"], size[0] - leo.right - g["gap"] - g["m"], g["bar_top"] - g["content_top"] - g["gap"])
        frame_size = max(60, min(area.width - 2 * g["gap"], round(area.height * 0.68), round(240 * self._scale(size))))
        frame_rect = pygame.Rect(0, 0, frame_size, frame_size)
        frame_rect.midtop = (area.centerx, area.top)
        frame = self.kit.art.image("ui.avatar.frame", frame_size)
        if frame is not None:
            self._blit(target, frame, frame_rect)
            inner_center = (frame_rect.centerx, frame_rect.top + round(frame_rect.height * 123 / 260))
            avatar_size = round(frame_size * 0.53)
        else:
            pygame.draw.circle(target, SURFACE, frame_rect.center, frame_size // 2)
            pygame.draw.circle(target, INK, frame_rect.center, frame_size // 2, width=3)
            inner_center = frame_rect.center
            avatar_size = round(frame_size * 0.62)
        avatar = self._avatar(self.wizard.avatar_id, avatar_size)
        if avatar is not None:
            self._blit(target, avatar, avatar.get_rect(center=inner_center))
        age = self.wizard.approximate_age
        if age is not None:
            badge_r = max(16, frame_size // 8)
            center = (frame_rect.right - badge_r // 2, frame_rect.top + badge_r)
            pygame.draw.circle(target, (255, 194, 52), center, badge_r)
            pygame.draw.circle(target, INK, center, badge_r, width=3)
            digits = self._label(str(age), round(badge_r * 1.1), max_width=badge_r * 2)
            target.blit(digits, digits.get_rect(center=center))
        pill_h = max(40, round(g["heading"] * 1.05))
        slot = pygame.Rect(area.left, frame_rect.bottom + g["gap"], area.width, pill_h)
        label = self._label(self._transform(self.wizard.display_name), round(pill_h * 0.62), max_width=area.width - pill_h)
        draw_caption_pill(target, pygame, slot, label, focused=True)
        if self.wizard.commit_failed and self.wizard.step is FirstProfileStep.CHECK:
            note = self._label(self._transform(self.copy.try_again), max(14, round(pill_h * 0.4)), max_width=area.width, role=FontRole.TITLE)
            target.blit(note, note.get_rect(midtop=(area.centerx, slot.bottom + g["gap"])))
        self._geometry["card"] = frame_rect

    def _draw_stars(self, target: pygame.Surface) -> None:
        card = self._geometry.get("card")
        if card is None:
            return
        now = self._clock()
        phase = int(now * 4) % 2
        base = max(18, card.width // 6)
        # Five stars hug the avatar frame (never the heading or screen edge).
        positions = (
            (card.left - base // 2, card.top + base),
            (card.right + base // 2, card.top + base // 2),
            (card.left - base * 2 // 3, card.bottom - base),
            (card.right + base * 2 // 3, card.bottom - base // 2),
            (card.left + base // 3, card.centery),
        )
        for index, (x, y) in enumerate(positions):
            size = base if (index + phase) % 2 == 0 else round(base * 0.7)
            star = self.kit.star(size)
            self._blit(target, star, star.get_rect(center=(x, y)))
