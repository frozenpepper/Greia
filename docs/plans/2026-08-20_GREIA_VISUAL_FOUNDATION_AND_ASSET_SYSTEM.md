# Greia Visual Foundation and Asset System — Active Art Workstream Plan

**Status:** ACTIVE ART/VISUAL WORKSTREAM  
**Date:** 2026-08-20  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`

This plan owns the current Greia art/visual workstream.

The goal is **not** to make isolated mock screens. The goal is to build a **high-quality reusable visual library** that Greia can compose into many Shell screens and Activities.

The production model is:

> **excellent individual assets → reusable asset packs → layered composition → subtle motion/light/shadow → shared UI system**

Characters are one part of that library, not the whole project.

---

# 1. Non-negotiable direction

Greia visuals must be built from reusable, attractive source assets that look intentional **on their own** and become richer when composed.

## 1.1 Asset-first, not mock-scene-first

Before building a scene family, create and approve the reusable pieces that compose it.

Examples:

- trees;
- bushes;
- flowers;
- rocks;
- logs;
- clouds;
- hills/mountains;
- grass/ground edges;
- houses/castles;
- furniture;
- clinic/workshop props;
- shadow decals;
- fog/light overlays;
- fireflies/sparkles/dust;
- UI panels/cards/buttons/badges/icons.

A crude full-screen mock-up is **not** evidence that the asset system works.

## 1.2 Quality target

The simplification strategy applies mainly to reproducibility and animation complexity. It does **not** mean low-quality flat primitives.

Individual assets should aim for:

- polished storybook/toy-diorama quality;
- attractive silhouettes;
- controlled texture/detail;
- soft but visible depth;
- coherent warm lighting;
- useful local highlights and cast/contact shadows;
- visual richness that survives composition;
- transparency/clean edges where the asset is composable;
- consistency with the Greia palette without forcing every asset to use identical colors.

Raw circles/rectangles/tutorial trees are prototype/debug art only.

## 1.3 Scenes are compositions

A normal Greia environment should be assembled from multiple reusable layers, not baked as one giant background whenever avoidable.

Typical layer model:

1. **sky / room-base layer**;
2. **far background** — mountains, distant forest, distant buildings;
3. **mid background** — hills, tree line, room walls/furniture mass;
4. **playfield / ground**;
5. **interactive prop layer**;
6. **foreground framing** — foliage, shelves, curtains, etc.;
7. **atmosphere/light layer** — rays, fog, dust, glows;
8. **character/UI layer**.

Not every scene needs all eight layers.

## 1.4 Parallax and subtle life

Where useful, scene layers should support inexpensive parallax and restrained ambient animation.

Examples:

- clouds drifting very slowly;
- far/mid/foreground moving at different ratios;
- grass/bush/tree tips swaying a few pixels/degrees;
- fireflies appearing/fading;
- dust motes drifting;
- water shimmer;
- warm light rays breathing slightly;
- foreground shadow/light shifts;
- tiny prop idles.

The visual result should feel alive without turning the C0 device into an animation workload.

## 1.5 Lighting and shadow are shared visual assets

Depth should not be reinvented independently inside every Activity.

The shared library should include reusable treatments such as:

- soft ground/contact shadows;
- object shadow decals;
- warm/cool glow overlays;
- window/sun light shafts;
- foreground vignette/framing shadows;
- ambient fog/haze strips;
- sparkle/discovery/reward light effects.

---

# 2. Character library

Working core cast:

- **Lilli** — unicorn Puff;
- **Nino** — owl Bean;
- **Tito** — fox Puff;
- **Momo** — friendly monster Puff.

The accepted simplified-character direction remains valid: clear silhouette, expressive face, simple body, cheap whole-body motion.

Shared base motions remain:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Rules:

- motion must preserve the same character artwork;
- `blink` must actually blink;
- expression changes must not degrade the approved character design;
- character work may continue, but it must **not block** development of the wider asset/UI/background library.

---

# 3. Reusable environment asset library

Build environment packs from reusable individual assets.

## 3.1 Forest / meadow pack — first target

Create polished reusable assets, initially including:

- 2–3 large tree variants;
- 3 bush/foliage variants;
- grass edge / ground patch variants;
- 2 rock clusters;
- 1 fallen log;
- mushroom/flower clusters;
- 2 cloud variants;
- distant hill / mountain silhouettes;
- distant tree-line layer;
- warm sunlight shaft overlay;
- soft fog/haze strip;
- contact-shadow assets;
- fireflies/sparkles/ambient particles.

Only after these pieces are visually strong should they be composed into meadow/forest scene examples.

## 3.2 Indoor packs

After the first outdoor pack:

### Workshop / creative room

- workbench/table;
- shelves;
- paper/paint/brush/pencil props;
- blocks/tools;
- lamp/window light;
- rugs/storage boxes;
- wall/room base layers.

### Clinic / care room

- bed/cushion;
- cabinet/shelf;
- bowls/bottles/bandage/toy medical props;
- rug;
- window/light layer;
- soft heart/care FX.

Additional families later: reading corner, fantasy/castle, night/sky, pond/water, village.

---

# 4. Shared UI visual library

Greia already has semantic UI architecture. This workstream supplies the polished visual pieces and states.

Create reusable families for:

- primary / secondary / quiet buttons;
- icon buttons;
- activity cards;
- profile/avatar frames;
- panels and sheets;
- tabs/category pills;
- selected/focused/hovered/pressed states;
- new/completed/favorite/locked badges;
- progress bars/pills;
- speech/thought/help bubbles;
- reward/badge popups;
- loading/error/empty-state illustration pieces;
- category/location portal art;
- subtle shadows, highlights and decorative trims.

## 4.1 UI depth/motion

Shared UI motion vocabulary:

- hover/focus: tiny lift + shadow/highlight change;
- press: small squash/depress;
- launch: short bounce/squiggle/pop while loading;
- selected: clearer frame/glow/depth, not color alone;
- reward: sparkle + pop;
- gentle error/wrong choice: small wobble, never alarming shake.

UI pieces must remain readable and performant at 800×600 / 1024×600.

---

# 5. Asset storage and metadata

The library is organized semantically. Exact runtime-loading architecture remains source-owned and is not invented by this plan.

Conceptual source tree:

```text
assets/visual/
  characters/
  environments/
    forest/
    meadow/
    workshop/
    clinic/
  props/
  atmosphere/
  fx/
  ui/
  shadows/
  specimens/
  catalog/
```

Each reusable asset should record at least:

- semantic ID;
- source/master path;
- asset family;
- status: `concept | candidate | approved | superseded | rejected`;
- provenance/license;
- intended scale range;
- whether alpha/transparency is required;
- optional animation/parallax role;
- optional theme variants.

Presence in Git does not mean approved.

---

# 6. Production / review workflow

For each asset family:

1. define a short asset list;
2. create the **individual high-quality assets**;
3. visually review them individually on neutral/light/dark sample grounds;
4. fix weak assets instead of hiding them in a composition;
5. approve a coherent pack;
6. compose a small reference scene/UI using only approved pieces;
7. test layering/parallax/subtle animation where relevant;
8. only then integrate into Shell/Activities.

Do **not** spend time making decorative HTML presentations of low-quality placeholder content.

HTML/browser review is useful only when it demonstrates actual reusable assets or interaction states that are already worth reviewing.

---

# 7. Current checkpoint

| Field | Current state |
|---|---|
| Active focus | **V2 — high-quality composable asset foundation** |
| Character status | Lilli/Nino/Tito/Momo establish the simplified Greia character direction; character refinements continue but are no longer the only visual task |
| First environment pack | **forest / meadow reusable asset pack** |
| First UI work | reusable panels/cards/buttons/badges/shadows after the first outdoor asset tranche begins |
| Current required output | actual reusable transparent/vector assets, not crude full-scene mockups |
| Composition target | layered scenes with far/mid/playfield/foreground/atmosphere planes, optional parallax, subtle animation, reusable light/shadow assets |
| Current evidence | character direction only; no environment/UI pack is approved yet |
| Next exact action | create the first polished forest/meadow single-asset tranche: hero tree, secondary tree, bush, rock/log cluster, cloud, ground/grass edge, sunlight/fog overlay, contact shadow and firefly FX; review assets individually before composing a scene |

---

# 8. Near-term milestones

## V1 — Character/style seed **[STARTED / sufficient to unblock wider library]**

- [x] simplified Greia character direction established;
- [x] Lilli/Nino/Tito/Momo seed cast;
- [ ] continue expression/motion refinements as useful;
- [ ] do not block other visual-library work on perfect character completion.

## V2 — Composable artwork foundation **[ACTIVE]**

- [ ] first forest/meadow individual-asset pack;
- [ ] reusable light/shadow/atmosphere/FX primitives;
- [ ] asset metadata/provenance;
- [ ] individual asset review;
- [ ] one layered forest/meadow composition using approved assets;
- [ ] parallax/subtle ambient-motion proof using the approved layers.

## V3 — Shared UI visual kit

- [ ] panels/cards/buttons/tabs/pills;
- [ ] visual states;
- [ ] common shadows/highlights;
- [ ] reward/help/error UI art;
- [ ] launch/hover/press/selection motion treatment;
- [ ] launcher/Activity reference compositions using the real kit.

## V4 — Additional environment packs

- [ ] workshop;
- [ ] clinic;
- [ ] reading/classroom;
- [ ] fantasy/village/night/water as prioritized.

## V5 — Shared consumption/integration

- [ ] explicit catalogue/consumption seam through accepted platform architecture;
- [ ] bounded loading/caching;
- [ ] Shell + Activities reuse the same assets/components;
- [ ] no random per-Activity visual systems;
- [ ] simulator and physical low-resource acceptance where implementation claims require it.

---

# 9. Failure patterns — do not repeat

- detailed traditional character rigs as the default solution;
- one-shot AI sprite sheets assumed production-ready;
- programmatic recreations that visibly degrade approved character art;
- fake face overlays that make characters worse;
- calling a non-blinking animation `blink`;
- crude circles/rectangles/tutorial trees presented as the new Greia art direction;
- full-screen scene mockups made from weak primitives before a real asset library exists;
- decorative HTML presentations that hide the fact that the underlying assets are not good enough;
- spending the whole visual workstream on characters while backgrounds, props, light, shadow, FX and UI remain untouched.

---

# 10. Progress log — append only

## 2026-08-20 — visual pivot established

- Constraint-native simplified characters accepted as the practical default direction.
- Working cast: Lilli, Nino, Tito, Momo.
- Detailed quadruped/sprite-sheet/automatic-rig approaches retained as rejected defaults.

## 2026-08-20 — character work over-expanded and drifted

- Work spent too long on character motion review harnesses.
- A face-overlay A2 demo degraded Nino and introduced an inappropriate Object Friend example.
- A later correction preserved the A1 characters but still failed to implement a true blink.
- These are retained as lessons, not direction-setting successes.

## 2026-08-20 — crude UI/background HTML rejected

- A launcher/background/UI HTML prototype used low-quality primitive scene art.
- Owner rejected it correctly because it moved **away** from the intended high-quality composable asset system.
- The underlying mistake was scene-first placeholder drawing instead of asset-first production.
- This plan was corrected to make **high-end reusable individual assets, layered composition, parallax, subtle animation, light and shadows** explicit.

### Next exact action

Produce and review the first real forest/meadow single-asset tranche before composing another scene.
