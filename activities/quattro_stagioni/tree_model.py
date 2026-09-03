"""Data models and state simulation for Il Grande Albero delle Stagioni."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
import random
from typing import Final

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600


class WeatherMode(StrEnum):
    SUN = "sun"
    RAIN = "rain"
    WIND = "wind"
    SNOW = "snow"


class Season(StrEnum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


@dataclass
class Cloud:
    x: float
    y: float
    scale: float
    speed: float


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    kind: str  # "rain", "snow", "leaf", "sparkle", "butterfly"
    life: float = 1.0
    color: tuple[int, int, int] = (255, 255, 255)
    size: float = 4.0
    angle: float = 0.0


@dataclass
class Apple:
    tree_rel_x: float
    tree_rel_y: float
    in_basket: bool = False
    is_falling: bool = False
    fall_y: float = 0.0
    fall_speed: float = 0.0


class TreeModel:
    """Simulate seasons, day/night transitions, weather, and interactive entities."""

    def __init__(self) -> None:
        self.day_ratio: float = 1.0  # 1.0 = Day, 0.0 = Night
        self.target_day_ratio: float = 1.0
        self.weather: WeatherMode = WeatherMode.SUN
        self.season: Season = Season.SPRING

        # Exploration tracking
        self.discovered_seasons: set[Season] = {Season.SPRING}
        self.discovered_weather: set[WeatherMode] = {WeatherMode.SUN}
        self.experienced_night: bool = False
        self.completed_cycle: bool = False

        # Entity lists
        self.clouds: list[Cloud] = [
            Cloud(x=120.0, y=80.0, scale=1.0, speed=12.0),
            Cloud(x=450.0, y=110.0, scale=0.8, speed=16.0),
            Cloud(x=820.0, y=70.0, scale=1.2, speed=10.0),
        ]
        self.particles: list[Particle] = []
        self.apples: list[Apple] = self._spawn_apples()
        self.snowman_stage: int = 0  # 0 to 3 parts

        # Tito animation state
        self.tito_anim_timer: float = 0.0
        self.tito_hop_offset: float = 0.0
        self.tito_puddle_splash: float = 0.0

    def _spawn_apples(self) -> list[Apple]:
        return [
            Apple(tree_rel_x=-70, tree_rel_y=-60),
            Apple(tree_rel_x=-20, tree_rel_y=-100),
            Apple(tree_rel_x=45, tree_rel_y=-75),
            Apple(tree_rel_x=90, tree_rel_y=-40),
            Apple(tree_rel_x=-100, tree_rel_y=-20),
        ]

    def set_day_ratio(self, val: float) -> None:
        self.target_day_ratio = max(0.0, min(1.0, val))
        if self.target_day_ratio < 0.2:
            self.experienced_night = True

    def toggle_day_night(self) -> bool:
        """Toggle day/night. Returns True if now daytime, False if nighttime."""
        if self.target_day_ratio > 0.5:
            self.set_day_ratio(0.0)
            return False
        self.set_day_ratio(1.0)
        return True

    def set_weather(self, mode: WeatherMode) -> None:
        if self.weather == mode:
            return
        self.weather = mode
        self.discovered_weather.add(mode)
        # Clear particles when weather shifts dramatically
        if mode in (WeatherMode.RAIN, WeatherMode.SNOW):
            self.particles.clear()

    def set_season(self, season: Season) -> None:
        if self.season == season:
            return
        self.season = season
        self.discovered_seasons.add(season)
        if len(self.discovered_seasons) == 4 and not self.completed_cycle:
            self.completed_cycle = True
        # Reset season-specific props
        if season == Season.SUMMER:
            self.apples = self._spawn_apples()
        elif season == Season.WINTER:
            self.snowman_stage = 1

    def tap_snowman(self) -> bool:
        if self.season == Season.WINTER:
            self.snowman_stage = min(3, self.snowman_stage + 1)
            # Add sparkles around snowman
            for _ in range(8):
                self.particles.append(
                    Particle(
                        x=750 + random.uniform(-40, 40),
                        y=450 + random.uniform(-30, 30),
                        vx=random.uniform(-40, 40),
                        vy=random.uniform(-60, -10),
                        kind="sparkle",
                        color=(255, 255, 255),
                        size=random.uniform(4, 8),
                    )
                )
            return True
        return False

    def tap_tito(self) -> None:
        self.tito_hop_offset = 25.0
        # Cheer sparkles
        for _ in range(6):
            self.particles.append(
                Particle(
                    x=230 + random.uniform(-30, 30),
                    y=440 + random.uniform(-20, 20),
                    vx=random.uniform(-50, 50),
                    vy=random.uniform(-90, -30),
                    kind="sparkle",
                    color=(255, 215, 0),
                    size=random.uniform(5, 9),
                )
            )

    def tap_apple(self, index: int) -> bool:
        if 0 <= index < len(self.apples):
            apple = self.apples[index]
            if not apple.in_basket and not apple.is_falling:
                apple.is_falling = True
                apple.fall_speed = 40.0
                return True
        return False

    def update(self, dt: float) -> None:
        self.tito_anim_timer += dt

        # Smooth day/night ratio transition
        if abs(self.day_ratio - self.target_day_ratio) > 0.001:
            step = dt * 1.8
            if self.day_ratio < self.target_day_ratio:
                self.day_ratio = min(self.target_day_ratio, self.day_ratio + step)
            else:
                self.day_ratio = max(self.target_day_ratio, self.day_ratio - step)

        # Tito hop decay
        if self.tito_hop_offset > 0.0:
            self.tito_hop_offset = max(0.0, self.tito_hop_offset - dt * 90.0)

        # Clouds movement
        wind_speed_mult = 3.5 if self.weather == WeatherMode.WIND else 1.0
        for c in self.clouds:
            c.x += c.speed * wind_speed_mult * dt
            if c.x > REFERENCE_WIDTH + 150:
                c.x = -150.0

        # Falling apples update
        for a in self.apples:
            if a.is_falling:
                a.fall_speed += 450.0 * dt
                a.fall_y += a.fall_speed * dt
                if a.fall_y > 220.0:  # Reached ground/basket
                    a.is_falling = False
                    a.in_basket = True
                    a.fall_y = 220.0

        # Weather particle spawning & physics
        self._update_weather_particles(dt)

    def _update_weather_particles(self, dt: float) -> None:
        # Spawn new particles
        if self.weather == WeatherMode.RAIN:
            if len(self.particles) < 90:
                for _ in range(4):
                    self.particles.append(
                        Particle(
                            x=random.uniform(0, REFERENCE_WIDTH),
                            y=random.uniform(-40, 10),
                            vx=random.uniform(-40, -10),
                            vy=random.uniform(400, 600),
                            kind="rain",
                            color=(135, 206, 250),
                            size=random.uniform(3, 5),
                        )
                    )
        elif self.weather == WeatherMode.SNOW or self.season == Season.WINTER:
            if len(self.particles) < 60:
                self.particles.append(
                    Particle(
                        x=random.uniform(0, REFERENCE_WIDTH),
                        y=-20,
                        vx=random.uniform(-20, 20),
                        vy=random.uniform(50, 110),
                        kind="snow",
                        color=(255, 255, 255),
                        size=random.uniform(3, 7),
                    )
                )
        elif self.weather == WeatherMode.WIND or self.season == Season.AUTUMN:
            if len(self.particles) < 40:
                leaf_colors = [(230, 81, 0), (255, 152, 0), (216, 67, 21), (245, 127, 23)]
                self.particles.append(
                    Particle(
                        x=random.uniform(400, 650),
                        y=random.uniform(150, 320),
                        vx=random.uniform(80, 180),
                        vy=random.uniform(30, 100),
                        kind="leaf",
                        color=random.choice(leaf_colors),
                        size=random.uniform(7, 13),
                        angle=random.uniform(0, math.pi * 2),
                    )
                )
        elif self.season in (Season.SPRING, Season.SUMMER) and self.weather == WeatherMode.SUN:
            # Occasional floating butterflies
            butterflies = [p for p in self.particles if p.kind == "butterfly"]
            if len(butterflies) < 3 and random.random() < 0.05:
                bf_colors = [(255, 105, 180), (255, 235, 59), (147, 112, 219)]
                self.particles.append(
                    Particle(
                        x=random.uniform(100, REFERENCE_WIDTH - 100),
                        y=random.uniform(300, 480),
                        vx=random.uniform(-40, 40),
                        vy=random.uniform(-20, 20),
                        kind="butterfly",
                        color=random.choice(bf_colors),
                        size=10.0,
                        life=8.0,
                    )
                )

        # Update and cull existing particles
        surviving = []
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            if p.kind == "butterfly":
                p.vx += random.uniform(-30, 30) * dt
                p.vy += random.uniform(-30, 30) * dt
                p.vx = max(-50.0, min(50.0, p.vx))
                p.vy = max(-30.0, min(30.0, p.vy))
                p.life -= dt
                if p.life > 0:
                    surviving.append(p)
            elif p.kind == "leaf":
                p.angle += dt * 3.0
                p.x += math.sin(p.angle) * 20.0 * dt
                if p.y < REFERENCE_HEIGHT - 30:
                    surviving.append(p)
            elif p.kind == "sparkle":
                p.life -= dt * 2.0
                if p.life > 0:
                    surviving.append(p)
            else:
                if p.y < REFERENCE_HEIGHT - 40 and 0 <= p.x <= REFERENCE_WIDTH:
                    surviving.append(p)
        self.particles = surviving
