from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from greia_platform.pygame_completion import (
    CompletionContent,
    CompletionPalette,
    PygameCompletionScreen,
)


class CountingTypography:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def render(self, text, role, size, color):
        self.calls.append((str(text), int(size)))
        return pygame.Surface((max(1, len(str(text)) * 8), max(1, int(size) + 4)))


class PygameCompletionScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_prepared_frame_is_opaque_and_repeated_draw_does_not_render_text(self) -> None:
        typography = CountingTypography()
        completion = PygameCompletionScreen(typography)
        content = CompletionContent(
            title="Great work!",
            body_lines=("Five rounds complete",),
            primary_label="Play again",
            achievement_count=5,
        )

        completion.prepare(content)
        prepared = completion.prepared_surface
        self.assertIsNotNone(prepared)
        assert prepared is not None
        self.assertEqual(prepared.get_flags() & pygame.SRCALPHA, 0)
        render_calls = len(typography.calls)
        self.assertGreater(render_calls, 0)

        target = pygame.Surface((1024, 600))
        frame_identity = id(prepared)
        for _ in range(20):
            completion.draw(target)

        self.assertEqual(len(typography.calls), render_calls)
        self.assertEqual(id(completion.prepared_surface), frame_identity)

    def test_same_semantic_content_does_not_rebuild_but_changed_content_does(self) -> None:
        typography = CountingTypography()
        completion = PygameCompletionScreen(typography)
        first = CompletionContent(title="Done", primary_label="Again")

        completion.prepare(first)
        initial_calls = len(typography.calls)
        initial_surface = completion.prepared_surface
        completion.prepare(first)

        self.assertEqual(len(typography.calls), initial_calls)
        self.assertIs(completion.prepared_surface, initial_surface)

        completion.prepare(
            CompletionContent(
                title="Done",
                body_lines=("New score",),
                primary_label="Again",
            )
        )
        self.assertGreater(len(typography.calls), initial_calls)
        self.assertIsNot(completion.prepared_surface, initial_surface)

    def test_palette_change_invalidates_prepared_frame(self) -> None:
        typography = CountingTypography()
        completion = PygameCompletionScreen(typography)
        content = CompletionContent(title="Done", primary_label="Again")
        completion.prepare(content)
        first_surface = completion.prepared_surface

        completion.prepare(
            content,
            palette=CompletionPalette(background=(20, 30, 40)),
        )

        self.assertIsNot(completion.prepared_surface, first_surface)

    def test_primary_hit_target_is_stable_and_clear_releases_frame(self) -> None:
        completion = PygameCompletionScreen(CountingTypography())
        completion.prepare(CompletionContent(title="Done", primary_label="Again"))

        self.assertTrue(completion.primary_contains(completion.primary_rect.center))
        self.assertFalse(completion.primary_contains((0, 0)))

        completion.clear()
        self.assertFalse(completion.is_prepared)
        with self.assertRaisesRegex(RuntimeError, "must be prepared"):
            completion.draw(pygame.Surface((1024, 600)))

    def test_invalid_content_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CompletionContent(title="", primary_label="Again")
        with self.assertRaises(ValueError):
            CompletionContent(title="Done", primary_label="")
        with self.assertRaises(ValueError):
            CompletionContent(title="Done", primary_label="Again", achievement_count=-1)


if __name__ == "__main__":
    unittest.main()
