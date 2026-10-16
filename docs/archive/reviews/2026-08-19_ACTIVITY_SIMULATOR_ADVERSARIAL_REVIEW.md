# Greia Activity Simulator — Deep Adversarial Review

**Date:** 2026-08-19  
**Reviewed source head:** `b4cda82ca18996ad67859976292f0457315052d4`  
**Review type:** static/adversarial architecture + implementation review  
**Execution evidence:** no new simulator/full-suite PASS was executed in this review environment  
**Architecture authority:** ADR 0029 remains the intended design; this review assesses whether the first implementation actually satisfies it.

## Executive conclusion

The **product/architecture idea is correct**, but the first implementation is **not yet strong enough to call alignment-enforcing or acceptance-ready**.

The main concern is not polish. Several implementation choices undermine the exact property ADR 0029 was created to guarantee: that the simulator automatically stays on the real Greia path and cannot become a second platform implementation.

Four findings are blockers before investing in broad Mac acceptance:

1. simulator composition duplicates production composition instead of injecting only the synthetic variation points;
2. the trusted Python simulator bootstrap can be shadowed by Activity package content;
3. Stop / Restart can terminate the Shell while leaving the Activity process/session resources alive;
4. `Load Activity Folder…` copies source before canonical validation and follows symlinks, changing the package being validated and allowing unbounded/recursive staging.

There are also important security/evidence, capability, cross-platform and test gaps described below.

The correct response is **not** to abandon the simulator or replace it with a VM. The correct response is to strengthen the shared Greia seams so the simulator becomes thinner.

---

# 1. Severity model

- **BLOCKER** — fix before simulator acceptance/use is treated as reliable developer evidence.
- **HIGH** — strong correctness/security/fidelity gap; fix in the immediate hardening tranche.
- **MEDIUM** — meaningful drift/UX/portability problem; should be resolved before calling the tool mature/multiplatform.
- **LOW** — useful cleanup after the core boundary is trustworthy.

---

# 2. BLOCKER — simulator duplicates the production composition it is supposed to reuse

## Evidence

`src/greia_launcher/composition.py::build_launcher_runtime_services()` is the production owner that composes:

```text
DeviceCapabilityService
PermissionBroker
RuntimeManager
ActivityStorageService
PlatformHistoryService
```

`src/greia_simulator/runtime.py::build_simulator_runtime_services()` re-implements the same composition almost line-for-line, changing only the HAL and Python runtime adapter.

Likewise, `GreiaChildShell._rebuild_runtime_services()` is the production child-shell composition seam, while `GreiaSimulatorChildShell._rebuild_runtime_services()` replaces the entire method and manually reconstructs the supervisor/services.

`GreiaSimulatorChildShell._draw()` also reaches into private presentation fields (`_icon_cache`, `_font_cache`, `_shadow_cache`, `_decorated_icon_cache`, `_activity_scroll_start`) and duplicates resize invalidation behavior from the production run loop.

The current test that checks only:

```python
issubclass(SimulatorPythonRuntimeAdapter, PythonRuntimeAdapter)
issubclass(SimulatorActivitySupervisor, ProfileVisualActivitySupervisor)
issubclass(GreiaSimulatorChildShell, GreiaChildShell)
```

does **not** protect against this drift. A subclass can replace every important method and still satisfy `issubclass()`.

## Why this matters

This creates the exact future failure ADR 0029 is intended to prevent.

Example: production Greia later adds the canonical Web adapter, Awards presentation service, a new lifecycle resource, system-chrome composition or another shared runtime service to `build_launcher_runtime_services()` / `GreiaChildShell._rebuild_runtime_services()`. The simulator does not automatically inherit it. Someone must remember to make a matching edit in the simulator copy.

That is a parallel platform composition even though the classes share names/inheritance.

## Required correction

Refactor the **production owner** once, then make the simulator inject only true variation points.

Recommended shape:

```text
build_launcher_runtime_services(
    ...,
    hal=<injected GreiaHAL>,
    runtime_adapters=<injected adapter set/factory>,
)
```

or an equivalent typed composition object/factory.

`GreiaChildShell` should continue to own the one authoritative rebuild sequence and expose narrow protected/injected seams such as:

```text
device HAL / capability provider
runtime adapter provider
display-session backend/coordinator
ActivitySupervisor class/factory (only if genuinely required)
display/window policy
```

The simulator should ideally **not override `_rebuild_runtime_services()` at all**.

For window sizing, add one shared display/window configuration seam rather than overriding `_draw()` and clearing private caches by name. Cache invalidation should remain owned by the normal Shell run/display code.

`SimulatorPythonRuntimeAdapter.command_for()` should also derive from `super().command_for()` and preserve the canonical cwd/environment rather than duplicating the Python environment tuple.

## Acceptance regression

Add a contract test that proves simulator composition calls the production composition owner with injected HAL/adapters rather than constructing PermissionBroker/Storage/History independently.

---

# 3. BLOCKER — Activity package content can shadow the trusted simulator bootstrap

## Evidence

The simulator currently launches Python Activities as:

```text
python -m greia_simulator.python_activity <validated-entrypoint>
```

with:

```text
cwd = manifest.root
```

For `python -m`, the working directory participates before the repository `PYTHONPATH` in module resolution.

A valid Activity package can therefore contain:

```text
my-activity/
├── activity.toml
├── main.py
└── greia_simulator/
    ├── __init__.py
    └── python_activity.py
```

`greia_simulator` is not a curated Activity import root and is not currently a reserved/shadow-protected package name in `PythonRuntimeAdapter.validate_package()`. Such a directory is not forbidden by the normal package tree rules.

The Activity-owned `greia_simulator.python_activity` may therefore be selected instead of Greia's trusted bootstrap.

## Impact

This can bypass the synthetic viewport patch entirely and makes the executable boundary depend on Activity package naming.

This is primarily a **simulator fidelity/authority bypass**, not a new production privilege escalation: the Activity already runs its own code. But it invalidates a core simulator claim—Greia cannot guarantee that the runtime adapter actually installed the intended display interception.

## Required correction

Do not resolve the trusted bootstrap through a module name that can be shadowed from the Activity cwd.

Prefer an absolute Greia-owned bootstrap executable/script path, or another trusted launcher mechanism whose resolution is independent of Activity package contents.

If using an absolute script, make its pre-Activity dependencies resolve from trusted Greia source/install locations before adding the Activity package to `sys.path`.

Do **not** solve this by making simulator validation reject arbitrary package names such as `greia_simulator` if production Greia would otherwise accept them. That would create simulator-only package semantics.

## Required regression

Create a valid test Activity containing a top-level `greia_simulator/` package and prove the real trusted bootstrap still executes and the synthetic viewport remains enforced.

---

# 4. BLOCKER — Stop / Restart can orphan a running Activity and its session state

## Evidence

`SimulatorDesktopApp.stop()` does:

```text
terminate Shell process
wait 2 s
kill Shell process if needed
```

It signals only the child-Shell process.

Python Activities are launched by `PythonRuntimeAdapter.launch()` with:

```text
start_new_session=True
```

so the Activity is deliberately in its own process group/session.

The simulator child Shell does not install a SIGTERM shutdown handler that calls `ActivitySupervisor.shutdown_active()`.

The Shell's normal `finally:` cleanup is not a reliable response to an external default SIGTERM termination.

## Failure scenario

1. launch a long-running Activity;
2. press **Restart** or **Stop** in the simulator control window;
3. the control plane terminates the Shell;
4. the Activity process is in a separate session and may remain alive;
5. storage/event broker threads die with the Shell;
6. lifecycle/control directories and history may remain unfinished until later recovery;
7. a new Shell starts while the old Activity window/process is still present.

That violates the platform-owned lifecycle property the simulator is meant to exercise.

## Required correction

Add a **bounded graceful simulator-shell shutdown protocol**.

At minimum:

- simulator child Shell handles the control-plane shutdown signal/request;
- it calls `supervisor.shutdown_active()` when an Activity exists;
- it polls/forces that Activity to a terminal result using the normal supervisor path;
- broker/control/history cleanup completes;
- then the Shell exits;
- the control plane escalates to hard kill only after a bounded deadline.

A tiny explicit control channel is preferable if signal-handler complexity would mix unsafe work into a signal callback.

## Required regression

Run a deliberately long Activity, stop/restart the simulator and prove:

```text
no Activity process survives
no stale broker process/thread endpoint survives
history session receives a normalized terminal reason
control channel is removed
new Shell starts cleanly
```

---

# 5. BLOCKER — `Load Activity Folder…` changes the source package before validation and is unbounded

## Evidence

`SimulatorWorkspace.load_activity()` currently:

1. creates a staging directory under simulator state;
2. `shutil.copytree(source, staged, ...)`;
3. then asks `ActivityRegistry` to validate the copy.

Python `shutil.copytree()` follows symlinks by default (`symlinks=False`).

The canonical registry explicitly rejects symlinks in `_validate_tree()`.

Therefore a developer source package containing a symlink is not validated as that package. The simulator first dereferences the symlink into ordinary staged files/directories, then validates the transformed copy.

A symlink pointing outside the Activity source can cause external host content to be copied into the managed Activity.

A directory symlink can also create pathological traversal/recursion behavior.

The copy also occurs **before** the canonical maximum Activity byte limit is checked, so the 50 MiB runtime package limit does not bound staging work.

If the chosen source is the simulator state directory or an ancestor of it, the newly created staging directory can live inside the source being copied, creating a recursive/self-containing copy hazard.

## Required correction

The source package must be safely/canonically inspected **before** an unbounded transformation/copy.

Best architectural fix: extract/reuse a canonical single-package validation owner from `ActivityRegistry`, so developer staging can validate one explicit source root with the exact normal tree/manifest rules without scanning unrelated siblings.

Then copy only after validation using bounded, lstat-aware logic, and validate the final staged tree again.

At minimum until that refactor:

- preserve/reject symlinks rather than dereferencing them;
- reject source == state root and source ancestors that would contain the staging destination;
- bound copied bytes/entries while staging;
- preserve the last known-good developer copy until final validation succeeds;
- roll back on final publication failure.

## Required negative tests

```text
file symlink -> rejected
directory symlink -> rejected
symlink escaping source -> rejected
source > maximum_activity_bytes -> rejected without unbounded copy
source == simulator state root -> rejected
source ancestor of simulator state -> rejected
failed reload preserves previous valid developer copy
```

---

# 6. HIGH — simulator exposes its identity to Activity code despite the non-drift rule

## Evidence

`SimulatorActivitySupervisor._sanitized_environment()` adds:

```text
GREIA_SIMULATOR=1
GREIA_SIMULATOR_VIEWPORT=<WxH>
PYTHONPATH=<repo>/src
```

`python_activity.py` reads the viewport but does not remove simulator-specific variables before `runpy.run_path()` executes Activity code.

The current anti-drift test scans first-party source only for literal strings `GREIA_SIMULATOR` and `greia_simulator`.

## Why the current test is insufficient

Third-party Activities are not scanned by this test.

Even first-party code could detect the environment indirectly without containing the exact literal/import pattern the scan expects. The test is a useful lint, not an authority boundary.

More importantly, Greia should not expose simulator identity when Activity code has no legitimate need to know it.

## Required correction

Pass synthetic viewport information to the **trusted bootstrap**, not to the Activity contract.

Prefer a trusted command argument or bootstrap-private value consumed/removed before Activity execution.

Do not provide `GREIA_SIMULATOR` to Activity code.

Add a runtime regression proving an Activity sees the normal Greia launch context and **cannot observe simulator identity or a simulator-only layout flag**.

The source lint may remain as a secondary regression, but it must not be the primary protection.

---

# 7. HIGH — the desktop simulator is not a security sandbox; current UI/docs need a stronger warning

## Evidence

Because simulator `GREIA_OS_ROOT` is a source checkout rather than `/opt/greia-os`, `ActivitySupervisor._sandbox_required()` returns false.

That is intentional for desktop development, and ADR 0029 correctly says simulator evidence does not prove Bubblewrap/kernel containment.

However, a valid Activity still runs as the developer's normal host user with ordinary host filesystem visibility. The Python policy forbids many imports but allows `pathlib`, and Python builtins can open/write files. Filesystem permission decisions are therefore not physically contained by Greia's production Bubblewrap boundary in the simulator.

Likewise, current Pygame code can observe host input/device behavior independently of synthetic HAL facts where R7 has not yet supplied the final input broker.

## Consequences

- **Load Activity Folder… / Install Activity Package… must be treated as executing trusted developer code.**
- A parent-trusted package tested in the simulator is not made safe simply because `PermissionBroker` issued the correct semantic grant object.
- Turning `pointer`, `keyboard`, `controller` etc. off proves compatibility/grant facts; it does not necessarily prevent the host SDL/Pygame layer from physically seeing that device/input.
- The acceptance step saying an ordinary Activity does not gain customization write authority must be worded carefully: the simulator can prove Greia did not grant/expose the capability/path contract, not production filesystem containment.

## Required correction

Before ordinary developer use:

- show a visible control-plane warning that the current desktop simulator is **not an untrusted-code sandbox**;
- document “load only code/packages you trust” prominently;
- distinguish **semantic capability simulation** from **physical input suppression**;
- remove any acceptance wording that implies negative filesystem/input containment can be proven here.

A future optional host-sandbox adapter may improve developer safety, but it must not be relabeled as production Bubblewrap evidence.

---

# 8. HIGH — the current automated tests are too shallow for the claims being made

## Evidence

`tests/test_greia_simulator.py` currently covers:

- viewport parsing;
- synthetic HAL state;
- display-request normalization as a pure function;
- simulator adapter command shape;
- inheritance checks;
- first-party literal simulator-reference scan;
- workspace environment paths;
- workspace-outside-checkout rule.

It does **not** exercise the highest-risk behavior:

```text
build_simulator_runtime_services()
PermissionBroker capability denial
real RuntimeManager launch preparation
Load Activity Folder positive/negative cases
symlink handling
reload rollback
ActivityPackageService invocation
profile UiPreferences persistence
Activity launch lifecycle
READY/STOP/history/storage/event integration
Stop/Restart cleanup
bootstrap shadow resistance
simulator identity absence
launcher rescan publication
actual Pygame child bootstrap behavior
```

The 324-line acceptance protocol is useful, but it is a manual protocol and has never been executed for this head.

## Required correction

Build a focused provider-free integration layer before broad visual testing.

At minimum add tests for every blocker above plus:

- runtime/capability mismatch through real `PermissionBroker` + `RuntimeManager`;
- `Load Activity Folder` uses `DEVELOPER_UNSIGNED` and built-in collision fails;
- package install delegates to the canonical service;
- interface size is read back from the real profile customization store;
- real supervisor launch of a tiny test Activity records READY, storage/event/history and cleanup correctly;
- production composition changes cannot silently leave the simulator with a different service set.

Do not call the inheritance tests “non-drift enforcement” by themselves.

---

# 9. MEDIUM — capability vocabulary is duplicated in simulator source

## Evidence

`src/greia_simulator/device.py` hard-codes `SIMULATOR_CAPABILITIES` while `RuntimeCatalogue.allowed_capabilities` is already loaded from `runtime/child-runtime.toml` as canonical runtime vocabulary.

The values happen to match now.

## Drift scenario

Greia adds a new semantic capability. The normal runtime catalogue accepts it, while `SimulatedDeviceProfile` rejects it as an unknown simulator capability until somebody remembers to update a second constant.

## Required correction

Do not make the simulator an independent vocabulary owner.

Either derive the allowed synthetic capability set from the canonical RuntimeCatalogue or promote the semantic HAL capability vocabulary to one platform-owned constant/schema consumed by both.

Add a regression that fails when the simulator/HAL mapping no longer covers the platform capability vocabulary it claims to simulate.

---

# 10. MEDIUM — “device presets” currently change only resolution and are misleading

## Evidence

`DEVICE_PRESETS` maps labels to `(width, height)` only.

Selecting a preset in the desktop app calls `_preset_selected()`, which changes only `self.viewport`.

Therefore:

- `Tablet 1280x800` does **not** enable touch;
- `Acer / low-resource 1024x600` does **not** simulate low RAM/CPU/GPU/storage;
- machine architecture is not simulated.

## Required correction

Either rename the UI to **Viewport presets** and use labels such as:

```text
Reference 1024x600
1280x720
1280x800
...
```

or define a typed `DevicePreset` containing viewport + capabilities and make every non-simulated property explicit.

If retaining an Acer label, use wording such as:

```text
Acer viewport 1024x600 (geometry only)
```

Do not imply resource/performance emulation.

---

# 11. MEDIUM — “core-platform-neutral” currently fails at import time on Windows

## Evidence

`src/greia_simulator/workspace.py` imports `ActivityPackageService` at module import time.

`src/greia_platform/activity_packages.py` imports POSIX `fcntl` at module import time.

On Windows this prevents the simulator workspace module from importing even if the developer only wants Python Activity resolution/profile testing and never uses package installation.

## Required correction

Mac-first is acceptable, but the current documentation should not imply Windows is already primarily a packaging exercise.

For actual multiplatform progression:

- move the package-service process lock behind a portable platform lock abstraction, **or**
- lazily load the canonical package service so non-package simulator functionality can work on platforms where that service is unavailable, while clearly disabling package-install acceptance there.

Do not create a simulator-only package installer.

---

# 12. MEDIUM — one global state root has no simulator-instance/source-version lock

## Evidence

Default state is always:

```text
~/.greia-simulator
```

There is no workspace-level process lock or metadata binding this mutable synthetic device to a particular checkout/runtime schema.

Package installation has its own canonical `flock`, but profiles, active-profile status and developer Activity staging do not share one simulator-instance lock.

## Failure modes

- two simulator apps can run against the same active-profile file and developer root;
- two different Greia checkouts/branches can reuse the same package/profile state with different runtime/schema expectations;
- one instance can reload developer source while another Shell is reading it.

## Required correction

Add a small platform-neutral `SimulatorWorkspace` metadata/locking layer:

```text
workspace schema version
canonical/selected repo path or source identity
single active simulator writer lock
optional last device-profile state
```

Allow deliberate reuse/migration, but make it explicit rather than accidental.

---

# 13. MEDIUM — current Pygame interception is not a complete Activity display abstraction

## Evidence

The bootstrap monkeypatches only:

```text
pygame.display.set_mode
```

The Python runtime policy permits the `pygame` import root generally. A valid Activity can potentially create/display content through other Pygame/SDL APIs rather than the one patched call.

## Consequence

The current adapter is useful for existing first-party Activities but it is not yet a universal guarantee that every valid Python Activity receives the synthetic physical surface.

## Required direction

Keep ADR 0029's compatibility patch explicitly temporary and continue the shared Greia display/surface abstraction work.

A canonical Activity display API/backend seam should eventually own the physical Activity surface. Production selects the real fullscreen/session backend; the simulator selects the bounded desktop viewport backend. Activities should not need to own SDL display creation directly forever.

Do not expand monkeypatching into a large simulator-specific SDL interception framework.

---

# 14. MEDIUM — acceptance protocol contains one runtime-validation overclaim

The `Load Activity Folder` negative matrix says an unsupported runtime declaration should fail through normal validation.

Current `ActivityRegistry` validates that `runtime.type` is a bounded identifier but does **not** require that a matching runtime adapter currently exists. Runtime availability is checked later by `RuntimeManager` at launch preparation.

That means a structurally valid `runtime.type = "web"` Activity can be discovered today even though the current launcher has no Web adapter; launch then fails as unavailable.

This is a current canonical platform behavior, not something the simulator should secretly change.

Correct the acceptance protocol to distinguish:

```text
invalid runtime declaration syntax/schema -> registry rejection
valid but unavailable runtime family -> discoverable/incompatible or launch-time RuntimeUnavailable according to current canonical behavior
```

Longer-term R9/R10 may choose a richer compatibility classification.

---

# 15. LOW — quick interface-size control always changes the first profile

`SimulatorWorkspace.set_default_interface_size()` calls `profiles[0]`.

The control window says **Child interface size**, which can imply the currently selected child in the Greia Shell. If the workspace contains multiple profiles, a child selected in the Shell may not be the profile modified by the control plane.

Either:

- label it explicitly as the **default/first simulator profile** setting;
- add an explicit profile selector that writes through the same real `UiPreferencesStore`; or
- remove the shortcut and require profile-specific changes through My Greia.

Do not introduce a shadow profile preference store.

---

# 16. LOW — control plane does not monitor Shell process health

After `Popen`, the control plane sets status to Running but does not periodically poll the Shell process.

If the child Shell crashes shortly after start, the UI can continue to say it is running. `stop()` also returns early for an already-dead process without necessarily correcting status.

Add a Tk `after()` health poll and surface the actual exit code/failure state.

This is developer UX rather than platform authority, so keep it out of Greia OS source.

---

# 17. Evidence/claim corrections required before acceptance

Until the blockers are fixed, classify the simulator as:

```text
SOURCE IMPLEMENTED
ADVERSARIAL REVIEW: BLOCKED
FOCUSED TESTS: NOT RUN for current head
FULL make verify: NOT RUN for current head
MAC END-TO-END ACCEPTANCE: NOT RUN
```

Do **not** yet call it:

```text
acceptance-ready
alignment-enforcing
safe for untrusted Activity packages
multiplatform implementation
```

The ADR remains accepted as architecture; the implementation needs hardening to meet it.

---

# 18. Recommended fix order

## Tranche S1 — eliminate composition drift first

1. Refactor canonical launcher runtime-service composition to accept HAL/runtime-adapter injection.
2. Refactor `GreiaChildShell` so simulator overrides only true variation hooks, not `_rebuild_runtime_services()`.
3. Add a shared display/window policy seam so simulator stops reaching into `_draw()`/private caches.
4. Make `SimulatorPythonRuntimeAdapter.command_for()` preserve canonical base command environment/cwd.

**Why first:** every later fix is safer once there is one composition path.

## Tranche S2 — close executable/lifecycle hazards

1. Replace shadowable `python -m greia_simulator...` bootstrap resolution.
2. remove simulator identity from Activity-visible environment;
3. implement bounded Shell shutdown via the normal supervisor lifecycle;
4. add process/session/broker cleanup regressions.

## Tranche S3 — harden developer source acquisition

1. canonical prevalidation before copy;
2. reject/preserve symlinks correctly;
3. bound bytes/entries while staging;
4. prevent source/state recursive containment;
5. transactional reload/rollback;
6. positive/negative source-loading integration tests.

## Tranche S4 — make claims and device semantics honest

1. visible “not an untrusted-code sandbox” warning;
2. capability-policy vs physical-input wording;
3. rename/strengthen viewport/device presets;
4. canonical capability vocabulary;
5. correct unavailable-runtime acceptance behavior;
6. first-profile UI-size wording/selection.

## Tranche S5 — portability and developer polish

1. workspace lock/metadata;
2. process health monitoring;
3. lazy/portable package lock path for Windows progression;
4. Mac packaging only after source/lifecycle hardening passes.

## Longer shared-platform direction

Move current direct `pygame.display.set_mode()` ownership out of Activities behind a canonical Greia Activity display/surface API. The simulator then becomes a natural desktop backend instead of relying on Pygame monkeypatch compatibility.

---

# 19. What is good and should be preserved

The review found real problems, but several decisions are strong and should survive the hardening:

- isolated simulator profile/package/media state rather than mutating the checkout;
- real ActivityRegistry/package trust instead of a fake loader;
- canonical `ActivityPackageService` rather than a simulator unzip path;
- real PermissionBroker/RuntimeManager conceptually in the launch path;
- synthetic HAL facts rather than per-Activity device branches;
- no simulator-only Web browser workaround;
- strict evidence separation from R7/R8/R9/R10/R14;
- Mac-first is a sensible initial product scope;
- the non-drift goal is exactly the right goal—the implementation simply needs stronger seams/tests to make that goal mechanical rather than aspirational.

---

# 20. Next exact step

Do **not** start broad manual viewport acceptance yet.

Implement **S1 + S2**, add the focused regressions, then run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_greia_simulator -v
```

and the affected launcher/runtime/supervisor suites.

Only after those pass should S3 source-loading hardening be completed and the full `make verify` / Mac acceptance protocol be attempted.

No R7 production-backend claim changes as a result of this review.