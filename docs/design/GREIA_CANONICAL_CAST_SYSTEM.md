# Greia Canonical Cast System

**Status:** promoted to stable v0.1 source (`assets/visual/characters/canonical/v0.1/`) & runtime simulator accepted  
**Date:** 2026-08-24  
**Character construction grammar:** `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`  
**Expression/motion vocabulary:** `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`  
**Current source-art authority:** `PRIMARY_REVIEW.md` (archived; see git history)  
**Runtime status:** Promoted & integrated via `2026-08-22_CANONICAL_CAST_V01_PROMOTION_RUNTIME_SIMULATOR.md` (archived; see git history) (30 runtime PNGs in `assets/visual/runtime/v1/characters/`)

## 1. Purpose

Greia's recurring characters are a small shared cast that gives children recognizable social anchors across the OS and Activities.

The core rule is:

> **Each character may have a primary home turf, but the cast belongs to one shared world. Activities may have a lead mascot, not an exclusive mascot.**

Characters are presentation/identity semantics. They do not own permissions, trust, progression, package authority or top-level navigation taxonomy.

## 2. Accepted current cast

| Character | Form | Primary meaning |
|---|---|---|
| **Lilli** | unicorn Puff | wonder, creativity, stories, art, imagination |
| **Leo** | owl Bean with glasses | learning, reading, language, knowledge, thoughtful guidance |
| **Flash** | white rabbit with coral shirt + lightning bolt | games, speed, action, reflex, playful challenge |
| **Dani** | friendly toy robot | math, logic, patterns, sequencing, structured problem solving |
| **Tito** | fox Puff | exploration, nature, discovery, investigation, adventure |
| **Momo** | friendly monster Puff | emotion, music, silliness, experimentation, celebration |

The six-character source ensemble was owner-reviewed at pixel level on 2026-08-22. Flash's final source direction is the later white-rabbit revision, not the earlier raspberry-bodied candidate.

No further pure-art cast pass is currently authorized before runtime promotion/integration.

## 3. Naming and provenance

### Lilli, Tito, Momo

Names remain current.

### Leo

`Leo` supersedes the earlier owl identity/name `Nino` for the current product cast.

Current semantic ID:

```text
character.leo
```

Historical Nino candidate/source/review evidence remains provenance. Do not silently rewrite history or delete it.

### Flash

Current semantic ID:

```text
character.flash
```

Accepted identity cues:

- white/warm-white rabbit fur;
- tall pink-inner ears;
- simple coral/raspberry torso shirt;
- one bold golden lightning-bolt emblem;
- small round pom tail;
- spring-loaded/action posture.

The shirt/bolt is a broad speed/energy identity cue, not a commitment to racing or one specific game type.

### Dani

Current semantic ID:

```text
character.dani
```

Dani remains cute/friendly first and robotic second.

## 4. Soft specialization, not hard silos

Useful default lead affinities:

```text
Lilli  → creativity / stories / art / imagination
Leo    → learning / reading / language / knowledge
Flash  → games / speed / action / playful challenge
Dani   → math / logic / patterns / sequencing
Tito   → exploration / nature / discovery / investigation
Momo   → emotion / music / silly play / celebration
```

These are soft lead-mascot semantics.

Good examples:

- Leo leads a reading Activity while Lilli appears in celebration feedback;
- Dani leads a pattern puzzle listed in both `learn` and `play`;
- Flash leads a reaction game with Tito as a supporting challenger;
- Momo leads a rhythm Activity while Leo briefly explains a rule;
- ensemble scenes use several characters together.

Do not make rules such as "Leo can appear only in Learn" or "Dani means the Activity must be Math".

### 4.1 Activity presenter convention

The cast is not only decorative branding. In Activity authoring it should often provide a recognizable **presenter/guide role**.

Every new Activity design must explicitly decide whether it has:

```text
one lead presenter/mascot
small supporting character presence
or a deliberate no-presenter choice
```

A fitting lead may:

- welcome/frame the Activity briefly;
- visually demonstrate or orient the first interaction;
- give one short contextual instruction or hint;
- react through shared utterance families;
- celebrate completion;
- host an optional curiosity/facts affordance;
- narrate short researched real-world facts when the Activity subject supports it.

Do not force a mascot into every screen or turn Greia into a talking tutorial. The child should still spend most of the time acting, exploring and playing.

Presenter/speech/factual authoring rules live in:

```text
skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```

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

Natural affinities are:

```text
create  → Lilli often leads
play    → Flash often leads
learn   → Leo often leads
explore → Tito often leads
```

Dani and Momo are deliberately cross-cutting. `my_greia` remains child/profile-centered rather than permanently assigned to a mascot.

## 6. Visual identity rules

### Lilli

Preserve:

- warm cream body;
- golden horn;
- localized rainbow forelock;
- pink hoof cues;
- optional small flank star when it survives the intended size.

### Leo

Preserve:

- upright compact owl/Bean silhouette;
- chestnut/brown + cream family;
- side wing flaps;
- small beak/feet;
- **integrated teal rounded glasses** as the signature cue.

Do not recreate the earlier circular-eye-ring + glasses double-ring/goggle treatment.

### Flash

Preserve the owner-accepted white-rabbit revision:

- white/warm-white fur mass;
- tall unmistakable rabbit ears with pink inners;
- slightly more directional/spring-loaded posture than Lilli/Tito;
- coral/raspberry torso garment;
- one large golden lightning bolt;
- small round pom tail;
- readable face at 64/128 px.

Do not add racing numbers, controllers, stopwatches, helmets, shoes, shorts, gloves, headbands, capes or permanent speed trails as default identity.

Do not reopen the art merely to make the Puff-scale torso garment anatomically literal.

### Dani

Preserve:

- rounded toy-like geometry;
- clear cream/ice face/display area;
- sky/cyan/teal body family;
- one top antenna/light cue;
- simple feet/base;
- emotionally readable face before mechanical detail.

No dense panels, wires, tiny sci-fi markings or baked numerals/text.

### Tito

Preserve the accepted orange fox identity, triangular ears, cream muzzle/chest and large chunky tail.

### Momo

Preserve the purple scalloped/fluffy silhouette, asymmetric antennae, turquoise feet and comic single-tooth cue where readable.

## 7. Shared expression-state contract

The first canonical reusable source state set is:

```text
neutral
blink
happy
surprised
sleepy
```

All six support the same semantic state names while retaining character-specific expression geometry.

For runtime catalogue compatibility, the neutral source state may be exposed as runtime variant `default`; the semantic expression remains `neutral`.

At 64 px, identity and broad emotional readability are the main contract. Fine distinctions such as blink versus sleepy may be naturally weaker than at 128/256 px.

## 8. Shared motion contract

The semantic vocabulary remains:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

The first runtime implementation should prioritize resource economy:

- complete authored state swaps;
- fixed-size whole-character x/y translation;
- bounded timing/amplitude;
- shared contact-shadow grounding;
- optional small per-character intensity/timing variation.

Do not require literal reproduction of every storyboard transform. In particular, do not introduce per-frame rotated-surface allocation or continuously varying raster sizes merely to imitate storyboard rotation/squash.

The semantic result matters more than mechanically copying the sketch.

## 9. Authoring components

Canonical source masters may expose semantic groups such as:

```text
body
face
eyes
mouth
identity
accent
```

plus a few character-specific groups.

Standalone authoring components remain source-authoring aids, not a runtime body-part API.

Examples include Lilli horn/forelock, Leo glasses/face treatment, Flash ears/shirt-bolt treatment, Dani face-display/antenna treatment, Tito tail/muzzle and Momo antennae/fluff.

## 10. Source promotion target

The first stable current source family should be materialized under:

```text
assets/visual/characters/canonical/v0.1/
```

with exactly the six current semantic IDs and all five source states.

Promotion/runtime acceptance is owned by:

`2026-08-22_CANONICAL_CAST_V01_PROMOTION_RUNTIME_SIMULATOR.md` (archived; see git history)

Source promotion is not the same as runtime acceptance.

## 11. Future Activity metadata concept

After the six-character runtime family is actually accepted, Greia may add optional Activity presentation metadata conceptually equivalent to:

```toml
[presentation]
lead_character = "leo"
supporting_characters = ["dani", "lilli"]
```

This remains a future design target, not current parser/runtime authority.

When implemented:

- optional, never mandatory;
- presentation-only;
- no effect on permissions/trust/saves/progression/Collection membership;
- one lead plus a small bounded supporting list;
- unknown/unavailable IDs fail soft;
- package authors may request canonical identities but may not replace platform canonical art under those IDs.

The absence of current manifest metadata does **not** mean Activity authors should ignore presenter design. Until metadata exists, presenter ownership remains an Activity design/runtime composition decision.

## 12. Current evidence boundary

Accepted at **source/design pixel-review** scope:

- six-character ensemble identity;
- Leo glasses treatment;
- revised white-rabbit Flash identity;
- Dani character/device separation;
- five registered source states;
- storyboard compatibility with the shared motion vocabulary;
- authoring-time semantic source groups/components.

Not yet accepted:

- stable promoted source package;
- all 30 generated runtime PNG renditions;
- semantic runtime expression/motion behavior;
- variant fallback behavior;
- runtime cache/frame behavior;
- responsive Activity integration;
- physical Acer/Pi performance;
- Web runtime support;
- Activity lead/support metadata.

The current exact gate is:

`2026-08-22_CANONICAL_CAST_V01_PROMOTION_RUNTIME_SIMULATOR.md` (archived; see git history)
