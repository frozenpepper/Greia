# Greia Canonical Cast System

**Status:** accepted design direction; expanded six-character art pending owner visual acceptance  
**Date:** 2026-08-22  
**Character construction grammar:** `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`  
**Expression/motion vocabulary:** `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`  
**Current visual review:** `docs/reviews/visual/2026-08-22_canonical-character-cast-reauthoring/PRIMARY_REVIEW.md`

## 1. Purpose

Greia's recurring characters are not decorative stickers attached arbitrarily to Activities. They are a small shared cast that gives children recognizable social anchors across the OS and Activities.

The cast should help a child anticipate the **kind of experience** they are entering without turning characters into rigid content silos.

The core rule is:

> **Each character may have a primary home turf, but the cast belongs to one shared world. Activities may have a lead mascot, not an exclusive mascot.**

## 2. Current target cast

| Character | Form | Primary meaning |
|---|---|---|
| **Lilli** | unicorn Puff | wonder, creativity, stories, art, imagination |
| **Leo** | owl Bean with glasses | learning, reading, language, knowledge, thoughtful guidance |
| **Flash** | rabbit | games, speed, action, reflex, playful challenge |
| **Dani** | friendly robot | math, logic, patterns, sequencing, structured problem solving |
| **Tito** | fox Puff | exploration, nature, discovery, investigation, adventure |
| **Momo** | friendly monster Puff | emotion, music, silliness, experimentation, celebration |

The set is deliberately varied in silhouette, material language and personality while retaining the common Greia face/state/motion grammar.

## 3. Naming and migration

### Lilli, Tito, Momo

Current names remain.

### Leo

`Leo` replaces the previous owl display name `Nino` in the current cast direction. The name is short, child-friendly and internationally pronounceable, with a light Leonardo/Leonardo da Vinci association supporting the curious/knowledge identity.

Historical `Nino` source art and IDs remain provenance until a later explicit promotion/migration gate. Do not silently rewrite historical review evidence.

Current target semantic identity:

```text
character.leo
```

### Flash

New rabbit identity:

```text
character.flash
```

The name carries immediate playful speed/action meaning and should be supported by the silhouette even in a static neutral pose.

### Dani

New robot identity:

```text
character.dani
```

The name is intentionally warm and human-friendly, with only a light Daneel/Asimov naming echo. Dani must read as a friend first and a machine second.

## 4. Soft specialization, not hard silos

The cast may guide Activity identity and discovery, but character assignment is **presentation semantics**, not package authority.

Good examples:

- Leo leads a reading Activity while Lilli appears in a celebration;
- Dani leads a pattern puzzle that appears in both `learn` and `play`;
- Flash leads a reaction game with Tito as a supporting challenger;
- Momo leads a rhythm Activity while Leo briefly explains a rule;
- ensemble scenes use several characters together.

Do not make a rule such as "Leo can appear only in Learn" or "Dani means the Activity must be Math".

## 5. Relationship to Collection-first Home

Greia Home remains platform-owned:

```text
create
play
learn
explore
my_greia
```

Characters do not create new top-level Collections.

Useful default affinities are:

```text
create  → Lilli
play    → Flash
learn   → Leo
explore → Tito
```

Dani and Momo are intentionally cross-cutting:

- Dani commonly leads logic/math/pattern experiences within `learn`, `play`, or both;
- Momo commonly leads music/emotion/silly-play/celebration experiences across appropriate Collections;
- `my_greia` remains child/profile-centered and may use the child identity or an ensemble rather than a permanently assigned mascot.

This keeps the five-destination child mental model stable while allowing much richer character semantics inside Collections and Activities.

## 6. Visual identity rules

### Lilli

Preserve the strong current anchors:

- warm cream body;
- golden horn;
- localized rainbow forelock;
- pink hoof cues;
- optional small flank star when it survives the intended size.

Do not redesign Lilli merely to make her match a new character.

### Leo

Preserve the useful owl Bean foundation:

- upright compact owl silhouette;
- warm chestnut/brown + cream family;
- readable eye-mask/belly relationship;
- side wing flaps;
- small beak/feet.

Add **signature glasses** as the primary new cue.

Glasses requirements:

- rounded-square or rounded-oval;
- medium-weight, warm dark or softened teal-brown frames;
- legible at 64/128 px;
- friendly, not severe or elderly;
- integrated with the eye-mask design.

Do **not** simply place glasses over the current circular eye rings. If necessary, simplify the existing eye-ring treatment so the glasses become the clean outer frame rather than producing four competing circles.

The old teal feather/badge is secondary and may be removed or demoted if it competes with the glasses.

### Flash

Flash must be identifiable before color is considered.

Requirements:

- long unmistakable rabbit ears;
- compact but more directional body than Lilli/Tito;
- static posture should imply stored spring/forward energy;
- face must remain immediately readable at 64 px;
- small tail/muzzle cues only if they help rather than clutter.

Do not make Flash a Tito recolor with long ears or a Lilli body without a horn.

Palette should separate him from Tito's strong orange. Good starting directions are raspberry/coral/berry with cream and a small cool accent. Palette is subordinate to silhouette.

Avoid baked racing clothing or activity-specific props as permanent identity unless a later review specifically approves one.

### Dani

Dani should be **cute first, robot second**.

Requirements:

- rounded toy-like geometry;
- simple, emotionally readable face/display area;
- one or two mechanical signature cues only;
- compact body with clear feet/base;
- no tiny panels, wires, pseudo-realistic robotics or dense sci-fi detail;
- no baked numerals/text/icons required to understand the character.

Good palette direction: sky/cyan/teal-blue + cream/pale neutral with a small warm yellow/coral accent.

Dani must remain a character at 64 px, not collapse into a generic device icon.

### Tito

Preserve the accepted orange fox identity, triangular ears, cream muzzle/chest and chunky tail. The arrival of Flash makes the tail/ear relationship more important for species separation.

### Momo

Preserve the purple scalloped body, asymmetric antennae, turquoise feet and comic single-tooth cue where readable.

## 7. Shared expression-state contract

The first canonical reusable state set remains:

```text
neutral
blink
happy
surprised
sleepy
```

All six characters should support the same semantic names while retaining character-specific facial personality.

This is not a demand for identical facial geometry.

Examples:

- Leo surprise can emphasize owl-eye expansion behind glasses;
- Flash happy can be especially energetic;
- Dani happy can read as satisfying "solved it" delight without text;
- Momo surprise may be broader/comic;
- Lilli happy remains warm rather than hyperactive.

## 8. Shared motion contract

The current motion vocabulary remains:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Character life should come from:

- complete authored state swaps;
- whole-body translation;
- small rotation;
- modest squash/stretch where supported;
- small character-specific amplitude/timing differences;
- optional shared FX.

Do not introduce a skeletal rig merely because the cast expanded.

## 9. Authoring components

Source masters may expose semantic groups such as:

```text
body
face
eyes
mouth
identity
accent
```

plus a few character-specific groups.

Useful standalone components may be kept for authoring, for example:

- Lilli horn/forelock;
- Leo glasses/wing/face-mask treatment;
- Flash ears/tail or speed-accent treatment;
- Dani face-display/antenna/pointer-light treatment;
- Tito tail/muzzle;
- Momo antennae/fluff.

These are **authoring-time source resources**, not a runtime body-part API.

## 10. Future Activity metadata concept

After the six-character art family and semantic IDs are accepted, Greia may add optional Activity presentation metadata conceptually equivalent to:

```toml
[presentation]
lead_character = "leo"
supporting_characters = ["dani", "lilli"]
```

This is a future design target, not current parser/runtime authority.

Rules when implemented:

- optional, never mandatory for an Activity;
- presentation-only;
- does not alter permissions, trust, saves, progression or Collection membership;
- one lead plus a small bounded supporting list;
- unknown/unavailable character IDs fail soft;
- package authors may request canonical cast use but may not replace platform character identity assets with arbitrary lookalikes under canonical IDs.

## 11. Current evidence boundary

The 2026-08-22 four-character candidate proved:

- useful five-state registration;
- low-resolution family readability;
- shared semantic-motion storyboard compatibility;
- authoring-level source grouping.

It did **not** prove:

- the final six-character ensemble;
- Leo glasses readability;
- Flash-vs-Tito/Lilli silhouette separation;
- Dani low-resolution character readability;
- runtime behavior for the expanded states/motions;
- simulator/physical acceptance of all six.

The current exact visual gate is:

`docs/testing/2026-08-22_CANONICAL_CAST_EXPANSION_LEO_FLASH_DANI.md`

Runtime promotion follows only after owner pixel review of that gate.
