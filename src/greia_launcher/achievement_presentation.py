from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from greia_platform.achievements import (
    AchievementEntry,
    AchievementError,
    AchievementSnapshot,
)
from greia_platform.history import HistoryError
from greia_platform.localization import LocalizationError, shared_character_audio_path
from greia_platform.pygame_achievements import (
    PygameAchievementBadgeRenderer,
    award_family,
)
from greia_platform.typography import FontRole
from greia_platform.ui_core import BoundedCache

from .achievement_celebration import (
    BADGE_REST_SIZE,
    FLIGHT_BADGE_SIZES,
    FRAME_FPS,
    INTRO_BADGE_SIZES,
    CelebrationFrame,
    CelebrationPhase,
    CelebrationTimeline,
    LibraryHop,
)
from .achievement_localization import (
    achievement_ui_strings,
    resolve_achievement_locale,
)
from .catalogue_view import ALL_ACTIVITIES_ID
from .home_layout import achievement_button_rect
from .main import HitTarget
from .profile_chrome_presentation import greeter_character_for

logger = logging.getLogger(__name__)

# Shared award frame renditions (assets/catalog/shared_visuals_v1_source.toml):
# native sizes and their variant names. The renderer scales the nearest larger
# rendition once into its own bounded cache.
_AWARD_RENDITIONS = ((64, "size_64"), (112, "size_112"), (160, "default"))

# Shared character cues (accepted v0.2 library) used by the badge moments.
CUE_CELEBRATE = "celebrate.success"
CUE_PRAISE = "praise.general"
CUE_ENCOURAGE = "encourage.progress"
VOICE_COOLDOWN_SECONDS = 3.0

# Trophy-shelf palette, derived from runtime/theme-defaults.toml tokens and
# the SVG ink (docs/design/GREIA_SVG_AUTHORING_RULES.md §2).
_INK = (75, 55, 47)  # ink #4B372F
_SHELF_BACK = (238, 221, 186)  # sand #EEDDBA
_SHELF_FRAME = (184, 119, 53)  # orange mixed 35% with ink
_PLANK_TOP = (233, 172, 108)  # orange mixed 25% with white
_PLANK_FRONT = (196, 128, 58)  # orange mixed 25% with ink
_FLOOR = (247, 235, 203)  # cream #F7EBCB
_SKY = (207, 234, 247)  # sky #CFEAF7
# Badge centre on the 310 px-tall celebration card (title/eyebrow keep clear).
_BADGE_Y = 122


@dataclass(slots=True)
class _ActiveCelebration:
    """One badge's celebration: timing plus the few cached things it paints.

    ``backdrop_valid`` says whether the launcher's restore surface still holds
    the Home frame (without star/card) for this celebration's dirty frames.
    """

    entry: AchievementEntry
    timeline: CelebrationTimeline
    voiced: bool
    phase: CelebrationPhase = CelebrationPhase.INTRO
    phase_started: float = 0.0
    cheered: bool = False
    landed: bool = False
    presented: CelebrationFrame | None = None
    rects: list[Any] = field(default_factory=list)
    backdrop_valid: bool = False
    fx: tuple[Any, ...] = ()
    text: tuple[Any, ...] | None = None


@dataclass(frozen=True, slots=True)
class _ShelfLayout:
    """Trophy-shelf geometry for one viewport (8 badges per page)."""

    back: Any
    count: Any
    cabinet: Any
    planks: tuple[Any, ...]
    slots: tuple[Any, ...]
    badge_centers: tuple[tuple[int, int], ...]
    badge_size: int
    detail: Any
    greeter: Any


class AchievementLibraryMixin:
    """Profile-owned Badge Library ("trophy shelf") and badge celebration.

    This presentation layer never decides whether an achievement is earned. It
    reads only ``ProfileAchievementService`` snapshots composed by the trusted
    launcher. Activity processes cannot invoke this UI or mutate its state.

    Historical/reconstructed unlocks appear as NEW in the library but are not
    replayed as a popup queue on profile activation. Celebrations are for
    achievements earned during the Activity session that just returned control
    to the Shell. Animated frames are presented through the Shell loop's
    incremental frame hook (``_present_ambient_frame``) as small dirty
    rectangles; while the card waits for the child and while the library is
    idle the loop presents nothing.
    """

    _ACHIEVEMENTS_PER_PAGE = 8
    _SHELF_COLUMNS = 4
    # After a refresh failure the draw path must not reopen the history
    # database every frame; one retry per interval is enough for recovery.
    _ACHIEVEMENT_REFRESH_RETRY_SECONDS = 5.0
    _achievement_retry_at = 0.0
    _achievement_failure_logged = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._achievement_snapshot: AchievementSnapshot | None = None
        self._achievement_retry_at = 0.0
        self._achievement_failure_logged = False
        self._achievement_selected = 0
        self._achievement_library_seen_ids: tuple[str, ...] = ()
        self._achievement_queue: list[AchievementEntry] = []
        self._achievement_celebration: _ActiveCelebration | None = None
        self._achievement_badges = PygameAchievementBadgeRenderer(
            self._load_icon, frame_provider=self._achievement_award_frame
        )
        self._achievement_locale = resolve_achievement_locale()
        self._achievement_clock = time.monotonic
        self._achievement_star_focused = False
        self._achievement_star_return_index = 0
        self._achievement_capturing = False
        self._achievement_backdrop: Any = None
        self._achievement_hop: LibraryHop | None = None
        self._achievement_hop_presented: int | None = None
        self._achievement_voice_ready_at = 0.0
        self._achievement_greeter_pose = "pose_point"
        self._achievement_shelf_surface: Any = None
        self._achievement_shelf_key: tuple[Any, ...] | None = None
        self._achievement_detail_cache: BoundedCache[tuple[Any, ...], Any] = BoundedCache(8)
        # Incremental frames actually presented (tests/perf evidence).
        self._achievement_frames_presented = 0

    # ------------------------------------------------------------ services
    @property
    def _achievement_service(self) -> Any | None:
        services = getattr(self, "runtime_services", None)
        return None if services is None else getattr(services, "achievement_service", None)

    def _refresh_achievement_locale(self) -> str:
        """Refresh presentation locale at explicit Shell transition boundaries."""

        self._achievement_locale = resolve_achievement_locale()
        return self._achievement_locale

    def _achievement_award_frame(
        self, family: str, locked: bool, size: int, pygame: Any
    ) -> Any | None:
        """Frame provider: the nearest-larger ``ui.award.<family>`` rendition."""

        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is None:
            return None
        native, variant = next(
            ((px, name) for px, name in _AWARD_RENDITIONS if px >= size),
            _AWARD_RENDITIONS[-1],
        )
        if locked:
            variant = "locked" if variant == "default" else f"locked_{native}"
        return visual_cache.get(
            f"ui.award.{family}", variant=variant, size=(native, native)
        )

    def _activate_profile(self, profile: Any, pygame: Any) -> None:
        super()._activate_profile(profile, pygame)
        self._achievement_selected = 0
        self._achievement_retry_at = 0.0
        self._achievement_star_focused = False
        self._achievement_hop = None
        self._refresh_achievement_locale()
        # Do not replay historical/reconstructed achievements as a popup storm.
        self._refresh_achievements()

    def _logout(self, pygame: Any) -> None:
        self._achievement_snapshot = None
        self._achievement_queue.clear()
        self._achievement_celebration = None
        self._achievement_library_seen_ids = ()
        self._achievement_star_focused = False
        self._achievement_hop = None
        self._achievement_badges.clear()
        self._achievement_shelf_surface = None
        self._achievement_shelf_key = None
        self._achievement_backdrop = None
        super()._logout(pygame)

    def _launch_selected(self, pygame: Any) -> None:
        snapshot = getattr(self, "_achievement_snapshot", None)
        before = {
            entry.definition.achievement_id
            for entry in (
                snapshot.entries
                if snapshot is not None
                else ()
            )
            if entry.unlocked
        }
        super()._launch_selected(pygame)
        if getattr(self, "_active_profile", None) is None:
            return
        self._refresh_achievement_locale()
        snapshot = self._refresh_achievements()
        if snapshot is None:
            return
        new_entries = [
            entry
            for entry in snapshot.entries
            if entry.unlocked
            and entry.definition.achievement_id not in before
            and entry.announced_at is None
        ]
        self._queue_achievement_announcements(new_entries, pygame)

    def _refresh_achievements(self) -> AchievementSnapshot | None:
        service = self._achievement_service
        profile = getattr(self, "_active_profile", None)
        if service is None or profile is None:
            self._achievement_snapshot = None
            return None
        if time.monotonic() < self._achievement_retry_at:
            return None
        try:
            snapshot = service.refresh(profile)
        except (AchievementError, HistoryError, OSError, ValueError) as exc:
            # Achievements are read-side enrichment: a broken or unreadable
            # history store must never take down the child Shell. Log once,
            # hide the badge UI, and retry at a bounded interval.
            if not self._achievement_failure_logged:
                self._achievement_failure_logged = True
                logger.warning(
                    "Achievements unavailable for the active profile: %s", exc
                )
            self._achievement_snapshot = None
            self._achievement_retry_at = (
                time.monotonic() + self._ACHIEVEMENT_REFRESH_RETRY_SECONDS
            )
            return None
        self._achievement_failure_logged = False
        self._achievement_snapshot = snapshot
        return snapshot

    # ------------------------------------------------------- celebration
    def _queue_achievement_announcements(
        self,
        entries: list[AchievementEntry],
        pygame: Any,
    ) -> None:
        known = {item.definition.achievement_id for item in self._achievement_queue}
        if self._achievement_celebration is not None:
            known.add(self._achievement_celebration.entry.definition.achievement_id)
        for entry in entries:
            if entry.definition.achievement_id not in known:
                self._achievement_queue.append(entry)
                known.add(entry.definition.achievement_id)
        if self._achievement_celebration is None and self._achievement_queue:
            # A new queue: only its first badge gets the full intro and voice.
            self._start_next_celebration(pygame, first=True)

    def _start_next_celebration(self, pygame: Any, *, first: bool) -> None:
        entry = self._achievement_queue.pop(0)
        family = award_family(entry.definition.tier, secret=entry.definition.secret)
        grand = family in {"gold", "special"}
        fx = self._celebration_fx(grand)
        timeline = CelebrationTimeline(
            first=first, sparkle_frames=3 if grand and fx else 2
        )
        now = self._achievement_clock()
        celebration = _ActiveCelebration(
            entry=entry,
            timeline=timeline,
            voiced=first,
            phase_started=now,
            fx=fx,
        )
        self._achievement_celebration = celebration
        self._achievement_star_focused = False
        # Prepare every badge size this celebration can show now, so no frame
        # ever scales or composes art (bounded renderer cache).
        for size in (*INTRO_BADGE_SIZES, *FLIGHT_BADGE_SIZES):
            try:
                self._achievement_badges.render(entry, size, pygame)
            except Exception:  # noqa: BLE001 - decorative preparation only
                break
        self._greeter_react("surprised", now)
        if not self._achievement_loop_drives_frames():
            self._run_achievement_phase_blocking(pygame)

    def _celebration_fx(self, grand: bool) -> tuple[Any, ...]:
        """Pre-scaled sparkle sprites (gold/secret: star bursts + confetti)."""

        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is None:
            return ()
        if grand:
            wanted = (
                ("fx.star_burst", ("default", "frame_2", "frame_3"), 56),
                ("fx.confetti", ("default", "frame_2", "frame_3"), 56),
            )
        else:
            wanted = (("fx.sparkle", ("default", "frame_2"), 48),)
        sprites: list[Any] = []
        try:
            for asset_id, variants, px in wanted:
                for variant in variants:
                    sprites.append(visual_cache.get(asset_id, variant=variant, size=(px, px)))
        except Exception:  # noqa: BLE001 - sparkles are optional decoration
            return ()
        return tuple(sprites)

    def _achievement_loop_drives_frames(self) -> bool:
        """Whether the Shell loop calls the incremental ``_present_ambient_frame``."""

        return any(
            "_present_ambient_frame" in vars(cls)
            for cls in type(self).__mro__
            if cls is not AchievementLibraryMixin
        )

    def _run_achievement_phase_blocking(self, pygame: Any) -> None:
        """Fallback for a Shell loop without the incremental frame hook.

        Plays the current animated phase (≤ 0.56 s) with the same dirty-rect
        frames, then returns. Never used when the loop drives frames.
        """

        screen = pygame.display.get_surface()
        if screen is None:
            return
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            celebration = self._achievement_celebration
            if celebration is None or celebration.phase in {
                CelebrationPhase.WAITING,
                CelebrationPhase.DONE,
            }:
                return
            now = self._achievement_clock()
            self._present_achievement_frame(screen, pygame, now)
            wait = self._achievement_wait_seconds(self._achievement_clock())
            time.sleep(max(0.005, min(1.0 / FRAME_FPS, wait if wait is not None else 0.0)))

    def _greeter_react(self, kind: str, now: float) -> None:
        """Ask the Home animator (when present) for a greeter reaction."""

        animator = getattr(self, "_home_animator", None)
        if not animator:
            return
        try:
            animator.react(kind, now)
        except TypeError:
            try:
                animator.react(kind)
            except Exception:  # noqa: BLE001 - optional presentation
                pass
        except Exception:  # noqa: BLE001 - optional presentation
            pass

    def _play_greeter_cue(self, cue_id: str, pygame: Any) -> bool:
        """Play one accepted shared clip for the profile's greeter.

        Never interrupts anything audible (spoken labels, other character
        speech); system mute/volume apply because playback uses the Shell's
        single narration channel on the shared mixer.
        """

        controller = getattr(self, "_spoken_labels", None)
        profile = getattr(self, "_active_profile", None)
        if controller is None or profile is None:
            return False
        root = getattr(controller, "root", None) or getattr(controller, "_root", None)
        if root is None:
            return False
        character = greeter_character_for(getattr(profile.profile, "avatar_id", None))
        try:
            locale = self._spoken_locale()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            locale = self._achievement_locale
        try:
            clip = shared_character_audio_path(Path(root), character, cue_id, locale)
        except (LocalizationError, OSError, ValueError):
            return False
        if clip is None:
            return False
        player = controller.player
        play_if_idle = getattr(player, "play_if_idle", None)
        try:
            if callable(play_if_idle):
                return bool(play_if_idle(clip, pygame))
            if pygame.mixer.get_init() and pygame.mixer.get_busy():
                return False
            return bool(
                player.announce(f"achievement:{cue_id}:{time.monotonic_ns()}", clip, pygame)
            )
        except Exception:  # noqa: BLE001 - speech is optional presentation
            return False

    def _celebration_tick(self, now: float, pygame: Any) -> None:
        """Advance phase transitions and one-shot moments (voice, landing)."""

        celebration = self._achievement_celebration
        if celebration is None:
            return
        elapsed = now - celebration.phase_started
        timeline = celebration.timeline
        if celebration.phase is CelebrationPhase.INTRO:
            if not celebration.cheered and elapsed >= timeline.reveal_at:
                celebration.cheered = True
                self._greeter_react("cheer", now)
                if celebration.voiced:
                    self._play_greeter_cue(CUE_CELEBRATE, pygame)
            if elapsed >= timeline.intro_seconds:
                celebration.phase = CelebrationPhase.WAITING
        elif celebration.phase is CelebrationPhase.FLIGHT:
            frame = timeline.flight_frame(elapsed)
            if frame.landed and not celebration.landed:
                celebration.landed = True
            if elapsed >= timeline.flight_seconds:
                celebration.phase = CelebrationPhase.DONE

    def _current_celebration_frame(self, now: float) -> CelebrationFrame | None:
        celebration = self._achievement_celebration
        if celebration is None:
            return None
        elapsed = now - celebration.phase_started
        timeline = celebration.timeline
        if celebration.phase is CelebrationPhase.INTRO:
            return timeline.intro_frame(elapsed)
        if celebration.phase is CelebrationPhase.WAITING:
            return timeline.resting_frame
        if celebration.phase is CelebrationPhase.FLIGHT:
            return timeline.flight_frame(elapsed)
        return timeline.landed_frame

    def _dismiss_achievement_celebration(self, pygame: Any) -> None:
        """Child tapped/pressed: the badge flies into the star."""

        celebration = self._achievement_celebration
        if celebration is None or celebration.phase in {
            CelebrationPhase.FLIGHT,
            CelebrationPhase.DONE,
        }:
            return
        profile = self._active_profile
        service = self._achievement_service
        if profile is not None and service is not None:
            try:
                service.mark_announced(
                    profile,
                    celebration.entry.definition.achievement_id,
                )
            except (AchievementError, OSError, ValueError):
                pass
        now = self._achievement_clock()
        celebration.cheered = True
        celebration.phase = CelebrationPhase.FLIGHT
        celebration.phase_started = now
        self._greeter_react("happy", now)
        if not self._achievement_loop_drives_frames():
            self._run_achievement_phase_blocking(pygame)
            self._finish_celebration_if_done(pygame)

    def _finish_celebration_if_done(self, pygame: Any) -> bool:
        celebration = self._achievement_celebration
        if celebration is None or celebration.phase is not CelebrationPhase.DONE:
            return False
        self._achievement_celebration = None
        if self._achievement_queue:
            self._start_next_celebration(pygame, first=False)
        else:
            self._refresh_achievements()
        return True

    def _achievement_display_count(self, snapshot: AchievementSnapshot) -> int:
        """Star count, holding back badges that have not flown in yet."""

        pending = len(self._achievement_queue)
        celebration = self._achievement_celebration
        if celebration is not None and not celebration.landed:
            pending += 1
        return max(0, snapshot.unlocked_count - pending)

    # ------------------------------------------------- incremental frames
    def _present_ambient_frame(self, screen: Any, pygame: Any, now: float) -> bool:
        parent = getattr(super(), "_present_ambient_frame", None)
        presented = bool(parent(screen, pygame, now)) if callable(parent) else False
        mine = self._present_achievement_frame(screen, pygame, now)
        return presented or mine

    def _ambient_wait_seconds(self, now: float) -> float | None:
        parent = getattr(super(), "_ambient_wait_seconds", None)
        waits = [
            value
            for value in (
                parent(now) if callable(parent) else None,
                self._achievement_wait_seconds(now),
            )
            if value is not None
        ]
        return min(waits) if waits else None

    def _achievement_wait_seconds(self, now: float) -> float | None:
        """Seconds until the next badge frame (``None`` = nothing animating)."""

        if self._mode == "achievements":
            hop = self._achievement_hop
            if hop is None:
                return None
            return 0.0 if hop.finished(now) else hop.next_change(now)
        celebration = self._achievement_celebration
        if celebration is None:
            return None
        elapsed = now - celebration.phase_started
        if celebration.phase is CelebrationPhase.INTRO:
            change = celebration.timeline.next_intro_change(elapsed)
        elif celebration.phase is CelebrationPhase.FLIGHT:
            change = celebration.timeline.next_flight_change(elapsed)
        elif celebration.phase is CelebrationPhase.DONE:
            change = 0.0
        else:
            return None
        return 0.0 if change is None else change

    def _present_achievement_frame(self, screen: Any, pygame: Any, now: float) -> bool:
        if self._mode == "achievements":
            return self._present_library_hop(screen, pygame, now)
        self._celebration_tick(now, pygame)
        if self._finish_celebration_if_done(pygame):
            celebration = self._achievement_celebration
            if celebration is None:
                # Last badge landed: settle the star at rest in one frame.
                return self._present_rest_star(screen, pygame)
        celebration = self._achievement_celebration
        if celebration is None or self._mode != "activities":
            return False
        frame = self._current_celebration_frame(now)
        if frame is None or frame == celebration.presented:
            return False
        if not celebration.backdrop_valid:
            self._capture_achievement_backdrop(screen, pygame)
            celebration.backdrop_valid = True
        backdrop = self._achievement_backdrop
        if backdrop is None:
            return False
        rects = self._celebration_rects(screen, pygame, frame)
        dirty = [rect.clip(screen.get_rect()) for rect in (*celebration.rects, *rects)]
        dirty = [rect for rect in dirty if rect.width > 0 and rect.height > 0]
        for rect in dirty:
            screen.blit(backdrop, rect.topleft, rect)
        self._paint_celebration(screen, pygame, frame)
        dirty.extend(self._repaint_pointer_over(screen, pygame, dirty))
        pygame.display.update(dirty)
        celebration.presented = frame
        celebration.rects = rects
        self._achievement_frames_presented += 1
        return True

    def _present_rest_star(self, screen: Any, pygame: Any) -> bool:
        snapshot = self._achievement_snapshot
        backdrop = self._achievement_backdrop
        if snapshot is None or backdrop is None or self._mode != "activities":
            return False
        rect = self._star_dirty_rect(screen, pygame)
        screen.blit(backdrop, rect.topleft, rect)
        self._draw_achievement_library_button(screen, self.theme_controller.theme, pygame)
        dirty = [rect, *self._repaint_pointer_over(screen, pygame, [rect])]
        pygame.display.update(dirty)
        self._achievement_frames_presented += 1
        return True

    def _capture_achievement_backdrop(self, screen: Any, pygame: Any) -> None:
        """Copy the Home frame *without* star, card or pointer for restores.

        Allocated once per screen size and reused. Afterwards the star and
        pointer are drawn back so the back buffer matches what is on screen.
        """

        self._achievement_capturing = True
        try:
            AchievementLibraryMixin._draw_base(self, screen, pygame)
        finally:
            self._achievement_capturing = False
        backdrop = self._achievement_backdrop
        if backdrop is None or backdrop.get_size() != screen.get_size():
            self._achievement_backdrop = screen.copy()
        else:
            backdrop.blit(screen, (0, 0))
        if self._achievement_snapshot is not None:
            self._draw_achievement_library_button(
                screen, self.theme_controller.theme, pygame
            )
        self._draw_pointer(screen, pygame)

    def _draw_base(self, screen: Any, pygame: Any) -> None:
        super(AchievementLibraryMixin, self)._draw(screen, pygame)

    def _repaint_pointer_over(
        self, screen: Any, pygame: Any, dirty: list[Any]
    ) -> list[Any]:
        if not self._is_pointer_active(pygame):  # type: ignore[attr-defined]
            return []
        x, y = self._pointer_pos(pygame)  # type: ignore[attr-defined]
        pointer = pygame.Rect(int(x) - 13, int(y) - 13, 27, 27)
        if not any(pointer.colliderect(rect) for rect in dirty):
            return []
        self._draw_pointer(screen, pygame)
        return [pointer.clip(screen.get_rect())]

    def _draw_pointer(self, screen: Any, pygame: Any) -> None:
        if self._achievement_capturing:
            return
        super()._draw_pointer(screen, pygame)

    # ---------------------------------------------------- celebration paint
    def _celebration_card_geometry(self, screen: Any, pygame: Any) -> tuple[Any, float]:
        width, height = screen.get_size()
        panel_w = min(520, width - 70)
        panel_h = min(310, height - 70)
        full = pygame.Rect(0, 0, panel_w, panel_h)
        full.center = screen.get_rect().center
        return full, panel_h / 310.0

    def _star_rect(self, screen: Any, pygame: Any) -> Any:
        corner = achievement_button_rect(screen.get_width(), screen.get_height())
        return pygame.Rect(corner.x, corner.y, corner.width, corner.height)

    def _star_dirty_rect(self, screen: Any, pygame: Any) -> Any:
        star = self._star_rect(screen, pygame)
        grown = star.inflate(int(star.width * 0.36) + 14, int(star.height * 0.36) + 14)
        return grown.clip(screen.get_rect())

    def _celebration_badge_center(
        self, screen: Any, pygame: Any, frame: CelebrationFrame
    ) -> tuple[int, int]:
        full, k = self._celebration_card_geometry(screen, pygame)
        rest = (full.centerx, full.top + int(_BADGE_Y * k))
        if frame.card_scale is not None:
            scale = frame.card_scale
            top = full.centery - int(full.height * scale) // 2
            return (full.centerx, top + int(_BADGE_Y * k * scale))
        if frame.flight is not None:
            star = self._star_rect(screen, pygame).center
            t = frame.flight
            # A gentle upward arc reads as "flying into the star".
            lift = int(math.sin(t * math.pi) * 40)
            return (
                int(rest[0] + (star[0] - rest[0]) * t),
                int(rest[1] + (star[1] - rest[1]) * t) - lift,
            )
        return rest

    def _sparkle_positions(
        self, center: tuple[int, int], badge_size: int
    ) -> tuple[tuple[int, int], ...]:
        radius = badge_size // 2 + 34
        angles = (150, 190, 228, 312, 350, 30)
        return tuple(
            (
                center[0] + int(math.cos(math.radians(angle)) * radius),
                center[1] + int(math.sin(math.radians(angle)) * radius * 0.8),
            )
            for angle in angles
        )

    def _celebration_rects(
        self, screen: Any, pygame: Any, frame: CelebrationFrame
    ) -> list[Any]:
        rects: list[Any] = []
        full, _k = self._celebration_card_geometry(screen, pygame)
        if frame.card_scale is not None:
            card = pygame.Rect(
                0, 0, int(full.width * frame.card_scale), int(full.height * frame.card_scale)
            )
            card.center = full.center
            rects.append(card)
        center = self._celebration_badge_center(screen, pygame, frame)
        if frame.badge_size is not None:
            badge = pygame.Rect(0, 0, frame.badge_size, frame.badge_size)
            badge.center = center
            rects.append(badge)
        celebration = self._achievement_celebration
        if frame.sparkle_frame is not None and celebration is not None and celebration.fx:
            size = celebration.fx[0].get_width()
            for x, y in self._sparkle_positions(center, frame.badge_size or BADGE_REST_SIZE):
                rects.append(pygame.Rect(x - size // 2, y - size // 2, size, size))
        if frame.card_scale is None:
            rects.append(self._star_dirty_rect(screen, pygame))
        return rects

    def _paint_celebration(
        self, screen: Any, pygame: Any, frame: CelebrationFrame
    ) -> None:
        celebration = self._achievement_celebration
        if celebration is None:
            return
        theme = self.theme_controller.theme
        entry = celebration.entry
        full, k = self._celebration_card_geometry(screen, pygame)
        center = self._celebration_badge_center(screen, pygame, frame)

        if frame.card_scale is None:
            # Flight: the star bounces in its corner and shows the new count.
            self._draw_achievement_library_button(
                screen, theme, pygame, scale=frame.star_scale
            )
        else:
            card = pygame.Rect(
                0, 0, int(full.width * frame.card_scale), int(full.height * frame.card_scale)
            )
            card.center = full.center
            radius = max(12, int(28 * frame.card_scale))
            # Opaque card; no full-screen alpha blend over the launcher.
            pygame.draw.rect(screen, theme.panel, card, border_radius=radius)
            pygame.draw.rect(screen, theme.accent, card, width=6, border_radius=radius)
            if frame.show_text:
                for index in range(12):
                    if index in (2, 3, 4, 8, 9, 10):
                        continue  # keep the eyebrow and title clear
                    angle = index * math.tau / 12.0
                    inner, outer = 72, 92
                    pygame.draw.line(
                        screen,
                        theme.accent,
                        (center[0] + int(math.cos(angle) * inner), center[1] + int(math.sin(angle) * inner)),
                        (center[0] + int(math.cos(angle) * outer), center[1] + int(math.sin(angle) * outer)),
                        width=5,
                    )
                self._paint_celebration_text(screen, pygame, full, k)

        if frame.badge_size is not None:
            badge = self._achievement_badges.render(entry, frame.badge_size, pygame)
            screen.blit(badge, badge.get_rect(center=center))

        if frame.sparkle_frame is not None and celebration.fx:
            fx = celebration.fx
            frames = celebration.timeline.sparkle_frames
            groups = max(1, len(fx) // frames)
            positions = self._sparkle_positions(center, frame.badge_size or BADGE_REST_SIZE)
            for index, (x, y) in enumerate(positions):
                group = index % groups
                sprite = fx[group * frames + (frame.sparkle_frame + index) % frames]
                screen.blit(sprite, sprite.get_rect(center=(x, y)))

    def _paint_celebration_text(self, screen: Any, pygame: Any, full: Any, k: float) -> None:
        celebration = self._achievement_celebration
        if celebration is None:
            return
        if celebration.text is None:
            theme = self.theme_controller.theme
            copy = achievement_ui_strings(self._achievement_locale)
            entry = celebration.entry
            eyebrow = self._typography.font(FontRole.CONTROL, 19).render(
                copy.new_badge, True, theme.accent
            )
            title = self._fit_text(
                self._child_display_text(
                    entry.definition.title.resolve(self._achievement_locale)
                ),
                max_width=full.width - 50,
                size=28,
                color=theme.text,
            )
            description = self._child_display_text(
                entry.definition.description.resolve(self._achievement_locale)
            )
            lines = tuple(
                self._typography.font(FontRole.BODY, 18).render(line, True, theme.text)
                for line in self._wrap_text(description, max_width=full.width - 60, size=18)[:2]
            )
            celebration.text = (eyebrow, title, *lines)
        eyebrow, title, *lines = celebration.text
        screen.blit(eyebrow, eyebrow.get_rect(center=(full.centerx, full.top + int(24 * k))))
        screen.blit(title, title.get_rect(center=(full.centerx, full.top + int(222 * k))))
        y = full.top + int(258 * k)
        for rendered in lines:
            screen.blit(rendered, rendered.get_rect(center=(full.centerx, y)))
            y += rendered.get_height() + 3

    # ------------------------------------------------------- library open
    def _open_achievement_library(self) -> None:
        self._refresh_achievement_locale()
        snapshot = self._refresh_achievements()
        if snapshot is None:
            return
        self._achievement_selected = 0
        self._achievement_hop = None
        self._achievement_greeter_pose = "pose_point"
        self._achievement_library_seen_ids = tuple(
            entry.definition.achievement_id
            for entry in snapshot.entries
            if entry.unlocked
        )
        self._mode = "achievements"

    def _close_achievement_library(self) -> None:
        service = self._achievement_service
        profile = self._active_profile
        if service is not None and profile is not None:
            try:
                service.mark_seen(profile, self._achievement_library_seen_ids)
            except (AchievementError, OSError, ValueError):
                pass
        self._achievement_library_seen_ids = ()
        self._achievement_hop = None
        self._refresh_achievements()
        self._mode = "activities"

    def _tap_achievement_badge(self, index: int, pygame: Any) -> None:
        """Select a shelf badge: it hops and the greeter says one kind word."""

        entries = self._achievement_visible_entries()
        if not 0 <= index < len(entries):
            return
        self._achievement_selected = index
        now = self._achievement_clock()
        layout = self._shelf_layout_for_display(pygame)
        amplitude = 1.0 if layout is None else layout.badge_size / 110.0
        self._achievement_hop = LibraryHop(index, now, amplitude)
        self._achievement_hop_presented = None
        unlocked = entries[index].unlocked
        self._achievement_greeter_pose = "happy" if unlocked else "pose_think"
        if now >= self._achievement_voice_ready_at:
            if self._play_greeter_cue(CUE_PRAISE if unlocked else CUE_ENCOURAGE, pygame):
                self._achievement_voice_ready_at = now + VOICE_COOLDOWN_SECONDS

    # ------------------------------------------------------------ input
    def _home_star_route_active(self) -> bool:
        return (
            self._mode == "activities"
            and getattr(self, "_category_id", None) == ALL_ACTIVITIES_ID
            and self._achievement_service is not None
            and self._active_profile is not None
            and self._achievement_snapshot is not None
        )

    def _focus_achievement_star(self) -> None:
        self._achievement_star_return_index = max(
            0, getattr(self, "_home_collection_selected", 0)
        )
        self._achievement_star_focused = True
        # One selection marker on screen: no portal wears the focus ring
        # while the star is focused (index -1 matches no portal).
        self._home_collection_selected = -1
        self._cached_activities_key = None

    def _unfocus_achievement_star(self, index: int | None = None) -> None:
        if not self._achievement_star_focused:
            return
        self._achievement_star_focused = False
        target = self._achievement_star_return_index if index is None else index
        setter = getattr(self, "_set_home_collection_selected", None)
        if callable(setter):
            setter(target)
        else:
            self._home_collection_selected = max(0, target)
        self._cached_activities_key = None

    def _handle_home_star_key(self, key: int, pygame: Any) -> bool | None:
        """Keyboard/controller route to the Badge Library from Home.

        Returns None when the key is not part of the star route.
        """

        if not self._home_star_route_active():
            self._unfocus_achievement_star()
            return None
        collections_fn = getattr(self, "_home_collections", None)
        collections = collections_fn() if callable(collections_fn) else ()
        columns_fn = getattr(self, "_home_columns", None)
        columns = max(1, columns_fn(pygame)) if callable(columns_fn) else 3
        if self._achievement_star_focused:
            if key in {pygame.K_RETURN, pygame.K_SPACE}:
                self._open_achievement_library()
            elif key == pygame.K_TAB:
                # Focus cycle: portals -> star -> greeter (when the Home
                # animator offers it) -> first portal.
                enter_greeter = getattr(self, "_enter_greeter_focus", None)
                animator = getattr(self, "_home_animator", None)
                if callable(enter_greeter) and getattr(animator, "greeter_rect", None) is not None:
                    self._achievement_star_focused = False
                    self._home_collection_selected = 0
                    enter_greeter()
                else:
                    self._unfocus_achievement_star(0)
            elif key in {pygame.K_DOWN, pygame.K_LEFT}:
                self._unfocus_achievement_star(min(columns, len(collections)) - 1)
            elif key in {pygame.K_ESCAPE, pygame.K_BACKSPACE}:
                self._unfocus_achievement_star()
            return True
        if not collections or getattr(self, "_home_greeter_focused", False):
            return None
        selected = getattr(self, "_home_collection_selected", 0)
        if (key == pygame.K_TAB and selected >= len(collections) - 1) or (
            key == pygame.K_UP and selected < columns
        ):
            self._focus_achievement_star()
            return True
        return None

    def _handle_key(self, key: int, pygame: Any) -> bool:
        if self._achievement_celebration is not None:
            if key in {
                pygame.K_RETURN,
                pygame.K_SPACE,
                pygame.K_ESCAPE,
                pygame.K_BACKSPACE,
            }:
                self._dismiss_achievement_celebration(pygame)
            return True
        if self._mode != "achievements":
            handled = self._handle_home_star_key(key, pygame)
            if handled is not None:
                return handled
            return super()._handle_key(key, pygame)

        entries = self._achievement_visible_entries()
        columns = self._SHELF_COLUMNS
        if key in {pygame.K_ESCAPE, pygame.K_BACKSPACE}:
            self._close_achievement_library()
        elif entries and key in {pygame.K_RETURN, pygame.K_SPACE}:
            self._tap_achievement_badge(self._achievement_selected, pygame)
        elif entries and key in {pygame.K_LEFT, pygame.K_UP}:
            delta = -1 if key == pygame.K_LEFT else -columns
            self._select_achievement(self._achievement_selected + delta, entries)
        elif entries and key in {pygame.K_RIGHT, pygame.K_DOWN, pygame.K_TAB}:
            delta = 1 if key in {pygame.K_RIGHT, pygame.K_TAB} else columns
            self._select_achievement(self._achievement_selected + delta, entries)
        return True

    def _select_achievement(self, index: int, entries: tuple[AchievementEntry, ...]) -> None:
        self._achievement_selected = min(max(0, index), len(entries) - 1)
        self._achievement_hop = None
        self._achievement_greeter_pose = "pose_point"

    def _handle_click(self, position: tuple[int, int], pygame: Any) -> None:
        if self._achievement_celebration is not None:
            self._dismiss_achievement_celebration(pygame)
            return
        if self._mode == "achievements":
            for target in reversed(self._targets):
                if not target.rect.collidepoint(position):
                    continue
                if target.action == "achievement_back":
                    self._close_achievement_library()
                    return
                if target.action == "achievement_entry":
                    self._tap_achievement_badge(int(target.value), pygame)
                    return
                if target.action == "achievement_page_prev":
                    self._achievement_selected = max(
                        0,
                        (self._achievement_selected // self._ACHIEVEMENTS_PER_PAGE - 1)
                        * self._ACHIEVEMENTS_PER_PAGE,
                    )
                    self._achievement_hop = None
                    return
                if target.action == "achievement_page_next":
                    entries = self._achievement_visible_entries()
                    self._achievement_selected = min(
                        max(0, len(entries) - 1),
                        (self._achievement_selected // self._ACHIEVEMENTS_PER_PAGE + 1)
                        * self._ACHIEVEMENTS_PER_PAGE,
                    )
                    self._achievement_hop = None
                    return
            return

        for target in reversed(self._targets):
            if (
                target.rect.collidepoint(position)
                and target.action == "achievement_library"
            ):
                self._achievement_star_focused = False
                self._open_achievement_library()
                return
        if self._achievement_star_focused:
            self._unfocus_achievement_star()
        super()._handle_click(position, pygame)

    # ------------------------------------------------------------- draw
    def _draw(self, screen: Any, pygame: Any) -> None:
        now = self._achievement_clock()
        if self._mode == "achievements":
            self._targets.clear()
            theme = self.theme_controller.theme
            self._draw_achievement_library(screen, theme, pygame)
            self._draw_pointer(screen, pygame)
            hop = self._achievement_hop
            self._achievement_hop_presented = None if hop is None else hop.offset(now)
            return
        self._celebration_tick(now, pygame)
        self._finish_celebration_if_done(pygame)
        super()._draw(screen, pygame)
        celebration = self._achievement_celebration
        if celebration is not None:
            frame = self._current_celebration_frame(now)
            if frame is not None:
                self._paint_celebration(screen, pygame, frame)
                celebration.presented = frame
                celebration.rects = self._celebration_rects(screen, pygame, frame)
            # The full frame changed the Home under the card: recapture the
            # restore surface before the next incremental frame.
            celebration.backdrop_valid = False
            # Base Shell draws its pointer before this mixin; redraw it last so
            # the child cursor never disappears behind the celebration card.
            self._draw_pointer(screen, pygame)

    def _draw_activities(self, screen: Any, theme: Any, pygame: Any) -> None:
        """Add the profile badge-library route after any Activity/Home projection.

        Hooking the complete activities surface, rather than only
        ``_render_activities_content``, keeps the route present even when an
        earlier adaptive-discovery mixin intentionally renders a sub-Collection
        chooser without delegating farther down the content chain.
        """

        super()._draw_activities(screen, theme, pygame)
        if self._achievement_service is None or self._active_profile is None:
            return
        if (
            (getattr(self, "_last_result", None) and not self._last_result.succeeded)
            or getattr(self, "_catalogue_error", False)
        ):
            return
        if self._achievement_capturing:
            # Backdrop capture: keep the hit target, leave the pixels empty.
            snapshot = self._achievement_snapshot
            if snapshot is not None:
                self._targets.append(
                    HitTarget(
                        "achievement_library",
                        None,
                        self._star_rect(screen, pygame).inflate(8, 8),
                    )
                )
            return
        self._draw_achievement_library_button(screen, theme, pygame)

    def _draw_achievement_library_button(
        self, screen: Any, theme: Any, pygame: Any, *, scale: float = 1.0
    ) -> None:
        snapshot = self._achievement_snapshot or self._refresh_achievements()
        if snapshot is None:
            return
        base = self._star_rect(screen, pygame)
        rect = base
        if scale != 1.0:
            rect = base.inflate(int(base.width * (scale - 1.0)), int(base.height * (scale - 1.0)))
        size = rect.width
        focused = self._achievement_star_focused and self._home_star_route_active()
        if focused:
            ring = rect.inflate(10, 10)
            pygame.draw.rect(screen, (255, 255, 255), ring, border_radius=26)
            pygame.draw.rect(screen, theme.accent, ring, width=5, border_radius=26)
        pygame.draw.rect(screen, theme.panel, rect, border_radius=20)
        pygame.draw.rect(screen, theme.accent, rect, width=6 if focused else 4, border_radius=20)
        icon = self._load_icon("yellow_star", max(30, size - 24), pygame)
        screen.blit(
            self._star_presentable(icon, screen),
            icon.get_rect(center=(rect.centerx, rect.centery - 4)),
        )
        # The star is repainted on every Home frame (pointer moves included):
        # keep its count label instead of re-rendering the text each time.
        count_key = (
            str(self._achievement_display_count(snapshot)),
            max(12, base.width // 5),
            tuple(theme.text),
        )
        cached_count = getattr(self, "_star_count_label", None)
        if cached_count is not None and cached_count[0] == count_key:
            count = cached_count[1]
        else:
            count = self._typography.font(FontRole.CONTROL, count_key[1]).render(
                count_key[0], True, theme.text
            )
            self._star_count_label = (count_key, count)
        pill = pygame.Rect(
            0,
            0,
            max(22, count.get_width() + 10),
            max(20, count.get_height() + 4),
        )
        pill.bottomright = (rect.right + 2, rect.bottom + 2)
        pygame.draw.rect(screen, theme.accent, pill, border_radius=pill.height // 2)
        screen.blit(count, count.get_rect(center=pill.center))
        if scale == 1.0:
            self._targets.append(
                HitTarget("achievement_library", None, rect.inflate(8, 8))
            )

    def _star_presentable(self, icon: Any, screen: Any) -> Any:
        """The star icon's RLE copy for the opaque screen (Atom alpha-blit cost)."""

        fast = getattr(self, "_star_fast", None)
        if fast is None:
            from greia_platform.pygame_blit import PreparedSurfaces

            fast = self._star_fast = PreparedSurfaces(max_entries=4, max_pixels=256 * 256)
        try:
            return fast.for_target(icon, screen)
        except Exception:  # noqa: BLE001 - presentation must never fail Home
            return icon

    def _achievement_visible_entries(self) -> tuple[AchievementEntry, ...]:
        snapshot = self._achievement_snapshot
        return () if snapshot is None else snapshot.visible_entries

    # ------------------------------------------------------ trophy shelf
    def _shelf_layout(self, width: int, height: int, pygame: Any) -> _ShelfLayout:
        s = max(0.5, min(width / 1024.0, height / 600.0))
        back_size = max(54, min(68, height // 9))
        back = pygame.Rect(14, 12, back_size, back_size)
        count = pygame.Rect(0, 0, int(118 * s), back_size - 8)
        count.midright = (width - 16, back.centery)
        greeter_px = int(130 * s)
        detail_h = max(78, int(104 * s))
        detail = pygame.Rect(0, 0, 0, detail_h)
        detail.left = 14 + greeter_px
        detail.width = width - detail.left - 16
        detail.bottom = height - 10
        greeter = pygame.Rect(8, height - greeter_px - 4, greeter_px, greeter_px)
        side = max(int(66 * s), 48)
        cabinet = pygame.Rect(side + 6, back.bottom + 10, width - 2 * (side + 6), 0)
        cabinet.height = detail.top - 10 - cabinet.top
        inner_top = cabinet.top + int(14 * s)
        row_h = (cabinet.bottom - int(14 * s) - inner_top) // 2
        badge = max(56, min(int(110 * s), row_h - int(52 * s)))
        plank_h = max(10, int(18 * s))
        column_w = (cabinet.width - int(20 * s)) // self._SHELF_COLUMNS
        planks: list[Any] = []
        slots: list[Any] = []
        centers: list[tuple[int, int]] = []
        for row in range(2):
            plank_top = inner_top + (row + 1) * row_h - int(26 * s)
            planks.append(
                pygame.Rect(cabinet.left + int(8 * s), plank_top, cabinet.width - int(16 * s), plank_h)
            )
            for column in range(self._SHELF_COLUMNS):
                left = cabinet.left + int(10 * s) + column * column_w
                center = (left + column_w // 2, plank_top - badge // 2 - 2)
                centers.append(center)
                slots.append(
                    pygame.Rect(
                        left + 6,
                        plank_top - badge - int(46 * s),
                        column_w - 12,
                        badge + int(46 * s) + int(8 * s),
                    )
                )
        return _ShelfLayout(
            back=back,
            count=count,
            cabinet=cabinet,
            planks=tuple(planks),
            slots=tuple(slots),
            badge_centers=tuple(centers),
            badge_size=badge,
            detail=detail,
            greeter=greeter,
        )

    def _shelf_layout_for_display(self, pygame: Any) -> _ShelfLayout | None:
        surface = pygame.display.get_surface()
        if surface is None:
            return None
        return self._shelf_layout(surface.get_width(), surface.get_height(), pygame)

    def _shelf_backdrop(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
        layout: _ShelfLayout,
        *,
        page_index: int,
        total_pages: int,
        count: int,
    ) -> Any:
        """Static trophy-room surface; rebuilt only when its content changes."""

        width, height = screen.get_size()
        key = (
            (width, height),
            self._achievement_locale,
            count,
            page_index,
            total_pages,
            tuple(theme.panel),
            tuple(theme.accent),
            tuple(theme.text),
            id(getattr(self, "_visual_cache", None)),
        )
        surface = self._achievement_shelf_surface
        if surface is not None and self._achievement_shelf_key == key:
            return surface
        if surface is None or surface.get_size() != (width, height):
            surface = pygame.Surface((width, height)).convert() if pygame.display.get_surface() else pygame.Surface((width, height))
        self._achievement_shelf_surface = surface
        self._achievement_shelf_key = key

        # The child's meadow behind the shelf (one cached opaque blit; no live
        # scene, no alpha layer). Without shared art: a sky band over cream.
        sky = self._shelf_sky(width, height, pygame)
        if sky is not None:
            # The landscape rendition leaves the sky transparent: the theme
            # background is the sky colour, exactly as on Home.
            surface.fill(theme.background)
            surface.blit(sky, (0, 0))
        else:
            surface.fill(_FLOOR)
            surface.fill(_SKY, pygame.Rect(0, 0, width, int(height * 0.5)))

        cabinet = layout.cabinet
        s = layout.badge_size / 110.0
        pygame.draw.rect(surface, _SHELF_FRAME, cabinet, border_radius=int(30 * s))
        pygame.draw.rect(surface, _INK, cabinet, width=3, border_radius=int(30 * s))
        inner = cabinet.inflate(-int(22 * s), -int(22 * s))
        pygame.draw.rect(surface, _SHELF_BACK, inner, border_radius=int(22 * s))
        pygame.draw.rect(surface, _INK, inner, width=2, border_radius=int(22 * s))
        for plank in layout.planks:
            top = pygame.Rect(plank.left, plank.top, plank.width, max(5, plank.height // 2))
            front = pygame.Rect(plank.left, top.bottom, plank.width, plank.height - top.height + 4)
            pygame.draw.rect(surface, _PLANK_FRONT, front, border_radius=6)
            pygame.draw.rect(surface, _INK, front, width=2, border_radius=6)
            pygame.draw.rect(surface, _PLANK_TOP, top, border_radius=6)
            pygame.draw.rect(surface, _INK, top, width=2, border_radius=6)
            for bracket_x in (plank.left + plank.width // 5, plank.right - plank.width // 5):
                bracket = pygame.Rect(0, 0, int(16 * s), int(16 * s))
                bracket.midtop = (bracket_x, front.bottom - 2)
                pygame.draw.polygon(
                    surface,
                    _PLANK_FRONT,
                    (bracket.topleft, bracket.topright, bracket.midbottom),
                )
                pygame.draw.polygon(
                    surface,
                    _INK,
                    (bracket.topleft, bracket.topright, bracket.midbottom),
                    width=2,
                )

        # Back button (top-left, unchanged position).
        back = layout.back
        pygame.draw.rect(surface, theme.panel, back, border_radius=18)
        pygame.draw.rect(surface, theme.accent, back, width=4, border_radius=18)
        points = (
            (back.centerx + 10, back.top + 14),
            (back.centerx - 10, back.centery),
            (back.centerx + 10, back.bottom - 14),
        )
        pygame.draw.lines(surface, theme.text, False, points, width=6)

        copy = achievement_ui_strings(self._achievement_locale)
        title = self._fit_text(
            copy.library_title,
            max_width=max(120, layout.count.left - back.right - 40),
            size=max(22, min(32, height // 18)),
            color=_INK,
        )
        pill = title.get_rect(center=(width // 2, back.centery)).inflate(36, 14)
        pygame.draw.rect(surface, (255, 251, 235), pill, border_radius=pill.height // 2)
        pygame.draw.rect(surface, _INK, pill, width=2, border_radius=pill.height // 2)
        surface.blit(title, title.get_rect(center=pill.center))

        # Unlocked count as a star pill: the number of badges the child has,
        # never "x of y" (no deficit framing).
        count_rect = layout.count
        pygame.draw.rect(surface, theme.accent, count_rect, border_radius=count_rect.height // 2)
        pygame.draw.rect(surface, _INK, count_rect, width=2, border_radius=count_rect.height // 2)
        star_px = max(24, count_rect.height - 10)
        star = self._load_icon("yellow_star", star_px, pygame)
        surface.blit(star, star.get_rect(midleft=(count_rect.left + 8, count_rect.centery)))
        number = self._typography.font(FontRole.CONTROL, max(18, count_rect.height // 2 + 4)).render(
            str(count), True, theme.accent_text
        )
        surface.blit(
            number,
            number.get_rect(
                center=(
                    (count_rect.left + 8 + star_px + count_rect.right) // 2,
                    count_rect.centery,
                )
            ),
        )

        if page_index > 0:
            self._draw_page_arrow(surface, theme, pygame, left=True, action=None)
        if page_index + 1 < total_pages:
            self._draw_page_arrow(surface, theme, pygame, left=False, action=None)
        return surface

    def _shelf_sky(self, width: int, height: int, pygame: Any) -> Any | None:
        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is None:
            return None
        try:
            return visual_cache.get("bg.meadow_day.home", variant="default", size=(width, height))
        except Exception:  # noqa: BLE001 - decorative backdrop
            return None

    def _draw_achievement_library(
        self, screen: Any, theme: Any, pygame: Any
    ) -> None:
        snapshot = self._refresh_achievements()
        entries = () if snapshot is None else snapshot.visible_entries
        width, height = screen.get_size()
        layout = self._shelf_layout(width, height, pygame)
        per_page = self._ACHIEVEMENTS_PER_PAGE
        if entries:
            self._achievement_selected = min(self._achievement_selected, len(entries) - 1)
        page_index = self._achievement_selected // per_page if entries else 0
        total_pages = max(1, (len(entries) + per_page - 1) // per_page)
        count = 0 if snapshot is None else snapshot.unlocked_count
        backdrop = self._shelf_backdrop(
            screen,
            theme,
            pygame,
            layout,
            page_index=page_index,
            total_pages=total_pages,
            count=count,
        )
        screen.blit(backdrop, (0, 0))
        self._targets.append(HitTarget("achievement_back", None, layout.back))
        if page_index > 0:
            self._targets.append(
                HitTarget("achievement_page_prev", None, self._page_arrow_rect(screen, pygame, left=True))
            )
        if page_index + 1 < total_pages:
            self._targets.append(
                HitTarget("achievement_page_next", None, self._page_arrow_rect(screen, pygame, left=False))
            )

        self._draw_shelf_greeter(screen, pygame, layout)
        if not entries:
            copy = achievement_ui_strings(self._achievement_locale)
            empty = self._typography.font(
                FontRole.BODY, max(20, height // 24)
            ).render(self._child_display_text(copy.empty_library), True, _INK)
            screen.blit(empty, empty.get_rect(center=layout.cabinet.center))
            return

        now = self._achievement_clock()
        page_start = page_index * per_page
        for local_index, entry in enumerate(entries[page_start : page_start + per_page]):
            global_index = page_start + local_index
            self._paint_shelf_slot(screen, pygame, layout, local_index, entry, global_index, now)
            self._targets.append(
                HitTarget("achievement_entry", global_index, layout.slots[local_index])
            )
        self._paint_shelf_detail(screen, theme, pygame, layout, entries[self._achievement_selected])

    def _paint_shelf_slot(
        self,
        screen: Any,
        pygame: Any,
        layout: _ShelfLayout,
        local_index: int,
        entry: AchievementEntry,
        global_index: int,
        now: float,
    ) -> None:
        theme = self.theme_controller.theme
        slot = layout.slots[local_index]
        center = layout.badge_centers[local_index]
        size = layout.badge_size
        if global_index == self._achievement_selected:
            ring = slot.inflate(-4, -4)
            pygame.draw.rect(screen, theme.accent, ring, width=5, border_radius=22)
        hop = self._achievement_hop
        dy = hop.offset(now) if hop is not None and hop.index == global_index else 0
        shadow = self._shelf_shadow(size, pygame)
        if shadow is not None:
            # The shadow shrinks a little while the badge is in the air.
            screen.blit(shadow, shadow.get_rect(center=(center[0], center[1] + size // 2)))
        badge = self._achievement_badges.render(entry, size, pygame)
        screen.blit(badge, badge.get_rect(center=(center[0], center[1] + dy)))
        if entry.is_new:
            self._paint_new_marker(screen, pygame, center, size, dy)

    def _shelf_shadow(self, size: int, pygame: Any) -> Any | None:
        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is None:
            return None
        try:
            return visual_cache.get(
                "ui.shadow.soft", variant="default", size=(int(size * 0.82), max(8, size // 7))
            )
        except Exception:  # noqa: BLE001 - decorative grounding only
            return None

    def _paint_new_marker(
        self, screen: Any, pygame: Any, center: tuple[int, int], size: int, dy: int
    ) -> None:
        anchor = (center[0] + size // 2 - 6, center[1] - size // 2 + 8 + dy)
        visual_cache = getattr(self, "_visual_cache", None)
        if visual_cache is not None:
            try:
                sparkle = visual_cache.get("fx.sparkle", variant="default", size=(40, 40))
                screen.blit(sparkle, sparkle.get_rect(center=anchor))
                return
            except Exception:  # noqa: BLE001 - fall back to the text marker
                pass
        theme = self.theme_controller.theme
        copy = achievement_ui_strings(self._achievement_locale)
        new = self._typography.font(FontRole.CONTROL, 12).render(copy.new_label, True, theme.accent_text)
        rect = new.get_rect(center=anchor).inflate(12, 5)
        pygame.draw.rect(screen, theme.accent, rect, border_radius=8)
        screen.blit(new, new.get_rect(center=rect.center))

    def _paint_shelf_detail(
        self, screen: Any, theme: Any, pygame: Any, layout: _ShelfLayout, entry: AchievementEntry
    ) -> None:
        detail = layout.detail
        key = (
            entry.definition.achievement_id,
            entry.unlocked,
            self._achievement_locale,
            detail.size,
        )
        rendered = self._achievement_detail_cache.get(key)
        if rendered is None:
            heading = self._fit_text(
                self._child_display_text(entry.definition.title.resolve(self._achievement_locale)),
                max_width=detail.width - 36,
                size=max(18, min(24, detail.height // 4)),
                color=theme.text,
            )
            text = (
                entry.definition.description
                if entry.unlocked
                else entry.definition.locked_hint
            ).resolve(self._achievement_locale)
            body_size = max(15, min(19, detail.height // 5))
            lines = self._wrap_text(
                self._child_display_text(text), max_width=detail.width - 36, size=body_size
            )
            body = tuple(
                self._typography.font(FontRole.BODY, body_size).render(line, True, theme.text)
                for line in lines[:2]
            )
            rendered = (heading, body)
            self._achievement_detail_cache[key] = rendered
        heading, body = rendered
        pygame.draw.rect(screen, theme.panel, detail, border_radius=20)
        pygame.draw.rect(screen, theme.accent, detail, width=3, border_radius=20)
        screen.blit(heading, (detail.left + 18, detail.top + 10))
        y = detail.top + 14 + heading.get_height()
        for line in body:
            screen.blit(line, (detail.left + 18, y))
            y += line.get_height() + 2

    def _draw_shelf_greeter(self, screen: Any, pygame: Any, layout: _ShelfLayout) -> None:
        visual_cache = getattr(self, "_visual_cache", None)
        profile = getattr(self, "_active_profile", None)
        if visual_cache is None or profile is None:
            return
        character = greeter_character_for(getattr(profile.profile, "avatar_id", None))
        rect = layout.greeter
        try:
            sprite = visual_cache.get(
                f"character.{character}",
                variant=self._achievement_greeter_pose,
                size=(rect.width, rect.height),
            )
        except Exception:  # noqa: BLE001 - the guide is decorative
            return
        screen.blit(sprite, rect.topleft)

    def _present_library_hop(self, screen: Any, pygame: Any, now: float) -> bool:
        """Incremental frame for a hopping shelf badge (slot rect only)."""

        hop = self._achievement_hop
        if hop is None:
            return False
        entries = self._achievement_visible_entries()
        backdrop = self._achievement_shelf_surface
        if backdrop is None or not 0 <= hop.index < len(entries):
            self._achievement_hop = None
            return False
        offset = 0 if hop.finished(now) else hop.offset(now)
        if hop.finished(now):
            self._achievement_hop = None
        if offset == self._achievement_hop_presented:
            return False
        layout = self._shelf_layout(screen.get_width(), screen.get_height(), pygame)
        per_page = self._ACHIEVEMENTS_PER_PAGE
        local = hop.index - (hop.index // per_page) * per_page
        if hop.index // per_page != self._achievement_selected // per_page:
            self._achievement_hop = None
            return False
        slot = layout.slots[local].clip(screen.get_rect())
        screen.blit(backdrop, slot.topleft, slot)
        self._paint_shelf_slot(screen, pygame, layout, local, entries[hop.index], hop.index, now)
        dirty = [slot, *self._repaint_pointer_over(screen, pygame, [slot])]
        pygame.display.update(dirty)
        self._achievement_hop_presented = offset
        self._achievement_frames_presented += 1
        return True

    def _page_arrow_rect(self, screen: Any, pygame: Any, *, left: bool) -> Any:
        size = max(42, min(54, screen.get_height() // 11))
        return pygame.Rect(
            8 if left else screen.get_width() - size - 8,
            screen.get_height() // 2 - size // 2,
            size,
            size,
        )

    def _draw_page_arrow(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
        *,
        left: bool,
        action: str | None,
    ) -> None:
        rect = self._page_arrow_rect(screen, pygame, left=left)
        pygame.draw.rect(screen, theme.panel, rect, border_radius=16)
        pygame.draw.rect(screen, theme.accent, rect, width=3, border_radius=16)
        inset = 13
        points = (
            (
                (rect.right - inset, rect.top + inset),
                (rect.left + inset, rect.centery),
                (rect.right - inset, rect.bottom - inset),
            )
            if left
            else (
                (rect.left + inset, rect.top + inset),
                (rect.right - inset, rect.centery),
                (rect.left + inset, rect.bottom - inset),
            )
        )
        pygame.draw.lines(screen, theme.text, False, points, width=5)
        if action is not None:
            self._targets.append(HitTarget(action, None, rect))

    # ------------------------------------------------------------- text
    def _fit_text(
        self,
        text: str,
        *,
        max_width: int,
        size: int,
        color: tuple[int, int, int],
    ) -> Any:
        current = max(11, size)
        while current > 11:
            rendered = self._typography.font(FontRole.CONTROL, current).render(
                text, True, color
            )
            if rendered.get_width() <= max_width:
                return rendered
            current -= 1
        return self._typography.font(FontRole.CONTROL, 11).render(
            text, True, color
        )

    def _wrap_text(
        self, text: str, *, max_width: int, size: int
    ) -> tuple[str, ...]:
        font = self._typography.font(FontRole.BODY, size)
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if current and font.size(candidate)[0] > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return tuple(lines)

    @staticmethod
    def _mix_color(
        first: tuple[int, int, int],
        second: tuple[int, int, int],
        weight_first: float,
    ) -> tuple[int, int, int]:
        return tuple(
            int(a * weight_first + b * (1.0 - weight_first))
            for a, b in zip(first[:3], second[:3])
        )
