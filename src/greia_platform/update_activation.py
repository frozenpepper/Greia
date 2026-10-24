"""Mounted-state checks and the explicit profile-picker update restart.

The restart path is intentionally narrow: it reuses the shared
``ActiveProfileSession`` lock, rechecks the staged journal and attached boot
backend, arms the existing one-shot selector, records a volatile fence, then
asks systemd for one bounded reboot. Parent supplies no command or selector.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from .profiles import ActiveProfileSession, ProfileError


PERSIST_MOUNTPOINT = Path("/run/greia-persist")
GREIA_OS_STATE_MOUNTPOINT = Path("/var/lib/greia-os")
BOOT_CONTROL_MOUNTPOINT = Path("/boot")
PERSIST_SCHEMA_MARKER = PERSIST_MOUNTPOINT / "greia" / "persist-schema.json"
DEFAULT_RESTART_FENCE = Path("/run/greia-update-authority/restart-pending.json")
DEFAULT_ACTIVE_PROFILE_STATUS = Path("/run/greia-os/active-profile.json")
MAX_RESTART_FENCE_BYTES = 512
_REQUEST_ID = re.compile(r"^[0-9a-f]{32}$")


class UpdateActivationError(RuntimeError):
    """A required mounted-state or restart precondition is not authoritative."""


@dataclass(frozen=True, slots=True)
class MountRecord:
    major_minor: str
    root: str
    mountpoint: str


class RuntimeMountProbe:
    """Read-only verification that a Greia mount is backed by its UUID."""

    def __init__(
        self,
        *,
        mountinfo_path: Path = Path("/proc/self/mountinfo"),
        device_uuid_root: Path = Path("/dev/disk/by-uuid"),
    ) -> None:
        self.mountinfo_path = Path(mountinfo_path)
        self.device_uuid_root = Path(device_uuid_root)

    def mounted_uuid_matches(
        self,
        mountpoint: Path,
        filesystem_uuid: str,
        *,
        expected_mount_root: str | None = None,
    ) -> bool:
        """Require one exact mount and matching UUID-backed block identity."""
        records = self._mounts_at(mountpoint)
        if len(records) != 1:
            return False
        record = records[0]
        if expected_mount_root is not None and record.root != expected_mount_root:
            return False
        try:
            device = os.stat(self.device_uuid_root / filesystem_uuid)
        except OSError:
            return False
        if not stat.S_ISBLK(device.st_mode):
            return False
        try:
            from os import major, minor

            return record.major_minor == f"{major(device.st_rdev)}:{minor(device.st_rdev)}"
        except (AttributeError, ValueError):  # pragma: no cover - Linux deployment
            return False

    def mounted_device_matches(self, left: Path, right: Path) -> bool:
        """Require both exact mountpoints to resolve to the same filesystem."""
        left_records = self._mounts_at(left)
        right_records = self._mounts_at(right)
        return (
            len(left_records) == 1
            and len(right_records) == 1
            and left_records[0].major_minor == right_records[0].major_minor
        )

    def _mounts_at(self, mountpoint: Path) -> list[MountRecord]:
        wanted = str(Path(os.path.abspath(mountpoint)))
        try:
            lines = self.mountinfo_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        found: list[MountRecord] = []
        for line in lines:
            fields = line.split()
            try:
                separator = fields.index("-")
                major_minor = fields[2]
                root = _unescape_mount_field(fields[3])
                actual_mountpoint = _unescape_mount_field(fields[4])
            except (ValueError, IndexError):
                continue
            if separator + 2 >= len(fields) or not re.fullmatch(r"\d+:\d+", major_minor):
                continue
            if actual_mountpoint == wanted:
                found.append(MountRecord(major_minor, root, actual_mountpoint))
        return found


def _unescape_mount_field(value: str) -> str:
    return (
        value.replace(r"\040", " ")
        .replace(r"\011", "\t")
        .replace(r"\012", "\n")
        .replace(r"\134", "\\")
    )


def read_restart_fence(path: Path) -> dict[str, str] | None:
    """Read the small root-owned volatile restart handoff record, if any."""
    candidate = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise UpdateActivationError("restart handoff state is unreadable") from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise UpdateActivationError("restart handoff state is invalid")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            raw = handle.read(MAX_RESTART_FENCE_BYTES + 1)
    except OSError as exc:
        raise UpdateActivationError("restart handoff state is unreadable") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(raw) > MAX_RESTART_FENCE_BYTES:
        raise UpdateActivationError("restart handoff state exceeds Greia bounds")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateActivationError("restart handoff state is invalid") from exc
    if (
        not isinstance(value, dict)
        or set(value) != {"request_id", "schema", "state"}
        or isinstance(value.get("schema"), bool)
        or value.get("schema") != 1
        or not isinstance(value.get("request_id"), str)
        or not _REQUEST_ID.fullmatch(value["request_id"])
        or value.get("state") not in {"handoff_pending", "systemd_accepted"}
    ):
        raise UpdateActivationError("restart handoff state is invalid")
    return {
        "request_id": value["request_id"],
        "state": value["state"],
    }


def write_restart_fence(path: Path, request_id: str, state: str) -> None:
    """Atomically publish the active restart fence while holding profile lock."""
    if not _REQUEST_ID.fullmatch(request_id) or state not in {
        "handoff_pending",
        "systemd_accepted",
    }:
        raise UpdateActivationError("restart handoff state is invalid")
    candidate = Path(path)
    if candidate.parent.is_symlink() or not candidate.parent.is_dir():
        raise UpdateActivationError("restart handoff directory is unavailable")
    payload = (
        json.dumps(
            {"request_id": request_id, "schema": 1, "state": state},
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("ascii")
    temporary = candidate.with_name(f".{candidate.name}.{request_id}.tmp")
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        # A prior process may have died between writing and renaming. The
        # request is serialized by the profile lock, so this request may
        # safely remove only its own request-id-scoped temporary file.
        temporary.unlink(missing_ok=True)
        descriptor = os.open(temporary, flags, 0o644)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, candidate)
        directory_fd = os.open(candidate.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise UpdateActivationError("restart handoff state could not be recorded") from exc


def clear_restart_fence(path: Path) -> None:
    """Remove the fence only when systemd definitively refused its job."""
    candidate = Path(path)
    try:
        candidate.unlink(missing_ok=True)
        directory_fd = os.open(candidate.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        raise UpdateActivationError("restart refusal could not clear its profile fence") from exc


def request_profile_picker_restart(
    *,
    session: ActiveProfileSession,
    fence_path: Path,
    recheck: Callable[[], Mapping[str, object]],
    arm_candidate: Callable[[], Mapping[str, object]],
    reboot_handoff: Callable[[], subprocess.CompletedProcess[bytes]] | None = None,
    request_id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
) -> dict[str, object]:
    """Recheck, arm and request one reboot while profile activation is fenced."""
    try:
        with session.profile_picker_restart_guard():
            ready = dict(recheck())
            if ready.get("ready") is not True:
                return _refused(str(ready.get("reason") or "restart preconditions are unavailable"))
            journal_state = ready.get("journal_state")
            if journal_state not in {"update_staged", "one_shot_armed"}:
                return _refused("no validated staged update is ready to restart")
            existing = read_restart_fence(fence_path)
            if existing is not None and existing["state"] == "systemd_accepted":
                return {
                    "status": "RESTART_ACCEPTED",
                    "request_id": existing["request_id"],
                    "state": existing["state"],
                }
            request_id = existing["request_id"] if existing else request_id_factory()
            if not _REQUEST_ID.fullmatch(request_id):
                return _refused("restart request identity is invalid")
            # The shared lock remains held from the idle proof through arm,
            # fence publication and reboot request. Publish only after a
            # confirmed arm so a rejected arm does not strand the picker.
            is_new_request = existing is None
            if journal_state == "update_staged":
                try:
                    arm_result = dict(arm_candidate())
                except Exception as exc:
                    return _refused(
                        f"candidate arm failed: {exc}",
                        state="handoff_pending" if existing else "update_staged",
                        request_id=request_id if is_new_request or existing else None,
                    )
                if arm_result.get("armed") is not True:
                    return _refused(
                        "candidate arm was not confirmed",
                        state="handoff_pending" if existing else "update_staged",
                        request_id=request_id if is_new_request or existing else None,
                    )
            handoff = reboot_handoff or _systemd_reboot_handoff
            if is_new_request:
                write_restart_fence(fence_path, request_id, "handoff_pending")
            try:
                result = handoff()
            except (OSError, subprocess.TimeoutExpired):
                # The reboot may have been queued before a timeout. Keep the
                # fence and allow an explicit retry from the still-idle picker.
                return _refused(
                    "reboot handoff result is unknown; profile selection remains paused",
                    state="handoff_pending",
                    request_id=request_id,
                )
            if result.returncode != 0:
                clear_restart_fence(fence_path)
                return _refused(
                    "systemd refused the reboot request",
                    state="one_shot_armed",
                    request_id=request_id,
                )
            try:
                write_restart_fence(fence_path, request_id, "systemd_accepted")
            except UpdateActivationError:
                # The handoff already returned success; keep the earlier
                # pending record as the session fence and report acceptance.
                pass
            return {
                "status": "RESTART_ACCEPTED",
                "request_id": request_id,
                "state": "systemd_accepted",
            }
    except ProfileError as exc:
        return _refused(str(exc))
    except UpdateActivationError as exc:
        return _refused(str(exc), state="one_shot_armed")


def _systemd_reboot_handoff() -> subprocess.CompletedProcess[bytes]:
    """Ask systemd to queue a normal reboot through its local control socket."""
    return subprocess.run(
        ["/usr/bin/systemctl", "--no-block", "reboot"],
        check=False,
        shell=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=8.0,
    )


def _refused(
    reason: str,
    *,
    state: str = "refused",
    request_id: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": "REFUSED",
        "reason": reason[:256],
        "state": state[:64],
    }
    if request_id is not None:
        payload["request_id"] = request_id
    return payload


class InstalledUpdateActivation:
    """Compose installed readiness facts and safe restart around one authority.

    The existing update service remains the owner of candidate verification,
    slot writing, journal and boot-control mutations. This collaborator only
    reads their authoritative state and coordinates the idle-picker restart.
    """

    def __init__(self, authority: object) -> None:
        self.authority = authority

    def __getattr__(self, name: str) -> object:
        return getattr(self.authority, name)

    def status_payload(self) -> dict[str, object]:
        """Return bounded installed identity and update readiness facts.

        Backend availability, layout presence, PERSIST readability and
        activation readiness are separate facts. A/B layout alone never
        makes a device ready: installed acceptance, attached boot control,
        the mounted expected PERSIST and its schema marker must all agree.
        """
        from .boot_transaction import BootTransactionState
        from .persistent_layout import (
            PersistentLayoutError,
            parse_persist_schema_marker,
            read_persist_schema_marker,
        )
        from .system_updates import (
            MIN_INBOX_FREE_BYTES,
            SystemUpdateError,
            UpdateLayoutError,
            load_installed_layout_record,
            load_installed_release_identity,
        )
        reasons: list[str] = []
        record = None
        layout_error = ""
        try:
            record = load_installed_layout_record(self._backend_layout_path())
        except UpdateLayoutError as exc:
            layout_error = str(exc)
        is_ab = record is not None and record.system_b is not None
        if not is_ab:
            layout: dict[str, object] = {
                "single_root": True,
                "slots": ["A"],
                "active_slot": None,
                "accepted_slot": None,
            }
            reasons.append(layout_error or "installed A/B layout is unavailable")
        else:
            layout = {
                "single_root": False,
                "slots": ["A", "B"],
                "active_slot": record.boot_control.active_slot,
                "accepted_slot": record.accepted_slot,
            }

        release: dict[str, object] | None = None
        identity_error = ""
        try:
            release = load_installed_release_identity()
        except UpdateLayoutError as exc:
            identity_error = str(exc)
        current_slot = (
            release.get("slot") if isinstance(release, dict) else None
        )
        current_release_id = (
            release.get("release_id") if isinstance(release, dict) else None
        )
        if not isinstance(current_slot, str) and record is not None:
            current_slot = record.boot_control.active_slot
        if not isinstance(current_release_id, str) and record is not None:
            current_release_id = record.accepted_release_id
        if not isinstance(current_slot, str):
            current_slot = "unknown"
        if not isinstance(current_release_id, str):
            current_release_id = "unknown"
        identity: dict[str, object] = {
            "version": self.identity.version,
            "release_id": current_release_id,
            "profile": self.identity.profile,
            "platform_family": self.identity.platform_family,
            "architecture": self.identity.architecture,
            "board": self.identity.board,
            "current_slot": current_slot,
        }
        if identity_error:
            reasons.append(identity_error)
        identity_known = all(
            isinstance(identity.get(key), str)
            and bool(identity.get(key))
            and identity.get(key) != "unknown"
            for key in (
                "version",
                "release_id",
                "profile",
                "platform_family",
                "architecture",
                "current_slot",
            )
        )
        board = identity.get("board")
        board_known = board is None or (
            isinstance(board, str) and bool(board) and len(board) <= 64
        )
        identity_known = identity_known and board_known
        if not identity_known:
            reasons.append("installed release identity is incomplete")
        identity_layout_matches = True
        if record is not None and is_ab:
            if (
                current_slot != record.accepted_slot
                or current_slot != record.boot_control.active_slot
                or current_release_id != record.accepted_release_id
            ):
                identity_layout_matches = False
                reasons.append("installed identity does not match the accepted slot")

        try:
            candidate = self.candidate_summary()
            candidate_payload = {
                "present": candidate.present,
                "release_id": candidate.release_id,
                "bundle_sha256": candidate.bundle_sha256,
            }
        except Exception as exc:
            candidate_payload = {
                "present": False,
                "release_id": "",
                "bundle_sha256": "",
            }
            reasons.append(f"update candidate state is unavailable: {exc}")

        journal: dict[str, object] = {
            "state": "none",
            "release_id": "",
            "trial_slot": None,
            "decision": "none",
        }
        journal_error = ""
        journal_record = None
        loader = getattr(self.backend, "_load_journal", None)
        if callable(loader):
            try:
                journal_record = loader()
            except SystemUpdateError as exc:
                journal_error = str(exc)
        else:
            journal_error = "update journal authority is unavailable"
        if journal_error:
            journal["state"] = "unavailable"
            journal["decision"] = "unavailable"
            reasons.append(journal_error)
        elif journal_record is not None:
            transitions = getattr(journal_record, "transitions", ())
            last_transition = transitions[-1] if transitions else None
            decision = getattr(getattr(last_transition, "state", None), "value", None)
            state_value = getattr(getattr(journal_record, "state", None), "value", "unavailable")
            journal = {
                "state": state_value,
                "release_id": getattr(journal_record, "release_id", ""),
                "trial_slot": getattr(journal_record, "candidate_slot", None),
                "decision": decision or state_value,
            }

        persist: dict[str, object] = {
            "available": False,
            "readable": False,
            "schema": None,
            "readable_min": None,
            "readable_max": None,
            "free_bytes": 0,
        }
        persist_error = "installed PERSIST state is unavailable"
        persist_schema: int | None = None
        mount_probe = RuntimeMountProbe()
        if record is not None:
            uuid_value = record.persist.filesystem_uuid
            root_mounted = mount_probe.mounted_uuid_matches(
                PERSIST_MOUNTPOINT,
                uuid_value,
                expected_mount_root="/",
            )
            state_mounted = mount_probe.mounted_uuid_matches(
                GREIA_OS_STATE_MOUNTPOINT,
                uuid_value,
                expected_mount_root="/greia/namespaces/parent-credentials",
            )
            if root_mounted and state_mounted:
                try:
                    marker_bytes = read_persist_schema_marker(PERSIST_SCHEMA_MARKER)
                    persist_schema = parse_persist_schema_marker(marker_bytes)
                    persist_error = ""
                    free_bytes = shutil.disk_usage(GREIA_OS_STATE_MOUNTPOINT).free
                    persist = {
                        "available": True,
                        "readable": True,
                        "schema": persist_schema,
                        # With no candidate, the installed marker is the
                        # observed readable value; a candidate-specific range
                        # is enforced again before any slot write.
                        "readable_min": persist_schema,
                        "readable_max": persist_schema,
                        "free_bytes": free_bytes,
                    }
                except (OSError, ValueError, PersistentLayoutError, SystemUpdateError) as exc:
                    persist_error = f"installed PERSIST schema marker is unavailable: {exc}"
            else:
                persist_error = "expected PERSIST mount or shared Greia state bind is unavailable"
        if persist_error:
            reasons.append(persist_error)

        backend: dict[str, object] = {
            "available": False,
            "kind": getattr(record, "boot_backend", "unknown") if record else "unknown",
            "reason": "boot-control readiness is unavailable",
        }
        boot_error = ""
        if not is_ab or record is None:
            boot_error = "A/B boot-control layout is unavailable"
        elif not record.accepted_slot or record.boot_control.active_slot != record.accepted_slot:
            boot_error = "accepted boot slot is not authoritative"
        else:
            boot_backend = getattr(self.backend, "boot_backend", None)
            backend_id = getattr(boot_backend, "backend_id", None)
            try:
                from .fstab import read_fstab_uuid_for_mount

                boot_uuid = read_fstab_uuid_for_mount(Path("/etc/fstab"), "/boot")
                boot_mounted = mount_probe.mounted_uuid_matches(
                    BOOT_CONTROL_MOUNTPOINT,
                    boot_uuid,
                    expected_mount_root="/",
                )
            except (OSError, ValueError, ImportError):
                boot_mounted = False
            inspector = getattr(boot_backend, "inspect", None)
            try:
                observed_boot = inspector() if callable(inspector) else None
            except Exception:
                observed_boot = None
            default_slot = getattr(observed_boot, "default_slot", None)
            one_shot_slot = getattr(observed_boot, "one_shot_slot", None)
            expected_one_shot = (
                getattr(journal_record, "candidate_slot", None)
                if getattr(journal_record, "state", None) is BootTransactionState.ONE_SHOT_ARMED
                else None
            )
            if not boot_mounted:
                boot_error = "expected shared boot-control mount is unavailable"
            elif backend_id != record.boot_backend:
                boot_error = "attached boot backend does not match the installed layout"
            elif default_slot != record.accepted_slot:
                boot_error = "boot backend default does not match the accepted slot"
            elif one_shot_slot != expected_one_shot:
                boot_error = "boot backend one-shot state does not match the journal"
            elif journal_error:
                boot_error = journal_error
            elif journal_record is not None and getattr(journal_record, "state", None) not in {
                BootTransactionState.UPDATE_STAGED,
                BootTransactionState.ONE_SHOT_ARMED,
                BootTransactionState.ACCEPTED,
                BootTransactionState.ROLLED_BACK,
                BootTransactionState.FAILED,
            }:
                boot_error = "boot transaction is not in an update-ready state"
            else:
                boot_error = ""
        if boot_error:
            backend["reason"] = boot_error
            reasons.append(boot_error)
        else:
            backend = {
                "available": True,
                "kind": record.boot_backend if record else "unknown",
                "reason": "",
            }

        if persist.get("available") is True and int(persist["free_bytes"]) < MIN_INBOX_FREE_BYTES:
            reasons.append("PERSIST has insufficient free space for a safe update")
        restart_fence_error = False
        try:
            restart_fence = read_restart_fence(
                Path(os.environ.get("GREIA_UPDATE_RESTART_FENCE", str(DEFAULT_RESTART_FENCE)))
            )
        except Exception as exc:
            restart_fence = None
            restart_fence_error = True
            reasons.append(f"restart handoff state is unavailable: {exc}")
        if restart_fence is not None:
            # This is surfaced separately; the root request operation can
            # safely continue an already-pending handoff from the picker.
            pass

        activation_available = bool(
            is_ab
            and identity_known
            and not identity_error
            and not layout_error
            and identity_layout_matches
            and backend.get("available") is True
            and persist.get("available") is True
            and persist.get("readable") is True
            and int(persist.get("free_bytes", 0)) >= MIN_INBOX_FREE_BYTES
            and not journal_error
            and not restart_fence_error
        )
        if journal_record is not None and getattr(journal_record, "state", None) is BootTransactionState.CANDIDATE_BOOTING:
            activation_available = False
            reasons.append("candidate boot is pending health reconciliation")
        activation_reason = "A/B update is ready" if activation_available else (
            reasons[0] if reasons else "Greia update activation is unavailable"
        )

        return {
            "status": "OK",
            "identity": identity,
            "backend": backend,
            "layout": layout,
            "persist": persist,
            "journal": journal,
            "candidate": candidate_payload,
            "activation_available": activation_available,
            "activation_reason": activation_reason[:256],
            "restart_pending": restart_fence is not None,
            "restart_request_id": restart_fence["request_id"] if restart_fence else None,
            "restart_state": restart_fence["state"] if restart_fence else None,
        }

    def request_restart(self) -> dict[str, object]:
        """Explicitly authorize restart of the already-staged candidate."""
        from .update_activation import (
            DEFAULT_ACTIVE_PROFILE_STATUS,
            DEFAULT_RESTART_FENCE,
            request_profile_picker_restart,
        )
        from .profiles import ActiveProfileSession

        session_path = Path(
            os.environ.get("GREIA_ACTIVE_PROFILE_STATUS", str(DEFAULT_ACTIVE_PROFILE_STATUS))
        )
        fence_path = Path(
            os.environ.get("GREIA_UPDATE_RESTART_FENCE", str(DEFAULT_RESTART_FENCE))
        )
        return request_profile_picker_restart(
            session=ActiveProfileSession(session_path),
            fence_path=fence_path,
            recheck=self._restart_preconditions,
            arm_candidate=self.service.arm,
        )

    def _restart_preconditions(self) -> dict[str, object]:
        """Recheck mounted readiness and the staged journal under session lock."""
        from .system_updates import load_installed_layout_record

        status = self.status_payload()
        if status.get("activation_available") is not True:
            return {
                "ready": False,
                "reason": status.get("activation_reason") or "update readiness is unavailable",
            }
        journal_payload = status.get("journal")
        journal_state = (
            journal_payload.get("state") if isinstance(journal_payload, dict) else None
        )
        if journal_state not in {"update_staged", "one_shot_armed"}:
            return {"ready": False, "reason": "no validated staged update is ready to restart"}
        record = load_installed_layout_record(self._backend_layout_path())
        journal_loader = getattr(self.backend, "_load_journal", None)
        journal = journal_loader() if callable(journal_loader) else None
        if record is None or record.system_b is None or journal is None:
            return {"ready": False, "reason": "installed layout or update journal is unavailable"}
        if (
            journal.state.value != journal_state
            or journal.candidate_slot == record.accepted_slot
            or journal.accepted_slot != record.accepted_slot
            or record.boot_control.active_slot != record.accepted_slot
            or not journal.release_id
            or journal.release_id != self._staged_release_id()
        ):
            return {"ready": False, "reason": "staged journal no longer matches the accepted layout"}
        boot_backend = getattr(self.backend, "boot_backend", None)
        inspect_backend = getattr(boot_backend, "inspect", None)
        try:
            observed = inspect_backend() if callable(inspect_backend) else None
        except Exception:
            observed = None
        if (
            getattr(boot_backend, "backend_id", None) != record.boot_backend
            or getattr(observed, "default_slot", None) != record.accepted_slot
            or getattr(observed, "one_shot_slot", None)
            != (journal.candidate_slot if journal_state == "one_shot_armed" else None)
        ):
            return {"ready": False, "reason": "boot-control state does not match the staged journal"}
        return {"ready": True, "journal_state": journal_state}

    def _staged_release_id(self) -> str:
        from .system_updates import SystemUpdateError

        journal_loader = getattr(self.backend, "_load_journal", None)
        try:
            journal = journal_loader() if callable(journal_loader) else None
        except SystemUpdateError:
            return ""
        return getattr(journal, "release_id", "") if journal is not None else ""
