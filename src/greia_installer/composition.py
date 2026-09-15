"""Shipped installer composition: explicit backends plus the A/B service builder.

The live installer UI depends only on :class:`HardwareSessionController`;
``provisional_installer_hardware_controller`` is today's explicit
compatibility backend (R7 may replace it after the display-session
architecture is selected).

TAKEOVER-3 T3.1 (D54) adds the shipped service-side composition: for a
release-capable A/B profile the builder below constructs the release-capable
A/B executor from device-owned/profile-owned configuration only — trusted
signer/key directory, Setup-resolved release bundle source, typed layout
adapter bound to the observed record, production slot-filesystem/mount
seams, the shared ``SlotWriter``/``SlotFinalizer``, PERSIST authority, boot
backend, journal and hardware inventory/support finalization. A
release-capable profile with missing composition is a hard failure before
destructive work; it never silently routes to the legacy single-root engine.
Legacy/single-root recovery profiles stay explicit (``legacy-single`` mode)
and update-activation-disabled (``none-v1`` boot backend, no A/B executor).

Live A/B knobs (Setup authority owns the values; the builder only
validates). On the release medium these arrive as one immutable image-owned
file (``/etc/greia-os/installer-ab.env``, loaded through the unit's
``EnvironmentFile`` and parsed centrally by
:func:`ab_executor_facts_from_environment`); an explicitly exported
``GREIA_AB_*`` variable wins per key so tests/harnesses can override a
single fact without copying the file:

- ``GREIA_AB_RELEASE_BUNDLE``: absolute path to the signed deterministic
  ``.greiaupdate`` v2 release artifact;
- ``GREIA_AB_TRUSTED_KEY_DIR``: absolute real directory holding the release
  signer public keys;
- ``GREIA_AB_GRUB_PASSWORD_HASH``: stored GRUB PBKDF2 token rendered into
  the fixed boot entries;
- ``GREIA_AB_DEVELOPER``: ``1``/``true`` for developer images, else false;
- ``GREIA_AB_SUPPORT_INSTALLED_BYTES``: release support-set installed-size
  bound in bytes (non-negative integer).

Block-effect seams (partition runner, slot storage/filesystem, persist
staging, observed-identity observation) resolve on the device-execution
path: :func:`build_install_service` takes them as explicit factories so the
*configuration* resolution is shipped code while block drivers stay behind
the T6 device seam. Missing factories fail closed at composition time.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Mapping

from greia_platform.hal_legacy_x import LegacyXHardwareSessionController
from greia_platform.hardware_session import HardwareSessionController
from greia_platform.persistent_layout import AB_LAYOUT_ADAPTERS

from .disk import DeviceObservation
from .fresh_ab_install import (
    AbExecutorFacts,
    FreshAbInstallError,
    FreshAbInstallSeams,
    build_ab_executor,
)
from .layout import LayoutError, LayoutPlan, ProfileSizing


def provisional_installer_hardware_controller() -> HardwareSessionController:
    """Return today's explicit compatibility backend for the live installer.

    R7 may replace this composition with a direct/Wayland settings controller
    after the corresponding display-session architecture is selected. Installer
    UI/state code depends only on HardwareSessionController.
    """

    return LegacyXHardwareSessionController()


class AbInstallCompositionError(RuntimeError):
    """Release-capable A/B composition is absent or incomplete (fail closed)."""


#: Boot backends that carry the A/B lifecycle (mirrors the platform-owned
#: ``BOOT_CONTROL_KINDS``/``AB_LAYOUT_ADAPTERS`` binding; ``none-v1`` is the
#: explicit legacy single-root backend).
AB_INSTALL_BOOT_BACKENDS = frozenset({"grub-ab-v1", "pi-tryboot-ab-v1"})

#: Environment contract for live A/B composition (Setup authority owns the
#: values; validated by :func:`ab_executor_facts_from_environment`).
AB_INSTALL_ENV_BUNDLE = "GREIA_AB_RELEASE_BUNDLE"
AB_INSTALL_ENV_KEY_DIR = "GREIA_AB_TRUSTED_KEY_DIR"
AB_INSTALL_ENV_PASSWORD_HASH = "GREIA_AB_GRUB_PASSWORD_HASH"
AB_INSTALL_ENV_DEVELOPER = "GREIA_AB_DEVELOPER"
AB_INSTALL_ENV_SUPPORT_BOUND = "GREIA_AB_SUPPORT_INSTALLED_BYTES"

#: Image-owned A/B release-facts file shipped on the installer medium and
#: loaded through the unit's ``EnvironmentFile``. The release image must not
#: depend on undocumented operator environment: individual ``GREIA_AB_*``
#: variables remain accepted as explicit test/harness overrides, but on the
#: release medium the values below come from this one immutable file, which
#: the image build generates from the same image profile/release build.
AB_INSTALL_ENV_FILE_DEFAULT = "/etc/greia-os/installer-ab.env"

#: Optional override pointing at a disposable env file (tests/harness only).
#: When set, this path replaces the image-owned default; it is never set by
#: the shipped unit.
AB_INSTALL_CONFIG_PATH_ENV = "GREIA_AB_CONFIG"

#: Upper bound for the env-file read: the file carries five short scalar
#: assignments, never payloads or key material.
AB_INSTALL_ENV_FILE_MAX_BYTES = 8 * 1024

#: Keys the env file may assign. Unknown keys fail closed so a misspelled
#: release fact can never be silently ignored.
AB_INSTALL_ENV_FILE_KEYS = frozenset(
    {
        AB_INSTALL_ENV_BUNDLE,
        AB_INSTALL_ENV_KEY_DIR,
        AB_INSTALL_ENV_PASSWORD_HASH,
        AB_INSTALL_ENV_DEVELOPER,
        AB_INSTALL_ENV_SUPPORT_BOUND,
    }
)


def install_mode_for_state(state: object) -> str:
    """Return the explicit install mode for installer service state.

    ``"ab"`` for release-capable A/B profiles (A/B layout adapter plus A/B
    boot backend), ``"legacy-single"`` when neither fact is A/B. A profile
    mixing A/B and single-root facts fails closed instead of guessing an
    engine — in particular an A/B adapter is never silently served by the
    legacy single-partition engine.
    """
    try:
        adapter_id = state.layout_adapter_id  # type: ignore[union-attr]
        boot_backend = state.boot_backend  # type: ignore[union-attr]
    except AttributeError as exc:
        raise AbInstallCompositionError(
            "installer service state carries no layout/boot facts"
        ) from exc
    try:
        adapter_ab = adapter_id in AB_LAYOUT_ADAPTERS
        backend_ab = boot_backend in AB_INSTALL_BOOT_BACKENDS
    except TypeError as exc:
        raise AbInstallCompositionError(
            "installer service layout/boot facts are not authoritative"
        ) from exc
    if adapter_ab and backend_ab:
        return "ab"
    if not adapter_ab and not backend_ab:
        return "legacy-single"
    raise AbInstallCompositionError(
        "installer profile mixes A/B and single-root facts "
        f"(adapter={adapter_id!r} backend={boot_backend!r}); "
        "refusing to guess the install engine"
    )


def ab_sizing_for_state(state: object) -> ProfileSizing:
    """Return the profile-owned sizing facts for an A/B profile.

    Refuses fail-closed for non-A/B profiles so release-capable composition
    can never be assembled for the wrong engine.
    """
    if install_mode_for_state(state) != "ab":
        raise AbInstallCompositionError(
            "A/B composition requires a release-capable A/B profile"
        )
    try:
        return ProfileSizing(
            layout_adapter_id=state.layout_adapter_id,  # type: ignore[union-attr]
            slot_bytes=state.slot_bytes,  # type: ignore[union-attr]
            persist_minimum_bytes=state.persist_minimum_bytes,  # type: ignore[union-attr]
            boot_backend=state.boot_backend,  # type: ignore[union-attr]
        )
    except (LayoutError, AttributeError, TypeError) as exc:
        raise AbInstallCompositionError(
            f"A/B profile sizing is not authoritative: {exc}"
        ) from exc


def _require_existing_file(value: object, *, field_name: str) -> Path:
    location = Path(value) if isinstance(value, (Path, str)) and value else None
    if location is None or not location.is_absolute():
        raise AbInstallCompositionError(f"A/B {field_name} must be an absolute path")
    if location.is_symlink() or not location.is_file():
        raise AbInstallCompositionError(f"A/B {field_name} is not a regular file")
    return location


def _require_real_dir(value: object, *, field_name: str) -> Path:
    location = Path(value) if isinstance(value, (Path, str)) and value else None
    if location is None or not location.is_absolute():
        raise AbInstallCompositionError(f"A/B {field_name} must be an absolute path")
    if location.is_symlink() or not location.is_dir():
        raise AbInstallCompositionError(
            f"A/B {field_name} must be an absolute real directory"
        )
    return location


def resolve_ab_executor_facts(
    *,
    state: object,
    release_bundle: object,
    trusted_key_dir: object,
    password_hash: object,
    developer: object = False,
    support_installed_bytes: object,
) -> AbExecutorFacts:
    """Bind device-owned/profile-owned configuration into executor facts.

    Every element is required: a missing bundle, key directory, password
    hash, support bound or non-A/B profile fails closed here, before any
    service or destructive work exists to fall back from.
    """
    sizing = ab_sizing_for_state(state)
    bundle = _require_existing_file(release_bundle, field_name="release bundle")
    key_dir = _require_real_dir(trusted_key_dir, field_name="trusted key dir")
    if not isinstance(password_hash, str) or not password_hash:
        raise AbInstallCompositionError("A/B GRUB password hash must be non-empty text")
    if not isinstance(developer, bool):
        raise AbInstallCompositionError("A/B developer flag must be a boolean")
    if (
        isinstance(support_installed_bytes, bool)
        or not isinstance(support_installed_bytes, int)
        or support_installed_bytes < 0
    ):
        raise AbInstallCompositionError(
            "A/B support installed-size bound must be a non-negative integer"
        )
    try:
        profile_id = state.compatible_profile_id  # type: ignore[union-attr]
        platform_family = state.platform_family  # type: ignore[union-attr]
        architecture = state.architecture  # type: ignore[union-attr]
    except AttributeError as exc:
        raise AbInstallCompositionError(
            "installer service state carries no profile/family/architecture facts"
        ) from exc
    try:
        return AbExecutorFacts(
            bundle_path=bundle,
            trusted_key_dir=key_dir,
            expected_profile_id=profile_id,
            expected_platform_family=platform_family,
            expected_architecture=architecture,
            sizing=sizing,
            support_installed_bytes=support_installed_bytes,
            password_hash=password_hash,
            developer=developer,
        )
    except (FreshAbInstallError, TypeError) as exc:
        raise AbInstallCompositionError(
            f"A/B executor facts are not authoritative: {exc}"
        ) from exc


def ab_env_file_path_from_environment() -> Path | None:
    """Return the image-owned A/B env-file path, or ``None`` when absent.

    ``GREIA_AB_CONFIG`` (tests/harness only) replaces the image-owned
    default ``/etc/greia-os/installer-ab.env``. A configured-but-missing
    file fails closed in :func:`read_ab_env_file`; an unset default that
    does not exist simply means "no image-owned facts" (legacy media or a
    bare test environment relying on explicit ``GREIA_AB_*`` overrides).
    """
    override = os.environ.get(AB_INSTALL_CONFIG_PATH_ENV, "").strip()
    if override:
        return Path(override)
    return Path(AB_INSTALL_ENV_FILE_DEFAULT)


def read_ab_env_file(path: Path) -> dict[str, str]:
    """Parse one immutable A/B env file into raw ``GREIA_AB_*`` assignments.

    Strict systemd-``EnvironmentFile``-shaped subset: ``KEY=VALUE`` lines,
    ``#`` comments and blank lines; optional surrounding double quotes on
    values; no ``export`` prefix, no shell expansion, no line continuations.
    Unknown keys, empty values for required names, oversized files,
    symlinks and missing files all raise
    :class:`AbInstallCompositionError` fail-closed.
    """
    if not isinstance(path, Path):
        raise AbInstallCompositionError("A/B env-file path must be a Path")
    if not path.is_absolute():
        raise AbInstallCompositionError("A/B env-file path must be absolute")
    if path.is_symlink() or not path.is_file():
        raise AbInstallCompositionError(
            f"A/B release facts file is missing: {path} "
            "(release medium carries /etc/greia-os/installer-ab.env; "
            "tests set explicit GREIA_AB_* overrides or GREIA_AB_CONFIG)"
        )
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AbInstallCompositionError(
            f"A/B release facts file is unreadable: {path}: {exc}"
        ) from exc
    if len(raw) > AB_INSTALL_ENV_FILE_MAX_BYTES:
        raise AbInstallCompositionError("A/B release facts file exceeds Greia bound")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AbInstallCompositionError(
            "A/B release facts file is not valid UTF-8"
        ) from exc
    facts: dict[str, str] = {}
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise AbInstallCompositionError(
                f"A/B release facts file line {lineno} is not KEY=VALUE"
            )
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()
        if key in ("export", "") or not key.startswith("GREIA_AB_"):
            raise AbInstallCompositionError(
                f"A/B release facts file line {lineno} carries an invalid key"
            )
        if key not in AB_INSTALL_ENV_FILE_KEYS:
            raise AbInstallCompositionError(
                f"A/B release facts file carries unknown key {key!r}"
            )
        if key in facts:
            raise AbInstallCompositionError(
                f"A/B release facts file repeats key {key!r}"
            )
        if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        if not value:
            raise AbInstallCompositionError(
                f"A/B release facts file key {key!r} must be non-empty"
            )
        if "\n" in value or "\r" in value:
            raise AbInstallCompositionError(
                f"A/B release facts file key {key!r} carries an invalid value"
            )
        facts[key] = value
    return facts


def _merged_ab_assignments() -> dict[str, str]:
    """Merge image-owned env-file facts with explicit ``GREIA_AB_*`` overrides.

    The file supplies the release baseline; an explicitly exported variable
    wins per key so tests and harnesses can override one fact without
    copying the whole file. Absence of both is not an error here — the
    downstream validators name the missing ``GREIA_AB_*`` fact.
    """
    merged: dict[str, str] = {}
    candidate = ab_env_file_path_from_environment()
    assert candidate is not None
    use_file = False
    if os.environ.get(AB_INSTALL_CONFIG_PATH_ENV, "").strip():
        use_file = True
    elif candidate.is_file() and not candidate.is_symlink():
        use_file = True
    if use_file:
        merged.update(read_ab_env_file(candidate))
    for key in (
        AB_INSTALL_ENV_BUNDLE,
        AB_INSTALL_ENV_KEY_DIR,
        AB_INSTALL_ENV_PASSWORD_HASH,
        AB_INSTALL_ENV_DEVELOPER,
        AB_INSTALL_ENV_SUPPORT_BOUND,
    ):
        if key in os.environ:
            merged[key] = os.environ[key]
    return merged


def _env_flag(name: str) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if raw in ("", "0", "false", "no"):
        return False
    if raw in ("1", "true", "yes"):
        return True
    raise AbInstallCompositionError(f"{name} must be a boolean flag")


def _env_support_bound(name: str) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        raise AbInstallCompositionError(f"{name} is required for A/B composition")
    try:
        bound = int(raw, 10)
    except ValueError as exc:
        raise AbInstallCompositionError(f"{name} must be a non-negative integer") from exc
    if bound < 0:
        raise AbInstallCompositionError(f"{name} must be a non-negative integer")
    return bound


def ab_executor_facts_from_environment(*, state: object) -> AbExecutorFacts:
    """Resolve executor facts from the live Setup-owned release facts.

    Single central parser: the image-owned env file
    (``/etc/greia-os/installer-ab.env`` via the unit's ``EnvironmentFile``,
    or ``GREIA_AB_CONFIG`` in tests) supplies the release baseline and an
    explicitly exported ``GREIA_AB_*`` variable wins per key. A missing
    bundle, key directory, password hash, support bound or non-A/B profile
    fails closed here, before any service or destructive work exists.
    """
    merged = _merged_ab_assignments()
    password_hash = (merged.get(AB_INSTALL_ENV_PASSWORD_HASH) or "").strip()
    if not password_hash:
        raise AbInstallCompositionError(
            f"{AB_INSTALL_ENV_PASSWORD_HASH} is required for A/B composition"
        )
    developer_raw = (merged.get(AB_INSTALL_ENV_DEVELOPER) or "").strip().lower()
    if developer_raw in ("", "0", "false", "no"):
        developer = False
    elif developer_raw in ("1", "true", "yes"):
        developer = True
    else:
        raise AbInstallCompositionError(
            f"{AB_INSTALL_ENV_DEVELOPER} must be a boolean flag"
        )
    support_raw = (merged.get(AB_INSTALL_ENV_SUPPORT_BOUND) or "").strip()
    if not support_raw:
        raise AbInstallCompositionError(
            f"{AB_INSTALL_ENV_SUPPORT_BOUND} is required for A/B composition"
        )
    try:
        support_bound = int(support_raw, 10)
    except ValueError as exc:
        raise AbInstallCompositionError(
            f"{AB_INSTALL_ENV_SUPPORT_BOUND} must be a non-negative integer"
        ) from exc
    if support_bound < 0:
        raise AbInstallCompositionError(
            f"{AB_INSTALL_ENV_SUPPORT_BOUND} must be a non-negative integer"
        )
    return resolve_ab_executor_facts(
        state=state,
        release_bundle=merged.get(AB_INSTALL_ENV_BUNDLE, ""),
        trusted_key_dir=merged.get(AB_INSTALL_ENV_KEY_DIR, ""),
        password_hash=password_hash,
        developer=developer,
        support_installed_bytes=support_bound,
    )


def compose_ab_executor(
    *,
    facts: AbExecutorFacts,
    seams_factory: Callable[[DeviceObservation], FreshAbInstallSeams] | None,
    identities_factory: (
        Callable[
            [DeviceObservation, LayoutPlan], Mapping[str, Mapping[str, str]]
        ]
        | None
    ),
):  # -> Callable (executor; annotation kept loose for the narrow protocol)
    """Bind executor facts plus per-target factories into the A/B executor.

    ``seams_factory`` owns every destructive/filesystem effect for the
    rematerialized target; ``identities_factory`` is the post-layout
    identity observer the orchestrator invokes as ``observer(target, plan)``
    only after the partition/filesystem effects exist (never before the
    first destructive command). Either missing fails closed here — the
    executor is never built half-wired.
    """
    if not isinstance(facts, AbExecutorFacts):
        raise AbInstallCompositionError("A/B composition requires typed executor facts")
    if seams_factory is None or identities_factory is None:
        raise AbInstallCompositionError(
            "A/B composition is missing its seam/identity factories; "
            "refusing to build a half-wired executor"
        )
    try:
        return build_ab_executor(
            facts, seams_factory, identities_factory=identities_factory
        )
    except FreshAbInstallError as exc:
        raise AbInstallCompositionError(
            f"A/B executor composition refused: {exc}"
        ) from exc


def build_install_service(
    *,
    state: object,
    authority: object,
    ab_release_bundle: object = None,
    ab_trusted_key_dir: object = None,
    ab_password_hash: object = None,
    ab_developer: object = False,
    ab_support_installed_bytes: object = None,
    ab_seams_factory: Callable[[DeviceObservation], FreshAbInstallSeams] | None = None,
    ab_identities_factory: (
        Callable[
            [DeviceObservation, LayoutPlan], Mapping[str, Mapping[str, str]]
        ]
        | None
    ) = None,
    ab_from_environment: bool = False,
    engine_factory: object = None,
):  # -> InstallTransactionService (imported lazily; see below)
    """Assemble the shipped install-transaction service for a profile.

    ``"ab"`` profiles get the release-capable A/B executor bound from
    device-owned/profile-owned configuration; any missing element raises
    :class:`AbInstallCompositionError` — never a silent legacy fallback.
    ``"legacy-single"`` profiles get the explicit legacy single-partition
    engine path (``ab_executor=None``, mode ``"legacy-single"``).
    Block-effect seams stay explicit factories so tests and the T6 device
    seam drive the shipped wiring with zero valued-disk contact.
    """
    from .transaction_service import InstallTransactionService

    mode = install_mode_for_state(state)
    if mode == "legacy-single":
        return InstallTransactionService(
            authority=authority,  # type: ignore[arg-type]
            state=state,  # type: ignore[arg-type]
            engine_factory=engine_factory,  # type: ignore[arg-type]
            install_mode="legacy-single",
        )
    if ab_from_environment:
        facts = ab_executor_facts_from_environment(state=state)
    else:
        facts = resolve_ab_executor_facts(
            state=state,
            release_bundle=ab_release_bundle,
            trusted_key_dir=ab_trusted_key_dir,
            password_hash=ab_password_hash,
            developer=ab_developer,
            support_installed_bytes=ab_support_installed_bytes,
        )
    executor = compose_ab_executor(
        facts=facts,
        seams_factory=ab_seams_factory,
        identities_factory=ab_identities_factory,
    )
    return InstallTransactionService(
        authority=authority,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        ab_executor=executor,
        install_mode="ab",
    )


__all__ = [
    "AB_INSTALL_BOOT_BACKENDS",
    "AB_INSTALL_CONFIG_PATH_ENV",
    "AB_INSTALL_ENV_BUNDLE",
    "AB_INSTALL_ENV_DEVELOPER",
    "AB_INSTALL_ENV_FILE_DEFAULT",
    "AB_INSTALL_ENV_FILE_KEYS",
    "AB_INSTALL_ENV_FILE_MAX_BYTES",
    "AB_INSTALL_ENV_KEY_DIR",
    "AB_INSTALL_ENV_PASSWORD_HASH",
    "AB_INSTALL_ENV_SUPPORT_BOUND",
    "AbInstallCompositionError",
    "ab_env_file_path_from_environment",
    "ab_executor_facts_from_environment",
    "ab_sizing_for_state",
    "build_install_service",
    "compose_ab_executor",
    "install_mode_for_state",
    "provisional_installer_hardware_controller",
    "read_ab_env_file",
    "resolve_ab_executor_facts",
]
