# Greia Activity Simulator — Acceptance Protocol

**Date:** 2026-08-19  
**Architecture authority:** `docs/adr/0029-real-runtime-activity-simulator.md`  
**Developer guide:** `docs/development/GREIA_ACTIVITY_SIMULATOR.md`  
**Evidence class:** **SIMULATOR / developer semantic evidence only**

This protocol validates that the Activity Simulator remains a thin synthetic-device composition over the real Greia platform. It must never be used to replace VM/image, production sandbox/backend, or physical-hardware acceptance.

---

## 1. Hard invariants

A passing simulator implementation must satisfy all of these:

1. The child-facing window is the real profile-aware Greia child Shell, not a parallel launcher implementation.
2. Activity discovery/manifest validation uses the real `RuntimeCatalogue` + `ActivityRegistry` and real trust vocabulary.
3. Launch authorization/compatibility uses the real `PermissionBroker` + `RuntimeManager`.
4. Activity lifecycle, READY/STOP, storage, history/events and profile visual context use the normal Greia service owners.
5. Device variation is injected through typed synthetic `GreiaHAL` facts, not through Activity-specific conditionals.
6. Resolution testing exercises the same Greia responsive/canvas/system-safe geometry used outside the simulator.
7. `Load Activity Folder…` uses `DEVELOPER_UNSIGNED` trust and cannot collide with built-in identity authority.
8. `Install Activity Package…` calls the canonical `ActivityPackageService` and does not implement a second extraction/install path.
9. Simulator mutable state remains outside the Greia checkout.
10. First-party Activities contain no `GREIA_SIMULATOR` branch/import and do not import `greia_simulator`.
11. The current Pygame display override exists only below the simulator runtime-adapter seam and does not patch Greia policy/services.
12. Web/HTML execution is unavailable until the canonical R9 Web runtime adapter exists; host-browser/private-webview execution is not an acceptable substitute.
13. A simulator PASS is never promoted into Bubblewrap, display-session, trusted-system-chrome, physical-controller, boot/installer, Acer/Pi performance or R7/R8/R9/R10/R14 closure evidence.

A violation of any item above is a **FAIL** even if an Activity appears to run.

---

## 2. Preconditions

Use an owner-controlled current checkout with:

```text
correct repository: frozenpepper/Greia
correct branch: main
exact tested SHA recorded
clean source tree, except deliberate work being tested
Python 3 with current Greia/Pygame dependencies
Tk available for the desktop control plane
```

Do not use GitHub-hosted Actions unless the owner explicitly authorizes that hosted execution.

Choose simulator state **outside** the repository, for example:

```text
~/.greia-simulator-acceptance
```

Do not put the state directory under the Greia checkout.

---

## 3. Source contract gate

Record the exact SHA first:

```bash
git rev-parse HEAD
```

Run the focused simulator suite:

```bash
PYTHONPATH=src python3 -m unittest tests.test_greia_simulator -v
```

This focused suite must include the non-drift checks that:

- `SimulatorPythonRuntimeAdapter` extends the canonical Python runtime adapter;
- `SimulatorActivitySupervisor` extends the canonical profile-visual supervisor;
- `GreiaSimulatorChildShell` extends the canonical Greia child Shell;
- first-party Activity Python source does not branch/import on simulator identity;
- simulator workspace state cannot be placed inside the source checkout;
- synthetic capability/viewport facts round-trip through the intended environment/HAL path.

Then run the canonical full source gate:

```bash
make verify
```

**Stop on a real failure.** Repair the source contract; do not weaken the simulator test or bypass registry/runtime authority to make the UI appear functional.

---

## 4. Desktop launch smoke test

Start the simulator from the repository root:

```bash
python3 tools/greia_simulator.py \
  --state-dir "$HOME/.greia-simulator-acceptance"
```

Expected:

- the control plane opens without modifying the source checkout;
- pressing **Start / Apply** opens a separate child-facing Greia window;
- the child-facing window is the normal Greia profile picker/Shell composition;
- closing/stopping the synthetic child leaves the control plane usable;
- Restart creates a fresh child session using the current selected synthetic facts.

Record screenshots if visual behavior is part of the retained evidence.

---

## 5. Required viewport / interface-size matrix

Exercise at least:

```text
1024×600  + normal
1024×600  + large
1280×800  + normal
1366×768  + compact
1920×1080 + normal
```

Also use at least one awkward custom viewport/aspect ratio appropriate to the Activity under test.

For each configuration verify:

- Greia Shell exactly uses the selected synthetic viewport;
- profile/category/Activity controls remain reachable;
- labels remain readable enough for the intended child-facing UI;
- essential Activity controls stay outside platform-protected Home/Back geometry;
- reference-canvas content keeps aspect ratio according to its selected fit policy;
- world/expand content reveals world rather than stretching gameplay coordinates;
- fluid collections reflow/scroll rather than using a hidden per-resolution coordinate table;
- `compact` / `normal` / `large` changes semantic sizing without creating a separate authored layout;
- rendered and pointer/hit geometry remain aligned.

A layout fix that checks `GREIA_SIMULATOR`, a preset name or a hardware model is a **FAIL**. Fix the ordinary Activity/shared Greia layout implementation instead.

---

## 6. Load Activity Folder acceptance

Choose a valid development Activity source using **Load Activity Folder…**.

Expected:

1. source is copied into private simulator staging rather than symlinked;
2. normal VCS/bytecode cache residue may be omitted;
3. the real registry/runtime policy validates it;
4. the package appears through the normal developer source with `DEVELOPER_UNSIGNED` trust;
5. the real Greia launcher discovers it through its normal rescan path;
6. its launcher category/title/icon behavior follows normal Greia presentation;
7. launch goes through the real permission/runtime/lifecycle path.

Negative cases to exercise at least once:

- duplicate built-in Activity ID;
- invalid/escaping entrypoint;
- unsupported capability/permission/runtime declaration;
- forbidden package content.

Each must fail through normal Greia validation. Do not manually copy a rejected Activity into managed simulator state.

Reload the same Activity after a small source edit and verify the managed developer copy is updated and normal discovery recovers.

---

## 7. Capability-policy acceptance

Use one Activity whose requirements make the result observable.

### Required capability denial

Example: an Activity requiring `touch`.

1. enable `touch`; confirm compatibility/launch behaves normally;
2. disable `touch`, press **Start / Apply**, select the same profile/Activity;
3. confirm the normal Greia compatibility/permission/runtime path rejects the missing required capability rather than Activity code discovering it ad hoc.

### Optional capability fallback

For an optional capability such as `controller`, toggle presence/absence and confirm the Activity remains launchable while its normal semantic fallback behaves correctly.

Do **not** call this physical controller/touch acceptance. This proves capability-policy behavior only.

---

## 8. Profile / My Greia acceptance

Use at least two simulator profiles where available.

Verify:

- `compact` / `normal` / `large` persists through the real `UiPreferencesStore`;
- the real child Shell supplies the same read-only visual context to ordinary Activities;
- ordinary Activities do not gain customization write authority merely because they run in the simulator;
- colors/wallpaper/avatar are changed through the actual **My Greia** Activity, not a duplicate simulator preference store;
- profile-specific visual settings do not leak between child profiles;
- restarting the simulator preserves the isolated profile state.

Language controls are not accepted as a simulator feature until Greia's authoritative profile-language persistence/end-to-end ADR-0028 integration is available. Do not add a shadow language setting just for the simulator.

---

## 9. Python Activity lifecycle acceptance

Launch a first-party Python Activity from the real simulator Shell.

Verify:

- the Activity uses the selected synthetic viewport rather than taking over the developer's physical display;
- current fullscreen requests are translated only in the simulator child process;
- the first usable frame is presented before the Activity publishes READY according to the normal Activity contract;
- storage/history/event behavior remains usable through the real Greia services;
- normal exit/Greia stop returns to the child Shell;
- a failed/never-ready Activity follows the normal supervisor failure/timeout semantics rather than wedging the control plane.

The simulator's desktop process/window lifecycle is developer evidence. It does not prove production display-session handoff/recovery.

---

## 10. Canonical package-install acceptance

Choose a valid `.greiaactivity`/ZIP package using **Install Activity Package…**.

Expected:

- the call goes through `ActivityPackageService`;
- normal bounded archive/path/content validation executes;
- installed state is written under the isolated simulator package root;
- the normal Parent-trusted source becomes discoverable through the real launcher;
- re-import of an already-installed ID follows current canonical service behavior.

Also exercise one malformed archive and preserve its actual rejection.

A PASS here is evidence only for the **currently implemented local new-install transaction**. It does not establish R10 update/remove/rollback/signature/revocation/save-migration completion.

---

## 11. Web/HTML expected result

At the current source boundary, the normal launcher/runtime composition has no canonical Web runtime adapter.

Therefore the correct acceptance result is:

```text
Web/HTML Activity execution: NOT IMPLEMENTED / R9 prerequisite
```

Do not:

- open the package in Safari/Chrome and call that a simulator PASS;
- embed a simulator-only browser/private webview;
- implement separate DOM storage/input/Home semantics.

When R9 lands, update this protocol so the simulator is required to instantiate the **same canonical Web adapter** under the synthetic device composition.

---

## 12. Evidence to preserve

For a retained simulator acceptance run record:

```text
exact repository SHA
host OS/Python/Pygame versions as relevant
simulator state-root path
viewport/interface-size/capability matrix exercised
Activity IDs/versions tested
focused simulator test command/result
make verify command/result
Load Activity positive/negative validation outcomes
package install positive/negative outcomes
screenshots for visually meaningful states
first genuine failure, if any
```

Label the report prominently:

```text
SIMULATOR / DEVELOPER EVIDENCE
```

---

## 13. Explicit non-claims

Even a complete PASS of this protocol does **not** prove:

```text
production Bubblewrap/kernel isolation
production filesystem mount containment
Xorg/KMSDRM/Wayland/compositor ownership or transition behavior
DRM/input device authority
trusted Home/Back non-coverability/input interception
physical controller mapping/latency/noise/reconnect
physical touch/audio/network/removable-media behavior
initramfs/GRUB/installer/boot continuity
Acer/Pi CPU/RAM/GPU/storage/resource behavior
Web runtime support before R9
full R10 lifecycle beyond the current new-install service
R7/R8/R9/R10/R14 closure
```

Use the specific VM/image/physical protocol for those claims.

---

## 14. Failure rules

Stop and report rather than hiding the defect if:

- the simulator needs a second implementation of a Greia service/policy;
- Activity source needs `GREIA_SIMULATOR` logic to pass;
- a missing capability is handled only by simulator UI rather than the real runtime authority path;
- a developer source is accepted only by bypassing `ActivityRegistry`;
- package testing needs a custom simulator extractor/installer;
- simulator state writes into the source checkout;
- Web support requires a host-browser/private-webview shortcut;
- a PASS claim would require relabeling simulator evidence as production/backend/physical proof.

The correct fix is to strengthen the shared Greia abstraction or preserve the open evidence boundary—not to make the simulator more special.
