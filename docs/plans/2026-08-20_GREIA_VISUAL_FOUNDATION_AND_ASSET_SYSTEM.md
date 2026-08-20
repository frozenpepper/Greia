# Greia Visual Foundation and Asset System — Active Art Workstream Plan

**Status:** ACTIVE ART/VISUAL WORKSTREAM  
**Date:** 2026-08-20  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`

This plan owns the current Greia visual-library workstream.

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → Shell/Activity reuse**

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

Allowed design metadata includes cheap cloud drift, far/mid/near parallax, tiny foliage sway, firefly/dust drift, fog movement, slow light breathing, water shimmer and contact-shadow response. Motion enriches good static assets; it does not rescue bad art.

## Reuse before duplication

When an existing pack already contains a suitable tree, bush, block, pencil cup, firefly, shadow or other generic visual, reference that shared asset rather than repainting a near-duplicate just because a new environment family is being built.

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

Preserve character identity across states; `blink` must actually blink. Character refinement may continue without blocking environments/UI.

---

# 3. Current reusable packs

## V2A — Forest / meadow v0.2

```text
assets/visual/environments/forest_meadow/v0.2/
```

- **27 reusable SVG masters**;
- trees, foliage, rocks/log/stump, mushrooms, clouds/hills/tree line, ground, sunlight/fog, shadows and optional ambient FX;
- composition metadata + actual-asset parallax proof;
- bounded independent **1024×600 and 800×600** restraint references;
- default daytime treatment keeps fireflies/dust/leaves optional and protects a calm center.

`runtime_consumed = false`.

## V3 — Shared UI v0.1

```text
assets/visual/ui/v0.1/
```

Broad shared visual family for panels/sheets, activity cards and states, buttons and states, tabs, badges, progress, bubbles, reward/avatar frames, loading/error/empty/portal art, focus, shadow and highlight treatment.

Independent **1024×600 and 800×600** references use the real shared masters. `runtime_consumed = false`.

## V4A — Workshop v0.1

```text
assets/visual/environments/workshop/v0.1/
```

- **19 reusable masters**;
- warm creative-room furniture/props plus only composition-critical wall/floor, stool, pegboard, easel and pinboard-note additions;
- window/light remain separate;
- independent 1024×600 / 800×600 layered references.

`runtime_consumed = false`.

## V4B — Clinic / care v0.1

```text
assets/visual/environments/clinic/v0.1/
```

- **17 reusable masters**;
- bed/cushion, cabinet/side table, bowl/bottles/bandage box, toy stethoscope, care kit, plush helper, heart rug, curtains, room bases, window/light and restrained heart FX;
- reduced-size + independent target-size desktop review;
- warm pretend-care rather than sterile hospital imagery; no medicine labels/dosage-like content.

`runtime_consumed = false`.

## V4C — Reading / classroom v0.1

```text
assets/visual/environments/reading_classroom/v0.1/
```

- **17 reusable masters**;
- room bases, arched window/light, bookcase/books, reading tent/rug/seating, chalkboard and restrained decor;
- reuses Workshop `blocks` and `pencil_cup` by reference rather than duplicating them;
- first desktop review revised weak `book_stack`, `reading_tent` and `beanbag` treatments;
- catalog/review/composition metadata committed.

`runtime_consumed = false`.

## V4D — Fantasy / village / night v0.1 **[NEW]**

```text
assets/visual/environments/fantasy_village_night/v0.1/
```

The first pack contains **15 reusable masters**:

- night sky base;
- crescent moon;
- distant village;
- castle-on-hill layer;
- round and tall cottages;
- castle tower;
- stone bridge;
- lantern post;
- wooden signpost;
- stone well;
- cobblestone edge;
- window glow;
- moonlight rays;
- optional magic sparkle FX.

The catalog explicitly references existing Forest trees/bushes/fireflies rather than duplicating night-colored versions.

First desktop asset review found the cottages, castle tower, lantern, well and cobblestone treatment too flat/weak; those assets were revised before commit. The first layered composition then exposed an oversized cobblestone placement and over-dominant moonlight; both target references were corrected before the review was recorded.

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

`runtime_consumed = false`.

---

# 4. Asset metadata and state

Reusable assets record semantic ID, source path, family/role, review state, provenance/license, intended alpha/scale where relevant, and optional parallax/ambient-motion metadata.

Use:

```text
concept | candidate | approved | superseded | rejected
```

Presence in Git never means approved. Current packs remain candidate unless their own records explicitly say otherwise.

---

# 5. Review loop

For each family:

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

# 6. Current checkpoint

| Field | Current state |
|---|---|
| Active focus | **V4D Fantasy/Village/Night built; next bounded environment family is water/pond** |
| Forest | 27 masters + target-size restraint + parallax proof |
| UI | broad shared component/state pack + target-size references |
| Workshop | 19 masters + target-size layered references |
| Clinic | 17 masters + reduced-size + target-size references |
| Reading/Classroom | 17 masters + review/composition metadata |
| Fantasy/Village/Night | 15 masters + corrected individual review + two target-size layered references |
| Evidence | **SOURCE + DESKTOP VISUAL REVIEW** only; current art remains candidate |
| Runtime boundary | all current visual catalogs remain `runtime_consumed = false`; no loader/compositor architecture invented here |
| Next exact action | build the **water/pond** reusable asset family: water base/edge, reeds/lilies, stones/log/bridge reuse where appropriate, reflection/light/shimmer overlays, fish/frog/duck-friendly props only where broadly reusable; then individual review before composition |

---

# 7. Milestones

## V1 — Character/style seed **[SUFFICIENT TO UNBLOCK LIBRARY]**
- [x] simplified character direction;
- [x] core cast seed;
- [ ] continue useful character refinement without blocking wider art.

## V2 — Forest/meadow composable environment **[DESKTOP CANDIDATE BUILT]**
- [x] 27-source-asset candidate pack;
- [x] light/shadow/atmosphere/FX;
- [x] metadata + review;
- [x] layered composition/parallax proof;
- [x] final 800×600 / 1024×600 restraint pass;
- [ ] owner approval/revision when appropriate.

## V3 — Shared UI visual kit **[DESKTOP CANDIDATE BUILT]**
- [x] core components/states/illustration pieces;
- [x] common shadow/highlight treatment;
- [x] multi-ground desktop review;
- [x] independent 800×600 / 1024×600 reference compositions;
- [ ] owner approval/revision when appropriate.

## V4 — Additional environment packs **[ACTIVE]**
- [x] Workshop;
- [x] Clinic;
- [x] Reading/classroom;
- [x] Fantasy/village/night;
- [ ] Water/pond;
- [ ] additional families only when they add genuinely reusable coverage.

## V5 — Shared consumption/integration
- [ ] explicit catalog/consumption seam through accepted architecture;
- [ ] bounded loading/caching;
- [ ] Shell + Activities reuse same assets/components;
- [ ] simulator/physical low-resource acceptance where implementation claims require it.

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
- inventing new runtime/UI architecture during art production;
- replacing asset-first production with generated scene concept images;
- repainting duplicate generic assets instead of reusing the shared library.

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
- Reading pack landed on current `main` at `6b94d6ddd8cdbecea171f40a1e47c1ac49f3aec9` after preserving concurrent repository changes.

## 2026-08-20 — Fantasy/Village/Night v0.1
- Built a bounded 15-master night/fantasy village pack.
- Reused Forest greenery/fireflies semantically instead of creating unnecessary night duplicates.
- First desktop asset review rejected/revised weak cottages, tower, lantern, well and cobblestone treatments.
- Layered target references were then corrected for cobblestone scale and excessive moonlight dominance.
- Source + composition/review metadata committed in `0958f8a0ca1b583798a245464b9e3e87a74d883c`.
- Evidence remains **SOURCE + DESKTOP VISUAL REVIEW** only; no runtime/simulator/hardware acceptance claimed.

Next exact action: build and review the **water/pond** individual-asset family without drifting into runtime work or scene-first concept art.
