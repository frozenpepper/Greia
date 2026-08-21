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

For a new visual-workstream session read:

```text
1. AGENTS.md
2. docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
3. docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
4. this file
5. HANDOVER.md
6. skills/greia-visual-authoring/SKILL.md
7. exact source files for the current gate
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

Broad reusable source coverage already exists under:

```text
assets/visual/environments/forest_meadow/v0.2/
assets/visual/ui/v0.1/
assets/visual/environments/workshop/v0.1/
assets/visual/environments/clinic/v0.1/
assets/visual/environments/reading_classroom/v0.1/
assets/visual/environments/fantasy_village_night/v0.1/
assets/visual/environments/water_pond/v0.1/
```

Core characters remain Lilli, Nino, Tito and Momo in the accepted Puff/Bean constraint-native direction. Character minutiae do not block V5.

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
ui.empty.basket      SOURCE / NOT EXERCISED
```

The latest accepted feedback run is commit `5d8208883b840318b508b2dddc83c829e826a0e7` and confirmed:

- real launch overlay using `ui.loading.orbit`;
- dismissible catalogue-error cloud using `ui.error.gentle`;
- isolated corrupt-PNG fallbacks;
- headless simulator execution;
- responsive launch-overlay review;
- 280 frames / 10.03 s = 27.9 FPS simulator sanity.

No physical Acer/Pi performance claim and no R7 closure.

---

# 4. Accepted Shell composition details

Current visual composition owners:

```text
src/greia_launcher/shared_ui_presentation.py
src/greia_launcher/profile_chrome_presentation.py
src/greia_launcher/feedback_presentation.py
src/greia_launcher/child_shell.py
```

Important accepted relationships:

- `ui.panel.base` uses the available vertical catalogue space beginning immediately below the category row (`panel_top=52..62`, `bottom_margin=4`) while preserving its authored 640:420 aspect ratio;
- Activity layout consumes the panel's authored inner tray;
- cards retain a prominent approximately 198–205 px scale where geometry permits;
- `ui.card.activity/default|focused` preserves its authored 360:430 portrait ratio;
- root categories use `ui.button.primary/default|hover`;
- profile-picker identities and the active-profile switcher use `ui.avatar.frame/default`;
- launch/error feedback is shared artwork with narrow independent fallbacks;
- headless simulator support is `--headless` / `GREIA_SIMULATOR_HEADLESS=1` using SDL dummy video/audio while still capturing the real Shell pixel buffer.

---

# 5. Activity semantic seam

Python Activity shared-visual source API exists in:

```text
src/greia_platform/activity_api.py
```

with:

```python
get_shared_visual(asset_id, variant="default")
get_shared_visual_path(asset_id, variant="default")
```

`activities/shape_garden/main.py` remains the first source proof. It is **non-blocking** and must not displace visible Shell work again.

Future Web Activity support must preserve semantic IDs/variants through a controlled URL/handle transport rather than exposing host filesystem paths.

---

# 6. Current exact gate — shared Shell navigation chrome

New source consumer:

```text
ui.button.icon/default
```

Source master:

```text
assets/visual/ui/v0.1/icon_button.svg
```

Source rendition declaration:

```text
assets/catalog/shared_visuals_v1_source.toml
```

Expected generated runtime file after `make visual-assets`:

```text
assets/visual/runtime/v1/ui/icon_button.png
```

Implementation:

```text
src/greia_launcher/navigation_chrome_presentation.py
src/greia_launcher/child_shell.py
```

`SharedUiNavigationChromeMixin` reuses the same tactile circular icon-button frame for Shell-local navigation while leaving semantics/hit authority in the existing launcher:

1. **mandatory runtime consumer:** in-category local Back control;
2. Activity collection up/down scroll controls when a real collection requires scrolling;
3. profile previous/next page controls when real profile pagination exists.

The visual layer keeps the original hit rectangles. Hover is only a tiny visual lift plus accent-arrow treatment. A bad/missing `ui.button.icon` disables only this shared navigation treatment and falls back to the existing primitive controls; panel/cards/categories/profile/feedback remain independent.

This does **not** replace protected Activity system Home/Back chrome.

Current evidence: **SOURCE**. No simulator PASS yet.

Required protocol:

```text
docs/testing/2026-08-21_V5_SHARED_NAVIGATION_CHROME_SIMULATOR.md
```

---

# 7. Exact continuation sequence

```text
1. sync current main
2. run make visual-assets
3. confirm assets/visual/runtime/v1/ui/icon_button.png and generated catalogue entry
4. start Activity Simulator with GREIA_SIMULATOR_HEADLESS=1 using an isolated state root
5. run docs/testing/2026-08-21_V5_SHARED_NAVIGATION_CHROME_SIMULATOR.md
6. mandatory: inspect in-category Back default/hover/click behavior
7. exercise Activity scroll/profile pagination only if legitimately reachable; otherwise record NOT EXERCISED
8. verify corrupt icon-button PNG falls back only navigation chrome
9. run full 6-row responsive matrix for the in-category Back control
10. record frame-count sanity
11. fix only shared/root causes
12. update plan/resume/HANDOVER/LOCAL_AGENT_RESULT.md
13. commit and push accepted work to canonical main
```

After this gate, continue to another coherent product-visible shared surface or the Web semantic adapter. Do not create a new environment pack without a concrete reusable gap.

---

# 8. Simulator rule

Owner-directed local runtime/visual/fallback/responsive acceptance uses the Greia Activity Simulator.

Prefer non-intrusive local-agent execution:

```bash
GREIA_SIMULATOR_HEADLESS=1 python3 tools/greia_simulator.py --state-dir <isolated-state>
```

Remote bridge remains local loopback only:

```text
http://127.0.0.1:8767
```

No Cloudflare/tunnel/hosted service belongs in the workflow. Do not query/run GitHub-hosted Actions unless the owner explicitly authorizes that specific use.

---

# 9. Accepted simulator protocols

```text
docs/testing/2026-08-20_V5_SHARED_UI_CARD_SIMULATOR.md
docs/testing/2026-08-20_V5_SHARED_UI_PANEL_SIMULATOR.md
docs/testing/2026-08-20_V5_SHARED_UI_CATEGORY_BUTTON_SIMULATOR.md
docs/testing/2026-08-21_V5_SHARED_PROFILE_IDENTITY_SIMULATOR.md
docs/testing/2026-08-21_V5_SHARED_FEEDBACK_SIMULATOR.md
```

Current pending protocol:

```text
docs/testing/2026-08-21_V5_SHARED_NAVIGATION_CHROME_SIMULATOR.md
```

---

# 10. Rejected/drift directions

Do not resume:

- detailed traditional character rigs as default;
- generated sprite sheets treated as production-ready;
- fake expression overlays;
- crude UI/background mockups;
- decorative HTML presentations instead of real assets;
- one-shot scene images as source architecture;
- more environment packs without a real gap;
- runtime SVG rendering on target devices;
- arbitrary visual-directory discovery;
- a second visual catalogue/cache framework;
- per-frame PNG decode/scale;
- unbounded caches;
- simulator-only production branches;
- per-resolution production forks;
- broad exception swallowing;
- proof-only Activities consuming the workstream after the Shell seam is already proven.

---

# 11. Documentation map

Stable visual architecture/index:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

Current sequencing/history:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
```

Practical visual authoring:

```text
skills/greia-visual-authoring/SKILL.md
```

Simulator developer guide:

```text
docs/development/GREIA_ACTIVITY_SIMULATOR.md
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

Update this file whenever the active visual phase, next action, runtime consumption, evidence boundary, blocker or testing rule materially changes.

Chronology belongs in the active plan's append-only progress ledger. Stable architecture belongs in `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`. Project-wide continuation belongs in `HANDOVER.md`.
