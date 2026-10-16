"""Curated interpreter start-up policy shared by every Greia Python process.

Greia processes (child Shell, trusted fallback presentation and every Python
Activity) run on the one curated system interpreter. Some distribution modules
pull expensive optional dependencies in at import time even though Greia never
uses them. The clearest case is ``pkg_resources`` (setuptools): Pygame's
``pygame.pkgdata`` - imported by ``import pygame`` itself - tries
``from pkg_resources import resource_stream, resource_exists`` and falls back
to a plain package-directory ``open()`` when that import fails. Importing
``pkg_resources`` scans every ``sys.path`` entry for distributions; measured
on the Atom N270 reference device it cost about 3.6 s per process, for a
resource lookup that resolves to the very same file either way (Greia's
Pygame is a normal filesystem package, never a zip/egg).

The policy uses the documented import-system contract: a ``None`` entry in
``sys.modules`` makes ``import name`` raise ``ModuleNotFoundError`` (an
``ImportError``) immediately, which Pygame's guarded import already handles.
It must run before the first ``import pygame``; it never removes a module that
some code already imported, and it is idempotent.
"""

from __future__ import annotations

import sys
from typing import Final, MutableMapping

#: Optional modules that no Greia process may spend start-up time importing.
#: Every entry must be imported only behind an ``except ImportError`` fallback
#: by the curated runtime packages; add nothing that a dependency needs.
BLOCKED_STARTUP_MODULES: Final[tuple[str, ...]] = ("pkg_resources",)


def apply_curated_interpreter_startup(
    modules: MutableMapping[str, object] | None = None,
) -> tuple[str, ...]:
    """Block unused optional start-up imports; return the names newly blocked.

    ``modules`` defaults to ``sys.modules`` and exists only so tests can verify
    the policy without mutating the test runner's interpreter.
    """

    table = sys.modules if modules is None else modules
    blocked: list[str] = []
    for name in BLOCKED_STARTUP_MODULES:
        if name not in table:
            table[name] = None  # type: ignore[assignment]
            blocked.append(name)
    return tuple(blocked)


__all__ = ["BLOCKED_STARTUP_MODULES", "apply_curated_interpreter_startup"]
