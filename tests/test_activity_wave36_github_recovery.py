"""Regression for missing Wave 36 gameplay repairs restored to GitHub main.

Provider-free; run with the supported Pygame/Greia test environment.
These are source/interaction tests, not a substitute for real child sessions.
"""

from __future__ import annotations

# Memory Meraviglie's keyboard-only round, theme/grid key switching and
# wrong-pair lock moved to tests/test_activity_memory_meraviglie.py
# (AppLoopTests: keyboard board, pointer round, miss lock) when the Activity
# was reworked into Wonder Match on the shared control kit; albums are now
# chosen by picture tiles and the grid adapts, so the old T/G/N keys, MemoryApp
# dict cards and unflip timer no longer exist.


# Magical Labyrinth's "a new command cannot overwrite an active slide" lock
# moved to tests/test_activity_labirinto_magico.py (AppLoopTests) when the
# Activity was reworked onto the shared control kit; a press while Tito walks
# is now one buffered turn applied on arrival. The old MazeApp/MazeEngine no
# longer exist.


# Treno Numeri's keyboard-only journey and bounded-celebration recovery moved to
# tests/test_activity_treno_numeri.py (AppLoopTests) when the Activity was
# reworked onto the shared control kit; the old TrainModel/auto-cap app no
# longer exists.


# Stelle Incantate's keyboard-only figure and number-input recovery moved to
# tests/test_activity_stelle_incantate.py (AppLoopTests) when the Activity was
# reworked onto the shared control kit; the old SkySession/auto-focus app no
# longer exists. Its "fact speech disallows foreign-language fallback" check was
# retired: the owner's speech fallback policy (selected -> base -> English ->
# silence) supersedes it.


