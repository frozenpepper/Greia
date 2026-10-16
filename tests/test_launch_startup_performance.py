"""Launch start-up performance contracts (Acer sweep 2026-10-16 §3.2/§3.3/§3.5).

Covers the curated interpreter start-up policy (no pkg_resources), the
platform Python Activity entry, the image-owned read-only bytecode prefix,
the hardware-aware READY timeout and the Shell foreground cadence.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_launcher.foreground_cadence import ActivityForegroundCadence
from greia_launcher.launch_timing import (
    DEFAULT_READY_TIMEOUT_SECONDS,
    MAXIMUM_READY_TIMEOUT_SECONDS,
    ActivityReadyTimeoutPolicy,
    installed_compatibility_class,
    ready_timeout_for,
    resolve_ready_timeout_seconds,
)
from greia_launcher.lifecycle import ActivitySessionState
from greia_launcher.runtime_adapter import PythonRuntimeAdapter
from greia_platform.assets import AssetCatalogueError, _AssetPathResolver, _safe_path
from greia_platform.bytecode_cache import (
    TRUSTED_BYTECODE_PREFIX,
    BytecodePrecompiler,
    TrustedBytecodePrefix,
)
from greia_platform.python_startup import (
    BLOCKED_STARTUP_MODULES,
    apply_curated_interpreter_startup,
)


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _python_env(**extra: str) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PYTHON")
    }
    env.update(
        PYTHONPATH=str(SRC),
        PYTHONDONTWRITEBYTECODE="1",
        PYGAME_HIDE_SUPPORT_PROMPT="1",
        SDL_VIDEODRIVER="dummy",
        SDL_AUDIODRIVER="dummy",
    )
    env.update(extra)
    return env


class CuratedInterpreterStartupTests(unittest.TestCase):
    def test_blocks_pkg_resources_without_replacing_loaded_modules(self) -> None:
        table: dict[str, object] = {}
        self.assertEqual(apply_curated_interpreter_startup(table), ("pkg_resources",))
        self.assertIsNone(table["pkg_resources"])
        self.assertEqual(apply_curated_interpreter_startup(table), ())

        loaded = object()
        table = {"pkg_resources": loaded}
        self.assertEqual(apply_curated_interpreter_startup(table), ())
        self.assertIs(table["pkg_resources"], loaded)
        self.assertIn("pkg_resources", BLOCKED_STARTUP_MODULES)

    def test_pygame_falls_back_cleanly_when_pkg_resources_is_blocked(self) -> None:
        # pygame.pkgdata guards the import with ``except ImportError`` and then
        # opens package resources directly; the default font must still load.
        code = (
            "import sys\n"
            "from greia_platform.python_startup import apply_curated_interpreter_startup\n"
            "apply_curated_interpreter_startup()\n"
            "import pygame, pygame.pkgdata\n"
            "pygame.font.init()\n"
            "assert pygame.font.Font(None, 20).size('Hi')[0] > 0\n"
            "assert sys.modules['pkg_resources'] is None\n"
            "print('ok')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], env=_python_env(),
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok", result.stdout)

    def test_shell_package_applies_policy_before_pygame(self) -> None:
        code = (
            "import sys, greia_launcher\n"
            "assert sys.modules.get('pkg_resources', 'absent') is None\n"
            "assert 'pygame' not in sys.modules\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], env=_python_env(),
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class PythonActivityEntryTests(unittest.TestCase):
    def test_entry_runs_script_with_script_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            activity = Path(temporary) / "activity"
            activity.mkdir()
            (activity / "helper.py").write_text("VALUE = 7\n", encoding="utf-8")
            (activity / "main.py").write_text(
                "import sys, json, helper\n"
                "print(json.dumps({'name': __name__, 'argv': sys.argv, "
                "'path0': sys.path[0], 'blocked': sys.modules.get('pkg_resources', 'x') is None, "
                "'helper': helper.VALUE}))\n"
                "raise SystemExit(3)\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "-P", "-m", "greia_platform.python_activity_entry",
                 str(activity / "main.py"), "extra"],
                cwd=temporary, env=_python_env(),
                capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 3, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["name"], "__main__")
        self.assertEqual(Path(payload["argv"][0]).name, "main.py")
        self.assertEqual(payload["argv"][1:], ["extra"])
        self.assertEqual(Path(payload["path0"]).name, "activity")
        self.assertTrue(payload["blocked"])
        self.assertEqual(payload["helper"], 7)

    def test_entry_rejects_missing_script(self) -> None:
        result = subprocess.run(
            [sys.executable, "-P", "-m", "greia_platform.python_activity_entry",
             "/nonexistent/main.py"],
            env=_python_env(), capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 2)


class _Manifest:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.launch_path = root / "main.py"


class PythonRuntimeAdapterBytecodeTests(unittest.TestCase):
    def test_command_uses_platform_entry_and_no_untrusted_prefix(self) -> None:
        manifest = _Manifest(Path("/opt/greia-os/activities/demo"))
        adapter = PythonRuntimeAdapter(Path("/usr/bin/python3"))
        with mock.patch.object(sys, "pycache_prefix", None):
            command = adapter.command_for(manifest)  # type: ignore[arg-type]
        self.assertEqual(
            command.command,
            ("/usr/bin/python3", "-P", "-m", "greia_platform.python_activity_entry",
             "/opt/greia-os/activities/demo/main.py"),
        )
        self.assertEqual(
            dict(command.environment),
            {"PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def test_trusted_prefix_is_handed_to_the_activity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            prefix = Path(temporary) / "pycache"
            prefix.mkdir()
            prefix.chmod(0o555)
            try:
                trust = TrustedBytecodePrefix(required_owner_uid=os.getuid())
                adapter = PythonRuntimeAdapter(
                    Path("/usr/bin/python3"), bytecode_prefix=trust
                )
                manifest = _Manifest(Path(temporary))
                with mock.patch.object(sys, "pycache_prefix", str(prefix)):
                    command = adapter.command_for(manifest)  # type: ignore[arg-type]
                env = dict(command.environment)
                self.assertEqual(env["PYTHONPYCACHEPREFIX"], str(prefix))
                self.assertEqual(env["PYTHONDONTWRITEBYTECODE"], "1")
            finally:
                prefix.chmod(0o755)

    def test_untrusted_prefixes_are_refused(self) -> None:
        trust = TrustedBytecodePrefix(required_owner_uid=os.getuid())
        self.assertIsNone(trust.resolve(None))
        self.assertIsNone(trust.resolve("relative/prefix"))
        self.assertIsNone(trust.resolve("/nonexistent/greia/pycache"))
        with tempfile.TemporaryDirectory() as temporary:
            writable = Path(temporary) / "writable"
            writable.mkdir()
            writable.chmod(0o755)
            if os.geteuid() != 0:
                self.assertIsNone(trust.resolve(writable))  # caller may write
            group_writable = Path(temporary) / "group"
            group_writable.mkdir()
            group_writable.chmod(0o575)
            self.assertIsNone(trust.resolve(group_writable))
            group_writable.chmod(0o755)
            sealed = Path(temporary) / "sealed"
            sealed.mkdir()
            sealed.chmod(0o555)
            try:
                self.assertEqual(trust.resolve(sealed), sealed)
                foreign = TrustedBytecodePrefix(required_owner_uid=os.getuid() + 1)
                self.assertIsNone(foreign.resolve(sealed))
            finally:
                sealed.chmod(0o755)


class BytecodePrecompilerTests(unittest.TestCase):
    def test_prefix_mirrors_sources_and_hash_check_rejects_stale_bytecode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source_root = base / "activities" / "demo"
            (source_root / "__pycache__").mkdir(parents=True)
            module = source_root / "demo_mod.py"
            module.write_text("VALUE = 'compiled'\n", encoding="utf-8")
            prefix = base / "prefix"
            report = BytecodePrecompiler(prefix).compile_tree(base / "activities")
            self.assertEqual(report.compiled, 1)
            self.assertEqual(report.failed, [])
            cached = BytecodePrecompiler(prefix).cache_path_for(module)
            self.assertTrue(cached.is_file())
            self.assertIn(str(prefix), str(cached))
            self.assertEqual(list((source_root / "__pycache__").iterdir()), [])
            self.assertFalse(any(source_root.rglob("*.pyc")))
            # checked-hash flag (bit 0 = hash-based, bit 1 = check_source)
            flags = int.from_bytes(cached.read_bytes()[4:8], "little")
            self.assertEqual(flags, 0b11)

            probe = (
                "import demo_mod, sys; print(demo_mod.VALUE); "
                "print(demo_mod.__cached__)"
            )
            env = _python_env(PYTHONPYCACHEPREFIX=str(prefix))
            env["PYTHONPATH"] = str(source_root)
            first = subprocess.run(
                [sys.executable, "-c", probe], env=env,
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout.splitlines()[0], "compiled")
            self.assertTrue(first.stdout.splitlines()[1].startswith(str(prefix)))

            module.write_text("VALUE = 'edited'\n", encoding="utf-8")
            second = subprocess.run(
                [sys.executable, "-c", probe], env=env,
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(second.stdout.splitlines()[0], "edited")
            self.assertFalse(any(source_root.rglob("*.pyc")))

    def test_seal_leaves_prefix_read_only_for_group_and_other(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            (base / "src").mkdir()
            (base / "src" / "m.py").write_text("X = 1\n", encoding="utf-8")
            compiler = BytecodePrecompiler(base / "prefix")
            compiler.compile_tree(base / "src")
            compiler.seal()
            for path in (base / "prefix").rglob("*"):
                mode = stat.S_IMODE(path.stat().st_mode)
                self.assertFalse(mode & (stat.S_IWGRP | stat.S_IWOTH), path)


class ImageBytecodeContractTests(unittest.TestCase):
    def test_compose_precompiles_target_after_hygiene_inside_chroot(self) -> None:
        text = (ROOT / "build/lib/compose.sh").read_text(encoding="utf-8")
        self.assertIn("compose_precompile_bytecode()", text)
        self.assertRegex(
            text,
            r'chroot "\$rootfs" /usr/bin/env -i [^\n]*\\\n\s+/usr/bin/python3 -I -B - '
            r"--greia-root /opt/greia-os",
        )
        self.assertIn('< "$project_root/tools/precompile_greia_bytecode.py"', text)
        body = text[text.index("compose_root() {"):]
        hygiene = body.index('compose_footprint_hygiene "$rootfs"')
        precompile = body.index('compose_precompile_bytecode "$rootfs"')
        self.assertLess(hygiene, precompile)
        self.assertTrue((ROOT / "tools/precompile_greia_bytecode.py").is_file())

    def test_launcher_and_parent_read_the_trusted_prefix(self) -> None:
        units = ROOT / "build/overlay/etc/systemd/system"
        for unit in ("greia-launcher.service", "greia-parent.service"):
            text = (units / unit).read_text(encoding="utf-8")
            self.assertIn(
                f"Environment=PYTHONPYCACHEPREFIX={TRUSTED_BYTECODE_PREFIX}\n", text
            )
            self.assertIn("Environment=PYTHONDONTWRITEBYTECODE=1\n", text)


class ReadyTimeoutPolicyTests(unittest.TestCase):
    def test_shipped_policy_gives_c0_headroom_and_keeps_default(self) -> None:
        policy = ActivityReadyTimeoutPolicy.load(ROOT / "runtime" / "activity-launch.toml")
        self.assertEqual(policy.seconds_for(None), DEFAULT_READY_TIMEOUT_SECONDS)
        self.assertEqual(policy.seconds_for("C3"), DEFAULT_READY_TIMEOUT_SECONDS)
        self.assertEqual(policy.seconds_for("C0"), 30.0)
        self.assertGreater(policy.seconds_for("C1"), DEFAULT_READY_TIMEOUT_SECONDS)

    def test_values_are_bounded_and_broken_policy_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "activity-launch.toml"
            path.write_text(
                "[ready_timeout_seconds]\ndefault = 0.1\nC0 = 9999\n", encoding="utf-8"
            )
            policy = ActivityReadyTimeoutPolicy.load(path)
            self.assertEqual(policy.seconds_for("C0"), MAXIMUM_READY_TIMEOUT_SECONDS)
            self.assertGreaterEqual(policy.seconds_for(None), 5.0)
            path.write_text("not = [toml", encoding="utf-8")
            self.assertEqual(ActivityReadyTimeoutPolicy.load(path).seconds_for("C0"), 30.0)

    def test_class_comes_from_installed_image_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary) / "image-profile.json"
            self.assertIsNone(installed_compatibility_class(profile))
            profile.write_text(
                json.dumps({"platform": {"family": "legacy-x86", "compatibility_class": "C0"}}),
                encoding="utf-8",
            )
            self.assertEqual(installed_compatibility_class(profile), "C0")
            self.assertEqual(
                resolve_ready_timeout_seconds(
                    ROOT / "runtime" / "activity-launch.toml", profile
                ),
                30.0,
            )

    def test_runtime_services_carry_the_bound_with_a_safe_default(self) -> None:
        class _Services:
            activity_ready_timeout_seconds = 30.0

        self.assertEqual(ready_timeout_for(_Services()), 30.0)
        self.assertEqual(ready_timeout_for(object()), DEFAULT_READY_TIMEOUT_SECONDS)


class ForegroundCadenceTests(unittest.TestCase):
    def test_running_activity_is_serviced_at_most_ten_hertz(self) -> None:
        cadence = ActivityForegroundCadence()
        self.assertGreaterEqual(
            cadence.poll_interval(ActivitySessionState.RUNNING, modal_active=False), 0.1
        )
        self.assertLessEqual(
            cadence.poll_interval(ActivitySessionState.STARTING, modal_active=False), 0.05
        )
        self.assertLessEqual(
            cadence.poll_interval(ActivitySessionState.RUNNING, modal_active=True), 0.02
        )
        self.assertFalse(cadence.wait_screen_due(10.1, 10.0))
        self.assertTrue(cadence.wait_screen_due(10.25, 10.0))

    def test_shell_loop_uses_the_cadence_instead_of_a_fixed_sleep(self) -> None:
        text = (SRC / "greia_launcher" / "main.py").read_text(encoding="utf-8")
        self.assertNotIn("time.sleep(0.02)", text)
        self.assertIn("self.FOREGROUND_CADENCE.poll_interval(", text)


class AssetPathResolverTests(unittest.TestCase):
    def test_matches_full_resolution_for_plain_symlink_and_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "assets"
            (root / "visual").mkdir(parents=True)
            (root / "visual" / "a.png").write_bytes(b"x")
            (root / "visual" / "link.png").symlink_to(root / "visual" / "a.png")
            outside = Path(temporary).resolve() / "outside.png"
            outside.write_bytes(b"x")
            (root / "visual" / "escape.png").symlink_to(outside)
            resolver = _AssetPathResolver(root)
            for relative in ("visual/a.png", "visual/link.png", "visual/../visual/a.png"):
                self.assertEqual(resolver.resolve(relative), _safe_path(root, relative))
            for relative in ("visual/escape.png", "../outside.png", "visual/missing.png"):
                with self.assertRaises(AssetCatalogueError):
                    resolver.resolve(relative)


if __name__ == "__main__":
    unittest.main()
