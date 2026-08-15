# Greia — Standalone Engineering Handover

**Date:** 2026-08-15  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4  
**Blocking phase:** **R7 — Direct graphics/session/input architecture**

## Resume order

Read `AGENTS.md`, `README.md`, `docs/DOCUMENTATION.md`, `docs/architecture/GREIA_ARCHITECTURE.md`, relevant accepted ADRs through ADR 0020, `docs/engineering/ENGINEERING_FOUNDATIONS.md`, applicable product requirements, the active remediation plan, this handover, agent operations, the Activity authoring skill, and the applicable testing procedure.

GitHub is canonical. Resolve actual branch HEAD before editing/testing.

## Hosted execution

Do **not** use, query, trigger or rerun GitHub Actions without explicit owner authorization for that specific hosted use. Repository source/PR operations remain allowed. No Actions service was used in the 2026-08-15 system-navigation/input tranches.

## Verification boundary

Last complete source gate genuinely executed:

```text
commit: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Everything newer is **UNPROVEN** unless explicitly recorded otherwise. No new PASS is claimed for current UI, creative, system-chrome, controller/input or Shell-input source.

## Mandatory Activity system navigation — ADR 0019

Product requirement:

```text
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
```

Normative architecture:

```text
docs/adr/0019-platform-owned-activity-system-navigation.md
```

Permanent behavior:

- Home is mandatory whenever a child-facing Activity is visible.
- Home is outside Activity rendering/input authority and uses one stable Greia location/graphic.
- Home ends the Activity through Greia lifecycle authority: graceful STOP first, then bounded forced return if required.
- Back is optional Greia navigation shown only for a meaningful previous Shell/Collection origin; it is not browser history or Activity-internal navigation.
- first-party Activities receive no exemption.
- pointer/touch/controller input reserved for system navigation must be consumed before Activity delivery.

Renderer-neutral source:

```text
src/greia_platform/system_chrome.py
```

Backend-neutral lifecycle/navigation seam:

```text
src/greia_launcher/system_chrome.py
```

It defines `SystemChromeBackend`, exact-generation leases/snapshots, `SystemChromeCoordinator`, `SystemChromeNavigationBridge`, `SystemNavigationRequest` and the narrow `ActivityStopController` protocol.

No concrete production `SystemChromeBackend` exists yet. The current Xorg/xinit path therefore remains unproven for the actual unforgeable overlay/protected-input guarantee.

## Phase-0 input/controller standard — ADR 0020

Product requirement:

```text
docs/product/ACTIVITY_INPUT_STANDARDS.md
```

Normative architecture:

```text
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
```

Controller/joystick support is a Phase-0 requirement, but Activities describe **interaction intent**, not controller brands or raw devices.

Current profiles:

```text
navigation
pointer
directional
game
text
hybrid
```

Learned baseline:

```text
navigation: arrows / D-pad-or-left-stick; Space/Enter / south face activate
simple game: arrows + Space; D-pad/left-stick + south face primary
pointer: mouse/touch plus Greia controller virtual pointer; south face primary
text: preserve real typing/editing semantics; do not steal Space/Enter/arrows
```

Keyboard, pointer, touch and controller can coexist. `controller` is a device capability, not an instruction that every Activity must require a gamepad.

The controller Guide/system control is platform-reserved where reliably available. No fallback multi-button Home chord is frozen yet; it requires accidental-activation evidence first.

Ordinary Activities must not receive broad `/dev/input` access merely for controller support.

## Input source implementation

Renderer/runtime-neutral input semantics:

```text
src/greia_platform/input_core.py
```

Current contracts include:

```text
InteractionProfile
InputSource
PhysicalControl
ControllerAxis
SemanticAction
InputEdge
SemanticInputEvent
MovementVector
StandardInputPolicy
StandardInputMapper
VirtualPointer
normalize_stick()
navigation_direction()
```

Important current centralized defaults are initial tuning values, not hardware facts:

```text
stick dead zone:              0.22
navigation threshold:         0.55
initial analog repeat delay:  0.36 s
repeat interval:              0.12 s
virtual-pointer speed:        screen-relative/bounded
```

Pygame adapter/trusted-controller helper:

```text
src/greia_platform/pygame_input.py
```

It translates SDL/Pygame controller constants immediately into brand-neutral Greia positional semantics and contains `PygameControllerSet`, a trusted bounded owner with current hard bounds:

```text
maximum simultaneously opened controllers: 4
maximum controller candidates scanned:      16
```

It has explicit start/refresh/close lifecycle and is **not** an Activity permission mechanism.

Typed device capability changes:

```text
src/greia_platform/hal.py
src/greia_platform/hal_legacy_x.py
src/greia_platform/device_capabilities.py
runtime/child-runtime.toml
```

`InputState` now includes controller availability while preserving its previous positional constructor meaning. `LinuxControllerPresenceProbe` conservatively detects conventional controller nodes without opening them; that is capability observation, not Activity authority.

## Activity input manifest / SDK

Current manifest contract accepts:

```toml
[input]
profile = "pointer"
```

`src/greia_platform/activities.py` validates the profile. Existing API 0.1 packages without `[input]` temporarily resolve to `hybrid` for compatibility.

The Supervisor places the validated profile in platform launch context as:

```text
GREIA_ACTIVITY_INPUT_PROFILE
```

Python SDK helper:

```python
get_input_profile()
```

This is descriptive context, not physical-device authority.

First-party reference declarations:

```text
org.greia.painting → pointer
org.greia.writing  → text
```

Neither requires `controller`, intentionally.

## Shell controller source boundary

Source-ready trusted Shell helper:

```text
src/greia_launcher/shell_input.py
```

`ShellInputController` owns:

- bounded `PygameControllerSet` lifecycle;
- controller-only semantic event translation so keyboard events cannot be double-handled;
- D-pad/south/east navigation semantics;
- left-stick navigation using centralized dead-zone and repeat policy;
- Guide remaining reserved/non-navigation;
- analog state reset at ownership boundaries.

Regression source:

```text
tests/test_shell_input.py
```

**Important:** `ShellInputController` is not yet composed into the large `src/greia_launcher/main.py` event loop. This is deliberate. The available repository write surface requires whole-file replacement for `main.py`; doing that before source verification would add disproportionate unexecuted risk. After focused PASS, make the smallest possible integration:

1. lazily construct/start `ShellInputController` after Pygame initialization;
2. feed only controller events to its semantic navigation path while preserving the existing keyboard handlers unchanged;
3. poll bounded left-stick navigation once per Shell loop;
4. close/suspend Shell controller ownership before launching an Activity and restart/reset it when Shell returns;
5. always close it in launcher shutdown cleanup;
6. do not combine this with the larger UI migration.

This Shell integration is useful but does **not** solve Activity controller delivery. Production Activity controller input still belongs to the R7 trusted semantic input broker/session layer described below.

## Critical production input boundary

The target architecture is now:

```text
physical keyboard / mouse / touch / controller
                  ↓
        Greia trusted input/session owner
                  ↓
     reserve Home/Back/system input first
                  ↓
       interaction-profile normalization
                  ↓
        runtime-neutral Activity input
             ┌─────────┴─────────┐
          Python/Pygame       Web/HTML
```

The current Activity sandbox does not receive broad `/dev/input`, and that must not be changed merely to make controller events appear in Pygame.

R7 must provide the production semantic controller/input bridge/broker so Activities can receive appropriate controller semantics without bypassing Greia's reserved system input. The same bridge model must be reusable by Web rather than each page implementing browser-specific Gamepad mappings.

## System/input regression source — committed but unexecuted

Current relevant tests include:

```text
tests/test_input_core.py
tests/test_pygame_input.py
tests/test_activity_input_contract.py
tests/test_hal_legacy_x.py
tests/test_shell_input.py
tests/test_system_chrome.py
tests/test_activity_ui.py
```

Coverage includes standard mappings, text-key preservation, Guide reservation, analog normalization, virtual-pointer bounds, controller capability separation, manifest compatibility/validation, bounded Pygame controller ownership, no keyboard double-handling in the Shell helper, analog repeat behavior, and trusted system-chrome lifecycle/action routing.

Pure tests cannot prove physical controller latency/reconnect, Activity raw-device denial under the selected backend, or real protected system-input interception.

## Physical controller acceptance protocol

Use:

```text
docs/testing/2026-08-15_PHASE0_INPUT_CONTROLLER_ACCEPTANCE.md
```

The protocol covers:

- source gate;
- Shell D-pad/left-stick/south-face navigation;
- keyboard/mouse coexistence;
- controller disconnect/reconnect;
- directional/game baseline;
- pointer-profile controller virtual pointer;
- Writing/text-key preservation;
- Guide/system-input interception;
- negative raw `/dev/input` evidence;
- Acer resource/latency measurements.

Remote `xdotool` keyboard/mouse injection is not physical controller evidence.

## UI/OOP foundation

ADR 0018 remains the lightweight UI foundation. `src/greia_platform/ui_core.py` owns renderer-neutral Screen/Overlay/Control/Collection/PagedGrid/BoundedCache/Invalidation/SurfaceNavigator semantics.

`docs/engineering/ENGINEERING_FOUNDATIONS.md` now explicitly requires controller/input ownership bounds, centralized mappings/dead zones, no per-Activity brand/raw-button stacks, no global controller-to-Linux-mouse architecture, and no broad Activity `/dev/input` authority.

## Phase-0 creative Activities

Writing (`org.greia.writing`) and Painting (`org.greia.painting`) remain source-implemented but execution/hardware-unproven. They now explicitly declare `text` and `pointer` input profiles respectively.

Painting has **not yet** been wired to a production controller virtual-pointer transport; Writing intentionally does not pretend a controller is a general typing device.

## R7 production state

```text
installed display path:       Xorg + xinit compatibility
status:                       PROVISIONAL
production compositor:        none selected
serial direct DRM:            evidence candidate only
trusted system chrome:        contract/coordinator/bridge source implemented; backend UNPROVEN
controller semantic core:     source implemented; UNPROVEN
trusted Pygame controller set: source implemented; Shell composition pending verification
production Activity input broker: NOT IMPLEMENTED
physical controller evidence: NOT RUN
```

R7 production acceptance now requires both ADR 0019 and ADR 0020:

- Home above arbitrary Activity content;
- protected pointer/touch/controller system input consumed before Activity input;
- Activity cannot suppress/replace Home;
- graceful and forced Home return;
- controller device ownership without broad raw Activity input access;
- Shell controller navigation;
- simple-game keyboard/controller mapping;
- pointer-profile virtual-pointer behavior;
- disconnect/reconnect recovery;
- Guide/system input intercepted before Activity delivery where supported;
- reusable semantic transport for Web;
- measured Acer resource/input-latency cost;
- no desktop/window-manager creep.

## Exact next source verification

On an owner-controlled current Linux checkout:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_input_core \
  tests.test_pygame_input \
  tests.test_activity_input_contract \
  tests.test_hal_legacy_x \
  tests.test_shell_input \
  tests.test_system_chrome \
  tests.test_ui_core \
  tests.test_ui_core_lifecycle \
  tests.test_activity_ui \
  tests.test_core_creation_activities \
  tests.test_activity_theme_access \
  -v

PYTHONPATH=src python3 tools/validate_activity.py activities/writing
PYTHONPATH=src python3 tools/validate_activity.py activities/painting

PYTHONPATH=src python3 -m unittest discover \
  -s tests \
  -p 'test_developer_remote.py' \
  -v

make verify
```

Stop on the first real failure and preserve exact stdout/stderr. Do not weaken contracts to manufacture PASS.

## Next implementation after source PASS

Keep the sequence narrow:

1. minimally compose `ShellInputController` into `greia_launcher.main` with explicit suspend/resume/cleanup around Activity launch;
2. verify Shell D-pad/left-stick/south-face navigation and reconnect on owner-controlled hardware;
3. design/implement the R7 trusted physical-input broker/bridge beside the system-chrome/display-session authority so controller events can reach Activities semantically without `/dev/input` access;
4. integrate `pointer` virtual-pointer semantics with Painting as the first spatial reference;
5. add one simple directional/game reference proving arrows+Space and D-pad/stick+south-face parity;
6. prove Guide/system input is withheld from Activity content;
7. measure Acer resource/latency behavior using `docs/testing/2026-08-15_PHASE0_INPUT_CONTROLLER_ACCEPTANCE.md`;
8. later expose the same semantic bridge to the Web runtime.

Do not combine step 1 with the pending broad Shell UI migration. Do not invent a controller Home chord before child accidental-activation evidence.

## Existing R7 evidence

Use the existing graphics/session protocol:

```text
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
```

Its existing scanout/seat evidence predates ADR 0019/0020 and therefore cannot by itself close trusted chrome or controller/input requirements.

## Invariants

- no visible Linux UI in normal child operation;
- Activity remains runtime-neutral;
- every child-facing Activity retains Greia-owned Home outside Activity rendering/input authority;
- controller/joystick support is a Phase-0 platform concern, not per-Activity hardware code;
- Activities declare interaction intent, not controller brands/raw indices;
- simple game defaults remain arrows+Space and D-pad/left-stick+south-face;
- pointer Activities may use Greia virtual-pointer semantics; text Activities keep real typing semantics;
- ordinary Activities do not gain raw `/dev/input` merely for controller support;
- Guide/system input is platform-reserved where supported;
- progression/rewards remain platform-owned;
- child state remains portable/profile-scoped;
- Acer remains the extreme resource floor and ARM remains co-equal;
- no unauthorized hosted execution;
- no desktop/window-manager architecture;
- strong OOP/polymorphic seams with bounded resource ownership;
- source/VM/physical evidence boundaries remain explicit and honest.
