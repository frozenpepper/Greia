"""Platform-owned interpreter entry point for Python Activity processes.

``PythonRuntimeAdapter`` launches ``python3 -P -m
greia_platform.python_activity_entry <Activity main.py>`` instead of executing
the Activity script directly. The platform then applies the curated
interpreter start-up policy (:mod:`greia_platform.python_startup`) before any
Activity import runs, and only afterwards executes the Activity's entry script
with ordinary script semantics:

* ``__name__ == "__main__"`` and ``__file__`` is the entry script;
* ``sys.argv[0]`` is the entry script and later arguments are preserved;
* ``sys.path[0]`` is the entry script's directory (``-P`` stops the
  interpreter from prepending the working directory first, so the Activity
  directory cannot shadow ``greia_platform`` before this module is running).

Before the script runs, the entry also routes ``pygame.mixer`` through the
platform's idle mixer lease (:mod:`greia_platform.activity_mixer_lease`), so
every Activity's audio device closes after 10 s of silence and reopens on the
next sound without Activity code changes.

This module grants nothing: it runs inside the same sandbox, environment and
identity as the Activity and has no access the Activity itself lacks.
"""

from __future__ import annotations

import os
import runpy
import sys
from typing import Sequence

from .python_startup import apply_curated_interpreter_startup


class ActivityEntryError(RuntimeError):
    """The platform entry received no usable Activity entry script."""


def run_activity_script(argv: Sequence[str]) -> None:
    """Execute ``argv[0]`` as ``__main__`` after the curated start-up policy."""

    if not argv:
        raise ActivityEntryError("Activity entry script is required")
    script = os.path.abspath(argv[0])
    if not script.endswith(".py") or not os.path.isfile(script):
        raise ActivityEntryError(f"Activity entry script is not a .py file: {script}")
    apply_curated_interpreter_startup()
    _install_mixer_lease()
    sys.argv[:] = [script, *argv[1:]]
    sys.path.insert(0, os.path.dirname(script))
    runpy.run_path(script, run_name="__main__")


def _install_mixer_lease() -> None:
    """Fail-soft: without the lease the mixer simply stays open, as before."""

    try:
        from .activity_mixer_lease import install_activity_mixer_lease

        install_activity_mixer_lease()
    except Exception as exc:  # noqa: BLE001 - never block the Activity launch
        print(f"greia: idle audio release unavailable: {exc}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        run_activity_script(sys.argv[1:] if argv is None else argv)
    except ActivityEntryError as exc:
        print(f"greia: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
