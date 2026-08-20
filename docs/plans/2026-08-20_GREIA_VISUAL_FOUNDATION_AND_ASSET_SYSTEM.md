# Greia Visual Foundation and Asset System — Active Art Workstream Plan

**Status:** ACTIVE ART/VISUAL WORKSTREAM  
**Date:** 2026-08-20  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`

This plan owns the current Greia visual-library workstream.

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → one explicit shared consumption seam → Shell/Activity reuse**

The project is not making decorative mock screens. Characters are one part of the library, not the workstream bottleneck.

---

# 1. Non-negotiable production rules

## Asset first

A scene or UI family starts with reusable source assets that are worth keeping individually. Weak primitives may not be hidden by a busy composition.

## Quality target

Aim for polished storybook / toy-diorama quality with attractive silhouette, coherent warm palette, restrained gradients/detail, local highlights and soft depth, clean alpha edges, reusable shadows, low-resolution readability, and cheap/static fallback viability on Greia's low-resource floor.

Raw tutorial rectangles/circles/polygon scenery are prototype/debug art only.

## Layered environments

Use separate sky/base, far background, mid background, playfield, interactive props, foreground, atmosphere/light/shadow/FX, character and protected-UI layers.

## Subtle life

Allowed design metadata includes cheap cloud drift, far/mid/near parallax, tiny foliage/reed sway, firefly/dust drift, fog movement, slow light breathing, water shimmer/ripples and contact-shadow response. Motion enriches good static assets; it does not rescue bad art.

## Reuse before duplication

When an existing pack already contains a suitable tree, bush, rock, log, block, pencil cup, firefly, shadow, distant hill or other generic visual, reference that shared asset rather than repainting a near-duplicate just because a new environment family is being built.

## Stop expanding once coverage is good

Do not invent more environment families merely to keep producing art. Additional packs now require a concrete reusable coverage gap. The next planned phase is the **shared consumption seam**, not endless asset-family proliferation.

---

# 2. Character seed

Working core cast remains **Lilli, Nino, Tito, Momo** with the accepted simplified Puff/Bean direction.

Base motion names remain:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Preserve character identity across states; `blink` must actually blink. Character refinement may continue without blocking environments/UI or the shared-library consumption work.

---

# 3. Current reusable packs

All current packs are **candidate** unless their own records explicitly say otherwise. All environment/UI catalogs remain `runtime_consumed = false`.

## V2A — Forest / meadow v0.2

`assets/visual/environments/forest_meadow/v0.2/`

- **27 reusable SVG masters**;
- trees, foliage, rocks/log/stump, mushrooms, clouds/hills/tree line, ground, sunlight/fog, shadows and optional ambient FX;
- composition metadata + actual-asset parallax proof;
- independent **1024×600 and 800×600** restraint references;
- default daytime treatment keeps fireflies/dust/leaves optional and protects a calm center.

## V3 — Shared UI v0.1

`assets/visual/ui/v0.1/`

Broad shared family for panels/sheets, activity cards and states, buttons and states, tabs, badges, progress, bubbles, reward/avatar frames, loading/error/empty/portal art, focus, shadow and highlight treatment.

Independent **1024×600 and 800×600** references use the real shared masters.

## V4A — Workshop v0.1

`assets/visual/environments/workshop/v0.1/`

- **19 reusable masters**;
- warm creative-room furniture/props plus only composition-critical wall/floor, stool, pegboard, easel and pinboard-note additions;
- window/light remain separate;
- independent target-size layered references.

## V4B — Clinic / care v0.1

`assets/visual/environments/clinic/v0.1/`

- **17 reusable masters**;
- warm pretend-care furniture/props, room bases, window/light and restrained care FX;
- reduced-size + independent target-size desktop review;
- no medicine labels/dosage-like content.

## V4C — Reading / classroom v0.1

`assets/visual/environments/reading_classroom/v0.1/`

- **17 reusable masters**;
- room bases, arched window/light, bookcase/books, reading tent/rug/seating, chalkboard and restrained decor;
- reuses Workshop blocks/pencil-cup assets by reference rather than duplication;
- weak book-stack, tent and beanbag treatments were revised during desktop review.

## V4D — Fantasy / village / night v0.1

`assets/visual/environments/fantasy_village_night/v0.1/`

- **15 reusable masters**;
- night sky/moon, distant village/castle, cottages, tower, bridge, lantern, signpost, well, cobblestone and separate light/FX overlays;
- Forest greenery/fireflies remain shared dependencies;
- weak cottages/tower/lantern/well/cobblestone were revised before commit;
- both target references were corrected for cobblestone scale and excessive moonlight dominance.

## V4E — Water / pond v0.1 **[NEW]**

`assets/visual/environments/water_pond/v0.1/`

The first bounded Water/Pond family contains **14 water-specific reusable masters**:

- pond-water base;
- shoreline/bank edge;
- lily-pad cluster;
- water-lily cluster;
- reeds/cattails;
- small dock;
- stepping stones;
- duckweed;
- ripple ring;
- water shimmer;
- reflection glow;
- fish shadows;
- dragonfly FX;
- bubble FX.

Reuse is explicit: target references use canonical Forest/Meadow distant hills/tree line, and the catalog points to Forest rocks/log/grass/flowers instead of repainting them.

Desktop review corrected weak dock/lily-pad treatments, then strengthened the water base, lily-pad geometry and reed depth before independent **1024×600 and 800×600** composition review.

Authority/evidence:

```text
catalog.toml
README.md
REVIEW.md
COMPOSITION.md
composition.toml
reference_1024x600.svg
reference_800x600.svg
```

---

# 4. Library inventory / metadata authority

Pack-level design inventory:

```text
assets/visual/packs_v0.1.toml
```

Character/archetype/motion seed inventory:

```text
assets/visual/library_v0.1.toml
```

`library_v0.1.toml` now points to the pack index and no longer describes environment/UI/FX families as merely planned.

These files are **design/review inventory, not runtime filesystem discovery**.

Reusable assets record semantic ID, source path, family/role, review state, provenance/license, intended alpha/scale where relevant, layer/parallax role and optional ambient-motion metadata.

Use:

```text
concept | candidate | approved | superseded | rejected
```

Presence in Git never means approved.

---

# 5. Shared consumption seam — V5 direction

Greia already has platform-owned asset code:

```text
src/greia_platform/assets.py
src/greia_platform/activity_assets.py
assets/catalog/core_icons_v1.toml
```

Important existing behavior:

- `AssetCatalogue` already provides explicit manifest-driven global icon resolution with path containment;
- Activity packages may use validated package-owned PNG/WebP launcher icons through `activity_assets.py`;
- therefore V5 must **extend the accepted explicit catalogue pattern**, not add arbitrary directory scans or a second unrelated asset framework.

### V5 first implementation gate

Before runtime consumption is enabled for any visual pack:

1. inspect current callers/tests of `AssetCatalogue` and Activity asset boundaries;
2. define the smallest typed extension that can resolve a shared visual asset by semantic ID + variant/role while preserving existing icon behavior;
3. keep manifest paths explicit and path-contained;
4. define bounded decode/cache behavior separately from lookup;
5. preserve static fallback for semantic motion;
6. add provider-free unit tests for duplicate IDs, missing files, path escape, unsupported kinds/variants and backward compatibility;
7. integrate **one controlled Shell/UI path first** before claiming general Activity consumption;
8. keep Web/Python Activities on the same semantic contract rather than creating parallel libraries.

No V5 runtime implementation is accepted merely because design catalogs exist.

---

# 6. Review loop

For each asset family:

1. define a bounded list;
2. make individual assets;
3. rasterize/review individually;
4. inspect on representative grounds/sizes;
5. fix weak assets instead of masking them;
6. record metadata/provenance;
7. identify a coherent subset;
8. make a small reference composition only from real pieces;
9. test restrained layering/parallax/motion where relevant;
10. integrate later only through accepted Greia platform seams.

Focused browser/HTML files are allowed only as proofs using real assets; they are not visual presentations or runtime authority.

Do **not** replace this process with generated scene/concept imagery.

---

# 7. Current checkpoint

| Field | Current state |
|---|---|
| Active focus | **V4 environment coverage complete through Water/Pond; V5 shared-consumption seam is now the next planned work** |
| Forest | 27 masters + target-size restraint + parallax proof |
| UI | broad shared component/state pack + target-size references |
| Workshop | 19 masters + target-size layered references |
| Clinic | 17 masters + reduced-size + target-size references |
| Reading/Classroom | 17 masters + review/composition metadata |
| Fantasy/Village/Night | 15 masters + corrected individual review + target references |
| Water/Pond | 14 water-specific masters + Forest reuse + corrected target references |
| Inventory | `assets/visual/packs_v0.1.toml` + refreshed `library_v0.1.toml` |
| Evidence | **SOURCE + DESKTOP VISUAL REVIEW** only; current art remains candidate |
| Runtime boundary | all current visual packs remain `runtime_consumed = false` |
| Next exact action | start **V5 preflight** by tracing current `AssetCatalogue` callers/tests and defining the minimal backwards-compatible explicit visual-asset manifest extension; do not create more environment families without a concrete coverage gap |

---

# 8. Milestones

## V1 — Character/style seed **[SUFFICIENT TO UNBLOCK LIBRARY]**
- [x] simplified character direction;
- [x] core cast seed;
- [ ] continue useful character refinement without blocking wider art.

## V2 — Forest/meadow composable environment **[DESKTOP CANDIDATE BUILT]**
- [x] 27-source-asset candidate pack;
- [x] light/shadow/atmosphere/FX;
- [x] metadata + review;
- [x] layered composition/parallax proof;
- [x] final target-size restraint pass;
- [ ] owner approval/revision when appropriate.

## V3 — Shared UI visual kit **[DESKTOP CANDIDATE BUILT]**
- [x] core components/states/illustration pieces;
- [x] common shadow/highlight treatment;
- [x] multi-ground desktop review;
- [x] independent target-size reference compositions;
- [ ] owner approval/revision when appropriate.

## V4 — Additional environment packs **[DESKTOP CANDIDATE COVERAGE COMPLETE]**
- [x] Workshop;
- [x] Clinic;
- [x] Reading/classroom;
- [x] Fantasy/village/night;
- [x] Water/pond;
- [x] pack-level inventory and reuse dependencies;
- [ ] additional family only when a concrete reusable coverage gap is demonstrated.

## V5 — Shared consumption/integration **[NEXT]**
- [ ] trace existing catalogue callers/tests;
- [ ] explicit backwards-compatible visual-asset manifest contract;
- [ ] bounded lookup/cache/decode boundaries;
- [ ] first controlled Shell/UI consumption path;
- [ ] shared Python/Web Activity contract;
- [ ] simulator/physical low-resource acceptance where implementation claims require it.

---

# 9. Failure patterns — do not repeat

- spending the workstream on character minutiae;
- detailed traditional rigs as default;
- one-shot sprite sheets assumed production-ready;
- degrading accepted character art with overlays/redraws;
- non-blinking `blink`;
- crude primitive scenery presented as redesign;
- full-screen mockups before real assets exist;
- decorative HTML hiding weak art;
- inventing a second runtime/UI asset architecture when accepted platform seams exist;
- replacing asset-first production with generated scene concept images;
- repainting duplicate generic assets instead of reusing the shared library;
- continuing to create environment packs after reusable coverage is already broad without a concrete need.

---

# 10. Progress log — append only

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

Next exact action: V5 preflight against the existing platform asset catalogue and Activity asset boundary; extend the accepted manifest-driven architecture instead of inventing a new one.
