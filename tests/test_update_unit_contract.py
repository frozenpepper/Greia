"""A/B update unit contract: release identity, local socket and full OS staging.

Structured assertions (configparser + targeted reads), never a full-file
snapshot: the updater identity resolves from the image-owned
``release-identity.json`` with the installed layout record and
``image-profile.json`` as fallbacks for unstated compatibility facts
(``GREIA_SYSTEM_*`` environment stays a test-only fallback), and the shipped
unit carries exactly the writable paths and capabilities the P3.2
implementation requires (exactly ``CAP_SYS_ADMIN`` plus ``CAP_SYS_CHROOT``
for the shared finalize path's ``chroot`` hardware-support install leg).
"""

import configparser
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "build/overlay/etc/systemd/system/greia-system-update.service"
SOCKET_PATH = ROOT / "build/overlay/etc/systemd/system/greia-system-update.socket"
PARENT_PATH = ROOT / "build/overlay/etc/systemd/system/greia-parent.service"
LAUNCHER_PATH = ROOT / "build/overlay/etc/systemd/system/greia-launcher.service"

UUID_A = "11111111-1111-1111-1111-111111111111"
UUID_B = "22222222-2222-2222-2222-222222222222"
UUID_P = "33333333-3333-3333-3333-333333333333"

_FAMILY = "legacy-x86"
_ARCH = "i386"
_PROFILE = "legacy-x86-i686"

_IDENTITY_VARS = (
    "GREIA_SYSTEM_VERSION",
    "GREIA_SYSTEM_PLATFORM_FAMILY",
    "GREIA_SYSTEM_ARCHITECTURE",
    "GREIA_SYSTEM_PROFILE",
)
_PATH_VARS = (
    "GREIA_RELEASE_IDENTITY_PATH",
    "GREIA_INSTALLED_LAYOUT_RECORD",
    "GREIA_IMAGE_PROFILE_PATH",
)


def _canonical(payload: dict) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _layout_dict(**overrides: object) -> dict:
    base: dict = {
        "accepted_release_id": "greia-r8",
        "accepted_slot": "A",
        "boot_backend": "grub-ab-v1",
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": _PROFILE,
        "install_target_sha256": "ab" * 32,
        "installed_at_unix": 1757000000,
        "layout_id": "legacy-bios-ab-v1",
        "persist": {"filesystem_uuid": UUID_P, "partuuid": UUID_P},
        "platform_family": _FAMILY,
        "schema_version": 1,
        "slot_bytes": 1073741824,
        "system_a": {"filesystem_uuid": UUID_A, "partuuid": UUID_A},
        "system_b": {"filesystem_uuid": UUID_B, "partuuid": UUID_B},
    }
    base.update(overrides)
    return base


def _identity_dict(**overrides: object) -> dict:
    base: dict = {
        "boot_backend": "grub-ab-v1",
        "layout_id": "legacy-bios-ab-v1",
        "release_id": "greia-r9",
        "role": "system-b",
        "slot": "B",
    }
    base.update(overrides)
    return base


def _profile_doc(**overrides: object) -> dict:
    base: dict = {
        "platform": {"family": _FAMILY},
        "profile": {"id": _PROFILE},
        "base": {"architecture": _ARCH},
    }
    base.update(overrides)
    return base


def _parse_unit(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    parser.optionxform = str  # type: ignore[assignment]
    parser.read(path, encoding="utf-8")
    return parser


class _IsolatedEnv:
    """Pin every identity/path variable so host image state cannot leak in."""

    def __init__(self, root: Path, env: dict | None = None) -> None:
        self._root = root
        self._patch = mock.patch.dict(
            os.environ,
            {
                "GREIA_RELEASE_IDENTITY_PATH": str(root / "release-identity.json"),
                "GREIA_INSTALLED_LAYOUT_RECORD": str(root / "installed-layout.json"),
                "GREIA_IMAGE_PROFILE_PATH": str(root / "image-profile.json"),
                **{var: "" for var in _IDENTITY_VARS},
                **(env or {}),
            },
            clear=False,
        )

    def __enter__(self) -> Path:
        self._patch.start()
        return self._root

    def __exit__(self, *exc: object) -> None:
        self._patch.stop()


def _directive_values(path: Path, name: str) -> set[str]:
    """Collect every value of a (possibly repeated) unit directive, parsed."""
    values: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith(name + "="):
            values.update(stripped.split("=", 1)[1].split())
    return values


class ReleaseIdentityAuthorityTests(unittest.TestCase):
    def test_files_resolve_identity_without_env(self) -> None:
        from greia_platform.system_updates import resolve_installed_system_identity

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release-identity.json").write_bytes(
                _canonical(_identity_dict())
            )
            (root / "installed-layout.json").write_bytes(
                _canonical(_layout_dict())
            )
            (root / "image-profile.json").write_bytes(
                json.dumps(_profile_doc()).encode() + b"\n"
            )
            with _IsolatedEnv(root):
                identity = resolve_installed_system_identity()
        self.assertEqual(identity.platform_family, _FAMILY)
        self.assertEqual(identity.profile, _PROFILE)
        self.assertEqual(identity.architecture, _ARCH)
        self.assertEqual(identity.version, "unknown")
        self.assertTrue(identity.compatibility_known)

    def test_installed_files_beat_environment(self) -> None:
        from greia_platform.system_updates import resolve_installed_system_identity

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release-identity.json").write_bytes(
                _canonical(_identity_dict())
            )
            (root / "installed-layout.json").write_bytes(
                _canonical(_layout_dict())
            )
            (root / "image-profile.json").write_bytes(
                json.dumps(_profile_doc()).encode() + b"\n"
            )
            with _IsolatedEnv(
                root,
                {
                    "GREIA_SYSTEM_VERSION": "wrong-version",
                    "GREIA_SYSTEM_PLATFORM_FAMILY": "wrong-family",
                    "GREIA_SYSTEM_ARCHITECTURE": "wrong-arch",
                    "GREIA_SYSTEM_PROFILE": "wrong-profile",
                },
            ):
                identity = resolve_installed_system_identity()
        self.assertEqual(
            (identity.platform_family, identity.architecture, identity.profile),
            (_FAMILY, _ARCH, _PROFILE),
        )

    def test_release_identity_states_own_compat_facts(self) -> None:
        from greia_platform.system_updates import resolve_installed_system_identity

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release-identity.json").write_bytes(
                _canonical(
                    _identity_dict(
                        platform_family="other-family",
                        architecture="other-arch",
                        profile="other-profile",
                        version="9.9.9",
                    )
                )
            )
            (root / "installed-layout.json").write_bytes(
                _canonical(_layout_dict())
            )
            (root / "image-profile.json").write_bytes(
                json.dumps(_profile_doc()).encode() + b"\n"
            )
            with _IsolatedEnv(root):
                identity = resolve_installed_system_identity()
        self.assertEqual(
            (
                identity.platform_family,
                identity.architecture,
                identity.profile,
                identity.version,
            ),
            ("other-family", "other-arch", "other-profile", "9.9.9"),
        )

    def test_absent_files_keep_test_env_fallback(self) -> None:
        from greia_platform.system_updates import resolve_installed_system_identity

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with _IsolatedEnv(
                root,
                {
                    "GREIA_SYSTEM_VERSION": "0.16.0",
                    "GREIA_SYSTEM_PLATFORM_FAMILY": _FAMILY,
                    "GREIA_SYSTEM_ARCHITECTURE": _ARCH,
                    "GREIA_SYSTEM_PROFILE": _PROFILE,
                },
            ):
                identity = resolve_installed_system_identity()
        self.assertEqual(
            (
                identity.version,
                identity.platform_family,
                identity.architecture,
                identity.profile,
            ),
            ("0.16.0", _FAMILY, _ARCH, _PROFILE),
        )
        self.assertTrue(identity.compatibility_known)

    def test_absent_everything_is_unknown_and_refuses(self) -> None:
        from greia_platform.system_updates import (
            UpdateCompatibilityError,
            resolve_installed_system_identity,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with _IsolatedEnv(root):
                identity = resolve_installed_system_identity()
        self.assertEqual(
            (
                identity.version,
                identity.platform_family,
                identity.architecture,
                identity.profile,
            ),
            ("unknown", "unknown", "unknown", "unknown"),
        )
        self.assertFalse(identity.compatibility_known)
        manifest = mock.Mock()
        manifest.platform_family = _FAMILY
        manifest.architecture = _ARCH
        manifest.profile = _PROFILE
        with self.assertRaises(UpdateCompatibilityError):
            identity.assert_compatible(manifest)

    def test_corrupt_identity_fails_closed(self) -> None:
        from greia_platform.system_updates import (
            UpdateLayoutError,
            load_installed_release_identity,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with _IsolatedEnv(root):
                for name, payload in (
                    ("garbage.json", b"not json"),
                    ("wrong-keys.json", _canonical({"slot": "B"})),
                    ("bad-slot.json", _canonical(_identity_dict(slot="C"))),
                    (
                        "non-canonical.json",
                        json.dumps(_identity_dict(), indent=2).encode() + b"\n",
                    ),
                ):
                    target = root / name
                    target.write_bytes(payload)
                    with mock.patch.dict(
                        os.environ,
                        {"GREIA_RELEASE_IDENTITY_PATH": str(target)},
                        clear=False,
                    ):
                        with self.assertRaises(UpdateLayoutError, msg=name):
                            load_installed_release_identity()
                link = root / "link.json"
                (root / "real.json").write_bytes(_canonical(_identity_dict()))
                try:
                    link.symlink_to(root / "real.json")
                except OSError:
                    self.skipTest("symlinks unavailable")
                with mock.patch.dict(
                    os.environ,
                    {"GREIA_RELEASE_IDENTITY_PATH": str(link)},
                    clear=False,
                ):
                    with self.assertRaises(UpdateLayoutError):
                        load_installed_release_identity()

    def test_corrupt_layout_does_not_break_identity_composition(self) -> None:
        from greia_platform.system_updates import (
            UpdateLayoutError,
            load_installed_layout_record,
            resolve_installed_system_identity,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release-identity.json").write_bytes(
                _canonical(_identity_dict())
            )
            (root / "installed-layout.json").write_bytes(b"corrupt")
            (root / "image-profile.json").write_bytes(
                json.dumps(_profile_doc()).encode() + b"\n"
            )
            with _IsolatedEnv(root):
                with self.assertRaises(UpdateLayoutError):
                    load_installed_layout_record()
                identity = resolve_installed_system_identity()
        self.assertEqual(
            (identity.platform_family, identity.architecture, identity.profile),
            (_FAMILY, _ARCH, _PROFILE),
        )

    def test_shipped_composition_reads_installed_authority(self) -> None:
        from greia_platform.system_updates import build_live_update_service

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir = root / "state"
            (root / "release-identity.json").write_bytes(
                _canonical(_identity_dict())
            )
            (root / "installed-layout.json").write_bytes(
                _canonical(_layout_dict())
            )
            (root / "image-profile.json").write_bytes(
                json.dumps(_profile_doc()).encode() + b"\n"
            )
            with _IsolatedEnv(
                root,
                {
                    "GREIA_SYSTEM_PLATFORM_FAMILY": "wrong-family",
                    "GREIA_SYSTEM_ARCHITECTURE": "wrong-arch",
                    "GREIA_SYSTEM_PROFILE": "wrong-profile",
                },
            ):
                authority = build_live_update_service(
                    state_dir=state_dir,
                    layout_record_path=root / "installed-layout.json",
                )
        self.assertEqual(
            (
                authority.identity.platform_family,
                authority.identity.architecture,
                authority.identity.profile,
            ),
            (_FAMILY, _ARCH, _PROFILE),
        )


class UpdateUnitProductTests(unittest.TestCase):
    def test_offline_slot_worker_can_run_real_dpkg_package_scripts(self) -> None:
        parser = _parse_unit(SERVICE_PATH)
        self.assertEqual(parser.get("Service", "User"), "root")
        self.assertEqual(
            parser.get("Service", "ExecStart"),
            "/usr/bin/python3 -m greia_platform.update_privileged --socket-activated",
        )
        blocked = (
            "CapabilityBoundingSet", "AmbientCapabilities", "NoNewPrivileges",
            "ProtectSystem", "ReadWritePaths", "PrivateTmp", "ProtectHome",
            "RestrictSUIDSGID", "RestrictAddressFamilies", "SystemCallFilter",
            "TasksMax", "SystemCallArchitectures",
        )
        raw = SERVICE_PATH.read_text(encoding="utf-8")
        active = [
            line.split("=", 1)[0].strip()
            for line in raw.splitlines()
            if line and not line.lstrip().startswith(("#", ";", "["))
            and "=" in line
        ]
        for directive in blocked:
            self.assertNotIn(directive, active, directive)

    def test_shared_package_install_is_real_argv_apt_not_shell(self) -> None:
        source = (
            ROOT / "src/greia_installer/hardware_support_install.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"chroot"', source)
        self.assertIn('"apt-get"', source)
        self.assertNotIn("shell=True", source)
        seam = (ROOT / "src/greia_installer/device_seams.py").read_text(encoding="utf-8")
        self.assertIn("shell=False", seam)

    def test_no_key_trust_root_in_shipped_unit(self) -> None:
        # v3 carries no key material: the shipped unit must not grant any
        # key trust root (read-only or otherwise).
        bound = _directive_values(SERVICE_PATH, "BindReadOnlyPaths")
        self.assertNotIn("/etc/greia-os/system-update-keys", bound)
        raw = SERVICE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("system-update-keys", raw)

    def test_no_env_identity_in_shipped_units(self) -> None:
        for path in (SERVICE_PATH, SOCKET_PATH):
            raw = path.read_text(encoding="utf-8")
            for var in _IDENTITY_VARS:
                self.assertNotIn(var, raw)

    def test_no_launcher_parent_gains(self) -> None:
        for path in (PARENT_PATH, LAUNCHER_PATH):
            raw = path.read_text(encoding="utf-8")
            self.assertNotIn("CAP_SYS_ADMIN", raw)
        parent_paths = _directive_values(PARENT_PATH, "ReadWritePaths")
        self.assertNotIn("/etc/greia-os", parent_paths)
        self.assertNotIn("/boot/grub", parent_paths)
        launcher_raw = LAUNCHER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("ReadWritePaths=/etc/greia-os", launcher_raw)
        self.assertNotIn("ReadWritePaths=/boot/grub", launcher_raw)

    def test_mount_root_default_lives_under_granted_runtime(self) -> None:
        from greia_platform.system_updates import UPDATE_MOUNT_ROOT_DEFAULT

        self.assertEqual(UPDATE_MOUNT_ROOT_DEFAULT, "/run/greia-os/slots")

    def test_socket_essentials_preserved(self) -> None:
        parser = _parse_unit(SOCKET_PATH)
        self.assertEqual(
            parser.get("Socket", "ListenStream").strip(),
            "/run/greia-os/system-update.sock",
        )
        self.assertEqual(parser.get("Socket", "Accept").strip(), "no")
        self.assertEqual(parser.get("Socket", "SocketMode").strip(), "0660")
        self.assertEqual(parser.get("Socket", "SocketGroup").strip(), "greiapanel")


if __name__ == "__main__":
    unittest.main()
