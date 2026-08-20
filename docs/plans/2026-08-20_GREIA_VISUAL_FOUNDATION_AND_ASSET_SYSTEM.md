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

A scene family starts with reusable individual source assets that are worth keeping on their own.

Examples:

- trees, bushes, flowers, rocks, logs, clouds, hills, tree lines, grass/ground pieces;
- workshop/clinic furniture and props;
- shadow decals, light shafts, fog/haze, fireflies, dust, sparkles;
- UI panels, cards, buttons, badges, frames, icons and trims.

Weak primitives do not become acceptable because they are hidden inside a scene.

## 1.2 Quality target

Assets should aim for polished storybook / toy-diorama quality:

- attractive silhouette;
- warm coherent palette;
- controlled gradients/detail;
- soft local highlights;
- visible but restrained depth;
- clean alpha edges;
- reusable contact/cast shadow treatment;
- readable at low resolution;
- simple enough to remain viable on Greia's low-resource targets.

Raw tutorial circles/rectangles/polygon scenery are prototype/debug art only.

## 1.3 Layered composition

Normal environment composition should separate useful planes:

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

No scene requires every effect. Static meaning and visual quality remain primary.

---

# 2. Character library

Core cast remains:

- **Lilli** — unicorn Puff;
- **Nino** — owl Bean;
- **Tito** — fox Puff;
- **Momo** — friendly monster Puff.

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

# 3. Environment packs

## V2A — Forest / meadow **[ACTIVE]**

Canonical candidate pack:

```text
assets/visual/environments/forest_meadow/v0.2/
```

Current source inventory:

- 4 tree variants;
- 3 bush variants;
- fern cluster;
- flower patch;
- mushroom cluster;
- 2 rock clusters;
- fallen log;
- stump;
- 2 cloud variants;
- distant hills;
- distant tree line;
- grass edge;
- dirt playfield patch;
- sunlight rays;
- fog strip;
- small/wide contact shadows;
- fireflies;
- dust motes;
- falling leaves.

The pack has explicit semantic IDs, candidate status, parallax role and ambient-motion metadata in:

```text
assets/visual/environments/forest_meadow/v0.2/catalog.toml
```

All assets are still **candidate**, not approved release art and not runtime-authority assets.

### Current review result

Desktop visual review of the v0.2 contact sheet found the first pass materially better than the rejected primitive scene work. Weak first-pass assets were revised immediately rather than hidden in composition:

- sapling silhouette/details refined;
- distant tree line changed from repetitive geometric triangles to a more organic mixed canopy;
- fog changed to layered wisps;
- dust motes given visible soft glow treatment.

### Next exact V2A work

1. continue individual review of the pack on light + dark + representative sky/ground backgrounds;
2. revise/reject any remaining weak assets;
3. add any missing composition-critical outdoor pieces only where needed;
4. approve a coherent subset;
5. **then** make one layered forest/meadow composition using only that subset;
6. test cheap far/mid/near parallax, cloud/fog drift, foliage sway and light/FX restraint;
7. do not turn the composition proof into a new private scene system.

## V2B — Workshop / creative room

After the outdoor pack is coherent:

- workbench/table;
- shelves;
- paper/paint/brush/pencil props;
- blocks/tools;
- rug/storage;
- window/lamp/light assets;
- wall/base layers.

## V2C — Clinic / care room

- bed/cushion;
- cabinet/shelf;
- bowls/bottles/bandages/toy-care props;
- rug;
- window/light assets;
- heart/care FX;
- room-base layers.

---

# 4. Shared UI visual kit — V3

The semantic UI architecture already exists; this work supplies reusable visual assets/states.

Required families:

- primary / secondary / quiet buttons;
- icon buttons;
- activity cards;
- profile/avatar frames;
- panels/sheets;
- tabs/category pills;
- selected/focused/hovered/pressed states;
- new/completed/favorite/locked badges;
- progress bars/pills;
- speech/thought/help bubbles;
- reward/badge popups;
- loading/error/empty-state pieces;
- category/location portal art;
- shared shadows/highlights/trims.

UI motion language:

- focus/hover: tiny lift + shadow/highlight change;
- press: restrained depress/squash;
- selected: stronger frame/depth, not color alone;
- launch: short bounce/squiggle/pop while loading;
- reward: sparkle + pop;
- gentle wrong choice: small wobble, never alarming shake.

V3 starts after the first V2 outdoor tranche is visually coherent; it should then progress in parallel with later environment packs.

---

# 5. Storage and metadata

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
- intended scale range;
- alpha requirement;
- parallax/layer role where relevant;
- optional ambient-motion role;
- optional theme variants.

Presence in Git never means approved.

---

# 6. Production and review loop

For every asset family:

1. define a bounded asset list;
2. make individual source assets;
3. render/review assets individually;
4. inspect against neutral/light/dark representative grounds;
5. fix weak assets instead of masking them in a composition;
6. record metadata/provenance;
7. approve a coherent subset;
8. compose a small reference scene/UI only from approved pieces;
9. test layering/parallax/subtle motion where relevant;
10. integrate only through accepted Greia platform seams.

HTML/browser demos are allowed only when they demonstrate real reusable assets or real interaction states that are already worth reviewing.

---

# 7. Current checkpoint

| Field | Current state |
|---|---|
| Active focus | **V2A — forest/meadow reusable asset pack** |
| Current pack | `assets/visual/environments/forest_meadow/v0.2/` |
| Pack size | **27 reusable SVG masters + catalog + README** |
| Current evidence | **SOURCE + DESKTOP VISUAL REVIEW**; candidate only |
| Strong direction | layered storybook/toy-diorama assets, warm light, reusable shadows/atmosphere, explicit far/mid/near/overlay roles |
| Current correction | weak sapling/tree-line/fog/dust assets already revised after visual review |
| Next exact action | finish individual v0.2 review/refinement, then create the first layered forest/meadow composition and cheap parallax/ambient-motion proof from the approved subset |
| UI | **V3 queued immediately after first coherent outdoor subset; do not postpone it behind endless character work** |
| Runtime | asset metadata remains non-runtime authority; no new loader/framework invented here |

---

# 8. Milestones

## V1 — Character/style seed **[SUFFICIENT TO UNBLOCK LIBRARY]**

- [x] simplified character direction;
- [x] Lilli/Nino/Tito/Momo seed cast;
- [ ] continue useful expression/motion refinements without blocking wider art.

## V2 — Composable artwork foundation **[ACTIVE]**

- [x] first forest/meadow candidate asset pack committed;
- [x] light/shadow/atmosphere/FX candidate primitives committed;
- [x] semantic metadata/provenance seed committed;
- [x] first individual visual review and weak-asset revision pass;
- [ ] finish individual pack review;
- [ ] approve coherent subset;
- [ ] layered forest/meadow composition;
- [ ] cheap parallax/subtle ambient-motion proof.

## V3 — Shared UI visual kit **[NEXT]**

- [ ] buttons/cards/panels/tabs/pills;
- [ ] focus/hover/press/selected states;
- [ ] badges/progress/help/reward/error assets;
- [ ] common shadows/highlights/trims;
- [ ] low-resolution reference compositions.

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

# 9. Failure patterns — do not repeat

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

# 10. Progress log — append only

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

**Work:**
- created 27 individual SVG masters covering trees, foliage, props, sky/background, ground, light/fog, shadows and ambient FX;
- added semantic catalog with parallax/ambient roles and provenance seed;
- rendered/inspected a desktop contact sheet;
- revised weak sapling, distant tree line, fog and dust-mote treatments after review.

**Evidence:** SOURCE + DESKTOP VISUAL REVIEW only.

**Commits:**
- initial v0.2 pack: `ee1faa2056156d756d233f01e7b46cdde2c1e4f3`
- visual-review refinements: `eefb9db344ab59aa25be0f341e34e4ecb777a517`

**Next exact action:** finish individual v0.2 review/refinement and then build the first layered forest/meadow composition/parallax proof from the accepted subset.
