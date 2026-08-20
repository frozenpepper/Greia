# Greia Visual Foundation and Asset System — Active Art Workstream Plan

**Status:** ACTIVE ART/VISUAL WORKSTREAM  
**Date:** 2026-08-20  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Stable system/index guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Current visual resume:** `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`

This plan owns the current Greia visual-library workstream **sequencing, checkpoint and append-only progress history**. The stable architecture/index belongs in `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`; the short cross-session continuation contract belongs in `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`.

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

Current source authority:

```text
src/greia_platform/assets.py
src/greia_platform/activity_assets.py
src/greia_platform/ui_core.py
src/greia_platform/pygame_visual_assets.py
src/greia_launcher/visual_assets.py
assets/catalog/core_icons_v1.toml
assets/catalog/shared_visuals_v1_source.toml
tools/build_visual_renditions.py
tools/validate_visual_renditions.py
Makefile: visual-assets / visual-assets-check
tests/test_asset_catalogue.py
tests/test_asset_catalogue_merge.py
tests/test_pygame_visual_assets.py
tests/test_build_visual_renditions.py
tests/test_validate_visual_renditions.py
tests/test_launcher_visual_assets.py
```

The complete architecture/navigation explanation for these files is in `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`.

## 4.1 Catalogue contract — source implemented

`AssetCatalogue` retains existing icon behavior and supports typed shared visuals:

- semantic visual ID;
- bounded visual kind;
- role;
- explicit named variants with required `default`;
- duplicate-ID rejection;
- file existence + asset-root path containment;
- no directory discovery.

Separate explicit manifests can now be combined with `AssetCatalogue.merged(...)` only when they resolve under the same `assets/` root. Icon and visual IDs remain one global namespace after merge; cross-catalogue collisions fail.

## 4.2 Build-time runtime renditions — source implemented

`assets/catalog/shared_visuals_v1_source.toml` explicitly selects the first reviewed UI masters/variants for runtime rendition:

```text
ui.panel.base
ui.card.activity            default / focused / completed
ui.button.primary           default / hover / pressed / disabled
ui.shadow.soft              default
```

`ui.shadow.soft` is intentionally included as the safest first controlled Shell visual enhancement because it can improve existing activity tiles without forcing a layout/card redesign.

`tools/build_visual_renditions.py`:

- accepts only explicit SVG sources under the assets root;
- invokes build-host `rsvg-convert`/librsvg;
- writes explicit PNG rendition paths;
- validates source/output containment, kind/variant names, dimensions, duplicate outputs and generated PNG IHDR dimensions;
- renders each PNG to a temporary sibling and atomically replaces the previous output only after validation;
- writes the generated runtime catalogue atomically with the source SHA256;
- preserves prior good generated output if a rasterizer invocation fails;
- never requires SVG rendering on the target device.

`make visual-assets` is the explicit generation entrypoint.

## 4.3 Generated-rendition validation — source implemented

`tools/validate_visual_renditions.py` / `make visual-assets-check` validates existing generated output without rasterizing:

- source-spec SHA256 freshness;
- catalog ID/version parity;
- exact visual ID/kind/role/variant mapping parity;
- explicit runtime paths;
- PNG signatures;
- exact expected PNG dimensions.

This validator remains part of the source/build contract. The current owner-directed local-agent acceptance tranche uses the Activity Simulator for runtime/visual/fallback/responsive testing; direct validator/unit invocations are not the named PASS evidence path for that current local-agent session unless the owner changes the instruction.

## 4.4 Bounded Pygame surface cache — source implemented

`PygameVisualSurfaceCache` sits on existing `ui_core.BoundedCache`:

- semantic ID + explicit variant + requested size key;
- PNG-only runtime enforcement;
- lazy Pygame import;
- no display-dependent `convert()` / `convert_alpha()` in its loader;
- one-time scaling on cache miss;
- default **12-entry** LRU;
- default per-surface pixel ceiling **1024×600**;
- no per-frame file/decode work after cache hit;
- explicit `clear()`.

Provider-free cache tests cover hits, scaling keys, variants, LRU eviction/reload, clear/reload, invalid dimensions, pixel ceiling, SVG rejection and unknown catalogue entries/variants.

An isolated local provider-free harness using the exact cache source passed **9/9**. This is not a repository-wide `make test` / `make verify` claim.

## 4.5 Launcher fallback bridge — source implemented, not wired yet

`src/greia_launcher/visual_assets.py` provides the explicit bridge required before the first Shell consumer:

- mandatory core-icon catalogue always loads first;
- generated shared-visual catalogue is loaded only from an exact supplied path;
- valid generated visuals merge into the same `AssetCatalogue` namespace;
- missing/invalid generated visuals leave the established core/static launcher path intact;
- no source-art scanning or automatic discovery.

Provider-free tests cover missing optional output, valid merge, invalid generated catalogue fallback and mismatched asset-root fallback.

**The bridge is not yet called from `greia_launcher.main`; therefore no actual Shell visual is claimed consumed yet.**

## 4.6 Current evidence / environmental blocker

The previous execution environment did not provide `rsvg-convert`, so the real `assets/visual/runtime/v1/...` PNGs and `assets/catalog/shared_visuals_v1.toml` were not honestly generated/validated there.

Committed provider-free test source covers catalogue merging, cache behavior, transactional generation, generated-output validation and launcher fallback. Only the previously recorded isolated cache harness (9/9) and builder harness (3/3) have actually executed locally. Newer focused test files remain **SOURCE only** until executed through an owner-approved procedure.

## 4.7 V5 gate still open

V5 is **not complete** until all of the following occur:

1. on an owner-controlled/build checkout with librsvg, run `make visual-assets` to generate the explicit runtime PNG/catalogue prerequisite;
2. inspect the generated PNGs/catalogue and preserve the fail-closed build contract;
3. wire one existing controlled Shell/UI path first through the generated catalogue/cache — current first candidate: `ui.shadow.soft` beneath existing activity tiles, with current primitive/static rendering retained as fallback;
4. verify no per-frame decode/discovery and clear/rebound cache correctly on relevant viewport changes;
5. execute the current owner-directed simulator acceptance in `docs/testing/2026-08-20_V5_VISUAL_INTEGRATION_SIMULATOR_LOCAL_AGENT.md`, including normal, fallback, interaction and responsive cases;
6. only then expand the same semantic contract toward Activities/Web;
7. collect physical low-resource evidence later before stronger physical/runtime claims.

Until step 3 succeeds and simulator acceptance is recorded, source packs remain `runtime_consumed = false`.

---

# 5. Current checkpoint

| Field | Current state |
|---|---|
| Stable visual-system/index guide | `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` |
| Cross-session resume | `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` |
| Active focus | **V5 shared consumption/integration** |
| Environment coverage | V4 complete through Water/Pond; no new pack without a concrete gap |
| Catalogue | typed explicit visuals + safe cross-manifest merge implemented |
| Runtime rendition source | first bounded UI selection includes `ui.shadow.soft` |
| Build tooling | transactional SVG→PNG tool + `make visual-assets` |
| Generated-output validation | `make visual-assets-check` implemented as source/build contract |
| Runtime cache | bounded PNG-only Pygame surface cache implemented |
| Launcher preparation | explicit optional shared-visual merge/fallback bridge implemented; `main.py` not yet wired |
| Test evidence | cache isolated harness 9/9 PASS; builder isolated harness 3/3 PASS; newer focused test files remain SOURCE only |
| Generated PNG/catalog evidence | **not generated in the previous execution environment**; `rsvg-convert` was unavailable there |
| Actual Shell/Activity consumption | **not yet wired/accepted** |
| Current local acceptance rule | runtime/visual/fallback/responsive V5 acceptance through the Activity Simulator using the dated V5 local-agent runbook |
| Evidence boundary | art: SOURCE + DESKTOP VISUAL REVIEW; V5: SOURCE + narrow isolated provider-free evidence only |
| Next exact action | owner/build checkout: install/check librsvg → `make visual-assets` → wire `ui.shadow.soft` through launcher bridge/cache → execute simulator normal/fallback/interaction/responsive matrix → update plan/resume/HANDOVER |

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
- [ ] generate first runtime PNG catalogue on a build host with librsvg;
- [ ] first controlled Shell/UI consumption path (`ui.shadow.soft` candidate);
- [ ] simulator normal/fallback/interaction/responsive acceptance for first consumer;
- [ ] shared Python/Web Activity semantic contract;
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
- continuing to create environment packs after reusable coverage is broad without a concrete need;
- wiring a visual that changes launcher geometry before the existing layout can safely accommodate it;
- treating generated build products as valid when stale/corrupt/unverified.

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
- New merge/validator/launcher test files are **SOURCE only** until executed through an owner-approved procedure; no false PASS claim is made.

## 2026-08-20 — visual-system documentation consolidated
- Added `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` as the stable human/agent visual-system architecture and index.
- Added `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` as the short cross-session visual continuation contract.
- Updated `AGENTS.md` and `docs/DOCUMENTATION.md` so visual work starts from the new system guide, then the active plan/resume and narrower authorities.
- Updated the visual-authoring skill to remove stale “first pack” guidance and focus current work on V5 integration.
- Current owner-directed V5 local-agent acceptance remains Activity-Simulator based through `docs/testing/2026-08-20_V5_VISUAL_INTEGRATION_SIMULATOR_LOCAL_AGENT.md`.

Next exact action: on an owner-controlled/build checkout with librsvg, run `make visual-assets`, wire `ui.shadow.soft` into the existing launcher activity-tile draw path through the merged catalogue + bounded surface cache, preserve the primitive/static fallback, then execute the full simulator normal/fallback/interaction/responsive acceptance matrix and update this plan/resume/HANDOVER with exact evidence.
