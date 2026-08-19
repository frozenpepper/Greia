# Greia Activity Simulator — Acceptance Protocol

**Date:** 2026-08-19  
**Architecture authority:** `docs/adr/0029-real-runtime-activity-simulator.md`  
**Developer guide:** `docs/development/GREIA_ACTIVITY_SIMULATOR.md`  
**Adversarial review:** `docs/reviews/2026-08-19_ACTIVITY_SIMULATOR_ADVERSARIAL_REVIEW.md`  
**Hardening response:** `docs/reviews/2026-08-19_ACTIVITY_SIMULATOR_HARDENING_RESPONSE.md`  
**Evidence class:** **SIMULATOR / developer semantic evidence only**

This protocol validates the hardened Activity Simulator as a thin synthetic-device composition over real Greia owners. It never replaces VM/image, production sandbox/backend or physical-hardware acceptance.

---

## 1. Hard invariants

A PASS requires all of these:

1. The child-facing window is the real `GreiaChildShell`.
2. `build_launcher_runtime_services()` remains the single PermissionBroker/RuntimeManager/storage/history composition owner.
3. `GreiaChildShell` remains the single runtime-service/supervisor rebuild owner; `GreiaSimulatorChildShell` does not override `_rebuild_runtime_services()` or `_draw()`.
4. Simulator variation is injected only through typed HAL/runtime/display-policy seams.
5. Discovery/manifest validation uses real `RuntimeCatalogue` + `ActivityRegistry` and real package trust.
6. Required-capability denial reaches real PermissionBroker/RuntimeManager authority.
7. Activity lifecycle, READY/STOP, storage, events/history and profile visual context use normal Greia owners.
8. The Python compatibility bootstrap is an absolute Greia-owned path, not Activity-resolved `python -m` content.
9. No `GREIA_SIMULATOR*`, simulator viewport flag or preset identity is exposed as an Activity API.
10. Exact viewport sizing goes through shared Shell display-policy hooks and the temporary narrow Python Activity display bootstrap; no simulator `_draw()`/cache clone exists.
11. Developer-folder acquisition rejects symlinks/special files/oversize/containment overlap before managed copy, content-fingerprints the inspected snapshot, then uses real registry validation and transactional last-known-good publication.
12. Package install calls only canonical `ActivityPackageService`; no simulator extractor exists.
13. Workspace state is outside the checkout, checkout-bound and single-writer.
14. The workspace lease records both the controller PID and any owned Shell PID; a controller crash must not make a still-running Shell's workspace reusable.
15. Quick interface-size changes target an explicitly selected real child profile through `UiPreferencesStore`.
16. Stop/Restart retires an active Activity through `ActivitySupervisor` before the Shell is considered cleanly stopped, and the desktop controller retains process ownership until exit/lease cleanup is confirmed.
17. Viewport presets make geometry-only claims; they do not claim Acer/tablet/performance emulation.
18. The UI/documentation prominently states that source-mode simulator execution is **not an untrusted-code security sandbox**.
19. Web execution remains unavailable until canonical R9 Web runtime; no host-browser/private-webview substitute is accepted.
20. Simulator PASS is never promoted into production sandbox/display-session/physical/boot/performance/phase-closure evidence.

Any violation is a **FAIL**, even if an Activity appears to run.

---

## 2. Preconditions

Use an owner-controlled checkout:

```text
repository: frozenpepper/Greia
branch: main
record exact SHA
working tree clean except deliberate test work
Python with current Greia dependencies
Pygame installed for complete simulator lifecycle coverage
Tk available for desktop control-plane smoke test
```

Do not run/query/download GitHub-hosted Actions unless the owner explicitly authorizes that hosted execution.

Choose state outside the checkout, for example:

```text
$HOME/.greia-simulator-acceptance
```

Run only Activity source/packages you trust. This protocol does not turn the desktop simulator into malware isolation.

---

## 3. Source contract gate

Record exact head:

```bash
git rev-parse HEAD
```

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_greia_simulator -v
```

A complete focused PASS must include the hardened regressions for:

```text
canonical composition injection
no simulator service graph / _rebuild_runtime_services / _draw replacement
canonical capability vocabulary coverage
absolute bootstrap + Activity shadow resistance
no Activity-visible GREIA_SIMULATOR* identity
trusted Greia source path ahead of Activity package
shared exact Shell display hooks
workspace checkout binding + single writer
writer-lease-before-rebind ordering
controller + owned-Shell PID lease ownership
controller-crash / live-Shell stale-lock retention
partial/malformed lock fail-closed behavior
non-POSIX stale-lock fail-closed behavior
control-plane Start registers Shell PID
control-plane Stop retains a live handle when termination fails
control-plane Stop clears child lease before dropping a dead handle
named-profile UiPreferencesStore persistence
positive DEVELOPER_UNSIGNED source load
built-in identity collision rejection
source/state containment rejection
file + directory symlink rejection
oversize rejection before staging
content-fingerprinted source mutation/TOCTOU rejection
failed replacement restores previous valid managed Activity
canonical ActivityPackageService delegation where host supports it
missing-required-capability denial through real authority
registry-valid but unavailable Web runtime fails at RuntimeManager
bounded graceful/forced supervisor shutdown
real local Python READY/storage/event/history/STOP integration
```

If the Pygame lifecycle integration is skipped because Pygame is absent, the **complete simulator source gate is NOT fully exercised**. Install the simulator dependency and rerun before retaining a complete simulator PASS.

Then run affected shared-owner suites as appropriate and finally:

```bash
make verify
```

Stop on the first real failure. Repair the implementation; do not weaken tests or create simulator exceptions.

---

## 4. Workspace / safety smoke

Start:

```bash
python3 tools/greia_simulator.py \
  --state-dir "$HOME/.greia-simulator-acceptance"
```

Verify:

- visible warning says this is not an untrusted-code sandbox;
- `workspace.json` records this checkout;
- `.workspace.lock` is present while the control plane owns the workspace;
- before a Shell is started the lease records the controller and no child PID;
- after Start the lease records the owned Shell PID;
- a second simulator pointed at the same state root is rejected while the first is active;
- state is outside the checkout;
- ordinary start does not require canonical package-service import on a host where package install is unavailable;
- normal Stop clears the child PID before the writer lease can be released;
- control plane remains usable after child Shell exits/stops;
- unexpected child exit displays its actual exit code and clears child ownership before allowing another Start.

Do **not** delete a live workspace lock to create two writers.

A malformed/partial lock is intentionally fail-closed. Do not delete one merely to continue the test; first prove that no controller or Shell from that workspace remains alive.

If deliberately testing checkout rebind, first stop the old simulator/Shell and use `--rebind-state`; record that action as part of evidence.

---

## 5. Required viewport / interface-size matrix

Exercise:

```text
1024×600  + normal
1024×600  + large
1280×800  + normal
1366×768  + compact
1920×1080 + normal
1111×700  + normal (or another awkward custom viewport)
```

For each:

- Shell surface remains exactly the selected synthetic viewport even after host resize attempts;
- normal Shell resize/cache behavior remains visually correct;
- profile/category/Activity controls remain reachable;
- labels remain readable;
- essential Activity controls remain outside protected Home/Back geometry;
- reference canvas preserves aspect ratio;
- expand/world content reveals world instead of stretching coordinates;
- fluid collections reflow/scroll;
- semantic interface size changes sizing without a separately authored layout;
- rendered and hit/pointer geometry remain aligned.

A fix that checks simulator identity, viewport preset name or a hardware model in Activity code is a **FAIL**.

Viewport preset names must remain geometry-only. Do not describe 1024×600 as Acer performance emulation or 1280×800 as touch/tablet emulation.

---

## 6. Developer source loading

Use **Load Activity Folder…** on a valid trusted source folder.

Positive expectations:

1. source/state do not overlap;
2. source is lstat-inspected before managed copy;
3. allowed VCS/cache residue may be ignored;
4. no source symlink is dereferenced;
5. source bytes stay within canonical maximum;
6. inspected regular files are content-fingerprinted and copied bytes are checked against that fingerprint;
7. staged package passes real registry validation with built-in identity authority;
8. registration is `DEVELOPER_UNSIGNED`;
9. launcher discovers it by normal rescan;
10. launcher category/title/icon behavior is ordinary Greia behavior;
11. launch authorization goes through normal permission/runtime/lifecycle authority.

Required negatives:

```text
duplicate built-in Activity ID
invalid/escaping entrypoint
unknown capability
unknown permission
forbidden package content
executable package file
file symlink escaping source
directory symlink escaping source
special file where host supports creating one
source inside simulator state
simulator state inside source
source larger than RuntimeCatalogue.maximum_activity_bytes
same-inode/same-size/same-mtime content mutation between preflight and copy (automated regression)
```

For all preflight failures verify no unbounded staging copy remains.

### Replacement rollback

1. Load a valid Activity version/source state A.
2. Change source to valid state B.
3. Inject/cause a final publication/discovery failure in the automated regression or an equivalent controlled test.
4. Confirm managed state A remains launchable/intact.

Never delete the last-known-good managed Activity before replacement has committed.

### Runtime declaration distinction

Do not use “unsupported runtime” as a generic registry-negative case.

- malformed/invalid runtime syntax/schema: registry validation may reject;
- syntactically valid `runtime.type = "web"` at the current source boundary: registry may accept, while `RuntimeManager` must report runtime unavailable because R9 adapter does not exist.

That distinction is canonical behavior and must not be hidden by simulator-specific prevalidation.

---

## 7. Capability authority

Use an Activity requiring `touch`.

1. Enable `touch`, restart/apply and verify ordinary launch eligibility.
2. Disable `touch`, restart/apply and select the same Activity.
3. Confirm the real PermissionBroker/RuntimeManager path denies the missing required capability before Activity code can treat an environment flag as authority.

For an optional capability such as controller, toggle presence and verify launch remains possible with ordinary semantic fallback.

These tests prove policy semantics only. They do **not** prove host device denial, physical controller/touch correctness or production `/dev/input` containment.

---

## 8. Profile / My Greia

Use at least two profiles where available.

Verify:

- control-plane profile selector reads each profile's actual `UiPreferencesStore` value;
- changing `compact`/`normal`/`large` writes only the selected profile;
- switching profiles updates the displayed current value;
- ordinary Activities get read-only `GREIA_INTERFACE_SIZE`/theme context without customization write authority;
- My Greia changes colors/wallpaper/avatar through normal Activity permissions;
- state persists across Restart/control-plane relaunch;
- settings do not leak between profiles.

No shadow language setting is allowed before authoritative profile-language persistence is integrated.

---

## 9. Python bootstrap / identity / lifecycle

Launch a first-party or dedicated trusted Python probe Activity.

Verify:

- exact synthetic viewport is used instead of physical fullscreen takeover;
- bootstrap command uses the absolute Greia-owned `python_activity.py` file;
- an Activity containing `greia_simulator/python_activity.py` cannot replace the bootstrap;
- Activity code cannot observe `GREIA_SIMULATOR`, `GREIA_SIMULATOR_VIEWPORT` or another simulator-only identity variable;
- trusted Greia source remains importable even though supervisor strips inherited `PYTHONPATH`;
- first frame is flipped before READY;
- storage broker writes succeed;
- declared event reaches history;
- STOP reaches normal lifecycle channel;
- graceful exit returns to Shell;
- never-ready/crash path follows normal supervisor timeout/failure semantics.

### Stop / Restart while Activity is running

This is mandatory:

1. Launch a probe Activity and wait until it is READY.
2. Press **Restart** (repeat once with **Stop**).
3. Verify the Activity receives/obeys normal STOP where cooperative.
4. Verify non-cooperative Activity is escalated through supervisor force-stop.
5. Verify the desktop controller does not discard its Shell handle before exit is confirmed.
6. Verify the workspace child PID remains registered while the Shell is still alive and is cleared only after confirmed exit.
7. Verify no Activity process, storage/event broker socket/thread or unfinished live session is left behind after bounded cleanup.
8. Verify new Shell can start and use the same profile cleanly.

Do not infer cleanup merely because the Activity window disappeared.

The automated focused suite also covers the crash-survival lease rule: a stale controller PID is insufficient to reclaim a workspace when the recorded Shell PID is still alive.

---

## 10. Canonical package install

Where the host supports importing/running `ActivityPackageService`:

- install a valid `.greiaactivity`/ZIP;
- confirm normal archive/path/content bounds execute;
- confirm state lands under isolated package root;
- confirm normal Parent-trusted source becomes discoverable;
- repeat same ID and preserve canonical current behavior;
- test one malformed archive.

Where the canonical package service is unavailable on that host, the correct result is:

```text
PACKAGE INSTALL: NOT AVAILABLE ON THIS HOST THROUGH CURRENT CANONICAL SERVICE
```

Do not add a simulator unzip fallback to make this green.

A PASS is only current local new-install transaction evidence, not full R10.

---

## 11. Web/HTML expected result

Current canonical runtime composition has no R9 Web adapter.

Expected execution result:

```text
Web/HTML Activity execution: RUNTIME UNAVAILABLE / R9 prerequisite
```

A structurally valid Web package may still appear in registry/discovery. That is not a simulator bug.

Forbidden substitutes:

```text
Safari/Chrome launch claimed as simulator PASS
simulator-only browser/webview
parallel DOM storage/input/Home APIs
```

After R9 lands, update this protocol to require injection of the same canonical Web adapter through the existing composition seam.

---

## 12. Evidence to preserve

Record:

```text
exact repository SHA
host OS / architecture
Python / Pygame versions
Tk availability
state-root path and whether --rebind-state was used
focused simulator suite result including skips
make verify result
workspace single-writer / child-PID lease smoke outcome
viewport/interface-size/capability matrix
profiles tested
Activity IDs/versions tested
source-load positive/negative outcomes
Stop/Restart while running outcome and process/resource checks
package install result or canonical host-unavailable result
Web runtime-unavailable result
screenshots where useful
first genuine failure if any
```

Label retained report:

```text
SIMULATOR / DEVELOPER EVIDENCE
```

---

## 13. Explicit non-claims

Even a complete PASS does not prove:

```text
untrusted-code isolation on developer host
production Bubblewrap/kernel/filesystem containment
physical host input denial
Xorg/KMSDRM/Wayland/compositor ownership/transitions
DRM/input device authority
trusted Home/Back non-coverability/input interception
physical controller/touch/audio/network/removable-media behavior
boot/initramfs/GRUB/installer continuity
Acer/Pi CPU/RAM/GPU/storage performance
Web runtime support before R9
full R10 update/remove/rollback/signature/revocation/save migration
R7/R8/R9/R10/R14 closure
```

Use the relevant VM/image/physical/security protocol for those claims.

---

## 14. Stop conditions

Stop and report the first genuine failure if:

- simulator needs another Greia service/policy implementation;
- simulator subclass replaces production rebuild/draw authority;
- Activity needs simulator-specific code;
- bootstrap can be shadowed by Activity content;
- simulator identity leaks into Activity launch context;
- missing capability is handled only by simulator UI;
- source loading follows symlinks, copies unverified content, or destroys last-known-good state on failed replacement;
- two control planes can write one workspace concurrently;
- a controller crash allows a second controller to adopt a workspace while its old Shell is still alive;
- control plane drops a live Shell handle/lease before confirmed exit;
- malformed/partial lock state is automatically discarded without proving ownership is dead;
- package testing requires a simulator extractor;
- Stop/Restart leaves Activity/session/broker resources alive;
- Web support needs a private browser path;
- a PASS claim requires relabeling simulator evidence as production/backend/physical/security proof.

Fix the shared abstraction or preserve an honest NOT-RUN/NOT-AVAILABLE boundary. Do not make the simulator more special.
