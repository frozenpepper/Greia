# Primary Review — Canonical Cast Expansion

**Date:** 2026-08-22  
**Candidate commit reviewed:** `cfbb9512723353dd34f6081c174410401e290ca8`  
**Candidate source:** `assets/visual/pack_candidates/canonical_cast_expansion/2026-08-22/`  
**Evidence reviewed:** all 14 PNGs from `GREIA_VISUAL_REVIEW_CANONICAL_CAST_EXPANSION_2026-08-22.zip` plus `REVIEW.md` and `audit.json`  
**Cast authority:** `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`

## 1. Verdict

The six-character candidate is **accepted as the canonical cast-system direction**, with one bounded visual correction required before source promotion/runtime integration:

> **Flash should be revised from a raspberry/pink-fur rabbit into a clearly white/warm-white rabbit whose speed identity is carried by a simple colored shirt with one lightning-bolt emblem.**

Do not reopen Leo, Dani, Lilli, Tito or Momo unless the revised Flash creates a concrete ensemble collision.

The current result is otherwise strong enough that the workstream should move to promotion/runtime/simulator integration immediately after this one Flash gate.

## 2. What the pixels actually support

### Leo — accepted

Leo successfully supersedes the historical Nino presentation direction:

- the owl/Bean silhouette remains recognizable;
- teal glasses are integrated with the face-mask rather than stacked over the old circular eye-ring treatment;
- the old teal feather/badge clutter is removed;
- `neutral`, `blink`, `happy`, `surprised`, and `sleepy` remain readable at the reviewed scales;
- the result reads as a friendly learning/knowledge mascot rather than an elderly/stern owl.

No further Leo art pass is authorized before runtime integration.

### Dani — accepted

Dani reads as a character rather than a device icon:

- rounded toy-like chassis;
- clear face/display area;
- sparse mechanical cues;
- warm antenna accent;
- readable emotional states at 128/64 px;
- distinct silhouette within the ensemble.

No further Dani art pass is authorized before runtime integration.

### Lilli / Tito / Momo — accepted carry-forward anchors

The existing candidate art remains compatible with the expanded cast. No redraw was required and none should be introduced now merely to equalize microscopic craft details.

### Flash — structurally accepted, identity color treatment requires one correction

The current Flash succeeds at several important things:

- unmistakable long rabbit ears;
- good silhouette separation from Tito and Lilli;
- useful spring-loaded/action personality;
- readable five-state set;
- clean small-size silhouette;
- correct role fit for games/action/play.

However, the dominant raspberry body makes the character read first as a **pink/red round mascot with rabbit ears** and only second as a familiar rabbit. For a recurring child-facing mascot named Flash, species recognition should be more immediate.

The owner-directed correction is therefore:

```text
white / warm-white rabbit fur
+ pink inner ears
+ simple coral/raspberry shirt
+ one large yellow/gold lightning bolt
+ existing long-ear / pom-tail / spring-loaded posture identity
```

This should make the semantic shorthand immediate:

> **white rabbit + lightning = Flash**

The shirt/bolt is approved as a canonical identity cue because it communicates broad speed/energy/action rather than one narrow Activity type. Do not add racing numbers, controller symbols, stopwatch props, headbands, shoes, shorts, gloves, or other sports-costume clutter.

## 3. Ensemble assessment

The six-character family now has useful separation in:

- silhouette;
- dominant palette/material treatment;
- face construction;
- role/personality;
- motion personality.

Current conceptual ensemble remains:

```text
Lilli — creativity / stories / art / imagination
Leo   — learning / reading / language / knowledge
Flash — games / speed / action / playful challenge
Dani  — math / logic / patterns / sequencing
Tito  — exploration / nature / discovery / investigation
Momo  — emotion / music / silly play / celebration
```

This is still a **soft lead-mascot system**, not exclusive silos and not six new Home categories.

## 4. Flash visual correction authority

The bounded Flash revision must preserve:

- current semantic ID target: `character.flash`;
- current rabbit silhouette logic;
- long ears;
- pom-pom tail;
- spring-loaded posture;
- current five-state contract;
- whole-character motion compatibility.

Change only what is required to establish the stronger species/identity treatment:

1. body/fur becomes white or warm white;
2. inner ears remain clearly pink;
3. add a simple coral/raspberry shirt or sleeveless top;
4. add one bold gold/yellow lightning bolt on the shirt;
5. keep face readable and avoid making Flash resemble Lilli.

The shirt and bolt may be separate semantic groups in `source_master.svg` for authoring convenience. They are **not** a runtime clothing/equipment API.

## 5. Important Lilli separation

A white Flash must not become "Lilli without a horn."

The revised ensemble should reinforce:

### Lilli

- warm creamy magical body;
- horn;
- rainbow forelock;
- softer/wonder posture;
- pink hoof cues.

### Flash

- cleaner white fur;
- much taller rabbit ears;
- more directional/spring-loaded posture;
- colored shirt silhouette across torso;
- lightning-bolt chest cue;
- pom tail.

At 64 px, ears + shirt color mass + posture should do more identity work than fine facial detail.

## 6. Motion evidence boundary

The supplied `happy_hop` and `surprised_wobble` sheets successfully demonstrate a coherent **design vocabulary** across all six while preserving personality differences.

They do **not** yet prove runtime timing, interpolation, cache behavior, fallback behavior, or Activity Simulator behavior.

After Flash is corrected and owner-reviewed, the next gate should move directly to stable source promotion + explicit build-time renditions + renderer-neutral semantic motion/state support + Activity Simulator acceptance.

## 7. Next exact gate

Execute:

`docs/testing/2026-08-22_FLASH_WHITE_RABBIT_IDENTITY_REVISION.md`

This is the **last intended pure-art correction before canonical cast promotion**.

Do not create another general cast redesign pass after it unless the owner identifies a concrete blocker in the returned pixels.
