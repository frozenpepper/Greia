from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .localization import LocalizationError, LocaleTag


SCHEMA_VERSION = 1
DEFAULT_SYSTEM_LOCALE = "en"
DEFAULT_STATE_DIR = Path("/var/lib/greia-system-settings")
DEFAULT_INSTALL_RECORD = Path("/etc/greia-os/install-record.json")
DEFAULT_PRIVILEGED_HELPER = Path("/usr/local/lib/greia-os/greia-languagectl")


class SystemLanguageError(RuntimeError):
    """Raised when a Greia device-language operation cannot be completed safely."""


@dataclass(frozen=True, slots=True)
class SystemLanguage:
    """One product-selected Greia device language.

    ``name`` is deliberately a simple Latin-script label that the current
    Pygame installer/on-device Parent surface can always render with Nunito.
    ``native_name`` is available to richer clients such as Greia Parents.
    ``flag`` is child/parent presentation metadata only; the locale tag remains
    the actual language identity.
    """

    locale: str
    name: str
    native_name: str
    flag: str

    def as_json_dict(self) -> dict[str, str]:
        return {
            "locale": self.locale,
            "name": self.name,
            "native_name": self.native_name,
            "flag": self.flag,
        }


# Language manifests are packaged beside this module and shipped in OS images.
# One directory with a valid manifest represents one offered product locale.
# Translators stage incomplete work outside this directory; placing a manifest
# here is the explicit product-promotion action, not a background file scan.
LANGUAGE_ROOT = Path(__file__).resolve().parent / "languages"
MAX_SYSTEM_LANGUAGES = 32
MAX_LANGUAGE_MANIFEST_BYTES = 4096


def load_system_languages(root: Path | None = None) -> tuple[SystemLanguage, ...]:
    """Read the bounded, sorted language manifests once at process startup.

    Supplying a root makes this independently testable without patching global
    variables. Never follow symlinked directories or manifests, and fail with
    the offending file named instead of silently hiding an advertised locale.
    """
    directory = LANGUAGE_ROOT if root is None else Path(root)
    try:
        entries = sorted(directory.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        raise SystemLanguageError(f"cannot read Greia language manifests: {directory}") from exc
    result: list[tuple[int, SystemLanguage]] = []
    seen: set[str] = set()
    for entry in entries:
        if not entry.is_dir() or entry.is_symlink():
            continue
        manifest = entry / "manifest.json"
        if not manifest.exists():
            continue
        if manifest.is_symlink() or not manifest.is_file():
            raise SystemLanguageError(f"invalid language manifest path: {manifest}")
        try:
            if manifest.stat().st_size > MAX_LANGUAGE_MANIFEST_BYTES:
                raise ValueError("oversized language manifest")
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("schema_version") != 1:
                raise ValueError("expected schema_version 1 object")
            locale = LocaleTag.parse(data["locale"]).value
            if locale != entry.name or locale in seen:
                raise ValueError("locale must match a unique directory name")
            name, native, flag = (data[key] for key in ("name", "native_name", "flag"))
            if not all(isinstance(value, str) and 0 < len(value.strip()) <= 80
                       for value in (name, native, flag)):
                raise ValueError("name, native_name and flag must be nonempty bounded strings")
            order = data.get("order", 1000)
            if type(order) is not int or not 0 <= order <= 10000:
                raise ValueError("order must be an integer from 0 to 10000")
            if data.get("direction", "ltr") not in ("ltr", "rtl"):
                raise ValueError("direction must be ltr or rtl")
            seen.add(locale)
            result.append((order, SystemLanguage(locale, name, native, flag)))
        except (OSError, ValueError, KeyError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
            raise SystemLanguageError(f"invalid language manifest {manifest}: {exc}") from exc
        if len(result) > MAX_SYSTEM_LANGUAGES:
            raise SystemLanguageError("too many Greia language manifests")
    result.sort(key=lambda row: (row[0], row[1].locale))
    if DEFAULT_SYSTEM_LOCALE not in seen:
        raise SystemLanguageError("required English language manifest is missing")
    return tuple(item for _, item in result)


SUPPORTED_SYSTEM_LANGUAGES: tuple[SystemLanguage, ...] = load_system_languages()
SUPPORTED_SYSTEM_LOCALES: tuple[str, ...] = tuple(
    item.locale for item in SUPPORTED_SYSTEM_LANGUAGES
)
_LANGUAGES_BY_LOCALE = {item.locale: item for item in SUPPORTED_SYSTEM_LANGUAGES}


def language_ui(locale: str, section: str) -> dict[str, str]:
    """Optional per-language UI text resources (loaded only once per process).

    Source sections: installer, installer_dynamic, parent, parent_constants,
    parent_audio_presets, launcher_feedback, collections, discoveries.
    Unknown keys/sections never become executable format or filesystem paths.
    """
    try:
        canonical = str(LocaleTag.parse(locale))
    except LocalizationError:
        return {}
    if canonical not in _LANGUAGES_BY_LOCALE:
        return {}
    return _language_ui_cached(canonical).get(section, {})


@lru_cache(maxsize=MAX_SYSTEM_LANGUAGES)
def _language_ui_cached(locale: str) -> dict[str, dict[str, str]]:
    path = LANGUAGE_ROOT / locale / "ui.json"
    if not path.is_file() or path.is_symlink():
        return {}
    try:
        if path.stat().st_size > 256 * 1024:
            raise ValueError("oversized language UI catalog")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ValueError("invalid schema")
        result: dict[str, dict[str, str]] = {}
        for section, mapping in data.items():
            if section == "schema_version":
                continue
            if not isinstance(section, str) or not isinstance(mapping, dict):
                raise ValueError("section must be a string-to-string map")
            if any(not isinstance(key, str) or not isinstance(value, str)
                   or len(key) > 160 or len(value) > 8192
                   for key, value in mapping.items()):
                raise ValueError("invalid UI string or key")
            result[section] = mapping
        return result
    except (OSError, ValueError, UnicodeError) as exc:
        raise SystemLanguageError(f"invalid language UI catalog {path}: {exc}") from exc


def system_language(locale: str | LocaleTag) -> SystemLanguage:
    """Resolve one supported locale without accepting arbitrary host locales."""

    try:
        canonical = str(locale if isinstance(locale, LocaleTag) else LocaleTag.parse(locale))
    except LocalizationError as exc:
        raise SystemLanguageError(str(exc)) from exc
    try:
        return _LANGUAGES_BY_LOCALE[canonical]
    except KeyError as exc:
        raise SystemLanguageError(f"unsupported Greia system language: {canonical}") from exc


class SystemLanguageStore:
    """Small atomic device-language store with installer-record bootstrap.

    The installer already records its selected locale in
    ``/etc/greia-os/install-record.json``. Until a parent changes the language,
    that immutable install fact is the initial device default. A later change
    creates ``language.json`` in the Greia system-settings state directory and
    overrides the install-time value without rewriting installation evidence.
    """

    def __init__(
        self,
        state_dir: Path,
        *,
        install_record_path: Path = DEFAULT_INSTALL_RECORD,
    ) -> None:
        self.state_dir = Path(state_dir)
        self.path = self.state_dir / "language.json"
        self.install_record_path = Path(install_record_path)

    @classmethod
    def from_environment(cls) -> "SystemLanguageStore":
        return cls(
            Path(os.environ.get("GREIA_SYSTEM_SETTINGS_DIR", str(DEFAULT_STATE_DIR))),
            install_record_path=Path(
                os.environ.get("GREIA_INSTALL_RECORD", str(DEFAULT_INSTALL_RECORD))
            ),
        )

    def read(self) -> SystemLanguage:
        stored = self._read_state_locale()
        if stored is not None:
            return stored
        installed = self._read_install_locale()
        if installed is not None:
            return installed
        return system_language(DEFAULT_SYSTEM_LOCALE)

    def replace(self, locale: str | LocaleTag) -> SystemLanguage:
        selected = system_language(locale)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        payload = {
            "schema_version": SCHEMA_VERSION,
            "locale": selected.locale,
        }
        try:
            temporary.write_text(
                json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            os.chmod(temporary, 0o660)
            temporary.replace(self.path)
            os.chmod(self.path, 0o660)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise
        return selected

    def as_json_dict(self) -> dict[str, object]:
        selected = self.read()
        return {
            "schema_version": SCHEMA_VERSION,
            "locale": selected.locale,
            "selected": selected.as_json_dict(),
            "languages": [item.as_json_dict() for item in SUPPORTED_SYSTEM_LANGUAGES],
        }

    def _read_state_locale(self) -> SystemLanguage | None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
            return None
        locale = raw.get("locale")
        if not isinstance(locale, str):
            return None
        try:
            return system_language(locale)
        except SystemLanguageError:
            return None

    def _read_install_locale(self) -> SystemLanguage | None:
        try:
            raw = json.loads(self.install_record_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        locale = raw.get("locale")
        if not isinstance(locale, str):
            return None
        try:
            return system_language(locale)
        except SystemLanguageError:
            return None


def resolve_device_locale(
    environ: Mapping[str, str] | None = None,
    *,
    store: "SystemLanguageStore | None" = None,
) -> str:
    """Return the Greia device-default UI locale (single source of truth).

    An explicit ``GREIA_DEVICE_LOCALE`` launch value (simulator, test harness,
    supervisor-injected Activity environment) wins when it names a released
    language. Otherwise the persisted device language is read: the parent's
    choice in ``language.json`` or, before any change, the installer's choice in
    the install record. Anything unreadable or retired falls back to
    ``DEFAULT_SYSTEM_LOCALE``. Never guesses a language from Linux ``LANG``.
    """

    env = os.environ if environ is None else environ
    explicit = (env.get("GREIA_DEVICE_LOCALE") or "").strip()
    if explicit:
        try:
            return system_language(explicit).locale
        except SystemLanguageError:
            pass
    try:
        return (store or SystemLanguageStore.from_environment()).read().locale
    except (SystemLanguageError, OSError, ValueError):
        return DEFAULT_SYSTEM_LOCALE


def resolve_child_locale(
    profile_locale: str | None = None,
    environ: Mapping[str, str] | None = None,
    *,
    store: "SystemLanguageStore | None" = None,
) -> str:
    """Return the child's effective UI locale: profile override, then device.

    ``profile_locale`` (a profile's own override) or an explicit
    ``GREIA_PROFILE_LOCALE`` win when they name a released language; otherwise
    :func:`resolve_device_locale` applies.
    """

    env = os.environ if environ is None else environ
    for candidate in (profile_locale, env.get("GREIA_PROFILE_LOCALE")):
        value = (candidate or "").strip()
        if not value:
            continue
        try:
            return system_language(value).locale
        except SystemLanguageError:
            continue
    return resolve_device_locale(env, store=store)


class CachedDeviceLocale:
    """Tiny time-bounded cache of :func:`resolve_device_locale` for render loops.

    The Shell asks for its language every frame; re-reading two small JSON
    files that often is wasteful on the Acer floor. A parent's change is
    picked up within ``ttl_seconds``.
    """

    def __init__(self, ttl_seconds: float = 2.0, *, clock=time.monotonic) -> None:
        self._ttl = float(ttl_seconds)
        self._clock = clock
        self._value: str | None = None
        self._read_at = 0.0

    def get(self) -> str:
        now = self._clock()
        if self._value is None or now - self._read_at >= self._ttl:
            self._value = resolve_device_locale()
            self._read_at = now
        return self._value

    def invalidate(self) -> None:
        self._value = None


class SystemLanguageService:
    """Typed language mutation surface for Greia-owned parent UI.

    The network Parent service normally owns the system-settings directory and
    can write directly. The child launcher intentionally cannot; its hidden,
    authenticated Parent panel falls back to one tightly scoped root helper
    which accepts only a supported locale. No generic shell/root API is exposed.
    """

    def __init__(
        self,
        store: SystemLanguageStore,
        *,
        privileged_helper: Path = DEFAULT_PRIVILEGED_HELPER,
    ) -> None:
        self.store = store
        self.privileged_helper = Path(privileged_helper)

    @classmethod
    def from_environment(cls) -> "SystemLanguageService":
        return cls(
            SystemLanguageStore.from_environment(),
            privileged_helper=Path(
                os.environ.get(
                    "GREIA_LANGUAGE_HELPER",
                    str(DEFAULT_PRIVILEGED_HELPER),
                )
            ),
        )

    def read(self) -> SystemLanguage:
        return self.store.read()

    def set(self, locale: str | LocaleTag) -> SystemLanguage:
        selected = system_language(locale)
        try:
            return self.store.replace(selected.locale)
        except PermissionError:
            pass
        except OSError as exc:
            # EACCES/EROFS commonly arrive as subclasses other than a bare
            # PermissionError on older systems. A missing/unwritable state path
            # may use the narrow helper; other helper failures remain explicit.
            if not self.privileged_helper.is_file():
                raise SystemLanguageError(f"could not save Greia language: {exc}") from exc
        if not self.privileged_helper.is_file() or not os.access(
            self.privileged_helper, os.X_OK
        ):
            raise SystemLanguageError("Greia language helper is unavailable")
        try:
            completed = subprocess.run(
                ["sudo", "-n", str(self.privileged_helper), "set", selected.locale],
                check=False,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10.0,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise SystemLanguageError("Greia language helper could not run") from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip() or "language helper rejected the change"
            raise SystemLanguageError(detail)
        return self.store.read()


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Greia narrow device-language helper")
    subparsers = parser.add_subparsers(dest="command", required=True)
    set_parser = subparsers.add_parser("set")
    set_parser.add_argument("locale")
    args = parser.parse_args(argv)
    if os.geteuid() != 0:
        raise SystemExit("greia-languagectl must run as root")
    if args.command == "set":
        selected = SystemLanguageStore.from_environment().replace(args.locale)
        print(selected.locale)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
