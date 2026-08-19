# Greia Activity Simulator — Adversarial Review Hardening Response

**Date:** 2026-08-19  
**Review addressed:** `docs/reviews/2026-08-19_ACTIVITY_SIMULATOR_ADVERSARIAL_REVIEW.md`  
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
| BLOCKER — Stop/Restart could orphan Activity process/brokers/history | **ADDRESSED IN SOURCE** | simulator Shell handles control-plane SIGTERM by unwinding, then uses real `ActivitySupervisor.request_stop`, bounded polling and `force_stop(... SYSTEM_SHUTDOWN)` escalation. Control plane hard-kills only after bounded Shell cleanup fails. |
| BLOCKER — source copied before safe validation; symlinks dereferenced/unbounded recursion possible | **ADDRESSED IN SOURCE** | `SimulatorWorkspace.load_activity()` performs finite lstat safety inspection and canonical byte bound before managed copy, rejects symlinks/special/executable/forbidden content and containment overlap, then registry-validates staged content. |
| BLOCKER — failed reload could destroy last-known-good managed Activity | **ADDRESSED IN SOURCE** | replacement publication holds previous directory until new final registry discovery succeeds and restores it on failure. Regression explicitly injects final-discovery failure and checks rollback. |
| HIGH — `GREIA_SIMULATOR`/viewport exposed to Activity | **ADDRESSED IN SOURCE** | workspace child environment contains only normal Greia roots. Viewport is trusted adapter CLI plumbing. Bootstrap removes any stale `GREIA_SIMULATOR*` variables before Activity execution. |
| HIGH — desktop simulator could be mistaken for untrusted-code sandbox | **ADDRESSED IN UI/DOCS** | control plane has prominent trusted-code-only warning. ADR/developer/acceptance docs state semantic capability toggles do not physically revoke host permissions and simulator does not prove Bubblewrap/kernel containment. |
| HIGH — regression suite too shallow | **ADDRESSED IN TEST SOURCE** | focused suite now attacks composition, shadowing, identity leakage, capability authority, workspace lock/binding, profile preference, source transaction negatives, package delegation, unavailable runtime, bounded shutdown and real READY/storage/event/history/STOP integration. Execution still required. |
| MEDIUM — duplicate capability vocabulary | **ADDRESSED IN SOURCE** | control-plane choices derive from `RuntimeCatalogue.allowed_capabilities`; simulator owns only a HAL mapping and fails if canonical Greia gains an unmapped capability. |
| MEDIUM — Acer/tablet/low-resource preset labels overclaimed simulation | **ADDRESSED IN SOURCE/DOCS** | presets are geometry-only labels (`Reference 1024x600`, numeric resolutions). UI explicitly says CPU/RAM/GPU/hardware model is not emulated. |
| MEDIUM — normal Windows-capable startup imported POSIX `fcntl` via package service | **ADDRESSED IN SOURCE** | package-service import moved inside `install_activity_package()`. Hosts unable to load canonical package service get feature-unavailable, never a simulator unzip fallback. |
| MEDIUM — shared state had no checkout identity/single-writer rule | **ADDRESSED IN SOURCE** | `workspace.json` binds schema + repo root; explicit `--rebind-state` is required to change checkout; `.workspace.lock` serializes active control-plane writer. |
| MEDIUM — Pygame `set_mode` interception incomplete as universal display abstraction | **BOUNDARY ENFORCED; LONG-TERM R7 DEBT REMAINS** | bootstrap remains intentionally narrow and docs forbid expanding it into a simulator SDL framework. Shared Shell display seam was improved now. Activity display ownership is still R7 debt and is not claimed solved by simulator. |
| MEDIUM — acceptance conflated registry-invalid runtime with unavailable runtime adapter | **ADDRESSED IN TEST/DOCS** | focused regression demonstrates valid `runtime.type = "web"` may register while RuntimeManager reports unavailable. Acceptance protocol now distinguishes malformed runtime declarations from current R9 absence. |
| LOW — quick UI size always edited first profile | **ADDRESSED IN SOURCE** | control plane has explicit real profile selector; reads/writes selected profile's real `UiPreferencesStore`. |
| LOW — control plane did not notice unexpected Shell death | **ADDRESSED IN SOURCE** | periodic child-process health polling clears stale process handle and reports actual exit code. |

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
named-profile preference persistence
positive DEVELOPER_UNSIGNED load
built-in collision
source/state overlap
file + directory symlinks
oversize-before-copy
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

At the time this response was authored, the hardening commits and expanded tests are committed to `main`, but the owner-controlled commands have **not yet been executed for the hardened head**:

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
