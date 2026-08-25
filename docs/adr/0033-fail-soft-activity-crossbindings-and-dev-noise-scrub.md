# ADR 0033 — Installed-OS Activity fault containment and development-noise sanitation

Status: **Accepted; installed-runtime hardening implemented, physical re-validation pending**

Date: 2026-08-25

Extends: ADR 0017 (platform-owned sessions/events/progression/reward ledger), ADR 0018 (lightweight UI), ADR 0012 (platform architecture constitution)

## Context

A single broken or not-loadable Activity must never take the whole child OS down.

Greia already isolates invalid packages during ordinary discovery: `ActivityRegistry.discover(fail_closed=False)` skips a corrupt Activity with a warning. The physical failure seen during Activity work was downstream of that boundary. Host tooling had injected regenerable macOS/cache files into an Activity tree, validation skipped that Activity, but `ProgressionPolicy.load` then encountered a rule referencing the absent Activity and raised. The exception escaped launcher runtime composition; systemd restarted the launcher; the same deterministic failure repeated.

The first ADR-0033 tranche fixed the absent-Activity progression binding and added an in-process cleanup. Review of the installed permission model exposed an important flaw in that cleanup placement: `/opt/greia-os` is installed `root:root` and read-only while `greia-launcher.service` runs as `greiakid`. An unprivileged launcher therefore cannot be relied upon to delete contamination from the built-in tree. Developer and parent-installed Activities also live in distinct roots.

The system must be resilient **at the installed OS boundary**, independent of whether a human or coding agent used the preferred copy/deploy workflow.

## Decision

Greia uses three independent containment layers.

### 1. Privileged, fail-open pre-launch sanitation

Immediately before every installed launcher start, systemd runs:

```text
/usr/local/lib/greia-os/scrub-activity-trees
```

as a privileged `ExecStartPre=+` helper. The launcher process itself remains `greiakid`.

The helper invokes the shared `greia_platform.activity_tree_cleanup` implementation over every Activity source the installed launcher can consume:

```text
built-in:  ${GREIA_OS_ROOT:-/opt/greia-os}/activities
developer: ${GREIA_DEVELOPER_ACTIVITY_ROOT:-/var/lib/greia-developer/activities}
parent:    ${GREIA_PARENT_ACTIVITY_ROOT:-${GREIA_PARENT_ACTIVITY_PACKAGE_ROOT:-/var/lib/greia-os/activity-packages}/active}
```

Only a fixed, reviewed set of fully regenerable development noise is removable:

- macOS: `._*`, `.DS_Store`, `__MACOSX/`
- Windows: `Thumbs.db`, `desktop.ini`, `~$*`
- editor/cache: `*~`, `*.swp`, `*.swx`, `*.tmp`, `.nfs*`, `__pycache__/`, `*.pyc`

This is intentionally not a general cleaner. Real Activity content is never repaired, rewritten, synthesized or restored.

The scrubber is:

- bounded to each configured root;
- non-following for directory symlinks and refusing a symlink used as a root;
- best-effort for filesystem races, read-only mounts and permission failures;
- truthful about successful removals versus failed removals;
- idempotent on a healthy tree;
- **never boot authority**.

The shell wrapper exits zero even if the Python cleanup process fails unexpectedly. A cleanup defect therefore cannot create the restart loop it exists to prevent.

The earlier in-process cleanup remains only defense in depth; installed correctness no longer depends on the unprivileged launcher being able to mutate `/opt`.

### 2. Per-Activity discovery isolation

After sanitation, `ActivityRegistry` remains the authority for package validity.

A genuinely broken Activity is not auto-healed. It is skipped and recorded/logged as unvalidated while unrelated Activities remain available.

This distinction is deliberate:

```text
regenerable host dirt -> installed OS may remove
real package defect   -> Activity remains broken/unloaded
```

### 3. Enrichment must not become OS availability authority

History storage bounds and trusted event recording remain hard platform authority.

Progression and achievements are enrichment. Their source/build validation remains strict, but the **installed launcher runtime** is fail-soft:

- a progression rule referencing an Activity absent from the loaded catalogue is dropped with a warning;
- if runtime progression policy is otherwise stale or corrupt, including an undeclared event binding against a loaded Activity, the launcher disables progression for that launcher instance and logs the defect;
- strict `ProgressionPolicy.load(...)` remains available to source/build/test validation and continues to raise for those defects;
- achievement policy already follows the same availability principle: invalid achievement enrichment disables the badge service instead of stopping Activity launch/history.

Therefore an Activity edit can temporarily lose its own/global reward enrichment, but it cannot turn a child OS into a launcher restart storm.

## Why runtime and source validation differ

Fail-soft installed runtime is **not** permission to merge bad policy.

The correct split is:

```text
source/build/test:
    invalid package or progression contract -> FAIL loudly

installed child runtime:
    invalid Activity -> isolate Activity
    invalid progression/achievement enrichment -> disable affected enrichment
    trust/storage/history safety corruption -> remain fail-closed
```

This preserves engineering pressure without making a child-facing appliance depend on perfect enrichment metadata at every instant during development or update rollout.

## Restart-loop boundary

`greia-launcher.service` retains systemd restart behavior for genuine launcher/process failures. This ADR removes the known deterministic Activity-contamination path from that failure class instead of trying to paper over it by increasing restart delays or suppressing systemd recovery.

The developer boot contract remains independently observable (`panic=0`, developer SSH, visible diagnostic policy). Kernel/initramfs/first-boot failures are not reclassified as Activity failures.

## Consequences

- Root-owned/read-only built-in Activities can actually be sanitized before the unprivileged launcher starts.
- Developer and parent Activity roots receive the same installed hygiene boundary.
- Raw SSH/SCP contamination by common host metadata no longer relies on agent discipline for recovery.
- A dirty-but-otherwise-valid package can become loadable again automatically.
- A genuinely broken package stays broken and isolated.
- Stale progression/achievement metadata cannot take down the launcher.
- History/event safety and package trust remain strict.
- Cleanup adds one bounded filesystem walk at launcher start/restart, never in the hot child session/render path.
- Repeated cleanup removals remain useful diagnostics that a development/update path is producing dirty trees; self-healing does not make the contamination invisible.

## Rejected alternatives

- **Document the correct SSH/deploy procedure and rely on agents to follow it.** Rejected as the primary defense. The installed appliance must be resilient even when development workflows are imperfect.
- **Run cleanup only inside `LauncherApplication`.** Rejected as the installed authority because the launcher is intentionally unprivileged and `/opt/greia-os` is root-owned/read-only.
- **Make the launcher run as root.** Rejected. A small privileged pre-start operation is substantially narrower than widening the child Shell's authority.
- **Auto-repair broken Activities.** Rejected. Missing/invalid real content must remain visible as a package defect.
- **Keep runtime progression corruption fatal to boot.** Rejected. Progression is enrichment, not an OS availability/safety authority; strict source validation still catches the defect.
- **Disable systemd restart for the launcher.** Rejected. The service still needs recovery from genuine process failures; deterministic Activity faults should be contained before they reach that layer.
- **Sanitize only developer uploads.** Rejected. That depends on one ingress path and does not protect an already-dirty installed tree.

## Source owners

```text
src/greia_platform/activity_tree_cleanup.py
build/overlay/usr/local/lib/greia-os/scrub-activity-trees
build/overlay/etc/systemd/system/greia-launcher.service
src/greia_platform/activities.py
src/greia_platform/history.py
src/greia_launcher/composition.py
```

## Verification boundary

The original ADR tranche recorded `make verify` **1,313/1,313 PASS** at `c8921313`.

The installed-runtime hardening tranche adds focused regression coverage for:

- the complete installed Activity-root set;
- symlink-root refusal;
- truthful failed-removal accounting;
- runtime fail-soft progression corruption/stale event bindings while strict source validation remains strict;
- privileged pre-launch scrub ordering before the unprivileged launcher;
- explicit fail-open behavior of the installed scrub wrapper.

Those new tests and the full repository gate must execute on the final source state before this tranche is called source-closed. Physical Acer acceptance must then deliberately contaminate a disposable/test Activity with representative safe junk, restart the launcher, verify the junk is removed by the privileged pre-start helper, verify the Activity/launcher behavior, and prove fresh SSH/launcher recovery without a restart storm.
