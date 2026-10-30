"""Validation for the appliance GRUB and kernel command-line contract.

The child-visible boot path has one automatic unrestricted menu entry. GRUB
command-line and entry editing are protected by the canonical Greia owner
credential, stored as a PBKDF2 hash, and every kernel line is forced onto the
appropriate console policy.

Two independent facts drive validation:

* ``developer`` -- the image carries the explicit developer-remote marker
  (SSH, ``greia-devctl``). It no longer implies a verbose console by itself.
* the **boot console policy** (:class:`BootConsolePolicy`): ``quiet`` (the
  child-facing appliance path: no kernel/systemd text, no cursor) or
  ``diagnostic`` (tty1 status output kept for hardware recovery). Release
  images are always ``quiet``. Developer images default to ``diagnostic``
  and may declare ``quiet`` (the release-candidate profile does). Both
  policies keep ``panic=0``: a fatal error is never turned into a timed
  reboot loop.

The installed GRUB generator declares the policy it rendered with a
``# greia-boot-console-policy: <policy>`` comment. A quiet developer
configuration may carry one extra owner-restricted (not ``--unrestricted``)
diagnostics entry so a verbose boot stays reachable without editing.
"""

from __future__ import annotations

import argparse
import shlex
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Sequence

from greia_platform.grub_security import GRUB_USER


_LINUX_COMMANDS = {"linux", "linux16", "linuxefi"}

COMMON_REQUIRED_ARGUMENTS = {
    "systemd.crash_shell=no",
    "systemd.crash_chvt=0",
    "consoleblank=0",
}
#: Console arguments that leave the system with *no* console. The kernel maps
#: ``console=null`` (and an empty ``console=``) to the ``ttynull`` driver, which
#: the Debian 686 kernel does not build (``CONFIG_NULL_TTY`` unset). PID 1 then
#: has no stdin/stdout/stderr, live-boot's ``exec 6>&1`` and initramfs-tools'
#: ``exec run-init ... <dev/console`` fail, and the kernel panics before any
#: pixel is drawn (2026-10-17 RC stick froze on the Syslinux banner). Quiet
#: boots silence a real console instead (``console=tty1`` + quiet arguments).
FATAL_CONSOLE_ARGUMENTS = frozenset({"console=null", "console="})

RELEASE_REQUIRED_ARGUMENTS = {
    "quiet",
    "splash",
    "loglevel=0",
    "console=tty1",
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
    # live-boot's Netbase() otherwise writes an ifupdown file into
    # /root/etc/network/interfaces. The Greia live root uses systemd-networkd
    # and has no /etc/network, so it printed "/init: line 29: can't create
    # /root/etc/network/interfaces" on the quiet screen and ran a pointless
    # initramfs `udevadm trigger; udevadm settle`.
    "nonetworking",
    "silent",
    "overlay-size=128M",
}

RELEASE_FORBIDDEN_ARGUMENTS = {
    "console=null",
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



class BootConsolePolicy(str, Enum):
    """What the boot path shows on the console (profile ``boot.console_policy``)."""

    QUIET = "quiet"
    DIAGNOSTIC = "diagnostic"

    @classmethod
    def parse(cls, value: object) -> "BootConsolePolicy":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip())
        except ValueError as exc:
            raise GrubContractError(
                f"unknown boot console policy {value!r}; expected quiet or diagnostic"
            ) from exc

    @property
    def required_arguments(self) -> frozenset[str]:
        if self is BootConsolePolicy.DIAGNOSTIC:
            return frozenset(DEVELOPER_REQUIRED_ARGUMENTS)
        return frozenset(RELEASE_REQUIRED_ARGUMENTS)

    @property
    def forbidden_arguments(self) -> frozenset[str]:
        if self is BootConsolePolicy.DIAGNOSTIC:
            return frozenset(DEVELOPER_FORBIDDEN_ARGUMENTS)
        return frozenset(RELEASE_FORBIDDEN_ARGUMENTS)


#: Comment line the installed GRUB generator emits to declare its policy.
CONSOLE_POLICY_DECLARATION = "# greia-boot-console-policy:"
#: Root-owned image file the generator reads (written by the composer).
CONSOLE_POLICY_FILE = Path("etc/greia-os/boot-console-policy")
#: Stable id of the optional owner-restricted diagnostics entry.
DIAGNOSTIC_ENTRY_ID = "greia-os-diagnostics"


def declared_console_policy(text: str) -> BootConsolePolicy | None:
    """Return the policy declared by a generated GRUB configuration, if any."""

    declared: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith(CONSOLE_POLICY_DECLARATION):
            declared.append(stripped[len(CONSOLE_POLICY_DECLARATION):].strip())
    if not declared:
        return None
    if len(set(declared)) != 1:
        raise GrubContractError(
            f"conflicting boot console policy declarations: {sorted(set(declared))!r}"
        )
    return BootConsolePolicy.parse(declared[0])


def resolve_console_policy(
    text: str,
    *,
    developer: bool,
    console_policy: BootConsolePolicy | str | None = None,
) -> BootConsolePolicy:
    """Resolve the effective console policy for one GRUB configuration.

    Release images (``developer=False``) are always ``quiet``. Developer
    images default to ``diagnostic`` unless the configuration (or the caller)
    declares ``quiet``. An explicit caller policy must agree with any
    declaration in the text, so a build cannot validate the wrong mode.
    """

    declared = declared_console_policy(text)
    requested = None if console_policy is None else BootConsolePolicy.parse(console_policy)
    if requested is not None and declared is not None and requested is not declared:
        raise GrubContractError(
            f"GRUB configuration declares console policy {declared.value!r} "
            f"but {requested.value!r} was required"
        )
    effective = requested or declared
    if not developer:
        if effective is BootConsolePolicy.DIAGNOSTIC:
            raise GrubContractError(
                "a non-developer (release) image must use the quiet console policy"
            )
        return BootConsolePolicy.QUIET
    return effective or BootConsolePolicy.DIAGNOSTIC


def read_root_console_policy(root: Path | str) -> BootConsolePolicy | None:
    """Read ``/etc/greia-os/boot-console-policy`` below an image/target root."""

    path = Path(root) / CONSOLE_POLICY_FILE
    try:
        value = path.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as exc:
        raise GrubContractError(f"cannot read boot console policy {path}: {exc}") from exc
    return BootConsolePolicy.parse(value)


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


@dataclass(frozen=True)
class _MenuEntry:
    line_number: int
    tokens: tuple[str, ...]
    kernel_lines: tuple[KernelCommandLine, ...]

    @property
    def unrestricted(self) -> bool:
        return "--unrestricted" in self.tokens

    @property
    def entry_id(self) -> str | None:
        if "--id" not in self.tokens:
            return None
        marker = self.tokens.index("--id")
        return self.tokens[marker + 1] if marker + 1 < len(self.tokens) else None


def _menu_entries(text: str) -> tuple[list[_MenuEntry], list[str]]:
    """Group kernel command lines under the menuentry that contains them."""

    errors: list[str] = []
    kernels = {line.line_number: line for line in kernel_command_lines(text)}
    entries: list[_MenuEntry] = []
    current: tuple[int, tuple[str, ...]] | None = None
    current_kernels: list[KernelCommandLine] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tokens = _tokens(stripped)
        if tokens and tokens[0] == "submenu":
            errors.append(f"line {line_number}: submenus are forbidden in the appliance boot menu")
        if tokens and tokens[0] == "menuentry":
            if current is not None:
                entries.append(_MenuEntry(current[0], current[1], tuple(current_kernels)))
            current = (line_number, tuple(tokens))
            current_kernels = []
        elif line_number in kernels:
            if current is None:
                errors.append(f"line {line_number}: Linux kernel line outside a menuentry")
            else:
                current_kernels.append(kernels[line_number])
    if current is not None:
        entries.append(_MenuEntry(current[0], current[1], tuple(current_kernels)))
    return entries, errors


def _auth_errors(text: str) -> list[str]:
    errors: list[str] = []
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


def _line_errors(
    line: KernelCommandLine,
    *,
    live_installer: bool,
    developer: bool,
    console_policy: BootConsolePolicy | str | None = None,
) -> list[str]:
    errors: list[str] = []
    args = line.arguments

    # The diagnostic policy keeps the boot observable: status on tty1, and a
    # kernel panic stays on screen (panic=0) so failure state remains
    # observable. The quiet policy (release, and the developer RC) silences
    # the same tty1 console and also never reboots on panic.
    # See docs/engineering/boot/INSTALLED_OS_BOOT_POSTMORTEM.md §16.
    if console_policy is None:
        policy = BootConsolePolicy.DIAGNOSTIC if developer else BootConsolePolicy.QUIET
    else:
        policy = BootConsolePolicy.parse(console_policy)
        if not developer and policy is BootConsolePolicy.DIAGNOSTIC:
            return [
                f"line {line.line_number}: a non-developer (release) image must use "
                "the quiet console policy"
            ]
    required_pool = set(COMMON_REQUIRED_ARGUMENTS) | set(policy.required_arguments)
    profile_forbidden = policy.forbidden_arguments

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
        if argument in FATAL_CONSOLE_ARGUMENTS:
            errors.append(
                f"line {line.line_number}: {argument} leaves the kernel without a "
                "console (no ttynull driver); PID 1 cannot open /dev/console and "
                "the boot panics silently. Use console=tty1 with the quiet arguments"
            )
        elif argument in profile_forbidden:
            mode_name = policy.value
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
    console_policy: BootConsolePolicy | str | None = None,
) -> tuple[KernelCommandLine, ...]:
    """Validate the complete appliance GRUB configuration.

    Exactly one ``--unrestricted`` appliance entry must exist and match the
    effective console policy (:func:`resolve_console_policy`). Only a quiet
    developer image may add one owner-restricted entry with id
    ``greia-os-diagnostics`` whose kernel line follows the diagnostic policy.
    Returns the appliance entry's kernel line(s).
    """

    errors: list[str] = _auth_errors(text)
    try:
        policy = resolve_console_policy(
            text, developer=developer, console_policy=console_policy
        )
    except GrubContractError as exc:
        raise GrubContractError(str(exc)) from None
    entries, structure_errors = _menu_entries(text)
    errors.extend(structure_errors)

    diagnostic_entry_allowed = (
        developer and policy is BootConsolePolicy.QUIET and not live_installer
    )
    appliance = [entry for entry in entries if entry.unrestricted]
    restricted = [entry for entry in entries if not entry.unrestricted]
    if len(appliance) != 1:
        errors.append(f"expected exactly one appliance menuentry; found {len(appliance)}")
    for entry in restricted:
        if not diagnostic_entry_allowed:
            errors.append(
                f"line {entry.line_number}: normal automatic boot entry must be --unrestricted"
            )
        elif entry.entry_id != DIAGNOSTIC_ENTRY_ID:
            errors.append(
                f"line {entry.line_number}: the only restricted entry allowed is "
                f"--id {DIAGNOSTIC_ENTRY_ID}"
            )
    if len(restricted) > 1:
        errors.append(f"at most one owner-restricted diagnostics entry; found {len(restricted)}")
    if appliance and entries and entries[0] is not appliance[0]:
        errors.append("the appliance entry must be the first (default) menuentry")

    lowered = text.casefold()
    if "recovery mode" in lowered:
        errors.append("generated GRUB configuration contains a recovery-mode entry")

    appliance_lines: tuple[KernelCommandLine, ...] = ()
    all_lines = kernel_command_lines(text)
    grouped = sum(len(entry.kernel_lines) for entry in entries)
    if grouped != len(all_lines):
        errors.append("every Linux kernel command line must belong to a menuentry")
    if len(appliance) == 1:
        appliance_lines = appliance[0].kernel_lines
        if len(appliance_lines) != 1:
            errors.append(
                f"expected exactly one Linux kernel command line; found {len(appliance_lines)}"
            )
        for line in appliance_lines:
            errors.extend(
                _line_errors(
                    line,
                    live_installer=live_installer,
                    developer=developer,
                    console_policy=policy,
                )
            )
    for entry in restricted:
        if len(entry.kernel_lines) != 1:
            errors.append(
                f"line {entry.line_number}: diagnostics entry needs exactly one kernel line"
            )
        for line in entry.kernel_lines:
            errors.extend(
                _line_errors(
                    line,
                    live_installer=live_installer,
                    developer=developer,
                    console_policy=BootConsolePolicy.DIAGNOSTIC,
                )
            )

    if errors:
        raise GrubContractError("; ".join(errors))
    return appliance_lines


def validate_kernel_command_line(
    line: KernelCommandLine,
    *,
    live_installer: bool = False,
    developer: bool = False,
    console_policy: BootConsolePolicy | str | None = None,
) -> None:
    """Validate one parsed kernel command line against appliance boot policy.

    Thin public wrapper over the same per-line checks used by
    :func:`validate_grub_text`, so multi-entry (A/B) configurations reuse the
    exact release/developer/live argument contract without copying it.
    Raises :class:`GrubContractError` on the first policy violation set.
    """

    errors = _line_errors(
        line,
        live_installer=live_installer,
        developer=developer,
        console_policy=console_policy,
    )
    if errors:
        raise GrubContractError("; ".join(errors))


def validate_grub_config(
    path: Path | str,
    *,
    live_installer: bool = False,
    developer: bool = False,
    console_policy: BootConsolePolicy | str | None = None,
) -> tuple[KernelCommandLine, ...]:
    config_path = Path(path)
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GrubContractError(f"cannot read generated GRUB configuration: {exc}") from exc
    return validate_grub_text(
        text,
        live_installer=live_installer,
        developer=developer,
        console_policy=console_policy,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a generated GRUB configuration against Greia OS boot policy."
    )
    parser.add_argument("config", type=Path)
    parser.add_argument("--live-installer", action="store_true")
    parser.add_argument(
        "--developer",
        action="store_true",
        help="image carries the developer-remote marker (SSH/greia-devctl)",
    )
    parser.add_argument(
        "--console-policy",
        choices=[policy.value for policy in BootConsolePolicy],
        default=None,
        help=(
            "required console policy (default: quiet for release, the "
            "declared policy or diagnostic for developer images)"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        entries = validate_grub_config(
            args.config,
            live_installer=args.live_installer,
            developer=args.developer,
            console_policy=args.console_policy,
        )
    except GrubContractError as exc:
        print(f"GRUB boot contract failed: {exc}")
        return 1
    print(f"GRUB boot contract passed for {len(entries)} kernel command line(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
