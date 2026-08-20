# Greia Visual Foundation and Asset System — Active Art Workstream Plan

**Status:** ACTIVE ART/VISUAL WORKSTREAM  
**Date:** 2026-08-20  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Stable system/index guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Current visual resume:** `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`

This plan owns **sequencing, current checkpoint, milestone state and append-only progress history** for the Greia visual workstream. Stable architecture belongs in `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`; quick continuation state belongs in `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`.

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → explicit semantic runtime consumption → Shell/Activity reuse**

Broad source-art coverage already exists. **V5 shared consumption/integration remains the active phase.** `ui.shadow.soft`, `ui.card.activity`, and `ui.panel.base` are accepted in the real child Shell at Activity Simulator scope. The next visible shared UI consumer, `ui.button.primary`, is now wired into root Activity-category controls in source and awaits simulator acceptance. The workstream remains focused on real product-visible integration, not more art-pack production.

---

# 1. Non-negotiable production rules

- **Asset first:** reusable individual masters before compositions.
- **Quality:** polished storybook/toy-diorama silhouettes, warm light, soft depth, clean alpha, low-resolution readability.
- **Layered scenes:** base/far/mid/playfield/props/foreground/atmosphere/light/character/UI remain separable where reuse benefits.
- **Subtle life:** cheap parallax, tiny sway, fog, shimmer, light breathing; static fallback remains complete.
- **Reuse before duplication:** use shared generic assets instead of repainting them for each environment.
- **Stop pack proliferation:** a new environment family requires a concrete reusable coverage gap.
- **Cheap explicit runtime:** no runtime SVG rasterization, source-directory scanning, per-frame file decode/scale, or unbounded image caches.
- **Visible integration matters:** plumbing gates must lead to actual Greia presentation improvements; do not spend the workstream indefinitely on invisible proof consumers.

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

| Pack | Source | Current desktop scope |
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

Most pack art remains **candidate SOURCE + DESKTOP VISUAL REVIEW** unless a narrower record states otherwise.

---

# 4. V5 — Shared consumption/integration

Current source authority:

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
src/greia_launcher/child_shell.py
activities/shape_garden/main.py
assets/catalog/core_icons_v1.toml
assets/catalog/shared_visuals_v1_source.toml
assets/catalog/shared_visuals_v1.toml
tools/build_visual_renditions.py
tools/validate_visual_renditions.py
```

The architecture/index for these pieces is `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`.

## 4.1 Explicit catalogue + variants — implemented

`AssetCatalogue` supports semantic shared visuals with kind, role and explicit variants while preserving existing icons. IDs remain globally unique; paths remain contained under the assets root; arbitrary discovery is forbidden.

## 4.2 Build-time SVG→PNG rendition pipeline — implemented and exercised

The explicit source manifest currently promotes:

```text
ui.panel.base
ui.card.activity            default / focused / completed
ui.button.primary           default / hover / pressed / disabled
ui.shadow.soft              default
```

`tools/build_visual_renditions.py` renders through build-host librsvg/`rsvg-convert`, validates dimensions/containment and writes PNG/catalog output transactionally.

Generated runtime output is committed on canonical `main`, including `assets/catalog/shared_visuals_v1.toml` and `assets/visual/runtime/v1/ui/soft_shadow.png`.

## 4.3 Generated-output validation — implemented

`tools/validate_visual_renditions.py` / `make visual-assets-check` checks source hash, mapping parity, explicit runtime paths, PNG signatures and dimensions.

## 4.4 Bounded Pygame cache — implemented and consumed

`PygameVisualSurfaceCache` provides semantic ID + variant + requested-size caching on existing `ui_core.BoundedCache`, with a default 12-entry LRU, a 1024×600 per-surface ceiling, PNG-only runtime enforcement and explicit clear.

## 4.5 Launcher seam — COMPLETE AT SIMULATOR SCOPE

`ui.shadow.soft` is the first accepted shared Shell consumer beneath existing Activity tiles.

Accepted Activity Simulator evidence from `LOCAL_AGENT_RESULT.md`:

```text
6/6 responsive viewport/interface rows PASS
keyboard selection PASS
pointer hover PASS
Activity launch lifecycle PASS
missing generated catalogue fallback PASS
malformed generated catalogue fallback PASS
corrupt/missing PNG fallback PASS
299 frames / 10.165 s = 29.41 FPS sanity
```

Evidence class: **SIMULATOR VISUAL REVIEW**.

No physical Acer/Pi performance claim and no R7 closure.

## 4.6 Activity semantic resolver — SOURCE IMPLEMENTED

The first Activity-facing semantic contract is now in `src/greia_platform/activity_api.py`:

```python
get_shared_visual(asset_id, variant="default")
get_shared_visual_path(asset_id, variant="default")
```

`get_shared_visual(...)` returns a read-only `SharedVisualReference` containing semantic ID, kind, role, requested variant and the current Python runtime path realization.

Invariants:

- Activity supplies semantic ID + variant, not a host path;
- no raw catalogue mutation is exposed;
- optional generated visual catalogue failure leaves core icons/API available;
- unknown shared visuals fail narrowly;
- Activity-private art remains supported;
- the Python `Path` realization does **not** define the future Web transport.

## 4.7 First Python Activity consumer — SOURCE IMPLEMENTED, SIMULATOR PENDING

`activities/shape_garden/main.py` is the first Activity source consumer.

It resolves `ui.shadow.soft` once at startup, scales it once to a bounded reference size, and reuses that prepared Pygame surface while drawing shapes. If the optional shared visual cannot be resolved/decoded, Shape Garden remains playable without the shadow.

No per-frame asset path resolution, file decode or smoothscale was added.

This gate remains **SOURCE only** until the Activity Simulator protocol passes:

```text
docs/testing/2026-08-20_V5_ACTIVITY_SHARED_VISUAL_SIMULATOR.md
```

This proof is no longer blocking visible Shell work.

## 4.8 First substantial visible shared UI consumer — ACCEPTED (SIMULATOR VISUAL REVIEW)

The production child Shell consumes the reviewed `ui.card.activity` artwork through:

```text
src/greia_launcher/shared_ui_presentation.py
src/greia_launcher/child_shell.py
```

Behavior:

- neutral Activity tiles request `ui.card.activity/default`;
- selected / hovered / launching tiles request `ui.card.activity/focused`;
- the authored 360:430 portrait ratio is preserved inside the existing logical launcher hit target instead of stretching the artwork into a square;
- Activity icon and localized title are placed into the card's authored illustration well and lower label band;
- the existing primitive launcher tile remains the fail-soft fallback when the optional shared card catalogue/PNG/cache path fails;
- no Activity selection, hit target, catalogue, lifecycle or runtime authority is replaced by this mixin.

Accepted via:

```text
docs/testing/2026-08-20_V5_SHARED_UI_CARD_SIMULATOR.md
```

All 6 responsive matrix rows, keyboard navigation, hover, return Home lifecycle, fail-soft fallbacks and 27.2 FPS frame sanity passed.

## 4.9 Second visible shared UI consumer — ACCEPTED (SIMULATOR VISUAL REVIEW)

The production child Shell consumes `ui.panel.base/default` through:

```text
src/greia_launcher/shared_ui_presentation.py
src/greia_launcher/child_shell.py
```

Behavior:

- the panel frames both profile picker and Activity catalogue;
- authored 640:420 aspect ratio is preserved across all viewports;
- rainbow header, category bar, avatar and Activity cards remain on top and unclipped;
- cached Activity tiles use alpha surfaces so the panel is not obscured by rectangular background cutouts;
- fail-soft isolation disables only panel framing on panel-specific failure without affecting independent card artwork.

Accepted via:

```text
docs/testing/2026-08-20_V5_SHARED_UI_PANEL_SIMULATOR.md
```

All 6 responsive matrix viewports, profile picker, Activity catalogue, return Home lifecycle, missing/malformed/corrupt fallback cases and 29.5 FPS frame sanity passed.

## 4.10 Third visible shared UI consumer — ACCEPTED (SIMULATOR VISUAL REVIEW)

The root Activity-category row now consumes:

```text
ui.button.primary/default
ui.button.primary/hover
```

through `SharedUiCategoryButtonMixin` in `src/greia_launcher/shared_ui_presentation.py`.

Behavior:

- existing category IDs, ordering and hit rectangles are preserved;
- default and hover visual states come from the generated shared button catalogue;
- category icons and localized labels remain overlaid by existing launcher typography/icon authorities;
- the in-category Back/header control deliberately stays on its existing renderer because its geometry does not match the wide reviewed primary-button asset;
- a button-specific failure disables only the shared category-button treatment and falls back to the proven primitive category renderer while accepted shared panels/cards remain live.

Accepted via:

```text
docs/testing/2026-08-20_V5_SHARED_UI_CATEGORY_BUTTON_SIMULATOR.md
```

All 6 responsive matrix viewports, baseline buttons, button hover, category open/return navigation, launch/return Home lifecycle, missing/malformed/corrupt-button fallback cases, and 29.6 FPS frame sanity passed with full evidence in `tmp/v5-button-simulator-evidence/`.

## 4.11 Fourth visible shared UI consumer — ACCEPTED (SIMULATOR VISUAL REVIEW)

The production child Shell consumes:

```text
ui.avatar.frame/default
```

through `SharedUiProfileChromeMixin` in `src/greia_launcher/profile_chrome_presentation.py`.

Behavior:

- profile picker cards overlay the reviewed storybook circular frame over the avatar area with centered icons and clean card backgrounds;
- the active-profile switcher at the top-left of the Activity catalogue cleanly displays the circular frame badge without underlying square raised panel corners peeking;
- the main Activity background panel (`ui.panel.base`) maximizes available vertical screen height (starting right under the category row at `panel_top=52..62` down to `bottom_margin=4`) while maintaining authentic 640:420 aspect ratio;
- activity cards retain their full prominent large scale (~198-205px) comfortably centered within the inner panel tray;
- non-intrusive headless simulator execution (`--headless` / `GREIA_SIMULATOR_HEADLESS=1`) operates silently via SDL dummy drivers without stealing window focus;
- fail-soft isolation cleanly falls back to primitive profile treatment if the avatar frame fails while accepted panel, cards, and buttons remain live.

Accepted via:

```text
docs/testing/2026-08-21_V5_SHARED_PROFILE_IDENTITY_SIMULATOR.md
```

All 6 responsive matrix viewports, profile picker baseline, active profile switcher, return to profile picker, missing/malformed/corrupt fallback cases, and 27.4 FPS frame sanity passed with evidence in `tmp/v5-profile-simulator-evidence/`.

## 4.12 After the profile-identity gate

Following simulator acceptance of `ui.shadow.soft`, `ui.card.activity`, `ui.panel.base`, `ui.button.primary`, and `ui.avatar.frame`:

1. record `ui.avatar.frame` as an accepted visible Shell consumer at **SIMULATOR VISUAL REVIEW** scope;
2. continue only to another product-visible shared UI surface that materially improves Greia, rather than adding proof-only consumers;
3. separately complete the Web Activity semantic adapter using the same semantic IDs/variants through a controlled URL/handle transport, not host filesystem exposure;
4. do not return to new environment-pack production without a demonstrated reusable coverage gap.

---

# 5. Current checkpoint

| Field | Current state |
|---|---|
| Stable guide | `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` |
| Resume | `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` |
| Active focus | **V5 — shared `ui.avatar.frame` profile identity accepted in Activity Simulator** |
| Environment coverage | V4 complete through Water/Pond; no new pack without concrete gap |
| Catalogue/renditions | explicit semantic catalogue + generated PNG runtime catalogue present |
| First Shell consumer | `ui.shadow.soft` accepted at **SIMULATOR VISUAL REVIEW** scope |
| Visible Shell card consumer | `ui.card.activity/default|focused` accepted at **SIMULATOR VISUAL REVIEW** scope |
| Visible Shell panel consumer | `ui.panel.base/default` accepted at **SIMULATOR VISUAL REVIEW** scope |
| Visible category-button consumer | `ui.button.primary/default|hover` accepted at **SIMULATOR VISUAL REVIEW** scope |
| Visible profile-identity consumer | `ui.avatar.frame/default` accepted at **SIMULATOR VISUAL REVIEW** scope |
| Activity API | `get_shared_visual(...)` + `get_shared_visual_path(...)` implemented in source |
| First Activity consumer | Shape Garden consumes `ui.shadow.soft` in source with optional fallback; non-blocking simulator proof pending |
| Completed visible protocols | `docs/testing/2026-08-20_V5_SHARED_UI_CARD_SIMULATOR.md`; `docs/testing/2026-08-20_V5_SHARED_UI_PANEL_SIMULATOR.md`; `docs/testing/2026-08-20_V5_SHARED_UI_CATEGORY_BUTTON_SIMULATOR.md`; `docs/testing/2026-08-21_V5_SHARED_PROFILE_IDENTITY_SIMULATOR.md` |
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
- [x] first Shell consumer `ui.shadow.soft`;
- [x] Shell simulator normal/fallback/interaction/responsive acceptance;
- [x] renderer-neutral semantic request portion of Activity API (`get_shared_visual`);
- [x] first Python Activity source consumer (Shape Garden);
- [ ] Shape Garden Activity Simulator acceptance (non-blocking visible-Shell work);
- [x] shared Activity card source consumer;
- [x] shared Activity card simulator acceptance;
- [x] shared Shell panel source consumer;
- [x] shared Shell panel simulator acceptance;
- [x] shared root category-button source consumer (`ui.button.primary/default|hover`);
- [x] shared category-button simulator acceptance;
- [x] shared profile-identity source consumer (`ui.avatar.frame/default`);
- [x] shared profile-identity simulator acceptance;
- [ ] future Web Activity semantic adapter/transport;
- [ ] further visible Shell integration using existing shared UI families where materially useful;
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

Committed source is not PASS by itself. Generated runtime output is not consumer evidence until the relevant consumer is exercised.

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
- spending the visual workstream indefinitely on invisible plumbing once the seam is already proven.

---

# 9. Progress log — append only

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
- Removed stale plan/resume language saying the first Shell consumer was still unwired.
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
- Synthetic pointer tracking was corrected for headless/simulator MOUSEMOTION.
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
- Preserved existing category ordering, hit targets and navigation; in-category Back/header remains on the existing geometry-specific renderer.
- Added isolated fail-soft behavior so button-specific corruption falls back only the category row while accepted panel/card shared visuals remain active.
- Added `docs/testing/2026-08-20_V5_SHARED_UI_CATEGORY_BUTTON_SIMULATOR.md`.
- Evidence remains **SOURCE** until the simulator protocol passes.

Next exact action: **execute `docs/testing/2026-08-20_V5_SHARED_UI_CATEGORY_BUTTON_SIMULATOR.md`; inspect actual button quality, hover, category open/back lifecycle, isolated fallback, responsive matrix and frame sanity; fix only root causes and then record exact simulator evidence.**
