"""Greia composition root for My Time."""
from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.localization import activity_resources

if __package__:
    from .time_app import TimeActivity
    from .time_renderer import WORD_KEYS
    from .time_audio import LocalTimeSpeechTransport
    from .time_speech import TimeSpeech
else:
    from time_app import TimeActivity
    from time_renderer import WORD_KEYS
    from time_audio import LocalTimeSpeechTransport
    from time_speech import TimeSpeech


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((1024, 600), pygame.RESIZABLE)
    resources = activity_resources(Path(__file__).resolve().parent)
    locale = resources.context.selected.language
    words = {key: resources.text(key) for key in WORD_KEYS}
    speech = TimeSpeech(LocalTimeSpeechTransport(resources))
    return TimeActivity(screen, locale, words, speech=speech).run()


if __name__ == "__main__":
    raise SystemExit(main())
