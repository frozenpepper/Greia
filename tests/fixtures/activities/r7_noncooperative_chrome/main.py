from __future__ import annotations

import pygame

from greia_platform.activity_api import mark_activity_ready


def main() -> int:
    """Deliberately refuse every Activity-owned route back to Greia.

    R7 physical acceptance deploys this fixture only to a developer Activity
    source. It draws over the complete surface, provides no Home/Back helper,
    ignores all local input, and never checks the graceful STOP marker. The
    only supported way out is therefore Greia's trusted chrome followed by the
    platform lifecycle's bounded forced return.
    """

    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    screen.fill((178, 38, 55))
    pygame.draw.rect(screen, (90, 0, 18), screen.get_rect(), width=16)
    pygame.display.flip()
    mark_activity_ready()

    while True:
        # Keep SDL responsive enough to prove the window is alive, but ignore
        # every Activity-local key/pointer/quit event and intentionally do not
        # call activity_stop_requested().
        pygame.event.pump()
        pygame.time.wait(20)


if __name__ == "__main__":
    raise SystemExit(main())
