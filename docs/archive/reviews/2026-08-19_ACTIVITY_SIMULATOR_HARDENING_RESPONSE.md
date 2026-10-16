# Greia Activity Simulator — Adversarial Review Hardening Response

**Date:** 2026-08-19  
**Review addressed:** `docs/archive/reviews/2026-08-19_ACTIVITY_SIMULATOR_ADVERSARIAL_REVIEW.md`  
**Status:** source fixes committed; owner-controlled focused/full execution still required  
**Evidence warning:** this document records source disposition, not a test PASS.

## Executive disposition

Every issue identified in the 2026-08-19 adversarial simulator review has been addressed either by a concrete source change/regression or, where the review explicitly described a long-term R7/R9/host-portability boundary rather than an immediately implementable simulator feature, by making the limitation mechanical and non-claiming.

The hardening deliberately made the simulator **thinner**. No review item was solved by adding a simulator copy of a Greia service.

## Finding-by-finding resolution

| Review finding | Disposition | Hardened source/contract |
|---|---|---|
| BLOCKER — duplicated runtime/service composition | **ADDRESSED IN SOURCE** | `src/greia_launcher/composition.py` accepts injected HAL/runtime adapters while retaining one PermissionBroker/RuntimeManager/storage/history graph. `GreiaChildShell` owns the one rebuild/supervisor publication sequence. Simulator no longer owns `build_simulator_runtime_services` or `SimulatorActivitySupervisor`. |
| BLOCKER — simulator Shell replaced rebuild/draw/private cache behavior | **ADDRESSED IN SOURCE** | `GreiaSimulatorChildShell` does not override `_rebuild_runtime_services()` or `_draw()`. Exact synthetic sizing uses shared launcher display-policy hooks in `GreiaLauncherPresentation`. |
| BLOCKER — `python -m greia_simulator...` bootstrap shadowable by Activity content | **ADDRESSED IN SOURCE** | `SimulatorPythonRuntimeAdapter` wraps `super().command_for()` and executes `python_activity.py` by absolute Greia-owned path. Bootstrap imports trusted Pygame before Activity path and restores trusted Greia `src/` ahead of Activity content. |
| BLOCKER — Stop/Restart could orphan Activity process/brokers/history | **ADDRESSED IN SOURCE/TEST** | simulator Shell handles control-plane SIGTERM by unwinding, then uses real `ActivitySupervisor.request_stop`, bounded polling and `force_stop(... SYSTEM_SHUTDOWN)` escalation. The desktop controller retains the `Popen` handle until exit is confirmed, records the Shell PID in the workspace lease, clears that PID before dropping the dead handle and refuses a replacement Start/lease release if ownership cleanup fails. If the controller crashes while the Shell survives, stale-lock recovery keeps the workspace locked. |
| BLOCKER — source copied before safe validation; symlinks dereferenced/unbounded recursion possible | **ADDRESSED IN SOURCE** | `SimulatorWorkspace.load_activity()` performs a finite lstat safety inspection and canonical byte bound before managed copy, rejects symlinks/special/executable/forbidden content and containment overlap, content-fingerprints the inspected files, then registry-validates the exact staged snapshot. |
| BLOCKER — failed reload could destroy last-known-good managed Activity | **ADDRESSED IN SOURCE** | replacement publication holds the previous directory until new final registry discovery succeeds and restores it on failure. Regression explicitly injects final-discovery failure and checks rollback. |
| HIGH — `GREIA_SIMULATOR`/viewport exposed to Activity | **ADDRESSED IN SOURCE** | workspace child environment contains only normal Greia roots. Viewport is trusted adapter CLI plumbing. Bootstrap removes any stale `GREIA_SIMULATOR*` variables before Activity execution. |
| HIGH — desktop simulator could be mistaken for untrusted-code sandbox | **ADDRESSED IN UI/DOCS** | control plane has a prominent trusted-code-only warning. ADR/developer/acceptance docs state semantic capability toggles do not physically revoke host permissions and simulator does not prove Bubblewrap/kernel containment. |
| HIGH — regression suite too shallow | **ADDRESSED IN TEST SOURCE** | focused suite now attacks composition, shadowing, identity leakage, capability authority, workspace lock/binding/process ownership, profile preference, source transaction negatives, package delegation, unavailable runtime, bounded shutdown and real READY/storage/event/history/STOP integration. Execution still required. |
| MEDIUM — duplicate capability vocabulary | **ADDRESSED IN SOURCE** | control-plane choices derive from `RuntimeCatalogue.allowed_capabilities`; simulator owns only a HAL mapping and fails if canonical Greia gains an unmapped capability. |
| MEDIUM — Acer/tablet/low-resource preset labels overclaimed simulation | **ADDRESSED IN SOURCE/DOCS** | presets are geometry-only labels (`Reference 1024x600`, numeric resolutions). UI explicitly says CPU/RAM/GPU/hardware model is not emulated. |
| MEDIUM — normal Windows-capable startup imported POSIX `fcntl` via package service | **ADDRESSED IN SOURCE** | package-service import moved inside `install_activity_package()`. Hosts unable to load canonical package service get feature-unavailable, never a simulator unzip fallback. |
| MEDIUM — shared state had no checkout identity/single-writer rule | **ADDRESSED IN SOURCE/TEST** | `workspace.json` binds schema + repo root; explicit `--rebind-state` is allowed only while holding the writer lease. `.workspace.lock` records the controller PID plus any owned Shell PID, is inode-owned, cannot be released while a child is registered and prevents a second controller from adopting state after a controller crash while its Shell remains alive. |
| MEDIUM — lock creation/rewrite had an observation race | **ADDRESSED IN SOURCE/TEST** | `O_EXCL` establishes the writer path, complete payload writes are fsynced, and a partial/malformed lease fails closed rather than being mistaken for stale. Lease rewrites use the owned descriptor and concurrent readers cannot turn an in-progress payload into a second-writer grant. |
| MEDIUM — stale-lock probing was not safely portable | **ADDRESSED IN SOURCE/TEST** | live-PID probing is POSIX-only. Non-POSIX hosts fail closed on an existing lock instead of using `os.kill(pid, 0)`, whose Windows semantics can terminate a process. A regression locks this boundary. |
| MEDIUM — source could change after metadata-only preflight | **ADDRESSED IN SOURCE/TEST** | preflight records file identity, size, mtime and SHA-256 content; the copy rechecks opened-file identity/size and hashes the exact bytes copied. A regression mutates a file to same-size different bytes while restoring mtime and confirms staging still rejects it. |
| MEDIUM — Pygame `set_mode` interception incomplete as universal display abstraction | **BOUNDARY ENFORCED; LONG-TERM R7 DEBT REMAINS** | bootstrap remains intentionally narrow and docs forbid expanding it into a simulator SDL framework. Shared Shell display seam was improved now. Activity display ownership is still R7 debt and is not claimed solved by simulator. |
| MEDIUM — acceptance conflated registry-invalid runtime with unavailable runtime adapter | **ADDRESSED IN TEST/DOCS** | focused regression demonstrates valid `runtime.type = "web"` may register while RuntimeManager reports unavailable. Acceptance protocol now distinguishes malformed runtime declarations from current R9 absence. |
| LOW — quick UI size always edited first profile | **ADDRESSED IN SOURCE** | control plane has an explicit real profile selector; reads/writes the selected profile's real `UiPreferencesStore`. Start preserves the user's newly selected size instead of rereading and overwriting it first. |
| LOW — control plane did not notice unexpected Shell death | **ADDRESSED IN SOURCE/TEST** | periodic health polling records the real exit, clears the registered child PID before dropping the process handle, and fails closed if workspace ownership cannot be updated. |

## New/strengthened shared seams

The hardening improved normal Greia rather than introducing simulator policy:

```text
src/greia_launcher/composition.py
  canonical runtime-adapter injection seam

src/greia_launcher/child_shell.py
  canonical HAL/runtime/display-session variation hooks
  one runtime-service/supervisor rebuild sequence

src/greia_launcher/presentation.py
  shared initial/resize display request + caption hooks
  normal cache invalidation remains presentation-owned
```

These are intended to support future R7/R9 evolution too; they are not simulator-only policy.

## Focused regression source now expected

`tests/test_greia_simulator.py` now includes source contracts for:

```text
canonical capability coverage
absolute/bootstrap shadow resistance
Activity-visible simulator identity absence
trusted Greia import path
no simulator Shell rebuild/draw replacement
shared exact display-policy hooks
workspace repo binding + single writer
writer-lease-before-rebind ordering
controller + owned-Shell PID lease ownership
controller-crash / live-Shell stale-lock retention
partial/malformed lock fail-closed behavior
non-POSIX stale-lock fail-closed behavior
control-plane Start registers Shell PID
control-plane Stop retains live process on termination failure
control-plane Stop clears lease before dropping dead handle
named-profile preference persistence
positive DEVELOPER_UNSIGNED load
built-in collision
source/state overlap
file + directory symlinks
oversize-before-copy
content-fingerprinted source staging including same-metadata mutation rejection
last-known-good rollback
canonical package-service delegation
missing required capability through normal authority
valid-but-unavailable Web runtime behavior
bounded graceful/forced shutdown path
real local Pygame READY/storage/event/history/STOP integration
```

The integration test uses the ordinary `ProfileVisualActivitySupervisor`, storage/event brokers, history service and simulator-injected canonical Python adapter; it is not a simulator mock lifecycle.

## Still deliberately open / not converted into false closure

This hardening does **not** close:

```text
R7 production graphics/session/input architecture
production Bubblewrap/kernel containment
physical input/audio/network/media behavior
Acer/Pi performance/resource acceptance
R9 canonical Web runtime
R10 full Activity update/remove/signature/revocation lifecycle
Windows/Linux packaged simulator maturity
```

Package install can remain unavailable on hosts that cannot currently run the canonical package service. The correct fix for future portability is to make the canonical package service portable, not add a simulator implementation.

Likewise, the current Python Pygame `set_mode` bootstrap is temporary compatibility debt. The proper long-term removal point is the shared R7 Activity display/surface abstraction.

## Verification status

At the time this response was updated, the hardening commits and expanded tests were committed to `main`, but the owner-controlled commands had **not yet been executed for the hardened head**:

```bash
PYTHONPATH=src python3 -m unittest tests.test_greia_simulator -v
make verify
python3 tools/greia_simulator.py --state-dir "$HOME/.greia-simulator-acceptance"
```

Therefore the correct current classification remains:

```text
ADVERSARIAL FINDINGS: ADDRESSED IN SOURCE
FOCUSED HARDENING REGRESSIONS: COMMITTED, NOT YET EXECUTED
FULL make verify: NOT YET EXECUTED FOR HARDENED HEAD
MAC MANUAL ACCEPTANCE: NOT YET EXECUTED FOR HARDENED HEAD
PRODUCTION/HARDWARE CLAIMS: NONE
```
