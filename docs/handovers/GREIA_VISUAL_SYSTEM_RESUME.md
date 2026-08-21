# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-21  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Active plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Project-wide handover:** `HANDOVER.md`

---

# 1. Resume order

Read, in order:

```text
1. AGENTS.md
2. docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
3. docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
4. docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
5. docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
6. this file
7. HANDOVER.md
8. skills/greia-visual-authoring/SKILL.md
9. exact source files for the current gate
```

Do not resume from chat memory alone.

---

# 2. Stable production direction

Greia visual production remains:

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → explicit semantic runtime consumption → Shell/Activity reuse**

Non-negotiables:

- asset-first, not crude full-screen mockups;
- polished storybook/toy-diorama language;
- readable at low resolution;
- reuse before duplication;
- no target runtime SVG rasterization;
- no arbitrary runtime asset-directory scanning;
- no per-frame PNG decode/scale;
- bounded runtime caches;
- no simulator-specific production rendering;
- visual work must not deepen provisional X11 coupling or bypass protected platform Home/Back authority;
- no new environment pack merely to keep producing assets.

Broad reusable source coverage already exists under the Forest/Meadow, Shared UI, Workshop, Clinic, Reading/Classroom, Fantasy/Village/Night and Water/Pond packs. Core characters remain Lilli, Nino, Tito and Momo in the accepted Puff/Bean direction. Character minutiae do not block V5.

---

# 3. Proven V5 runtime seam

The active visual phase remains **V5 — shared consumption/integration**.

Proven path:

```text
reviewed SVG master
→ explicit source rendition manifest
→ build-time PNG via rsvg-convert
→ generated runtime catalogue
→ AssetCatalogue
→ PygameVisualSurfaceCache
→ real GreiaChildShell consumer
→ Activity Simulator acceptance
```

Accepted visible/shared Shell consumers:

```text
ui.shadow.soft       SIMULATOR VISUAL REVIEW
ui.card.activity     SIMULATOR VISUAL REVIEW
ui.panel.base        SIMULATOR VISUAL REVIEW
ui.button.primary    SIMULATOR VISUAL REVIEW
ui.avatar.frame      SIMULATOR VISUAL REVIEW
ui.loading.orbit     SIMULATOR VISUAL REVIEW
ui.error.gentle      SIMULATOR VISUAL REVIEW
ui.button.icon       SIMULATOR VISUAL REVIEW
ui.portal.frame      SIMULATOR VISUAL REVIEW
ui.empty.basket      SOURCE (NOT EXERCISED)
```

Latest accepted Collection-first Home evidence: primary Collection destinations on Home (`Crea`, `Gioca`, `Impara`, `Esplora`, `Mio Greia`, `Care`), keyboard/pointer navigation, return origin from activity, multi-membership sanity, fail-soft portal fallback, all 6 responsive rows, and 277 frames / 10.01 s = 27.7 FPS in headless Activity Simulator. No physical Acer/Pi claim and no R7 closure.

---

# 4. Accepted Collection-first product architecture

The normal child Shell now uses Collection-first discovery:

```text
profile
  → Greia Home
    → primary Collection
      → Activity
```

with at most one future optional sub-Collection layer when a large effective catalogue actually benefits from it.

Implementation:

```text
src/greia_launcher/collection_home_presentation.py
src/greia_launcher/child_shell.py
```

`CollectionFirstHomeMixin` treats `ALL_ACTIVITIES_ID` as an internal projection only. At launcher root it renders the available non-empty primary Collections as large destinations; entering one reuses the already-accepted Activity card/panel/navigation path; local Back returns to Collection Home; root Back returns to profile choice.

Accepted shared visual:

```text
ui.portal.frame/default
```

from:

```text
assets/visual/ui/v0.1/portal_frame.svg
```

with generated runtime file:

```text
assets/visual/runtime/v1/ui/portal_frame.png
```

Accepted via `docs/testing/2026-08-21_COLLECTION_FIRST_HOME_SIMULATOR.md` at **SIMULATOR VISUAL REVIEW** scope.

---

# 5. Exact continuation sequence

```text
1. sync current main
2. continue to Web Activity semantic adapter or next targeted product-visible Shell integration
3. preserve headless simulator testing (GREIA_SIMULATOR_HEADLESS=1) so local work is non-intrusive
4. run full responsive matrix and fail-soft verification
5. update result/product/design/plan/resume/HANDOVER
6. commit and push accepted work to canonical main
```

Do **not** mark adaptive sub-Collections, age/development policy, Parent per-child visibility, Web semantic transport or physical hardware performance as implemented by this gate.

---

# 6. Current Shell composition owners

```text
src/greia_launcher/collection_home_presentation.py
src/greia_launcher/shared_ui_presentation.py
src/greia_launcher/profile_chrome_presentation.py
src/greia_launcher/feedback_presentation.py
src/greia_launcher/navigation_chrome_presentation.py
src/greia_launcher/child_shell.py
```

Accepted existing relationships remain:

- `ui.portal.frame/default` renders large primary Collection destinations on Home;
- `ui.panel.base` provides the large Shell tray;
- `ui.card.activity/default|focused` renders Activity cards inside Collections;
- `ui.button.icon/default` provides local Back and scroll chrome;
- `ui.avatar.frame/default` provides profile identity;
- launch/error feedback uses shared artwork with narrow isolated fallbacks;
- headless simulator mode is `--headless` / `GREIA_SIMULATOR_HEADLESS=1` using SDL dummy video/audio while retaining real pixel-buffer capture.

The old `ui.button.primary` root category row remains accepted evidence for the previous presentation but is superseded by Collection-first Home for normal child discovery.

---

# 7. Activity semantic seam

Python Activity shared-visual source API remains:

```python
get_shared_visual(asset_id, variant="default")
get_shared_visual_path(asset_id, variant="default")
```

in `src/greia_platform/activity_api.py`.

`activities/shape_garden/main.py` remains a non-blocking source proof. Do not let it displace visible Shell/product work again. Future Web Activity support must preserve semantic IDs/variants through a controlled URL/handle transport rather than exposing host filesystem paths.

---

# 8. Simulator rule

Owner-directed local runtime/visual/fallback/responsive acceptance uses the Greia Activity Simulator.

Prefer:

```bash
GREIA_SIMULATOR_HEADLESS=1 python3 tools/greia_simulator.py --state-dir <isolated-state>
```

Remote bridge remains local loopback only at `http://127.0.0.1:8767`. No Cloudflare/tunnel/hosted service belongs in this workflow. Do not query/run GitHub-hosted Actions without explicit owner authorization.

---

# 9. Accepted protocols so far

```text
docs/testing/2026-08-20_V5_SHARED_UI_CARD_SIMULATOR.md
docs/testing/2026-08-20_V5_SHARED_UI_PANEL_SIMULATOR.md
docs/testing/2026-08-20_V5_SHARED_UI_CATEGORY_BUTTON_SIMULATOR.md
docs/testing/2026-08-21_V5_SHARED_PROFILE_IDENTITY_SIMULATOR.md
docs/testing/2026-08-21_V5_SHARED_FEEDBACK_SIMULATOR.md
docs/testing/2026-08-21_V5_SHARED_NAVIGATION_CHROME_SIMULATOR.md
docs/testing/2026-08-21_COLLECTION_FIRST_HOME_SIMULATOR.md
```

---

# 10. Rejected/drift directions

Do not resume:

- treating `All + filter tabs` as the final child Home;
- filesystem-style nested folders;
- deep taxonomies beyond one optional sub-Collection layer;
- detailed traditional character rigs as default;
- generated sprite sheets treated as production-ready;
- crude UI/background mockups;
- more environment packs without a real gap;
- runtime SVG rendering on target devices;
- arbitrary visual-directory discovery;
- a second visual catalogue/cache framework;
- per-frame PNG decode/scale;
- unbounded caches;
- simulator-only production branches;
- per-resolution production forks;
- proof-only Activities consuming the workstream after the Shell seam is proven.

---

# 11. Documentation map

Stable visual architecture/index:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

Collection-first product/design authority:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
```

Visual sequencing/history:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
```

Practical visual authoring:

```text
skills/greia-visual-authoring/SKILL.md
```

Project-wide state:

```text
HANDOVER.md
```

Execution results:

```text
LOCAL_AGENT_RESULT.md
```

---

# 12. End-of-session rule

Update this file whenever the active visual phase, next action, runtime consumption, evidence boundary, blocker or testing rule materially changes. Chronology belongs in the active plan; stable architecture belongs in `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`; project-wide continuation belongs in `HANDOVER.md`.
