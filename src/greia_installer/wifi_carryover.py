"""Carry the Wi-Fi network joined in the installer over to the installed Greia.

The parent may join a network on the installer's Wi-Fi page. The whole point
of that page is that the installed system then comes up on the same network,
so the network has to survive the install. This module owns that hand-off.

Two halves, split along the installer's privilege boundary (Step 8A.5):

- **UI side (unprivileged).** :func:`carryover_snapshot_fields` turns the
  tested profile the Wi-Fi controller already holds into two non-secret,
  bounded settings scalars: the SSID as lowercase UTF-8 hex and the security
  type (``open``/``psk``). They travel inside ``PREPARE_PLAN``'s settings
  snapshot, so they are part of the canonical, digest-bound plan the parent
  confirms, and the confirm page's "Wi-Fi: <network>" line is the consent.
  The passphrase never crosses the socket; hex keeps arbitrary SSID bytes
  (``/``, ``://``, ``..``) away from the channel's raw-authority scanner and
  away from any path.

- **Root side (privileged install).** :class:`IwdProfileCarryover` copies
  exactly that one network's iwd known-network file from the live system's
  root-only ``/var/lib/iwd`` (iwd wrote it itself when the join succeeded
  through the passphrase agent) into the target's ``/var/lib/iwd`` as
  ``0600 root:root`` inside a ``0700`` directory. Nothing else of the live
  system's network state is read or copied. The file name is derived from the
  validated SSID with iwd's own naming rule, never taken from request bytes.

Copying is best-effort by contract: Wi-Fi is never a prerequisite for a
finished install (``docs/product/INSTALLER_WIFI_SETUP.md``). Every refusal or
I/O failure returns a :class:`WifiCarryoverOutcome` with a short non-secret
reason and is logged; it never raises into the install.
"""

from __future__ import annotations

import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from greia_platform.wifi import (
    IWD_STATE_DIR,
    IwdNetworkProfile,
    WifiSecurity,
    _profile_filename,
    _validate_ssid,
)

#: Settings-snapshot keys carrying the non-secret carry-over choice.
WIFI_SSID_HEX_KEY = "wifi_ssid_hex"
WIFI_SECURITY_KEY = "wifi_security"
WIFI_SNAPSHOT_KEYS = frozenset({WIFI_SSID_HEX_KEY, WIFI_SECURITY_KEY})

#: Upper bound for one iwd known-network file. Real files are a few hundred
#: bytes (passphrase, derived PSK, SAE points); anything larger is not a
#: profile iwd wrote for a household network and is not copied.
MAX_PROFILE_BYTES = 8 * 1024

#: Target-relative iwd state directory (``/var/lib/iwd`` on the installed root).
TARGET_IWD_RELATIVE = IWD_STATE_DIR.relative_to("/")

_CARRYABLE_SECURITY = {
    WifiSecurity.OPEN.value: WifiSecurity.OPEN,
    WifiSecurity.PERSONAL.value: WifiSecurity.PERSONAL,
}

#: Content written for an open network when the live iwd kept no file for it.
#: Carries no secret, so synthesizing it is equivalent to copying it.
_OPEN_PROFILE_CONTENT = "[Settings]\nAutoConnect=true\n"


class WifiCarryoverError(ValueError):
    """The carry-over choice in a settings snapshot is malformed."""


@dataclass(frozen=True, slots=True)
class WifiCarryoverChoice:
    """The one network the parent joined in this installer session.

    Non-secret by construction: an SSID and a security type. The iwd file
    name is derived here from the validated SSID, so no caller can address a
    path through it.
    """

    ssid: str
    security: WifiSecurity

    def __post_init__(self) -> None:
        _validate_ssid(self.ssid)
        if self.security not in (WifiSecurity.OPEN, WifiSecurity.PERSONAL):
            raise WifiCarryoverError("only open or Personal Wi-Fi can be carried over")

    @property
    def filename(self) -> str:
        """iwd's own known-network file name for this SSID (one basename)."""
        name = _profile_filename(self.ssid, self.security)
        if Path(name).name != name or name in {".", ".."} or "/" in name:
            raise WifiCarryoverError("derived iwd profile name is not a basename")
        return name

    def snapshot_fields(self) -> dict[str, str]:
        """Render the bounded settings scalars sent with ``PREPARE_PLAN``."""
        return {
            WIFI_SSID_HEX_KEY: self.ssid.encode("utf-8").hex(),
            WIFI_SECURITY_KEY: self.security.value,
        }

    @classmethod
    def from_profile(cls, profile: IwdNetworkProfile) -> "WifiCarryoverChoice":
        """Derive the choice from the tested profile the UI controller holds."""
        if profile.filename.endswith(".psk"):
            security = WifiSecurity.PERSONAL
        elif profile.filename.endswith(".open"):
            security = WifiSecurity.OPEN
        else:
            raise WifiCarryoverError("only open or Personal Wi-Fi can be carried over")
        return cls(profile.ssid, security)

    @classmethod
    def from_snapshot(
        cls, snapshot: Mapping[str, object]
    ) -> "WifiCarryoverChoice | None":
        """Parse the choice from a settings snapshot; ``None`` when absent.

        Both keys or neither: a half-present choice is malformed and refused,
        so a plan can never be confirmed with a network the root side would
        then silently drop.
        """
        present = WIFI_SNAPSHOT_KEYS & set(snapshot)
        if not present:
            return None
        if present != WIFI_SNAPSHOT_KEYS:
            raise WifiCarryoverError("Wi-Fi carry-over needs both network and security")
        raw_hex = snapshot.get(WIFI_SSID_HEX_KEY)
        raw_security = snapshot.get(WIFI_SECURITY_KEY)
        if not isinstance(raw_hex, str) or not isinstance(raw_security, str):
            raise WifiCarryoverError("Wi-Fi carry-over values must be text")
        if (
            not 2 <= len(raw_hex) <= 64
            or len(raw_hex) % 2
            or any(ch not in "0123456789abcdef" for ch in raw_hex)
        ):
            raise WifiCarryoverError("Wi-Fi network name is outside Greia bounds")
        try:
            ssid = bytes.fromhex(raw_hex).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise WifiCarryoverError("Wi-Fi network name is not UTF-8") from exc
        security = _CARRYABLE_SECURITY.get(raw_security)
        if security is None:
            raise WifiCarryoverError("Wi-Fi security cannot be carried over")
        try:
            return cls(ssid, security)
        except (TypeError, ValueError) as exc:
            raise WifiCarryoverError(str(exc) or "Wi-Fi network is invalid") from exc


def carryover_snapshot_fields(profile: IwdNetworkProfile | None) -> dict[str, str]:
    """UI helper: snapshot scalars for the joined network, or ``{}``.

    Called with the Wi-Fi controller's tested profile (``None`` when the
    parent skipped Wi-Fi or no adapter exists). Only the SSID and security
    leave the UI; the profile content (passphrase) never does.
    """
    if profile is None:
        return {}
    try:
        return WifiCarryoverChoice.from_profile(profile).snapshot_fields()
    except (TypeError, ValueError):
        return {}


@dataclass(frozen=True, slots=True)
class WifiCarryoverOutcome:
    """Result of one carry-over attempt; ``reason`` is short and non-secret."""

    copied: bool
    reason: str
    security: str = ""


def _default_log(event: str, **fields: object) -> None:
    parts = [f"greia-install-tx: {event}"]
    for key in sorted(fields):
        text = str(fields[key]).replace("\r", " ").replace("\n", " ")[:128]
        parts.append(f"{key}={text}")
    try:
        print(" ".join(parts), file=sys.stderr, flush=True)
    except (OSError, ValueError):
        return


class IwdProfileCarryover:
    """Root-side copier: one live iwd known network -> target iwd state.

    ``source_dir`` is the live system's iwd state directory and ``trusted_uid``
    the only owner accepted for it and the profile (root in production; the
    test user in the unit suite). ``target_owner`` is the ``(uid, gid)``
    applied to the written directory and file; ``None`` means "root:root when
    running as root, otherwise leave ownership alone" so unprivileged tests
    still prove modes. ``log`` receives one bounded event per attempt and
    never sees the SSID or the profile content.
    """

    def __init__(
        self,
        *,
        source_dir: Path = IWD_STATE_DIR,
        trusted_uid: int | None = None,
        target_owner: tuple[int, int] | None = None,
        max_bytes: int = MAX_PROFILE_BYTES,
        log: Callable[..., None] | None = None,
    ) -> None:
        self.source_dir = Path(source_dir)
        self.trusted_uid = os.geteuid() if trusted_uid is None else int(trusted_uid)
        if target_owner is None and os.geteuid() == 0:
            target_owner = (0, 0)
        self.target_owner = target_owner
        self.max_bytes = max(1, min(int(max_bytes), 64 * 1024))
        self._log = log or _default_log

    # -- public ------------------------------------------------------------

    def carry_over(
        self, choice: WifiCarryoverChoice | None, target_root: Path
    ) -> WifiCarryoverOutcome:
        """Copy the chosen network into ``target_root``; never raises."""
        if choice is None:
            return WifiCarryoverOutcome(False, "no-network-chosen")
        security = choice.security.value
        try:
            outcome = self._carry_over(choice, Path(target_root))
        except Exception as exc:  # best-effort by contract
            outcome = WifiCarryoverOutcome(
                False, f"failed:{type(exc).__name__}", security
            )
        self._log(
            "wifi_carryover",
            outcome="copied" if outcome.copied else "skipped",
            reason=outcome.reason,
            security=security,
        )
        return outcome

    # -- internals ---------------------------------------------------------

    def _carry_over(
        self, choice: WifiCarryoverChoice, target_root: Path
    ) -> WifiCarryoverOutcome:
        security = choice.security.value
        name = choice.filename
        content, how = self._read_source(choice, name)
        if content is None:
            return WifiCarryoverOutcome(False, how, security)
        reason = self._write_target(target_root, name, content)
        if reason is not None:
            return WifiCarryoverOutcome(False, reason, security)
        return WifiCarryoverOutcome(True, how, security)

    def _read_source(
        self, choice: WifiCarryoverChoice, name: str
    ) -> tuple[bytes | None, str]:
        try:
            dir_info = os.lstat(self.source_dir)
        except FileNotFoundError:
            dir_info = None
        if dir_info is not None and (
            not stat.S_ISDIR(dir_info.st_mode)
            or dir_info.st_uid != self.trusted_uid
            or dir_info.st_mode & 0o022
        ):
            return None, "source-unsafe"
        raw: bytes | None = None
        if dir_info is not None:
            raw, problem = self._read_profile_file(self.source_dir / name)
            if problem is not None:
                return None, problem
        if raw is None:
            # iwd keeps a file for open networks too, but an open network has
            # no secret: when none exists, the equivalent profile is written.
            if choice.security is WifiSecurity.OPEN:
                return _OPEN_PROFILE_CONTENT.encode("ascii"), "copied-open-default"
            return None, "source-missing"
        if not _looks_like_iwd_profile(raw, choice.security):
            return None, "source-invalid"
        return raw, "copied"

    def _read_profile_file(self, path: Path) -> tuple[bytes | None, str | None]:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        try:
            fd = os.open(path, flags)
        except FileNotFoundError:
            return None, None
        except OSError:
            # ELOOP (a symlink) and everything else: never follow, never copy.
            return None, "source-unsafe"
        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != self.trusted_uid
                or info.st_mode & 0o022
                or info.st_nlink != 1
            ):
                return None, "source-unsafe"
            if info.st_size > self.max_bytes:
                return None, "source-too-large"
            chunks: list[bytes] = []
            remaining = self.max_bytes + 1
            while remaining > 0:
                chunk = os.read(fd, min(4096, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
            if len(data) > self.max_bytes:
                return None, "source-too-large"
            return data, None
        finally:
            os.close(fd)

    def _write_target(self, target_root: Path, name: str, content: bytes) -> str | None:
        root_info = os.lstat(target_root)
        if not stat.S_ISDIR(root_info.st_mode):
            return "target-unsafe"
        # Walk var -> lib -> iwd without following a symlink at any level, so
        # a link planted in the payload can never redirect the write.
        current = target_root
        parts = TARGET_IWD_RELATIVE.parts
        for index, part in enumerate(parts):
            current = current / part
            last = index == len(parts) - 1
            try:
                info = os.lstat(current)
            except FileNotFoundError:
                os.mkdir(current, 0o700 if last else 0o755)
                info = os.lstat(current)
            if not stat.S_ISDIR(info.st_mode):
                return "target-unsafe"
        return self._write_state_dir(current, name, content)

    def carry_over_to_state_dir(self, choice: WifiCarryoverChoice, state_dir: Path) -> WifiCarryoverOutcome:
        """Copy a tested network into a verified, already-created PERSIST namespace."""
        try:
            content, how = self._read_source(choice, choice.filename)
            if content is None:
                outcome = WifiCarryoverOutcome(False, how, choice.security.value)
            else:
                reason = self._write_state_dir(Path(state_dir), choice.filename, content)
                outcome = WifiCarryoverOutcome(reason is None, reason or how, choice.security.value)
        except Exception as exc:
            outcome = WifiCarryoverOutcome(False, f"failed:{type(exc).__name__}", choice.security.value)
        self._log("wifi_carryover", outcome="copied" if outcome.copied else "skipped",
                  reason=outcome.reason, security=choice.security.value)
        return outcome

    def _write_state_dir(self, state_dir: Path, name: str, content: bytes) -> str | None:
        dir_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        dir_fd = os.open(state_dir, dir_flags)
        temporary = f".{name}.greia-carryover.tmp"
        try:
            os.fchmod(dir_fd, 0o700)
            if self.target_owner is not None:
                os.fchown(dir_fd, *self.target_owner)
            try:
                os.unlink(temporary, dir_fd=dir_fd)
            except FileNotFoundError:
                pass
            file_flags = (
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            )
            fd = os.open(temporary, file_flags, 0o600, dir_fd=dir_fd)
            try:
                os.fchmod(fd, 0o600)
                if self.target_owner is not None:
                    os.fchown(fd, *self.target_owner)
                view = memoryview(content)
                while view:
                    written = os.write(fd, view)
                    view = view[written:]
                os.fsync(fd)
            finally:
                os.close(fd)
            os.replace(temporary, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
            try:
                os.fsync(dir_fd)
            except OSError:
                pass
        except OSError:
            try:
                os.unlink(temporary, dir_fd=dir_fd)
            except OSError:
                pass
            return "write-failed"
        finally:
            os.close(dir_fd)
        return None


def _looks_like_iwd_profile(raw: bytes, security: WifiSecurity) -> bool:
    """Shallow shape check of an iwd key file; never inspects secret values."""
    if b"\x00" in raw:
        return False
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    group = ""
    has_secret = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            group = stripped[1:-1]
            continue
        if "=" not in stripped:
            return False
        key = stripped.split("=", 1)[0].strip()
        if group == "Security" and key in {"Passphrase", "PreSharedKey"}:
            has_secret = True
    if security is WifiSecurity.PERSONAL:
        return has_secret
    return True


__all__ = [
    "MAX_PROFILE_BYTES",
    "WIFI_SECURITY_KEY",
    "WIFI_SNAPSHOT_KEYS",
    "WIFI_SSID_HEX_KEY",
    "IwdProfileCarryover",
    "WifiCarryoverChoice",
    "WifiCarryoverError",
    "WifiCarryoverOutcome",
    "carryover_snapshot_fields",
]
