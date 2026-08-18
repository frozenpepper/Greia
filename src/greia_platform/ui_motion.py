from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InteractionVisualState:
    """Renderer-neutral visual state for one child-facing control.

    This describes presentation only. It never grants focus, authority or input
    ownership; the owning Screen/Control remains authoritative for interaction.
    """

    hovered: bool = False
    selected: bool = False
    pressed: bool = False
    launching: bool = False

    @property
    def emphasized(self) -> bool:
        return self.hovered or self.selected or self.pressed or self.launching


@dataclass(frozen=True, slots=True)
class MotionSample:
    """One cheap transform sample consumed by a renderer."""

    scale: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    shadow_lift: float = 0.0


@dataclass(frozen=True, slots=True)
class LaunchMotion:
    """Short bounded squiggle/bounce used while an Activity is being launched.

    The animation is deliberately mathematical and allocation-free: old
    machines can sample it at 30 Hz without a retained animation framework.
    It settles exactly to the neutral transform after ``duration_seconds``.
    """

    duration_seconds: float = 0.42
    wiggle_pixels: float = 7.0
    bounce_pixels: float = 10.0
    peak_scale: float = 0.075

    def __post_init__(self) -> None:
        if self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        if self.wiggle_pixels < 0 or self.bounce_pixels < 0 or self.peak_scale < 0:
            raise ValueError("motion amplitudes must be non-negative")

    def sample(self, elapsed_seconds: float) -> MotionSample:
        elapsed = max(0.0, float(elapsed_seconds))
        if elapsed >= self.duration_seconds:
            return MotionSample()
        progress = elapsed / self.duration_seconds
        # Ease the amplitude down to zero so the handoff never jumps.
        envelope = (1.0 - progress) ** 1.5
        wiggle = math.sin(progress * math.tau * 3.0) * self.wiggle_pixels * envelope
        bounce = -abs(math.sin(progress * math.pi * 2.0)) * self.bounce_pixels * envelope
        scale = 1.0 + abs(math.sin(progress * math.pi)) * self.peak_scale * envelope
        return MotionSample(
            scale=scale,
            offset_x=wiggle,
            offset_y=bounce,
            shadow_lift=max(0.0, (scale - 1.0) / max(self.peak_scale, 0.0001)),
        )


@dataclass(frozen=True, slots=True)
class HoverMotion:
    """Subtle static emphasis for pointer/keyboard focus."""

    scale: float = 1.025
    lift_pixels: float = 3.0

    def sample(self, state: InteractionVisualState) -> MotionSample:
        if not state.emphasized:
            return MotionSample()
        if state.launching:
            return MotionSample()
        if state.pressed:
            return MotionSample(scale=max(1.0, self.scale - 0.02), offset_y=1.0)
        return MotionSample(scale=self.scale, offset_y=-self.lift_pixels, shadow_lift=1.0)
