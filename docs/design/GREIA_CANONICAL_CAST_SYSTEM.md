# Greia Canonical Cast System

**Status:** accepted six-character design direction; bounded Flash identity revision pending before promotion  
**Date:** 2026-08-22  
**Character construction grammar:** `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`  
**Expression/motion vocabulary:** `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`  
**Current visual review:** `docs/reviews/visual/2026-08-22_canonical-cast-expansion/PRIMARY_REVIEW.md`

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
| **Flash** | white rabbit with lightning shirt | games, speed, action, reflex, playful challenge |
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

Current semantic identity:

```text
character.flash
```

The name carries immediate playful speed/action meaning. The accepted target identity is now **white/warm-white rabbit + simple coral/raspberry shirt + one gold/yellow lightning bolt**. The bolt is a broad speed/energy cue, not a commitment to one specific game genre.

### Dani

Current semantic identity:

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

This keeps the five-destination child mental model stable while allowing richer character semantics inside Collections and Activities.

## 6. Visual identity rules

### Lilli

Preserve the strong current anchors:

- warm cream body;
- golden horn;
- localized rainbow forelock;
- pink hoof cues;
- optional small flank star when it survives the intended size.

Do not redesign Lilli merely to make her match another character.

### Leo

Accepted current direction:

- upright compact owl/Bean silhouette;
- warm chestnut/brown + cream family;
- readable eye-mask/belly relationship;
- side wing flaps;
- small beak/feet;
- integrated teal rounded glasses as the primary identity addition.

Glasses requirements:

- rounded-square or rounded-oval;
- medium-weight;
- legible at 64/128 px;
- friendly, not severe or elderly;
- integrated with the eye-mask design rather than stacked over redundant eye rings.

The old teal feather/badge is superseded by the cleaner glasses-led identity.

### Flash

Flash must read immediately as a rabbit and as an energetic/playful cast member.

Accepted target identity:

- **white or warm-white fur/body**;
- long unmistakable rabbit ears;
- clearly pink inner ears;
- compact spring-loaded/directional posture;
- simple **coral/raspberry shirt or sleeveless top**;
- one large **yellow/gold lightning bolt** on the shirt;
- small round pom-pom tail;
- large readable face.

The shirt/bolt is a canonical identity cue, not an Activity-specific costume system. It is accepted because lightning broadly communicates speed/energy/action without encoding a specific game, sport, controller, number or text.

Do not add racing numbers, stopwatch props, controllers, headbands, gloves, shoes, shorts, helmets, permanent speed trails or other costume clutter.

Flash must remain distinct from both:

```text
Lilli → warm cream magical Puff + horn + rainbow forelock + soft/wonder posture
Tito  → orange fox + triangular ears + massive bushy tail + explorer stance
```

At small sizes, ears + shirt color mass + posture should carry more identity than fine detail.

### Dani

Dani should be **cute first, robot second**.

Accepted direction:

- rounded toy-like geometry;
- simple emotionally readable face/display area;
- one or two mechanical signature cues only;
- compact body with clear feet/base;
- sky/cyan/teal-blue family + pale faceplate + restrained warm accent;
- no tiny panels, wires, pseudo-realistic robotics or dense sci-fi detail;
- no baked numerals/text/icons required to understand the character.

Dani must remain a character at 64 px, not collapse into a generic device icon.

### Tito

Preserve the accepted orange fox identity, triangular ears, cream muzzle/chest and chunky tail. Flash's rabbit identity must not erode this separation.

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

- Leo surprise emphasizes owl-eye expansion behind glasses;
- Flash happy is especially energetic;
- Dani happy reads as satisfying "solved it" delight without text;
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
- Flash ears, shirt+bolt treatment, tail/muzzle treatment;
- Dani face-display/antenna/light treatment;
- Tito tail/muzzle;
- Momo antennae/fluff.

These are **authoring-time source resources**, not a runtime body-part or clothing API.

## 10. Future Activity metadata concept

After the six-character art family and semantic IDs are accepted and promoted, Greia may add optional Activity presentation metadata conceptually equivalent to:

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

## 11. Current evidence boundary and next gate

The 2026-08-22 six-character expansion candidate established at owner pixel-review scope:

- Leo's glasses/eye-mask treatment works;
- Dani reads as a friendly character rather than a device icon;
- Flash's rabbit silhouette and five-state structure work;
- all six form a coherent ensemble;
- shared `happy_hop` / `surprised_wobble` storyboard semantics remain coherent across the expanded cast.

One bounded owner-directed identity correction remains before promotion:

> revise Flash from raspberry fur to white/warm-white fur with a simple colored shirt and one lightning-bolt chest cue.

Current exact gate:

`docs/testing/2026-08-22_FLASH_WHITE_RABBIT_IDENTITY_REVISION.md`

After owner pixel acceptance of that revision, do not run another pure-art cast pass unless a concrete blocker is identified. Move directly to canonical source promotion, build-time runtime renditions, semantic state/motion integration, and Activity Simulator acceptance.
