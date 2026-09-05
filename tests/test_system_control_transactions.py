from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from greia_platform.system_controls import (
    SystemControlAction,
    SystemControlApplyResult,
    SystemControlService,
    SystemControlSettings,
    SystemControlSettingsStore,
)
from greia_platform.system_controls_legacy_x import (
    LegacyXMediaKeyListener,
    LegacyXSystemControlBackend,
    run_legacy_x_system_controls,
)


class _TransactionalStore:
    """Minimal desired-state authority exposing only the atomic mutation seam."""

    def __init__(self, current: SystemControlSettings) -> None:
        self.current = current
        self.mutate_calls = 0

    def read(self) -> SystemControlSettings:
        raise AssertionError("relative system-key updates must not use an unlocked read")

    def update(self, **_changes: object) -> SystemControlSettings:
        raise AssertionError("relative system-key updates must not split read and write")

    def mutate(self, mutation):
        self.mutate_calls += 1
        self.current = mutation(self.current)
        return self.current


class _RecordingBackend:
    def __init__(self) -> None:
        self.applied: list[SystemControlSettings] = []

    def apply(self, settings: SystemControlSettings) -> SystemControlApplyResult:
        self.applied.append(settings)
        return SystemControlApplyResult(
            applied=True,
            volume_available=True,
            brightness_available=True,
            brightness_backend="test",
        )


class _QueuedX11:
    def __init__(self, keycodes: list[int]) -> None:
        self.keycodes = list(keycodes)

    def XPending(self, _display: int) -> int:
        return len(self.keycodes)

    def XNextEvent(self, _display: int, event_pointer: object) -> int:
        keycode = self.keycodes.pop(0)
        event = event_pointer._obj  # ctypes.byref(_XEvent) target
        event.type = LegacyXMediaKeyListener._KEY_PRESS
        event.xkey.keycode = keycode
        return 0


class SystemControlTransactionTests(unittest.TestCase):
    def test_relative_key_update_uses_latest_locked_state(self) -> None:
        # Model a Parent write that has already committed immediately before the
        # physical key transaction. The key delta must be derived from that
        # latest state, not from a separately read stale snapshot.
        store = _TransactionalStore(
            SystemControlSettings(
                volume_percent=40,
                muted=True,
                brightness_percent=65,
            )
        )
        backend = _RecordingBackend()
        service = SystemControlService(store, backend)  # type: ignore[arg-type]

        result = service.handle_action(SystemControlAction.VOLUME_UP)

        self.assertTrue(result.applied)
        self.assertEqual(store.mutate_calls, 1)
        self.assertEqual(store.current.volume_percent, 45)
        self.assertFalse(store.current.muted)
        self.assertEqual(store.current.brightness_percent, 65)
        self.assertEqual(backend.applied, [store.current])

    def test_buffered_media_keys_are_drained_before_waiting_on_x_socket(self) -> None:
        listener = LegacyXMediaKeyListener.__new__(LegacyXMediaKeyListener)
        listener._display = 1
        listener._fd = 7
        listener._x11 = _QueuedX11([10, 11])
        listener._actions_by_keycode = {
            10: SystemControlAction.VOLUME_UP,
            11: SystemControlAction.VOLUME_DOWN,
        }

        # Both events are already buffered inside Xlib. Waiting on the kernel
        # socket here can delay/drop the second key until unrelated X traffic.
        with patch(
            "greia_platform.system_controls_legacy_x.select.select",
            side_effect=AssertionError("select must not run while Xlib has events"),
        ):
            first = listener.wait_action(0.25)
            second = listener.wait_action(0.25)

        self.assertIs(first, SystemControlAction.VOLUME_UP)
        self.assertIs(second, SystemControlAction.VOLUME_DOWN)
        self.assertEqual(listener._x11.keycodes, [])


ROOT = Path(__file__).resolve().parents[1]


class _RecordingAlsaRunner:
    """Recording CommandRunner with per-control ALSA results (real command shape)."""

    def __init__(self, *, failing_controls: frozenset[str] = frozenset()) -> None:
        self.commands: list[tuple[str, ...]] = []
        self.failing_controls = failing_controls

    def run(self, command) -> subprocess.CompletedProcess[str]:
        items = tuple(command)
        self.commands.append(items)
        if len(items) >= 4 and items[0] == "amixer":
            control = items[3]
            if control in self.failing_controls:
                return subprocess.CompletedProcess(items, 1, "", "no such control")
            return subprocess.CompletedProcess(items, 0, "", "")
        # Brightness/xrandr probes fail closed in these tests: the ALSA
        # assertions must not depend on host display hardware.
        return subprocess.CompletedProcess(items, 1, "", "unavailable")


def _service_with_store(
    state_dir: Path, runner: _RecordingAlsaRunner
) -> tuple[SystemControlSettingsStore, SystemControlService]:
    store = SystemControlSettingsStore(state_dir)
    backend = LegacyXSystemControlBackend(runner=runner)  # type: ignore[arg-type]
    return store, SystemControlService(store, backend)


class SingleAudioOwnerTests(unittest.TestCase):
    """PLAN Phase 2C.3: exactly one ALSA output owner on the boot path.

    The hardware watcher (SystemControlService over the shared store, applied
    through LegacyXSystemControlBackend) is the single applier. The launcher
    pre-hook owns no mixer state.
    """

    def test_stored_volume_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runner = _RecordingAlsaRunner()
            store, service = _service_with_store(Path(temporary), runner)
            store.update(volume_percent=42, muted=False)

            result = service.apply_current()

            self.assertTrue(result.volume_available)
            alsa = [cmd for cmd in runner.commands if cmd[0] == "amixer"]
            self.assertEqual(
                alsa,
                [("amixer", "-q", "set", "Master", "42%", "unmute")],
            )

    def test_mute_state_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runner = _RecordingAlsaRunner()
            store, service = _service_with_store(Path(temporary), runner)
            store.update(volume_percent=55, muted=True)

            result = service.apply_current()

            self.assertTrue(result.volume_available)
            alsa = [cmd for cmd in runner.commands if cmd[0] == "amixer"]
            self.assertEqual(
                alsa,
                [("amixer", "-q", "set", "Master", "55%", "mute")],
            )

    def test_parent_volume_changes_propagate_through_shared_store(self) -> None:
        # The Parent API writes desired state only: UpdateParentApiApplication
        # .update_system_controls delegates to SystemControlSettingsStore.update
        # (src/greia_parent/update_api.py). The watcher re-applies on token
        # change, so a store update plus apply_current is the real propagation
        # mechanism, not a proxy.
        with tempfile.TemporaryDirectory() as temporary:
            runner = _RecordingAlsaRunner()
            store, service = _service_with_store(Path(temporary), runner)
            store.update(volume_percent=40, muted=False)
            service.apply_current()
            token_before = store.version_token()

            store.update(volume_percent=65, muted=True)

            self.assertNotEqual(store.version_token(), token_before)
            service.apply_current()
            alsa = [cmd for cmd in runner.commands if cmd[0] == "amixer"]
            self.assertEqual(
                alsa[-1],
                ("amixer", "-q", "set", "Master", "65%", "mute"),
            )

    def test_no_duplicate_alsa_owner_on_launch_pre_hook_path(self) -> None:
        pre_hook = (
            ROOT / "build/overlay/usr/local/lib/greia-os/prepare-launcher-vt"
        ).read_text(encoding="utf-8")
        session = (
            ROOT / "build/overlay/usr/local/lib/greia-os/greia-x-session"
        ).read_text(encoding="utf-8")
        unit = (
            ROOT / "build/overlay/etc/systemd/system/greia-launcher.service"
        ).read_text(encoding="utf-8")
        for name, text in (
            ("prepare-launcher-vt", pre_hook),
            ("greia-x-session", session),
            ("greia-launcher.service", unit),
        ):
            with self.subTest(script=name):
                self.assertNotIn("amixer", text)
        # B2/D2 frozen non-audio behavior is preserved byte-for-behavior.
        self.assertIn("--progress 78", pre_hook)
        self.assertIn("x_lock=/tmp/.X0-lock", pre_hook)
        self.assertIn("chvt 1", pre_hook)
        self.assertIn("hardware_session_legacy_x", session)
        # Repo-wide: no output-control `amixer set` outside the single owner.
        # The mic input-gain path (Capture/Mic) is a disjoint domain and stays.
        owner = ROOT / "src/greia_platform/system_controls_legacy_x.py"
        offenders: list[str] = []
        for candidate in list(ROOT.rglob("src/**/*.py")) + list(
            ROOT.rglob("build/**/*")
        ):
            if not candidate.is_file() or candidate == owner:
                continue
            try:
                text = candidate.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if "amixer" not in text:
                continue
            for control in ("Master", "Speaker", "Headphone", "PCM"):
                if control in text:
                    offenders.append(f"{candidate.relative_to(ROOT)}:{control}")
        self.assertEqual(offenders, [])

    def test_boot_chime_starts_after_intro_and_writes_no_mixer_state(self) -> None:
        presentation = (ROOT / "src/greia_launcher/presentation.py").read_text(
            encoding="utf-8"
        )
        chime = (ROOT / "src/greia_launcher/boot_chime.py").read_text(
            encoding="utf-8"
        )
        # Phase 4 order: display is created, then the intro (whose first
        # draw/flip lives in boot_intro.run_intro) runs with the post-frame
        # worker submitted from its first-frame callback, then the chime.
        set_mode_index = presentation.index("display_set_mode_end")
        intro_index = presentation.index("run_intro(")
        chime_index = presentation.index("play_boot_chime()")
        self.assertLess(set_mode_index, intro_index)
        self.assertLess(intro_index, chime_index)
        # The production first flip precedes preparation inside boot_intro.
        boot_intro = (ROOT / "src/greia_launcher/boot_intro.py").read_text(
            encoding="utf-8"
        )
        self.assertLess(
            boot_intro.index("pygame.display.flip()"),
            boot_intro.index("if on_first_frame is not None:"),
        )
        self.assertNotIn("amixer", chime)
        self.assertNotIn("mixer", chime.lower())
        self.assertIn('"aplay"', chime)
        self.assertIn("boot-chime-played", chime)

    def test_missing_alsa_device_fails_soft(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runner = _RecordingAlsaRunner(
                failing_controls=frozenset({"Master", "Speaker", "PCM"})
            )
            store, service = _service_with_store(Path(temporary), runner)
            store.update(volume_percent=70, muted=False)

            result = service.apply_current()

            self.assertFalse(result.volume_available)
            self.assertIn(
                "No supported ALSA output volume control was available.",
                result.messages,
            )
            # The watcher one-shot path (boot reconciliation) never raises for
            # missing audio hardware either.
            backend = LegacyXSystemControlBackend(runner=runner)  # type: ignore[arg-type]
            self.assertEqual(
                run_legacy_x_system_controls(store, backend=backend, once=True), 0
            )


if __name__ == "__main__":
    unittest.main()
