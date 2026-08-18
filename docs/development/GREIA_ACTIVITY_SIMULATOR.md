# Greia Activity Simulator — Developer Guide

**Status:** initial Mac-first developer implementation  
**Architecture:** ADR 0029  
**Evidence class:** developer/source/runtime-semantic only; never a substitute for image/backend/physical acceptance

## 1. What this tool is

The Greia Activity Simulator runs the **real Greia child Shell and platform services** on a synthetic device profile. It lets an Activity developer test ordinary Greia behavior without installing Greia OS or booting a VM.

The control window chooses the synthetic device. A separate Greia window is the actual child environment using the repository's real profile picker, launcher, Activity registry/trust, PermissionBroker, RuntimeManager, lifecycle supervision, profile-scoped storage/history/events, My Greia state and responsive/canvas/system-safe primitives.

Only missing physical-machine facts are synthetic: viewport geometry and semantic HAL capabilities, plus a narrow desktop Pygame display adapter for current Python Activities.

## 2. Start it

From the Greia repository root on macOS (or another desktop Python environment with Tk and current Greia Python dependencies):

```bash
python3 tools/greia_simulator.py
```

Optional isolated state directory:

```bash
python3 tools/greia_simulator.py --state-dir ~/.greia-simulator-my-project
```

Default state is `~/.greia-simulator`. Simulator state must remain outside the checkout.

## 3. Synthetic device controls

Initial viewport presets are:

```text
Acer / low-resource 1024x600
HD 1280x720
Tablet 1280x800
Laptop 1366x768
Full HD 1920x1080
```

The viewport field accepts bounded custom `WIDTHxHEIGHT` values.

Capability switches use Greia's semantic names: keyboard, pointer, touch, controller, audio.basic, network, removable_media and power.controlled_shutdown. `display` is always present.

These switches build a real synthetic `GreiaHAL`; the real runtime/permission compatibility path consumes the resulting `DeviceCapabilityService` snapshot. Press **Start / Apply** after changing device facts. The initial implementation restarts the synthetic child session rather than mutating hardware truth beneath a live Activity.

## 4. Profile and My Greia settings

The quick **Child interface size** selector writes the first simulator profile's real `UiPreferencesStore` value: `compact`, `normal` or `large`. The profile-aware launcher then supplies the same `GREIA_INTERFACE_SIZE` context as Greia OS.

For colors, wallpaper and avatar, launch the actual **My Greia** Activity in the simulator. This tests the real child flow and persistence rather than a duplicate settings form.

Language controls are intentionally not faked while profile-language persistence/end-to-end ADR-0028 integration remains incomplete. Add them only through the future authoritative store/service.

## 5. Load Activity Folder…

Use **Load Activity Folder…** for iterative development. The simulator:

1. copies the source into private staging;
2. removes only normal VCS/Python cache residue;
3. validates it with the real `RuntimeCatalogue` + `ActivityRegistry` together with built-in identity authority;
4. assigns `DEVELOPER_UNSIGNED` trust;
5. stages it under `developer-activities/<activity-id>/`;
6. validates the final developer source again;
7. leaves hot discovery/rescan to the actual Greia launcher.

It does not invent another manifest parser or grant built-in trust. Reload by choosing the same source folder again after edits.

A managed copy is used instead of a symlink because Greia package validation forbids symlinks and the runtime should not write incidental state into the developer source directory.

## 6. Install Activity Package…

Use **Install Activity Package…** to test a distributable archive. This calls the real `ActivityPackageService` against the isolated simulator package root, exercising current bounded archive validation, package trust, immutable versions, receipts and atomic activation.

A successful simulator install does not prove future R10 update/removal/signature/revocation/save-migration behavior.

## 7. Python Activity resolution behavior

Current Pygame Activities often request `pygame.display.set_mode((0, 0), pygame.FULLSCREEN)`. On a desktop that would use the developer's physical display instead of the synthetic Greia viewport.

The simulator's `SimulatorPythonRuntimeAdapter` launches through:

```text
python -m greia_simulator.python_activity <validated-entrypoint>
```

Inside that child process only, the bootstrap maps Pygame `set_mode()` to the chosen synthetic viewport and removes fullscreen. Everything else remains the normal Greia launch: manifest/runtime validation, capability/permission authority, lifecycle READY/STOP, Activity data, Storage/Event brokers and profile/theme/interface-size context.

Activity source should contain **no simulator-specific layout branch**. A resolution bug belongs in the Activity's Greia responsive/canvas implementation.

## 8. Suggested responsive pass

```text
1024×600  + normal
1024×600  + large
1280×800  + normal
1366×768  + compact
1920×1080 + normal
```

Then try an awkward custom aspect ratio for complex layouts. Check reachability, protected Home/Back geometry, readability, aspect ratio, render/hit-transform agreement, collection reflow/scrolling and the selected ADR-0027 canvas/world policy.

Simulator visual testing supplements automated geometry/property tests and physical 1024×600 readability/performance acceptance; it never replaces them.

## 9. Capability testing

If an Activity requires touch, disable `touch` and confirm Greia rejects compatibility rather than letting Activity code decide hardware suitability. For optional controller support, toggle `controller` and check semantic fallback.

The controller checkbox proves capability-policy behavior only. It does not prove physical mappings, latency, noisy axes, reconnect, Guide reservation or production `/dev/input` ownership.

## 10. Workspace layout

```text
~/.greia-simulator/
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

Built-in Activities, assets and runtime policy come from the real source checkout via development `GREIA_OS_ROOT`; mutable simulator state stays elsewhere.

## 11. HTML/Web Activities

Greia architecture intends Web/HTML to be first-class and the simulator is designed to consume it. **Current source does not yet have the canonical Web runtime adapter.** R9 owns engine selection and integration after R7 prerequisites.

The simulator therefore intentionally does not launch an HTML package in a host browser or private webview. When the canonical `WebRuntimeAdapter` exists, add that same adapter to simulator `RuntimeManager` composition and feed it synthetic device/session backends. Do not create simulator-only DOM storage/input/Home semantics.

## 12. What a simulator PASS means

Useful claims include: real package/source validation; launcher discovery; synthetic capability policy; launch through real runtime/lifecycle/profile/storage/history services; real shared layout/canvas code at selected viewport; real child visual context; current local package transaction.

It can never replace claims about Bubblewrap/kernel isolation, production display/session backend, trusted system-chrome non-coverability/input interception, physical controller/touch/audio/network/media, boot/installer/initramfs, Acer/Pi resource performance, or R7/R8/R9/R10/R14 closure.

## 13. Troubleshooting

- **Tk unavailable:** use a developer Python distribution with Tk. This is control-plane packaging, not Greia OS architecture.
- **Activity validation failure:** fix the real validation error; do not bypass the registry by copying directly into the developer root.
- **Activity not visible:** allow the launcher's bounded rescan interval or Restart after fixing the invalid tree.
- **Activity takes over the desktop:** treat that as simulator/runtime-adapter defect; do not add simulator conditionals to Activity layout.
- **Unix socket path too long:** choose a shorter `--state-dir`. The simulator deliberately keeps the real bounded broker transport.

## 14. Alignment rule

Before changing the simulator, read ADR 0029 and the exact production service being touched. A simulator change is suspect if it introduces a second implementation of a Greia concept that already has an owner. When production manifest/runtime/profile/layout/input/package/lifecycle contracts change, update simulator source/tests and this guide in the same tranche when affected.
