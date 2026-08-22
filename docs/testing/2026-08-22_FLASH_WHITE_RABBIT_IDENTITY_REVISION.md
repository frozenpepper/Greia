# Flash White-Rabbit Identity Revision — Final Pre-Promotion Art Gate

**Status:** EXECUTE  
**Date:** 2026-08-22  
**Owner review authority:** `docs/reviews/visual/2026-08-22_canonical-cast-expansion/PRIMARY_REVIEW.md`  
**Cast system:** `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`  
**Character grammar:** `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`  
**Motion vocabulary:** `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`

## 1. Purpose

Perform exactly one **bounded identity correction** to Flash before Greia promotes the six-character canonical cast.

The current six-character candidate is already accepted as the cast-system direction. Leo, Dani, Lilli, Tito and Momo are not open for another art pass.

The sole visual issue to solve is:

> Current Flash's raspberry body reads first as a pink/red mascot with rabbit ears. Revise him into an immediately recognizable **white/warm-white rabbit** whose broad speed/action identity is communicated by a simple colored shirt with a single lightning-bolt emblem.

This is not a new cast design exercise.

## 2. Source boundary

Preserve the prior candidate intact:

`assets/visual/pack_candidates/canonical_cast_expansion/2026-08-22/`

Create a new bounded candidate workspace:

`assets/visual/pack_candidates/flash_identity_revision/2026-08-22/`

Recommended layout:

```text
catalog.toml
README.md
flash/
  source_master.svg
  neutral.svg
  blink.svg
  happy.svg
  surprised.svg
  sleepy.svg
  components/
```

The review catalogue may reference Leo/Dani/Lilli/Tito/Momo from existing candidate work rather than copying them.

Do not overwrite historical candidate evidence.

## 3. Semantic identity

Preserve exactly:

```text
character.flash
Display name: Flash
Species: rabbit
Primary meaning: games / speed / action / reflex / playful challenge
```

Do not invent a replacement name or new character ID.

## 4. Required visual direction

### 4.1 Fur/body

Change Flash's dominant fur/body treatment to **white or warm white**.

Good direction:

- primary fur near white / soft ivory rather than strong cream-yellow;
- enough warm value variation to preserve volume on white backgrounds;
- dark warm outline remains consistent with the Greia cast;
- cheeks and muzzle may retain restrained warm/pink cues.

Do not make the body pure flat `#FFFFFF` with no internal value separation.

### 4.2 Ears

Keep the tall rabbit-ear identity.

- outer fur should follow the new white/warm-white body;
- inner ears remain clearly pink/coral;
- preserve the current directional/spring-loaded asymmetry where useful;
- ears must remain readable at 64 px.

### 4.3 Shirt

Add one **simple coral/raspberry shirt or sleeveless top** as a permanent canonical identity cue.

The shirt should:

- read as one clean torso color mass;
- avoid tiny seams, buttons, logos or clothing detail;
- not cover the face/muzzle;
- remain visible at 64 px;
- preserve enough white fur around head/ears/feet/tail that the child immediately reads "white rabbit" rather than "red character."

The previous raspberry/coral body color is a good starting family for the shirt, because it preserves continuity without keeping the entire rabbit pink.

### 4.4 Lightning bolt

Place one **large simple yellow/gold lightning bolt** on the shirt.

The bolt should:

- be readable at 128 px;
- survive as a recognizable energetic mark at 64 px where possible;
- use one simple silhouette;
- contain no text or numeral;
- communicate speed/energy/action broadly.

Use a warm Greia-compatible yellow/gold family, conceptually near the existing sunshine/gold accents.

Do not add multiple bolts or electrical FX to the neutral identity.

### 4.5 Tail / posture / face

Preserve the successful current:

- round pom-pom tail;
- spring-loaded/eager stance;
- friendly large face;
- five-state registration.

Do not redesign Flash into an anatomically detailed rabbit.

## 5. Explicit anti-clutter rule

The approved identity shorthand is intentionally only:

> **white rabbit + colored shirt + one lightning bolt + long ears + pom tail**

Do **not** add:

- racing numbers;
- controllers;
- stopwatches;
- shoes;
- shorts;
- gloves;
- headbands;
- helmets;
- capes;
- sports equipment;
- permanent speed trails;
- readable text.

Those would over-specialize him toward one Activity genre.

## 6. Lilli / Tito separation requirement

The revision must make species recognition stronger without creating a new collision.

### Against Lilli

Flash must not look like Lilli without a horn.

At minimum, preserve these distinctions:

```text
Lilli → warm cream magical Puff + horn + rainbow forelock + soft wonder posture
Flash → cleaner white rabbit + very tall ears + shirt/bolt torso + spring-loaded posture + pom tail
```

### Against Tito

Flash must remain clearly distinct from Tito by:

- long rabbit ears vs triangular fox ears;
- small pom tail vs large bushy fox tail;
- white body/shirt construction vs orange fox body;
- directional rabbit posture vs Tito's explorer stance.

## 7. State set

Reauthor exactly the same five complete registered states using the new identity treatment:

```text
neutral
blink
happy
surprised
sleepy
```

The shirt and bolt must remain registered across all five states.

Expression identity should preserve the successful prior state semantics rather than inventing a new personality.

## 8. Source-master / component rule

`source_master.svg` should expose useful semantic groups, including at least conceptually:

```text
body_fur
ears
shirt
lightning_bolt
tail
face
eyes
mouth
```

Up to 3 standalone authoring components are allowed only if genuinely useful.

Useful candidates include:

- shirt + bolt treatment;
- ears;
- blink-eye treatment.

These are authoring-time resources only. Do not create a runtime clothing/equipment system or body-part rig.

## 9. Required owner-review evidence

Create:

`docs/reviews/visual/2026-08-22_flash-white-rabbit-identity-revision/`

Required PNGs:

1. `01-old-vs-revised-flash-neutral.png` — current raspberry Flash beside revised white-shirt Flash.
2. `02-revised-flash-state-matrix.png` — all five revised states.
3. `03-six-character-revised-ensemble.png` — Lilli, Leo, revised Flash, Dani, Tito, Momo.
4. `04-lilli-flash-tito-species-separation.png` — direct three-character comparison emphasizing rabbit/unicorn/fox separation.
5. `05-revised-flash-multiscale.png` — revised Flash at 256/128/64 px.
6. `06-revised-flash-silhouette-and-color-mass.png` — silhouette plus simplified color-mass proof showing white fur vs shirt identity.
7. `07-revised-flash-expression-small-size.png` — five states at 128/64 px.
8. `08-revised-happy-hop-ensemble.png` — all six using the prior `happy_hop` storyboard with revised Flash.
9. `09-shirt-bolt-detail-crops.png` — fur/shirt/bolt/ear treatment close-up.
10. `10-source-component-structure.png` — source groups/components.

Also include:

- `REVIEW.md` with conservative self-assessment;
- `audit.json` with exact files/state/component mapping.

Follow `docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`.

## 10. Evidence questions REVIEW.md must answer

Answer explicitly:

1. Does Flash now read immediately as a white rabbit before the viewer reads explanatory text?
2. Is the colored shirt visible as clothing rather than simply another body patch?
3. Does the lightning bolt survive meaningfully at 128 and 64 px?
4. Does revised Flash remain clearly distinct from Lilli at 64/128 px?
5. Does revised Flash remain clearly distinct from Tito at 64/128 px?
6. Do all five expression states remain readable after the identity revision?
7. Does the revised Flash improve the six-character ensemble without forcing changes to the other five?
8. Did any asset outside Flash change? Expected answer is `No`; if not, explain exactly why.

Do not claim PASS merely because files exist.

## 11. Runtime / architecture boundary

This gate is **art only**.

Do not modify:

- runtime catalogues;
- generated runtime PNGs;
- `SceneActorDefinition`;
- Activities;
- launcher code;
- Activity manifest schemas;
- Collection mapping.

Do not implement `lead_character` or `supporting_characters` yet.

## 12. Promotion consequence

If the revised Flash is owner-approved, **do not create another pure-art cast gate**.

The immediate next gate should be:

```text
canonical six-cast stable source promotion
→ build-time rendition integration
→ renderer-neutral semantic state/motion support
→ Activity Simulator visual/fallback/responsive acceptance
```

The only exception is a concrete owner-identified visual blocker in the returned pixels.

## 13. Owner transfer ZIP

Create at project root and do not commit:

`GREIA_VISUAL_REVIEW_FLASH_WHITE_RABBIT_REVISION_2026-08-22.zip`

Include only:

- the 10 curated PNGs;
- `REVIEW.md`;
- `audit.json`.

Final response must include the exact line:

`VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_FLASH_WHITE_RABBIT_REVISION_2026-08-22.zip`

## 14. Stop conditions

Stop and report rather than improvising if:

- prior Flash candidate sources are missing;
- the six-cast evidence cannot be reproduced;
- white fur cannot be separated legibly from review/background values;
- shirt/bolt addition destroys small-size face/species readability;
- the revision would require changing the other five characters;
- the task would require runtime architecture changes.

## 15. Return

Commit and push the bounded Flash candidate workspace, metadata and curated review evidence.

Return:

- pushed commit SHA;
- candidate workspace path;
- revised five-state inventory;
- component inventory;
- evidence path;
- owner ZIP path;
- conservative self-assessment;
- explicit confirmation that only Flash art/evidence changed and runtime/catalogue/Activity code was untouched.
