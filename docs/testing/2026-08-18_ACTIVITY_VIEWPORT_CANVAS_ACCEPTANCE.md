# Greia — Activity Viewport / Canvas / World-Camera Acceptance

**Date:** 2026-08-18  
**Audience:** owner-controlled local coding/test agent  
**Applies with:**

```text
docs/testing/2026-08-18_LOCAL_AGENT_FULL_TEST_AND_FIX_SESSION.md
docs/testing/2026-08-18_RESPONSIVE_UI_ACCEPTANCE.md
```

**Architecture:** ADR 0026 + ADR 0027  
**Design guide:** `docs/design/GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md`

---

## 0. Mandatory goal

Greia Activity authors must be able to author one Activity without maintaining per-resolution geometry.

The local agent is authorized to refactor first-party Activities and shared UI/viewport helpers to achieve this. Do not preserve raw physical coordinate logic merely because it works at 1024×600.

`1024×600` is the default **logical reference authoring canvas**, not the physical display contract.

---

# 1. Source tests first

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_responsive_layout \
  tests.test_activity_viewport \
  tests.test_ui_motion_scroll \
  tests.test_launcher_presentation \
  -v
```

If a genuine source defect is found, fix root cause, add/retain regression coverage, rerun focused tests, then rerun `make verify` before calling the tranche source-clean.

Do not claim PASS for tests not executed.

---

# 2. Audit every first-party Activity for its spatial model

Current built-ins:

```text
activities/painting
activities/writing
activities/shape_garden
activities/workshop_settings
```

For each Activity, explicitly classify each visual layer as one of:

```text
fluid
reference_canvas
world_camera
hybrid
```

Record the classification in the session result.

If the Activity is hybrid, list each layer separately.

---

# 3. Forbidden pattern audit

Treat these as defects or explicit migration debt:

- raw physical positions that assume one screen size (`x=48`, `ground=70px`, etc.) for semantic/game objects;
- a chain of resolution-specific coordinate tables;
- device-name-specific Activity layout;
- x/y non-uniform stretching to fit another aspect ratio;
- hit testing in physical coordinates when rendering uses reference/world scaling;
- saved state containing screen-specific button/card positions;
- game physics expressed in current monitor pixels when they should be world units;
- a world larger than the screen represented as one giant display-sized bitmap;
- essential Activity controls placed beneath Greia protected Home/Back chrome;
- separate pointer hit rectangles not derived from the rendered/layout geometry.

Small local pixel constants are not automatically wrong. The problem is making physical resolution the semantic coordinate system.

---

# 4. Reference-canvas acceptance

Create or use a representative fixed Activity/puzzle path using:

```text
reference: 1024×600 logical units
fit: contain
```

Verify across the responsive resolution matrix:

- the complete logical view remains visible;
- aspect ratio is preserved;
- letterbox/pillarbox regions do not receive false logical pointer coordinates;
- a point rendered at one logical coordinate is hit at the same logical coordinate after physical→logical mapping;
- no per-resolution author branch is needed.

Also exercise `cover` with a deliberately bleed-safe scene and verify that only outer expendable logical content is cropped.

---

# 5. World-camera acceptance

Create/use a representative world-camera test with:

```text
reference camera: 1024×600 logical units
fit: expand
camera center: arbitrary world coordinates
```

At minimum compare:

```text
800×600
1024×600
1366×768
1920×1080
```

Verify:

- camera center remains the same world coordinate;
- 16:9/wider screens reveal additional horizontal world rather than stretching it;
- 4:3/taller screens reveal additional vertical world rather than changing physics;
- world→physical→world round-trip is stable;
- culling can use `visible_logical_rect`;
- changing resolution does not mutate world positions, collision coordinates, gravity, speeds or saved level data.

A side-scroller does **not** need to exist in the current built-ins for this source-level acceptance; the platform primitive must nevertheless be exercised because future Activities require it.

---

# 6. Hybrid acceptance

At minimum Painting should be reviewed as a hybrid candidate:

```text
fluid toolbar/palette
logical document canvas
platform system chrome
```

Verify that resizing the Activity viewport changes editor presentation, not the painting document's durable semantic dimensions/content.

Likewise, Writing should normally behave as fluid UI/content:

- toolbar remains reachable;
- editor consumes remaining space;
- text rewraps according to current editor width;
- stored text does not change merely because line wrapping changed;
- cursor hit testing remains aligned after resize.

---

# 7. Shape Garden migration requirement

The current Shape Garden implementation historically used raw physical screen coordinates for several semantic elements. Treat it as a deliberate migration probe.

Refactor it to an appropriate Greia spatial model rather than adding resolution conditionals.

Likely choices:

- fixed/reference canvas if the scene is intended to preserve exact authored composition; or
- fluid/hybrid if the play field should genuinely consume available safe space.

The agent must decide from gameplay intent and document the choice. Do not simply multiply every physical coordinate by a global width/height ratio without considering system chrome, aspect ratio and input mapping.

Add regression coverage for the resulting shared behavior where practical.

---

# 8. Safe UI / system chrome acceptance

For each model:

- verify `ActivityViewport` receives/derives protected Greia system-chrome geometry;
- verify `safe_ui_rect()` does not overlap protected regions;
- verify essential UI uses safe geometry or an equivalent platform-owned exclusion-aware layout;
- verify background/world rendering may use the full surface without gaining input authority in protected chrome;
- verify the Activity does not draw fake Home/Back controls as a substitute.

On 1024×600 specifically, ensure the safe-area behavior does not make the Activity visually absurd or wasteful. If the shared safe-region selection needs improvement, fix the shared policy rather than adding an Acer branch.

---

# 9. Pygame convenience acceptance

Exercise:

```text
greia_platform.pygame_ui.PygameReferenceCanvas
greia_platform.pygame_ui.PygameCanvasMapper
```

Verify:

- a simple author can draw in one reference coordinate system;
- pointer input returns reference coordinates;
- world mapper returns world coordinates;
- reference canvas rejects `expand` because a finite bitmap cannot invent extra world;
- native/reference presentation avoids unnecessary scaling where dimensions match;
- scaled presentation clips safely to the target region;
- repeated viewport changes do not accumulate unbounded renderer resources.

Do not make the off-screen reference surface the required architecture for complex games.

---

# 10. Resolution matrix

Use the responsive UI matrix plus arbitrary generated dimensions.

At minimum:

```text
640×480
800×600
1024×600
1024×768
1280×720
1366×768
1920×1080
2560×1440
3840×2160
720×1280 stress probe
```

The authoring source must remain one semantic layout/camera definition throughout. If a test requires editing source to move elements for one resolution, the architecture has failed that test.

---

# 11. Performance acceptance

On the Acer/reference class:

- reference-canvas helpers must not cause avoidable extra scaling at native size;
- world-camera math must be negligible compared with rendering;
- world Activities must cull rather than draw unbounded off-screen content;
- no persistent 4K off-screen logical surface merely because a 4K display exists;
- resize caches remain bounded;
- no per-frame image decode/font creation/filesystem work is introduced by adaptation.

If abstraction cost is noticeable, optimize the shared adapter; do not reintroduce physical-resolution branches.

---

# 12. Required report

Add this section to the local-agent session result:

```text
ACTIVITY SPATIAL MODEL REVIEW
- Painting:
- Writing:
- Shape Garden:
- Workshop Settings:

REFERENCE CANVAS TEST:
WORLD CAMERA TEST:
HYBRID TEST:
SAFE UI / SYSTEM CHROME TEST:
PHYSICAL↔LOGICAL INPUT ROUNDTRIP:
RESOLUTIONS EXERCISED:

RAW PHYSICAL-COORDINATE DEBT FOUND:
FIXES COMMITTED:
REMAINING DEBT:
```

Use PASS / FAIL / NOT-RUN / UNPROVEN honestly.
