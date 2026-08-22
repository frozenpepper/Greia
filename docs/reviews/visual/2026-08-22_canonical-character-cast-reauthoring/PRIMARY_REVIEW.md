# Primary Review — Canonical Character Cast Reauthoring

**Date:** 2026-08-22  
**Candidate commit reviewed:** `59336d1c34e119e04c40b32f2c1901e1dbfb1b60`  
**Candidate source:** `assets/visual/pack_candidates/canonical_characters/2026-08-22/`  
**Evidence reviewed:** all 13 PNGs from `GREIA_VISUAL_REVIEW_CANONICAL_CHARACTER_CAST_2026-08-22.zip` plus `REVIEW.md` and `audit.json`

## 1. Verdict

The four-character candidate is a **successful state-system and motion-design foundation**, but it should **not be promoted as the final canonical cast yet** because the owner has now expanded and clarified the cast system.

Carry the following forward without another broad redraw:

- **Lilli** — current candidate is a stable visual anchor;
- **Tito** — current candidate is a stable visual anchor;
- **Momo** — current candidate is a stable visual anchor;
- **Nino owl artwork** — useful visual starting point only; the current cast direction renames/refines the owl as **Leo** and adds signature glasses.

The next visual gate is therefore a **bounded cast expansion/refinement**, not a promotion gate for the old four-character lineup and not another generic-art batch.

## 2. What the pixels actually support

### 2.1 Strengths

- The cast is immediately readable as one family at 256 and 128 px.
- Lilli, Tito and Momo keep distinct silhouettes and color identities at 64 px.
- The five authored states (`neutral`, `blink`, `happy`, `surprised`, `sleepy`) are clearly registered and avoid body-position jumps.
- `happy` and `surprised` are especially strong across the current cast.
- Whole-character motion storyboards are compatible with the existing cheap semantic-motion architecture.
- The source-component approach is useful at **authoring time** and does not imply a runtime bone/limb rig.

### 2.2 Important cautions

The producing-agent statement that the character art now matches the recent generic-library craft level should be read narrowly. The characters remain intentionally **clean, economical mascot/vector forms**, not materially rich environment paintings. That is acceptable because the accepted character grammar prioritizes silhouette, face, low-resolution readability and cheap state swapping.

At 64 px, the overall characters remain recognizable, but not every expression has equal separation. The current owl's white eye disks dominate its face, so `blink`, `happy` and `sleepy` converge more than the larger sheets suggest. This matters directly for the Leo refinement: adding glasses on top of the existing ringed eye treatment could create a cluttered double-ring/goggle face unless the eye-mask/glasses relationship is redesigned as one system.

The motion sheets are **design/storyboard evidence**, not runtime animation acceptance. They show plausible semantic transforms; they do not prove timing, caching, interpolation or simulator behavior.

## 3. Current four-character disposition

### Lilli — carry forward

Keep the current candidate state set as the full-cast comparison anchor. The horn/forelock/cream-body silhouette remains the strongest flagship identity. Do not redraw her merely because the cast grows.

### Tito — carry forward

Keep the current candidate state set. His fox identity depends heavily on ears + tail; this is sufficiently distinct now. The new rabbit must therefore avoid becoming a Tito recolor with longer ears.

### Momo — carry forward

Keep the current candidate state set. The scalloped purple silhouette, antennae and turquoise feet give useful ensemble contrast. His large facial states read well at the supplied sizes.

### Nino — superseded as current cast identity

Do **not** promote `character.nino` as the current canonical owl identity. Preserve the source and candidate work as provenance.

The new current target is:

```text
character.leo
Display name: Leo
Species/archetype: owl Bean
Primary identity addition: simple readable glasses
```

Leo should evolve from the useful owl base rather than discard it, but the glasses must be integrated into the face architecture rather than simply drawn over the current circular eye rings.

## 4. Accepted cast-system direction

The current target ensemble is:

```text
Lilli — unicorn
Leo  — owl
Flash — rabbit
Dani  — robot
Tito  — fox
Momo  — friendly monster
```

The characters use **soft primary domains**, not exclusive silos.

Recommended product meaning:

```text
Lilli  → creativity / stories / art / imagination
Leo    → learning / reading / language / knowledge
Flash  → games / action / reflex / playful challenge
Dani   → math / logic / patterns / sequencing
Tito   → exploration / nature / discovery / investigation
Momo   → emotion / music / silly play / celebration
```

This is a lead-mascot model. A character may lead an Activity while other cast members still appear. Character identity must not become permission, package authority, or a hard navigation gate.

## 5. Relationship to Collection-first Home

Do not create six new Home categories to match six characters.

The existing platform-owned primary Collections remain:

```text
create
play
learn
explore
my_greia
```

Natural affinity is useful:

```text
Create   → Lilli often leads
Play     → Flash often leads
Learn    → Leo often leads
Explore  → Tito often leads
```

But Dani and Momo are intentionally cross-cutting:

- Dani may lead math/logic Activities inside `learn`, `play`, or both;
- Momo may lead music/emotion/silly Activities inside `create`, `play`, or other appropriate Collections;
- `my_greia` should remain child/profile-owned and may use ensemble or profile identity rather than being assigned permanently to one mascot.

Future Activity metadata may expose an optional lead/supporting cast relationship, but that is a later product/runtime gate after the six-character visual family is approved.

## 6. Character-art architecture retained

Keep the existing rule:

> **complete authored state SVGs + semantic source groups/components for authoring + cheap whole-character runtime transforms**

Do not introduce:

- skeletal animation;
- runtime body-part composition;
- dozens of limb sprites;
- frame-by-frame sprite-sheet proliferation.

The five shared visual states remain sufficient for the next gate:

```text
neutral
blink
happy
surprised
sleepy
```

The six motion names remain design targets:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

## 7. Next exact gate

Execute:

`docs/testing/2026-08-22_CANONICAL_CAST_EXPANSION_LEO_FLASH_DANI.md`

That gate must:

1. refine the owl from Nino to **Leo** with integrated signature glasses;
2. create **Flash** as a visually distinct rabbit;
3. create **Dani** as a cute, low-complexity robot;
4. preserve Lilli/Tito/Momo candidate state art unless the six-cast ensemble exposes a concrete blocker;
5. show all six together at 256/128/64 px;
6. prove silhouette and expression separation, especially Leo glasses and Flash-vs-Tito distinction;
7. demonstrate shared motion vocabulary across all six at storyboard/design scope;
8. stop for owner pixel review before any runtime promotion or character-ID migration.
