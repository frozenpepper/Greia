# Greia Visual Foundation and Asset System — Active Art Workstream Plan

**Status:** ACTIVE ART/VISUAL WORKSTREAM  
**Date:** 2026-08-20  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`

This plan owns the current Greia visual-library workstream.

The production model is:

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → Shell/Activity reuse**

The project is not making decorative mock screens. Characters are only one part of the shared visual library.

---

# 1. Non-negotiable direction

## 1.1 Asset first

A scene or UI family starts with reusable individual source assets that are worth keeping on their own. Weak primitives do not become acceptable because they are hidden inside a busy composition.

Priority reusable families include:

- trees, bushes, flowers, rocks, logs, clouds, hills, tree lines and ground pieces;
- workshop / clinic furniture and props;
- shadow decals, light shafts, fog/haze, fireflies, dust and sparkles;
- UI panels, cards, buttons, tabs, badges, frames, bubbles, highlights and trims.

## 1.2 Quality target

Assets should aim for polished storybook / toy-diorama quality:

- attractive silhouette;
- warm coherent palette;
- controlled gradients and internal detail;
- soft local highlights;
- visible but restrained depth;
- clean alpha edges;
- reusable contact/cast shadow treatment;
- readable at low resolution;
- simple enough to remain viable on Greia's low-resource targets.

Raw tutorial circles/rectangles/polygon scenery are prototype/debug art only.

## 1.3 Layered composition

Normal environment composition separates useful planes:

1. sky / room base;
2. far background;
3. mid background;
4. ground / playfield;
5. interactive props;
6. foreground framing;
7. atmosphere / light / shadow / FX;
8. character + protected UI layers.

## 1.4 Subtle life

Reusable metadata may describe inexpensive motion such as:

- slow cloud drift;
- far/mid/near parallax;
- tiny foliage sway;
- firefly fade/drift;
- dust motes;
- falling leaves;
- fog drift;
- very slow light breathing;
- water shimmer;
- contact-shadow response.

Static quality and meaning remain primary. No scene requires every effect.

---

# 2. Character library

Core cast remains **Lilli, Nino, Tito, Momo**.

Base motions remain:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Rules:

- preserve the same character art across states;
- `blink` must actually blink;
- expression/motion work may continue, but must not block backgrounds, props, atmosphere, shadows and UI.

---

# 3. Forest / meadow environment pack — V2A

Canonical candidate pack:

```text
assets/visual/environments/forest_meadow/v0.2/
```

It contains **27 reusable SVG masters** plus metadata/review/proof source:

- 4 trees;
- 3 bushes;
- fern / flower / mushroom foliage;
- 2 rock clusters;
- fallen log + stump;
- 2 clouds;
- distant hills + tree line;
- grass edge + dirt playfield patch;
- sunlight + fog;
- 2 contact shadows;
- fireflies / dust motes / falling leaves.

Authority/metadata:

```text
assets/visual/environments/forest_meadow/v0.2/catalog.toml
assets/visual/environments/forest_meadow/v0.2/REVIEW.md
assets/visual/environments/forest_meadow/v0.2/composition_day.toml
assets/visual/environments/forest_meadow/v0.2/parallax_proof.html
```

All assets remain **candidate**. `runtime_consumed = false`; the composition/parallax files are design proofs, not a runtime scene framework.

## 3.1 Review already performed

Desktop individual/composition review found and corrected specific weak first-pass assets:

- sapling silhouette/detail balance;
- distant tree line repetitive geometry;
- fog depth/readability;
- dust-mote visibility.

A 1024×600 static composition was assembled locally from the real masters to verify that the pieces form a coherent layered family without repainting them into one baked background.

`parallax_proof.html` now exercises the same committed SVGs with only cheap CSS transforms/opacity changes: slow clouds, tiny tree/foliage sway, fog drift, light breathing and firefly drift. It is deliberately isolated design evidence and must not become runtime architecture.

## 3.2 Next V2A work

- check the composition at 800×600 and 1024×600;
- remove atmosphere/FX that adds noise rather than depth;
- ensure foreground framing leaves a calm gameplay center;
- then stop polishing the forest indefinitely and move to the next environment family.

---

# 4. Shared UI visual kit — V3 **[ACTIVE IN PARALLEL]**

Canonical candidate pack:

```text
assets/visual/ui/v0.1/
```

Current pack contains reusable masters for:

- panel + sheet;
- default + focused activity card;
- primary / secondary / quiet / icon button;
- default + selected tab pill;
- new / completed / locked badges;
- progress track + fill;
- speech + thought bubbles;
- reward frame;
- avatar frame;
- common focus ring;
- soft shadow;
- highlight sheen.

Metadata/review:

```text
assets/visual/ui/v0.1/catalog.toml
assets/visual/ui/v0.1/REVIEW.md
```

The pack is derived from `runtime/theme-defaults.toml` and contains no embedded child-facing text so the same visual pieces can be localized/reused.

## 4.1 Current UI review

Representative assets were rasterized locally and inspected on:

- Greia cream;
- Greia sky;
- dark charcoal.

The panel, focused activity card, primary button, selected tab, speech bubble and reward frame remained visually readable on all three grounds. Focus/selection uses frame/shape cues as well as color.

This is **DESKTOP VISUAL REVIEW only**, not owner approval or runtime integration.

## 4.2 Next UI tranche

Create/refine individual masters for:

- hover / pressed / disabled states where a distinct static treatment helps;
- favorite badge;
- progress-complete / reward states;
- loading, error and empty-state illustration pieces;
- category/location portal frames;
- any missing shared icon/decorative trim required by the launcher.

Then create one low-resolution UI composition from these real assets. Do not return to primitive mock-screen drawing.

---

# 5. Later environment packs

## Workshop / creative room

- workbench/table;
- shelves;
- paper / paint / brush / pencil props;
- blocks/tools;
- rug/storage;
- window/lamp/light assets;
- wall/base layers.

## Clinic / care room

- bed/cushion;
- cabinet/shelf;
- bowls/bottles/bandages/toy-care props;
- rug;
- window/light assets;
- heart/care FX;
- room-base layers.

Then reading/classroom and later fantasy/village/night/water families as prioritized.

---

# 6. Storage and metadata

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

Reusable assets record at least:

- semantic ID;
- source/master path;
- family;
- `concept | candidate | approved | superseded | rejected`;
- provenance/license;
- intended scale range where relevant;
- alpha requirement;
- parallax/layer role where relevant;
- optional ambient-motion role;
- optional theme variants.

Presence in Git never means approved.

---

# 7. Production and review loop

For every asset family:

1. define a bounded asset list;
2. make individual source assets;
3. render/review assets individually;
4. inspect against neutral/light/dark representative grounds;
5. fix weak assets instead of masking them in a composition;
6. record metadata/provenance;
7. approve a coherent subset;
8. compose a small reference scene/UI only from coherent pieces;
9. test layering/parallax/subtle motion where relevant;
10. integrate only through accepted Greia platform seams.

HTML/browser files are allowed only as focused proofs using real reusable assets. They are not deliverable "presentations" and do not create platform authority.

---

# 8. Current checkpoint

| Field | Current state |
|---|---|
| Active focus | **V2A forest/meadow finishing + V3 shared UI kit in parallel** |
| Environment pack | `assets/visual/environments/forest_meadow/v0.2/` — 27 reusable SVG masters |
| Environment proof | `composition_day.toml` + `parallax_proof.html` use the same committed masters |
| UI pack | `assets/visual/ui/v0.1/` — first shared component/shadow/highlight tranche committed |
| Evidence | **SOURCE + DESKTOP VISUAL REVIEW** only; all current environment/UI art remains candidate |
| Current quality rule | individual assets must survive review before composition; compositions may not conceal weak assets |
| Runtime boundary | both catalogs remain `runtime_consumed = false`; no new loader/framework is authorized here |
| Next exact action | complete the missing UI state/illustration masters and 800×600/1024×600 UI review, while doing one final restraint/readability pass on the forest composition; then start Workshop v0.1 individual assets |

---

# 9. Milestones

## V1 — Character/style seed **[SUFFICIENT TO UNBLOCK LIBRARY]**

- [x] simplified character direction;
- [x] Lilli/Nino/Tito/Momo seed cast;
- [ ] continue useful expression/motion refinement without blocking wider art.

## V2 — Composable environment foundation **[ACTIVE / FIRST PACK SUBSTANTIALLY BUILT]**

- [x] forest/meadow candidate asset pack;
- [x] light/shadow/atmosphere/FX primitives;
- [x] semantic metadata/provenance seed;
- [x] individual visual review + weak-asset revisions;
- [x] layered composition manifest/proof;
- [x] cheap parallax/ambient-motion proof source;
- [ ] final 800×600/1024×600 restraint/readability review;
- [ ] owner approval/revision when appropriate.

## V3 — Shared UI visual kit **[ACTIVE]**

- [x] first panels/cards/buttons/tabs/badges/progress/bubbles/frames tranche;
- [x] common shadow/highlight/focus pieces;
- [x] first light/sky/dark desktop review;
- [ ] missing hover/press/disabled/favorite/complete states;
- [ ] loading/error/empty-state illustration pieces;
- [ ] low-resolution reference composition;
- [ ] owner approval/revision when appropriate.

## V4 — Additional environment packs

- [ ] workshop;
- [ ] clinic;
- [ ] reading/classroom;
- [ ] later fantasy/village/night/water families.

## V5 — Shared consumption/integration

- [ ] explicit catalog/consumption seam through accepted architecture;
- [ ] bounded loading/caching;
- [ ] Shell + Activities reuse the same assets/components;
- [ ] simulator/physical low-resource acceptance where implementation claims require it.

---

# 10. Failure patterns — do not repeat

- spending the whole workstream on character minutiae;
- detailed traditional rigs as the default;
- one-shot sprite sheets assumed production-ready;
- degrading approved character art with fake overlays/redraws;
- calling a non-blinking animation `blink`;
- crude primitive trees/backgrounds presented as a visual redesign;
- full-screen mockups before a real asset library exists;
- decorative HTML that makes weak assets look busier instead of better;
- inventing new runtime/UI architecture during art production.

---

# 11. Progress log — append only

## 2026-08-20 — constraint-native visual pivot

- Simplified expressive characters established as practical direction.
- Lilli, Nino, Tito, Momo became the working core cast.
- Detailed quadruped/sprite-sheet/automatic-rig approaches retained as rejected defaults.

## 2026-08-20 — drift corrected

- Character motion work expanded too far and produced regressions.
- A crude UI/background HTML prototype was rejected.
- Workstream corrected to high-quality single assets first, followed by composition/parallax/light/shadow/UI.

## 2026-08-20 — forest/meadow v0.2 committed

**Files:** `assets/visual/environments/forest_meadow/v0.2/`

- created 27 reusable SVG masters across trees, foliage, props, background, ground, light/fog, shadows and ambient FX;
- added semantic catalog with parallax/ambient roles and provenance seed;
- rendered/inspected the candidate pack;
- revised weak sapling, distant tree line, fog and dust-mote treatments.

**Evidence:** SOURCE + DESKTOP VISUAL REVIEW only.

**Commits:**
- `ee1faa2056156d756d233f01e7b46cdde2c1e4f3` — initial pack
- `eefb9db344ab59aa25be0f341e34e4ecb777a517` — review refinements

## 2026-08-20 — composition/parallax proof and shared UI v0.1

**Environment work:**
- committed `composition_day.toml` with explicit far/mid/near/overlay layer roles;
- committed `parallax_proof.html` using only real pack SVGs and cheap CSS motion;
- added `REVIEW.md` recording actual review scope and boundaries.

**UI work:**
- created first reusable UI pack under `assets/visual/ui/v0.1/`;
- added panels, cards, buttons, tabs, badges, progress, bubbles, reward/avatar frames, focus, shadow and sheen masters;
- added semantic catalog and review record;
- desktop-reviewed representative pieces on cream, sky and dark grounds.

**Evidence:** SOURCE + DESKTOP VISUAL REVIEW only. No runtime/hardware/owner approval claim.

**Commits:**
- `70e9980392cb873fc1b4aab1234c75dd18ac4f3e` — shared UI pack + scene composition manifest
- `873d228c14539da1daf040949431b51ad8ed221a` — parallax proof + review records

**Next exact action:** finish missing UI states/illustration pieces and low-resolution review, do one final restraint/readability pass on the forest proof, then start the Workshop v0.1 individual asset pack.
