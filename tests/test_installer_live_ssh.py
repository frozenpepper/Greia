"""Live installer SSH: actual semantic routing and bounded service control."""
from __future__ import annotations

import os
import subprocess
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from greia_installer.install_transaction import InstallTransactionError
from greia_installer.live_ssh import LiveSshError, LiveSshService, LiveSshToggle
from greia_platform.privileged_channel import PeerCredential, encode_request
from test_install_transaction_service import FOREIGN_PEER, READY, ServiceHarness, make_disk


class LiveServiceTests(unittest.TestCase):
    def test_start_stop_and_observed_state(self):
        commands = []
        active = False
        def run(argv, **kwargs):
            nonlocal active
            commands.append(argv)
            self.assertFalse(kwargs["shell"])
            if argv[1] == "start":
                active = True
            elif argv[1] == "stop":
                active = False
            return subprocess.CompletedProcess(argv, 0 if argv[1] != "is-active" or active else 3)
        service = LiveSshService(run)
        self.assertTrue(service.set_enabled(True))
        self.assertFalse(service.set_enabled(False))
        self.assertEqual(commands, [["systemctl", "start", "ssh.service"],
            ["systemctl", "is-active", "--quiet", "ssh.service"],
            ["systemctl", "stop", "ssh.service"],
            ["systemctl", "is-active", "--quiet", "ssh.service"]])

    def test_failure_and_mismatched_state_are_not_reported_as_success(self):
        failed = LiveSshService(lambda argv, **kw: subprocess.CompletedProcess(argv, 1))
        with self.assertRaises(LiveSshError):
            failed.set_enabled(True)
        mismatch = LiveSshService(lambda argv, **kw: subprocess.CompletedProcess(
            argv, 3 if argv[1] == "is-active" else 0))
        with self.assertRaises(LiveSshError):
            mismatch.set_enabled(True)

    def test_socket_authorizes_and_carries_only_boolean(self):
        harness = ServiceHarness([make_disk()])
        with patch("greia_installer.transaction_service.LiveSshService") as cls:
            cls.return_value.set_enabled.return_value = True
            cls.return_value.status.return_value = True
            client = harness.client()
            self.assertTrue(client.set_live_ssh(True))
            self.assertTrue(client.live_ssh_status())
            cls.return_value.set_enabled.assert_called_once_with(True)
            for params in ({"enabled": "true"}, {"enabled": True, "extra": "bad"}, {}):
                with self.subTest(params=params), self.assertRaises(InstallTransactionError):
                    harness.service.handle_request(encode_request("LIVE_SSH_SET", params),
                        peer=PeerCredential(uid=65534), boot_state=READY)
            with self.assertRaises(InstallTransactionError):
                harness.service.handle_request(encode_request("LIVE_SSH_SET", {"enabled": True}),
                                               peer=FOREIGN_PEER, boot_state=READY)
            cls.return_value.set_enabled.assert_called_once()

    def test_ui_worker_never_claims_requested_state_on_failure(self):
        class Client:
            def set_live_ssh(self, enabled):
                raise RuntimeError("failed")
            def live_ssh_status(self):
                return False
        ui = LiveSshToggle(Client())
        ui.toggle()
        deadline = time.monotonic() + 2
        while ui.snapshot.busy and time.monotonic() < deadline:
            ui.drain()
            time.sleep(0.005)
        self.assertFalse(ui.snapshot.busy)
        self.assertFalse(ui.snapshot.enabled)
        self.assertTrue(ui.snapshot.error)

    def test_installer_composition_only_and_disabled_until_toggle(self):
        root = Path(__file__).resolve().parents[1]
        packages = (root / "build/package-sets/installer-base.txt").read_text().splitlines()
        self.assertIn("openssh-server", packages)
        self.assertIn("avahi-daemon", packages)
        self.assertIn("sudo", packages)
        builder = (root / "build/build-installer-image.sh").read_text()
        self.assertIn('compose_provision_developer_ssh_live "$LIVE_ROOT"', builder)
        self.assertIn('systemctl --root="$LIVE_ROOT" disable ssh.service', builder)
        self.assertIn('systemctl --root="$LIVE_ROOT" mask ssh.socket', builder)

class LiveInstallerUiTests(unittest.TestCase):
    def test_demo_keyboard_and_pointer_toggle_ssh_without_password_input(self):
        import sys
        import pygame
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / "tools"))
        import installer_screenshots as preview
        from greia_installer.main import InstallerPage
        app = preview._make_app("it")
        app.state.page = InstallerPage.WIFI
        app.wifi = preview._wifi(preview.WifiSetupPhase.READY, passphrase="secret")
        pygame.init()
        pygame.display.set_mode((800, 480))
        try:
            screen = pygame.Surface((800, 480)).convert()
            app._draw(screen, pygame)
            app._handle_mouse_up(app._buttons["wifi-ssh"].center)
            self.assertTrue(app._live_ssh.snapshot.enabled)
            app._handle_text_input("x")
            self.assertEqual(app.wifi.snapshot.passphrase, "secret")
            app._handle_key(pygame.K_RETURN, pygame)
            self.assertFalse(app._live_ssh.snapshot.enabled)
            app._handle_key(pygame.K_TAB, pygame)
            app._handle_key(pygame.K_TAB, pygame)
            app._handle_key(pygame.K_SPACE, pygame)
            self.assertTrue(app._live_ssh.snapshot.enabled)
        finally:
            pygame.quit()

    def test_running_installer_demo_accepts_pointer_toggle(self):
        import sys
        import pygame
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / "tools"))
        import installer_screenshots as preview
        app = preview._make_app("it")
        preview._wifi_state(preview._wifi(preview.WifiSetupPhase.READY, passphrase="secret"))(app)
        frames = []
        draw = app._draw
        def observe(screen, pygame_module):
            draw(screen, pygame_module)
            frames.append(app._live_ssh.snapshot.enabled)
        count = 0
        def events():
            nonlocal count
            count += 1
            if count == 2:
                return [pygame.event.Event(pygame.MOUSEBUTTONUP,
                    {"button": 1, "pos": app._buttons["wifi-ssh"].center})]
            if count == 3:
                return [pygame.event.Event(pygame.QUIT)]
            return []
        with patch.object(app, "_draw", side_effect=observe), patch.object(pygame.event, "get", side_effect=events):
            self.assertEqual(app.run(), 0)
        self.assertIn(False, frames)
        self.assertIn(True, frames)
