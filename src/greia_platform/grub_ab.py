"""Stable semantic GRUB A/B entries and the x86 one-shot boot backend.

Step 8B.2 source scope: files only, disposable media only. No valued
physical disk is touched, no Acer mutation (D50), no device contact.

Two responsibilities live here, both driven by semantic slots (``"A"`` /
``"B"``) resolved from the trusted layout record — never by
Parent-supplied boot entries or partition paths:

* :func:`render_grub_ab_config` generates the fixed two-entry ``grub.cfg``
  (``greia-a`` / ``greia-b``) referencing adapter-owned generic
  kernel/initramfs paths and role-owned slot identities. Each entry locates
  its slot filesystem with the documented ``search --fs-uuid`` primitive
  (filesystem UUID) while the kernel/initramfs receives the observed
  ``root=PARTUUID=`` (GPT GUID or MBR ``<disk-signature>-<partno>``) bound
  to the same semantic slot. Routine updates
  never run os-prober or cross-root discovery: every entry is
  self-contained (its own ``search --fs-uuid`` plus its own
  ``root=PARTUUID=`` binding).
* :class:`GrubEnvBackend` implements the x86 :class:`BootTransactionBackend`
  one-shot semantics (``inspect`` / ``arm_one_shot`` /
  ``observe_booted_slot`` / ``commit_accepted`` / ``verify_rollback_ready``
  / ``reconcile``) over stable GRUB state: a 1024-byte ``grubenv``
  environment block carrying ``saved_entry`` (persistent default) and
  ``next_entry`` (candidate-only one-shot), the same variables real GRUB
  honours. The persistent default changes only through the verified commit
  path after the candidate provably booted; a consumed one-shot without a
  health commit leaves the accepted default in place.

Validation reuses the existing contract pools
(:mod:`greia_platform.boot_contract` per-line checks and
:mod:`greia_platform.grub_security` credential shape). There is no new
manager, daemon or parser: menuentry headers are token-checked with
``shlex`` and kernel lines are parsed by the existing
:func:`kernel_command_lines` parser.
"""

from __future__ import annotations

import os
import re
import shlex
import tempfile
import uuid as _uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from greia_platform.boot_contract import (
    COMMON_REQUIRED_ARGUMENTS,
    BootConsolePolicy,
    GrubContractError,
    KernelCommandLine,
    kernel_command_lines,
    validate_kernel_command_line,
)
from greia_platform.boot_transaction import (
    GRUB_ENTRY_NAMES,
    SLOT_INITRAMFS_PATH,
    SLOT_KERNEL_PATH,
    BootArtifactSet,
    BootBackendState,
    BootTransactionError,
    RollbackReadiness,
)
from greia_platform.grub_security import GRUB_USER
from greia_platform.persistent_layout import InstalledLayoutRecord


class GrubAbConfigError(ValueError):
    """A generated or supplied GRUB A/B configuration violates policy."""


# ---------------------------------------------------------------------------
# Small guards (local; boot_transaction owns the backend state machine)
# ---------------------------------------------------------------------------


def _require_slot(value: object, *, field_name: str = "slot") -> str:
    if value not in ("A", "B"):
        raise BootTransactionError(f"{field_name} must be the semantic slot A or B")
    return str(value)


def _require_password_hash(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise GrubAbConfigError("GRUB password hash must be non-empty text")
    if len(value) > 1024:
        raise GrubAbConfigError("GRUB password hash is unexpectedly long")
    if any(char.isspace() for char in value):
        raise GrubAbConfigError("GRUB password hash must be a single token")
    if not value.startswith("grub.pbkdf2."):
        raise GrubAbConfigError("GRUB password hash must use a PBKDF2 declaration")
    return value


def _require_canonical_partuuid(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise GrubAbConfigError(f"{field_name} must be text")
    try:
        parsed = _uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise GrubAbConfigError(f"{field_name} is not a valid UUID") from exc
    if str(parsed) != value.lower():
        raise GrubAbConfigError(f"{field_name} must be canonical lowercase UUID text")
    return str(parsed)


def _require_filesystem_uuid(value: object, *, field_name: str) -> str:
    """Filesystem UUID for the proven ``search --fs-uuid`` locator.

    Filesystem UUIDs are always canonical lowercase UUIDs, on both GPT and
    MBR layouts. The partition-UUID search primitive (``search
    --part-uuid``) is unproven against the shipped GRUB binary (TAKEOVER-1
    T1.2, D52) and is rejected by the validator below.
    """
    return _require_canonical_partuuid(value, field_name=field_name)


def _require_root_partuuid(value: object, *, field_name: str) -> str:
    """Observed ``root=PARTUUID=`` value: GPT GUID or MBR ``<sig>-<NN>``.

    The kernel ABI keeps ``root=PARTUUID=`` for both schemes (T1-IDENT
    observed record): GPT layouts carry a canonical lowercase GUID, MBR
    layouts carry the Linux ``<disk-signature>-<partition-number>`` form
    (e.g. ``1234abcd-02``), never a minted UUID4. Canonicalization matches
    :func:`persistent_layout.normalize_mbr_partuuid` (lowercase signature,
    zero-padded two-digit number).
    """
    if not isinstance(value, str):
        raise GrubAbConfigError(f"{field_name} must be text")
    try:
        return _require_canonical_partuuid(value, field_name=field_name)
    except GrubAbConfigError:
        pass
    text = value.strip()
    if "-" not in text:
        raise GrubAbConfigError(
            f"{field_name} is neither a canonical UUID nor an MBR PARTUUID"
        )
    signature_text, _, number_text = text.rpartition("-")
    signature = signature_text.lower()
    if signature.startswith("0x"):
        signature = signature[2:]
    if not re.fullmatch(r"[0-9a-f]{8}", signature):
        raise GrubAbConfigError(
            f"{field_name} is neither a canonical UUID nor an MBR PARTUUID"
        )
    if not number_text.isascii() or not number_text.isdigit():
        raise GrubAbConfigError(
            f"{field_name} carries an invalid MBR partition number"
        )
    number = int(number_text, 10)
    if not 1 <= number <= 128:
        raise GrubAbConfigError(
            f"{field_name} carries an MBR partition number outside Greia bounds"
        )
    return f"{signature}-{number:02d}"


#: Entry name -> semantic slot (inverse of the adapter-owned GRUB_ENTRY_NAMES).
ENTRY_TO_SLOT = {entry: slot for slot, entry in GRUB_ENTRY_NAMES.items()}

#: Adapter-owned slot-local boot paths rendered with a GRUB-absolute slash.
GRUB_KERNEL_PATH = "/" + SLOT_KERNEL_PATH
GRUB_INITRAMFS_PATH = "/" + SLOT_INITRAMFS_PATH


def _effective_policy(
    developer: bool, console_policy: BootConsolePolicy | str | None
) -> BootConsolePolicy:
    """Console policy for A/B entries; ``developer`` alone keeps today's default.

    Release images are always quiet. A developer image defaults to the
    diagnostic console unless a quiet policy is requested explicitly (the
    release-candidate profile), mirroring :mod:`greia_platform.boot_contract`.
    """
    if console_policy is None:
        return BootConsolePolicy.DIAGNOSTIC if developer else BootConsolePolicy.QUIET
    policy = BootConsolePolicy.parse(console_policy)
    if not developer and policy is BootConsolePolicy.DIAGNOSTIC:
        raise GrubAbConfigError("a release image must use the quiet console policy")
    return policy


def _kernel_arguments(
    *,
    root_partuuid: str,
    developer: bool,
    console_policy: BootConsolePolicy | str | None = None,
) -> tuple[str, ...]:
    """Deterministic kernel arguments for one slot entry (sorted pools)."""
    pool = set(COMMON_REQUIRED_ARGUMENTS)
    pool |= _effective_policy(developer, console_policy).required_arguments
    ordered = sorted(pool)
    # ``quiet`` lowers the console log level to 4; a later ``loglevel=0`` must
    # win over that default. Kernel parameters are applied in order, so a
    # stable alphabetic sort (``loglevel=0`` before ``quiet``) silently made
    # release boots verbose. Keep ``quiet`` first while preserving a
    # deterministic remainder.
    if "quiet" in ordered:
        ordered.remove("quiet")
        ordered.insert(0, "quiet")
    return ("ro", f"root=PARTUUID={root_partuuid}", *ordered)


def _check_artifact_pair(
    artifact_a: object, artifact_b: object,
) -> tuple[BootArtifactSet, BootArtifactSet]:
    if not isinstance(artifact_a, BootArtifactSet):
        raise GrubAbConfigError("slot A facts must be a BootArtifactSet")
    if not isinstance(artifact_b, BootArtifactSet):
        raise GrubAbConfigError("slot B facts must be a BootArtifactSet")
    if artifact_a.slot != "A" or artifact_b.slot != "B":
        raise GrubAbConfigError("artifact slots must be exactly A and B")
    if artifact_a.layout_id != artifact_b.layout_id:
        raise GrubAbConfigError("slot artifacts must share one layout identity")
    if artifact_a.boot_backend != "grub-ab-v1" or artifact_b.boot_backend != "grub-ab-v1":
        raise GrubAbConfigError("GRUB entries exist only on the grub-ab-v1 backend")
    return artifact_a, artifact_b


# ---------------------------------------------------------------------------
# Deterministic A/B grub.cfg generation (no os-prober, no cross-root scan)
# ---------------------------------------------------------------------------


def render_grub_ab_config(
    *,
    artifact_a: BootArtifactSet,
    artifact_b: BootArtifactSet,
    password_hash: str,
    developer: bool = False,
    console_policy: BootConsolePolicy | str | None = None,
) -> str:
    """Render the fixed two-entry GRUB configuration for slots A and B.

    Only semantic artifact sets and the stored PBKDF2 hash are accepted:
    there is deliberately no parameter for a boot entry name, kernel path
    or partition path, so Parent input can never inject boot targets.
    Output is byte-deterministic for identical inputs (sorted pools,
    fixed template).
    """
    slot_a, slot_b = _check_artifact_pair(artifact_a, artifact_b)
    return _render_entries(
        partuuid_a=_require_root_partuuid(
            slot_a.root_partuuid, field_name="slot-A root PARTUUID"
        ),
        fs_uuid_a=_require_filesystem_uuid(
            slot_a.root_filesystem_uuid, field_name="slot-A filesystem UUID"
        ),
        partuuid_b=_require_root_partuuid(
            slot_b.root_partuuid, field_name="slot-B root PARTUUID"
        ),
        fs_uuid_b=_require_filesystem_uuid(
            slot_b.root_filesystem_uuid, field_name="slot-B filesystem UUID"
        ),
        password_hash=password_hash,
        developer=developer,
        console_policy=console_policy,
    )


def render_grub_ab_config_from_record(
    *,
    record: InstalledLayoutRecord,
    password_hash: str,
    developer: bool = False,
    console_policy: BootConsolePolicy | str | None = None,
) -> str:
    """Render the fixed two-entry configuration from the trusted layout record.

    First-install seam for X8-INSTALL: the inactive slot has layout-bound
    root identity but no finalizer receipt (and therefore no
    :class:`BootArtifactSet`) yet. The entry is still emitted pointing at
    the slot's own PARTUUID — selecting it before staging simply fails to
    boot — and one-shot arming to that slot stays gated on candidate
    staging in X8-UPDATE. Only the trusted record and the stored hash are
    accepted; Parent-supplied entries or paths remain inexpressible.
    """
    if not isinstance(record, InstalledLayoutRecord):
        raise GrubAbConfigError("slot roots must come from the trusted layout record")
    if record.boot_backend != "grub-ab-v1":
        raise GrubAbConfigError("GRUB entries exist only on the grub-ab-v1 backend")
    if record.system_b is None:
        raise GrubAbConfigError("single-root layouts carry no GRUB A/B entries")
    # Both identifiers come from the same trusted PartitionIdentity per
    # slot, so the locator/filesystem-UUID and kernel/PARTUUID binding is
    # proven at the record layer (scheme + cross-disk gates in
    # InstalledLayoutRecord.from_dict) and re-checked per entry below.
    return _render_entries(
        partuuid_a=_require_root_partuuid(
            record.system_a.partuuid, field_name="system-a PARTUUID"
        ),
        fs_uuid_a=_require_filesystem_uuid(
            record.system_a.filesystem_uuid,
            field_name="system-a filesystem UUID",
        ),
        partuuid_b=_require_root_partuuid(
            record.system_b.partuuid, field_name="system-b PARTUUID"
        ),
        fs_uuid_b=_require_filesystem_uuid(
            record.system_b.filesystem_uuid,
            field_name="system-b filesystem UUID",
        ),
        password_hash=password_hash,
        developer=developer,
        console_policy=console_policy,
    )


def _render_entries(
    *,
    partuuid_a: str,
    fs_uuid_a: str,
    partuuid_b: str,
    fs_uuid_b: str,
    password_hash: str,
    developer: bool,
    console_policy: BootConsolePolicy | str | None = None,
) -> str:
    """Shared deterministic template: adapter paths plus slot bindings.

    Each slot entry locates its filesystem with the documented
    ``search --fs-uuid`` primitive while booting ``root=PARTUUID=``: the
    unproven ``search --part-uuid`` primitive must not be reintroduced
    without an executable test against the exact shipped GRUB package
    (T1.2/D52).
    """
    digest = _require_password_hash(password_hash)
    if not isinstance(developer, bool):
        raise GrubAbConfigError("developer must be a boolean")

    def _entry(slot: str, partuuid: str, fs_uuid: str) -> str:
        args = " ".join(
            _kernel_arguments(
                root_partuuid=partuuid,
                developer=developer,
                console_policy=console_policy,
            )
        )
        return (
            f"menuentry 'Greia Slot {slot}' --unrestricted --id {GRUB_ENTRY_NAMES[slot]} {{\n"
            f"  search --no-floppy --fs-uuid --set=root {fs_uuid}\n"
            f"  linux {GRUB_KERNEL_PATH} {args}\n"
            f"  initrd {GRUB_INITRAMFS_PATH}\n"
            "}\n"
        )

    return (
        f'set superusers="{GRUB_USER}"\n'
        "export superusers\n"
        f"password_pbkdf2 {GRUB_USER} {digest}\n"
        "if [ -s $prefix/grubenv ]; then\n"
        "  load_env\n"
        "fi\n"
        'if [ -n "${next_entry}" ]; then\n'
        '  set default="${next_entry}"\n'
        "  unset next_entry\n"
        "  save_env next_entry\n"
        "else\n"
        '  set default="${saved_entry}"\n'
        "fi\n"
        "set timeout=0\n"
        "set timeout_style=hidden\n"
        # Brand the shared boot-control menu exactly like the single-root
        # appliance path. Without this preamble the A/B image showed raw
        # GRUB text ("Booting Greia Slot A") before the kernel started.
        "if loadfont unicode ; then\n"
        "  set gfxmode=auto\n"
        "  insmod all_video\n"
        "  insmod gfxterm\n"
        "  terminal_output gfxterm\n"
        "fi\n"
        "if [ -f $prefix/greia-theme.txt ]; then\n"
        "  insmod png\n"
        "  set theme=$prefix/greia-theme.txt\n"
        "  export theme\n"
        "  set gfxpayload=keep\n"
        "fi\n"
        + _entry("A", partuuid_a, fs_uuid_a)
        + _entry("B", partuuid_b, fs_uuid_b)
    )


# ---------------------------------------------------------------------------
# A/B configuration validation (reuses existing contract validators)
# ---------------------------------------------------------------------------


def _menuentry_headers(text: str) -> list[tuple[int, list[str]]]:
    headers: list[tuple[int, list[str]]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            tokens = shlex.split(stripped, comments=False, posix=True)
        except ValueError:
            raise GrubAbConfigError(f"line {line_number}: unparseable GRUB line")
        if tokens and tokens[0] == "submenu":
            raise GrubAbConfigError(
                f"line {line_number}: submenus are forbidden in the appliance boot menu"
            )
        if tokens and tokens[0] == "menuentry":
            headers.append((line_number, tokens))
    return headers


def _entry_id(line_number: int, tokens: list[str]) -> str:
    if "--unrestricted" not in tokens:
        raise GrubAbConfigError(
            f"line {line_number}: appliance boot entry must be --unrestricted"
        )
    if "--id" not in tokens:
        raise GrubAbConfigError(
            f"line {line_number}: appliance boot entry must carry a stable --id"
        )
    marker = tokens.index("--id")
    if marker + 1 >= len(tokens):
        raise GrubAbConfigError(
            f"line {line_number}: appliance boot entry --id has no value"
        )
    return tokens[marker + 1]


def validate_grub_ab_text(
    text: str,
    *,
    developer: bool = False,
    console_policy: BootConsolePolicy | str | None = None,
    artifact_a: BootArtifactSet | None = None,
    artifact_b: BootArtifactSet | None = None,
    record: InstalledLayoutRecord | None = None,
) -> tuple[KernelCommandLine, ...]:
    """Validate a two-entry GRUB A/B configuration.

    Reuses the existing per-line kernel contract
    (:func:`validate_kernel_command_line`) for both entries and enforces the
    A/B structure: exactly ``greia-a`` / ``greia-b`` unrestricted entries,
    owner auth, adapter-owned paths, self-contained ``search --fs-uuid`` +
    ``root=PARTUUID=`` bindings, and no os-prober / cross-root / recovery
    surface. The GRUB locator is always the documented ``search --fs-uuid``
    primitive (filesystem UUID); the unproven ``search --part-uuid``
    primitive is rejected. The kernel root is always ``root=PARTUUID=``
    carrying the observed GPT GUID or MBR ``<sig>-<NN>`` value.

    When artifact sets (and/or the trusted layout record) are supplied, the
    per-entry ``(search fs-uuid, kernel root PARTUUID)`` pair must equal the
    same slot's layout-bound identities: a locator from slot A paired with
    slot B's root — or any identifier foreign to the record — fails closed.
    Raises :class:`GrubAbConfigError` (or the contract's
    :class:`GrubContractError` for kernel-line violations).
    """
    if not isinstance(text, str) or not text:
        raise GrubAbConfigError("GRUB A/B configuration must be non-empty text")
    if (artifact_a is None) != (artifact_b is None):
        raise GrubAbConfigError("artifact sets must be supplied as the A/B pair")
    if record is not None and not isinstance(record, InstalledLayoutRecord):
        raise GrubAbConfigError("slot roots must come from the trusted layout record")
    expected_roots: dict[str, str] = {}
    expected_fs_uuids: dict[str, str] = {}
    if artifact_a is not None and artifact_b is not None:
        slot_a, slot_b = _check_artifact_pair(artifact_a, artifact_b)
        expected_roots = {
            GRUB_ENTRY_NAMES["A"]: _require_root_partuuid(
                slot_a.root_partuuid, field_name="slot-A root PARTUUID"
            ),
            GRUB_ENTRY_NAMES["B"]: _require_root_partuuid(
                slot_b.root_partuuid, field_name="slot-B root PARTUUID"
            ),
        }
        expected_fs_uuids = {
            GRUB_ENTRY_NAMES["A"]: _require_filesystem_uuid(
                slot_a.root_filesystem_uuid, field_name="slot-A filesystem UUID"
            ),
            GRUB_ENTRY_NAMES["B"]: _require_filesystem_uuid(
                slot_b.root_filesystem_uuid, field_name="slot-B filesystem UUID"
            ),
        }
    if record is not None:
        if record.boot_backend != "grub-ab-v1":
            raise GrubAbConfigError("GRUB entries exist only on the grub-ab-v1 backend")
        if record.system_b is None:
            raise GrubAbConfigError("single-root layouts carry no GRUB A/B entries")
        record_roots = {
            GRUB_ENTRY_NAMES["A"]: _require_root_partuuid(
                record.system_a.partuuid, field_name="system-a PARTUUID"
            ),
            GRUB_ENTRY_NAMES["B"]: _require_root_partuuid(
                record.system_b.partuuid, field_name="system-b PARTUUID"
            ),
        }
        record_fs = {
            GRUB_ENTRY_NAMES["A"]: _require_filesystem_uuid(
                record.system_a.filesystem_uuid,
                field_name="system-a filesystem UUID",
            ),
            GRUB_ENTRY_NAMES["B"]: _require_filesystem_uuid(
                record.system_b.filesystem_uuid,
                field_name="system-b filesystem UUID",
            ),
        }
        for entry_id in record_roots:
            if entry_id in expected_roots:
                if expected_roots[entry_id] != record_roots[entry_id]:
                    raise GrubAbConfigError(
                        f"entry {entry_id}: artifact root does not match the layout record"
                    )
                if expected_fs_uuids[entry_id] != record_fs[entry_id]:
                    raise GrubAbConfigError(
                        f"entry {entry_id}: artifact filesystem UUID "
                        "does not match the layout record"
                    )
            else:
                expected_roots[entry_id] = record_roots[entry_id]
                expected_fs_uuids[entry_id] = record_fs[entry_id]

    headers = _menuentry_headers(text)
    if len(headers) != 2:
        raise GrubAbConfigError(
            f"expected exactly two appliance menuentries; found {len(headers)}"
        )
    ids = [_entry_id(number, tokens) for number, tokens in headers]
    if set(ids) != {GRUB_ENTRY_NAMES["A"], GRUB_ENTRY_NAMES["B"]}:
        raise GrubAbConfigError(
            "appliance menuentries must carry exactly the stable "
            f"{sorted(GRUB_ENTRY_NAMES.values())} ids; found {sorted(ids)}"
        )

    superuser_double = f'set superusers="{GRUB_USER}"'
    superuser_single = f"set superusers='{GRUB_USER}'"
    if superuser_double not in text and superuser_single not in text:
        raise GrubAbConfigError(f"missing GRUB {GRUB_USER} superuser declaration")
    if "export superusers" not in text:
        raise GrubAbConfigError("missing exported GRUB superusers variable")
    password_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("password_pbkdf2 ")
    ]
    if len(password_lines) != 1:
        raise GrubAbConfigError(
            "expected exactly one GRUB PBKDF2 password declaration; "
            f"found {len(password_lines)}"
        )
    if not password_lines[0].startswith(f"password_pbkdf2 {GRUB_USER} grub.pbkdf2."):
        raise GrubAbConfigError(
            f"GRUB password must use a {GRUB_USER} PBKDF2 hash declaration"
        )

    lowered = text.casefold()
    if "recovery mode" in lowered:
        raise GrubAbConfigError("generated GRUB configuration contains a recovery-mode entry")
    for forbidden in ("os-prober", "configfile", "chainloader", "/dev/"):
        if forbidden in text:
            raise GrubAbConfigError(
                f"GRUB A/B configuration must not contain {forbidden!r}: "
                "entries are self-contained, never discovered"
            )
    if "root=UUID=" in text:
        raise GrubAbConfigError(
            "GRUB A/B entries must bind roots by PARTUUID, never filesystem UUID"
        )
    if "--part-uuid" in text:
        raise GrubAbConfigError(
            "GRUB A/B entries must locate slots with the documented "
            "search --fs-uuid primitive; search --part-uuid is unproven "
            "against the shipped GRUB binary (T1.2/D52)"
        )

    entries = kernel_command_lines(text)
    if len(entries) != 2:
        raise GrubAbConfigError(
            f"expected exactly two Linux kernel command lines; found {len(entries)}"
        )
    try:
        for line in entries:
            validate_kernel_command_line(
                line,
                developer=developer,
                console_policy=_effective_policy(developer, console_policy),
            )
    except GrubContractError as exc:
        raise GrubAbConfigError(f"kernel command-line contract failed: {exc}") from exc

    seen_roots: dict[str, str] = {}
    for line in entries:
        if line.kernel_path != GRUB_KERNEL_PATH:
            raise GrubAbConfigError(
                f"line {line.line_number}: kernel path must be the adapter-owned "
                f"{GRUB_KERNEL_PATH}; found {line.kernel_path!r}"
            )
        roots = [
            argument.split("root=PARTUUID=", 1)[1]
            for argument in line.arguments
            if argument.startswith("root=PARTUUID=")
        ]
        if len(roots) != 1:
            raise GrubAbConfigError(
                f"line {line.line_number}: expected exactly one root=PARTUUID= binding"
            )
        partuuid = _require_root_partuuid(roots[0], field_name="root PARTUUID")
        for argument in line.arguments:
            if argument.startswith("root=") and argument != f"root=PARTUUID={roots[0]}":
                raise GrubAbConfigError(
                    f"line {line.line_number}: only one root binding is allowed"
                )
        seen_roots[partuuid] = seen_roots.get(partuuid, line.kernel_path)
    if len(seen_roots) != 2:
        raise GrubAbConfigError("slot entries must bind two distinct root PARTUUIDs")
    seen_fs: set[str] = set()
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("search "):
            parts = stripped.split()
            if "--set=root" in parts and "--fs-uuid" in parts:
                target = parts[parts.index("--set=root") + 1]
                seen_fs.add(
                    _require_filesystem_uuid(target, field_name="search filesystem UUID")
                )
    if len(seen_fs) != 2:
        raise GrubAbConfigError(
            "slot entries must locate two distinct filesystem UUIDs "
            "with search --fs-uuid"
        )

    initrd_paths = [
        line.strip().split()
        for line in text.splitlines()
        if line.strip().startswith("initrd ")
    ]
    if len(initrd_paths) != 2 or any(
        parts != ["initrd", GRUB_INITRAMFS_PATH] for parts in initrd_paths
    ):
        raise GrubAbConfigError(
            "each slot entry must load exactly the adapter-owned "
            f"{GRUB_INITRAMFS_PATH}"
        )

    # Each entry block must be self-contained: its search line locates the
    # slot filesystem (fs-uuid) whose kernel line boots the same slot's
    # root PARTUUID. Blocks are delimited by menuentry braces.
    blocks = _entry_blocks(text)
    if set(blocks) != {GRUB_ENTRY_NAMES["A"], GRUB_ENTRY_NAMES["B"]}:
        raise GrubAbConfigError("slot entry blocks do not match the stable entry ids")
    for entry_id, body in blocks.items():
        search_targets = [
            parts[parts.index("--set=root") + 1]
            for parts in (line.split() for line in body.splitlines())
            if "--set=root" in parts and "--fs-uuid" in parts
        ]
        if len(search_targets) != 1:
            raise GrubAbConfigError(
                f"entry {entry_id}: expected exactly one self-contained "
                "search --fs-uuid --set=root binding"
            )
        search_fs = _require_filesystem_uuid(
            search_targets[0], field_name=f"entry {entry_id} search filesystem UUID"
        )
        kernel_lines = kernel_command_lines(body)
        if len(kernel_lines) != 1:
            raise GrubAbConfigError(
                f"entry {entry_id}: expected exactly one kernel command line"
            )
        kernel_roots = [
            argument.split("root=PARTUUID=", 1)[1]
            for argument in kernel_lines[0].arguments
            if argument.startswith("root=PARTUUID=")
        ]
        if len(kernel_roots) != 1:
            raise GrubAbConfigError(
                f"entry {entry_id}: expected exactly one root=PARTUUID= binding"
            )
        kernel_root = _require_root_partuuid(
            kernel_roots[0], field_name=f"entry {entry_id} root PARTUUID"
        )
        if expected_roots:
            if kernel_root != expected_roots[entry_id]:
                raise GrubAbConfigError(
                    f"entry {entry_id}: root identity does not match the layout record"
                )
            if search_fs != expected_fs_uuids[entry_id]:
                raise GrubAbConfigError(
                    f"entry {entry_id}: filesystem locator does not match "
                    "the slot's layout identity"
                )
        else:
            # Without record/artifact authority, self-containment still
            # requires the two entries to carry distinct locator pairs so a
            # duplicated slot cannot pass as an A/B configuration.
            pass
    if not expected_roots:
        pairs = set()
        for entry_id, body in blocks.items():
            search_targets = [
                parts[parts.index("--set=root") + 1]
                for parts in (line.split() for line in body.splitlines())
                if "--set=root" in parts and "--fs-uuid" in parts
            ]
            kernel_roots = [
                argument.split("root=PARTUUID=", 1)[1]
                for argument in kernel_command_lines(body)[0].arguments
                if argument.startswith("root=PARTUUID=")
            ]
            pairs.add((search_targets[0], kernel_roots[0]))
        if len(pairs) != 2:
            raise GrubAbConfigError(
                "slot entries must carry two distinct locator/root pairs"
            )
    return entries


def _entry_blocks(text: str) -> dict[str, str]:
    """Split the configuration into per-entry bodies keyed by --id."""
    blocks: dict[str, str] = {}
    current_id: str | None = None
    depth = 0
    collected: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("menuentry "):
            try:
                tokens = shlex.split(stripped, comments=False, posix=True)
            except ValueError as exc:
                raise GrubAbConfigError(f"unparseable menuentry line: {exc}") from exc
            current_id = _entry_id(0, tokens)
            if current_id in blocks:
                raise GrubAbConfigError(f"duplicate appliance boot entry {current_id}")
            depth = 0
            collected = []
        if current_id is not None:
            collected.append(raw_line)
            depth += raw_line.count("{") - raw_line.count("}")
            if depth <= 0 and len(collected) > 1:
                blocks[current_id] = "\n".join(collected)
                current_id = None
    return blocks


# ---------------------------------------------------------------------------
# grubenv one-shot backend (production x86 BootTransactionBackend)
# ---------------------------------------------------------------------------


#: GRUB environment block file inside the caller-provided state directory.
GRUBENV_FILE_NAME = "grubenv"

#: Real GRUB environment blocks are exactly this size (header + padding).
GRUBENV_SIZE = 1024

#: First line of every grubenv block (also recognised by grub-editenv/GRUB).
GRUBENV_HEADER = "# GRUB Environment Block"

#: Persistent-default variable honoured by GRUB and the generated config.
SAVED_ENTRY_KEY = "saved_entry"

#: Candidate-only one-shot variable honoured by GRUB and the generated config.
NEXT_ENTRY_KEY = "next_entry"

#: Platform-only last-observation variable (unknown keys are ignored by GRUB).
LAST_BOOTED_KEY = "greia_last_booted"

#: Deterministic serialization order for the environment block.
_ENV_KEY_ORDER = (SAVED_ENTRY_KEY, NEXT_ENTRY_KEY, LAST_BOOTED_KEY)


def _grubenv_bytes(entries: Mapping[str, str]) -> bytes:
    lines = [GRUBENV_HEADER + "\n"]
    for key in _ENV_KEY_ORDER:
        if key in entries:
            lines.append(f"{key}={entries[key]}\n")
    payload = "".join(lines).encode("ascii")
    if len(payload) > GRUBENV_SIZE:
        raise BootTransactionError("GRUB environment exceeds the stable block size")
    return payload + b"#" * (GRUBENV_SIZE - len(payload))


def _parse_grubenv(raw: bytes) -> dict[str, str]:
    if not raw or len(raw) > GRUBENV_SIZE:
        raise BootTransactionError("GRUB environment size is outside Greia bounds")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise BootTransactionError("GRUB environment is not ASCII text") from exc
    lines = text.split("\n")
    if not lines or lines[0] != GRUBENV_HEADER:
        raise BootTransactionError("GRUB environment header is invalid")
    entries: dict[str, str] = {}
    for line in lines[1:]:
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key or any(char.isspace() for char in key + value):
            raise BootTransactionError("GRUB environment entry is invalid")
        if key in entries:
            raise BootTransactionError("GRUB environment carries a duplicate entry")
        if key not in _ENV_KEY_ORDER:
            continue
        entries[key] = value
    saved = entries.get(SAVED_ENTRY_KEY)
    if saved not in ENTRY_TO_SLOT:
        raise BootTransactionError("GRUB saved_entry is not a stable slot entry")
    one_shot = entries.get(NEXT_ENTRY_KEY)
    if one_shot is not None:
        if one_shot not in ENTRY_TO_SLOT:
            raise BootTransactionError("GRUB next_entry is not a stable slot entry")
        if one_shot == saved:
            raise BootTransactionError("one-shot state must be candidate-only")
    last_booted = entries.get(LAST_BOOTED_KEY)
    if last_booted is not None:
        _require_slot(last_booted, field_name="last_booted")
    return entries


def _fsync_directory(directory: Path) -> None:
    try:
        directory_fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


@dataclass(frozen=True, slots=True)
class GrubEnvBackend:
    """x86 one-shot backend over a stable GRUB environment block.

    ``state_dir/grubenv`` is a 1024-byte GRUB environment block (same shape
    ``grub-editenv`` and GRUB itself read): ``saved_entry`` is the
    persistent default, ``next_entry`` is the candidate-only one-shot the
    generated ``grub.cfg`` boots exactly once, and ``greia_last_booted`` is
    the platform's last authoritative boot observation (ignored by GRUB).
    Writes are atomic (write-temp/fsync/rename/dir-sync plus re-read
    verification). No subprocess, no shell, no device nodes: the backend
    takes only semantic slots, never entries or paths.
    """

    state_dir: Path

    @property
    def backend_id(self) -> str:
        return "grub-ab-v1"

    @classmethod
    def initialize(cls, state_dir: Path, *, default_slot: str) -> "GrubEnvBackend":
        """Create backend state with the accepted slot as persistent default."""
        backend = cls(state_dir=Path(state_dir))
        _require_slot(default_slot, field_name="default_slot")
        backend._write_entries({SAVED_ENTRY_KEY: GRUB_ENTRY_NAMES[default_slot]})
        return backend

    @classmethod
    def attach(cls, state_dir: Path) -> "GrubEnvBackend":
        """Re-attach to existing backend state (reboot/crash survival)."""
        backend = cls(state_dir=Path(state_dir))
        backend.inspect()
        return backend

    def entry_name(self, slot: str) -> str:
        """Stable adapter-owned GRUB entry for a semantic slot."""
        _require_slot(slot)
        return GRUB_ENTRY_NAMES[slot]

    def inspect(self) -> BootBackendState:
        entries = self._read_entries()
        saved = entries[SAVED_ENTRY_KEY]
        one_shot = entries.get(NEXT_ENTRY_KEY)
        last_booted = entries.get(LAST_BOOTED_KEY)
        return BootBackendState(
            backend_id=self.backend_id,
            default_slot=ENTRY_TO_SLOT[saved],
            one_shot_slot=ENTRY_TO_SLOT[one_shot] if one_shot is not None else None,
            last_booted_slot=last_booted,
        )

    def arm_one_shot(self, candidate: str) -> BootBackendState:
        """Arm a candidate-only one-shot; the persistent default is untouched."""
        _require_slot(candidate, field_name="candidate")
        state = self.inspect()
        if candidate == state.default_slot:
            raise BootTransactionError(
                "refusing to one-shot the persistent default: "
                "one-shot state is candidate-only"
            )
        if state.one_shot_slot is not None:
            raise BootTransactionError(
                "a one-shot is already armed; reconcile before re-arming"
            )
        record: dict[str, str] = {SAVED_ENTRY_KEY: GRUB_ENTRY_NAMES[state.default_slot]}
        if state.last_booted_slot is not None:
            record[LAST_BOOTED_KEY] = state.last_booted_slot
        record[NEXT_ENTRY_KEY] = GRUB_ENTRY_NAMES[candidate]
        self._write_entries(record)
        return self.inspect()

    def observe_booted_slot(self) -> str:
        state = self.inspect()
        if state.last_booted_slot is None:
            raise BootTransactionError("no authoritative boot observation yet")
        return state.last_booted_slot

    def commit_accepted(self, slot: str) -> BootBackendState:
        """Persist a new default only for the slot that actually booted."""
        _require_slot(slot)
        state = self.inspect()
        if state.last_booted_slot != slot:
            raise BootTransactionError(
                "refusing to commit a default that never booted: "
                "health commit requires the candidate to have booted"
            )
        record: dict[str, str] = {SAVED_ENTRY_KEY: GRUB_ENTRY_NAMES[slot]}
        if state.last_booted_slot is not None:
            record[LAST_BOOTED_KEY] = state.last_booted_slot
        self._write_entries(record)
        return self.inspect()

    def verify_rollback_ready(self) -> RollbackReadiness:
        state = self.inspect()
        if state.one_shot_slot is not None:
            return RollbackReadiness(
                ready=False,
                accepted_slot=state.default_slot,
                reason="a one-shot is still armed; reconcile first",
            )
        if state.last_booted_slot != state.default_slot:
            return RollbackReadiness(
                ready=False,
                accepted_slot=state.default_slot,
                reason="machine is not running its persistent default",
            )
        return RollbackReadiness(
            ready=True,
            accepted_slot=state.default_slot,
            reason="persistent default is booted and no one-shot is armed",
        )

    def reconcile(self, observed_booted: str) -> BootBackendState:
        """Fold an authoritative boot observation: the one-shot is consumed."""
        _require_slot(observed_booted, field_name="observed_booted")
        state = self.inspect()
        self._write_entries(
            {
                SAVED_ENTRY_KEY: GRUB_ENTRY_NAMES[state.default_slot],
                LAST_BOOTED_KEY: observed_booted,
            }
        )
        return self.inspect()

    def simulate_reboot(self) -> str:
        """Source-scope test hook standing in for firmware boot selection.

        A set one-shot boots the candidate exactly once and is consumed; an
        unhealthy candidate therefore falls back to the persistent default
        on the following boot without any backend mutation.
        """
        state = self.inspect()
        booted = state.one_shot_slot if state.one_shot_slot is not None else state.default_slot
        self._write_entries(
            {
                SAVED_ENTRY_KEY: GRUB_ENTRY_NAMES[state.default_slot],
                LAST_BOOTED_KEY: booted,
            }
        )
        return booted

    @property
    def _env_path(self) -> Path:
        return Path(self.state_dir) / GRUBENV_FILE_NAME

    def _read_entries(self) -> dict[str, str]:
        # Fail-closed on shape only: unlike the JSON boot records, Unix
        # ownership/mode are deliberately not enforced here because the
        # production grubenv lives on a FAT boot-control filesystem without
        # Unix ownership semantics.
        location = self._env_path
        try:
            if location.is_symlink():
                raise BootTransactionError("GRUB environment may not be a symbolic link")
            import stat as _stat

            status = location.stat()
            if not _stat.S_ISREG(status.st_mode):
                raise BootTransactionError("GRUB environment must be a regular file")
            raw = location.read_bytes()
        except OSError as exc:
            raise BootTransactionError(
                f"GRUB environment is not accessible: {exc}"
            ) from exc
        return _parse_grubenv(raw)

    def _write_entries(self, entries: Mapping[str, str]) -> None:
        location = self._env_path
        payload = _grubenv_bytes(entries)
        location.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{location.name}.", dir=location.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, location)
            _fsync_directory(location.parent)
            os.sync()
        finally:
            temporary.unlink(missing_ok=True)
        try:
            observed = location.read_bytes()
        except OSError as exc:
            raise BootTransactionError(
                f"GRUB environment re-read failed after durable write: {exc}"
            ) from exc
        if observed != payload:
            raise BootTransactionError(
                "GRUB environment re-read does not match written bytes"
            )
