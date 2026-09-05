"""Developer-mode explicitness for launcher boot composition (T35, PLAN D3).

Production boot with developer mode off configures no developer
``ActivitySource`` and performs no developer-root filesystem scan. Developer
mode on keeps live ``ActivityRegistry`` validation on the explicit developer
path without ever promoting developer trust to built-in trust.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from greia_launcher import main as launcher_main
from greia_platform.activities import (
    ActivityRegistry,
    ActivityValidationError,
    RuntimeCatalogue,
)
from greia_platform.trust import PackageTrust


def _write_activity(
    root: Path,
    *,
    activity_id: str,
    api_version: str = "0.1",
    body: str = "pass\n",
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    root.joinpath("activity.toml").write_text(
        f'''[activity]
id = "{activity_id}"
legacy_ids = []
title_key = "Test Activity"
version = "1.0.0"
icon = "robot"
languages = ["*"]

[presentation]
categories = ["play"]

[education]
categories = ["test"]
difficulty = 1
skills = [{{ id = "test.skill", weight = 1 }}]
events = [{{ id = "probe.completed", kind = "completion" }}]

[runtime]
type = "python"
api_version = "{api_version}"
entrypoint = "main.py"

[input]
profile = "hybrid"

[requirements]
required_capabilities = []
optional_capabilities = []

[permissions]
requested = []

[storage]
schema_version = 1
''',
        encoding="utf-8",
    )
    root.joinpath("main.py").write_text(body, encoding="utf-8")
    return root


class DeveloperModeExplicitnessTests(unittest.TestCase):
    def _tree(self, tmp: str) -> tuple[Path, Path]:
        builtin_root = Path(tmp) / "builtin"
        dev_root = Path(tmp) / "dev"
        _write_activity(
            builtin_root / "builtin.pkg", activity_id="org.greia.builtin-probe"
        )
        _write_activity(dev_root / "dev.pkg", activity_id="org.greia.dev-probe")
        return builtin_root, dev_root

    def test_mode_off_excludes_developer_source_and_performs_no_dev_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            builtin_root, dev_root = self._tree(tmp)
            missing_marker = Path(tmp) / "no-marker"
            self.assertFalse(missing_marker.exists())
            with mock.patch.dict(
                os.environ,
                {launcher_main.DEVELOPER_MARKER_ENV_VAR: str(missing_marker)},
                clear=False,
            ):
                self.assertFalse(launcher_main.is_developer_mode())
                paths = SimpleNamespace(
                    activities=builtin_root,
                    developer_activities=dev_root,
                )
                # Explicit helper: no developer source when mode is off, even
                # though a developer root is configured.
                self.assertIsNone(
                    launcher_main.developer_activity_source(dev_root)
                )
                # Production boot source set excludes the developer root.
                sources = launcher_main.boot_activity_sources(paths)
                self.assertEqual(len(sources), 1)
                self.assertEqual(sources[0].trust, PackageTrust.BUILT_IN)
                self.assertEqual(
                    sources[0].source_id, launcher_main.BUILT_IN_SOURCE_ID
                )
                for source in sources:
                    self.assertNotEqual(
                        Path(source.root).resolve(), dev_root.resolve()
                    )

                runtime = RuntimeCatalogue.default_safe()
                registry = ActivityRegistry(
                    sources, runtime, fail_closed=False
                )
                self.assertNotIn(
                    dev_root.resolve().as_posix(),
                    [root.resolve().as_posix() for root in registry._roots],
                )

                # No developer-root filesystem scan: spy on directory listing
                # while the production registry reads its token and discovers.
                seen: list[str] = []
                real_glob = Path.glob

                def _spy(self: Path, pattern: str, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
                    if pattern == "*/activity.toml":
                        seen.append(self.resolve().as_posix())
                    return real_glob(self, pattern, *args, **kwargs)  # type: ignore[arg-type]

                with mock.patch.object(Path, "glob", _spy):
                    token = registry.discovery_token()
                    discovered = registry.discover()
                dev_prefix = dev_root.resolve().as_posix()
                self.assertFalse(
                    any(
                        entry == dev_prefix
                        or entry.startswith(dev_prefix + "/")
                        for entry in seen
                    ),
                    f"production boot scanned developer root: {seen}",
                )
                token_text = repr(token)
                self.assertNotIn(dev_prefix, token_text)
                found = {item.activity_id for item in discovered}
                self.assertIn("org.greia.builtin-probe", found)
                self.assertNotIn("org.greia.dev-probe", found)

    def test_mode_on_uses_live_discovery_without_promoting_trust(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            builtin_root, dev_root = self._tree(tmp)
            marker = Path(tmp) / "developer-remote"
            marker.write_text("profile=modern-amd64-dev\n", encoding="utf-8")
            with mock.patch.dict(
                os.environ,
                {launcher_main.DEVELOPER_MARKER_ENV_VAR: str(marker)},
                clear=False,
            ):
                self.assertTrue(launcher_main.is_developer_mode())
                dev_source = launcher_main.developer_activity_source(dev_root)
                self.assertIsNotNone(dev_source)
                assert dev_source is not None
                # Developer trust is never promoted to built-in trust and the
                # developer index is never consumed as a built-in index: the
                # explicit source carries developer identity only.
                self.assertEqual(dev_source.trust, PackageTrust.DEVELOPER_UNSIGNED)
                self.assertNotEqual(dev_source.trust, PackageTrust.BUILT_IN)
                self.assertEqual(
                    dev_source.source_id, launcher_main.DEVELOPER_SOURCE_ID
                )
                self.assertNotEqual(
                    dev_source.source_id, launcher_main.BUILT_IN_SOURCE_ID
                )

                paths = SimpleNamespace(
                    activities=builtin_root,
                    developer_activities=dev_root,
                )
                sources = launcher_main.boot_activity_sources(paths)
                self.assertEqual(len(sources), 2)
                self.assertEqual(sources[0].trust, PackageTrust.BUILT_IN)
                self.assertEqual(
                    sources[1].trust, PackageTrust.DEVELOPER_UNSIGNED
                )
                self.assertEqual(
                    sources[1].source_id, launcher_main.DEVELOPER_SOURCE_ID
                )

                runtime = RuntimeCatalogue.default_safe()
                # Live registry discovery on the explicit developer path.
                registry = ActivityRegistry(
                    sources, runtime, fail_closed=False
                )
                registrations = registry.discover_registrations()
                by_id = {item.manifest.activity_id: item for item in registrations}
                self.assertIn("org.greia.builtin-probe", by_id)
                self.assertIn("org.greia.dev-probe", by_id)
                dev_reg = by_id["org.greia.dev-probe"]
                self.assertEqual(
                    dev_reg.package_trust, PackageTrust.DEVELOPER_UNSIGNED
                )
                self.assertNotEqual(dev_reg.package_trust, PackageTrust.BUILT_IN)
                self.assertEqual(
                    dev_reg.source_id, launcher_main.DEVELOPER_SOURCE_ID
                )
                self.assertTrue(
                    dev_reg.manifest.root.resolve().as_posix().startswith(
                        dev_root.resolve().as_posix() + "/"
                    )
                )
                builtin_reg = by_id["org.greia.builtin-probe"]
                self.assertEqual(builtin_reg.package_trust, PackageTrust.BUILT_IN)

                # Live validation semantics are preserved: a corrupt developer
                # package still fails closed on the explicit path.
                broken = dev_root / "broken.pkg"
                _write_activity(
                    broken,
                    activity_id="org.greia.dev-broken",
                    api_version="9.9",
                )
                strict = ActivityRegistry(sources, runtime, fail_closed=True)
                with self.assertRaises(ActivityValidationError):
                    strict.discover_registrations()

    def test_no_developer_index_consumed_as_builtin(self) -> None:
        # The launcher boot path consumes live registry discovery only; it
        # must not wire a developer payload through the built-in index loader.
        source_path = Path(launcher_main.__file__).read_text(encoding="utf-8")
        self.assertNotIn("ActivityIndexLoader", source_path)
        self.assertNotIn("activity_index", source_path)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
