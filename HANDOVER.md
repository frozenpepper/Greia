# Greia — Standalone Engineering Handover

**Date:** 2026-08-15  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4  
**Blocking phase:** **R7 — Direct graphics/session architecture**

## Resume order

Read `AGENTS.md`, `README.md`, `docs/DOCUMENTATION.md`, the architecture synthesis, relevant accepted ADRs through ADR 0019, `docs/engineering/ENGINEERING_FOUNDATIONS.md`, applicable product requirements, the active remediation plan, this handover, agent operations, the Activity authoring skill, and the applicable testing procedure.

GitHub is canonical. Resolve actual branch HEAD before editing/testing.

## Hosted execution

Do **not** use, query, trigger or rerun GitHub Actions without explicit owner authorization for that specific hosted use. Repository source/PR operations remain allowed. No Actions service was used in this tranche.

## Verification boundary

Last complete source gate genuinely executed:

```text
commit: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Everything newer is **UNPROVEN** unless explicitly recorded otherwise. No new PASS is claimed for the current UI, creative or system-chrome source.

## Mandatory Activity system navigation

Accepted product requirement:

```text
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
```

Normative architecture:

```text
docs/adr/0019-platform-owned-activity-system-navigation.md
```

Permanent behavior:

- **Home is mandatory** whenever a child-facing Activity is visible.
- Home uses one stable Greia location/graphic with a child-sized hit target.
- Home is outside Activity rendering and input authority.
- Activity code cannot hide, move, restyle, cover, disable, replace or intercept the real Home control.
- Home ends the Activity through Greia lifecycle authority: graceful STOP first, then bounded forced return when required.
- **Back is optional Greia navigation**, shown only when Greia has a distinct previous Shell/Collection launch origin.
- Back ends the Activity and returns to that Greia origin. It is not browser history or Activity-internal navigation.
- first-party Activities receive no exemption.

Renderer-neutral source:

```text
src/greia_platform/system_chrome.py
```

Current source owns:

```text
SystemNavigationAction.HOME
SystemNavigationAction.BACK
UiRect
ActivitySystemChromeLayout
```

At 1024×600 the current layout is approximately:

```text
Home hit target: 60×60 px
Back hit target: 60×60 px
visible glyph:   36 px
protected area:  about 142×76 px, top-left
```

The complete Home+Back footprint remains reserved even when Back is absent.

Backend-neutral lifecycle seam:

```text
src/greia_launcher/system_chrome.py
```

It defines `SystemChromeBackend`, `SystemChromeCoordinator`, exact-generation leases/snapshots and fail-closed action validation.

Canonical Pygame glyph helpers now include `draw_home_symbol` and `draw_back_symbol`, exposed through `pygame_ui.py` and the current `activity_ui.py` compatibility implementation.

## Critical runtime boundary

**No concrete production `SystemChromeBackend` exists yet, and the current installed Xorg/xinit path does not yet compose the new coordinator.**

Therefore no claim is made yet that a real Activity cannot cover/intercept Home, that protected input is withheld from Python/Web content, or that Home has been exercised against a frozen Activity on target hardware.

This is intentional. Drawing Home inside a Python Activity or injecting it into Web content would violate ADR 0019 even if it looked correct.

R7 must provide:

```text
Greia display/session authority
├── mandatory Home / optional Back + protected input
└── Activity surface
    ├── Python/Pygame
    ├── future Web/HTML
    └── future runtimes
```

A serial direct-DRM design giving the Activity uncontested framebuffer/input ownership cannot close production R7 unless another trusted layer preserves the system chrome and protected input.

## System-chrome regression source

Committed but unexecuted:

```text
tests/test_system_chrome.py
tests/test_activity_ui.py
```

Coverage includes fixed Home geometry, reserved Back footprint, Back availability, child-sized hit geometry, coordinator lifecycle, Home action independent of Activity participation, invalid Back rejection and stale-lease rejection.

Pure tests cannot prove real display/input isolation; that requires backend/runtime evidence.

## UI/OOP foundation

ADR 0018 remains the lightweight UI foundation. `src/greia_platform/ui_core.py` owns renderer-neutral Screen/Overlay/Control/Collection/PagedGrid/BoundedCache/Invalidation/SurfaceNavigator semantics. Mandatory system Home/Back is explicitly **not** an Activity Overlay; ADR 0019 places it at a higher trust layer.

`docs/engineering/ENGINEERING_FOUNDATIONS.md` remains mandatory: cohesive OOP concepts, purposeful polymorphism, composition-first design, explicit dependencies/lifecycles, bounded resources, simple extension seams and useful public documentation.

## Phase-0 creative Activities

Writing (`org.greia.writing`) and Painting (`org.greia.painting`) remain source-implemented but execution/hardware-unproven. They receive no exemption from ADR 0019.

## R7 production state

```text
installed path:         Xorg + xinit compatibility
status:                 PROVISIONAL
production compositor:  none selected
serial direct DRM:      evidence candidate only
trusted system chrome:  source contract/seam implemented; concrete backend UNPROVEN
```

R7 production acceptance now also requires:

- platform Home rendered above arbitrary Activity content;
- protected Home/Back input consumed before Activity input;
- Activity cannot suppress or replace Home;
- Home graceful-stop plus forced-return behavior for an unresponsive Activity;
- identical external system-chrome semantics for future Web runtime;
- measured resource cost on the Acer floor;
- no desktop/window-manager creep.

## Exact next source verification

On an owner-controlled current Linux checkout:

```bash
PYTHONPATH=src python3 -m unittest \
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

Stop on first real failure and preserve exact stdout/stderr. Do not weaken contracts to manufacture PASS.

## Next system-chrome/R7 implementation

After source PASS:

1. compose `SystemChromeCoordinator` into installed Activity lifecycle beside `DisplaySessionCoordinator`, without making `ActivitySupervisor` a renderer;
2. implement/prototype the smallest trusted R7 overlay/input backend;
3. route Home into the existing authoritative `ActivitySupervisor.request_stop()` path;
4. preserve a Greia launch-origin token for optional Back; the current flat Activity catalogue has no distinct nested origin, so Back should remain unavailable there;
5. prove overlay/input authority with real Python Activity content;
6. measure resource cost versus current Xorg and direct-ownership candidates on the Acer floor;
7. later reuse the same external layer for Web rather than adding DOM controls.

Once a production backend is selected, installed composition should fail closed if mandatory Home cannot be prepared/preserved.

## Existing R7 evidence

Use the existing local protocol in `docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md`. Its existing scanout evidence predates ADR 0019 and therefore cannot by itself close the new trusted-chrome requirement.

## Invariants

- no visible Linux UI in normal child operation;
- Activity remains runtime-neutral;
- every child-facing Activity retains Greia-owned Home outside Activity rendering/input authority;
- Greia Back, when shown, returns to Greia launch origin and is not browser history;
- progression/rewards remain platform-owned;
- child state remains portable/profile-scoped;
- Acer remains the extreme resource floor and ARM remains co-equal;
- no unauthorized hosted execution;
- no desktop/window-manager architecture;
- strong OOP/polymorphic seams with bounded resource ownership;
- source/VM/physical evidence boundaries remain explicit and honest.
