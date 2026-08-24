from __future__ import annotations

from pathlib import Path
import sys

_ACTIVITY_DIR = Path(__file__).resolve().parent
if str(_ACTIVITY_DIR) not in sys.path:
    sys.path.insert(0, str(_ACTIVITY_DIR))

try:
    from maze_app import MazeApp
    from maze_audio import LabyrinthAudio, MazeAudio
    from maze_model import (
        BIOMES,
        DIFFICULTIES,
        HEROES,
        CollectibleStar,
        MazeEngine,
        MazeState,
    )
except ImportError:
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
