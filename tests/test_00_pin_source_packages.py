"""Pin the real src packages before other tests put ``tools/`` on sys.path.

``tools/greia_parent.py`` and ``tools/greia_simulator.py`` are launcher scripts
named like the ``src`` packages.  Many tests prepend ``tools/`` to ``sys.path``
at import time; once that happened, a later ``import greia_parent`` loaded the
script ("'greia_parent' is not a package") under plain
``unittest discover -s tests``.  Discovery imports modules alphabetically, so
this module (named to sort first) imports the real packages into
``sys.modules`` before any such path edit.  ``make test`` pins them the same
way through ``suite_lanes``.
"""

from __future__ import annotations

import importlib
import unittest

_SHADOWED_PACKAGES = ("greia_parent", "greia_simulator")

for _name in _SHADOWED_PACKAGES:
    importlib.import_module(_name)


class SourcePackagePinTest(unittest.TestCase):
    def test_shadowed_names_resolve_to_packages(self) -> None:
        for name in _SHADOWED_PACKAGES:
            module = importlib.import_module(name)
            self.assertTrue(hasattr(module, "__path__"), name)


if __name__ == "__main__":
    unittest.main()
