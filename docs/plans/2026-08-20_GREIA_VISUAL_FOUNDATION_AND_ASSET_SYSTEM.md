# Greia Visual Foundation and Asset System — Active Art Workstream Plan

**Status:** ACTIVE ART/VISUAL WORKSTREAM  
**Date:** 2026-08-20  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`

This plan owns the current Greia visual-library workstream.

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → one explicit shared consumption seam → Shell/Activity reuse**

The broad source-art library now exists. **V5 shared consumption/integration is the active phase.** Do not create more environment families merely to keep producing art.

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

These inventories are **not** runtime filesystem-discovery contracts.

---

# 4. V5 — Shared consumption/integration

V5 extends Greia's existing explicit asset architecture rather than creating a second framework.

Existing/implemented source authority:

```text
src/greia_platform/assets.py
src/greia_platform/activity_assets.py
src/greia_platform/ui_core.py
src/greia_platform/pygame_visual_assets.py
assets/catalog/core_icons_v1.toml
assets/catalog/shared_visuals_v1_source.toml
tools/build_visual_renditions.py
Makefile: visual-assets
tests/test_asset_catalogue.py
tests/test_pygame_visual_assets.py
```

## 4.1 Catalogue contract — implemented source

`AssetCatalogue` now retains its existing icon behavior and also supports explicit typed shared visuals:

- semantic visual ID;
- bounded visual kind;
- role;
- explicit named variants with required `default`;
- one namespace across icons/visuals;
- duplicate-ID rejection;
- file existence + asset-root path containment;
- no directory discovery.

This is lookup only. Decode/cache policy remains separate.

## 4.2 Build-time rendition contract — implemented source

`assets/catalog/shared_visuals_v1_source.toml` explicitly selects the first reviewed UI masters/variants for runtime rendition.

`tools/build_visual_renditions.py`:

- accepts only explicit SVG sources under the assets root;
- invokes build-host `rsvg-convert`/librsvg;
- writes explicit PNG rendition paths;
- validates path containment, kind/variant names, dimensions, duplicate outputs and generated PNG IHDR dimensions;
- writes `assets/catalog/shared_visuals_v1.toml` with a source SHA256;
- never requires SVG rendering on the target device.

`make visual-assets` is now the explicit build entrypoint.

**Current boundary:** this environment does not have `rsvg-convert`, so generated PNG renditions and `assets/catalog/shared_visuals_v1.toml` have not been produced/validated here. Do not claim them as runtime evidence yet.

## 4.3 Bounded Pygame surface cache — implemented source

`src/greia_platform/pygame_visual_assets.py` adds `PygameVisualSurfaceCache` on top of existing `ui_core.BoundedCache`:

- semantic ID + explicit variant + requested size key;
- PNG-only runtime enforcement;
- no SVG runtime path;
- lazy Pygame import;
- no display-dependent `convert()`/`convert_alpha()` in the loader;
- one-time scaling on cache miss;
- default **12-entry** LRU bound;
- default per-surface pixel ceiling of **1024×600**;
- no per-frame file/decode work after a cache hit;
- explicit `clear()`.

Provider-free tests cover hits, scaling keys, variants, LRU eviction/reload, clear/reload, invalid dimensions, pixel ceiling, SVG rejection and unknown catalogue entries/variants.

An isolated local provider-free harness using the exact new cache source passed **9/9** tests. This is not a repository-wide `make test` or `make verify` claim.

## 4.4 V5 gate still open

V5 is **not complete** until all of the following occur:

1. generate the first runtime PNG renditions on an owner-controlled/build checkout with librsvg available;
2. inspect/validate the generated runtime catalogue + PNGs;
3. run focused repository tests for `AssetCatalogue`, rendition tooling and `PygameVisualSurfaceCache`;
4. integrate **one existing controlled Shell/UI path first** through the generated catalogue/cache;
5. verify no per-frame decode/discovery and retain static/fail-closed fallback;
6. only then expand the same semantic contract toward Activities/Web;
7. collect simulator/physical low-resource evidence before stronger runtime/physical claims.

Until step 4 succeeds, source packs remain `runtime_consumed = false`.

---

# 5. Current checkpoint

| Field | Current state |
|---|---|
| Active focus | **V5 shared consumption/integration** |
| Environment coverage | V4 complete through Water/Pond; no new pack without a concrete gap |
| Catalogue | typed explicit visual variants added without breaking icon contract |
| Runtime rendition source | first bounded UI selection in `shared_visuals_v1_source.toml` |
| Build tooling | explicit SVG→PNG build tool + `make visual-assets` target |
| Runtime cache | bounded PNG-only Pygame surface cache implemented |
| Test evidence | new provider-free cache harness **9/9 PASS** in isolation; full repo tests not run here |
| Generated PNG/catalog evidence | **NOT YET GENERATED in this environment**; `rsvg-convert` unavailable here |
| Actual Shell/Activity consumption | **not yet wired** |
| Evidence boundary | art: SOURCE + DESKTOP VISUAL REVIEW; V5: SOURCE + isolated provider-free test only |
| Next exact action | on an owner-controlled checkout with librsvg: run `make visual-assets`, validate generated PNG/catalog outputs and focused tests, then wire one existing Shell/UI component path through `AssetCatalogue` + `PygameVisualSurfaceCache` before any broader Activity integration |

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
- [x] explicit build-time SVG→PNG rendition selection/tool;
- [x] bounded PNG-only Pygame surface cache;
- [x] provider-free cache test source;
- [x] explicit `make visual-assets` build target;
- [ ] generate/validate first runtime PNG catalogue on a build host with librsvg;
- [ ] focused repository test run on current source;
- [ ] first controlled Shell/UI consumption path;
- [ ] shared Python/Web Activity semantic contract;
- [ ] simulator/physical low-resource acceptance where implementation claims require it.

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

Committed tests are not PASS merely because they exist. Candidate art in Git is not approved. Generated runtime output is not evidence until actually built and checked.

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
- continuing to create environment packs after reusable coverage is already broad without a concrete need.

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
- `rsvg-convert` is absent in the current execution environment, so generated PNG/catalog output and full repository tests remain unverified here.

Next exact action: generate and validate the first runtime renditions on an owner-controlled/build checkout with librsvg, run focused current-source tests, then integrate one existing Shell/UI path through the explicit catalogue/cache before expanding the contract.
