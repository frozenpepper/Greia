# Canonical Cast Expansion — Leo, Flash, Dani

**Status:** EXECUTE  
**Date:** 2026-08-22  
**Authority:** `docs/reviews/visual/2026-08-22_canonical-character-cast-reauthoring/PRIMARY_REVIEW.md`  
**Cast system:** `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`  
**Character grammar:** `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`  
**Expression/motion vocabulary:** `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`

## 1. Purpose

Complete the **visual design candidate for Greia's six-character canonical cast** after owner review of the four-character reauthoring.

This is a bounded maintainer-side art gate.

Create/refine exactly:

- **Leo** — current owl identity replacing Nino as the target cast name;
- **Flash** — new rabbit;
- **Dani** — new friendly robot.

Use the already-reviewed 2026-08-22 candidates for **Lilli, Tito and Momo** as stable ensemble anchors. Do not redraw those three unless the six-character ensemble exposes a concrete visual collision that cannot be solved in the new characters.

This gate is source-art + state + motion-design evidence only. Do not modify runtime manifests, Activities, launcher code, `SceneActorDefinition`, or package schemas.

## 2. Preserve provenance

Do not overwrite:

`assets/visual/pack_candidates/canonical_characters/2026-08-22/`

That directory is historical evidence for the four-character candidate.

Create a new candidate workspace:

`assets/visual/pack_candidates/canonical_cast_expansion/2026-08-22/`

Recommended layout:

```text
catalog.toml
README.md
leo/
  source_master.svg
  neutral.svg
  blink.svg
  happy.svg
  surprised.svg
  sleepy.svg
  components/
flash/
  source_master.svg
  neutral.svg
  blink.svg
  happy.svg
  surprised.svg
  sleepy.svg
  components/
dani/
  source_master.svg
  neutral.svg
  blink.svg
  happy.svg
  surprised.svg
  sleepy.svg
  components/
```

The candidate catalogue may reference Lilli/Tito/Momo from the earlier candidate rather than copying their files.

## 3. Semantic identities

Use exactly these target IDs for the new/current identities:

```text
character.leo
character.flash
character.dani
```

Do not rename historical files in the previous candidate workspace.

`character.nino` is provenance/historical candidate identity. Do not silently alias it to Leo inside runtime/source manifests during this gate.

## 4. Shared state set

Author exactly these five complete registered states for Leo, Flash and Dani:

```text
neutral
blink
happy
surprised
sleepy
```

Use the common 256×256 logical artboard and the existing character grammar.

State changes must preserve character registration well enough for complete-state swapping without visible body jumps.

Do not create extra expression states merely to make the package look larger.

## 5. Leo — owl refinement brief

Leo starts from the useful current owl Bean direction, but must become the clearer learning/knowledge mascot.

### Preserve

- compact upright owl/Bean silhouette;
- chestnut/warm brown + cream family;
- clear face-mask/belly relationship;
- wing flaps, small beak and small feet;
- large friendly expressive eyes.

### Required new identity cue

**Simple signature glasses.**

The glasses must:

- read at 128 px and remain recognizable at 64 px;
- use rounded-square or rounded-oval geometry rather than thin formal spectacles;
- feel curious/friendly, not old/stern;
- remain one clean identity cue.

### Critical correction

Do **not** stack glasses over the current circular eye-ring treatment and produce a four-ring/goggle face.

Treat the eye mask, eye disks and glasses as one composition. Simplify or remove redundant circular outlines if necessary so Leo's face remains clean.

The old teal feather/badge is optional. Remove/demote it if the glasses already provide enough identity and the badge creates clutter.

### State notes

- `neutral` — alert, warm, observant;
- `blink` — actual closed eyes remain legible inside/behind glasses;
- `happy` — delighted/bright rather than clownish;
- `surprised` — strong owl-eye expansion without glasses becoming visual noise;
- `sleepy` — clearly distinct from blink at 64/128 px.

## 6. Flash — rabbit creation brief

Flash must be recognizable as a new cast silhouette, not a recolored Tito or hornless Lilli.

### Identity goal

> **He should look fast even while standing still.**

### Required cues

- unmistakable long rabbit ears;
- compact child-friendly body;
- directional/spring-loaded posture, e.g. slight forward readiness or asymmetrical ear energy;
- clear face at 64 px;
- small rabbit tail/muzzle cues only where they help.

### Separation requirements

At silhouette-only review:

- Flash must not be confused with Tito;
- Flash must not look like Lilli with a horn removed;
- ears + body stance should carry more identity than color.

### Palette

Avoid Tito's dominant orange family.

Good starting directions:

- raspberry / coral / berry body family;
- cream muzzle/belly accents;
- optional small mint/aqua or golden accent.

Do not bake racing clothes, numbered jerseys, stopwatches, controllers or a specific game into his permanent identity.

### State notes

- `neutral` — eager/ready;
- `blink` — clean state swap;
- `happy` — the most energetic happy expression in the cast;
- `surprised` — quick jolt, not fear;
- `sleepy` — funny contrast with his normal energy, but still recognizably Flash.

## 7. Dani — friendly robot creation brief

Dani is math/logic/pattern-oriented but must read as a **friend first, robot second**.

### Required cues

- rounded toy-like geometry;
- clear face/display area;
- one or two memorable mechanical identity cues;
- simple feet/base or another stable child-readable support;
- face remains expressive at 64 px.

### Avoid

- dense panels/wires;
- pseudo-realistic robotics;
- tiny sci-fi markings;
- baked numerals or text;
- a generic app/device icon silhouette;
- cold/menacing eyes.

### Palette

Good starting direction:

- sky/cyan/teal-blue;
- cream or pale neutral body sections;
- one restrained warm yellow/coral micro-accent.

### State notes

- `neutral` — calm, clever, reassuring;
- `blink` — clear closed-eye/display equivalent;
- `happy` — satisfying "solved it" energy without symbols/text;
- `surprised` — readable but controlled;
- `sleepy` — charming low-energy state, not broken/malfunctioning.

## 8. Lilli / Tito / Momo boundary

Use the existing candidates from:

`assets/visual/pack_candidates/canonical_characters/2026-08-22/`

Do not reauthor them during this gate unless a **specific full-cast evidence problem** is found.

If such a problem exists, report it before broad changes. A small bounded color/value correction is acceptable only when needed to establish six-cast separation.

## 9. Authoring-time source components

For each of Leo, Flash and Dani provide a semantically grouped `source_master.svg` and **up to 3 genuinely useful authoring components**.

Good examples:

```text
Leo  → glasses, wings/face-mask treatment, blink-eye treatment
Flash → ears, tail/muzzle treatment, expression-eye treatment
Dani  → face-display treatment, antenna/light cue, pointer/arm or base treatment
```

Do not create fragments merely to hit three.

These components are authoring-time assets only. Do not design a runtime body-part API.

## 10. Soft role map to demonstrate

The review material should communicate the current cast meaning:

```text
Lilli → creativity / stories / art
Leo   → learning / reading / knowledge
Flash → games / speed / playful action
Dani  → math / logic / patterns
Tito  → exploration / discovery
Momo  → emotion / music / silly play / celebration
```

This is a **soft lead-mascot map**, not six exclusive Activity silos.

Do not redesign Greia Home or create six top-level Collections. Existing platform Collections remain separate product architecture.

## 11. Motion-design proof

Use the existing semantic vocabulary:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

No runtime implementation is required here.

At minimum:

1. show `happy_hop` across **all six** characters to test shared vocabulary + personality differences;
2. show one second motion across all six, preferably `surprised_wobble` or `sleepy_sway`;
3. include explicit Leo/Flash/Dani motion notes where their personality differs.

Do not introduce skeletal/bone motion.

## 12. Small-size and silhouette proof

The full six-character cast must be reviewed at:

```text
256 px
128 px
64 px
```

Also create a **silhouette-only** comparison at 128 and 64 px.

The gate fails visually if:

- Flash/Tito become ambiguous without color;
- Flash/Lilli become ambiguous without color;
- Dani becomes a generic device/blob;
- Leo's glasses merge into eye-ring clutter;
- new expressions are unreadable at their claimed minimum size.

If 64 px is not honestly supported for a specific character/state, record a larger supported minimum instead of claiming otherwise.

## 13. Required owner-review evidence

Create:

`docs/reviews/visual/2026-08-22_canonical-cast-expansion/`

Required PNGs:

1. `01-four-character-anchor.png` — current reviewed Lilli/Nino/Tito/Momo candidate reference.
2. `02-six-character-neutral-ensemble.png` — Lilli, Leo, Flash, Dani, Tito, Momo together.
3. `03-nino-to-leo-refinement.png` — current owl candidate beside Leo, with glasses/eye-mask treatment clearly visible.
4. `04-leo-state-matrix.png` — five states.
5. `05-flash-state-matrix.png` — five states.
6. `06-dani-state-matrix.png` — five states.
7. `07-six-character-multiscale.png` — all six at 256/128/64.
8. `08-six-character-silhouettes.png` — silhouette-only at 128/64.
9. `09-new-character-expression-small-size.png` — Leo/Flash/Dani states at 128/64.
10. `10-role-map.png` — neutral presentation of the six soft primary roles; not a Home/UI redesign.
11. `11-happy-hop-all-six.png` — one shared motion storyboard across all six.
12. `12-secondary-motion-all-six.png` — surprised wobble or sleepy sway across all six.
13. `13-new-source-component-structure.png` — Leo/Flash/Dani semantic groups/components.
14. `14-detail-crops.png` — glasses, rabbit face/ears, robot face/material/identity details.

Also include:

- `REVIEW.md` with a conservative self-assessment;
- `audit.json` with exact file/state/component mapping.

Follow `docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`.

## 14. Evidence questions that REVIEW.md must answer

Answer explicitly:

1. Is Leo readable as the same broad owl family while clearly superseding Nino's identity/name?
2. Do the glasses remain readable without double-ring/goggle clutter?
3. Can Flash be distinguished from Tito and Lilli by silhouette alone at 64/128 px?
4. Does Dani read as a character rather than a device icon at 64/128 px?
5. Are `blink`, `happy`, `surprised`, and `sleepy` genuinely distinguishable for Leo/Flash/Dani at claimed sizes?
6. Do all six feel like one cast without becoming six clones?
7. Did any existing Lilli/Tito/Momo art need alteration? If yes, why exactly?

Do not write "PASS" merely because files exist. Report actual observed weaknesses.

## 15. Owner transfer ZIP

Create at project root and do not commit:

`GREIA_VISUAL_REVIEW_CANONICAL_CAST_EXPANSION_2026-08-22.zip`

Include only:

- the 14 curated PNGs;
- `REVIEW.md`;
- `audit.json`.

Final response must include the exact line:

`VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_CANONICAL_CAST_EXPANSION_2026-08-22.zip`

## 16. Stop conditions

Stop and report rather than improvising if:

- the prior canonical-character candidate is missing;
- the accepted character grammar/motion docs are missing;
- evidence cannot be rendered;
- creating the art would require runtime architecture changes;
- Leo cannot support readable glasses without a material owl-face redesign;
- Flash cannot be made silhouette-distinct from Tito/Lilli within the accepted character grammar;
- Dani cannot remain emotionally readable at the target size without adding excessive detail.

## 17. Prohibited drift

Do not:

- create generic Batch B;
- create a new themed environment pack;
- alter runtime catalogues;
- alter Activities;
- implement `lead_character` manifest parsing yet;
- create six new launcher/Home categories;
- replace the full cast with a new unrelated style;
- redraw Lilli/Tito/Momo without a demonstrated ensemble problem;
- create skeletal rigs or runtime body-part animation;
- claim simulator/runtime/physical acceptance.

## 18. Return

Commit and push the new candidate workspace, metadata and curated review evidence.

Return:

- pushed commit SHA;
- candidate workspace path;
- Leo/Flash/Dani state-file inventory;
- source component inventory;
- evidence path;
- owner ZIP path;
- conservative self-assessment;
- confirmation that runtime/catalogue/Activity code was untouched.
