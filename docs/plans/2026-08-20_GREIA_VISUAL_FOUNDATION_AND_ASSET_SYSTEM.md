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

Aim for polished storybook / toy-diorama quality with:

- attractive silhouette;
- coherent warm palette;
- restrained gradients/detail;
- local highlights and soft depth;
- clean alpha edges;
- reusable shadows;
- low-resolution readability;
- cheap/static fallback viability on Greia's low-resource floor.

Raw tutorial rectangles/circles/polygon scenery are prototype/debug art only.

## Layered environments

Use separate sky/base, far background, mid background, playfield, interactive props, foreground, atmosphere/light/shadow/FX, character and protected-UI layers.

## Subtle life

Allowed design metadata includes cheap cloud drift, far/mid/near parallax, tiny foliage sway, firefly/dust drift, fog movement, slow light breathing, water shimmer and contact-shadow response. Motion enriches good static assets; it does not rescue bad art.

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

# 3. Forest / meadow — V2A

Canonical pack:

```text
assets/visual/environments/forest_meadow/v0.2/
```

Current source includes **27 reusable SVG masters** across trees, bushes/foliage, mushrooms, rocks/log/stump, clouds/hills/tree line, ground, sunlight/fog, contact shadows and ambient FX.

The final desktop restraint pass now has dedicated **1024×600 and 800×600** reference compositions using the real pack assets. Default daytime composition keeps fireflies/dust/leaves optional, reduces fog/light opacity and deliberately protects a calm center.

`runtime_consumed = false`.

---

# 4. Shared UI visual kit — V3

Canonical pack:

```text
assets/visual/ui/v0.1/
```

Current reusable source covers panels/sheets, cards and states, buttons and states, tabs, badges, progress, bubbles, reward/avatar frames, loading/error/empty/portal art, focus ring, shared shadow and highlight treatment.

The pack now also has independently composed **1024×600 and 800×600** references using the real shared masters. Focus/completed/new/favorite states remain readable after target-size scaling.

`runtime_consumed = false`.

---

# 5. Workshop — V4A

Canonical pack:

```text
assets/visual/environments/workshop/v0.1/
```

Workshop now contains **19 reusable masters**, expanding the original prop set only with composition-critical wall/floor, stool, pegboard, easel and pinboard-note assets.

The pack has independently composed **1024×600 and 800×600** layered references. Window/light remain separate assets and the composition retains an uncluttered working/play area.

`runtime_consumed = false`.

---

# 6. Clinic / care — V4B

Canonical pack:

```text
assets/visual/environments/clinic/v0.1/
```

Clinic now contains **17 reusable masters** covering bed/cushion, cabinet/side table, bowl/bottles/bandage box, toy stethoscope, care kit, plush helper, heart rug, curtains, room bases, window/light and restrained heart FX.

The tone is deliberately warm pretend-care rather than sterile hospital imagery. It has reduced-size review plus independent **1024×600 and 800×600** references.

`runtime_consumed = false`.

Further Clinic work should now be defect-driven rather than decorative expansion.

---

# 7. Reading / classroom — V4C **[CURRENT NEW PACK]**

Canonical pack:

```text
assets/visual/environments/reading_classroom/v0.1/
```

The first reading/classroom tranche contains **17 reusable masters**:

- room wall + floor bases;
- arched window + optional window light;
- tall bookcase;
- book stack + open storybook;
- reading tent;
- round rug;
- beanbag, reading chair and floor cushion;
- chalkboard;
- bunting;
- potted plant;
- toy basket;
- hanging mobile.

The pack explicitly references existing Workshop `blocks` and `pencil_cup` assets rather than duplicating them.

First desktop review corrected three weak pieces before commit:

- `book_stack.svg` — too card-like;
- `reading_tent.svg` — insufficient fabric/depth treatment;
- `beanbag.svg` — insufficient volume/seam definition.

`composition.toml` records target-size layer roles and calm-center guidance. The local evidence pack also contains independently composed 1024×600 / 800×600 references.

`runtime_consumed = false`.

---

# 8. Storage and metadata

Reusable assets record semantic ID, source path, family, review state, provenance/license, intended scale/alpha where relevant, parallax/layer role where relevant, and optional ambient-motion/theme variants.

Use `concept | candidate | approved | superseded | rejected`. Presence in Git never means approved.

---

# 9. Review loop

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

---

# 10. Current checkpoint

| Field | Current state |
|---|---|
| Active focus | **V4C Reading/Classroom built; next pack is fantasy/village/night while UI/environment packs remain candidate for owner refinement** |
| Forest | `assets/visual/environments/forest_meadow/v0.2/` — 27 masters + final target-size restraint pass |
| UI | `assets/visual/ui/v0.1/` — broad component/state kit + target-size references |
| Workshop | `assets/visual/environments/workshop/v0.1/` — 19 masters + target-size references |
| Clinic | `assets/visual/environments/clinic/v0.1/` — 17 masters + reduced-size + target-size references |
| Reading/Classroom | `assets/visual/environments/reading_classroom/v0.1/` — 17 masters + metadata/review/composition manifest |
| Evidence | **SOURCE + DESKTOP VISUAL REVIEW** only; all current art remains candidate |
| Runtime boundary | all current visual catalogs remain `runtime_consumed = false`; no loader/compositor architecture invented here |
| Next exact action | start the fantasy/village/night reusable-asset family with individual assets first; continue UI/environment refinement only for concrete defects or owner feedback |

---

# 11. Milestones

## V1 — Character/style seed **[SUFFICIENT TO UNBLOCK LIBRARY]**
- [x] simplified character direction;
- [x] core cast seed;
- [ ] continue useful character refinement without blocking wider art.

## V2 — Forest/meadow composable environment **[DESKTOP CANDIDATE BUILT]**
- [x] 27-source-asset candidate pack;
- [x] light/shadow/atmosphere/FX;
- [x] metadata + review;
- [x] layered composition manifest;
- [x] cheap parallax/ambient-motion proof;
- [x] final 800×600 / 1024×600 restraint pass;
- [ ] owner approval/revision when appropriate.

## V3 — Shared UI visual kit **[DESKTOP CANDIDATE BUILT]**
- [x] panels/cards/buttons/tabs/badges/progress/bubbles/frames;
- [x] focus/hover/press/disabled/completed/favorite states;
- [x] loading/error/empty/portal art;
- [x] common shadow/highlight pieces;
- [x] multi-ground desktop review;
- [x] 800×600 / 1024×600 reference compositions;
- [ ] owner approval/revision when appropriate.

## V4 — Additional environment packs **[ACTIVE]**
- [x] Workshop asset pack + reference composition;
- [x] Clinic asset pack + reference composition;
- [x] Reading/classroom asset pack + composition metadata/review;
- [ ] fantasy/village/night family;
- [ ] later water/pond family as prioritized.

## V5 — Shared consumption/integration
- [ ] explicit catalog/consumption seam through accepted architecture;
- [ ] bounded loading/caching;
- [ ] Shell + Activities reuse same assets/components;
- [ ] simulator/physical low-resource acceptance where implementation claims require it.

---

# 12. Failure patterns — do not repeat

- spending the workstream on character minutiae;
- detailed traditional rigs as default;
- one-shot sprite sheets assumed production-ready;
- degrading accepted character art with overlays/redraws;
- non-blinking `blink`;
- crude primitive scenery presented as redesign;
- full-screen mockups before real assets exist;
- decorative HTML hiding weak art;
- inventing new runtime/UI architecture during art production;
- replacing asset-first production with generated scene concept images.

---

# 13. Progress log — append only

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
- Workshop first 13 masters committed and reviewed.

## 2026-08-20 — target-size tranche + Clinic
- Forest final restraint references created at 1024×600 and 800×600.
- Shared UI target-size compositions created.
- Workshop expanded to 19 masters with only composition-critical additions and target-size references.
- Clinic 17-master pack created with reduced-size and target-size desktop review.
- Source tranche committed in `869cdc502458d54d667d5ed60d781411be763851`.

## 2026-08-20 — Reading/Classroom v0.1
- Built a bounded 17-master reading/classroom source pack.
- Reused Workshop block/pencil assets by reference instead of duplicating them.
- Revised weak book-stack, tent and beanbag treatments after direct desktop review.
- Added `catalog.toml`, `REVIEW.md`, `COMPOSITION.md` and `composition.toml`.
- Evidence remains **SOURCE + DESKTOP VISUAL REVIEW**; no runtime/simulator/hardware acceptance claimed.

Next exact action: begin the fantasy/village/night individual-asset family and keep the same asset-first discipline.
