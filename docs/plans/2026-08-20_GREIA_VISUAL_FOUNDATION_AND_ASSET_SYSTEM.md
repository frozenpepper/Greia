# Greia Visual Foundation and Asset System — Active Art Workstream Plan

**Status:** ACTIVE ART/VISUAL WORKSTREAM  
**Last checkpoint review:** 2026-08-21  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Stable system/index guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Current visual resume:** `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`

This plan owns **sequencing, current checkpoint, milestone state and append-only progress history** for the Greia visual workstream. Stable architecture belongs in `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`; quick continuation state belongs in `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`.

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → explicit semantic runtime consumption → Shell/Activity reuse**

Broad source-art coverage already exists. **V5 shared consumption/integration remains active.** The reusable runtime seam is now proven across cards, panels, buttons, profile identity, feedback and Shell-local navigation. The current gate is no longer another decoration pass: it begins the accepted **Collection-first Greia Home** migration, replacing the temporary normal-child `All Activities + filter row` landing with large semantic Collection destinations while reusing the already-accepted Activity catalogue inside each Collection.

---

# 1. Non-negotiable production rules

- **Asset first:** reusable individual masters before compositions.
- **Quality:** polished storybook/toy-diorama silhouettes, warm light, soft depth, clean alpha, low-resolution readability.
- **Layered scenes:** base/far/mid/playfield/props/foreground/atmosphere/light/character/UI remain separable where reuse benefits.
- **Subtle life:** cheap parallax, tiny sway, fog, shimmer and light breathing; static fallback remains complete.
- **Reuse before duplication:** use shared generic assets instead of repainting them for each environment.
- **Stop pack proliferation:** a new environment family requires a concrete reusable coverage gap.
- **Cheap explicit runtime:** no runtime SVG rasterization, source-directory scanning, per-frame file decode/scale, or unbounded image caches.
- **Visible integration matters:** plumbing gates must lead to actual Greia presentation improvements.
- **Authority stays outside artwork:** shared visuals may restyle existing controls but may not take over Activity lifecycle, navigation, progression, profile or permission authority.
- **Protected navigation stays protected:** Shell-local Collection/page controls are not the same thing as protected Activity Home/Back chrome.
- **Collection-first means semantic navigation, not filesystem folders:** one Activity may appear in multiple Collections without package/state duplication.
- **Do not preserve obsolete UI merely because it has already been styled:** `All` remains useful internally, but the accepted normal child Home is Collection-first.

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
src/greia_launcher/collection_home_presentation.py
src/greia_launcher/child_shell.py

assets/catalog/core_icons_v1.toml
assets/catalog/shared_visuals_v1_source.toml
assets/catalog/shared_visuals_v1.toml

tools/build_visual_renditions.py
tools/validate_visual_renditions.py
```

Stable architecture/index: `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`.

Collection-first product/design authority:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
```

## 4.1 Explicit catalogue + variants — implemented

`AssetCatalogue` supports semantic shared visuals with kind, role and explicit variants while preserving core icons. IDs are globally unique, paths remain contained under the assets root, and arbitrary discovery is forbidden.

## 4.2 Build-time SVG→PNG rendition pipeline — implemented and exercised

The source rendition manifest now selects:

```text
ui.panel.base              default
ui.card.activity           default / focused / completed
ui.button.primary          default / hover / pressed / disabled
ui.button.icon             default
ui.avatar.frame            default
ui.loading.orbit           default
ui.error.gentle            default
ui.empty.basket            default
ui.portal.frame            default      ← current Collection-first Home source gate
ui.shadow.soft             default
```

`tools/build_visual_renditions.py` renders through build-host librsvg/`rsvg-convert`, validates dimensions/containment and writes PNG/catalog output transactionally. The target device does not rasterize SVG.

`ui.button.icon` has already been generated and simulator-accepted. `ui.portal.frame` was added to source catalogue version `0.1.5`; its runtime PNG/generated-catalogue entry must be produced by `make visual-assets` before the Collection-first Home simulator gate.

## 4.3 Generated-output validation — implemented

`tools/validate_visual_renditions.py` / `make visual-assets-check` checks source digest, mapping parity, explicit runtime paths, PNG signatures and exact dimensions. These build checks are not a substitute for the owner-required Activity Simulator acceptance path.

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

Accepted current catalogue composition includes the owner-directed geometry correction:

```text
panel_top     = 52..62 px
bottom_margin = 4 px
panel ratio   = authored 640:420
Activity grid = aligned to authored inner tray
large cards   ≈ 198–205 px where geometry permits
```

This relationship must be preserved. The panel acceptance matrix and isolated fallback cases passed; frame sanity was 29.5 FPS.

## 4.9 Root category buttons — ACCEPTED HISTORICAL PRESENTATION (SIMULATOR VISUAL REVIEW)

`ui.button.primary/default|hover` styles the previous root Activity-category row through `SharedUiCategoryButtonMixin`, preserving category IDs/order/hit targets/navigation. The accepted six-row simulator run included hover, category open/back, lifecycle, isolated fallback and 29.6 FPS sanity.

This evidence remains valid for the component. It does **not** mean the filter-row information architecture remains the preferred normal child Home. Collection-first Home now supersedes that root presentation when its simulator gate passes.

## 4.10 Profile identity — ACCEPTED (SIMULATOR VISUAL REVIEW)

`ui.avatar.frame/default` is consumed through `SharedUiProfileChromeMixin` for profile-picker identities and the active-profile switcher.

Owner-directed non-intrusive simulator mode is accepted infrastructure:

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

Accepted feedback run (`5d8208883b840318b508b2dddc83c829e826a0e7`) covered launch overlay, catalogue error cloud, isolated corrupt-PNG fallbacks, four responsive rows and 280 frames / 10.03 s = 27.9 FPS simulator sanity.

The empty basket was not legitimately reached through the production catalogue and therefore remains **SOURCE / NOT EXERCISED**.

## 4.12 Shared Shell navigation chrome — ACCEPTED (SIMULATOR VISUAL REVIEW)

`ui.button.icon/default` is consumed through:

```text
src/greia_launcher/navigation_chrome_presentation.py
```

Accepted behavior:

1. in-category local Back control uses the circular tactile frame;
2. Activity collection up/down controls use the same family when a real collection requires pagination;
3. profile previous/next controls share the same source path but remain **SOURCE / NOT EXERCISED** when profile count is <=4;
4. original action IDs and target rectangles remain authoritative;
5. corrupt `icon_button.png` falls back only the navigation controls while accepted panel/cards/profile/feedback visuals remain active;
6. protected Activity system Home/Back is not replaced.

Accepted via:

```text
docs/testing/2026-08-21_V5_SHARED_NAVIGATION_CHROME_SIMULATOR.md
```

Canonical acceptance commit: `370d96039546178ed2c64366bdaec1b5dc986be2`.

Evidence: six responsive rows, Back default/hover/click, Activity scroll controls, isolated corrupt-PNG fallback, and 271 frames / 10.01 s = 27.1 FPS simulator sanity.

## 4.13 Collection-first Greia Home — ACCEPTED

Accepted target:

```text
profile
  → Greia Home
    → primary Collection
      → Activity
```

Current primary Collection vocabulary:

```text
create
play
learn
explore
my_greia
```

Implementation:

```text
src/greia_launcher/collection_home_presentation.py
src/greia_launcher/catalogue_view.py
src/greia_launcher/child_shell.py
```

`CollectionFirstHomeMixin` now changes the normal launcher root projection without changing package/runtime authority:

- `ALL_ACTIVITIES_ID` remains available internally but is no longer rendered as the normal child Activity wall;
- root renders only available non-empty primary Collections as large destinations;
- arbitrary package categories do not manufacture top-level Home portals;
- unknown-category Activities are recovered through the bounded `browse`/`Altro` Collection;
- entering a Collection reuses the already-accepted panel, Activity-card, scroll/navigation and launch paths;
- local Back from a primary Collection returns to Collection Home;
- Back/Escape at Collection Home returns to profile choice;
- one Activity may appear in multiple Collections without duplicate installation, saves, permissions, history or progression;
- root mouse-wheel activity scrolling is disabled because there is no Activity wall at Home;
- active-profile switching remains available;
- keyboard, pointer and selection semantics remain renderer-independent launcher state.

Accepted shared visual:

```text
ui.portal.frame/default
```

Source master:

```text
assets/visual/ui/v0.1/portal_frame.svg
```

Generated runtime file:

```text
assets/visual/runtime/v1/ui/portal_frame.png
```

Fail-soft rule is deliberately narrow: corrupt/missing portal artwork preserves **Collection-first hierarchy** using a primitive circular Collection destination; it does not fall back to the obsolete All-Activities Home and does not disable unrelated accepted visuals.

Accepted protocols:

```text
docs/testing/2026-08-21_COLLECTION_FIRST_HOME_SIMULATOR.md
docs/testing/2026-08-21_COLLECTION_PRIMARY_VOCABULARY_SIMULATOR.md
```

All 6 responsive matrix viewports, keyboard/pointer navigation, return origin from activity, multi-membership sanity, fail-soft portal fallback, bounded unknown-only fallback, and 27.7 FPS frame sanity passed with evidence in `tmp/collection-home-simulator-evidence/` and `tmp/collection-primary-vocabulary-evidence/`.

Evidence class: **SIMULATOR VISUAL REVIEW**.

This gate does **not** implement or accept future adaptive sub-Collections, age/development profile policy, Parent per-child visibility policy or the Web visual adapter.

## 4.14 Scene Composition Runtime & Nascondino nel Bosco — ACCEPTED (SIMULATOR VISUAL REVIEW)

Architecture plan:

```text
docs/plans/2026-08-21_GREIA_SCENE_COMPOSITION_RUNTIME.md
```

Accepted components:

1. `SceneDefinition` + `SceneNode` + `SceneCamera` in `src/greia_platform/scene.py`;
2. `PygameSceneRenderer` with split $z$-range rendering ($z \le 59$ background, $z \ge 60$ foreground/atmosphere) in `src/greia_platform/pygame_scene.py`;
3. First runtime scene `assets/scenes/forest_meadow_day_v1.toml` with 15 semantic visual nodes;
4. Integration in `activities/nascondino_bosco/main.py` replacing primitive legacy background while preserving interactive gameplay spots, animal clue animations, and HUD layers;
5. Required asset corruption (`distant_hills.png`) fail-soft fallback to `_draw_legacy_forest_background`;
6. Optional atmosphere corruption (`fog_strip.png`) fail-soft soft isolation skipping only the fog node;
7. Camera parallax + ambient motion (`drift_x`, `sway_x`, `breathe_alpha`);
8. All six responsive matrix rows (`1024×600` normal/large, `1280×800`, `1366×768`, `1920×1080`, `1111×700`);
9. Frame performance sanity: 258 frames / 10.01 s = 25.8 FPS;
10. Curated review set committed in `docs/reviews/visual/2026-08-21_scene-compositor-nascondino/` per `docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`.

Accepted via:

```text
docs/testing/2026-08-21_SCENE_COMPOSITOR_NASCONDINO_SIMULATOR.md
```

Evidence class: **SIMULATOR VISUAL REVIEW**.

---

# 5. Current checkpoint

| Field | Current state |
|---|---|
| Stable guide | `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` |
| Resume | `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` |
| Product discovery authority | `docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md` |
| Active focus | **V5 — Scene Composition Runtime & Nascondino nel Bosco accepted in Activity Simulator** |
| Environment coverage | V4 complete through Water/Pond; first runtime scene `forest_meadow_day_v1.toml` active |
| Catalogue/renditions | explicit semantic catalogue present; source version `0.2.0`; 15 Forest/Meadow PNG renditions generated |
| Activity cards | accepted at **SIMULATOR VISUAL REVIEW** |
| Shell panel | accepted at **SIMULATOR VISUAL REVIEW** |
| Root category button component | accepted at **SIMULATOR VISUAL REVIEW**, but old filter-row Home is superseded by Collection-first Home |
| Profile identity | accepted at **SIMULATOR VISUAL REVIEW** |
| Launch/error feedback | accepted at **SIMULATOR VISUAL REVIEW** |
| Empty basket | **SOURCE / NOT EXERCISED** |
| Navigation icon button | accepted at **SIMULATOR VISUAL REVIEW** |
| Collection-first Home | accepted at **SIMULATOR VISUAL REVIEW** (5 primary collections) |
| Collection portal frame | `ui.portal.frame/default` accepted at **SIMULATOR VISUAL REVIEW** |
| Scene compositor runtime | `PygameSceneRenderer` + `SceneCamera` accepted at **SIMULATOR VISUAL REVIEW** |
| Nascondino scene integration | `forest_meadow_day_v1.toml` in Nascondino accepted at **SIMULATOR VISUAL REVIEW** |
| Activity semantic API | implemented in source; Shape Garden proof is non-blocking |
| Completed visible protocols | `docs/testing/2026-08-20_V5_SHARED_UI_CARD_SIMULATOR.md`; `docs/testing/2026-08-20_V5_SHARED_UI_PANEL_SIMULATOR.md`; `docs/testing/2026-08-20_V5_SHARED_UI_CATEGORY_BUTTON_SIMULATOR.md`; `docs/testing/2026-08-21_V5_SHARED_PROFILE_IDENTITY_SIMULATOR.md`; `docs/testing/2026-08-21_V5_SHARED_FEEDBACK_SIMULATOR.md`; `docs/testing/2026-08-21_V5_SHARED_NAVIGATION_CHROME_SIMULATOR.md`; `docs/testing/2026-08-21_COLLECTION_FIRST_HOME_SIMULATOR.md`; `docs/testing/2026-08-21_COLLECTION_PRIMARY_VOCABULARY_SIMULATOR.md`; `docs/testing/2026-08-21_SCENE_COMPOSITOR_NASCONDINO_SIMULATOR.md` |
| Next exact action | S4 motion/scene vocabulary expansion or Web Activity semantic visual adapter |

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
- [x] Collection-first Home source migration;
- [x] `ui.portal.frame/default` explicit source rendition selection;
- [x] Collection-first Home simulator acceptance;
- [x] renderer-neutral semantic request portion of Activity API;
- [x] first Python Activity source consumer (Shape Garden);
- [ ] Shape Garden Activity Simulator acceptance (non-blocking);
- [ ] future Web Activity semantic adapter/transport;
- [ ] future adaptive optional sub-Collection implementation;
- [ ] future audience/Parent per-child discovery policy implementation;
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
- proof-only Activities displacing visible product work once the shared seam is established;
- continuing to polish the old `All + filters` root after Collection-first Home is the accepted product target;
- exposing Collections as filesystem folders or building deep taxonomies.

---

# 9. Progress log — append only

The entries below preserve the workstream chronology. Corrections/new state are appended rather than rewriting old experiments into successes.

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
- Added pack/library inventories.
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

## 2026-08-20 — first Python Activity semantic visual source seam
- Added read-only `SharedVisualReference` plus `get_shared_visual(...)` / `get_shared_visual_path(...)`.
- Added Shape Garden as the first source consumer of `ui.shadow.soft`.
- Evidence remains SOURCE; the proof no longer blocks visible Shell work.

## 2026-08-20 — visible shared Activity cards moved into the real child Shell
- Added `SharedUiActivityCardMixin` for `ui.card.activity/default|focused`.
- Existing primitive tile remained fallback; lifecycle/catalogue/input authority stayed unchanged.

## 2026-08-20 — shared Activity cards accepted in simulator
- Full six-row matrix plus selection, hover, launch/return and fallback cases passed.
- Synthetic pointer tracking was corrected for simulator `MOUSEMOTION`.
- Frame sanity measured 27.2 FPS.

## 2026-08-20 — shared Shell panel accepted in simulator
- `ui.panel.base/default` integrated behind profile picker and Activity catalogue.
- Alpha tile-cache correction removed rectangular cutouts.
- Six-row matrix/fallback and 29.5 FPS sanity passed.

## 2026-08-20 — shared category buttons moved into the real child Shell
- Added `SharedUiCategoryButtonMixin` for `ui.button.primary/default|hover`.
- Preserved category identity/hit/navigation semantics and isolated fallback.

## 2026-08-20 — shared category buttons accepted in simulator
- Baseline/hover/category open-return/lifecycle/fallback + six-row matrix passed.
- Frame sanity measured 29.6 FPS.

## 2026-08-21 — panel geometry maximized, headless simulator added, profile identity accepted
- Owner-directed panel geometry was corrected to use the screen vertically while preserving 640:420 aspect ratio and full large Activity cards within the authored tray.
- Added non-intrusive `--headless` / `GREIA_SIMULATOR_HEADLESS=1` simulator execution through SDL dummy drivers.
- `ui.avatar.frame/default` generated and integrated.
- Six-row responsive/fallback/profile-switch review passed; frame sanity ~27.4 FPS.
- Canonical acceptance commit: `7dc5d39df51fd3404d222c762d7b5d48133def9d`.

## 2026-08-21 — shared Shell feedback accepted
- Generated `ui.loading.orbit`, `ui.error.gentle` and `ui.empty.basket` runtime renditions.
- Launch overlay and error cloud exercised through the real headless Activity Simulator with isolated fallbacks.
- Empty basket remained SOURCE / NOT EXERCISED.
- Responsive overlay review and 27.9 FPS sanity passed.
- Canonical acceptance commit: `5d8208883b840318b508b2dddc83c829e826a0e7`.

## 2026-08-21 — shared Shell navigation chrome source tranche
- Promoted `icon_button.svg` as semantic `ui.button.icon/default`.
- Added `SharedUiNavigationChromeMixin` for local Back and conditional page/scroll controls.
- Added isolated fail-soft fallback.

## 2026-08-21 — shared Shell navigation chrome accepted
- Local agent generated `icon_button.png` and exercised the dated navigation protocol headlessly.
- In-category Back default/hover/click passed.
- Activity scroll controls default/hover/page transitions passed.
- Profile pagination remained SOURCE / NOT EXERCISED because the workspace had <=4 profiles.
- Corrupt icon-button fallback preserved all unrelated shared visuals.
- Six responsive rows passed; frame sanity was 271 frames / 10.01 s = 27.1 FPS.
- Canonical acceptance commit: `370d96039546178ed2c64366bdaec1b5dc986be2`.

## 2026-08-21 — Scene Actor Lilli and Nascondino HUD accepted in simulator
- Integrated first shared Greia character actor (`character.lilli/default|blink`) and contact shadow (`shadow.contact.small.01/default`) using `SceneActorDefinition` and `actor_scene_sample`.
- Corrected Nascondino child HUD typography to 24 px in Normal, 26 px in Large, 20 px in Compact (eliminating the 18 px lower guardrail violation and fixing card geometry).
- Verified deterministic eye blink and grounded vertical idle motion.
- Six-row responsive matrix, optional corrupt fog isolation, and required scene fallback passed.
- Steady state simulator performance sanity measured 230 frames / 10.01 s = 23.0 FPS.
- Curated review set committed in `docs/reviews/visual/2026-08-21_scene-actor-lilli-nascondino/` and review package assembled at `./GREIA_VISUAL_REVIEW_SCENE_ACTOR_LILLI_2026-08-21.zip`.

## 2026-08-21 — Visual Authoring Library Comparison Benchmark
- Executed quality benchmark against baseline `forest_meadow/v0.2/` per `docs/testing/2026-08-21_VISUAL_AUTHORING_LIBRARY_COMPARISON.md`.
- Primary review (`PRIMARY_REVIEW.md`) confirmed local authoring agent superiority over legacy baseline.
- Assembled `./GREIA_VISUAL_REVIEW_AUTHORING_LIBRARY_COMPARISON_2026-08-21.zip`.

## 2026-08-21 — Visual Authoring Kit Variation Benchmark
- Executed variation & coherence benchmark per `docs/testing/2026-08-21_VISUAL_AUTHORING_KIT_VARIATION_BENCHMARK.md`.
- Created candidate Authoring Kit at `assets/visual/authoring_kit/v0.1-candidate/` (4 material standards, 4 assembly recipes, 9 candidate proof SVGs).
- Proved 3 distinct trees (Broad Oak, Slender Birch, Interactive Hollow Tree), 2 bushes (Plump Berry, Tall Bramble), and 2 rocks (Boulder Cluster, Shelf Outcrop) sharing cohesive storybook lighting and palette without formulaic cloning or glossy specular blobs.
- Rendered 6 curated review artifacts in `docs/reviews/visual/2026-08-21_authoring-kit-variation/` and packaged `./GREIA_VISUAL_REVIEW_AUTHORING_KIT_VARIATION_2026-08-21.zip`.

**Next exact action:** Owner visual review of Authoring Kit Variation transfer ZIP.

