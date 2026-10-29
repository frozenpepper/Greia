"""Greia installer transaction: release facts, startup and real Debian installs.

The transaction socket validates the request and disk identity. The one-shot
root worker must not carry systemd sandbox restrictions that break dpkg,
chroot, initramfs or bootloader installation on the reference Acer.
"""

from __future__ import annotations

import json
import os
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from greia_installer.composition import (
    AB_INSTALL_CONFIG_PATH_ENV,
    AB_INSTALL_ENV_BUNDLE,
    AB_INSTALL_ENV_DEVELOPER,
    AB_INSTALL_ENV_FILE_DEFAULT,
    AB_INSTALL_ENV_PASSWORD_HASH,
    AB_INSTALL_ENV_SUPPORT_BOUND,
    AbInstallCompositionError,
    ab_executor_facts_from_environment,
    read_ab_env_file,
)
from greia_installer.transaction_service import (
    InstallTransactionService,
    ServiceState,
    TransactionServiceError,
    build_live_service,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
UNIT_PATH = (
    REPO_ROOT
    / "build"
    / "installer-overlay"
    / "etc"
    / "systemd"
    / "system"
    / "greia-install-transaction.service"
)
ENTRYPOINT_PATH = (
    REPO_ROOT / "src" / "greia_installer" / "transaction_service_entrypoint.py"
)
SERVICE_IMPL_PATH = (
    REPO_ROOT / "src" / "greia_installer" / "transaction_service.py"
)
TMPFILES_PATH = (
    REPO_ROOT / "build" / "installer-overlay" / "etc" / "tmpfiles.d" / "greia-installer.conf"
)
AB_PRODUCT_PROFILE = REPO_ROOT / "build" / "profiles" / "acer-aspire-one-i386-ab.toml"
LEGACY_PROFILE = REPO_ROOT / "build" / "profiles" / "acer-aspire-one-i386.toml"

_AB_ENV_NAMES = (
    AB_INSTALL_ENV_BUNDLE,
    AB_INSTALL_ENV_PASSWORD_HASH,
    AB_INSTALL_ENV_DEVELOPER,
    AB_INSTALL_ENV_SUPPORT_BOUND,
)
_ALL_MANAGED_NAMES = _AB_ENV_NAMES + (
    AB_INSTALL_CONFIG_PATH_ENV,
    "GREIA_OS_ROOT",
    "GREIA_INSTALL_PAYLOAD",
    "GREIA_INSTALL_PAYLOAD_DIGEST",
    "GREIA_TARGET_IMAGE_PROFILE",
    "GREIA_HARDWARE_SUPPORT_POOL",
)

GIB = 1024 * 1024 * 1024
MIB = 1024 * 1024

_AB_PROFILE_ID = "test-unit-contract-ab-v1"
_AB_FAMILY = "legacy-x86"
_AB_ARCH = "i386"
_AB_LAYOUT = "legacy-bios-ab-v1"
_AB_BACKEND = "grub-ab-v1"

_AB_PASSWORD_HASH = "grub.pbkdf2.sha512.10000." + "U" * 64

EXPECTED_READ_WRITE_PATHS = frozenset(
    {
        "/run/greia-os",
        "/run/greia-install/persist",
        "/run/greia-install/boot-control",
        "/run/greia-slots",
    }
)


# ---------------------------------------------------------------------------
# Structured unit parsing (no full-file snapshot)
# ---------------------------------------------------------------------------


def parse_unit(path: Path) -> dict[str, object]:
    """Parse the shipped unit into typed facts (directives, not text)."""
    section: str | None = None
    facts: dict[str, object] = {
        "environment": {},
        "environment_files": [],
        "read_write_paths": set(),
        "exec_start": None,
    }
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if "=" not in line or section != "Service":
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key == "Environment":
            name, _, _ = value.partition("=")
            facts["environment"][name.strip()] = value  # type: ignore[index]
        elif key == "EnvironmentFile":
            facts["environment_files"].append(value)  # type: ignore[attr-defined]
        elif key == "ReadWritePaths":
            facts["read_write_paths"].update(value.split())  # type: ignore[attr-defined]
        elif key in (
            "CapabilityBoundingSet",
            "AmbientCapabilities",
            "ProtectSystem",
            "NoNewPrivileges",
            "RestrictAddressFamilies",
            "StandardInput",
            "StandardOutput",
            "User",
            "ExecStart",
        ):
            facts[key] = value
    facts["exec_start"] = facts.get("ExecStart")
    return facts


def parse_tmpfiles_dirs(path: Path) -> set[str]:
    """Return the absolute ``d``-entry paths a tmpfiles fragment creates."""
    created: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "d" and parts[1].startswith("/"):
            created.add(parts[1])
    return created


# ---------------------------------------------------------------------------
# Disposable fixtures
# ---------------------------------------------------------------------------


def _write_profile(path: Path, *, profile_id: str, layout: str, backend: str) -> Path:
    path.write_text(
        json.dumps(
            {
                "profile": {"id": profile_id},
                "platform": {"family": _AB_FAMILY},
                "base": {"architecture": _AB_ARCH},
                "storage": {
                    "layout_adapter": layout,
                    "system_slot_bytes": 1 * GIB,
                    "persistent_minimum_bytes": 256 * MIB,
                },
                "installer": {"target_policy": "pc-internal-v1"},
                "updates": {"boot_backend": backend},
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_ab_env_file(
    path: Path, *, bundle: Path, support_bound: int = MIB
) -> Path:
    path.write_text(
        "# disposable A/B release facts for the unit-contract suite\n"
        f"{AB_INSTALL_ENV_BUNDLE}={bundle}\n"
        f"{AB_INSTALL_ENV_PASSWORD_HASH}={_AB_PASSWORD_HASH}\n"
        f"{AB_INSTALL_ENV_DEVELOPER}=0\n"
        f"{AB_INSTALL_ENV_SUPPORT_BOUND}={support_bound}\n",
        encoding="utf-8",
    )
    return path


def _make_ab_tree(prefix: str = "installer-unit-contract-") -> tuple[str, dict[str, Path]]:
    directory = tempfile.mkdtemp(prefix=prefix)
    root = Path(directory).resolve()
    os_root = root / "os-root"
    os_root.mkdir()
    pool = root / "support-pool"
    pool.mkdir()
    payload = root / "payload.squashfs"
    payload.write_bytes(b"test-payload")
    digest = root / "expected-payload.sha256"
    digest.write_bytes(b"0" * 64)
    profile = root / "target-image-profile.json"
    _write_profile(
        profile, profile_id=_AB_PROFILE_ID, layout=_AB_LAYOUT, backend=_AB_BACKEND
    )
    bundle = root / "ab-release.greiaupdate"
    bundle.write_bytes(b"test-release-bundle")
    env_file = root / "installer-ab.env"
    _write_ab_env_file(env_file, bundle=bundle)
    return directory, {
        "root": root,
        "os_root": os_root,
        "pool": pool,
        "payload": payload,
        "digest": digest,
        "profile": profile,
        "bundle": bundle,
        "env_file": env_file,
    }


def _snapshot(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*")}


@contextmanager
def _hermetic_env(
    *,
    fix: dict[str, Path] | None = None,
    config_path: Path | str | None = "default",
    ab_overrides: dict[str, str] | None = None,
):
    """Hermetic GREIA_* environment: shipped five names + one env-file source.

    ``config_path="default"`` points ``GREIA_AB_CONFIG`` at the fixture env
    file; pass an explicit path (possibly nonexistent) to prove fail-closed
    handling independent of the host's ``/etc/greia-os``.
    """
    saved = {name: os.environ.get(name) for name in _ALL_MANAGED_NAMES}
    try:
        for name in _AB_ENV_NAMES:
            os.environ.pop(name, None)
        if fix is not None:
            os.environ["GREIA_OS_ROOT"] = str(fix["os_root"])
            os.environ["GREIA_INSTALL_PAYLOAD"] = str(fix["payload"])
            os.environ["GREIA_INSTALL_PAYLOAD_DIGEST"] = str(fix["digest"])
            os.environ["GREIA_TARGET_IMAGE_PROFILE"] = str(fix["profile"])
            os.environ["GREIA_HARDWARE_SUPPORT_POOL"] = str(fix["pool"])
            if config_path == "default":
                os.environ[AB_INSTALL_CONFIG_PATH_ENV] = str(fix["env_file"])
            elif config_path is not None:
                os.environ[AB_INSTALL_CONFIG_PATH_ENV] = str(config_path)
            else:
                os.environ.pop(AB_INSTALL_CONFIG_PATH_ENV, None)
        for name, value in (ab_overrides or {}).items():
            os.environ[name] = value
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _ab_state(fix: dict[str, Path]) -> ServiceState:
    return ServiceState.from_target_profile(
        fix["profile"],
        payload=fix["payload"],
        payload_digest=fix["digest"],
        project_root=fix["os_root"],
        hardware_support_pool=fix["pool"],
    )


# ---------------------------------------------------------------------------
# Immutable-facts source
# ---------------------------------------------------------------------------


class ImmutableFactsSourceTests(unittest.TestCase):
    def test_unit_loads_image_owned_env_file_and_hardcodes_no_ab_names(self) -> None:
        facts = parse_unit(UNIT_PATH)
        self.assertEqual(
            facts["environment_files"],
            ["-" + AB_INSTALL_ENV_FILE_DEFAULT],
            "unit must load exactly the image-owned A/B facts file (optional "
            "so legacy recovery media without A/B facts still boots)",
        )
        for name in _AB_ENV_NAMES:
            self.assertNotIn(
                name,
                facts["environment"],  # type: ignore[operator]
                f"release image must not depend on hardcoded {name}; "
                "it comes from installer-ab.env",
            )

    def test_central_parser_resolves_file_facts(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        with _hermetic_env(fix=fix):
            state = _ab_state(fix)
            resolved = ab_executor_facts_from_environment(state=state)
        self.assertEqual(resolved.bundle_path, fix["bundle"])
        self.assertEqual(resolved.password_hash, _AB_PASSWORD_HASH)
        self.assertFalse(resolved.developer)
        self.assertEqual(resolved.support_installed_bytes, MIB)

    def test_explicit_env_wins_per_key_over_file(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        with _hermetic_env(
            fix=fix, ab_overrides={AB_INSTALL_ENV_SUPPORT_BOUND: str(2 * MIB)}
        ):
            resolved = ab_executor_facts_from_environment(state=_ab_state(fix))
        self.assertEqual(resolved.support_installed_bytes, 2 * MIB)
        # Untouched keys still come from the file.
        self.assertEqual(resolved.bundle_path, fix["bundle"])

    def test_live_service_composes_ab_from_file_with_no_injected_factories(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        before = _snapshot(fix["root"])
        with _hermetic_env(fix=fix):
            with mock.patch.object(
                subprocess, "run", side_effect=AssertionError("no block commands")
            ):
                service = build_live_service()
        self.assertIs(type(service), InstallTransactionService)
        self.assertEqual(service.install_mode, "ab")
        self.assertIsNotNone(service.ab_executor)
        self.assertEqual(before, _snapshot(fix["root"]))

    def test_relative_bundle_path_in_file_refuses_centrally(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        fix["env_file"].write_text(
            f"{AB_INSTALL_ENV_BUNDLE}=relative/bundle.greiaupdate\n"
            f"{AB_INSTALL_ENV_PASSWORD_HASH}={_AB_PASSWORD_HASH}\n"
            f"{AB_INSTALL_ENV_DEVELOPER}=0\n"
            f"{AB_INSTALL_ENV_SUPPORT_BOUND}={MIB}\n",
            encoding="utf-8",
        )
        with _hermetic_env(fix=fix):
            with self.assertRaises(AbInstallCompositionError) as ctx:
                ab_executor_facts_from_environment(state=_ab_state(fix))
        self.assertIn("absolute path", str(ctx.exception))

    def test_unknown_file_key_fails_closed(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        with fix["env_file"].open("a", encoding="utf-8") as handle:
            handle.write("GREIA_AB_FUTURE_KNOB=1\n")
        with _hermetic_env(fix=fix):
            with self.assertRaisesRegex(AbInstallCompositionError, "unknown key"):
                ab_executor_facts_from_environment(state=_ab_state(fix))

    def test_read_ab_env_file_rejects_symlink(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        link = fix["root"] / "link.env"
        link.symlink_to(fix["env_file"])
        with self.assertRaisesRegex(AbInstallCompositionError, "missing"):
            read_ab_env_file(link)


# ---------------------------------------------------------------------------
# Bounded privilege / writable paths
# ---------------------------------------------------------------------------


class InstallerTransactionUnitTests(unittest.TestCase):
    def test_unit_uses_canonical_entrypoint(self) -> None:
        facts = parse_unit(UNIT_PATH)
        self.assertEqual(
            facts.get("exec_start"),
            "/usr/bin/python3 -m greia_installer.transaction_service_entrypoint",
        )
        source = ENTRYPOINT_PATH.read_text(encoding="utf-8")
        self.assertIn("from .transaction_service import main", source)

    def test_worker_runs_as_root_with_unrestricted_chroot_package_configuration(self) -> None:
        text = UNIT_PATH.read_text(encoding="utf-8")
        facts = parse_unit(UNIT_PATH)
        self.assertEqual(facts.get("User"), "root")
        # The entire installed filesystem must be writable and Debian
        # maintainer scripts must be able to create nodes, fork, chown,
        # update initramfs and use any required normal syscall.
        forbidden = (
            "CapabilityBoundingSet", "AmbientCapabilities", "NoNewPrivileges",
            "ProtectSystem", "ReadWritePaths", "PrivateTmp", "ProtectHome",
            "RestrictSUIDSGID", "RestrictAddressFamilies", "SystemCallFilter",
            "ProtectKernelModules", "ProtectKernelTunables", "TasksMax",
            "SystemCallArchitectures", "LockPersonality",
        )
        active = [
            line.split("=", 1)[0].strip()
            for line in text.splitlines()
            if line and not line.lstrip().startswith(("#", ";", "["))
            and "=" in line
        ]
        for directive in forbidden:
            self.assertNotIn(directive, active, directive)

    def test_socket_activation_and_release_facts_remain_unchanged(self) -> None:
        text = UNIT_PATH.read_text(encoding="utf-8")
        self.assertIn("Requires=greia-install-transaction.socket", text)
        self.assertIn("EnvironmentFile=-/etc/greia-os/installer-ab.env", text)
        self.assertIn("Environment=GREIA_HARDWARE_SUPPORT_POOL=/opt/greia-hardware-support", text)
        self.assertIn("Restart=no", text)
        self.assertNotIn("WantedBy=", text)
        self.assertNotIn("StandardInput=socket", text)
        self.assertEqual(parse_unit(UNIT_PATH)["read_write_paths"], set())

    def test_apt_dpkg_chroot_uses_argument_arrays(self) -> None:
        install_source = (
            REPO_ROOT / "src/greia_installer/hardware_support_install.py"
        ).read_text(encoding="utf-8")
        self.assertGreaterEqual(install_source.count('"chroot"'), 3)
        self.assertIn('"apt-get"', install_source)
        self.assertNotIn("shell=True", install_source)
        seams_source = (REPO_ROOT / "src/greia_installer/device_seams.py").read_text(encoding="utf-8")
        self.assertIn("shell=False", seams_source)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Product profile: A/B path defined, legacy kept explicit
# ---------------------------------------------------------------------------


class ProductProfileTests(unittest.TestCase):
    def _storage_updates(self, profile: Path) -> tuple[str, str]:
        try:
            import tomllib
        except ImportError:  # pragma: no cover
            self.skipTest("tomllib unavailable")
        with profile.open("rb") as handle:
            raw = tomllib.load(handle)
        return (
            raw["storage"]["layout_adapter"],
            raw["updates"]["boot_backend"],
        )

    def test_ab_product_profile_registers_ab_adapter_and_backend(self) -> None:
        layout, backend = self._storage_updates(AB_PRODUCT_PROFILE)
        self.assertEqual(layout, "legacy-bios-ab-v1")
        self.assertEqual(backend, "grub-ab-v1")

    def test_legacy_profile_stays_explicit_single_root(self) -> None:
        layout, backend = self._storage_updates(LEGACY_PROFILE)
        self.assertEqual(layout, "bios-single-ext4")
        self.assertEqual(backend, "none-v1")


# ---------------------------------------------------------------------------
# Fail-closed before any disk mutation
# ---------------------------------------------------------------------------


class FailClosedBeforeMutationTests(unittest.TestCase):
    def test_missing_facts_refuse_without_legacy_fallback(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        missing = fix["root"] / "absent-installer-ab.env"
        before = _snapshot(fix["root"])
        with _hermetic_env(fix=fix, config_path=missing):
            with mock.patch.object(
                subprocess, "run", side_effect=AssertionError("no block commands")
            ):
                with self.assertRaisesRegex(
                    TransactionServiceError, "GREIA_AB_"
                ):
                    build_live_service()
        self.assertEqual(before, _snapshot(fix["root"]))

    def test_missing_bundle_refuses(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        fix["bundle"].unlink()
        before = _snapshot(fix["root"])
        with _hermetic_env(fix=fix):
            with mock.patch.object(
                subprocess, "run", side_effect=AssertionError("no block commands")
            ):
                with self.assertRaises(AbInstallCompositionError):
                    ab_executor_facts_from_environment(state=_ab_state(fix))
        self.assertEqual(before, _snapshot(fix["root"]))

    def test_legacy_key_dir_entry_refuses(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        with fix["env_file"].open("a", encoding="utf-8") as handle:
            handle.write("GREIA_AB_TRUSTED_KEY_DIR=/no/such/keys\n")
        with _hermetic_env(fix=fix):
            with self.assertRaisesRegex(
                AbInstallCompositionError, "unknown key"
            ):
                ab_executor_facts_from_environment(state=_ab_state(fix))

    def test_mixed_ab_single_root_profile_refuses(self) -> None:
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        mixed = fix["root"] / "mixed-profile.json"
        _write_profile(
            mixed,
            profile_id=_AB_PROFILE_ID,
            layout=_AB_LAYOUT,
            backend="none-v1",
        )
        mixed_fix = dict(fix)
        mixed_fix["profile"] = mixed
        before = _snapshot(fix["root"])
        with _hermetic_env(fix=mixed_fix):
            with mock.patch.object(
                subprocess, "run", side_effect=AssertionError("no block commands")
            ):
                with self.assertRaises(
                    (AbInstallCompositionError, TransactionServiceError)
                ):
                    build_live_service()
        self.assertEqual(before, _snapshot(fix["root"]))


# ---------------------------------------------------------------------------
# Stale signed-release / trusted-key terminology (T14)
# ---------------------------------------------------------------------------


_STALE_TERMINOLOGY_PATTERNS = (
    re.compile(r"signed[-\s_]*release", re.IGNORECASE),
    re.compile(r"trusted[-\s_]*keys?", re.IGNORECASE),
)


def find_stale_terminology(text: str) -> list[str]:
    """Return stale unsigned-v3 terminology hits in installer-unit text."""
    hits: list[str] = []
    for pattern in _STALE_TERMINOLOGY_PATTERNS:
        hits.extend(match.group(0) for match in pattern.finditer(text))
    return hits


class StaleTerminologyTests(unittest.TestCase):
    def test_unit_has_no_stale_signed_release_or_trusted_key_wording(self) -> None:
        text = UNIT_PATH.read_text(encoding="utf-8")
        self.assertEqual(
            find_stale_terminology(text),
            [],
            "installer unit must use unsigned-v3 wording "
            "(no signed-release / trusted-key terms)",
        )

    def test_stale_terminology_detector_positive_control(self) -> None:
        # TEST-FIXTURE strings: known-bad wording the detector must flag RED.
        bad_signed = "the fresh signed-release installer mounts the slots"
        bad_signed_space = "the fresh signed release installer mounts the slots"
        bad_trusted = "payload digest, target profile, trusted keys"
        for bad in (bad_signed, bad_signed_space, bad_trusted):
            self.assertNotEqual(
                find_stale_terminology(bad),
                [],
                f"detector must flag known-bad fixture: {bad!r}",
            )
        self.assertEqual(
            find_stale_terminology(
                "the unsigned setup-release fresh install mounts the slots"
            ),
            [],
        )


# ---------------------------------------------------------------------------
# Sensitivity: break -> RED -> restore -> GREEN on the central mechanism
# ---------------------------------------------------------------------------


class SensitivityControlTests(unittest.TestCase):
    def test_withdraw_facts_red_restore_green(self) -> None:
        """Positive control: the file mechanism (not test syntax) gates GREEN."""
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        staged = fix["root"] / "staged.env"
        shutil.copyfile(fix["env_file"], staged)
        # GREEN: file present.
        with _hermetic_env(fix=fix):
            resolved = ab_executor_facts_from_environment(state=_ab_state(fix))
        self.assertEqual(resolved.bundle_path, fix["bundle"])
        # RED: withdraw the file (empty capabilities/write-path analogue at
        # the composition layer — no facts, no composition).
        fix["env_file"].unlink()
        with _hermetic_env(fix=fix, config_path=fix["env_file"]):
            with self.assertRaisesRegex(AbInstallCompositionError, "GREIA_AB_"):
                ab_executor_facts_from_environment(state=_ab_state(fix))
        # GREEN again: restore the exact intended state.
        shutil.copyfile(staged, fix["env_file"])
        with _hermetic_env(fix=fix):
            restored = ab_executor_facts_from_environment(state=_ab_state(fix))
        self.assertEqual(restored.bundle_path, fix["bundle"])
        self.assertEqual(restored.support_installed_bytes, MIB)


if __name__ == "__main__":
    unittest.main()


