from __future__ import annotations

import subprocess
import sys
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GreiaSimulatorImportShadowingTests(unittest.TestCase):
    def test_tools_shim_does_not_block_real_simulator_submodules(self) -> None:
        """Even a tools-first sys.path must still expose the real package."""

        probe = textwrap.dedent(
            f"""
            import sys
            from pathlib import Path

            root = Path({str(ROOT)!r})
            tools = str(root / 'tools')
            src = str(root / 'src')
            repo = str(root)
            preserved = [p for p in sys.path if p not in {{tools, src, repo}}]
            sys.path[:] = [tools, src, repo, *preserved]

            import greia_simulator
            from greia_simulator.device import parse_viewport

            package_paths = [Path(p).resolve() for p in getattr(greia_simulator, '__path__', ())]
            expected = (root / 'src' / 'greia_simulator').resolve()
            assert expected in package_paths, (package_paths, expected)
            assert parse_viewport('1024x600') == (1024, 600)
            """
        )
        completed = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=(
                "tools-first greia_simulator import probe failed\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            ),
        )


if __name__ == "__main__":
    unittest.main()
