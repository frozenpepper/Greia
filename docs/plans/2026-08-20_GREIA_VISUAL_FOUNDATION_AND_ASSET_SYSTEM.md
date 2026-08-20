# Greia Visual Foundation and Asset System — Active Art Workstream Plan

**Status:** ACTIVE ART/VISUAL WORKSTREAM  
**Date:** 2026-08-20  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Stable system/index guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Current visual resume:** `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`

This plan owns **sequencing, current checkpoint, milestone state and append-only progress history** for the Greia visual workstream. Stable architecture belongs in `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`; quick continuation state belongs in `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`.

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → explicit semantic runtime consumption → Shell/Activity reuse**

Broad source-art coverage already exists. **V5 shared consumption/integration remains the active phase.** The first real Shell consumer is now simulator-accepted; the workstream must generalize that seam toward Activities rather than resume pack proliferation.

---

# 1. Non-negotiable production rules

## Asset first
A scene or UI family starts with reusable source assets worth keeping individually. Weak primitives may not be hidden by a busy composition.

## Quality target
Aim for polished storybook / toy-diorama quality with attractive silhouettes, coherent warm palette, restrained gradients/detail, local highlights and soft depth, clean alpha edges, reusable shadows, low-resolution readability, and cheap/static fallback viability on Greia's low-resource floor.

Raw tutorial rectangles/circles/polygon scenery are prototype/debug art only.

## Layered environments
Keep sky/base, far background, mid background, playfield, interactive props, foreground, atmosphere/light/shadow/FX, character and protected-UI layers separate where reuse benefits.

## Subtle life
Cheap cloud drift, parallax, tiny foliage/reed sway, firefly/dust drift, fog, slow light breathing, water shimmer/ripples and contact-shadow response may enrich good static assets. Motion must never rescue weak art or carry essential meaning without a static fallback.

## Reuse before duplication
Reference an existing shared tree, bush, rock, log, block, pencil cup, firefly, shadow, distant hill or other generic asset instead of repainting near-duplicates for each environment.

## Stop expanding once coverage is good
Additional environment families now require a concrete reusable coverage gap. V5 integration takes priority over more pack proliferation.

## Runtime stays cheap and explicit
Target runtime must not scan visual source directories or rasterize SVG. Runtime consumes explicit pre-rendered PNG renditions through semantic IDs, bounded caches and accepted platform seams.

---

# 2. Character seed

Core cast remains **Lilli, Nino, Tito, Momo** in the accepted simplified Puff/Bean direction.

Base motion names remain:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Preserve character identity across states; `blink` must actually blink. Character refinement may continue without blocking V5.

---

# 3. Current reusable library

All current art packs are **candidate** unless their own records explicitly say otherwise.

| Pack | Source | Current desktop scope |
|---|---|---|
| Forest / Meadow v0.2 | `assets/visual/environments/forest_meadow/v0.2/` | 27 masters; layered/parallax proof; independent 1024×600 and 800×600 restraint references |
| Shared UI v0.1 | `assets/visual/ui/v0.1/` | shared panels/cards/buttons/tabs/badges/progress/bubbles/reward/focus/loading/error/empty/portal family + target references |
| Workshop v0.1 | `assets/visual/environments/workshop/v0.1/` | 19 masters + layered target references |
| Clinic / Care v0.1 | `assets/visual/environments/clinic/v0.1/` | 17 masters + reduced-size/target review |
| Reading / Classroom v0.1 | `assets/visual/environments/reading_classroom/v0.1/` | 17 masters; reuses Workshop generic assets |
| Fantasy / Village / Night v0.1 | `assets/visual/environments/fantasy_village_night/v0.1/` | 15 masters + corrected target references; reuses Forest assets |
| Water / Pond v0.1 | `assets/visual/environments/water_pond/v0.1/` | 14 water-specific masters + corrected target references; reuses Forest landscape/props |

Design/review inventories:

```text
assets/visual/library_v0.1.toml
assets/visual/packs_v0.1.toml
```

These inventories are not runtime discovery contracts.

---

# 4. V5 — Shared consumption/integration

V5 extends Greia's existing explicit asset architecture rather than creating a second framework.

Current source authority:

```text
src/greia_platform/assets.py
src/greia_platform/activity_assets.py
src/greia_platform/ui_core.py
src/greia_platform/pygame_visual_assets.py
src/greia_launcher/visual_assets.py
src/greia_launcher/main.py
src/greia_launcher/presentation.py
assets/catalog/core_icons_v1.toml
assets/catalog/shared_visuals_v1_source.toml
assets/catalog/shared_visuals_v1.toml
tools/build_visual_renditions.py
tools/validate_visual_renditions.py
Makefile: visual-assets / visual-assets-check
```

The full architecture/navigation explanation is in `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`.

## 4.1 Catalogue contract — implemented

`AssetCatalogue` preserves existing icon behavior and supports typed shared visuals:

- semantic visual ID;
- bounded visual kind;
- role;
- explicit named variants with required `default`;
- duplicate-ID rejection;
- file existence + asset-root path containment;
- no directory discovery.

Separate explicit manifests combine through `AssetCatalogue.merged(...)` only when they resolve under the same `assets/` root. Icon and visual IDs remain one global namespace.

## 4.2 Build-time runtime renditions — implemented and exercised

`assets/catalog/shared_visuals_v1_source.toml` explicitly selects the first reviewed UI masters/variants:

```text
ui.panel.base
ui.card.activity            default / focused / completed
ui.button.primary           default / hover / pressed / disabled
ui.shadow.soft              default
```

`tools/build_visual_renditions.py` performs build-host SVG→PNG conversion with librsvg/`rsvg-convert`, validates source/output containment and dimensions, writes each PNG transactionally, and writes the generated runtime catalogue atomically with the source SHA256.

The generated runtime output now exists on canonical `main`, including:

```text
assets/catalog/shared_visuals_v1.toml
assets/visual/runtime/v1/ui/soft_shadow.png
```

The target device does not require SVG rendering.

## 4.3 Generated-rendition validation — implemented

`tools/validate_visual_renditions.py` / `make visual-assets-check` validates generated output freshness/mapping/PNG dimensions without rasterizing.

This remains a source/build contract. Current runtime/visual acceptance for the first consumer was performed through the Activity Simulator under the owner-directed simulator runbook.

## 4.4 Bounded Pygame surface cache — implemented and consumed

`PygameVisualSurfaceCache` sits on the existing `ui_core.BoundedCache` and provides:

- semantic ID + explicit variant + requested size key;
- PNG-only runtime enforcement;
- lazy Pygame import;
- one-time scale on miss;
- default 12-entry LRU;
- default per-surface pixel ceiling 1024×600;
- explicit `clear()`;
- no per-frame file/decode after cache hit.

## 4.5 Launcher shared-visual bridge — implemented and wired

`src/greia_launcher/visual_assets.py` plus `LauncherApplication` now provide:

```text
mandatory core icons
+
optional generated shared visuals
=
one merged AssetCatalogue namespace
```

Missing/invalid generated visuals preserve the established launcher/static path.

The launcher owns one `PygameVisualSurfaceCache` and clears it on relevant display/viewport changes.

## 4.6 First controlled Shell consumer — COMPLETE AT SIMULATOR SCOPE

`ui.shadow.soft` is the first accepted shared Shell visual consumer beneath existing Activity tiles.

The integration preserves:

```text
Activity tile hit geometry
responsive grid geometry
label-band geometry
selection behavior
hover behavior
launch lifecycle
```

The primitive/static `draw_soft_shadow` path remains fallback.

Owner-directed simulator acceptance recorded in `LOCAL_AGENT_RESULT.md` covers:

- 1024×600 normal;
- 1024×600 large;
- 1280×800 normal;
- 1366×768 compact;
- 1920×1080 normal;
- 1111×700 normal;
- keyboard selection;
- pointer hover;
- Activity launch lifecycle;
- missing generated catalogue fallback;
- malformed generated catalogue fallback;
- corrupt/missing optional PNG fallback;
- 299 frames / 10.165 s = 29.41 FPS frame-rate sanity.

Evidence class: **SIMULATOR VISUAL REVIEW**.

No physical Acer/Pi performance claim and no R7 closure are made.

## 4.7 Next V5 gate — Activity semantic shared-visual contract

The next tranche must generalize the proven seam toward Activities rather than simply consume more decorative launcher assets.

Goal:

```text
Activity asks for semantic shared visual + explicit variant
→ platform resolves an allowed shared visual
→ renderer adapter returns renderer-appropriate realization
→ Activity does not discover arbitrary source paths or own a duplicate shared cache
```

Requirements:

- Python and future Web Activities converge on the same semantic IDs/variant names;
- Activity-private art remains supported;
- shared visual requests do not expose arbitrary host filesystem traversal or raw catalogue mutation;
- do not create a second asset catalogue/cache architecture;
- start with the smallest controlled request/resolution contract;
- simulator acceptance must exercise the real Activity path before claiming the gate complete.

Only after this Activity-facing seam exists should the workstream decide whether additional Shell-only consumption of `ui.panel.base`, `ui.card.activity`, or `ui.button.primary` adds enough value to justify another launcher tranche.

---

# 5. Current checkpoint

| Field | Current state |
|---|---|
| Stable visual-system/index guide | `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` |
| Cross-session resume | `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` |
| Active focus | **V5 shared consumption/integration — Activity-facing semantic seam next** |
| Environment coverage | V4 complete through Water/Pond; no new pack without a concrete gap |
| Catalogue | typed explicit visuals + safe cross-manifest merge implemented |
| Runtime rendition source | first bounded UI selection generated into explicit runtime PNG catalogue |
| Build tooling | transactional SVG→PNG tool + validator + Makefile targets implemented |
| Runtime cache | bounded PNG-only Pygame surface cache implemented and used by Launcher |
| Launcher integration | optional shared-visual merge/fallback bridge wired into `LauncherApplication` |
| First Shell consumer | `ui.shadow.soft` accepted at **SIMULATOR VISUAL REVIEW** scope |
| Simulator evidence | 6/6 responsive rows + interaction + 3 fail-soft cases + 29.41 FPS sanity |
| Physical evidence | not collected for this V5 consumer; no Acer/Pi performance claim |
| Next exact action | define and implement the smallest renderer-neutral Activity semantic shared-visual request/resolution seam; prove it through the Activity Simulator |

---

# 6. Milestones

## V1 — Character/style seed **[SUFFICIENT TO UNBLOCK LIBRARY]**
- [x] simplified character direction;
- [x] core cast seed;
- [ ] continue useful character refinement without blocking wider work.

## V2 — Forest/meadow composable environment **[DESKTOP CANDIDATE BUILT]**
- [x] 27-source-asset candidate pack;
- [x] light/shadow/atmosphere/FX;
- [x] metadata + layered/parallax proof;
- [x] target-size restraint pass;
- [ ] owner approval/revision when appropriate.

## V3 — Shared UI visual kit **[DESKTOP CANDIDATE BUILT]**
- [x] core components/states/illustration pieces;
- [x] common shadow/highlight treatment;
- [x] independent target-size references;
- [ ] owner approval/revision when appropriate.

## V4 — Additional environment packs **[DESKTOP CANDIDATE COVERAGE COMPLETE]**
- [x] Workshop;
- [x] Clinic;
- [x] Reading/classroom;
- [x] Fantasy/village/night;
- [x] Water/pond;
- [x] pack-level inventory and reuse dependencies;
- [ ] additional family only when a concrete reusable coverage gap is demonstrated.

## V5 — Shared consumption/integration **[ACTIVE]**
- [x] trace existing catalogue/tests and reuse existing architecture;
- [x] backwards-compatible typed visual-asset manifest extension;
- [x] explicit safe cross-manifest catalogue merge;
- [x] explicit build-time SVG→PNG rendition selection/tool;
- [x] transactional generated PNG/catalog writes;
- [x] generated-rendition validation tool;
- [x] bounded PNG-only Pygame surface cache;
- [x] explicit `make visual-assets` + `make visual-assets-check` targets;
- [x] optional launcher shared-visual merge/fallback bridge;
- [x] stable visual-system architecture/index + cross-session resume documentation;
- [x] generate first runtime PNG catalogue on owner/build checkout with librsvg;
- [x] first controlled Shell/UI consumption path: `ui.shadow.soft`;
- [x] simulator normal/fallback/interaction/responsive acceptance for first consumer;
- [ ] renderer-neutral Activity semantic shared-visual request/resolution contract;
- [ ] first Python Activity consumption through that semantic contract;
- [ ] future Web Activity equivalent semantic resolution path;
- [ ] physical low-resource acceptance where implementation claims require it.

---

# 7. Evidence vocabulary / review discipline

Use precise scopes:

```text
DESIGN SPEC
SOURCE
DESKTOP VISUAL REVIEW
SIMULATOR VISUAL REVIEW
PHYSICAL VISUAL REVIEW
REJECTED EXPERIMENT
```

Committed tests are not PASS merely because they exist. Candidate art in Git is not approved. Generated runtime output is not evidence until built and exercised by the relevant consumer.

---

# 8. Failure patterns — do not repeat

- spending the workstream on character minutiae;
- detailed traditional rigs as default;
- one-shot sprite sheets assumed production-ready;
- degrading accepted character art with overlays/redraws;
- non-blinking `blink`;
- crude primitive scenery presented as redesign;
- full-screen mockups before real assets exist;
- decorative HTML hiding weak art;
- inventing a second runtime/UI asset architecture when accepted platform seams exist;
- runtime SVG rendering on low-end targets;
- arbitrary visual-directory scanning;
- unbounded image caches or per-frame decode;
- replacing asset-first production with generated scene concept images;
- repainting duplicate generic assets instead of reusing the shared library;
- continuing to create environment packs after reusable coverage is broad without a concrete need;
- wiring a visual that changes launcher geometry before the existing layout can safely accommodate it;
- treating generated build products as valid when stale/corrupt/unverified;
- continuing to add launcher-only decorative consumers instead of completing the V5 Activity reuse seam.

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
- Reading pack landed on `main` at `6b94d6ddd8cdbecea171f40a1e47c1ac49f3aec9` after preserving concurrent repository changes.

## 2026-08-20 — Fantasy/Village/Night v0.1
- Built a bounded 15-master night/fantasy village pack.
- Reused Forest greenery/fireflies semantically instead of creating unnecessary night duplicates.
- First desktop asset review rejected/revised weak cottages, tower, lantern, well and cobblestone treatments.
- Layered target references were corrected for cobblestone scale and excessive moonlight dominance.
- Source + composition/review metadata committed in `0958f8a0ca1b583798a245464b9e3e87a74d883c`.

## 2026-08-20 — Water/Pond v0.1 + inventory consolidation
- Built and desktop-reviewed 14 water-specific reusable masters.
- Revised dock/lily pads during individual review; then strengthened water base, lily-pad geometry and reeds before target composition review.
- Built independent 1024×600 / 800×600 references using canonical Forest distant landscape by source reference.
- Catalog reuse IDs were aligned with the actual Forest/Meadow catalog.
- Added `assets/visual/packs_v0.1.toml` and refreshed `library_v0.1.toml` so the design inventory reflects the environment/UI library that now exists.
- Local validation: Water/Pond TOML parse PASS and all Water/Pond SVG XML sources parse PASS.
- Evidence remains **SOURCE + DESKTOP VISUAL REVIEW** only; no runtime/simulator/hardware acceptance claimed.

## 2026-08-20 — V5 explicit catalogue/rendition/cache seed
- Extended the existing `AssetCatalogue` contract with typed explicit visual variants while preserving icon behavior, path containment and one semantic ID namespace.
- Added provider-free catalogue tests for variants, duplicate IDs, missing paths, path escapes, unsupported kinds and old icon compatibility.
- Added `assets/catalog/shared_visuals_v1_source.toml` as the first explicit reviewed UI rendition selection.
- Added `tools/build_visual_renditions.py`; runtime PNGs are build-host products and SVG rasterization is forbidden on the target.
- Added `PygameVisualSurfaceCache` using existing `ui_core.BoundedCache`, a 12-entry default LRU and a 1024×600 per-surface pixel ceiling.
- Added provider-free cache tests; isolated local harness passed 9/9.
- Added `make visual-assets`.
- `rsvg-convert` was absent in that execution environment, so generated PNG/catalog output and full repository tests remained unverified there.

## 2026-08-20 — V5 integration hardening and first-consumer preparation
- Rendition writes were made transactional: validate temporary PNG first, atomically replace final output, and atomically replace generated catalogue; isolated builder harness previously passed 3/3.
- Added provider-free tests for transactional generation.
- Added explicit cross-manifest `AssetCatalogue.merged(...)` with same-root and global-ID enforcement plus merge tests.
- Added `ui.shadow.soft` to the first runtime rendition source as the safest controlled Shell enhancement candidate.
- Added `LauncherAssetSet` / `load_launcher_assets(...)` so mandatory core icons can merge optional generated visuals while invalid/missing visual output falls back to current static behavior.
- Added `validate_visual_renditions.py` + `make visual-assets-check` to reject stale/mismatched/corrupt generated output before integration/image use.
- Added focused validator and launcher-fallback tests.
- New merge/validator/launcher test files were SOURCE only at this checkpoint; no false PASS claim was made.

## 2026-08-20 — visual-system documentation consolidated
- Added `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` as the stable human/agent visual-system architecture and index.
- Added `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` as the short cross-session visual continuation contract.
- Updated `AGENTS.md` and `docs/DOCUMENTATION.md` so visual work starts from the new system guide, then the active plan/resume and narrower authorities.
- Updated the visual-authoring skill to remove stale “first pack” guidance and focus current work on V5 integration.
- Owner-directed first-consumer V5 acceptance remained Activity-Simulator based through `docs/testing/2026-08-20_V5_VISUAL_INTEGRATION_SIMULATOR_LOCAL_AGENT.md`.

## 2026-08-20 — V5 first Shell consumer (`ui.shadow.soft`) wired and simulator-verified
- Built explicit runtime visual renditions via `make visual-assets` using `rsvg-convert`.
- Integrated `load_launcher_assets(...)` into `LauncherApplication.__init__` and `LauncherPaths` to merge mandatory core icons with optional generated shared visuals.
- Wired `PygameVisualSurfaceCache` into `LauncherApplication` and `GreiaLauncherPresentation`.
- Integrated `ui.shadow.soft` underneath Activity tiles in `GreiaLauncherPresentation._draw_activity_tile_content`, positioned softly under the card base with motion lift support and fail-soft fallback to `draw_soft_shadow`.
- Wrapped `tomllib.TOMLDecodeError` in `AssetCatalogueError` in `AssetCatalogue.load` for resilient catalogue error containment.
- Fixed RGB pixel format capture in `SimulatorRemoteBridge.capture_frame`.
- Tested and accepted across the full simulator matrix (1024×600 normal & large, 1280×800 normal, 1366×768 compact, 1920×1080 normal, 1111×700 normal).
- Tested keyboard selection, hover motion, and launch lifecycle in simulator.
- Tested all fail-soft fallback cases in simulator (missing catalogue, invalid catalogue, missing/corrupt PNG).
- Frame rate sanity check verified 29.4 fps over 10.1s (~30 fps clock tick, no observed stalls).
- Evidence recorded under `./tmp/v5-simulator-evidence/`. Evidence class: **SIMULATOR VISUAL REVIEW**. No physical hardware or R7 closure claimed.

## 2026-08-20 — V5 state reconciled after canonical merge
- Reconciled the plan with the implementation/evidence already present on canonical `main`; removed stale statements that the launcher bridge or first Shell consumer were still unwired.
- Marked `ui.shadow.soft` first-consumer gate complete at **SIMULATOR VISUAL REVIEW** scope.
- Changed the next V5 target from “another launcher visual candidate” to the renderer-neutral Activity semantic shared-visual seam required for real Shell/Activity reuse.
- Updated the cross-session resume to match this exact continuation point.

Next exact action: **design and implement the smallest renderer-neutral Activity semantic shared-visual request/resolution contract on top of the existing AssetCatalogue/runtime adapters, then prove the first Activity-facing consumption path through the Greia Activity Simulator.**
