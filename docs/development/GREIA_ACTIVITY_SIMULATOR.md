# Greia Activity Simulator — Developer Guide

**Status:** hardened Mac-first developer implementation; current-head execution still required before PASS claims  
**Architecture:** ADR 0029  
**Evidence class:** developer/source/runtime-semantic only; never image/backend/physical/security acceptance

## 1. What this tool is

The Greia Activity Simulator runs the **real Greia child Shell and platform service graph** against synthetic device facts. It lets an Activity developer exercise ordinary Greia behavior without installing Greia OS or booting a VM.

The control window is desktop developer tooling. The separate Greia child window is the actual `GreiaChildShell`, using the repository's real profile picker, launcher, Activity registry/trust, PermissionBroker, RuntimeManager, ActivitySupervisor, storage/history/events, My Greia state and responsive/canvas/system-safe primitives.

The simulator injects only missing-machine variation:

```text
exact synthetic viewport
semantic synthetic GreiaHAL facts
SimulatorPythonRuntimeAdapter for current direct-Pygame display compatibility
isolated workspace roots
```

Permission/storage/history/lifecycle composition is not reimplemented in `greia_simulator`.

## 2. Safety boundary — read this before loading code

**The desktop simulator is not an untrusted-code security sandbox.**

Source-mode Activity execution does not prove or reproduce production Bubblewrap/kernel/filesystem containment. Run only Activity source and packages you trust on your developer computer.

Capability toggles test the real Greia semantic compatibility/grant path. Disabling `pointer`, `network`, etc. does **not** physically revoke the developer account's underlying host permissions. Do not treat the simulator as malware isolation.

## 3. Start it

From the Greia repository root on macOS with Tk, Pygame and current Greia Python dependencies:

```bash
python3 tools/greia_simulator.py
```

Optional isolated workspace:

```bash
python3 tools/greia_simulator.py --state-dir ~/.greia-simulator-my-project
```

Default state is `~/.greia-simulator`. State must stay outside the checkout.

A workspace is bound to the Greia checkout that created it and held by one active control-plane writer. The lease also records the owned Greia Shell PID while a child Shell exists. That second PID matters after crashes: if the desktop control plane dies but its Shell survives, a new simulator instance must **not** reuse the same mutable workspace just because the controller PID is gone.

If you deliberately want to reuse an inactive workspace with another checkout:

```bash
python3 tools/greia_simulator.py \
  --state-dir ~/.greia-simulator-my-project \
  --rebind-state
```

Do not use `--rebind-state` casually: checkout identity is there to prevent stale source/runtime policy and profile/package state from being silently mixed. Rebinding is only performed after the process owns the workspace writer lease.

## 4. Synthetic viewport and capabilities

Viewport presets are geometry only:

```text
Reference 1024x600
1280x720
1280x800
1366x768
1920x1080
```

They do **not** emulate an Acer, tablet, CPU, RAM, GPU, storage speed, architecture or touch panel. Use the bounded custom `WIDTHxHEIGHT` field for other shapes.

Capability checkboxes are derived from the current canonical `RuntimeCatalogue.allowed_capabilities`; the simulator does not maintain a separate allowed vocabulary. The current HAL mapping covers:

```text
display
keyboard
pointer
touch
controller
audio.basic
network
removable_media
power.controlled_shutdown
```

`display` is always present. If Greia adds a canonical capability not mapped by the synthetic HAL, simulator startup/tests should fail until that mapping is deliberately implemented.

Changing device facts is applied by restarting the child Shell. The simulator does not mutate device authority under a live Activity.

## 5. Profile and My Greia settings

The control plane has an explicit **child profile selector**. `compact`, `normal` or `large` is written for that named profile through the real `UiPreferencesStore`; it is not a shadow setting and it does not silently modify profile index zero.

For colors, wallpaper and avatar, use the actual **My Greia** Activity. This exercises normal permissions and profile persistence.

Language controls remain absent until the authoritative profile-language flow is fully integrated. Do not invent a simulator-only language preference.

## 6. Load Activity Folder…

Use **Load Activity Folder…** for trusted iterative source development.

The loader treats source acquisition as a bounded transaction:

1. source/state containment in either direction is rejected;
2. a finite lstat-based source snapshot is inspected before managed copying;
3. VCS/cache residue explicitly owned by this workflow may be omitted;
4. symlinks are rejected rather than followed;
5. special files, executable Activity files and canonical forbidden content are rejected;
6. source bytes are bounded by `RuntimeCatalogue.maximum_activity_bytes` before copying;
7. each inspected file is content-fingerprinted and the copy rechecks inode/type/size/mtime plus the exact bytes copied, so a same-size/metadata source mutation is still rejected;
8. staged content is validated by the real `ActivityRegistry` together with built-in identity authority;
9. it receives `DEVELOPER_UNSIGNED` trust;
10. replacement publication is atomic/transactional;
11. an existing last-known-good managed copy is restored if final registry discovery fails;
12. the normal launcher rescan discovers the final copy.

A managed copy is used rather than a symlink because Greia package validation forbids package symlinks and developer source should not receive runtime incidental state.

Reload the same source folder after edits. A rejected reload must leave the previous valid managed copy intact.

## 7. Install Activity Package…

Use **Install Activity Package…** for a distributable `.greiaactivity`/ZIP transaction. The simulator lazily loads and calls the real `ActivityPackageService` against the isolated package root.

There is no simulator extractor/install fallback. If the host cannot import/run the canonical package service (for example because its current lock backend is not portable there), package-install testing is unavailable on that host while the rest of the simulator remains usable.

A simulator package PASS covers only the currently implemented local new-install transaction. It does not close R10 update/removal/signature/revocation/save-migration work.

## 8. Python Activity display behavior

Current Pygame Activities may still request:

```python
pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
```

The simulator wraps the canonical `PythonRuntimeAdapter` command with one **absolute Greia-owned bootstrap path**. It does not resolve the bootstrap via `python -m` from the Activity working directory.

Conceptually:

```text
<canonical-python> /absolute/greia/src/greia_simulator/python_activity.py \
  --viewport 1024x600 \
  <validated-entrypoint>
```

The bootstrap imports trusted Pygame first, forces only `pygame.display.set_mode()` onto the selected synthetic viewport and removes fullscreen. `ActivitySupervisor` still supplies the normal sanitized launch environment, lifecycle channel, storage/event brokers and profile visual context.

The bootstrap explicitly restores the trusted Greia `src/` root because the normal supervisor strips inherited `PYTHONPATH`. Trusted Greia source stays ahead of Activity content in `sys.path`.

No `GREIA_SIMULATOR`, simulator viewport or preset name is an Activity-facing API. Stale `GREIA_SIMULATOR*` values are removed before Activity code executes.

This display interception is temporary R7 compatibility debt. It is **not** a universal SDL/display emulator and must not grow into broad simulator monkeypatching. The long-term fix is the shared Greia Activity display/surface abstraction.

## 9. Shell display and Stop / Restart

The child Shell uses shared launcher display-policy hooks for its exact synthetic viewport. The simulator does not replace `_draw()` or clear launcher private caches itself; ordinary Shell resize observation/cache invalidation remains authoritative.

Stop/Restart is lifecycle-aware. The control plane sends SIGTERM to the simulator Shell; the Shell unwinds to the normal cleanup boundary and then, when an Activity is active:

```text
request_stop through ActivitySupervisor
poll to a bounded graceful deadline
force_stop(... SYSTEM_SHUTDOWN) if still alive
poll bounded forced cleanup
```

Only if the Shell itself fails to exit within the control-plane deadline does the host control plane hard-kill the Shell process. Activity processes are not assumed to die merely because their Shell is gone.

Process ownership is fail-closed:

- the desktop controller keeps its `Popen` handle until child exit is confirmed;
- the workspace lease records the Shell PID immediately after spawn;
- the Shell PID is cleared from the lease before the dead process handle is dropped;
- Start refuses to spawn another Shell if the previous process or ownership record cannot be cleaned up;
- the workspace lock cannot be released while a child PID remains registered;
- if the controller crashes but the recorded Shell is still alive, POSIX stale-lock recovery keeps the workspace locked.

The control plane also polls Shell health and reports a real unexpected exit code rather than continuing to claim it is running.

## 10. Suggested responsive pass

After the source contract gate is green, exercise at least:

```text
1024×600  + normal
1024×600  + large
1280×800  + normal
1366×768  + compact
1920×1080 + normal
1111×700  + an appropriate semantic size
```

Check reachability, protected Home/Back geometry, readability, aspect ratio, render/hit-transform agreement, collection reflow/scrolling and the selected ADR-0027 canvas/world policy.

A fix must live in normal Activity/shared responsive code. Activity source must not branch on simulator identity, preset name or hardware model.

Visual simulator testing supplements automated geometry/property tests and physical reference acceptance; it does not replace them.

## 11. Capability testing

If an Activity requires `touch`, disable `touch`, restart/apply and confirm the **normal PermissionBroker/RuntimeManager path** rejects the missing required capability.

For optional controller support, toggle `controller` and verify semantic fallback remains launchable.

These results prove Greia capability-policy behavior only. They do not prove physical mappings, latency, noisy axes, reconnect, Guide reservation, host input suppression or production `/dev/input` ownership.

## 12. Workspace layout

```text
~/.greia-simulator/
├── workspace.json          # schema + owning checkout
├── .workspace.lock         # controller PID + owned Shell PID writer lease
├── profiles/
├── run/
├── developer-activities/
├── activity-packages/
│   ├── active/
│   ├── versions/
│   ├── staging/
│   └── receipts/
└── media/
```

Built-in Activities/assets/runtime policy come from the real checkout via `GREIA_OS_ROOT`. Mutable state stays outside it.

Lock recovery is intentionally conservative. On POSIX, a syntactically valid lease is automatically discarded only when both its controller PID and any recorded Shell PID are no longer alive. A partial/malformed lease fails closed because it may have been observed during a concurrent lease rewrite. On non-POSIX hosts the current implementation also fails closed rather than using POSIX-style `os.kill(pid, 0)` probing with unsafe Windows semantics.

## 13. HTML/Web Activities

Greia intends Web/HTML Activities to be first-class, but current source still has no canonical Web runtime adapter.

A package with a syntactically valid `runtime.type = "web"` can be structurally registry-valid; current failure is correctly a RuntimeManager/launch-time **runtime unavailable** result. Do not add an artificial simulator registry rejection just to make the error earlier.

Do not open the package in Safari/Chrome or embed a simulator-only webview. When R9 lands, inject the same canonical Web adapter through the existing launcher composition seam.

## 14. Current source regression scope

`tests/test_greia_simulator.py` is expected to lock:

```text
canonical runtime-service composition with injected adapter/HAL
no simulator replacement of Shell _rebuild_runtime_services or _draw
absolute bootstrap / shadow resistance
no Activity-visible simulator identity
canonical capability vocabulary coverage
shared Shell display-policy hooks
workspace checkout binding + single writer
partial/non-POSIX lock fail-closed behavior
workspace controller + Shell PID lease ownership
control-plane Start/Stop process-handle + child-PID registration semantics
named-profile UI preference persistence
source load positive + collision/symlink/oversize/overlap/rollback negatives
content-fingerprinted source snapshot TOCTOU rejection
canonical package-service delegation
valid-but-unavailable runtime behavior
bounded supervisor Stop/force-stop escalation
real local Python READY/storage/event/history/STOP integration when Pygame is installed
```

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_greia_simulator -v
```

Then the affected launcher/runtime/supervisor suites and finally `make verify` on an owner-controlled checkout. The existence of these tests is not itself a PASS.

## 15. What a simulator PASS means

A properly executed simulator PASS may support claims about:

```text
real package/source validation and trust
real launcher discovery
real semantic capability policy against synthetic HAL facts
real runtime/lifecycle/profile/storage/history/events in desktop composition
real shared layout/canvas behavior at selected viewport
real child visual context
current canonical local package transaction where available
```

It cannot prove:

```text
production Bubblewrap/kernel/filesystem containment
physical host input denial
production Xorg/KMSDRM/Wayland/compositor ownership
trusted system-chrome non-coverability/input interception
physical controller/touch/audio/network/removable-media behavior
boot/installer/initramfs
Acer/Pi CPU/RAM/GPU/storage performance
Web support before R9
R7/R8/R9/R10/R14 closure
```

## 16. Troubleshooting

- **Tk unavailable:** install/use a developer Python with Tk; this is control-plane packaging, not Greia OS architecture.
- **Workspace already in use:** close the other simulator using that state root, or choose a separate `--state-dir`; do not delete a live lock to force two writers.
- **Controller crashed but Greia Shell is still alive:** stop that actual Shell first. The recorded child PID intentionally prevents a second control plane from adopting the same workspace while the orphan remains.
- **Malformed/partial lock:** do not delete it blindly. Confirm no simulator controller or Shell from that workspace is alive before manual recovery; the automatic path fails closed because ownership cannot be reconstructed safely from corrupt lease data.
- **Workspace belongs to another checkout:** choose another state root or deliberately use `--rebind-state` only after the old simulator/Shell is inactive.
- **Activity source rejected for symlink/special/size/content:** fix the source; do not bypass managed staging.
- **Activity not visible:** allow the bounded launcher rescan or Restart after correcting the invalid tree.
- **Activity takes over the physical desktop:** simulator/runtime-adapter defect; do not add Activity-side simulator branches.
- **Package install unavailable on host:** this is a canonical package-service portability limitation; do not implement a simulator unzip fallback.
- **Unix broker socket path too long:** use a shorter state/runtime path appropriate to the host; the simulator deliberately retains real broker transport semantics.

## 17. Alignment rule

Before changing the simulator, read ADR 0029, the adversarial review, the hardening response and the exact production owner being varied. A simulator change is suspect when it copies a production service method instead of adding/using a narrow shared seam.

When manifest/runtime/profile/layout/input/package/lifecycle/display contracts change, update simulator source, regressions and this guide in the same tranche. Keep R7/R9/R10 and physical/security evidence boundaries explicit.
