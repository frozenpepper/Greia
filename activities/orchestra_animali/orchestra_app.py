"""Orchestra Animali — the Animal Band: lifecycle, input and the echo flow.

One core experience on one stage. Six canonical cast musicians (Leo drum,
Momo maracas, Lilli bells, Tito trumpet, Flash tambourine, Dani keyboard)
stand behind a rainbow xylophone; the child plays any of them at any time
(free play is the heart). Every few seconds of free play one musician steps
into the spotlight and invites a "copy my rhythm" echo inside the same
screen: it plays a short call (ear bubble), then points at the child (go
bubble) and the child's taps appear in the bubble at their real timing.
Correct = the musician cheers (``pose_cheer``) with a star burst and a
progress dot; try again = ``pose_think``, then the musician demonstrates the
call again with beat rings (unlimited, kind retries). Idle hints are
graduated (~6 s: point + beat ring; ~12 s: the call is played again). Loud/
soft (mouse | lion) and slow/fast (snail | horse) are properties of the whole
band. Five echoes make a concert, which ends on the shared completion scene
hosted by Momo; replay starts the next concert at the adapted stage.

A saved recording or song from My Creations can play as a backing track
(``PlayAlong``); invitations wait while it plays so the child's concert is
never interrupted.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from enum import StrEnum
import random
import time

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.frame_governor import FrameGovernor, FrameKind
from greia_platform.activity_controls import (
    ControlKit,
    ControlLayout,
    ControlTheme,
    KitPointer,
    PointerPhase,
    PygameControlInput,
)
from greia_platform.activity_feedback import CastFeedback, IdleHintScheduler
from greia_platform.localization import LocalizationError, LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_completion import (
    CompletionContent,
    CompletionOverlay,
    CompletionPalette,
    CompletionScene,
    PygameCompletionScreen,
)
from greia_platform.typography import GreiaTypography
from greia_platform.ui_core import SurfaceNavigator, UiEventResult

if __package__:
    from .orchestra_art import OrchestraArt
    from .orchestra_audio import BandAudio
    from .orchestra_content import (
        BAND,
        BAND_LEADER,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SESSION_ECHOES,
        Dynamics,
        Tempo,
    )
    from .orchestra_controls import OrchestraControls
    from .orchestra_layout import BAR_RECTS, CAST_HEIGHT, musician_anchor, musician_head
    from .orchestra_model import (
        ConcertProgress,
        ConcertSession,
        EchoPattern,
        EchoVerdict,
        PatternFactory,
        XYLOPHONE_VOICE,
    )
    from .orchestra_playalong import PlayAlong
    from .orchestra_renderer import BandMotion, Bubble, OrchestraRenderer, sway
    from .orchestra_services import EventPort, ProgressPort
else:  # pragma: no cover - runtime/script fallback
    from orchestra_art import OrchestraArt
    from orchestra_audio import BandAudio
    from orchestra_content import (
        BAND,
        BAND_LEADER,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SESSION_ECHOES,
        Dynamics,
        Tempo,
    )
    from orchestra_controls import OrchestraControls
    from orchestra_layout import BAR_RECTS, CAST_HEIGHT, musician_anchor, musician_head
    from orchestra_model import (
        ConcertProgress,
        ConcertSession,
        EchoPattern,
        EchoVerdict,
        PatternFactory,
        XYLOPHONE_VOICE,
    )
    from orchestra_playalong import PlayAlong
    from orchestra_renderer import BandMotion, Bubble, OrchestraRenderer, sway
    from orchestra_services import EventPort, ProgressPort

FIRST_INVITE_SECONDS = 7.0
FREE_PLAY_SECONDS = 9.0
QUIET_BEFORE_INVITE = 1.2
INVITE_LEAD = 1.0
CALL_TAIL = 0.7
ECHO_SETTLE = 0.35
ECHO_TIMEOUT = 2.4
THINK_SECONDS = 1.7
CHEER_HOLD = 2.6
INTRO_STEP = 0.22
MAX_SCHEDULED = 64
STAGE_NIGHT = (52, 36, 70)

_MUSICIAN_KEYS = {
    pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3, pygame.K_5: 4, pygame.K_6: 5,
    pygame.K_KP1: 0, pygame.K_KP2: 1, pygame.K_KP3: 2, pygame.K_KP4: 3, pygame.K_KP5: 4, pygame.K_KP6: 5,
}
_BAR_KEYS = {
    pygame.K_a: 0, pygame.K_s: 1, pygame.K_d: 2, pygame.K_f: 3,
    pygame.K_g: 4, pygame.K_h: 5, pygame.K_j: 6, pygame.K_k: 7,
}
_COPY_FALLBACK = {
    "victory.title": "What a concert!",
    "victory.subtitle": "You played with the whole band!",
    "button.play_again": "Play again",
}


class Phase(StrEnum):
    INTRO = "intro"        # the band says hello, one instrument after another
    FREE = "free"          # free play (the heart)
    LISTEN = "listen"      # a musician plays the call (stage input paused)
    ECHO = "echo"          # the child's turn
    CHEER = "cheer"        # celebrating a matched echo
    COMPLETE = "complete"  # shared completion scene


class Timeline:
    """Tiny bounded scheduler for scripted moments."""

    def __init__(self, clock: Callable[[], float]) -> None:
        self._clock = clock
        self._entries: deque[tuple[float, Callable[[], object]]] = deque(maxlen=MAX_SCHEDULED)

    def after(self, delay: float, action: Callable[[], object]) -> None:
        self._entries.append((self._clock() + delay, action))

    def run_due(self) -> bool:
        now = self._clock()
        due = [entry for entry in self._entries if entry[0] <= now]
        if not due:
            return False
        for entry in due:
            self._entries.remove(entry)
        for _, action in sorted(due, key=lambda entry: entry[0]):
            action()
        return True

    @property
    def busy(self) -> bool:
        return bool(self._entries)

    def clear(self) -> None:
        self._entries.clear()


class OrchestraApp:
    """Coordinate the band, the echo session, shared-kit input and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources | None,
        audio: BandAudio,
        progress: ProgressPort,
        events: EventPort,
        playalong: PlayAlong,
        rng: random.Random,
        session_id: str,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: OrchestraArt | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.typography = typography
        self.resources = resources
        self.audio = audio
        self.progress = progress
        self.events = events
        self.playalong = playalong
        self.playalong.on_concert = self._on_concert
        self.rng = rng
        self.session_id = session_id
        self.clock = clock

        # Shared control kit (ADR 0037): the music Collection hue is turquoise.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("turquoise"))
        self.art = art if art is not None else OrchestraArt(self.kit.painter)
        self.feedback = tuple(
            CastFeedback(musician.character, height=CAST_HEIGHT, art=self.art.art, clock=clock)
            for musician in BAND
        )
        self.renderer = OrchestraRenderer(self.art, self.feedback, clock=clock)
        self.motion = BandMotion()
        self.timeline = Timeline(clock)
        self.dynamics = Dynamics.LOUD
        self.tempo = Tempo.SLOW
        self.audio.set_dynamics(self.dynamics)
        self.controls = OrchestraControls(
            self.kit,
            self.art,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            on_musician=lambda index: self.play_musician(index),
            on_bar=lambda index: self.play_bar(index),
            on_import=self._on_import,
            on_play=self._on_play,
            on_dynamics=self.set_dynamics,
            on_tempo=self.set_tempo,
            dynamics=self.dynamics,
            tempo=self.tempo,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=STAGE_NIGHT),
            scene=CompletionScene(self.kit, character=BAND_LEADER, star_total=SESSION_ECHOES),
        )
        self.saved = progress.load()
        self.factory = PatternFactory(rng)
        self.session = ConcertSession(self.factory, level=self.saved.level, rng=rng)
        self.phase = Phase.INTRO
        self.attempt: list[tuple[int, float]] = []
        self._judging = False
        self._played: set[str] = set()
        self._concerts_heard = 0
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._activated = False
        self._swallow_up = False
        self._free_since = clock()
        self._first_window = True
        self._last_input = clock()
        self._echo_since = clock()
        self._hints = IdleHintScheduler(now=self._last_input)
        self._last_sway = 0
        self._hint_replay = False  # the call being replayed is an idle hint
        self.playalong.load_saved()
        self._start_concert()

    # -- main loop ------------------------------------------------------------------

    def run(self) -> int:
        frames = FrameGovernor()
        try:
            while self._running and not activity_stop_requested():
                for event in frames.events():
                    self.handle_event(event)
                    if not self._running:
                        break
                if not self._running:
                    break
                repeat = self._input.poll()
                if repeat is not None:
                    self._dispatch(repeat)
                animating = self.step()
                # The band's sway is decoration (quantised, so it only asks
                # for a frame when the bob changes); on the reference floor it
                # freezes while the child is idle unless a song is playing.
                swaying = self._sway_due() and (self.playalong.playing or not frames.ambient_frozen)
                frame = frames.frame(dirty=self._dirty or swaying, animating=animating)
                if frame is FrameKind.FULL:
                    self._last_sway = sway(self.clock(), self.tempo)
                    self.render()
                    self.canvas.present()
                    pygame.display.flip()
                    self._dirty = False
                    if not self._ready_published:
                        mark_activity_ready()
                        self._ready_published = True
                elif frame is FrameKind.POINTER:
                    self.canvas.present_pointer()
                frames.wait(polling=self._input.repeating)
        finally:
            self.playalong.stop()
            self._save()
            self.typography.clear()
        return 0

    def step(self) -> bool:
        """Advance timers and flows; return True while something is moving."""

        now = self.clock()
        if self.timeline.run_due():
            self._dirty = True
        if self.playalong.update(now):
            self._sync()
            self._dirty = True
        for feedback in self.feedback:
            if feedback.update():
                self._dirty = True
        self.motion.prune(now)
        if self.phase is Phase.FREE:
            self._maybe_invite(now)
        elif self.phase is Phase.ECHO:
            self._maybe_close_echo(now)
            self._maybe_hint(now)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        return self.motion.active(now) or any(feedback.animating for feedback in self.feedback)

    def _sway_due(self) -> bool:
        """True when the quantised band sway moved since the last frame."""

        return sway(self.clock(), self.tempo) != self._last_sway

    def render(self) -> None:
        surface = self.canvas.surface
        if self.phase is Phase.COMPLETE:
            self._surfaces.draw(surface)
            return
        self.renderer.draw(surface, self.motion, tempo=self.tempo, dynamics=self.dynamics)
        self._surfaces.draw(surface)

    # -- input ------------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._running = False
                return
            if self.phase is not Phase.COMPLETE:
                if event.key in _MUSICIAN_KEYS:
                    self._note_input()
                    self.play_musician(_MUSICIAN_KEYS[event.key])
                    return
                if event.key in _BAR_KEYS:
                    self._note_input()
                    self.play_bar(_BAR_KEYS[event.key])
                    return
        if event.type == pygame.VIDEORESIZE:
            self._resize()
            return
        translated = self._input.translate(event)
        if translated is not None:
            self._dispatch(translated)

    def _dispatch(self, kit_input) -> bool:
        if isinstance(kit_input, KitPointer):
            if kit_input.phase is PointerPhase.DOWN and self.phase is not Phase.COMPLETE:
                target = self.controls.pointer_target(kit_input.position)
                if target is not None:
                    # Music sounds on touch-down; the release is swallowed.
                    self._note_input()
                    self._swallow_up = True
                    self.controls.layer.focus_visible = False
                    kind, index = target
                    if kind == "bar":
                        self.play_bar(index)
                    else:
                        self.play_musician(index)
                    return True
            if kit_input.phase in {PointerPhase.UP, PointerPhase.CANCEL} and self._swallow_up:
                self._swallow_up = False
                return True
            if kit_input.phase is not PointerPhase.MOVE:
                self._note_input()
        else:
            self._note_input()
        result = self._surfaces.dispatch(kit_input)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        return result is not UiEventResult.IGNORED

    def tap(self, raw_pos: tuple[int, int]) -> bool:
        """Deliver one complete tap at a physical position (tests/tools)."""

        if not _safe_point(self.screen, raw_pos):
            return False
        logical = self.canvas.pointer(raw_pos)
        if logical is None:
            return False
        point = (int(logical[0]), int(logical[1]))
        self._activated = False
        self._dispatch(KitPointer(PointerPhase.DOWN, point))
        self._dispatch(KitPointer(PointerPhase.UP, point))
        return self._activated

    def press(self, key: int) -> bool:
        """Deliver one key press (number/letter keys or shared navigation)."""

        self._activated = False
        self.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
        return self._activated

    def _note_input(self) -> None:
        self._last_input = self.clock()
        self._hints.reset(self._last_input)

    def _resize(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.canvas = PygameReferenceCanvas(self.screen)
        self._input = PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.controls.relayout(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
        self._dirty = True

    # -- playing the band -------------------------------------------------------------

    @property
    def stage_live(self) -> bool:
        return self.phase in {Phase.FREE, Phase.ECHO}

    def play_musician(self, index: int) -> bool:
        """The child plays one band member (pointer, number key or focus)."""

        if not self.stage_live or not 0 <= index < len(BAND):
            return False
        self._activated = True
        now = self.clock()
        musician = BAND[index]
        self.audio.play_instrument(musician.instrument)
        self._strike(index, now)
        if musician.instrument not in self._played:
            self._played.add(musician.instrument)
            self.events.instrument_played(self.session_id, musician.instrument)
        self.playalong.note_played()
        if self.phase is Phase.ECHO:
            self._record(index, now)
        self._dirty = True
        return True

    def play_bar(self, index: int) -> bool:
        """The child plays one rainbow-xylophone bar."""

        if not self.stage_live or not 0 <= index < len(BAR_RECTS):
            return False
        self._activated = True
        now = self.clock()
        self.audio.play_note(index)
        self.motion.light_bar(index, now)
        rect = BAR_RECTS[index]
        self.motion.burst(self._note_fx(), (rect.centerx, rect.top - 18), now, duration=0.55, rise=50.0)
        self.playalong.note_played()
        if self.phase is Phase.ECHO:
            self._record(XYLOPHONE_VOICE, now)
        self._dirty = True
        return True

    def _strike(self, index: int, now: float, *, fx: bool = True) -> None:
        self.motion.strike(index, now)
        if fx:
            x, y = musician_head(index)
            self.motion.burst(self._note_fx(), (x + 26, y - 8), now, duration=0.6, rise=56.0)

    def _note_fx(self) -> str:
        return "note_burst" if self.dynamics is Dynamics.LOUD else "note_burst_soft"

    def set_dynamics(self, dynamics: Dynamics) -> None:
        """Loud (lion) / soft (mouse): the band answers with one tutti hit."""

        self._activated = True
        self.dynamics = dynamics
        self.audio.set_dynamics(dynamics)
        if self.phase is Phase.FREE:
            now = self.clock()
            for index in (0, 5):
                self.audio.play_instrument(BAND[index].instrument)
            for index in range(len(BAND)):
                self._strike(index, now, fx=index in (0, 5))
        self._dirty = True

    def set_tempo(self, tempo: Tempo) -> None:
        """Slow (snail) / fast (horse): Leo's drum shows the new speed."""

        self._activated = True
        self.tempo = tempo
        if self.phase is Phase.FREE:
            for beat in range(3):
                self.timeline.after(beat * tempo.beat_seconds, lambda: self._band_beat(0))
        self._dirty = True

    def _band_beat(self, index: int) -> None:
        self.audio.play_instrument(BAND[index].instrument)
        self._strike(index, self.clock())
        self._dirty = True

    # -- concert flow ----------------------------------------------------------------------

    def _start_concert(self) -> None:
        self.timeline.clear()
        self.motion.clear()
        for feedback in self.feedback:
            feedback.reset()
        self.phase = Phase.INTRO
        self.attempt = []
        self._judging = False
        # Hello from the band: each friend plays once, left to right.
        for index in range(len(BAND)):
            self.timeline.after(0.3 + INTRO_STEP * index, lambda i=index: self._band_beat(i))
        self.timeline.after(0.3 + INTRO_STEP * len(BAND) + 0.3, self._enter_free)
        self._sync()
        self._dirty = True

    def _enter_free(self) -> None:
        self.phase = Phase.FREE
        self._free_since = self.clock()
        self.motion.bubble = None
        self.motion.spotlight = None
        self._sync()
        self._dirty = True

    def _maybe_invite(self, now: float) -> None:
        if self.session.finished or self.playalong.playing or self.playalong.import_state == "pending":
            return
        window = FIRST_INVITE_SECONDS if self._first_window else FREE_PLAY_SECONDS
        if now - self._free_since < window or now - self._last_input < QUIET_BEFORE_INVITE:
            return
        self._first_window = False
        self.invite()

    def invite(self) -> None:
        """A musician steps into the spotlight with a "copy my rhythm" call."""

        invitation = self.session.invite()
        self._hint_replay = False
        now = self.clock()
        lead = invitation.lead
        self.motion.spotlight = lead
        self.motion.borrow(lead, "pose_wave", now + INVITE_LEAD)
        self.controls.focus_musician(lead)
        self._play_call(invitation.pattern, INVITE_LEAD)

    def _play_call(self, pattern: EchoPattern, lead_in: float, *, rings: bool = False) -> None:
        """Perform the call: strike + sound + bubble token per beat, then open the echo."""

        assert self.session.current is not None
        self.phase = Phase.LISTEN
        self.attempt = []
        self._judging = False
        self.motion.bubble = Bubble(self.session.current.lead, "listen", pattern.span)
        start = pattern.beats[0].at
        beat_seconds = self.tempo.beat_seconds
        for beat in pattern.beats:
            delay = lead_in + (beat.at - start) * beat_seconds
            self.timeline.after(delay, lambda b=beat: self._call_beat(b.voice, b.at - start, rings))
        self.timeline.after(lead_in + pattern.span * beat_seconds + CALL_TAIL, self._open_echo)
        self._sync()
        self._dirty = True

    def _call_beat(self, voice: int, position: float, ring: bool) -> None:
        now = self.clock()
        self.audio.play_instrument(BAND[voice].instrument)
        self._strike(voice, now)
        if ring:
            x, y = musician_anchor(voice)
            self.motion.ring((x, y - CAST_HEIGHT // 2), now)
        if self.motion.bubble is not None:
            self.motion.bubble.tokens.append((voice, position))
        self._dirty = True

    def _open_echo(self) -> None:
        invitation = self.session.current
        if invitation is None:
            return
        now = self.clock()
        self.phase = Phase.ECHO
        self.attempt = []
        self._judging = False
        self._echo_since = now
        self._last_input = now
        if not self._hint_replay:
            # A hint's own replay must not restart the back-off, or the band
            # would replay the call forever for a child who walked away.
            self._hints.reset(now)
        self._hint_replay = False
        self.motion.bubble = Bubble(invitation.lead, "echo", invitation.pattern.span)
        self.motion.borrow(invitation.lead, "pose_point", now + 1.4)
        self.audio.say(BAND[invitation.lead].character, "ready.go")
        self._sync()
        self._dirty = True

    def _record(self, voice: int, now: float) -> None:
        invitation = self.session.current
        if invitation is None or self._judging:
            return
        self.attempt.append((voice, now))
        if self.motion.bubble is not None:
            first = self.attempt[0][1]
            self.motion.bubble.tokens.append((voice, (now - first) / self.tempo.beat_seconds))
        if len(self.attempt) >= invitation.pattern.length:
            self._judging = True
            self.timeline.after(ECHO_SETTLE, self._judge)

    def _maybe_close_echo(self, now: float) -> None:
        if self.attempt and not self._judging and now - self.attempt[-1][1] >= ECHO_TIMEOUT:
            self._judging = True
            self._judge()

    def _judge(self) -> None:
        if self.phase is not Phase.ECHO or self.session.current is None:
            return
        verdict = self.session.answer(self.attempt)
        if verdict is EchoVerdict.MATCH:
            self._celebrate()
        else:
            self._try_again()

    def _celebrate(self) -> None:
        invitation = self.session.current
        assert invitation is not None
        now = self.clock()
        self.phase = Phase.CHEER
        lead = invitation.lead
        self.feedback[lead].correct()
        self.audio.cue("fanfare")
        self.audio.say(BAND[lead].character, "praise.general")
        for index in range(len(BAND)):
            if index != lead:
                self.motion.strike(index, now + 0.05 * index)
        x, _ = musician_anchor(lead)
        self.motion.burst("star_burst", (x, 168), now, duration=0.9)
        self.motion.burst("sparkle", (x - 70, 250), now + 0.15, duration=0.7)
        self.motion.burst("sparkle", (x + 70, 250), now + 0.3, duration=0.7)
        self.saved = ConcertProgress(self.session.level, self.saved.stars + 1, self.saved.concerts)
        self.events.echo_matched(self.session_id, invitation.index, invitation.pattern.level)
        self.timeline.after(CHEER_HOLD, self._after_cheer)
        self._sync()
        self._dirty = True

    def _after_cheer(self) -> None:
        self.session.close()
        if self.session.finished:
            self._complete()
            return
        self._enter_free()

    def _try_again(self) -> None:
        invitation = self.session.current
        assert invitation is not None
        self._hint_replay = False
        self.phase = Phase.LISTEN
        self.feedback[invitation.lead].try_again()
        self.audio.cue("boop")
        self.audio.say(BAND[invitation.lead].character, "encourage.retry")
        self.motion.bubble = Bubble(invitation.lead, "listen", invitation.pattern.span)
        # Demonstrate: the call again, with a beat ring on whoever plays.
        self.timeline.after(THINK_SECONDS, lambda: self._play_call(invitation.pattern, 0.2, rings=True))
        self._sync()
        self._dirty = True

    def _maybe_hint(self, now: float) -> None:
        invitation = self.session.current
        if invitation is None or self.attempt or self.timeline.busy:
            return
        step = self._hints.poll(now, self._last_input)
        if not step:
            return
        self.session.note_hint()
        lead = invitation.lead
        if step == 1:
            # Point and pulse the first player: "it's your turn, start here".
            self.motion.borrow(lead, "pose_point", now + self._hints.animation_seconds(1.8))
            first = invitation.pattern.beats[0].voice
            x, y = musician_anchor(first)
            self.motion.ring((x, y - CAST_HEIGHT // 2), now)
            self.motion.ring((x, y - CAST_HEIGHT // 2), now + 0.35)
        else:
            self._hint_replay = True
            self._play_call(invitation.pattern, 0.3, rings=True)
        self._dirty = True

    def _complete(self) -> None:
        self.timeline.clear()
        self.phase = Phase.COMPLETE
        self.motion.bubble = None
        self.motion.spotlight = None
        self.saved = ConcertProgress(self.session.level, self.saved.stars, self.saved.concerts + 1)
        self.progress.save(self.saved)
        self.events.concert_completed(
            self.session_id, {"echoes": self.session.completed, "level": self.session.level}
        )
        self.audio.say(BAND_LEADER, "celebrate.success")
        self.completion.prepare(
            CompletionContent(
                title=self._text("victory.title"),
                primary_label=self._text("button.play_again"),
                body_lines=(self._text("victory.subtitle"),),
                achievement_count=SESSION_ECHOES,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self._sync()
        self._dirty = True

    def _restart(self) -> None:
        self._activated = True
        self._surfaces.pop_overlay()
        self.completion.clear()
        self.session = ConcertSession(self.factory, level=self.saved.level, rng=self.rng)
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self._played.clear()
        self._first_window = True
        self._start_concert()

    def _save(self) -> None:
        self.progress.save(ConcertProgress(self.session.level, self.saved.stars, self.saved.concerts))

    # -- play along with a saved recording ------------------------------------------------

    def _on_import(self) -> None:
        self._activated = True
        self.playalong.request(self.clock())
        self._sync()
        self._dirty = True

    def _on_play(self) -> None:
        self._activated = True
        self.playalong.toggle(self.clock())
        self._sync()
        self._dirty = True

    def _on_concert(self, live_inputs: int) -> None:
        self._concerts_heard += 1
        self.events.concert_performed(f"{self.session_id}-song{self._concerts_heard}", live_inputs)

    # -- helpers ------------------------------------------------------------------------------

    def _sync(self) -> None:
        free = self.phase is Phase.FREE
        self.controls.sync(
            stage_live=self.stage_live,
            free_play=free,
            can_import=self.playalong.can_import,
            import_state=self.playalong.import_state,
            has_track=self.playalong.has_track,
            track_playing=self.playalong.playing,
            completed=self.session.completed,
        )
        for slot in (*self.controls.volume.controls, *self.controls.tempo.controls):
            slot.enabled = free

    def _text(self, key: str) -> str:
        if self.resources is not None:
            try:
                value = self.resources.text(key).strip()
                if value:
                    return value
            except LocalizationError:
                pass
        return _COPY_FALLBACK[key]


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["OrchestraApp", "Phase", "Timeline"]
