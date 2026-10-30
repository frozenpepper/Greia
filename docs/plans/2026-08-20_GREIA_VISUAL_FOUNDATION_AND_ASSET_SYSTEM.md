# Greia Visual Foundation and Asset System — Active Art Workstream Plan

**Status:** ACTIVE ART/VISUAL WORKSTREAM — Encyclopedia E3 ACCEPTED at 03bf76ac; Activity modernization COMPLETE at e2b831da (source green)  
**Last checkpoint review:** 2026-10-16  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Stable system/index guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Current visual resume:** `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`

This plan owns **sequencing, current checkpoint, milestone state and append-only progress history** for the Greia visual workstream. Stable architecture belongs in `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`; quick continuation state belongs in `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`.

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → explicit semantic runtime consumption → Shell/Activity reuse**

Broad source-art coverage already exists. **V5 shared consumption/integration remains active.** The reusable runtime seam is proven across Shell UI, canonical characters, scenes and multiple first-party Activity productizations. The current visible art focus is the **Greia Encyclopedia visual reauthoring**. The Encyclopedia golden-master direction is now owner-approved after direct source correction; the active subphase is E3 six-section runtime closure before any factual-entry migration.

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
2026-08-21_COLLECTION_FIRST_HOME_SIMULATOR.md (archived; see git history)
2026-08-21_COLLECTION_PRIMARY_VOCABULARY_SIMULATOR.md (archived; see git history)
```

Evidence class: **SIMULATOR VISUAL REVIEW**.

## 4.14 Scene Composition Runtime & Nascondino nel Bosco — ACCEPTED (SIMULATOR VISUAL REVIEW)

Architecture plan:

`docs/plans/2026-08-21_GREIA_SCENE_COMPOSITION_RUNTIME.md`

Accepted components include `SceneDefinition`, `SceneNode`, `SceneCamera`, `PygameSceneRenderer`, the `forest_meadow_day_v1.toml` scene, Nascondino integration, required/optional fail-soft behavior, parallax/ambient motion and the six-row responsive matrix.

Accepted via:

`2026-08-21_SCENE_COMPOSITOR_NASCONDINO_SIMULATOR.md` (archived; see git history)

Evidence class: **SIMULATOR VISUAL REVIEW**.

---

# 5. Current checkpoint

| Field | Current state |
|---|---|
| Stable guide | `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` |
| Resume | `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` |
| Product discovery authority | `docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md` |
| Runtime visual focus | **Existing V5 runtime/scene/shared UI foundations accepted where recorded. Encyclopedia E3 runtime pack is ACCEPTED at `03bf76ac`. Current focus (2026-10-15): art-direction reset and library redraw under `docs/design/GREIA_SVG_AUTHORING_RULES.md` (ACCEPTED), per `docs/reviews/visual/2026-10-15_asset_library_audit/REVIEW.md` (archived; see git history) Shell storybook redesign (Home, picker, Collection pages, Sea theme folder, My Creations, launch screen) and control-kit art are SOURCE + headless DESKTOP VISUAL REVIEW only (2026-10-15).** |
| Authoring focus | **Shared library v1 is REGISTERED (catalogue 0.6.0: `bg.*`, `prop.*`, `creature.*`, `icon.hud.*`, `fx.*`, cast variants). Cast poses, P0 Activity icons and the full flat core-icon family are done. Next art work is gap-filling only on demand from the P7 Activity reworks (W2); Opus remains the SVG model. Encyclopedia E4 remains governed by its own subplan.** |
| Checkpoint 2026-10-16 | **All 45 Activities are reworked on the shared library and control kit (P7 W0–W3, SOURCE + DESKTOP VISUAL REVIEW only).** Catalogue is 0.7.0 (62 vocabulary pictures added, `a779b10f`). Encyclopedia **E4 is COMPLETE** (`7b1f6b2c`, 36 authored storybook scenes, canonical cairo backend; 43 PNGs reproduce byte-for-byte); **E5 interaction visual-language pass is next**. Many Activities authored private art kept Activity-local as candidates awaiting library promotion (Serra plants, Specchi mosaic tiles, Alfabeto pictures, Stelle constellations, Morbidi parts, Teatrino puppets, bridge/marble-run/picnic sets, Volo dragon, Colline buggy, instruments, pet props, tokens; full list in `P7_ACTIVITY_QUALITY_PROGRAM.md` §8). No Simulator or physical visual review of the reworks exists. |
| Checkpoint 2026-10-16 (awards) | **Award frames redrawn as flat `ui.award.<family>` renditions (bronze medal / silver scalloped medal / gold cup / special rosette + grey locked silhouettes); badge celebration and trophy-shelf Badge Library consume them. SOURCE + DESKTOP VISUAL REVIEW only.** |
| Checkpoint 2026-10-21 (@2x) | **Shared and Activity-private runtime art now has `<name>@2x.png` siblings (same SVG masters, exact 2x) used only by the high-resolution layer at >=1.2x; 13 Activity PNGs have none because the shipped PNG no longer matches its SVG. SOURCE + DESKTOP VISUAL REVIEW only; no Aspire visual review of the new art.** |
| Parent mark (2026-10-30) | Parent client reuses the existing website Greia star-G asset instead of its placeholder; SOURCE + local browser review, not installed physical review. |
| Encyclopedia forensic audit | `2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md` (archived; see git history) — prior graphics rejected as final product quality |
| Encyclopedia visual subplan | `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md` |
| Encyclopedia current source review | `SOURCE_REVIEW.md` (archived; see git history) |
| Encyclopedia runtime gate | `2026-08-29_ENCYCLOPEDIA_E3_SECTION_RUNTIME_REVIEW.md` (archived; see git history) |
| Generic library | full source harvest complete; Batch A owner-reviewed selectively |
| Generic Batch B rule | remains unauthorized; Encyclopedia topic-specific art should normally stay Activity-local |
| Canonical cast | six-character v0.1 runtime family accepted; integrate intentionally rather than tiny corner stamps |
| Public website | owner promoted the first direction to the official website work in progress at `website/`. The opening now uses the original high-resolution final boot frame over a source-referenced, website-only wide panorama, with authentic 52-frame playback and continuous pointer-responsive fireflies. English Simulator captures, readable Parent enlargement, detailed OS/hardware/agent-authoring/voice/network/education copy, Downloads and individual Activity Library remain. DESIGN SPEC / DESKTOP VISUAL REVIEW only; installer and package releases remain unavailable, with no Greia runtime or Encyclopedia phase change. Historical alternatives remain at `docs/design/website_mocks_2026-09-23/`. |
| Prior first-party Batch 1 | `treno_numeri`, `labirinto_magico`, `acquario_magico` accepted historical productization evidence |
| Next exact action | Activity reworks (P7 W2: number, literacy and creative ladders) consume the library through semantic IDs and the shared control kit (ADR 0037) instead of private art; add a missing asset to `shared_visuals_v1_source.toml` only for a demonstrated gap, then `make visual-assets` / `make visual-assets-check`. Pending: stronger theme-folder tile silhouette; Simulator visual review of the redesigned Shell; owner voice approval (not an art task). |

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
- Resolved all review blockers from `OWNER_REVIEW.md` and `OWNER_REVIEW_CAPTURE_INTEGRITY.md` (archived; see git history).
- Implemented bounded failed-rendition cache (max 64 entries) in `PygameSceneRenderer` avoiding per-frame decode churn.
- Demonstrated cold required default failure safe-fallback screen and isolated single-target non-default fallback (`flash_happy.png`).
- Direct on-screen developer diagnostics proved active variant, fallback state, outer viewport, and UI scale.
- Formally accepted and closed via `docs/reviews/visual/2026-08-22_canonical-cast-v01-final-capture/OWNER_REVIEW.md` (archived; see git history).

## 2026-08-22 — Shape Garden Real Visual-Authoring Workflow Exercise
- Exercised full end-to-end authoring workflow on first-party Activity `org.greia.shape-garden` (`activities/shape_garden/`).
- Discovered and reused generic Pack A resources (`ground.grass_edge.01`, `atmosphere.sunlight_rays.01`, `hills.distant.01`, `cloud.large.01`, `cloud.small.01`, `bush.flowering.01`, `ui.shadow.soft`).
- Integrated canonical geometry companion Dani (`character.dani`) with happy reaction on shape creation.
- Preserved 100% educational geometry mechanics, added organic green sprout stems, grounded shadows, and spawn growth delight.
- Verified responsive presentation across 4 viewports (1024x600 normal, 1024x600 large, 1366x768 compact, 1280x800 normal), motion-disabled mode, and fail-soft optional node resilience.
- Curated review folder `docs/reviews/visual/2026-08-22_shape-garden-visual-authoring-workflow/` (archived; see git history) and transfer bundle `GREIA_VISUAL_REVIEW_SHAPE_GARDEN_AUTHORING_WORKFLOW_2026-08-22.zip`.
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
- Created review package `docs/reviews/visual/2026-08-22_costruiamo-ponti-visual-authoring-stress/` (archived; see git history) and transfer bundle `GREIA_VISUAL_REVIEW_COSTRUIAMO_PONTI_AUTHORING_STRESS_2026-08-22.zip`.
- Generic library gap outcome: `NO_GAP`. Generic Batch B remains unauthorized.

## 2026-08-22 — Painting Visual Productization Exercise
- Executed third real first-party Activity authoring exercise on UI-heavy Phase-0 creation Activity `org.greia.painting` (`activities/painting/`).
- Decisions:
  - `COMPOSE_ADAPT`: Storybook warm studio tabletop mat background framing the drawing canvas without eating screen space.
  - `CREATE_ORIGINAL`: Designed and rendered a complete activity-local UI asset family in `activities/painting/assets/` (`tool_gallery.png`, `tool_undo.png`, `tool_new.png`, `tool_eraser.png`, `brush_small.png`, `brush_medium.png`, `brush_large.png`, `canvas_card_frame.png`, `color_well_dish.png`) with clean SVG masters in `source/` and build-time PNGs in `runtime/`.
  - `KEEP_EXISTING_INTENTIONAL`: Preserved 100% of PaintingRepository, StrokeHistory, autosave idle loop, undo limits, and platform Home button integration.
  - Mascot Decision: Intentionally omitted mascot to ensure the child's drawing canvas remains generous, uncluttered, and unencumbered.
- Captured complete 12-PNG evidence suite in `docs/reviews/visual/2026-08-22_painting-visual-productization/` (archived; see git history) across empty canvas, drawing in progress, rich multi-color drawing, palette selection affordances, best product proof, 3 responsive viewports (1024x600 large, 1366x768 compact, 1280x800 normal), static motion-disabled mode, fail-soft procedural fallback, and gallery saved thumbnail persistence.
- Packaged owner transfer bundle: `GREIA_VISUAL_REVIEW_PAINTING_PRODUCTIZATION_2026-08-22.zip`.
- Generic library gap outcome: **`NO_GAP`**. Generic Batch B remains unauthorized.

## 2026-08-22 — First-Party Activity Visual Audit & Batch 1 Productization
- Executed full headless Simulator visual audit across all 19 first-party Activities at 1024×600, scoring each 1–5 on 8 dimensions.
- Created audit matrix `docs/reviews/visual/2026-08-22_first-party-activity-visual-audit/VISUAL_AUDIT.md` (archived; see git history), `visual-audit.json`, 5×4 owner contact sheet `CONTACT_SHEET.png`, and objective selection report `BATCH_1_SELECTION.md`.
- Selected lowest-scoring non-benchmarked priority targets for Batch 1:
  1. `org.greia.treno-numeri` (Initial score: 1.9 / 5.0 → Productized: **4.8 / 5.0**)
  2. `org.greia.labirinto-magico` (Initial score: 1.9 / 5.0 → Productized: **4.8 / 5.0**)
  3. `org.greia.acquario-magico` (Initial score: 2.4 / 5.0 → Productized: **4.7 / 5.0**)
- Productization Deliverables:
  - `treno_numeri`: Illustrated steam engine, Dani robot conductor mascot, rotating brass wheels, wooden fruit crates, scenic countryside valley, smoke particles.
  - `labirinto_magico`: Tito the Fox adventurer mascot, rotating magical vortex portal goal, 3D faceted crystal stars, beveled walls with depth shadows, tactile arrow D-pad.
  - `acquario_magico`: Illustrated tropical species (clownfish, sea turtle, octopus, dolphin, pufferfish), dual coral reefs, sunlight water caustics, day/night bioluminescence.
- Full 8-screenshot evidence suite, `AUTHORING_AUDIT.md`, `authoring-audit.json`, and `simulator-trace.json` generated for all 3 targets under `docs/reviews/visual/2026-08-22_first-party-batch-1/<activity>/` (archived; see git history).
- Batch review document `OWNER_RECHECK.md` and root transfer bundle `GREIA_VISUAL_REVIEW_FIRST_PARTY_ACTIVITY_BATCH_1_2026-08-22.zip` packaged.
- Generic library gap conclusion: `NO_GAP`. Generic Batch B remains unauthorized.

## 2026-08-28 — Encyclopedia visual forensic correction and reauthoring gate
- Owner rejected the complete 43-page Encyclopedia screenshot set as aesthetically unacceptable despite green mechanical breadth.
- Primary forensic review identified the systemic cause: final real-world subject art and section worlds are dominated by raw Pygame primitives, sparse flat backgrounds, floating instrumentation-like discovery bubbles, corner-stamped mascots and weak interaction payoff.
- Recorded the rejection and preservation boundary in `2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md` (archived; see git history).
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
- Curated review set committed at `docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/` (archived; see git history) with `REVIEW.md` (including a per-page defect log) and `layout-audit.json` derived from the real `PageShellLayout`, `PORTAL_CENTERS`, and per-page discovery centers. Non-committed owner-transfer ZIP: `GREIA_VISUAL_REVIEW_ENCYCLOPEDIA_GOLDEN_MASTER_2026-08-28.zip` (677 KB).
- `make verify`: 1462/1462 PASS on the real checkout at the final SHA. Focused Encyclopedia tests: 19/19 PASS. The only source correction needed was a one-file tightening of the over-broad runtime-cue vs voice-ledger parity check in `tests/test_encyclopedia_authoring_tools.py` (subtract `VisualLibrary.ART_ASSETS`).
- Pre-reader/no-reading review on the six prototypes: `PRE_READER_CORE_FLOW_PASS=yes`, `TEXT_REQUIRED_FOR_GAMEPLAY=no`, `NO_READING_FIRST_ACTION_PASS=yes`, `PRIMARY_INSTRUCTION_CHANNEL=visual`.
- This is `SIMULATOR VISUAL REVIEW` evidence only. **Owner direction approval still pending.** E3 section-page migration and E4 entry migration remain hard-blocked.

## 2026-08-28 — Encyclopedia E2R refinement (per primary review)

- Addressed every E2R correction in `PRIMARY_REVIEW_2026-08-29.md` (archived; see git history) on the same six pages: Home miniature worlds, Animals sun/Back fix + habitat props, Lion deeper mane + felt-tag tokens + integrated Tito + strengthened mane reveal, Saturn preserved reference + telescope-card tokens + Leo at telescope + full orbit path reveal, Gears real workshop + no rack collision + workshop-tag tokens + contact-point motion reveal, Pyramids authored workers + excavation tokens + Leo field-guide + outlined base block reveal.
- Discovery-token silhouettes are now scene-native (felt tag / telescope card / workshop tag / excavation marker). Shared interaction/state logic remains one component (`draw_discovery_token` accepts a `token_shape` parameter).
- Baked presenters removed from the six SVGs; runtime canonical character draws at the integrated scene position.
- Source at `8fa41a3`: `make verify` 1462/1462, focused Encyclopedia tests 19/19, build `--check` PASS 6, headless Simulator 6/6 sessions PASS, protected Greia Home 6/6, ACTIVATE payoffs 4/4, pre-reader/no-reading `yes/yes/yes/visual`.
- Updated curated review set + new `initial-vs-activated` comparison sheet under `docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/` (archived; see git history). New non-committed owner ZIP `GREIA_VISUAL_REVIEW_ENCYCLOPEDIA_GOLDEN_MASTER_2026-08-28.zip` (685 KB).
- `libpng error: bad adaptive filter value` line in the child log remains an unresolved diagnostic per the local-agent brief §7.
- **Owner direction approval is still pending.** E3/E4 remain hard-blocked.

## 2026-08-29 — Encyclopedia owner-directed correction, E3 section source, focus and evidence hardening

- Owner rejected the E2R visual execution despite green technical evidence and identified concrete visual blockers: Home cards escaping the book, disconnected Lion anatomy, ambiguous Animals silhouettes and non-meshing Gears.
- Primary agent corrected the actual repository masters directly. Home now uses the enlarged book and centered 3×2 portal block (`x=267/512/757`); Animals has recognizable lion/elephant silhouettes; Lion anatomy is contiguous; Gears is a real toothed meshing train.
- Owner explicitly approved the corrected golden-master **visual direction**, closing the E2 design gate and authorizing E3 source work. Older E2R runtime pixels remain stale for exact current source.
- Authored and source-reviewed the five remaining section worlds around the accepted Animals reference: Space observatory, Earth landscape, Body discovery room, Machines workbench and History time trail. Follow-up source review corrected Body's schematic feel, weak Machines/History silhouettes and hidden Earth rain.
- Added machine-checkable section target geometry, non-overlapping hit regions, generous Body/Machines authored-object target areas and a live Solar-System stage-bounds contract for Space.
- Replaced the authored-section translucent filled focus patch with a perimeter-only non-occluding halo and removed Earth's duplicate floating yellow focus dot. Local desktop preview confirms the authored objects retain their color/texture instead of becoming yellow UI cards.
- Optimized full-screen authored scene consumption to opaque `Surface.convert()` while preserving `convert_alpha()` for transparent canonical character sprites. The Encyclopedia build contract now rejects non-RGB/alpha-bearing scene renditions; the current staged nine changed/new PNGs all report PNG color type 2 (RGB).
- Hardened E3 evidence provenance: capture requires a clean checkout, exactly eleven runtime PNGs already committed in the captured `HEAD`, byte identity between working PNG and `HEAD:<path>`, and records/rechecks both SHA-256 and Git blob IDs. The review builder rejects incomplete/non-Git-bound manifests.
- Added/updated focused regressions for section hit geometry, exact-SHA review tooling, non-occluding focus treatment and opaque scene surfaces.
- A recoverable nine-PNG maintainer-local staging bundle exists for the four changed golden masters + five E3 sections, with later Earth/Body renders refreshed. It is explicitly **not** Simulator or committed-art evidence.
- **Current gate:** E4 remains blocked. Build/check/commit the exact eleven-PNG current art pack on a real checkout, run focused tests + required verification, then capture Home + six sections through the Git-bound real Simulator harness and visually review the resulting family before E3 can close.

## 2026-09-23 — Public website concept exploration

- Added three standalone, reviewable webpage concepts under `docs/design/website_mocks_2026-09-23/`: a scroll-led Storybook, a choice-led Constellation atlas, and a searchable/filterable Activity Fair. These differ in both visual style and visitor operation.
- Reused canonical v0.1 cast PNGs, existing first-party Activity icons, Greia Nunito font and source palette; no shared art source was changed or promoted.
- Chromium desktop previews were inspected at 1440×900. Mobile pages were rendered at 390×844 and checked for horizontal overflow; Constellation selection and Activity Fair filtering/detail opening were exercised.
- Evidence is **DESIGN SPEC / DESKTOP VISUAL REVIEW** for website mocks only. There is no Greia Shell, Parent API, Simulator, physical-device, release, or Encyclopedia E4 acceptance in this tranche. The active visual/runtime checkpoint remains unchanged.

## 2026-09-23 — Public website concepts revised after owner review

- Owner judged the initial set insufficiently modern, dynamic and fun, and identified a missing primary brand source: `assets/boot/frames/frame_0051.png` on the canonical white boot screen. The earlier three mock versions are superseded as a website direction; the earlier ledger entry remains as history.
- Reworked all three around the real boot constellation and its white-screen composition: The Portal replays actual boot frames and changes Simulator captures through scroll chapters; Orbit changes a spatial portal through cast-star selection, keyboard arrows and dragging; Play Lab opens from the boot screen into a drawable, colour-changing world switcher. The comparison page now explains these three different visitor operations.
- Reused the six accepted cast renditions and historical development Simulator captures of the Shell and Activities. Reviewed the current Awwwards Sites of the Month and interaction references for identity-led transitions and direct scene interaction. No external layout, artwork or code was copied.
- Chromium visual and interaction checks covered 1440×900 desktop, 390×844 mobile and 320×700 narrow mobile; loaded images resolved and no page errors or horizontal overflow were observed. Portal replay and chapter switching, Orbit selection and keyboard arrows, and Play Lab scene keys, pointer drawing, clearing and return were exercised.
- Evidence remains **DESIGN SPEC / DESKTOP VISUAL REVIEW** for local website mocks. There is no new Greia Simulator run, physical-device proof, production web deployment, Encyclopedia E4 progress or release acceptance.

## 2026-09-23 — Public website third pass after second owner rejection

- Owner found the second set too conservative and asked for a new design model rather than further refinement. The owner liked the page-drawing interaction and identified a concrete defect: dragging over text could select it and interrupt drawing. The second Portal / Orbit / Play Lab structures are superseded for website direction; both earlier ledger entries remain historical.
- Rebuilt the three local mock sites and chooser: **Worlds in Motion** uses five full-screen illustrated scenes with scene navigation and the authentic boot frames; **The Wonder Map** is a draggable/zoomable four-world atlas with detail sheets; **The Scribble Machine** turns the whole page into a drawing surface with colour, character stamps, clearing and world switching. The Greia boot art, accepted cast and historical development Simulator captures remain source-grounded, but the page structures and visitor operations are new.
- Reviewed the current Awwwards Sites of the Month plus the live Ponpon Mania and Lama Lama sites and the Anime.js award entry. Applied art-led full-screen presentation, purposeful scene transition and direct interaction as Greia-specific designs; no external artwork, layout or code was copied.
- The Scribble Machine now disables text selection and native image dragging around the drawing area. A Chromium drag across the large headline created canvas pixels while `window.getSelection()` stayed empty; pointer capture, `preventDefault` and `touch-action: none` keep the stroke continuous. Sticker, colour, world and Clear controls were exercised.
- Inspected 1440×900 desktop previews, interior scenes, map detail sheets and mobile layouts. Chromium checks at 1440×900, 390×844 and 320×700 found no missing loaded images, page errors or horizontal overflow. Evidence is **DESIGN SPEC / DESKTOP VISUAL REVIEW** for website mocks only, with no new Greia runtime, physical, release or Encyclopedia acceptance claim.

## 2026-09-23 — Parent-facing first concept refinement

- Owner selected the first concept's navigation for deeper work and corrected its audience and content emphasis: the public site must speak primarily to parents, explain the old-device mission and architecture, and cover Greia Parents, personalized Activities, parent-authorized installation, the Creation Pack direction and voices. The owner also required a much larger, more useful logo and an animated web introduction. This entry refines the first direction; the other two third-pass mocks remain unchanged.
- Rebuilt `storybook.html` into seven strongly differentiated chapters with an automatic, skippable/replayable presentation of the original 52 boot frames. Added large transparent G/Greia identity derivatives made from the final boot frame for the hero, persistent navigation and ending. The external 17 August boot patch contains rendered PNGs and Plymouth code, not an SVG source; the new SVGs are explicitly website-study derivatives, not accepted brand masters.
- Added actual Greia Shell and Parent app development captures, interactive device/architecture/Parent topic/Activity example controls, and click-to-play existing Lilli/Flash/Momo English introductions. The site distinguishes existing contributor tools and capability-gated installation from the proposed self-service family Creation Pack and incomplete ordinary-release package lifecycle.
- Reviewed the current Awwwards Sites of the Month and ERA Residence award entry for contemporary entrance/scroll storytelling cues, then used Greia's own content and artwork. Inspected 1440×900 and mobile layouts through 320 pixels; controls and a real voice sample were exercised, with no missing loaded images or horizontal overflow. Evidence is **DESIGN SPEC / DESKTOP VISUAL REVIEW** for the website mock only. Greia runtime, physical-device, production-site and Encyclopedia evidence remain unchanged.


## 2026-09-23 — Parent website first concept rebuilt around the Greia night

- Owner rejected the prior white-screen entrance, weak small identity and thin information. The revised `storybook.html` opens with a full-width website-specific SVG landscape derived from the actual boot frame motifs: mountains, trees, a lit village, stars, flowers and fireflies. The unchanged 52 rendered boot frames animate in the centre; navigation and controls fade in on completion. Replay, skip and reduced-motion paths are present. The isolated website-study lockups now have heavier paths and crisp star centres. These are not accepted shared brand masters or boot changes.
- Added a twelve-capture, filterable/zoomable child Shell and Activity gallery, a device mission explorer for the early Acer and Raspberry Pi 400/500, a four-layer architecture explanation, a real enlargable Greia Parents development capture, illustrative interest/mode combinations for personalized Activities, a grounded Creation Pack path, six click-to-play accepted cast introductions and eight parent FAQs. Copy distinguishes current source/development capability from incomplete family/release readiness.
- Updated the three-concept chooser, preview/contact sheet and mock README. Chromium review at 1440×900, 390×844 and 320×700 exercised the gallery, modal, device/layer/Parent/idea switches, real Lilli audio, FAQ and normal/reduced-motion intro; no page errors, broken loaded images or horizontal overflow were found. Evidence is **DESIGN SPEC / DESKTOP VISUAL REVIEW** for the local website mock only. Encyclopedia, Greia OS runtime and release gates are unchanged.

- Repository `make verify` was attempted on macOS: 3,646 tests ran, with 3 errors and 1 failure confined to `test_x8_qemu.test_session04_legs` because its Linux-only product host gate refused this Darwin host. Focused module rerun reproduced that boundary. Do not read this as an OS verification PASS; local website browser evidence is separate.

## 2026-09-23 — First website direction promoted to official site work in progress

- Owner promoted the first website direction from mock to the official site work in progress. `website/` now owns the standalone homepage, Downloads page and individual Activity Library. The former `storybook.html` entry point redirects to it; the previous mock remains preserved as `storybook-historical.html`, and the other two experiments remain historical alternatives.
- Retained the original 52 rendered boot frames and widened Greia night landscape. Added a bounded, continuously animated firefly swarm with gentle nearby pointer attraction, reduced-motion support and off-screen/hidden-tab pause. Re-spaced display type and repositioned the full hero logo to clear the headline on desktop.
- Replaced mixed-language/historical gallery selection with ten English real-service Simulator captures of the Shell and source Activities; only the explicit language-comparison section uses an Italian capture. Replaced the unreadable Parent montage zoom with one 1024×600 English client viewport. Six accepted prerecorded cast introductions remain directly playable.
- Rewrote the site around the whole Linux OS, broad old/new x86 and Pi 400/500 hardware mission, four-layer architecture, networked Parent control without a general child browser, agent-oriented Activity authoring and prerecorded voice production, open-source aims, and low-cost educational possibilities. Claims distinguish development capability from unclosed family/release gates.
- Downloads and per-Activity package buttons are present but disabled until exact reviewed installer or `.greiaactivity` files exist. The source repository and Activity authoring skill are linked; public visibility and release readiness remain separate gates. No Greia OS, physical-device, production deployment, Activity release or Encyclopedia acceptance is claimed by this website work.
- Local Chromium review exercised intro/replay/skip, firefly movement, gallery/filter/lightbox, hardware/Parent/idea switches, voice loading, library search/filter/details and inactive release buttons across desktop and mobile sizes. Evidence scope: **DESIGN SPEC / DESKTOP VISUAL REVIEW** of website source plus **SIMULATOR VISUAL REVIEW** for the newly selected English development captures only.
- Repository `make verify` attempted 3,646 tests on macOS and failed at the known Linux-only Session 04 product-host boundary (3 errors, 1 failure) plus one transient root boot-health timeout in the broad run; the exact timeout test passed in a focused rerun after bytecode cleanup. Browser/source visual checks passed separately. This is not a full `make verify` PASS or a change to platform release acceptance.

## 2026-09-24 — Official website opening corrected against original boot artwork

- Owner rejected the official site's guessed wide trees, mountains, houses and colors. Inspected the 17 August boot patch and its Plymouth script: it centers/plays 52 small rendered frames but includes no editable SVG or scene generator. Located the original 1080×2922 rendered frames outside the repository and used its final frame directly for the large central G, Greia wordmark and forest.
- Replaced the official website's guessed SVG with a website-only panoramic extension made with the original high-resolution final frame as image reference. The extension follows the source's near-black navy palette, fine blue mountain outlines, intricate sharp pine silhouettes, small warm-window village, sparse stars and lilac foreground flowers. The original final frame overlays it; the 52 canonical small playback frames remain unchanged. Removed the obsolete official-site SVG and recorded exact asset provenance and hashes in `website/README.md`.
- Evidence is **DESIGN SPEC / DESKTOP VISUAL REVIEW** of the local website opening. The wide background is a generated derivative, not an original boot master or exact vector reconstruction. This does not change Greia OS boot assets, accepted brand masters, device acceptance, release readiness or the Encyclopedia/R7 route.


## 2026-10-08 — Offline semantic visual browser and candidate Time icon (SOURCE)

Added `tools/visual_library_gallery.py` and a `gallery` subcommand to
the canonical `tools/visual_authoring_library.py` CLI. Six authoritative
generic index files / 101 indexed resources remain unchanged. The developer
can view large source masters, text/category/status filters and source links
in one local self-contained HTML gallery. Asset traversal/duplicates are
rejected, output creation is exclusive, no external CDN/runtime SVG is
introduced. Source tests at `tests/test_visual_library_gallery.py` have not
yet been run or visually captured; **no artwork admission/quality decision**
is implied. Existing visual scene renderer, cast semantics and award art are
unchanged. An isolated Time icon SVG/WebP source candidate resides in
`activity_incubator/tempo_di_greia/assets/` and is not promoted to the
shared catalogue; its final child usability and stylistic review is owed.
The Encyclopedia visual workstream's acceptance/continuation route is not
superseded by this bounded library affordance.

## 2026-10-08 — Offline actual-art comparison, SOURCE only

Added `tools/visual_family_contact_sheet.py` and
`tests/test_visual_family_contact_sheet.py` (source anchor `0a09eaf4`).
The developer tool compares the existing 39 canonical core icons,
45 Activity icons and 30 cast-expression files at 128/64/48px in one
PNG. No source asset was regenerated or newly approved, and
Encyclopedia's E3 acceptance remains unchanged. GLA-008 in
`docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md` owns generation,
small-size evaluation and annotated visual findings when agent is free.


### 2026-10-08 — Child Home art and layout organization (P6 cross-workstream; SOURCE WIP)

The Creations+Activity P6 owner reviewed the **actual 32 draft**
first-party Activity manifest memberships and corrected four
inappropriate Create entries. The existing Greia Shell Home now
places trusted **My Creations immediately after Create**,
using `backpack` instead of duplicating Create's `palette`
icon, and adapts compact landscape column count to avoid a
six-rows-high Home. This uses existing shared art and
Collection-first/Parent-policy authorities, no new icon family,
catalogue migration or visual pipeline.

Visual direction/complete 32-candidate editorial matrix lives
under `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P6_CHILD_NAVIGATION_AND_VISUAL_CURATION.md`.
The source organization tests are newly committed but
**UNEXECUTED**, as are real Shell screenshots at 1024×600,
800×480 and 480×320. The canonical 114-item contact sheet
is still pending actual visual inspection. Two existing
IT/EN spoken Home label catalogues lack
`my_creations.wav`; the local-agent queue GLA-010
tracks approved voice content and actual listening
without adding runtime TTS. A distinct existing icon is
not visual acceptance until it has been seen next to the
other portals by the owner/child. No P6/P7 release gate
or full V5 shared-graphics completion was claimed.


### 2026-10-08 — Distinct child theme icons; no duplicate symbolism (P6 SOURCE-ONLY)

Source review of actual first-party draft Home/Play/Learn
navigation found collisions in the canonical semantic
discovery icon mapping: Music and Making reused Drawing's
palette; Words and Writing reused Stories' book; Building,
Numbers and Action reused Puzzles' identical graphic.
This made the existing optional subcollection vocabulary
visually indistinguishable to prereaders. Updated only
`src/greia_launcher/catalogue_view.py` icon lookup to use
13 distinct **already-registered** Greia core images
(palette, notebook, music star, train blocks, coins,
alphabet board, block puzzle, garden, book, rainbow,
heart, lightning, unicorn). No art generation or
runtime rendering/cache layers were introduced.

Both launcher card variants now show launch-status copy
in the child's active IT/EN language. Two misleading Play
memberships were dropped from authoring/observation
Activities; current 21 Play/22 Learn remain directly
browsed rather than forcing incomplete semantic groups.
A 32-candidate curation matrix lives in the existing
P6 design record. The local agent's GLA-008 art contact
sheet/simulator screenshots at 128/64/48px and 1024×600,
800×480, 480×320 still require execution and human
visual judgment. **No new test or render was run**, and
art, voice and release approval remain OPEN.


### 2026-10-08 — Locally rasterized existing SVG art is not app acceptance

A remote development environment can use Python,
Pillow and CairoSVG for actual authored Greia SVG.
`assets/visual/ui/v0.1/portal_frame.svg` and
`activity_card.svg` were retrieved as text via the
GitHub connector and successfully rasterized at
256/128/48px into a labeled comparison PNG.
This is a **genuine source-art sample**, not
a complete Pygame/child Shell render: it lacks
actual Activity icons, text composition, focus,
hit targets, performance and real profile state.
The remote environment has no full checked-out
private source and no Pygame, and cannot clone
the source because its network DNS is unavailable.
Do not use this asset PNG to close GLA-008.

Source change: a compact variant of the visible
My Creations Home caption (IT Creazioni,
EN Creations, with corresponding ES/DE/FR)
is now used at widths <=800px; the normal
caption and prerecorded semantic name are
unmodified. Tests were authored but NOT RUN.
Real Greia screenshots at 1024×600/800×480/
480×320 and child-facing visual approval remain
OPEN. No duplicate screenshot pipeline was created.

## 2026-10-15 — Art direction reset, SVG rules accepted, library audit, repository weight retired (DESIGN SPEC / SOURCE)

The full-library audit (`docs/reviews/visual/2026-10-15_asset_library_audit/REVIEW.md` (archived; see git history); SOURCE + DESKTOP VISUAL REVIEW only) found off-model cast art inside Activities, placeholder Activity icons, a glossy-3D core-icon outlier, three coexisting vector dialects and about 7.5 MiB of retire-able tracked weight. Main-agent decisions: `docs/design/GREIA_SVG_AUTHORING_RULES.md` is ACCEPTED as the binding recipe (tile hues per Collection accepted); Opus is the selected SVG authoring model (bake-off `icon_marble_run`, `leo_celebrate`, `scene_river_valley`); production waves are cast poses, P0 Activity icons, core icons. Housekeeping executed: retired `assets/source/generated_variants`, `assets/visual/authoring_kit`, `assets/visual/authoring_candidates`, the core-icon contact sheet (now git-ignored) and the superseded `pack_candidates/{forest_meadow,workshop}/2026-08-21` sets (131 files, 7,606,588 bytes); the cast-provenance pack candidates and legacy per-character `blink.svg` stay until the cast catalogue provenance is repointed. `compose_install_runtime_assets` now installs only the runtime asset subtree (no SVG masters or candidate packs). Earlier ledger entries are unchanged; this is not Simulator, VM or physical evidence.

## 2026-10-15 — Shared art library v1 registered, Shell redesign, control-kit art, core icons complete (SOURCE / DESKTOP VISUAL REVIEW)

Executed the production waves of the entry above. **Core icons:** all 29 core icons are flat SVG (globe, car, dinosaur, wizard, star_trophy, abc_blocks redrawn; 10 unreferenced glossy icons retired; catalogue 1.2.0), built SVG-only by `tools/build_core_icons.py` with a pixel-exact `--check`; Home portal icons are larger and cached. **Activity icons:** eight placeholder/misleading icons redrawn in the tile recipe. **Cast:** `pose_cheer`, `pose_point`, `pose_think` for all six characters, plus `sad`/`angry`/`silly`/`pose_wave`/`pose_play` variants. **Library v1 (catalogue 0.6.0, 297 visuals / 518 variants, byte-identical rebuild):** `bg.*` 61 layered 1024×600 scenes/wallpapers, `prop.*` (food, vocab, everyday, nature, blocks, shapes, instruments), `creature.*` (pets with need states, marine incl. orca, woodland), `icon.hud.*` (33), `fx.*` (17 multi-frame); one drawing per animal via builder alias support; guarded by `tests/test_shared_visual_library.py`. **Control-kit art** (HUD glyphs, stars, completion card, `ui/controls/v1`) accompanies ADR 0037. **Shell:** storybook Home/picker, Collection pages, Sea theme-folder icon, activity-card hue tiles (catalogue 0.5.0 and later). Installed runtime visuals are about 8.9 MB. Not yet consumed by Activities (P7 W2 does that). Evidence: SOURCE and headless DESKTOP VISUAL REVIEW only; no SIMULATOR/VM/PHYSICAL VISUAL REVIEW. Known weaknesses: the theme-folder tile needs a stronger folder silhouette. Earlier ledger entries are unchanged.

## 2026-10-16 — All 45 Activities on the library; Encyclopedia E4 complete (SOURCE / DESKTOP VISUAL REVIEW)

P7 W0–W3 is complete at source level (`docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P7_ACTIVITY_QUALITY_PROGRAM.md` §6a lists the Activity commits). Art consequences: Activities consume scenes, props, creatures, HUD icons, FX and canonical cast poses by semantic ID; off-model private cast redraws were removed (Torre cat, Quattro owl/shirtless Flash, Sillabe owl, Corsa squirrel, Teatrino puppets rebuilt from shared cast art, private Tito/Flash art in Labirinto, Stagioni, Bosco and Contrari). The shared library gained 62 vocabulary pictures (50 new nouns plus 12 promoted from Activity-private copies, catalogue 0.7.0, existing renditions byte-identical, `a779b10f`). The Encyclopedia E4 entry migration finished (`7b1f6b2c`): nature, space, body, machines and history scenes at 1024x600 with live moving parts, build groups `e4_*`, cairo declared the canonical backend and `--check` reproduces 43/43 PNGs (2.47 MiB). A pointer-event crash on the magnet page and a dinosaurs fallback draw crash were fixed. `set_alpha(None)` was found to disable per-pixel alpha on cached glow/ghost surfaces and replaced by `set_alpha(255)` (`11a61e59`).

Evidence class: SOURCE + DESKTOP VISUAL REVIEW (headless Pygame frames at 1024x600 / 800x480 / 480x320). Not SIMULATOR VISUAL REVIEW, not PHYSICAL VISUAL REVIEW; no audible review. Known art follow-ups (P7 §8): Activity-private art promotion/migration, left-facing `pose_point` variants, woodland creature hurt/happy states, tileable `bg.sky_clouds` layers, `prop.marble_run.*`/`prop.bridge.*` art pass, mosaic/plant/constellation sets, disk pass on runtime PNG sizes. Next: Encyclopedia E5; then the library promotion pass.


## 2026-10-16 — Living Home: baked clouds become drifting sprites (SOURCE / DESKTOP VISUAL REVIEW)

`assets/visual/environments/meadow_day/v0.1/home_landscape.svg` no longer bakes its three sky clouds (PNG re-rendered with `rsvg-convert` at 1024x600; `make visual-assets-check` PASS; catalogue unchanged). Collection Home draws `cloud.large.01` / `cloud.small.01` as slowly drifting sprites in the free left/right sky, and other Shell surfaces compose the same two clouds at rest into their cached backdrop (`SharedUiShellPanelMixin._compose_resting_sky_clouds`). Home also reuses `prop.food.apple`, `fx.dust_puff`, `fx.sparkle`, `ui.portal.collection_focus` (greeter keyboard focus) and the cast `surprised`/`happy`/`pose_wave`/`pose_cheer`/`sleepy`/`blink` variants; no new art. Scene-space positions live in `src/greia_launcher/home_scenery.py` and must follow the SVG if the landscape is redrawn. Evidence: headless 1024x600 frames only; not SIMULATOR or PHYSICAL VISUAL REVIEW.

## 2026-10-16 — Award frames redrawn; badge celebration and trophy shelf (SOURCE / DESKTOP VISUAL REVIEW)

The five glossy `feDropShadow` award masters in `assets/source/achievements/` were retired and replaced by eight flat masters under the SVG rules (Opus author): `award_bronze` (round copper medal, short blue ribbons), `award_silver` (scalloped silver-blue medal, longer ribbons), `award_gold` (cup trophy), `award_special` (purple rosette over a sunshine star burst) and a grey `_locked` silhouette with padlock for each. Palette steps derive from orange/sky/ocean/gold/grape/sunshine/navy tokens with ink `#4B372F`; ≤2-stop gradients; no baked shadow (the Shell grounds/hops/flies the sprite); 1.8–3.4 KB each; §9 lint clean. Registered as `ui.award.<family>` with 160/112/64 renditions and locked variants (`make visual-assets`, `make visual-assets-check` PASS; all other renditions byte-identical). The renderer composites the Activity emblem/Greia icon into the cream slot; procedural frames remain the fail-soft fallback. Reviewed at 256/64/48 px on cream and navy and as a 48 px greyscale sheet: the four tiers stay distinguishable by silhouette alone. Shell consumers: post-Activity celebration (card, sparkles/star bursts/confetti, greeter reaction, flight into the Home star) and the trophy-shelf Badge Library on the meadow. Evidence: headless 1024x600 and 800x480 frames only; not SIMULATOR or PHYSICAL VISUAL REVIEW; no audible review of the `celebrate.success`/`praise.general`/`encourage.progress` use.

## 2026-10-21 — @2x renditions for shared and Activity art (SOURCE / DESKTOP VISUAL REVIEW)

`tools/build_visual_renditions.py` renders an `@2x.png` sibling per declared variant from the same SVG masters (`rsvg-convert`; `--no-hires` skips), and the shared-library contract checks the exact 2x size (`47eafcd49`, 175 files for `alfabeto_leo` and `memory_meraviglie`; `f22db8cb3`, all shared and Activity-private art). The high-resolution layer loads them at >=1.2x; the 1x PNGs stay for the reference netbook. 13 Activity PNGs have no `@2x` because the shipped PNG no longer matches its SVG (redraw or re-render decision open). No SIMULATOR or PHYSICAL visual review.


## 2026-10-30 — Parent brand reuse (SOURCE / DESKTOP VISUAL REVIEW)

Parent HTML reuses the existing website Greia mark instead of an unrelated
constellation. Previewed locally; no installed-Acer visual acceptance. No
shared Activity artwork or visual workstream phase changed.
