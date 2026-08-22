# Greia Canonical Character Cast — Reauthoring and State-Set Gate

**Status:** EXECUTE  
**Date:** 2026-08-22  
**Scope:** maintainer-side canonical character artwork and motion-design evidence only  
**Character grammar:** `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`  
**Expression/motion vocabulary:** `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`  
**Visual system:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`

## 1. Purpose

Use the owner's local maintainer agent to attempt a **full canonical-character quality pass** for Greia's four recurring characters:

- Lilli — unicorn Puff;
- Nino — owl Bean;
- Tito — fox Puff;
- Momo — friendly monster Puff.

This is a separate canonical-character track, not an extension of the six generic prop/environment collections.

The current A1 characters are accepted **style anchors**, not frozen final release art. Current source coverage is materially incomplete: neutral specimens exist, each character has a blink source, the shared motion vocabulary names several motions/states, and only Lilli currently has a narrow runtime neutral/blink integration.

The goal of this gate is to determine whether the maintainer agent can produce a stronger, coherent four-character cast plus the authored visual states needed by Greia's simple motion vocabulary.

## 2. Preserve existing provenance

Do not overwrite:

```text
assets/visual/specimens/a1/
assets/visual/characters/lilli/blink.svg
assets/visual/characters/nino/blink.svg
assets/visual/characters/tito/blink.svg
assets/visual/characters/momo/blink.svg
assets/visual/library/catalog.toml
assets/visual/library/animations.toml
assets/catalog/shared_visuals_v1_source.toml
```

Create the candidate workspace under:

```text
assets/visual/pack_candidates/canonical_characters/2026-08-22/
```

Do **not** promote candidate art into runtime manifests during this gate.

## 3. Canonical character identity must remain stable

Retain the accepted identity direction from `GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`.

### Lilli

- warm cream unicorn Puff;
- golden horn;
- localized rainbow forelock/tuft;
- pink cheek/hoof cues;
- wonder / kindness / imagination.

### Nino

- warm brown owl Bean;
- light eye-mask/belly treatment;
- very large expressive eyes;
- orange beak/feet;
- side wing-flap language;
- observation / books / thoughtfulness.

### Tito

- orange fox Puff;
- triangular ears;
- cream muzzle/chest;
- chunky one-piece tail;
- playful curiosity / exploration.

### Momo

- purple fluffy/scalloped monster Puff;
- two intentionally mismatched antenna tips;
- stub arms;
- turquoise feet;
- sparse large spots;
- humor / emotion / experimentation.

Do not redesign them into unrelated new mascots merely to demonstrate drawing skill.

## 4. Exact authored state set

For **each of the four characters**, create the following five complete full-character state SVGs on the same logical 256×256 artboard and registration:

```text
neutral
blink
happy
surprised
sleepy
```

That is **20 finished state SVGs total**.

Recommended file layout:

```text
assets/visual/pack_candidates/canonical_characters/2026-08-22/
  catalog.toml
  lilli/
    neutral.svg
    blink.svg
    happy.svg
    surprised.svg
    sleepy.svg
    source_master.svg
  nino/
    ...
  tito/
    ...
  momo/
    ...
```

The full state SVGs are the portable finished authoring sources. A runtime renderer should never need to reassemble eyes/mouths/body pieces every frame.

## 5. Source-level component structure

The user explicitly wants the canonical characters to be useful as **authoring systems**, not only as five unrelated flattened pictures.

Each `source_master.svg` should therefore use clear semantic group/layer IDs where practical, for example:

```text
body
identity
face
  eyes
  mouth
accent
```

Character-specific groups may be added when genuinely useful, for example:

```text
lilli: horn, forelock
nino: wings, beak
 tito: tail, muzzle
momo: antennae, spots
```

Do not force identical anatomy/grouping across all four characters when it damages the design.

Optional `components/` files are allowed only for **high-value character-specific authoring pieces** that genuinely help future pose/state authoring. Maximum **3 component files per character**. Do not manufacture component files just to hit a count.

### Critical boundary

These are **authoring-time source components**, not a skeletal runtime rig and not a new entity-component architecture.

Do not create:

- bone hierarchies;
- mesh deformation;
- dozens of limb fragments;
- frame-by-frame sprite explosions;
- a generic face stamp copied identically onto all characters.

## 6. Expression requirements

### `neutral`

- relaxed, friendly base state;
- immediately recognizable identity;
- useful as default scene presence.

### `blink`

- eyes must visibly close;
- everything else remains registered closely enough that swapping neutral→blink does not produce a body jump.

### `happy`

- clearly happier than neutral at 128px and still readable at 64px;
- may change mouth, cheeks, eye shape and small whole-body pose cues;
- preserve character identity.

### `surprised`

- readable surprise without fear/horror;
- large readable face change;
- compatible with a small recoil/wobble runtime motion.

### `sleepy`

- clearly sleepy/calm rather than sad;
- compatible with a slow sway runtime motion.

Expression should come primarily from face + a small number of broad pose cues. Do not require detailed anatomy.

## 7. Motion vocabulary to design against

The existing shared semantic motions remain:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

This gate does **not** implement the runtime expansion yet. It must, however, prove that the new state art is suitable for those motions.

Expected mapping:

```text
idle_bounce       → neutral + tiny whole-body vertical motion
blink             → neutral / blink / neutral state swap
happy_hop         → happy + small hop/squash/settle
celebrate_pop     → happy + larger hop/pop + optional shared sparkle FX
surprised_wobble  → surprised + small recoil/rotate/wobble
sleepy_sway       → sleepy + slow side-to-side sway
```

The next runtime gate, after owner pixel approval, may extend `SceneActorDefinition` / `sample_scene_actor` to consume these semantics. Do not pre-approve or implement that runtime change here.

## 8. Quality bar

The newer generic visual work has raised the expected craft level. Do not merely redraw the old A1 vectors with extra gradients.

Target:

- charming, deliberate Greia-native silhouettes;
- polished storybook/toy-diorama feel while retaining the constraint-native simplicity;
- stronger form/material treatment than the old A1 specimens;
- clean alpha and registration;
- face remains the emotional focal point;
- each character clearly distinct at silhouette level;
- no glossy plastic balloon treatment;
- no heavy coloring-book outline;
- no anatomical overengineering;
- no excessive tiny detail that collapses at 128/64px.

The four characters should feel like one cast without sharing one cloned body formula.

## 9. Required small-size evidence

For all four characters, review at:

```text
256px
128px
64px
```

At 64px, verify at minimum:

- silhouette identity;
- eye/face readability;
- horn / owl mask-beak / fox ear-tail / monster antenna cues;
- state changes do not collapse into noise.

If a state genuinely needs a larger minimum, document it rather than falsely claiming 64px support.

## 10. Required motion-design evidence

Create motion **storyboard strips** using the candidate states plus simple whole-character transforms. These are authoring/design evidence, not runtime acceptance.

Show at least:

- `idle_bounce` sequence;
- `blink` sequence;
- `happy_hop` sequence;
- `celebrate_pop` sequence;
- `surprised_wobble` sequence;
- `sleepy_sway` sequence.

At least one storyboard sheet must show all four characters performing the same semantic motion with small personality-appropriate amplitude differences while preserving the shared meaning.

Do not fake motion by redrawing every frame into unrelated poses. Prefer state + transform logic consistent with Greia's runtime architecture.

## 11. Candidate metadata

Create `catalog.toml` describing, for each character:

- canonical ID;
- display name;
- species/archetype;
- state paths;
- logical artboard;
- supported/reviewed size guidance;
- identity cue summary;
- source-master path;
- optional component paths;
- candidate admission status.

Use candidate status only. Owner review controls promotion.

## 12. Required review evidence

Create curated evidence under:

```text
docs/reviews/visual/2026-08-22_canonical-character-cast-reauthoring/
```

Required PNGs:

1. `01-current-a1-baseline-cast.png` — current A1 neutral cast, fairly presented.
2. `02-candidate-neutral-cast.png` — all four new neutral candidates together.
3. `03-lilli-state-matrix.png` — neutral/blink/happy/surprised/sleepy.
4. `04-nino-state-matrix.png`.
5. `05-tito-state-matrix.png`.
6. `06-momo-state-matrix.png`.
7. `07-small-size-cast-matrix.png` — all four at 256/128/64.
8. `08-expression-small-size-matrix.png` — representative state differences at 128/64.
9. `09-motion-storyboards-a.png` — idle/blink/happy-hop.
10. `10-motion-storyboards-b.png` — celebrate/surprised/sleepy.
11. `11-shared-motion-personality-proof.png` — one shared motion performed by all four.
12. `12-source-component-structure.png` — clear visual explanation of useful source-level groups/components without pretending they are a runtime rig.
13. `13-detail-crops.png` — face/material/identity-cue craft at source scale.

Also include:

- `REVIEW.md` with conservative self-assessment;
- `audit.json` with exact file/state/component mapping.

Follow `docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`.

## 13. Owner transfer ZIP

Create at project root and **do not commit**:

```text
GREIA_VISUAL_REVIEW_CANONICAL_CHARACTER_CAST_2026-08-22.zip
```

Include only the curated PNGs, `REVIEW.md`, and `audit.json`.

Final response must include exactly:

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_CANONICAL_CHARACTER_CAST_2026-08-22.zip
```

## 14. Stop conditions

Stop and report rather than improvising if:

- current A1 source anchors are missing;
- the accepted character grammar cannot be found;
- a state cannot preserve character registration/identity;
- evidence cannot be rendered;
- completing the task would require changing runtime architecture.

## 15. Prohibited drift

Do not:

- create new main characters;
- redesign the canonical cast into a different franchise/style;
- build a skeletal/bone rig;
- create dozens of sprite frames;
- modify Activities;
- modify `SceneActorDefinition` or runtime motion code during this gate;
- modify shared runtime visual manifests;
- claim simulator/runtime acceptance;
- use the maintainer agent's success as evidence about arbitrary user agents;
- reopen generic Batch B asset production.

## 16. Return

Commit and push candidate character source + metadata + curated evidence.

Return:

- pushed commit SHA;
- candidate workspace path;
- exact 20 finished state files;
- any optional authoring components created;
- review evidence path;
- owner ZIP path;
- concise conservative self-assessment;
- confirmation that runtime consumers/manifests were not modified.
