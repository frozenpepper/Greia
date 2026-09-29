from __future__ import annotations

import contextlib
import os
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from greia_installer.wifi import (
    IwdNetworkProfile,
    WifiError,
    WifiNetwork,
    WifiSecurity,
)


def network(
    ssid: str = "Family Wi-Fi",
    security: WifiSecurity = WifiSecurity.PERSONAL,
) -> WifiNetwork:
    return WifiNetwork(
        ssid,
        security,
        -42.0,
        "/net/connman/iwd/station/wlan0/1234",
    )


class InstallerWifiProfileTests(unittest.TestCase):
    def test_personal_profile_escapes_iwd_values_and_hides_secret_from_repr(self) -> None:
        secret = r"eight chars with spaces\and-more"
        profile = IwdNetworkProfile.for_network(network(), secret)
        self.assertIn(r"Passphrase=eight\schars\swith\sspaces\\and-more", profile.content)
        self.assertNotIn(secret, repr(profile))
        self.assertTrue(profile.filename.endswith(".psk"))

    def test_open_profile_has_no_security_secret(self) -> None:
        profile = IwdNetworkProfile.for_network(
            network("Library Guest", WifiSecurity.OPEN)
        )
        self.assertEqual(profile.content, "[Settings]\nAutoConnect=true\n")
        self.assertTrue(profile.filename.endswith(".open"))

    def test_enterprise_is_identified_but_not_faked_as_personal_wifi(self) -> None:
        enterprise = network("School", WifiSecurity.ENTERPRISE)
        self.assertFalse(enterprise.installer_supported)
        with self.assertRaisesRegex(WifiError, "enterprise credentials"):
            IwdNetworkProfile.for_network(enterprise, "not-a-real-eap-login")

    def test_passphrase_bounds_are_enforced(self) -> None:
        with self.assertRaisesRegex(WifiError, "8 to 63"):
            IwdNetworkProfile.for_network(network(), "short")
        profile = IwdNetworkProfile.for_network(network(), "a" * 63)
        self.assertIn("Passphrase=", profile.content)
        with self.assertRaisesRegex(WifiError, "8 to 63"):
            IwdNetworkProfile.for_network(network(), "a" * 64)

    def test_unusual_ssid_uses_iwd_hex_filename_not_path_components(self) -> None:
        profile = IwdNetworkProfile.for_network(
            network("Family/Home🔥"),
            "password123",
        )
        self.assertTrue(profile.filename.startswith("="))
        self.assertTrue(profile.filename.endswith(".psk"))
        self.assertNotIn("/", profile.filename)
        self.assertEqual(Path(profile.filename).name, profile.filename)

    def test_target_profile_is_atomic_and_private(self) -> None:
        profile = IwdNetworkProfile.for_network(network(), "password123")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = profile.write_to(root)
            self.assertEqual(destination.parent, root / "var/lib/iwd")
            self.assertEqual(destination.read_text(encoding="utf-8"), profile.content)
            self.assertEqual(os.stat(destination).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(destination.parent).st_mode & 0o777, 0o700)
            self.assertEqual(
                list(destination.parent.glob(".*.greia-installer.tmp")),
                [],
            )

    def test_ssid_is_limited_to_ieee_80211_length(self) -> None:
        with self.assertRaisesRegex(ValueError, "1 to 32"):
            network("x" * 33)


if __name__ == "__main__":
    unittest.main()


class InstallerWifiConnectOwnershipTests(unittest.TestCase):
    """Connecting must never write into iwd's own private state directory.

    The first implementation of ``connect`` wrote the iwd profile straight
    into ``/var/lib/iwd`` and then asked iwd to pick it up. That directory is
    iwd's, owned root with mode 0700, and the installer runs unprivileged as
    ``User=nobody``, so every attempt to join a network died with
    ``[Errno 1] Operation not permitted: '/var/lib/iwd'``. The passphrase is
    now supplied over iwd's own agent API and iwd persists the profile itself,
    so nothing in the installer needs that write.
    """

    def _backend(self, state_dir: Path):
        from greia_platform.wifi import IwdWifiBackend

        return IwdWifiBackend(state_dir=state_dir)

    def test_connect_does_not_create_or_chmod_the_iwd_state_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = Path(temporary) / "iwd"
            state_dir.mkdir(mode=0o700)
            backend = self._backend(state_dir)
            observed: list[str] = []
            original = os.stat

            def watch(path, *args, **kwargs):
                observed.append(str(path))
                return original(path, *args, **kwargs)

            with (
                unittest.mock.patch(
                    "greia_platform.wifi._iwd_passphrase_agent",
                    lambda *a, **k: contextlib.nullcontext(),
                ),
                unittest.mock.patch.object(
                    backend, "_connect_network", lambda network: None
                ),
                unittest.mock.patch(
                    "greia_platform.wifi.os.stat", side_effect=watch
                ),
                unittest.mock.patch("greia_platform.wifi.os.chmod") as chmod,
                unittest.mock.patch(
                    "greia_platform.wifi.os.makedirs"
                ) as makedirs,
            ):
                connection = backend.connect(network(), "a-good-passphrase")

            self.assertEqual(connection.network.ssid, "Family Wi-Fi")
            self.assertEqual(connection.profile.filename, "Family Wi-Fi.psk")
            for call in chmod.call_args_list:
                self.assertNotEqual(
                    str(call.args[0]),
                    str(state_dir),
                    "connect must not chmod a directory it does not own",
                )
            for call in makedirs.call_args_list:
                self.assertNotEqual(
                    str(call.args[0]),
                    str(state_dir),
                    "connect must not create iwd's state directory",
                )
            self.assertEqual(list(state_dir.iterdir()), [])

    def test_open_network_connect_needs_no_passphrase_agent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = Path(temporary) / "iwd"
            state_dir.mkdir(mode=0o700)
            backend = self._backend(state_dir)
            opened = network(security=WifiSecurity.OPEN)
            agent_used = False

            def agent(*args, **kwargs):
                nonlocal agent_used
                agent_used = True
                return contextlib.nullcontext()

            with (
                unittest.mock.patch(
                    "greia_platform.wifi._iwd_passphrase_agent", agent
                ),
                unittest.mock.patch.object(
                    backend, "_connect_network", lambda network: None
                ),
            ):
                backend.connect(opened)
            self.assertFalse(
                agent_used, "an open network needs no passphrase to be supplied"
            )
