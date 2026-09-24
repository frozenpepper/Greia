"""Executable wrapper for the Greia install-transaction service.

The service implementation lives in ``greia_installer.transaction_service``
and must be imported under that canonical module name. Keeping the executable
entrypoint separate prevents ``python -m`` from loading the implementation once
as ``__main__`` and again as ``greia_installer.transaction_service`` through
composition imports, which would split class/module identity inside one process.
"""

from __future__ import annotations

import sys

from .transaction_service import main


if __name__ == "__main__":  # pragma: no cover - executable wrapper
    raise SystemExit(main(sys.argv[1:]))
