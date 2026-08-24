from __future__ import annotations

from .maze_app import MazeApp
from .maze_audio import LabyrinthAudio, MazeAudio
from .maze_model import (
    BIOMES,
    DIFFICULTIES,
    HEROES,
    CollectibleStar,
    MazeEngine,
    MazeState,
)


def main() -> int:
    return MazeApp().run()


if __name__ == "__main__":
    raise SystemExit(main())
