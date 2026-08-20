# Greia Constraint-Native Character Grammar

**Status:** accepted visual-design grammar; A1 closed at static/design scope  
**Date:** 2026-08-20  
**Active plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Authoring skill:** `skills/greia-visual-authoring/SKILL.md`  
**Evidence scope:** DESIGN SPEC + SOURCE + DESKTOP VISUAL REVIEW + OWNER REVIEW; no runtime/physical acceptance implied

## 1. Purpose

This document makes the Greia character direction concrete enough that another model or contributor can build a recognizably Greia character without inventing a new art language or requiring traditional articulated anatomy.

The key rule is:

> **Character identity comes from silhouette + face + two or three strong cues. Character life comes from expression + whole-body motion.**

The target is not the fewest shapes possible. The target is the **smallest construction that still looks charming, intentional, tactile and alive**.

The A1 static cast review established this grammar as the accepted default direction. The current specimens are style anchors, not a claim that every present SVG is a frozen release asset.

## 2. Reference artboard and occupancy

Use a 256 × 256 logical reference artboard for reusable character masters and review.

Recommended neutral-pose occupancy:

- character height excluding ground shadow: about **68–80%** of the artboard;
- character width excluding optional tail/side attachments: about **48–68%**;
- keep at least **12 px** safe margin around ordinary identity attachments;
- the baseline/feet should normally sit around **80–86%** of artboard height;
- the face should remain inside the central safe area so 64/128 px crops do not destroy expression.

These are design targets, not a runtime coordinate API.

## 3. Edge and outline language

Greia character outlines should feel soft and illustrated rather than like thick coloring-book ink.

At a 256 px master:

- primary outer contour: **3–4 px**;
- secondary internal contour: **2–3 px**;
- rounded joins and caps;
- default outline should be a **tinted dark** related to Greia cocoa/plum/navy, not pure black;
- avoid doubled outlines, hairline micro-detail, or heavy 6–10 px borders.

A character may omit explicit outline on some large internal patches when contrast is already clear.

At 64 px, preserve silhouette and face rather than mechanically preserving every internal stroke.

## 4. Fill and depth language

Default character rendering should use:

- one dominant body fill;
- one or two identity/accent colors;
- optional one highlight color;
- one readable dark eye/mouth tone;
- optional blush/cheek tone.

Depth should come from **broad treatment**, not detailed painting.

Preferred:

- flat fill;
- or a restrained two-stop gradient across the main body;
- one broad highlight/belly/muzzle patch;
- one or two simple shadow patches;
- separate low-opacity ground shadow.

Avoid:

- realistic fur rendering;
- glossy 3D plastic shading;
- many tiny highlights;
- airbrushed painterly texture that cannot survive 128/64 px;
- gradients on every small part.

### Ground shadow

A reusable character may include or request a separate ground-shadow layer:

- broad ellipse;
- about **35–55%** of character width;
- about **6–10%** of character height;
- opacity roughly **8–15%**;
- no blur is required for the C0 visual language.

The shadow is a staging aid, not part of identity.

## 5. Shape language

### 5.1 Puff

Puff is a round/oval soft mass, but **not necessarily a mathematically perfect circle**.

Good options:

- slightly egg-shaped;
- subtly flattened bottom;
- 4–10 large soft scallops for a fluffy variant;
- one deliberate asymmetry.

Do not imitate fur by adding dozens of tiny spikes.

### 5.2 Bean

Bean is vertically oriented and compact.

Good options:

- rounded drop;
- broad upper half tapering slightly toward feet;
- mild left/right asymmetry;
- wing/flap shapes attached to the sides.

Bean should still be readable as one dominant mass.

### 5.3 Cutout Critter

Cutout Critter uses a deliberately flat felt/sticker/paper-cut logic.

Budget:

- **2–5 large silhouette layers**;
- strong overlap;
- almost no pseudo-anatomical modeling;
- no attempt to fake a complex 3D body with many thin vector pieces.

Flatness is intentional here, not a missing feature.

### 5.4 Object Friend

The pedagogical object stays primary.

Rules:

- preserve at least roughly **70% of the object/glyph silhouette** unobscured;
- face occupies a secondary area and must not make the learning object ambiguous;
- appendages are tiny and optional;
- avoid turning a number/letter/tool into a generic blob wearing the object as decoration.

The child should recognize the object before reading the face.

## 6. Face grammar

The face is the most important reusable character subsystem.

At 256 px:

- the face should normally occupy the central **45–60%** of the main body width;
- the eye pair should be large enough to remain legible at 64/128 px;
- individual eyes are commonly around **7–11% of body width**;
- leave generous whitespace around the eyes;
- mouth width is usually around **10–22% of body width**;
- cheeks/blush are broad soft patches, not tiny dots.

Default eye treatment:

- dark cocoa/plum/navy rather than pure black;
- one simple highlight per eye;
- no detailed irises required;
- asymmetry is allowed when it adds character without looking broken.

Default mouth treatment:

- one strong curve or simple open-mouth mass;
- avoid lips, teeth detail, tongue detail except one large readable comic cue;
- expression must remain readable after downscaling.

For emotion rules and semantic face states, continue into `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`.

## 7. Identity-cue budget

A default Greia character gets **up to three identity attachment groups** beyond its body/face.

Examples:

- unicorn: horn + ears + rainbow tuft;
- fox: ears + tail + muzzle/chest patch;
- owl: ear tufts + wings + beak/mask;
- monster: antennae + fluff silhouette + spots;
- rabbit: ears + tiny tail + muzzle;
- cat: ears + whisker cue + tail.

Pairs that function as one semantic cue may count as one group (for example, two ears).

This is not a validator. It is a complexity discipline.

## 8. Species simplification

Do not ask the character to prove its species through full anatomy.

Prefer strong cues:

- unicorn → horn, ear shape, rainbow cue, tiny hoof-like feet;
- fox → triangular ears, cream muzzle/chest, chunky tail;
- owl → eye mask, beak, wing flaps, upright bean body;
- cow → rounded horns/ears, spots, tiny hoof cue;
- frog → high-set eyes, green puff, simple mouth, maybe tiny side feet;
- dog → floppy ears, muzzle patch, tail cue.

If the species is not readable without realistic legs, simplify the visual brief before adding anatomy.

## 9. Interior-detail budget

At 256 px, a default reusable character should normally have no more than:

- 1 broad face/muzzle/belly patch;
- 0–5 small decorative marks/spots;
- 0–2 extra broad highlight/shadow shapes.

A minor detail that is smaller than about **5 px** at the 256 master should be treated skeptically unless it is essential.

The goal is to keep the 64/128 px versions from turning muddy.

## 10. Color discipline

Use `runtime/theme-defaults.toml` as the harmony anchor, not as a requirement that every character literally uses system theme colors.

Recommended discipline:

- 1 dominant body color;
- 1–2 identity accents;
- optional 1 highlight;
- dark readable face tone;
- blush tone only where useful.

Good Greia-adjacent anchor colors include:

- sunshine `#FFC234`;
- coral `#F46F61`;
- leaf `#59B86A`;
- ocean `#4A91D8`;
- grape `#9464C9`;
- raspberry `#D85683`;
- orange `#F39A38`;
- turquoise `#44B8AE`;
- cocoa `#3D2C1F`.

A rainbow identity cue should be localized. It should not turn the whole character into a seven-color surface.

## 11. “Economical” versus “placeholder”

### Appropriately economical

A production-intent simple character still has:

- deliberate silhouette;
- controlled outline;
- one coherent material/depth treatment;
- a large expressive face;
- species/role cues;
- intentional asymmetry or shape variation;
- small-size readability.

### Placeholder/debug look

Reject a candidate that is effectively:

- a perfect circle plus two dots and a smile with no identity shaping;
- raw Pygame primitives with default colors and no visual hierarchy;
- a pile of unrelated geometric parts;
- over-thick black outline around flat fills;
- emoji copied as the character art;
- detail added randomly because the base silhouette is weak.

**Simple is a style. Unconsidered is a placeholder.**

## 12. Core static style anchors

The first owner-reviewed static anchors are:

### Lilli — unicorn Puff

- warm cream Puff;
- localized three-color rainbow forelock;
- golden horn;
- tiny pink hoof cues;
- soft pink cheeks;
- small flank star may be retained if it stays readable and does not compete with the face;
- personality: wonder, kindness, imagination.

### Nino — owl Bean

- warm brown Bean;
- light eye-mask/belly treatment;
- very large eyes;
- orange beak/feet;
- side wing flaps rather than articulated wings;
- one turquoise learning/curiosity accent allowed;
- personality: observation, books, thoughtfulness.

### Tito — fox Puff

- orange Puff;
- triangular ears;
- cream muzzle/chest patch;
- chunky one-piece tail;
- tiny cream paw cues;
- personality: curiosity, exploration, playful cleverness.

### Momo — friendly monster Puff

- purple fluffy/scalloped Puff;
- two antennae with intentionally mismatched tips;
- stub arms;
- turquoise feet;
- a few large spots only;
- one tiny tooth allowed as a readable comic cue;
- personality: humor, emotion, experimentation.

These anchors establish a visual family. Future refinement is expected; they are not a requirement to clone or recolor the same body for every character.

## 13. Small-size review

For every reusable character candidate:

### 256 px

Review design quality:

- silhouette;
- balance;
- material/depth treatment;
- expression;
- attachment count;
- awkward tangencies.

### 128 px

Review actual intended UI readability:

- face remains immediately readable;
- species/role still obvious;
- interior patches do not merge;
- outline is not too heavy.

### 64 px

Review icon/avatar survival:

- silhouette remains distinct;
- eyes are still visible;
- identity cue is still visible;
- nonessential detail may disappear cleanly rather than becoming noise.

If a character fails at 64 px but will never be used that small, document the supported minimum instead of mutilating the larger design.

## 14. A1 specimen set and approval scope

The A1 source specimens are stored under:

```text
assets/visual/specimens/a1/
```

Files:

```text
lilli.svg
nino.svg
tito.svg
momo.svg
cutout_critter.svg
object_friend_3.svg
review.html
```

Lilli, Nino, Tito and Momo were owner-reviewed and accepted on 2026-08-20 as **static style anchors / design direction**. `cutout_critter.svg` and `object_friend_3.svg` remain archetype examples.

This approval does **not** mean:

- the current SVGs are frozen final release art;
- a runtime asset-loader contract exists;
- expression/motion work is complete;
- simulator or physical C0/Acer/Pi acceptance exists.

## 15. A1 closure boundary

A1 closed on 2026-08-20 after:

1. static owner review of Lilli, Nino, Tito and Momo;
2. acceptance of the constraint-native construction grammar;
3. promotion of the accepted language into `GREIA_VISUAL_STYLE_GUIDE.md`;
4. explicit library status update at static-style-anchor scope.

A2 owns expression and motion standardization. Runtime integration remains a later architecture-reviewed phase.
