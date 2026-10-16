"""Child-facing launcher for Greia OS.

Every Shell entry point (``python3 -m greia_launcher.child_shell``, the
trusted fallback ``greia_launcher.trusted_presentation`` and the development
``greia_launcher.main``) imports this package first, and their module imports
reach ``import pygame``. The curated interpreter start-up policy therefore
runs here, once, before any launcher submodule is imported; see
:mod:`greia_platform.python_startup` for what it blocks and why.
"""

from greia_platform.python_startup import apply_curated_interpreter_startup

apply_curated_interpreter_startup()
