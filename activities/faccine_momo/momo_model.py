"""Domain model and state simulation for Le Faccine di Momo."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
import random
from typing import Final

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600


class Emotion(StrEnum):
    HAPPY = "happy"
    SAD = "sad"
    SURPRISED = "surprised"
    SILLY = "silly"
    ANGRY = "angry"
    SLEEPY = "sleepy"


class GameMode(StrEnum):
    FREE_MIRROR = "free_mirror"
    GUESS_EMOTION = "guess_emotion"


@dataclass
class MomoParticle:
    x: float
    y: float
    vx: float
    vy: float
    kind: str  # "heart", "star", "confetti", "puff", "zzz", "sparkle"
    color: tuple[int, int, int]
    size: float
    life: float = 1.0


class MomoModel:
    """Manage Momo's emotional states, interactive face elements, and quiz rounds."""

    def __init__(self) -> None:
        self.emotion: Emotion = Emotion.HAPPY
        self.is_comforted: bool = False
        self.mode: GameMode = GameMode.FREE_MIRROR

        # Tracking for achievements/milestones
        self.discovered_emotions: set[Emotion] = {Emotion.HAPPY}
        self.quiz_streak: int = 0
        self.completed_all: bool = False

        # Quiz round state
        self.quiz_target: Emotion = Emotion.HAPPY
        self.quiz_choices: list[Emotion] = [Emotion.HAPPY, Emotion.SAD]

        # Particles & animations
        self.particles: list[MomoParticle] = []
        self.anim_timer: float = 0.0
        self.hop_offset: float = 0.0
        self.shake_offset: float = 0.0

    def set_emotion(self, emotion: Emotion) -> None:
        self.emotion = emotion
        self.is_comforted = False
        self.discovered_emotions.add(emotion)
        if len(self.discovered_emotions) == len(Emotion):
            self.completed_all = True

        # Spawn celebration particles when happy/silly
        if emotion == Emotion.HAPPY:
            self.hop_offset = 20.0
            self._spawn_confetti(30)
        elif emotion == Emotion.SILLY:
            self.shake_offset = 12.0
            self._spawn_stars(15)
        elif emotion == Emotion.ANGRY:
            self._spawn_puffs()

    def comfort_momo(self) -> bool:
        """Called when child taps/strokes Momo's cheek when sad."""
        if self.emotion == Emotion.SAD and not self.is_comforted:
            self.is_comforted = True
            # Spawn love hearts around Momo
            for _ in range(12):
                self.particles.append(
                    MomoParticle(
                        x=512 + random.uniform(-90, 90),
                        y=320 + random.uniform(-60, 60),
                        vx=random.uniform(-40, 40),
                        vy=random.uniform(-80, -25),
                        kind="heart",
                        color=(255, 64, 129),
                        size=random.uniform(14, 22),
                        life=1.4,
                    )
                )
            return True
        return False

    def toggle_mode(self) -> GameMode:
        if self.mode == GameMode.FREE_MIRROR:
            self.start_quiz_round()
        else:
            self.mode = GameMode.FREE_MIRROR
        return self.mode

    def start_quiz_round(self) -> None:
        self.mode = GameMode.GUESS_EMOTION
        # Pick an emotion distinct from current if possible
        all_emo = list(Emotion)
        self.quiz_target = random.choice(all_emo)
        self.emotion = self.quiz_target
        self.is_comforted = False

        # Pick one distractor
        distractors = [e for e in all_emo if e != self.quiz_target]
        distractor = random.choice(distractors)

        choices = [self.quiz_target, distractor]
        random.shuffle(choices)
        self.quiz_choices = choices

    def answer_quiz(self, choice: Emotion) -> bool:
        if choice == self.quiz_target:
            self.quiz_streak += 1
            self.hop_offset = 25.0
            self._spawn_confetti(40)
            return True
        # Friendly shake on retry
        self.shake_offset = 14.0
        return False

    def _spawn_confetti(self, count: int) -> None:
        colors = [
            (255, 235, 59),
            (255, 64, 129),
            (0, 229, 255),
            (118, 255, 3),
            (255, 145, 0),
        ]
        for _ in range(count):
            self.particles.append(
                MomoParticle(
                    x=512 + random.uniform(-140, 140),
                    y=260 + random.uniform(-100, 100),
                    vx=random.uniform(-90, 90),
                    vy=random.uniform(-120, 20),
                    kind="confetti",
                    color=random.choice(colors),
                    size=random.uniform(6, 12),
                    life=1.5,
                )
            )

    def _spawn_stars(self, count: int) -> None:
        for _ in range(count):
            self.particles.append(
                MomoParticle(
                    x=512 + random.uniform(-120, 120),
                    y=300 + random.uniform(-80, 80),
                    vx=random.uniform(-60, 60),
                    vy=random.uniform(-70, 30),
                    kind="star",
                    color=(255, 215, 0),
                    size=random.uniform(8, 14),
                    life=1.2,
                )
            )

    def _spawn_puffs(self) -> None:
        for ox in (-70, 70):
            for _ in range(3):
                self.particles.append(
                    MomoParticle(
                        x=512 + ox,
                        y=240,
                        vx=random.uniform(-15, 15) + (10 if ox > 0 else -10),
                        vy=random.uniform(-60, -30),
                        kind="puff",
                        color=(220, 220, 225),
                        size=random.uniform(10, 20),
                        life=1.0,
                    )
                )

    def update(self, dt: float) -> None:
        self.anim_timer += dt

        # Decay hop and shake
        if self.hop_offset > 0.0:
            self.hop_offset = max(0.0, self.hop_offset - dt * 80.0)
        if self.shake_offset > 0.0:
            self.shake_offset = max(0.0, self.shake_offset - dt * 50.0)

        # Ambient sleepy Zzz
        if self.emotion == Emotion.SLEEPY and random.random() < 0.04:
            self.particles.append(
                MomoParticle(
                    x=512 + 60,
                    y=260,
                    vx=random.uniform(10, 25),
                    vy=random.uniform(-40, -20),
                    kind="zzz",
                    color=(180, 205, 255),
                    size=random.uniform(12, 18),
                    life=2.0,
                )
            )

        # Update particles
        surviving = []
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.life -= dt
            if p.life > 0:
                surviving.append(p)
        self.particles = surviving
