"""POSTR1-P2-INSTALLER-PROOF: shipped installer A/B product composition is closed.

Gate P2 (``INSTALLER_PRODUCT_COMPOSED``) proof: the exact shipped composition
root :func:`greia_installer.transaction_service.build_live_service` with **no**
injected ``ab_seams_factory``/``ab_identities_factory`` composes the A/B
product service by itself.

Composition source (POSTR1-P2-INSTALLER-UNIT): the shipped unit supplies the
five ``GREIA_*`` names via ``Environment=`` plus one immutable image-owned
facts file (``/etc/greia-os/installer-ab.env`` via ``EnvironmentFile``,
parsed centrally by
:func:`greia_installer.composition.ab_executor_facts_from_environment``).
Tests shadow the image-owned path with disposable ``GREIA_AB_CONFIG``
files (documented tests/harness-only override) — never injected seam/identity
factories and never a test-local ``build_live_service`` stand-in.

What this module drives:

- Req3: shipped five names + disposable image-owned env file (``GREIA_AB_CONFIG``),
  no ``GREIA_AB_*`` explicit variables, no factories → ``install_mode == "ab"``
  with a bound ``ab_executor``. Construction runs zero block commands
  (``subprocess.run`` blocked) and writes nothing beside its fixtures.
- Req4: disposable ``GREIA_AB_*`` explicit release facts, still no injected
  factories → the production seam/identity pair binds by default
  (``install_mode == "ab"`` with a bound executor). Same no-execution,
  no-write guards.
- Req5: lower-level ``build_install_service`` with explicit facts + minimal
  non-executed fakes still returns ``"ab"`` (T3-S control).
- Req6: single-root profile yields ``"legacy-single"``; an A/B profile never
  silently becomes ``"legacy-single"`` (missing facts refuse closed).
- Req7 guards: no probe/resolver/factory execution during construction;
  failing construction writes nothing; the shipped unit contract (five names
  via ``Environment=`` plus the ``EnvironmentFile`` facts source, no
  hardcoded ``GREIA_AB_*`` values) is asserted structurally.

Gate P2 green does not close T3-P: T3-P remains OPEN until Gate P5.

No network, no ``cryptography``-dependent signing (construction validates
file shapes only, never bundle signatures), no ``/etc``/``/run``/``/opt``/
``/dev`` contact: all fixtures live under disposable tmpdirs.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from greia_installer.composition import (
    AB_INSTALL_CONFIG_PATH_ENV,
    AbInstallCompositionError,
    build_install_service,
    install_mode_for_state,
)
from greia_installer.disk import PcInternalTargetPolicy
from greia_installer.transaction_service import (
    PlatformInstallAuthority,
    ServiceState,
    TransactionServiceError,
    build_live_service,
)

GIB = 1024 * 1024 * 1024
MIB = 1024 * 1024

_AB_PROFILE_ID = "test-ab-product-v1"
_AB_FAMILY = "legacy-x86"
_AB_ARCH = "i386"
_AB_LAYOUT = "legacy-bios-ab-v1"
_AB_BACKEND = "grub-ab-v1"

_LEGACY_PROFILE_ID = "test-legacy-recovery-v1"
_LEGACY_LAYOUT = "bios-single-ext4"
_LEGACY_BACKEND = "none-v1"

# Exact GREIA_* names the shipped unit supplies via Environment= (read-only).
_SHIPPED_ENV_NAMES = (
    "GREIA_OS_ROOT",
    "GREIA_INSTALL_PAYLOAD",
    "GREIA_INSTALL_PAYLOAD_DIGEST",
    "GREIA_TARGET_IMAGE_PROFILE",
    "GREIA_HARDWARE_SUPPORT_POOL",
)

# Shipped unit supplies none of these via Environment=; they arrive through
# the image-owned env file (shadowed by GREIA_AB_CONFIG in tests) or as
# explicit test/harness overrides.
_AB_ENV_NAMES = (
    "GREIA_AB_RELEASE_BUNDLE",
    "GREIA_AB_TRUSTED_KEY_DIR",
    "GREIA_AB_GRUB_PASSWORD_HASH",
    "GREIA_AB_DEVELOPER",
    "GREIA_AB_SUPPORT_INSTALLED_BYTES",
)

_AB_PASSWORD_HASH = "grub.pbkdf2.sha512.10000." + "P" * 64
_AB_SUPPORT_BOUND = 1 * MIB


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
    path: Path, *, bundle: Path, key_dir: Path, support_bound: int = _AB_SUPPORT_BOUND
) -> Path:
    """Write a disposable image-owned-shaped A/B facts file."""
    path.write_text(
        "# disposable image-owned A/B release facts (GREIA_AB_CONFIG shadow)\n"
        f"GREIA_AB_RELEASE_BUNDLE={bundle}\n"
        f"GREIA_AB_TRUSTED_KEY_DIR={key_dir}\n"
        f"GREIA_AB_GRUB_PASSWORD_HASH={_AB_PASSWORD_HASH}\n"
        "GREIA_AB_DEVELOPER=0\n"
        f"GREIA_AB_SUPPORT_INSTALLED_BYTES={support_bound}\n",
        encoding="utf-8",
    )
    return path


def _snapshot_roots(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*")}


@contextmanager
def _shipped_env(*, root: Path, profile: Path, payload: Path,
                 digest: Path, pool: Path, os_root: Path,
                 ab_overrides: dict[str, str] | None = None,
                 config_path: Path | str | None = None):
    """Install exactly the shipped five-name environment plus one facts source.

    ``config_path`` shadows the image-owned ``/etc/greia-os/installer-ab.env``
    through the documented ``GREIA_AB_CONFIG`` tests-only override. ``None``
    means "no file" (legacy bare environment); explicit ``GREIA_AB_*``
    overrides win per key exactly as the central parser defines.
    """
    saved = {
        name: os.environ.get(name)
        for name in _SHIPPED_ENV_NAMES + _AB_ENV_NAMES + (AB_INSTALL_CONFIG_PATH_ENV,)
    }
    try:
        os.environ["GREIA_OS_ROOT"] = str(os_root)
        os.environ["GREIA_INSTALL_PAYLOAD"] = str(payload)
        os.environ["GREIA_INSTALL_PAYLOAD_DIGEST"] = str(digest)
        os.environ["GREIA_TARGET_IMAGE_PROFILE"] = str(profile)
        os.environ["GREIA_HARDWARE_SUPPORT_POOL"] = str(pool)
        for name in _AB_ENV_NAMES:
            os.environ.pop(name, None)
        if config_path is None:
            os.environ.pop(AB_INSTALL_CONFIG_PATH_ENV, None)
        else:
            os.environ[AB_INSTALL_CONFIG_PATH_ENV] = str(config_path)
        for name, value in (ab_overrides or {}).items():
            os.environ[name] = value
        # Req2: no GREIA_AB_* outside the explicit Req4 overrides.
        if ab_overrides is None and config_path is None:
            for name in _AB_ENV_NAMES:
                assert name not in os.environ, name
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _make_ab_tree() -> tuple[str, dict[str, Path]]:
    """Disposable tmpdir fixtures for one A/B product-composition attempt."""
    directory = tempfile.mkdtemp(prefix="installer-product-red-")
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
    key_dir = root / "ab-trusted-keys"
    key_dir.mkdir()
    env_file = root / "installer-ab.env"
    _write_ab_env_file(env_file, bundle=bundle, key_dir=key_dir)
    return directory, {
        "root": root,
        "os_root": os_root,
        "pool": pool,
        "payload": payload,
        "digest": digest,
        "profile": profile,
        "bundle": bundle,
        "key_dir": key_dir,
        "env_file": env_file,
    }


def _cause_chain(exc: BaseException) -> list[BaseException]:
    chain = []
    seen = exc.__cause__ or exc.__context__
    while seen is not None and seen not in chain:
        chain.append(seen)
        seen = seen.__cause__ or seen.__context__
    return chain


class _CountingProbe:
    """Fake disk probe: construction must never probe (no-touch guard)."""

    def __init__(self) -> None:
        self.calls = 0

    def probe(self):  # type: ignore[no-untyped-def]
        self.calls += 1
        raise AssertionError("no inventory probe during composition")


class _CountingResolver:
    def __init__(self) -> None:
        self.calls = 0

    def resolve(self, inventory=None):  # type: ignore[no-untyped-def]
        self.calls += 1
        raise AssertionError("no ancestry resolution during composition")


class ShippedAbProductCompositionTests(unittest.TestCase):
    """Req3/Req4 GREEN: shipped composition closes through build_live_service."""

    def test_req3_shipped_ab_composition_without_test_factories_is_complete(
        self,
    ) -> None:
        """Shipped root + shipped env + image-owned facts file composes A/B."""
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        before = _snapshot_roots(fix["root"])
        with _shipped_env(
            root=fix["root"],
            profile=fix["profile"],
            payload=fix["payload"],
            digest=fix["digest"],
            pool=fix["pool"],
            os_root=fix["os_root"],
            config_path=fix["env_file"],
        ):
            # Production constructor first: the profile itself is authoritative.
            state = ServiceState.from_target_profile(
                fix["profile"],
                payload=fix["payload"],
                payload_digest=fix["digest"],
                project_root=fix["os_root"],
                hardware_support_pool=fix["pool"],
            )
            self.assertEqual(install_mode_for_state(state), "ab")
            # No injected factories: production seam/identity pair binds by
            # default; construction runs zero block commands.
            with mock.patch.object(
                __import__("subprocess"), "run",
                side_effect=AssertionError("no block commands during composition"),
            ):
                service = build_live_service()
            # Post-fix shape: A/B profile never silently becomes legacy.
            self.assertEqual(service.install_mode, "ab")
            self.assertIsNotNone(service.ab_executor)
            after = _snapshot_roots(fix["root"])
            self.assertEqual(
                before, after, "successful construction must not write beside fixtures"
            )

    def test_req4_shipped_ab_factories_are_production_wired(self) -> None:
        """Disposable AB facts via explicit env, still no injected factories."""
        directory = tempfile.mkdtemp(prefix="installer-product-red-ab-")
        self.addCleanup(shutil.rmtree, directory, True)
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
        key_dir = root / "ab-trusted-keys"
        key_dir.mkdir()
        ab_overrides = {
            "GREIA_AB_RELEASE_BUNDLE": str(bundle),
            "GREIA_AB_TRUSTED_KEY_DIR": str(key_dir),
            "GREIA_AB_GRUB_PASSWORD_HASH": _AB_PASSWORD_HASH,
            "GREIA_AB_SUPPORT_INSTALLED_BYTES": str(_AB_SUPPORT_BOUND),
        }
        before = _snapshot_roots(root)
        with _shipped_env(
            root=root,
            profile=profile,
            payload=payload,
            digest=digest,
            pool=pool,
            os_root=os_root,
            ab_overrides=ab_overrides,
        ):
            state = ServiceState.from_target_profile(
                profile,
                payload=payload,
                payload_digest=digest,
                project_root=os_root,
                hardware_support_pool=pool,
            )
            self.assertEqual(install_mode_for_state(state), "ab")
            with mock.patch.object(
                __import__("subprocess"), "run",
                side_effect=AssertionError("no block commands during composition"),
            ):
                service = build_live_service()
            self.assertEqual(service.install_mode, "ab")
            self.assertIsNotNone(service.ab_executor)
        self.assertEqual(before, _snapshot_roots(root))


class InstallerProductControlsTests(unittest.TestCase):
    """Req5/Req6/Req7 passing controls: the GREEN is product, not fixture."""

    def test_req5_lower_level_builder_with_explicit_seams_stays_green(self) -> None:
        """T3-S control: explicit facts + non-executed fakes compose ``ab``."""
        directory = tempfile.mkdtemp(prefix="installer-product-ctrl-")
        self.addCleanup(shutil.rmtree, directory, True)
        root = Path(directory).resolve()
        payload = root / "payload.squashfs"
        payload.write_bytes(b"test-payload")
        digest = root / "expected-payload.sha256"
        digest.write_bytes(b"0" * 64)
        pool = root / "support-pool"
        pool.mkdir()
        profile = root / "target-image-profile.json"
        _write_profile(
            profile, profile_id=_AB_PROFILE_ID, layout=_AB_LAYOUT, backend=_AB_BACKEND
        )
        bundle = root / "release.greiaupdate"
        bundle.write_bytes(b"test-release-bundle")
        key_dir = root / "trusted-keys"
        key_dir.mkdir()
        project_root = Path(__file__).resolve().parents[1]
        state = ServiceState.from_target_profile(
            profile,
            payload=payload,
            payload_digest=digest,
            project_root=project_root,
            hardware_support_pool=pool,
        )
        self.assertEqual(install_mode_for_state(state), "ab")
        probe = _CountingProbe()
        resolver = _CountingResolver()
        authority = PlatformInstallAuthority(
            policy=PcInternalTargetPolicy(),
            compatible_profile=_AB_PROFILE_ID,
            probe=probe,  # type: ignore[arg-type]
            live_resolver=resolver,  # type: ignore[arg-type]
        )
        seam_calls: list[object] = []
        identity_calls: list[object] = []

        def _seams(target):  # type: ignore[no-untyped-def]
            seam_calls.append(target)
            raise AssertionError("seam factory must not run at construction")

        def _identities(target, plan=None):  # type: ignore[no-untyped-def]
            identity_calls.append(target)
            raise AssertionError("identity factory must not run at construction")

        service = build_install_service(
            state=state,
            authority=authority,
            ab_release_bundle=bundle,
            ab_trusted_key_dir=key_dir,
            ab_password_hash=_AB_PASSWORD_HASH,
            ab_support_installed_bytes=_AB_SUPPORT_BOUND,
            ab_seams_factory=_seams,
            ab_identities_factory=_identities,
        )
        self.assertEqual(service.install_mode, "ab")
        self.assertIsNotNone(service.ab_executor)
        # Factories are bound, not executed, at construction (Req5/Req7).
        self.assertEqual(seam_calls, [])
        self.assertEqual(identity_calls, [])
        self.assertEqual(probe.calls, 0)
        self.assertEqual(resolver.calls, 0)

    def test_req6_legacy_single_root_stays_explicit_legacy_via_live_service(
        self,
    ) -> None:
        """Legacy control: single-root profile yields ``legacy-single`` live."""
        directory = tempfile.mkdtemp(prefix="installer-product-legacy-")
        self.addCleanup(shutil.rmtree, directory, True)
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
            profile,
            profile_id=_LEGACY_PROFILE_ID,
            layout=_LEGACY_LAYOUT,
            backend=_LEGACY_BACKEND,
        )
        with _shipped_env(
            root=root,
            profile=profile,
            payload=payload,
            digest=digest,
            pool=pool,
            os_root=os_root,
        ):
            service = build_live_service()
            self.assertEqual(service.install_mode, "legacy-single")
            self.assertIsNone(service.ab_executor)

    def test_req6_ab_profile_never_silently_becomes_legacy_single(self) -> None:
        """A/B profile through the shipped root never routes to legacy."""
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        with _shipped_env(
            root=fix["root"],
            profile=fix["profile"],
            payload=fix["payload"],
            digest=fix["digest"],
            pool=fix["pool"],
            os_root=fix["os_root"],
            config_path=fix["env_file"],
        ):
            state = ServiceState.from_target_profile(
                fix["profile"],
                payload=fix["payload"],
                payload_digest=fix["digest"],
                project_root=fix["os_root"],
                hardware_support_pool=fix["pool"],
            )
            self.assertEqual(install_mode_for_state(state), "ab")
            service = build_live_service()
            self.assertNotEqual(
                service.install_mode,
                "legacy-single",
                "an A/B profile must never silently become legacy-single",
            )
            self.assertEqual(service.install_mode, "ab")

    def test_req7_shipped_unit_supplies_only_five_greia_names(self) -> None:
        """Guard: env recreation matches the shipped unit (five names + file)."""
        unit = (
            Path(__file__).resolve().parents[1]
            / "build"
            / "installer-overlay"
            / "etc"
            / "systemd"
            / "system"
            / "greia-install-transaction.service"
        )
        text = unit.read_text(encoding="utf-8")
        for name in _SHIPPED_ENV_NAMES:
            self.assertIn(name, text, f"shipped unit must supply {name}")
        # A/B facts arrive through EnvironmentFile, never hardcoded values.
        self.assertIn("EnvironmentFile=-/etc/greia-os/installer-ab.env", text)
        for name in _AB_ENV_NAMES:
            self.assertNotIn(
                f"Environment={name}=", text,
                f"shipped unit must not hardcode {name} (it comes from the file)",
            )

    def test_req7_failing_construction_touches_no_disk(self) -> None:
        """Guard: failing shipped construction writes nothing valued."""
        directory, fix = _make_ab_tree()
        self.addCleanup(shutil.rmtree, directory, True)
        before = _snapshot_roots(fix["root"])
        with _shipped_env(
            root=fix["root"],
            profile=fix["profile"],
            payload=fix["payload"],
            digest=fix["digest"],
            pool=fix["pool"],
            os_root=fix["os_root"],
        ):
            with self.assertRaises(TransactionServiceError):
                build_live_service()
        after = _snapshot_roots(fix["root"])
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
