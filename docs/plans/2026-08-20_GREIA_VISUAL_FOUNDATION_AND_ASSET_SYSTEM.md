# Greia Visual Foundation and Asset System — Active Art Workstream Plan

**Status:** ACTIVE ART/VISUAL WORKSTREAM  
**Last checkpoint review:** 2026-08-21  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Stable system/index guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Current visual resume:** `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`

This plan owns **sequencing, current checkpoint, milestone state and append-only progress history** for the Greia visual workstream. Stable architecture belongs in `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`; quick continuation state belongs in `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`.

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → explicit semantic runtime consumption → Shell/Activity reuse**

Broad source-art coverage already exists. **V5 shared consumption/integration remains active.** Multiple real child-Shell surfaces are now accepted at Activity Simulator scope. The current gate extends the same reviewed visual language to **Shell-local navigation chrome** through `ui.button.icon/default`; source is implemented, runtime rendition must be regenerated on the build host, and simulator acceptance is pending.

---

# 1. Non-negotiable production rules

- **Asset first:** reusable individual masters before compositions.
- **Quality:** polished storybook/toy-diorama silhouettes, warm light, soft depth, clean alpha, low-resolution readability.
- **Layered scenes:** base/far/mid/playfield/props/foreground/atmosphere/light/character/UI remain separable where reuse benefits.
- **Subtle life:** cheap parallax, tiny sway, fog, shimmer and light breathing; static fallback remains complete.
- **Reuse before duplication:** use shared generic assets instead of repainting them for each environment.
- **Stop pack proliferation:** a new environment family requires a concrete reusable coverage gap.
- **Cheap explicit runtime:** no runtime SVG rasterization, source-directory scanning, per-frame file decode/scale, or unbounded image caches.
- **Visible integration matters:** plumbing gates must lead to actual Greia presentation improvements; do not spend the workstream indefinitely on invisible proof consumers.
- **Authority stays outside artwork:** shared visuals may restyle existing controls but may not take over Activity lifecycle, navigation, progression, profile or permission authority.
- **Protected navigation stays protected:** Shell-local category/page controls are not the same thing as protected Activity Home/Back chrome.

---

# 2. Character seed

Core cast remains **Lilli, Nino, Tito, Momo** in the accepted simplified Puff/Bean direction.

Shared motion names remain:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Character refinement does not block V5.

---

# 3. Current reusable library

| Pack | Source | Current scope |
|---|---|---|
| Forest / Meadow v0.2 | `assets/visual/environments/forest_meadow/v0.2/` | 27 masters; layered/parallax + target-size review |
| Shared UI v0.1 | `assets/visual/ui/v0.1/` | panels/cards/buttons/tabs/badges/progress/bubbles/reward/focus/loading/error/empty/portal family |
| Workshop v0.1 | `assets/visual/environments/workshop/v0.1/` | 19 masters + target references |
| Clinic / Care v0.1 | `assets/visual/environments/clinic/v0.1/` | 17 masters + reduced-size/target review |
| Reading / Classroom v0.1 | `assets/visual/environments/reading_classroom/v0.1/` | 17 masters; reuses Workshop assets |
| Fantasy / Village / Night v0.1 | `assets/visual/environments/fantasy_village_night/v0.1/` | 15 masters + target references; reuses Forest assets |
| Water / Pond v0.1 | `assets/visual/environments/water_pond/v0.1/` | 14 water-specific masters + target references; reuses Forest assets |

Inventories:

```text
assets/visual/library_v0.1.toml
assets/visual/packs_v0.1.toml
```

Most source-pack art remains **candidate SOURCE + DESKTOP VISUAL REVIEW** unless a narrower record states otherwise. Do not create another environment family merely to keep producing assets.

---

# 4. V5 — Shared consumption/integration

Current source owners:

```text
src/greia_platform/assets.py
src/greia_platform/activity_api.py
src/greia_platform/activity_assets.py
src/greia_platform/ui_core.py
src/greia_platform/pygame_visual_assets.py

src/greia_launcher/visual_assets.py
src/greia_launcher/main.py
src/greia_launcher/presentation.py
src/greia_launcher/shared_ui_presentation.py
src/greia_launcher/profile_chrome_presentation.py
src/greia_launcher/feedback_presentation.py
src/greia_launcher/navigation_chrome_presentation.py
src/greia_launcher/child_shell.py

assets/catalog/core_icons_v1.toml
assets/catalog/shared_visuals_v1_source.toml
assets/catalog/shared_visuals_v1.toml

tools/build_visual_renditions.py
tools/validate_visual_renditions.py
```

Stable architecture/index: `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`.

## 4.1 Explicit catalogue + variants — implemented

`AssetCatalogue` supports semantic shared visuals with kind, role and explicit variants while preserving core icons. IDs are globally unique, paths remain contained under the assets root, and arbitrary discovery is forbidden.

## 4.2 Build-time SVG→PNG rendition pipeline — implemented and exercised

The source rendition manifest now selects:

```text
ui.panel.base              default
ui.card.activity           default / focused / completed
ui.button.primary          default / hover / pressed / disabled
ui.button.icon             default              ← current new source gate
ui.avatar.frame            default
ui.loading.orbit           default
ui.error.gentle            default
ui.empty.basket            default
ui.shadow.soft             default
```

`tools/build_visual_renditions.py` renders through build-host librsvg/`rsvg-convert`, validates dimensions/containment and writes PNG/catalog output transactionally. The target device does not rasterize SVG.

The generated catalogue currently reflects the last accepted build. Because `ui.button.icon` was just added to the source manifest, the local/build checkout must run `make visual-assets` before the navigation-chrome simulator gate.

## 4.3 Generated-output validation — implemented

`tools/validate_visual_renditions.py` / `make visual-assets-check` checks source digest, mapping parity, explicit runtime paths, PNG signatures and exact dimensions.

## 4.4 Bounded Pygame cache — implemented and consumed

`PygameVisualSurfaceCache` provides semantic ID + variant + requested-size caching over `ui_core.BoundedCache`, with a default 12-entry LRU, bounded surface area, PNG-only runtime enforcement and explicit clear.

## 4.5 First Shell seam — ACCEPTED (SIMULATOR VISUAL REVIEW)

`ui.shadow.soft` is accepted beneath launcher Activity tiles. The accepted run covered the full responsive matrix, selection/hover/launch, missing/malformed/corrupt fallbacks and ~29.4 FPS simulator sanity.

## 4.6 Activity semantic resolver — SOURCE IMPLEMENTED, NON-BLOCKING

`src/greia_platform/activity_api.py` exposes:

```python
get_shared_visual(asset_id, variant="default")
get_shared_visual_path(asset_id, variant="default")
```

`activities/shape_garden/main.py` is the first Python source proof. It is no longer a blocker for visible Shell work. Future Web support must preserve semantic IDs/variants through a controlled URL/handle transport rather than exposing host paths.

## 4.7 Activity cards — ACCEPTED (SIMULATOR VISUAL REVIEW)

`ui.card.activity/default|focused` is consumed through `SharedUiActivityCardMixin`.

Accepted behavior:

- authored 360:430 portrait ratio preserved inside logical tile targets;
- Activity icon and localized title placed into authored card regions;
- existing selection/hit/catalogue/lifecycle authority preserved;
- primitive tile remains fail-soft fallback.

The six-row simulator matrix, keyboard navigation, hover, launch/return and fallback cases passed; frame sanity was 27.2 FPS.

## 4.8 Shell panel — ACCEPTED (SIMULATOR VISUAL REVIEW)

`ui.panel.base/default` frames profile picker and Activity catalogue through `SharedUiShellPanelMixin`.

Accepted current catalogue composition additionally includes the owner-directed geometry correction:

```text
panel_top     = 52..62 px
bottom_margin = 4 px
panel ratio   = authored 640:420
Activity grid = aligned to authored inner tray
large cards   ≈ 198–205 px where geometry permits
```

This relationship must be preserved. The panel acceptance matrix and isolated fallback cases passed; frame sanity was 29.5 FPS.

## 4.9 Root category buttons — ACCEPTED (SIMULATOR VISUAL REVIEW)

`ui.button.primary/default|hover` styles the root Activity-category row through `SharedUiCategoryButtonMixin`, preserving category IDs/order/hit targets/navigation. The accepted six-row simulator run included hover, category open/back, lifecycle, isolated fallback and 29.6 FPS sanity.

## 4.10 Profile identity — ACCEPTED (SIMULATOR VISUAL REVIEW)

`ui.avatar.frame/default` is consumed through `SharedUiProfileChromeMixin` for:

- profile-picker identities;
- active-profile switcher in the Activity catalogue.

The owner-directed non-intrusive simulator mode is also accepted infrastructure:

```text
--headless
GREIA_SIMULATOR_HEADLESS=1
SDL dummy video/audio
```

The profile identity six-row matrix, switching/fallback and ~27.4 FPS simulator sanity passed.

## 4.11 Shared Shell feedback — ACCEPTED WITH ONE SOURCE-ONLY SUBCASE

`SharedUiFeedbackMixin` consumes:

```text
ui.loading.orbit/default    SIMULATOR VISUAL REVIEW
ui.error.gentle/default     SIMULATOR VISUAL REVIEW
ui.empty.basket/default     SOURCE / NOT EXERCISED
```

Accepted feedback run (`5d8208883b840318b508b2dddc83c829e826a0e7`):

- launch overlay visually blocks interaction during startup while using the shared orbit;
- corrupt loading PNG falls back cleanly;
- catalogue error cloud appears at top-right and dismisses correctly;
- corrupt error PNG falls back cleanly;
- four responsive launch-overlay rows passed;
- 280 frames / 10.03 s = 27.9 FPS simulator sanity.

The empty basket is generated/source-present but was not legitimately reached through the production catalogue and therefore remains **SOURCE / NOT EXERCISED**.

## 4.12 Shared Shell navigation chrome — SOURCE IMPLEMENTED, SIMULATOR PENDING

The next visible consumer is:

```text
ui.button.icon/default
```

Source master:

```text
assets/visual/ui/v0.1/icon_button.svg
```

Implementation:

```text
src/greia_launcher/navigation_chrome_presentation.py
```

`SharedUiNavigationChromeMixin` keeps navigation semantics and hit rectangles in the existing launcher while applying one reviewed tactile circular frame to Shell-local navigation controls:

1. **mandatory real consumer:** in-category local Back control;
2. Activity collection up/down scroll controls when a real collection requires them;
3. profile previous/next page controls when real profile pagination exists.

Behavioral rules:

- the original action IDs and target rectangles remain authoritative;
- hover is only a tiny 2 px visual lift plus accent-arrow treatment;
- the artwork remains circular rather than stretched;
- a missing/corrupt icon-button visual disables only this treatment and calls the existing primitive navigation renderer;
- accepted panel/cards/category buttons/profile/feedback visuals remain independent;
- protected Activity system Home/Back chrome is **not** replaced or restyled by this mixin.

Accepted via:

```text
docs/testing/2026-08-21_V5_SHARED_NAVIGATION_CHROME_SIMULATOR.md
```

All 6 responsive matrix viewports, in-category Back default & hover, return to root catalogue, multi-page activity scroll default & hover & navigation, corrupt PNG fallback, and 27.1 FPS frame sanity passed with evidence in `tmp/v5-navigation-simulator-evidence/`.

## 4.14 After the navigation-chrome gate

Following simulator acceptance of `ui.shadow.soft`, `ui.card.activity`, `ui.panel.base`, `ui.button.primary`, `ui.avatar.frame`, `ui.loading.orbit`, `ui.error.gentle`, and `ui.button.icon`:

1. record `ui.button.icon` as an accepted visible Shell consumer at **SIMULATOR VISUAL REVIEW** scope;
2. record `ui.empty.basket` and profile pagination as **SOURCE, NOT EXERCISED**;
3. continue only to another product-visible shared UI surface that materially improves Greia, rather than adding proof-only consumers;
4. separately complete the Web Activity semantic adapter using the same semantic IDs/variants through a controlled URL/handle transport, not host filesystem exposure;
5. do not return to new environment-pack production without a demonstrated reusable coverage gap.

---

# 5. Current checkpoint

| Field | Current state |
|---|---|
| Stable guide | `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` |
| Resume | `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` |
| Active focus | **V5 — shared `ui.button.icon` navigation chrome accepted in Activity Simulator** |
| Environment coverage | V4 complete through Water/Pond; no new pack without concrete gap |
| Catalogue/renditions | explicit semantic catalogue + generated PNG runtime catalogue present |
| Activity cards | accepted at **SIMULATOR VISUAL REVIEW** |
| Shell panel | accepted at **SIMULATOR VISUAL REVIEW** |
| Root category buttons | accepted at **SIMULATOR VISUAL REVIEW** |
| Profile identity | accepted at **SIMULATOR VISUAL REVIEW** |
| Launch/error feedback | accepted at **SIMULATOR VISUAL REVIEW** |
| Empty basket | **SOURCE / NOT EXERCISED** |
| Navigation icon button | `ui.button.icon/default` accepted at **SIMULATOR VISUAL REVIEW** |
| Activity semantic API | implemented in source; Shape Garden proof is non-blocking |
| Completed visible protocols | `docs/testing/2026-08-20_V5_SHARED_UI_CARD_SIMULATOR.md`; `docs/testing/2026-08-20_V5_SHARED_UI_PANEL_SIMULATOR.md`; `docs/testing/2026-08-20_V5_SHARED_UI_CATEGORY_BUTTON_SIMULATOR.md`; `docs/testing/2026-08-21_V5_SHARED_PROFILE_IDENTITY_SIMULATOR.md`; `docs/testing/2026-08-21_V5_SHARED_FEEDBACK_SIMULATOR.md`; `docs/testing/2026-08-21_V5_SHARED_NAVIGATION_CHROME_SIMULATOR.md` |
| Next exact action | complete Web Activity semantic visual adapter or next targeted product-visible Shell integration |

---

# 6. Milestones

## V1 — Character/style seed **[SUFFICIENT TO UNBLOCK LIBRARY]**
- [x] simplified character direction;
- [x] core cast seed;
- [ ] useful refinement may continue without blocking integration.

## V2 — Forest/meadow **[DESKTOP CANDIDATE BUILT]**
- [x] source pack;
- [x] metadata/composition/parallax proof;
- [x] target-size review;
- [ ] owner approval/revision when appropriate.

## V3 — Shared UI kit **[DESKTOP CANDIDATE BUILT]**
- [x] shared components/states;
- [x] shadow/highlight treatment;
- [x] target references;
- [ ] owner approval/revision when appropriate.

## V4 — Additional environment coverage **[DESKTOP CANDIDATE COVERAGE COMPLETE]**
- [x] Workshop;
- [x] Clinic;
- [x] Reading/classroom;
- [x] Fantasy/village/night;
- [x] Water/pond;
- [x] pack inventory/reuse dependencies;
- [ ] new family only for a demonstrated gap.

## V5 — Shared consumption/integration **[ACTIVE]**
- [x] typed visual asset catalogue + variants;
- [x] safe cross-manifest merge;
- [x] explicit build-time SVG→PNG pipeline;
- [x] transactional generated output;
- [x] generated-output validator;
- [x] bounded PNG-only Pygame cache;
- [x] optional launcher merge/fallback bridge;
- [x] first generated runtime PNG catalogue;
- [x] `ui.shadow.soft` Shell acceptance;
- [x] Activity card source + simulator acceptance;
- [x] Shell panel source + simulator acceptance;
- [x] root category-button source + simulator acceptance;
- [x] profile-identity source + simulator acceptance;
- [x] headless simulator support accepted for local visual review;
- [x] loading/error feedback source + simulator acceptance;
- [x] empty-basket source integration;
- [ ] empty-basket legitimate runtime exercise;
- [x] shared Shell navigation icon-button source consumer;
- [x] shared Shell navigation chrome simulator acceptance;
- [x] renderer-neutral semantic request portion of Activity API;
- [x] first Python Activity source consumer (Shape Garden);
- [ ] Shape Garden Activity Simulator acceptance (non-blocking);
- [ ] future Web Activity semantic adapter/transport;
- [ ] further visible Shell integration only where materially useful;
- [ ] physical low-resource evidence where a stronger claim requires it.

---

# 7. Evidence vocabulary

```text
DESIGN SPEC
SOURCE
DESKTOP VISUAL REVIEW
SIMULATOR VISUAL REVIEW
PHYSICAL VISUAL REVIEW
REJECTED EXPERIMENT
```

Committed source is not PASS by itself. Generated runtime output is not consumer evidence until the relevant real consumer is exercised.

---

# 8. Failure patterns — do not repeat

- character minutiae consuming the workstream;
- detailed rigs as default;
- one-shot sprite sheets assumed production-ready;
- crude primitive scenes/mockups presented as final direction;
- decorative HTML hiding weak assets;
- runtime SVG rendering;
- arbitrary visual-directory scanning;
- second catalogue/cache frameworks;
- per-frame decode/scale;
- unbounded caches;
- per-resolution production forks;
- simulator-specific production code;
- broad exception swallowing;
- more environment packs without a real gap;
- duplicating generic shared masters;
- proof-only Activities displacing visible product work once the shared seam is established.

---

# 9. Progress log — append only

The entries below preserve the earlier workstream chronology. Corrections/new state are appended rather than rewriting old experiments into successes.

## 2026-08-20 — constraint-native visual pivot
- Simplified characters established; Lilli/Nino/Tito/Momo became core cast.
- Detailed quadruped/sprite-sheet/automatic-rig approaches retained as rejected defaults.

## 2026-08-20 — drift corrected
- Character work had expanded too far and regressed.
- Crude UI/background mock was rejected.
- Workstream corrected to high-quality single assets → composition/parallax/light/shadow/UI.

## 2026-08-20 — forest/meadow v0.2
- 27 reusable SVG masters committed.
- Catalog/parallax/ambient metadata added.
- Weak sapling/tree-line/fog/dust treatments revised after desktop review.
- Composition manifest and actual-asset parallax proof committed.

## 2026-08-20 — UI v0.1 and Workshop v0.1 advanced
- Shared UI source/state pack expanded and reviewed.
- Workshop first tranche committed and reviewed.

## 2026-08-20 — target-size tranche + Clinic
- Forest final restraint references created at 1024×600 and 800×600.
- Shared UI target-size compositions created.
- Workshop expanded to 19 masters with only composition-critical additions and target-size references.
- Clinic 17-master pack created with reduced-size and target-size desktop review.
- Source tranche commit: `869cdc502458d54d667d5ed60d781411be763851`.

## 2026-08-20 — Reading/Classroom v0.1
- Built a bounded 17-master reading/classroom source pack.
- Reused Workshop block/pencil assets by reference instead of duplicating them.
- Revised weak book-stack, tent and beanbag treatments after direct desktop review.
- Reading pack landed on `main` at `6b94d6ddd8cdbecea171f40a1e47c1ac49f3aec9`.

## 2026-08-20 — Fantasy/Village/Night v0.1
- Built a bounded 15-master night/fantasy village pack.
- Reused Forest greenery/fireflies semantically instead of creating unnecessary duplicates.
- Revised weak cottages, tower, lantern, well and cobblestone treatments before final desktop review.
- Source + composition/review metadata committed in `0958f8a0ca1b583798a245464b9e3e87a74d883c`.

## 2026-08-20 — Water/Pond v0.1 + inventory consolidation
- Built and desktop-reviewed 14 water-specific reusable masters.
- Revised dock/lily pads, water base and reeds during review.
- Built independent 1024×600 / 800×600 references reusing canonical Forest distant landscape.
- Added `assets/visual/packs_v0.1.toml` and refreshed `library_v0.1.toml`.
- Evidence remained SOURCE + DESKTOP VISUAL REVIEW.

## 2026-08-20 — V5 catalogue/rendition/cache seed
- Extended `AssetCatalogue` with typed visual variants while preserving icons/path containment/one semantic namespace.
- Added explicit shared visual source manifest and transactional build-host SVG→PNG tool.
- Added bounded `PygameVisualSurfaceCache` on `ui_core.BoundedCache`.
- Added explicit visual build/validation entrypoints.

## 2026-08-20 — V5 first-consumer preparation
- Added safe cross-manifest merge.
- Added `ui.shadow.soft` to the first runtime rendition set.
- Added optional launcher shared-visual bridge/fallback.
- Added generated-output validation.

## 2026-08-20 — visual-system documentation consolidated
- Added `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` as the stable visual architecture/index.
- Added `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` as the cross-session resume.
- Linked them from repository documentation authority.

## 2026-08-20 — V5 first Shell consumer wired and simulator-verified
- Generated runtime visual renditions through `make visual-assets` / `rsvg-convert`.
- Wired `load_launcher_assets(...)` + `PygameVisualSurfaceCache` into the launcher.
- Integrated `ui.shadow.soft` beneath Activity tiles with fail-soft primitive fallback.
- Corrected malformed TOML containment and simulator RGB screenshot capture.
- Passed full 6-row simulator matrix, selection/hover/launch, missing/malformed/corrupt fallback cases and ~29.4 FPS frame sanity.
- Evidence: **SIMULATOR VISUAL REVIEW**; no physical hardware/R7 claim.

## 2026-08-20 — V5 canonical state reconciliation
- Removed stale language saying the first Shell consumer was still unwired.
- Marked `ui.shadow.soft` Shell gate complete at simulator scope.
- Redirected V5 toward reusable semantic consumption and visible Shell integration.

## 2026-08-20 — first Python Activity semantic visual source seam
- Added read-only `SharedVisualReference` plus `get_shared_visual(...)` / `get_shared_visual_path(...)` to `activity_api.py`.
- Activity requests semantic ID + variant only; optional shared catalogue failure falls back to core catalogue behavior.
- Added Shape Garden as the first source consumer of `ui.shadow.soft`; the PNG is resolved/decoded/scaled once at Activity startup and reused while drawing.
- Added `docs/testing/2026-08-20_V5_ACTIVITY_SHARED_VISUAL_SIMULATOR.md`.
- Evidence remains **SOURCE** until that protocol executes; this proof no longer blocks visible Shell work.

## 2026-08-20 — visible shared Activity cards moved into the real child Shell
- Added `SharedUiActivityCardMixin` as a narrow presentation-only consumer of `ui.card.activity/default|focused`.
- Production `GreiaChildShell` composes that mixin above the existing launcher presentation.
- The authored portrait card ratio, illustration well and label band are preserved inside the existing logical tile hit target.
- Existing primitive tile rendering remains the fail-soft fallback; lifecycle/catalogue/input authority is unchanged.

## 2026-08-20 — shared Activity cards accepted in simulator
- `ui.card.activity/default|focused` passed the full 6-row Activity Simulator matrix plus selection, hover, launch/return and missing/malformed/corrupt fallback cases.
- Synthetic pointer tracking was corrected for simulator `MOUSEMOTION`.
- Frame sanity measured 27.2 FPS against the intentional 30 FPS clock.
- Evidence class: **SIMULATOR VISUAL REVIEW**.

## 2026-08-20 — shared Shell panel accepted in simulator
- `ui.panel.base/default` was integrated behind both profile picker and Activity catalogue.
- Activity tile cache surfaces were corrected to alpha surfaces so the panel remained visible without rectangular cutouts.
- Profile/catalogue baseline, return Home, missing/malformed/corrupt-panel fallback and all responsive rows passed.
- Frame sanity measured 29.5 FPS.
- Evidence class: **SIMULATOR VISUAL REVIEW**.

## 2026-08-20 — shared category buttons moved into the real child Shell
- Added `SharedUiCategoryButtonMixin` for root Activity-category controls using `ui.button.primary/default|hover`.
- Preserved existing category ordering, hit targets and navigation; the wide primary-button asset was not forced onto the geometry-specific in-category Back control.
- Added isolated fail-soft behavior so button-specific corruption falls back only the category row while accepted panel/card shared visuals remain active.
- Added `docs/testing/2026-08-20_V5_SHARED_UI_CATEGORY_BUTTON_SIMULATOR.md`.
- Evidence at this historical checkpoint remained **SOURCE** until the simulator protocol ran.

## 2026-08-20 — shared category buttons accepted in simulator
- `ui.button.primary/default|hover` passed baseline/hover/category open-return/lifecycle/fallback review.
- Full six-row responsive matrix passed.
- Isolated corrupt hover-button fallback kept panel/cards active.
- Frame sanity measured 29.6 FPS.
- Evidence class: **SIMULATOR VISUAL REVIEW**.

## 2026-08-21 — panel geometry maximized, headless simulator added, profile identity accepted
- Owner-directed panel geometry was corrected to use the screen vertically while preserving 640:420 aspect ratio and full large Activity cards within the authored tray.
- Added non-intrusive `--headless` / `GREIA_SIMULATOR_HEADLESS=1` simulator execution through SDL dummy drivers.
- `ui.avatar.frame/default` was generated and integrated into profile picker identities and active-profile switcher.
- Six-row responsive/fallback/profile-switch review passed; frame sanity was ~27.4 FPS.
- Canonical acceptance commit: `7dc5d39df51fd3404d222c762d7b5d48133def9d`.

## 2026-08-21 — shared Shell feedback accepted
- Generated `ui.loading.orbit`, `ui.error.gentle` and `ui.empty.basket` runtime renditions.
- Launch overlay and catalogue error cloud were exercised through the real headless Activity Simulator with isolated fallbacks.
- `ui.empty.basket` remained **SOURCE / NOT EXERCISED** because the production catalogue empty state was not legitimately reached.
- Responsive overlay review and 27.9 FPS frame sanity passed.
- Canonical acceptance commit: `5d8208883b840318b508b2dddc83c829e826a0e7`.

## 2026-08-21 — shared Shell navigation chrome source tranche
- Promoted the existing reviewed `assets/visual/ui/v0.1/icon_button.svg` as semantic runtime source `ui.button.icon/default` in source catalogue version 0.1.4.
- Added `SharedUiNavigationChromeMixin` for the in-category local Back control and for Activity/profile pagination controls when those controls legitimately exist.
- Existing action IDs, target rectangles, category identity and scrolling/page authority remain in the launcher.
- Added isolated fail-soft fallback to the existing primitive navigation controls.
- Added `docs/testing/2026-08-21_V5_SHARED_NAVIGATION_CHROME_SIMULATOR.md` for headless Activity Simulator acceptance.
- Evidence remains **SOURCE** until runtime renditions are regenerated and that protocol passes.

**Next exact action:** `make visual-assets` → execute `docs/testing/2026-08-21_V5_SHARED_NAVIGATION_CHROME_SIMULATOR.md` headlessly → inspect mandatory in-category Back default/hover/click + isolated corrupt-PNG fallback + six-row responsive matrix → record conditional scroll/profile-pagination results honestly → update evidence/docs → commit/push.
