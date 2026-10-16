from __future__ import annotations

import re
import tempfile
import tomllib
import unittest
from pathlib import Path

import pygame

from greia_platform.achievement_art import ActivityAchievementEmblem
from greia_platform.achievements import (
    AchievementDefinition,
    AchievementEntry,
    LocalizedAchievementText,
)
from greia_platform.pygame_achievements import (
    AWARD_SLOTS,
    PygameAchievementBadgeRenderer,
    award_family,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
AWARD_MASTERS = REPO_ROOT / "assets" / "source" / "achievements"
SOURCE_SPEC = REPO_ROOT / "assets" / "catalog" / "shared_visuals_v1_source.toml"
_FORBIDDEN_SVG = re.compile(
    r'<image|data:|<text|<tspan|<filter|fe[A-Z]|<mask|<pattern|<style|<script|'
    r'foreignObject|<animate|blend-mode|skew|href="[^#]|xlink:href="[^#]|sodipodi|inkscape:'
)


def _text(value: str) -> LocalizedAchievementText:
    return LocalizedAchievementText((("en", value),), "en")


def _entry(
    *,
    unlocked: bool,
    tier: str = "gold",
    secret: bool = False,
    achievement_id: str = "greia.test.badge",
    activity_emblem: ActivityAchievementEmblem | None = None,
) -> AchievementEntry:
    definition = AchievementDefinition(
        achievement_id=achievement_id,
        category="test",
        tier=tier,
        icon_id="yellow_star",
        secret=secret,
        title=_text("Badge"),
        description=_text("Description"),
        locked_hint=_text("Hint"),
        criteria=(),
        activity_emblem=activity_emblem,
    )
    return AchievementEntry(
        definition=definition,
        unlocked_at=10.0 if unlocked else None,
        announced_at=None,
        seen_at=None,
    )


class _IconProvider:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, _icon_id: str, size: int, pygame_module):
        self.calls += 1
        surface = pygame_module.Surface((size, size), pygame_module.SRCALPHA)
        pygame_module.draw.circle(
            surface,
            (255, 215, 60),
            (size // 2, size // 2),
            max(1, size // 3),
        )
        return surface


class AchievementBadgeRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_same_semantic_badge_is_one_cache_entry(self) -> None:
        provider = _IconProvider()
        renderer = PygameAchievementBadgeRenderer(provider, max_entries=4)
        entry = _entry(unlocked=True)

        first = renderer.render(entry, 96)
        second = renderer.render(entry, 96)

        self.assertIs(first, second)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(first.get_size(), (96, 96))

    def test_locked_badge_does_not_request_reward_icon(self) -> None:
        provider = _IconProvider()
        renderer = PygameAchievementBadgeRenderer(provider)
        locked = renderer.render(_entry(unlocked=False), 80)
        self.assertEqual(provider.calls, 0)
        self.assertEqual(locked.get_size(), (80, 80))

    def test_size_is_bounded_and_never_full_screen(self) -> None:
        provider = _IconProvider()
        renderer = PygameAchievementBadgeRenderer(provider)
        badge = renderer.render(_entry(unlocked=True), 10_000)
        self.assertEqual(badge.get_size(), (220, 220))
        self.assertTrue(badge.get_flags() & pygame.SRCALPHA)

    def test_each_unlocked_award_family_uses_semantic_icon_once(self) -> None:
        provider = _IconProvider()
        renderer = PygameAchievementBadgeRenderer(provider)

        medal = renderer.render(
            _entry(unlocked=True, tier="silver", achievement_id="greia.test.medal"),
            96,
        )
        trophy = renderer.render(
            _entry(unlocked=True, tier="gold", achievement_id="greia.test.trophy"),
            96,
        )
        special = renderer.render(
            _entry(unlocked=True, tier="special", achievement_id="greia.test.special"),
            96,
        )

        self.assertEqual(provider.calls, 3)
        self.assertEqual(medal.get_size(), (96, 96))
        self.assertEqual(trophy.get_size(), (96, 96))
        self.assertEqual(special.get_size(), (96, 96))
        self.assertIsNot(medal, trophy)
        self.assertIsNot(trophy, special)

    def test_secret_gold_uses_special_family_but_keeps_bounded_cache(self) -> None:
        provider = _IconProvider()
        renderer = PygameAchievementBadgeRenderer(provider, max_entries=4)
        entry = _entry(
            unlocked=True,
            tier="gold",
            secret=True,
            achievement_id="greia.test.constellation",
        )

        first = renderer.render(entry, 110)
        second = renderer.render(entry, 110)

        self.assertIs(first, second)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(first.get_size(), (110, 110))

    def test_admitted_activity_emblem_replaces_fallback_icon_and_is_cached(self) -> None:
        provider = _IconProvider()
        renderer = PygameAchievementBadgeRenderer(provider, max_entries=4)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "emblem.png"
            source = pygame.Surface((64, 64), pygame.SRCALPHA)
            source.fill((0, 0, 0, 0))
            pygame.draw.circle(source, (42, 190, 110), (32, 32), 24)
            pygame.image.save(source, path)
            emblem = ActivityAchievementEmblem(
                activity_id="org.greia.test-activity",
                emblem_id="activity",
                asset_path=path,
                width=64,
                height=64,
                byte_size=path.stat().st_size,
            )
            entry = _entry(
                unlocked=True,
                tier="silver",
                achievement_id="greia.test.activity-art",
                activity_emblem=emblem,
            )

            first = renderer.render(entry, 96)
            second = renderer.render(entry, 96)

        self.assertIs(first, second)
        self.assertEqual(provider.calls, 0)
        self.assertEqual(first.get_size(), (96, 96))

    def test_broken_activity_emblem_falls_back_to_platform_icon(self) -> None:
        provider = _IconProvider()
        renderer = PygameAchievementBadgeRenderer(provider)
        emblem = ActivityAchievementEmblem(
            activity_id="org.greia.test-activity",
            emblem_id="broken",
            asset_path=Path("/definitely/missing/greia-achievement-emblem.png"),
            width=64,
            height=64,
            byte_size=128,
        )
        badge = renderer.render(
            _entry(
                unlocked=True,
                tier="bronze",
                achievement_id="greia.test.broken-art",
                activity_emblem=emblem,
            ),
            96,
        )

        self.assertEqual(provider.calls, 1)
        self.assertEqual(badge.get_size(), (96, 96))


class _FrameProvider:
    """Stand-in for the shared ``ui.award.<family>`` renditions."""

    def __init__(self, *, fail: bool = False, missing: bool = False) -> None:
        self.calls: list[tuple[str, bool, int]] = []
        self.fail = fail
        self.missing = missing

    def __call__(self, family: str, locked: bool, size: int, pygame_module):
        self.calls.append((family, locked, size))
        if self.fail:
            raise pygame_module.error("corrupt rendition")
        if self.missing:
            return None
        native = 64 if size <= 64 else 112 if size <= 112 else 160
        surface = pygame_module.Surface((native, native), pygame_module.SRCALPHA)
        surface.fill((10, 200, 30, 255) if not locked else (120, 120, 120, 255))
        return surface


class AwardRenditionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_renderer_uses_shared_award_rendition_with_emblem_in_slot(self) -> None:
        icons = _IconProvider()
        frames = _FrameProvider()
        renderer = PygameAchievementBadgeRenderer(icons, frame_provider=frames)

        badge = renderer.render(_entry(unlocked=True, tier="silver"), 112)

        self.assertEqual(frames.calls, [("silver", False, 112)])
        self.assertEqual(icons.calls, 1)
        # Frame pixels (rendition fill) outside the slot, icon in the slot.
        self.assertEqual(tuple(badge.get_at((4, 4)))[:3], (10, 200, 30))
        cx, cy, _radius = AWARD_SLOTS["silver"]
        centre = badge.get_at((int(cx * 112 / 256), int(cy * 112 / 256)))
        self.assertEqual(tuple(centre)[:3], (255, 215, 60))

    def test_locked_badge_uses_locked_rendition_and_never_requests_art(self) -> None:
        icons = _IconProvider()
        frames = _FrameProvider()
        renderer = PygameAchievementBadgeRenderer(icons, frame_provider=frames)
        renderer.render(_entry(unlocked=False, tier="bronze"), 64)
        self.assertEqual(frames.calls, [("bronze", True, 64)])
        self.assertEqual(icons.calls, 0)

    def test_secret_and_special_use_the_rosette_family(self) -> None:
        self.assertEqual(award_family("gold", secret=True), "special")
        self.assertEqual(award_family("special", secret=False), "special")
        self.assertEqual(award_family("gold", secret=False), "gold")
        self.assertEqual(award_family("unknown", secret=False), "bronze")

    def test_procedural_frame_is_the_fail_soft_fallback(self) -> None:
        for frames in (_FrameProvider(fail=True), _FrameProvider(missing=True)):
            with self.subTest(fail=frames.fail):
                icons = _IconProvider()
                renderer = PygameAchievementBadgeRenderer(icons, frame_provider=frames)
                badge = renderer.render(_entry(unlocked=True, tier="gold"), 96)
                self.assertEqual(len(frames.calls), 1)
                self.assertEqual(icons.calls, 1)
                self.assertEqual(badge.get_size(), (96, 96))
                # No rendition fill leaked into the procedural trophy.
                self.assertNotEqual(tuple(badge.get_at((2, 2)))[:3], (10, 200, 30))

    def test_cache_stays_bounded_at_64(self) -> None:
        renderer = PygameAchievementBadgeRenderer(
            _IconProvider(), frame_provider=_FrameProvider()
        )
        self.assertLessEqual(renderer.max_entries, 64)
        for index in range(90):
            renderer.render(
                _entry(unlocked=True, tier="bronze", achievement_id=f"greia.test.b{index}"),
                48 + index % 7,
            )
        self.assertLessEqual(len(renderer), 64)

    def test_award_masters_follow_svg_rules_and_slot_geometry(self) -> None:
        slot_circles = {
            "bronze": (128, 100, 56),
            "silver": (128, 100, 56),
            "gold": (128, 98, 42),
            "special": (128, 100, 47),
        }
        for family, (cx, cy, radius) in slot_circles.items():
            for suffix in ("", "_locked"):
                with self.subTest(family=family, locked=bool(suffix)):
                    source = (AWARD_MASTERS / f"award_{family}{suffix}.svg").read_text("utf-8")
                    self.assertIsNone(_FORBIDDEN_SVG.search(source))
                    self.assertIn('viewBox="0 0 256 256"', source)
                    self.assertLessEqual(len(source.encode("utf-8")), 6 * 1024)
                    self.assertIn(f'<circle cx="{cx}" cy="{cy}" r="{radius}"', source)
                    self.assertEqual(AWARD_SLOTS[family], (float(cx), float(cy), float(radius)))
                    for stops in re.findall(r"<linearGradient.*?</linearGradient>", source, re.S):
                        self.assertLessEqual(stops.count("<stop"), 2)

    def test_every_award_frame_has_catalogued_renditions(self) -> None:
        with SOURCE_SPEC.open("rb") as stream:
            spec = tomllib.load(stream)
        visuals = {item["id"]: item for item in spec["visuals"]}
        for family in AWARD_SLOTS:
            with self.subTest(family=family):
                variants = {v["name"]: v for v in visuals[f"ui.award.{family}"]["variants"]}
                self.assertEqual(
                    set(variants),
                    {"default", "size_112", "size_64", "locked", "locked_112", "locked_64"},
                )
                for name, variant in variants.items():
                    expected = 160 if name in {"default", "locked"} else int(name.rsplit("_", 1)[1])
                    self.assertEqual((variant["width"], variant["height"]), (expected, expected))
                    self.assertTrue((REPO_ROOT / "assets" / variant["output"]).is_file())


if __name__ == "__main__":
    unittest.main()
