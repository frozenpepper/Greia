"""Validation for the appliance GRUB and kernel command-line contract.

The child-visible boot path has one automatic unrestricted menu entry. GRUB
command-line and entry editing are protected by the canonical Greia owner
credential, stored as a PBKDF2 hash, and every kernel line is forced onto the
appropriate release or developer appliance path.
"""

from __future__ import annotations

import argparse
import shlex
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from greia_platform.grub_security import GRUB_USER


_LINUX_COMMANDS = {"linux", "linux16", "linuxefi"}

COMMON_REQUIRED_ARGUMENTS = {
    "systemd.crash_shell=no",
    "systemd.crash_chvt=0",
    "consoleblank=0",
}
RELEASE_REQUIRED_ARGUMENTS = {
    "quiet",
    "splash",
    "loglevel=0",
    "console=null",
    "panic=0",
    "systemd.show_status=false",
    "rd.systemd.show_status=false",
    "udev.log_priority=3",
    "vt.global_cursor_default=0",
}
DEVELOPER_REQUIRED_ARGUMENTS = {
    "loglevel=4",
    "console=tty1",
    "panic=0",
    "systemd.show_status=true",
    "rd.systemd.show_status=true",
    "udev.log_priority=4",
    "vt.global_cursor_default=1",
}
LIVE_REQUIRED_ARGUMENTS = {
    "boot=live",
    "components",
    "live-media-path=/live",
    "live-media-timeout=15",
    "nopersistence",
    "noeject",
    "silent",
    "overlay-size=128M",
}

RELEASE_FORBIDDEN_ARGUMENTS = {
    "console=tty1",
    "panic=30",
    "panic=5",
    "loglevel=4",
    "systemd.show_status=true",
    "rd.systemd.show_status=true",
    "udev.log_priority=4",
    "vt.global_cursor_default=1",
}
DEVELOPER_FORBIDDEN_ARGUMENTS = {
    "quiet",
    "splash",
    "console=null",
    "panic=5",
    "panic=30",
    "loglevel=0",
    "systemd.show_status=false",
    "rd.systemd.show_status=false",
}

# Compatibility aliases
_REQUIRED_ARGUMENTS = COMMON_REQUIRED_ARGUMENTS | RELEASE_REQUIRED_ARGUMENTS
_LIVE_REQUIRED_ARGUMENTS = LIVE_REQUIRED_ARGUMENTS

_SINGLE_VALUE_PREFIXES = (
    "console=",
    "panic=",
    "loglevel=",
    "systemd.show_status=",
    "rd.systemd.show_status=",
    "systemd.crash_shell=",
    "systemd.crash_chvt=",
    "udev.log_priority=",
    "vt.global_cursor_default=",
    "consoleblank=",
    "boot=",
    "live-media-path=",
    "live-media-timeout=",
    "overlay-size=",
    "greia.live_media_id=",
)
_FORBIDDEN_EXACT_ARGUMENTS = {
    "single",
    "1",
    "S",
    "-s",
    "rescue",
    "emergency",
    "debug",
    "break",
    "nosplash",
    "ignore_loglevel",
    "keep_bootcon",
    "plymouth.enable=0",
    "rd.plymouth=0",
}
_FORBIDDEN_PREFIXES = (
    "break=",
    "rd.break",
    "debug=",
    "init=",
    "earlyprintk",
    "earlycon",
    "systemd.debug_shell",
    "rd.systemd.debug_shell",
    "systemd.run=",
    "rd.systemd.run=",
    "systemd.wants=",
    "rd.systemd.wants=",
    "systemd.unit=rescue",
    "systemd.unit=emergency",
    "rd.systemd.unit=rescue",
    "rd.systemd.unit=emergency",
    "systemd.confirm_spawn",
    "rd.systemd.confirm_spawn",
    "systemd.log_target=console",
    "rd.systemd.log_target=console",
    "systemd.log_level=debug",
    "rd.systemd.log_level=debug",
    "rd.shell",
    "rd.emergency",
    "rd.rescue",
    "live-media=",
    "live-media-uuid=",
)


@dataclass(frozen=True)
class KernelCommandLine:
    line_number: int
    command: str
    kernel_path: str
    arguments: tuple[str, ...]


class GrubContractError(ValueError):
    """Raised when a generated GRUB configuration violates kiosk boot policy."""


def _tokens(line: str) -> list[str]:
    try:
        return shlex.split(line, comments=False, posix=True)
    except ValueError:
        return line.split()


def kernel_command_lines(text: str) -> tuple[KernelCommandLine, ...]:
    lines: list[KernelCommandLine] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tokens = _tokens(stripped)
        if len(tokens) < 2 or tokens[0] not in _LINUX_COMMANDS:
            continue
        lines.append(
            KernelCommandLine(
                line_number=line_number,
                command=tokens[0],
                kernel_path=tokens[1],
                arguments=tuple(tokens[2:]),
            )
        )
    return tuple(lines)


def _menu_errors(text: str) -> list[str]:
    errors: list[str] = []
    menu_lines: list[tuple[int, list[str]]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tokens = _tokens(stripped)
        if tokens and tokens[0] == "submenu":
            errors.append(f"line {line_number}: submenus are forbidden in the appliance boot menu")
        if tokens and tokens[0] == "menuentry":
            menu_lines.append((line_number, tokens))
            if "--unrestricted" not in tokens:
                errors.append(
                    f"line {line_number}: normal automatic boot entry must be --unrestricted"
                )
    if len(menu_lines) != 1:
        errors.append(f"expected exactly one appliance menuentry; found {len(menu_lines)}")

    superuser_double = f'set superusers="{GRUB_USER}"'
    superuser_single = f"set superusers='{GRUB_USER}'"
    if superuser_double not in text and superuser_single not in text:
        errors.append(f"missing GRUB {GRUB_USER} superuser declaration")
    if "export superusers" not in text:
        errors.append("missing exported GRUB superusers variable")
    password_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("password_pbkdf2 ")
    ]
    if len(password_lines) != 1:
        errors.append(f"expected exactly one GRUB PBKDF2 password declaration; found {len(password_lines)}")
    elif not password_lines[0].startswith(f"password_pbkdf2 {GRUB_USER} grub.pbkdf2."):
        errors.append(f"GRUB password must use a {GRUB_USER} PBKDF2 hash declaration")
    return errors


def _line_errors(line: KernelCommandLine, *, live_installer: bool, developer: bool) -> list[str]:
    errors: list[str] = []
    args = line.arguments

    # Developer/test builds deliberately keep the boot observable: a kernel
    # panic prints to tty1 and does not auto-reboot (panic=0) so failure state
    # remains observable. Normal/release builds stay silent and consoleless.
    # See docs/INSTALLED_OS_BOOT_POSTMORTEM.md §16.
    required_pool = set(COMMON_REQUIRED_ARGUMENTS)
    if developer:
        required_pool |= DEVELOPER_REQUIRED_ARGUMENTS
        profile_forbidden = DEVELOPER_FORBIDDEN_ARGUMENTS
    else:
        required_pool |= RELEASE_REQUIRED_ARGUMENTS
        profile_forbidden = RELEASE_FORBIDDEN_ARGUMENTS

    if live_installer:
        required_pool |= LIVE_REQUIRED_ARGUMENTS

    for prefix in _SINGLE_VALUE_PREFIXES:
        matching = [argument for argument in args if argument.startswith(prefix)]
        required = [argument for argument in required_pool if argument.startswith(prefix)]
        if required and matching != required:
            errors.append(
                f"line {line.line_number}: expected exactly {required!r} for {prefix}; found {matching!r}"
            )

    for required in sorted(required_pool):
        if required not in args:
            errors.append(f"line {line.line_number}: missing required argument {required}")

    for argument in args:
        if argument in profile_forbidden:
            mode_name = "developer" if developer else "release"
            errors.append(
                f"line {line.line_number}: forbidden {mode_name} argument {argument}"
            )

    if live_installer:
        media_ids = [
            argument.partition("=")[2]
            for argument in args
            if argument.startswith("greia.live_media_id=")
        ]
        if len(media_ids) != 1:
            errors.append(
                f"line {line.line_number}: expected exactly one greia.live_media_id; found {len(media_ids)}"
            )
        else:
            try:
                normalized_media_id = str(uuid.UUID(media_ids[0]))
            except ValueError:
                errors.append(
                    f"line {line.line_number}: greia.live_media_id must be a valid UUID"
                )
            else:
                if media_ids[0] != normalized_media_id:
                    errors.append(
                        f"line {line.line_number}: greia.live_media_id must use canonical UUID syntax"
                    )
        if "ignore_uuid" in args:
            errors.append(
                f"line {line.line_number}: live installer must not disable media UUID verification"
            )

    for argument in args:
        if argument in _FORBIDDEN_EXACT_ARGUMENTS or any(
            argument.startswith(prefix) for prefix in _FORBIDDEN_PREFIXES
        ):
            errors.append(
                f"line {line.line_number}: forbidden interactive/text/recovery argument {argument}"
            )
    return errors


def validate_grub_text(
    text: str,
    *,
    live_installer: bool = False,
    developer: bool = False,
) -> tuple[KernelCommandLine, ...]:
    """Validate the complete appliance GRUB configuration."""

    entries = kernel_command_lines(text)
    errors: list[str] = _menu_errors(text)
    if len(entries) != 1:
        errors.append(f"expected exactly one Linux kernel command line; found {len(entries)}")

    lowered = text.casefold()
    if "recovery mode" in lowered:
        errors.append("generated GRUB configuration contains a recovery-mode entry")

    for entry in entries:
        errors.extend(_line_errors(entry, live_installer=live_installer, developer=developer))

    if errors:
        raise GrubContractError("; ".join(errors))
    return entries


def validate_kernel_command_line(
    line: KernelCommandLine,
    *,
    live_installer: bool = False,
    developer: bool = False,
) -> None:
    """Validate one parsed kernel command line against appliance boot policy.

    Thin public wrapper over the same per-line checks used by
    :func:`validate_grub_text`, so multi-entry (A/B) configurations reuse the
    exact release/developer/live argument contract without copying it.
    Raises :class:`GrubContractError` on the first policy violation set.
    """

    errors = _line_errors(line, live_installer=live_installer, developer=developer)
    if errors:
        raise GrubContractError("; ".join(errors))


def validate_grub_config(
    path: Path | str,
    *,
    live_installer: bool = False,
    developer: bool = False,
) -> tuple[KernelCommandLine, ...]:
    config_path = Path(path)
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GrubContractError(f"cannot read generated GRUB configuration: {exc}") from exc
    return validate_grub_text(text, live_installer=live_installer, developer=developer)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a generated GRUB configuration against Greia OS boot policy."
    )
    parser.add_argument("config", type=Path)
    parser.add_argument("--live-installer", action="store_true")
    parser.add_argument(
        "--developer",
        action="store_true",
        help="developer/test build: keep boot observable (console=tty1, panic=0)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        entries = validate_grub_config(
            args.config,
            live_installer=args.live_installer,
            developer=args.developer,
        )
    except GrubContractError as exc:
        print(f"GRUB boot contract failed: {exc}")
        return 1
    print(f"GRUB boot contract passed for {len(entries)} kernel command line(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
