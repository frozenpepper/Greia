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

Authority/evidence files:

```text
catalog.toml
REVIEW.md
composition_day.toml
parallax_proof.html
```

`runtime_consumed = false`.

Desktop review corrected weak sapling, distant-tree-line, fog and dust-mote treatments. A 1024×600 static composition was assembled from the real assets, and the committed parallax proof uses the same SVGs with only cheap CSS transforms/opacity changes.

### Remaining V2A work

- 800×600 and 1024×600 restraint/readability pass;
- remove noisy atmosphere/FX if needed;
- keep a calm gameplay center;
- do not polish this pack indefinitely once coherent.

---

# 4. Shared UI visual kit — V3

Canonical pack:

```text
assets/visual/ui/v0.1/
```

Current reusable source now covers:

- panel / sheet;
- default / focused / completed activity cards;
- primary / hover / pressed / disabled / secondary / quiet / icon buttons;
- default / selected tabs;
- new / done / favorite / locked badges;
- progress track / fill / complete;
- speech / thought bubbles;
- reward and avatar frames;
- loading orbit;
- gentle-error cloud;
- empty basket;
- category/location portal frame;
- focus ring, soft shadow and highlight sheen.

Authority/evidence files:

```text
assets/visual/ui/v0.1/catalog.toml
assets/visual/ui/v0.1/README.md
assets/visual/ui/v0.1/REVIEW.md
```

The pack follows `runtime/theme-defaults.toml`, embeds no child-facing text, and remains `runtime_consumed = false`.

Desktop review has covered representative components on cream, sky and dark grounds plus the expanded static-state tranche.

### Remaining V3 work

- low-resolution 800×600 / 1024×600 component composition using the real masters;
- check state distinctions after scaling;
- add only genuinely missing shared launcher/system decorative pieces;
- owner refinement when a coherent reference composition is ready.

---

# 5. Workshop — V4A **[STARTED]**

Canonical pack:

```text
assets/visual/environments/workshop/v0.1/
```

First individual-asset tranche includes:

- workbench;
- shelf;
- paint palette;
- brush bundle;
- pencil cup;
- blocks;
- storage box;
- paper stack;
- rug;
- desk lamp;
- window;
- composable window-light overlay;
- paint jars.

Metadata/review:

```text
catalog.toml
README.md
REVIEW.md
```

First desktop review found a coherent warm wood/pastel creative-room family. Window/light remain separate composable assets. `runtime_consumed = false`.

### Next Workshop work

- reduced-size review of furniture/large pieces;
- add only composition-critical missing elements such as stool/chair, wall/floor base or pegboard;
- make one layered workshop composition from the coherent subset;
- do not fill the pack with decorative clutter.

---

# 6. Next environment families

## Clinic / care room

Planned individual assets:

- bed/cushion;
- cabinet/shelf;
- bowls/bottles/bandages/toy-care props;
- rug;
- window/light assets;
- heart/care FX;
- room-base layers.

Then reading/classroom and later fantasy/village/night/water families as prioritized.

---

# 7. Storage and metadata

Conceptual source organization:

```text
assets/visual/
  characters/
  environments/
  props/
  atmosphere/
  fx/
  shadows/
  ui/
  specimens/
  catalog/
```

Reusable assets record semantic ID, source path, family, review state, provenance/license, intended scale/alpha where relevant, parallax/layer role where relevant, and optional ambient-motion/theme variants.

Use `concept | candidate | approved | superseded | rejected`. Presence in Git never means approved.

---

# 8. Review loop

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

Focused browser/HTML files are allowed only as proofs using real assets; they are not visual "presentations" or runtime authority.

---

# 9. Current checkpoint

| Field | Current state |
|---|---|
| Active focus | **V3 shared UI review + V4A workshop pack; V2A forest in final restraint pass** |
| Forest | `assets/visual/environments/forest_meadow/v0.2/` — 27 SVG masters + composition/parallax proof |
| UI | `assets/visual/ui/v0.1/` — expanded component/state/illustration pack |
| Workshop | `assets/visual/environments/workshop/v0.1/` — first 13 individual masters committed |
| Evidence | **SOURCE + DESKTOP VISUAL REVIEW** only; current art remains candidate |
| Runtime boundary | all current visual catalogs remain `runtime_consumed = false`; no loader/compositor architecture invented here |
| Next exact action | do low-resolution UI + Workshop review/composition-critical refinement, finish forest restraint pass, then begin Clinic individual assets |

---

# 10. Milestones

## V1 — Character/style seed **[SUFFICIENT TO UNBLOCK LIBRARY]**
- [x] simplified character direction;
- [x] core cast seed;
- [ ] continue useful character refinement without blocking wider art.

## V2 — Forest/meadow composable environment **[SUBSTANTIALLY BUILT]**
- [x] 27-source-asset candidate pack;
- [x] light/shadow/atmosphere/FX;
- [x] metadata + review;
- [x] layered composition manifest;
- [x] cheap parallax/ambient-motion proof;
- [ ] final 800×600 / 1024×600 restraint pass;
- [ ] owner approval/revision when appropriate.

## V3 — Shared UI visual kit **[ACTIVE / SUBSTANTIALLY BUILT]**
- [x] panels/cards/buttons/tabs/badges/progress/bubbles/frames;
- [x] focus/hover/press/disabled/completed/favorite states;
- [x] loading/error/empty/portal art;
- [x] common shadow/highlight pieces;
- [x] first multi-ground desktop review;
- [ ] low-resolution reference composition;
- [ ] owner approval/revision when appropriate.

## V4 — Additional environment packs **[WORKSHOP STARTED]**
- [x] Workshop first individual-asset tranche;
- [ ] Workshop composition-critical refinement + reference composition;
- [ ] Clinic;
- [ ] reading/classroom;
- [ ] later fantasy/village/night/water families.

## V5 — Shared consumption/integration
- [ ] explicit catalog/consumption seam through accepted architecture;
- [ ] bounded loading/caching;
- [ ] Shell + Activities reuse same assets/components;
- [ ] simulator/physical low-resource acceptance where implementation claims require it.

---

# 11. Failure patterns — do not repeat

- spending the workstream on character minutiae;
- detailed traditional rigs as default;
- one-shot sprite sheets assumed production-ready;
- degrading accepted character art with overlays/redraws;
- non-blinking `blink`;
- crude primitive scenery presented as redesign;
- full-screen mockups before real assets exist;
- decorative HTML hiding weak art;
- inventing new runtime/UI architecture during art production.

---

# 12. Progress log — append only

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

Commits:
- `ee1faa2056156d756d233f01e7b46cdde2c1e4f3`
- `eefb9db344ab59aa25be0f341e34e4ecb777a517`
- `70e9980392cb873fc1b4aab1234c75dd18ac4f3e`
- `873d228c14539da1daf040949431b51ad8ed221a`

## 2026-08-20 — UI v0.1 and Workshop v0.1 advanced

UI:
- first broad shared UI source pack committed;
- expanded with hover/pressed/disabled/completed/favorite/progress-complete states;
- added loading/error/empty/portal illustration masters;
- indexed in catalog v0.1.1.

Workshop:
- first 13 individual creative-room masters committed;
- catalog/README/review added;
- assets reviewed together on Greia cream ground before any room composition.

Evidence: SOURCE + DESKTOP VISUAL REVIEW only.

Commits:
- `e42114e77d2c945e44febffec9b78b6490173504` — expanded UI source + Workshop initial pack
- `24abd46d4c61671612898730c2dd5deb99e0ea98` — UI catalog v0.1.1
- `f20cf179966282e763f663806995f10fb0ce9a80` — UI README refresh
- `d338fbd6170c2fe8d8c6060cb9537c9e8f2540aa` — Workshop review record

Next exact action: low-resolution UI/Workshop review and composition-critical refinements, final forest restraint pass, then Clinic individual-asset tranche.
