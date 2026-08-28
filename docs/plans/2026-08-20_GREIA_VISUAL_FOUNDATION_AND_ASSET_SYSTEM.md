# Greia Visual Foundation and Asset System — Active Art Workstream Plan

**Status:** ACTIVE ART/VISUAL WORKSTREAM  
**Last checkpoint review:** 2026-08-28  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Stable system/index guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Current visual resume:** `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`

This plan owns **sequencing, current checkpoint, milestone state and append-only progress history** for the Greia visual workstream. Stable architecture belongs in `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`; quick continuation state belongs in `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`.

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → explicit semantic runtime consumption → Shell/Activity reuse**

Broad source-art coverage already exists. **V5 shared consumption/integration remains active.** The reusable runtime seam is proven across Shell UI, canonical characters, scenes and multiple first-party Activity productizations. The current visible art focus is now the **Greia Encyclopedia visual reauthoring**, where complete mechanical breadth exposed a systemic quality failure caused by overuse of programmer-drawn Pygame primitives for final subject art. The response is not another generic pack or a 43-page bulk redraw: build a bounded Encyclopedia visual foundation, then owner-review a representative golden-master set before migration.

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

Canonical 6-member cast: **Lilli, Leo, Flash, Dani, Tito, Momo** in the accepted simplified Puff/Bean/Robot direction (Authority: `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`).

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

| Pack / layer | Source | Current scope |
|---|---|---|
| Forest / Meadow v0.3 | `assets/visual/environments/forest_meadow/v0.3/` | promoted source pool feeding generic Nature/Landscape + FX |
| Workshop v0.2 | `assets/visual/environments/workshop/v0.2/` | promoted source pool feeding generic interiors/furniture/props/play/light |
| Generic authoring library | `assets/visual/authoring_library/` | canonical semantic discovery indexes over promoted/reviewed source pools |
| Shared UI v0.1 | `assets/visual/ui/v0.1/` | panels/cards/buttons/tabs/badges/progress/bubbles/reward/focus/loading/error/empty/portal family |
| Historical source pools | Clinic / Reading / Fantasy / Water folders | provenance/reference pools harvested into generic admission states |

Inventories:

```text
assets/visual/library_v0.1.toml
assets/visual/packs_v0.1.toml
assets/visual/authoring_library/
```

Themed source pools remain provenance/reference material. The generic semantic authoring library is the primary Activity-author discovery layer. Do not create another environment family merely to keep producing assets.

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
ui.portal.frame            default
ui.shadow.soft             default
```

`tools/build_visual_renditions.py` renders through build-host librsvg/`rsvg-convert`, validates dimensions/containment and writes PNG/catalog output transactionally. The target device does not rasterize SVG.

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

`activities/shape_garden/main.py` is the first source proof. Future Web support must preserve semantic IDs/variants through a controlled URL/handle transport rather than exposing host paths.

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

This evidence remains valid for the component. It does **not** mean the filter-row information architecture remains the preferred normal child Home.

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

## 4.12 Shared Shell navigation chrome — ACCEPTED (SIMULATOR VISUAL REVIEW)

`ui.button.icon/default` is consumed through `src/greia_launcher/navigation_chrome_presentation.py`.

Accepted via:

`docs/testing/2026-08-21_V5_SHARED_NAVIGATION_CHROME_SIMULATOR.md`

Canonical acceptance commit: `370d96039546178ed2c64366bdaec1b5dc986be2`.

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

Accepted protocols:

```text
docs/testing/2026-08-21_COLLECTION_FIRST_HOME_SIMULATOR.md
docs/testing/2026-08-21_COLLECTION_PRIMARY_VOCABULARY_SIMULATOR.md
```

Evidence class: **SIMULATOR VISUAL REVIEW**.

## 4.14 Scene Composition Runtime & Nascondino nel Bosco — ACCEPTED (SIMULATOR VISUAL REVIEW)

Architecture plan:

`docs/plans/2026-08-21_GREIA_SCENE_COMPOSITION_RUNTIME.md`

Accepted components include `SceneDefinition`, `SceneNode`, `SceneCamera`, `PygameSceneRenderer`, the `forest_meadow_day_v1.toml` scene, Nascondino integration, required/optional fail-soft behavior, parallax/ambient motion and the six-row responsive matrix.

Accepted via:

`docs/testing/2026-08-21_SCENE_COMPOSITOR_NASCONDINO_SIMULATOR.md`

Evidence class: **SIMULATOR VISUAL REVIEW**.

---

# 5. Current checkpoint

| Field | Current state |
|---|---|
| Stable guide | `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` |
| Resume | `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` |
| Product discovery authority | `docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md` |
| Runtime visual focus | **Existing V5 runtime/scene/shared UI foundations accepted where recorded; current visible focus is Encyclopedia reauthoring** |
| Authoring focus | **Encyclopedia E1 + E2 source + runtime art + real-Simulator capture COMPLETE; awaiting owner direction approval** |
| Encyclopedia forensic audit | `docs/reviews/2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md` — current graphics rejected as final product quality |
| Encyclopedia visual subplan | `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md` |
| Encyclopedia golden-master review | `docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/` (REVIEW.md, layout-audit.json, contact-sheet-primary.png, 4 curated PNGs) + non-committed `GREIA_VISUAL_REVIEW_ENCYCLOPEDIA_GOLDEN_MASTER_2026-08-28.zip` |
| Generic library | full source harvest complete; Batch A owner-reviewed selectively |
| Generic Batch B rule | remains unauthorized; Encyclopedia topic-specific art should normally stay Activity-local |
| Canonical cast | six-character v0.1 runtime family accepted; integrate intentionally rather than tiny corner stamps |
| Prior first-party Batch 1 | `treno_numeri`, `labirinto_magico`, `acquario_magico` accepted historical productization evidence |
| Next exact action | STOP and wait for owner direction approval on the six golden-master prototypes before any E3 section-page or E4 entry migration |

---

# 6. Milestones

## V1 — Character/style seed **[SUFFICIENT TO UNBLOCK LIBRARY]**
- [x] simplified character direction;
- [x] core cast seed;
- [ ] useful refinement may continue without blocking integration.

## V2 — Forest/meadow **[PROMOTED SOURCE POOL]**
- [x] source pack;
- [x] metadata/composition/parallax proof;
- [x] target-size review;
- [x] v0.3 selective promotion.

## V3 — Shared UI kit **[DESKTOP CANDIDATE BUILT / RUNTIME SUBSET ACCEPTED]**
- [x] shared components/states;
- [x] shadow/highlight treatment;
- [x] target references;
- [x] multiple runtime consumers accepted at simulator scope.

## V4 — Additional environment/source coverage **[SOURCE COVERAGE COMPLETE; THEMES NOW PROVENANCE POOLS]**
- [x] Workshop;
- [x] Clinic;
- [x] Reading/classroom;
- [x] Fantasy/village/night;
- [x] Water/pond;
- [x] full source harvest into generic taxonomy;
- [ ] new family only for a demonstrated generic gap.

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
- [ ] physical low-resource evidence where a stronger claim requires it.

## V6 — Generic Activity-authoring toolbox **[ACTIVE]**
- [x] generic semantic taxonomy established;
- [x] six authoring-library indexes established;
- [x] full source harvest across Forest/Workshop/Clinic/Reading/Fantasy/Water;
- [x] preferred vs candidate-reference admission states;
- [x] Core Essentials Batch A created and owner-reviewed;
- [ ] Batch A selective stable admission;
- [ ] deterministic authoring discovery helper;
- [ ] skill update to use discovery helper;
- [ ] real Activity-authoring exercise using the generic toolbox/skill.

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
- exposing Collections as filesystem folders or building deep taxonomies;
- treating themed source bundles as the generic authoring taxonomy;
- redrawing every candidate-reference asset until it becomes preferred;
- expanding asset count by inertia before making the toolbox discoverable to user agents;
- treating a mechanically complete page set as visually complete;
- using raw Pygame primitives as the default final illustration method for real-world subjects;
- bulk-migrating a large Activity before a representative visual direction is owner-approved.

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
- Built a bounded 15-master night/fantasy village source pack.
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
- Corrected Nascondino child HUD typography to 24 px in Normal, 26 px in Large, 20 px in Compact.
- Verified deterministic eye blink and grounded vertical idle motion.
- Six-row responsive matrix, optional corrupt fog isolation, and required scene fallback passed.
- Steady state simulator performance sanity measured 230 frames / 10.01 s = 23.0 FPS.

## 2026-08-21 — Visual Authoring Library Comparison Benchmark
- Executed quality benchmark against baseline `forest_meadow/v0.2/`.
- Primary review confirmed the owner's local authoring agent could produce stronger source art than the legacy baseline.
- This conclusion applies only to maintainer-side art production, not arbitrary future user agents.

## 2026-08-21 — Visual Authoring Kit Variation Benchmark
- Created candidate Authoring Kit experiments.
- Subsequent owner review rejected treating those specimen/recipe iterations as a universal user-agent architecture and stopped the hero-tree/parametric-kit rabbit hole.

## 2026-08-21 — Generic semantic authoring-library correction
- Separated themed source/provenance pools from the user-facing generic semantic taxonomy.
- Established `assets/visual/authoring_library/` as the primary authoring discovery layer.
- Core generic collections: Nature/Landscape, Interiors/Architecture, Furniture/Storage, Everyday Props/Containers, Making/Learning/Play, Lighting/Atmosphere/FX/Shadows.
- `skills/greia-visual-authoring/SKILL.md` remains model/tool agnostic and teaches REUSE vs COMPOSE/ADAPT vs CREATE ORIGINAL.

## 2026-08-21 — Full source harvest
- Harvested Reading/Classroom, Fantasy/Village/Night and Water/Pond before declaring new gaps.
- Corrected false missing-role assumptions into `TRUE_MISSING`, `QUALITY_GAP`, `VARIETY_GAP`, and `NO_GAP`.
- Full-harvest commit: `2dcf306589efb721db4cac6bca7233c342fcfaa1`.

## 2026-08-21 — Generic Core Essentials Batch A
- Created 16 cross-category generic candidate assets + 2 authoring ingredients in `assets/visual/pack_candidates/generic_core_essentials/2026-08-21/`.
- Candidate commit: `574f19530ee292a81225ff14c09ad8b35f6cf933`.
- Owner reviewed the actual 10-sheet transfer ZIP.
- Selective disposition: 9 finished assets + 2 ingredients approved for `preferred`; 7 finished assets intentionally remain `candidate_reference`.
- No per-object Batch A redraw loop authorized.

## 2026-08-22 — Canonical Cast v0.1 Runtime Acceptance Recheck & Final Integrity Closure
- Resolved all review blockers from `OWNER_REVIEW.md` and `OWNER_REVIEW_CAPTURE_INTEGRITY.md`.
- Implemented bounded failed-rendition cache (max 64 entries) in `PygameSceneRenderer` avoiding per-frame decode churn.
- Demonstrated cold required default failure safe-fallback screen and isolated single-target non-default fallback (`flash_happy.png`).
- Direct on-screen developer diagnostics proved active variant, fallback state, outer viewport, and UI scale.
- Formally accepted and closed via `docs/reviews/visual/2026-08-22_canonical-cast-v01-final-capture/OWNER_REVIEW.md`.

## 2026-08-22 — Shape Garden Real Visual-Authoring Workflow Exercise
- Exercised full end-to-end authoring workflow on first-party Activity `org.greia.shape-garden` (`activities/shape_garden/`).
- Discovered and reused generic Pack A resources (`ground.grass_edge.01`, `atmosphere.sunlight_rays.01`, `hills.distant.01`, `cloud.large.01`, `cloud.small.01`, `bush.flowering.01`, `ui.shadow.soft`).
- Integrated canonical geometry companion Dani (`character.dani`) with happy reaction on shape creation.
- Preserved 100% educational geometry mechanics, added organic green sprout stems, grounded shadows, and spawn growth delight.
- Verified responsive presentation across 4 viewports (1024x600 normal, 1024x600 large, 1366x768 compact, 1280x800 normal), motion-disabled mode, and fail-soft optional node resilience.
- Curated review folder `docs/reviews/visual/2026-08-22_shape-garden-visual-authoring-workflow/` and transfer bundle `GREIA_VISUAL_REVIEW_SHAPE_GARDEN_AUTHORING_WORKFLOW_2026-08-22.zip`.
- Generic library gap outcome: `NO_GAP`. Generic Batch B remains unauthorized.

## 2026-08-22 — Costruiamo Ponti Real Visual-Authoring Stress Exercise
- Executed second real first-party Activity authoring exercise on `org.greia.costruiamo-ponti` (`activities/costruiamo_ponti/`).
- Stressed the full authoring spectrum:
  - `REUSE`: Canonical generic library assets (`character.flash`, `hills.distant.01`, `cloud.large.01`, `cloud.small.01`, `atmosphere.sunlight_rays.01`, `bush.flowering.01`, `rock.cluster.large.01`, `shadow.contact.small.01`, `ui.shadow.soft`).
  - `COMPOSE_ADAPT`: Authored 3 world terrain environments (`bank_river.png`, `bank_canyon.png`, `bank_space.png`) with distinct storybook diorama geology across River, Canyon, and Space worlds.
  - `CREATE_ORIGINAL`: Designed and rendered a coherent activity-local material family in `activities/costruiamo_ponti/assets/` (`block_wood.png`, `block_stone.png`, `block_shroom.png`, `block_rainbow.png`, `trampoline.png`, `goal_flag.png`) with SVG masters in `source/` and build-time PNGs in `runtime/`.
  - `KEEP_EXISTING_INTENTIONAL`: Preserved 100% of puzzle mechanics, 4-material requirements, sound synthesis, storage persistence, event emissions, and platform Home button integration.
- Integrated canonical traveler Flash (`character.flash`) with `neutral` idle, `happy` walking hop, spring bounce, and `surprised` trampoline rebound.
- Captured complete 13-PNG evidence suite across all 3 worlds, material selection, crossing success, trampoline failure rebound, 2 responsive viewports (1024x600 large, 1366x768 compact), static motion-disabled mode, and fail-soft procedural fallback.
- Created review package `docs/reviews/visual/2026-08-22_costruiamo-ponti-visual-authoring-stress/` and transfer bundle `GREIA_VISUAL_REVIEW_COSTRUIAMO_PONTI_AUTHORING_STRESS_2026-08-22.zip`.
- Generic library gap outcome: `NO_GAP`. Generic Batch B remains unauthorized.

## 2026-08-22 — Painting Visual Productization Exercise
- Executed third real first-party Activity authoring exercise on UI-heavy Phase-0 creation Activity `org.greia.painting` (`activities/painting/`).
- Decisions:
  - `COMPOSE_ADAPT`: Storybook warm studio tabletop mat background framing the drawing canvas without eating screen space.
  - `CREATE_ORIGINAL`: Designed and rendered a complete activity-local UI asset family in `activities/painting/assets/` (`tool_gallery.png`, `tool_undo.png`, `tool_new.png`, `tool_eraser.png`, `brush_small.png`, `brush_medium.png`, `brush_large.png`, `canvas_card_frame.png`, `color_well_dish.png`) with clean SVG masters in `source/` and build-time PNGs in `runtime/`.
  - `KEEP_EXISTING_INTENTIONAL`: Preserved 100% of PaintingRepository, StrokeHistory, autosave idle loop, undo limits, and platform Home button integration.
  - Mascot Decision: Intentionally omitted mascot to ensure the child's drawing canvas remains generous, uncluttered, and unencumbered.
- Captured complete 12-PNG evidence suite in `docs/reviews/visual/2026-08-22_painting-visual-productization/` across empty canvas, drawing in progress, rich multi-color drawing, palette selection affordances, best product proof, 3 responsive viewports (1024x600 large, 1366x768 compact, 1280x800 normal), static motion-disabled mode, fail-soft procedural fallback, and gallery saved thumbnail persistence.
- Packaged owner transfer bundle: `GREIA_VISUAL_REVIEW_PAINTING_PRODUCTIZATION_2026-08-22.zip`.
- Generic library gap outcome: **`NO_GAP`**. Generic Batch B remains unauthorized.

## 2026-08-22 — First-Party Activity Visual Audit & Batch 1 Productization
- Executed full headless Simulator visual audit across all 19 first-party Activities at 1024×600, scoring each 1–5 on 8 dimensions.
- Created audit matrix `docs/reviews/visual/2026-08-22_first-party-activity-visual-audit/VISUAL_AUDIT.md`, `visual-audit.json`, 5×4 owner contact sheet `CONTACT_SHEET.png`, and objective selection report `BATCH_1_SELECTION.md`.
- Selected lowest-scoring non-benchmarked priority targets for Batch 1:
  1. `org.greia.treno-numeri` (Initial score: 1.9 / 5.0 → Productized: **4.8 / 5.0**)
  2. `org.greia.labirinto-magico` (Initial score: 1.9 / 5.0 → Productized: **4.8 / 5.0**)
  3. `org.greia.acquario-magico` (Initial score: 2.4 / 5.0 → Productized: **4.7 / 5.0**)
- Productization Deliverables:
  - `treno_numeri`: Illustrated steam engine, Dani robot conductor mascot, rotating brass wheels, wooden fruit crates, scenic countryside valley, smoke particles.
  - `labirinto_magico`: Tito the Fox adventurer mascot, rotating magical vortex portal goal, 3D faceted crystal stars, beveled walls with depth shadows, tactile arrow D-pad.
  - `acquario_magico`: Illustrated tropical species (clownfish, sea turtle, octopus, dolphin, pufferfish), dual coral reefs, sunlight water caustics, day/night bioluminescence.
- Full 8-screenshot evidence suite, `AUTHORING_AUDIT.md`, `authoring-audit.json`, and `simulator-trace.json` generated for all 3 targets under `docs/reviews/visual/2026-08-22_first-party-batch-1/<activity>/`.
- Batch review document `OWNER_RECHECK.md` and root transfer bundle `GREIA_VISUAL_REVIEW_FIRST_PARTY_ACTIVITY_BATCH_1_2026-08-22.zip` packaged.
- Generic library gap conclusion: `NO_GAP`. Generic Batch B remains unauthorized.

## 2026-08-28 — Encyclopedia visual forensic correction and reauthoring gate
- Owner rejected the complete 43-page Encyclopedia screenshot set as aesthetically unacceptable despite green mechanical breadth.
- Primary forensic review identified the systemic cause: final real-world subject art and section worlds are dominated by raw Pygame primitives, sparse flat backgrounds, floating instrumentation-like discovery bubbles, corner-stamped mascots and weak interaction payoff.
- Recorded the rejection and preservation boundary in `docs/reviews/2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md`.
- Added bounded visual subplan `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md`.
- Preserved the healthy 43-page runtime/navigation/research architecture and the already-landed generic headless capture-settle repair.
- Paused broad 43-page visual recapture and final pointer/responsive acceptance until real graphics change.
- Established mandatory E1/E2 gate: shared Encyclopedia visual foundation + golden-master prototypes for Home, Animals section, Lion, Saturn, Gears and Pyramids (optional Body/Heart proof), followed by actual Simulator contact-sheet owner review.
- Explicitly prohibited bulk 43-page migration before owner direction approval and prohibited Generic Batch B by inertia.
- Current evidence class for the rejected presentation: **REJECTED EXPERIMENT / mechanically useful runtime foundation**.

**Next exact action:** implement Encyclopedia E1 visual foundation and E2 golden masters, capture a small curated real-Simulator prototype set, and stop for owner visual approval before migrating the remaining pages.

## 2026-08-28 — Encyclopedia E1 + E2 runtime art, Simulator prototype capture, review/contact-sheet (this work)

- Encyclopedia visual subplan E1 + E2 closed on the source/runtimer-artefact axis. Six 1024×600 PNGs built from the committed SVG masters (346 621 bytes), committed and pushed on `main` at `08fe71b`; `tools/build_encyclopedia_visual_assets.py --check` byte-verifies the committed pack against rebuilt masters.
- Three permanent review tools added under `tools/`: golden-master capture (one real Greia Shell session per page, launches the built-in `org.greia.enciclopedia` through the real launcher/profile-picker/catalogue path, captures initial + post-ACTIVATE frames, exercises the protected Greia Home return), review-set builder (3×2 contact sheet + 4 curated PNGs), and owner-transfer ZIP packager.
- Captured 10 1024×600 prototype frames (Home, Animals, Lion initial+ACTIVATE, Saturn initial+ACTIVATE, Gears initial+ACTIVATE, Pyramids initial+ACTIVATE) plus one compact (1024×600 + `interface_size=compact`) and one larger (1280×800 + `interface_size=normal`) responsive row, from the real headless Greia Simulator at `08fe71b`.
- Curated review set committed at `docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/` with `REVIEW.md` (including a per-page defect log) and `layout-audit.json` derived from the real `PageShellLayout`, `PORTAL_CENTERS`, and per-page discovery centers. Non-committed owner-transfer ZIP: `GREIA_VISUAL_REVIEW_ENCYCLOPEDIA_GOLDEN_MASTER_2026-08-28.zip` (677 KB).
- `make verify`: 1462/1462 PASS on the real checkout at the final SHA. Focused Encyclopedia tests: 19/19 PASS. The only source correction needed was a one-file tightening of the over-broad runtime-cue vs voice-ledger parity check in `tests/test_encyclopedia_authoring_tools.py` (subtract `VisualLibrary.ART_ASSETS`).
- Pre-reader/no-reading review on the six prototypes: `PRE_READER_CORE_FLOW_PASS=yes`, `TEXT_REQUIRED_FOR_GAMEPLAY=no`, `NO_READING_FIRST_ACTION_PASS=yes`, `PRIMARY_INSTRUCTION_CHANNEL=visual`.
- This is `SIMULATOR VISUAL REVIEW` evidence only. **Owner direction approval still pending.** E3 section-page migration and E4 entry migration remain hard-blocked.

## 2026-08-28 — Encyclopedia E2R refinement (per primary review)

- Addressed every E2R correction in `docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/PRIMARY_REVIEW_2026-08-29.md` on the same six pages: Home miniature worlds, Animals sun/Back fix + habitat props, Lion deeper mane + felt-tag tokens + integrated Tito + strengthened mane reveal, Saturn preserved reference + telescope-card tokens + Leo at telescope + full orbit path reveal, Gears real workshop + no rack collision + workshop-tag tokens + contact-point motion reveal, Pyramids authored workers + excavation tokens + Leo field-guide + outlined base block reveal.
- Discovery-token silhouettes are now scene-native (felt tag / telescope card / workshop tag / excavation marker). Shared interaction/state logic remains one component (`draw_discovery_token` accepts a `token_shape` parameter).
- Baked presenters removed from the six SVGs; runtime canonical character draws at the integrated scene position.
- Source at `8fa41a3`: `make verify` 1462/1462, focused Encyclopedia tests 19/19, build `--check` PASS 6, headless Simulator 6/6 sessions PASS, protected Greia Home 6/6, ACTIVATE payoffs 4/4, pre-reader/no-reading `yes/yes/yes/visual`.
- Updated curated review set + new `initial-vs-activated` comparison sheet under `docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/`. New non-committed owner ZIP `GREIA_VISUAL_REVIEW_ENCYCLOPEDIA_GOLDEN_MASTER_2026-08-28.zip` (685 KB).
- `libpng error: bad adaptive filter value` line in the child log remains an unresolved diagnostic per the local-agent brief §7.
- **Owner direction approval is still pending.** E3/E4 remain hard-blocked.

