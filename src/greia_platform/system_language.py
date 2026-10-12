from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
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


# This is the ONE canonical selectable-language registry for the installer,
# installed Parent panel, privileged helper and Parent API clients. Offering a
# locale is a product support claim, not merely an ability to persist its tag.
# Spanish/French translations are being authored but MUST NOT enter this list
# until text, locale switching, voice inventory and release checks are complete.
# See docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md.
SUPPORTED_SYSTEM_LANGUAGES: tuple[SystemLanguage, ...] = (
    SystemLanguage("en", "English", "English", "🇬🇧"),
    SystemLanguage("it", "Italian", "Italiano", "🇮🇹"),
)
_LANGUAGES_BY_LOCALE = {item.locale: item for item in SUPPORTED_SYSTEM_LANGUAGES}


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
