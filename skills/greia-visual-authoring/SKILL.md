---
name: greia-visual-authoring
description: Canonical practical guide for model-assisted Greia character, scene, prop, FX and UI visual design using the constraint-native Greia visual language.
---

# Greia Visual Authoring Skill

**Status:** living derived visual-authoring guide  
**Reviewed:** 2026-08-20  
**Active art plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`

This skill teaches models and contributors how to create Greia visuals without reinventing the art direction for each Activity. It is practical guidance, not a runtime API. Exact implemented asset/runtime contracts remain source-owned; accepted ADRs own architecture/trust boundaries; `docs/design/GREIA_VISUAL_STYLE_GUIDE.md` owns the overall visual language.

---

## 1. Mandatory context before visual work

Read, as relevant:

```text
AGENTS.md
docs/DOCUMENTATION.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md
docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
runtime/theme-defaults.toml
assets/catalog/core_icons_v1.toml
assets/visual/library_v0.1.toml
assets/visual/specimens/a2/base_motion_v0.1.toml
```

For Activity visuals also read:

```text
skills/greia-activity-authoring/SKILL.md
docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md
docs/design/GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md
```

For platform-owned UI, preserve ADR 0018/0019/0026 and the exact current source-owned UI/system-chrome contracts.

Do not use chat history as the only authority for art rules.

---

## 2. Core visual principle

Greia does **not** default to detailed traditionally articulated cartoon anatomy.

The default visual grammar is:

> **simple expressive characters + strong faces + whole-body motion + chunky illustrated props + cozy layered scenes + tactile Greia UI**

The style should look intentionally economical, not unfinished.

Greia is allowed to be simple. It is not allowed to look like placeholder/debug art in production.

---

## 3. Character archetype selection

Choose the simplest archetype that communicates the role.

### Puff

Use for most cute animal/mascot identities.

Construction target:

- one round/oval/fluffy primary body mass;
- large face area;
- zero/two tiny feet;
- zero/two stub arms/flaps;
- up to three identity attachment groups.

Good species cues: ears, horn, tuft, tail, markings, whisker cue, tiny wing, antennae.

### Bean

Use for upright compact characters such as owls, penguin-like creatures, helpers or robots.

Construction target:

- one vertical rounded/drop mass;
- face in upper half;
- tiny feet;
- optional flap/wing/arm shapes.

### Cutout Critter

Use when a flatter sticker/felt/paper-cut visual is appropriate.

Construction target:

- 2–5 large layers;
- strong silhouette;
- deliberately flat depth;
- no fake anatomical complexity.

### Object Friend

Use when educational content itself can be the character.

Examples:

- number;
- letter;
- geometric shape;
- block;
- train wagon;
- paint palette;
- cloud;
- star;
- tool;
- fruit/food item.

The object/glyph remains the primary silhouette. Prefer Object Friend over inventing an unnecessary animal mascot when the object itself can carry the interaction.

---

## 4. Character complexity and drawing rules

Default character budget:

```text
1 main body mass
1 face region
0–2 tiny feet
0–2 tiny arms/wings/flaps
0–3 identity attachment groups
```

For reusable vector masters, use the accepted 256×256 review convention where appropriate. At 256 px:

- normal primary contour: about 3–4 px;
- normal secondary contour: about 2–3 px;
- rounded joins/caps;
- tinted dark outline related to cocoa/plum/navy rather than pure black;
- broad flat or restrained two-stop fills;
- few large interior patches rather than detailed fur/texture.

Review at 128 and 64 px wherever those sizes are supported.

Avoid by default:

- articulated knees/elbows;
- realistic quadruped legs;
- separate near/far multi-limb gait rigs;
- long detailed neck/torso anatomy;
- many tiny fur/hair pieces;
- detailed fingers/toes;
- anatomy whose correctness depends on one exact pose;
- ornament that disappears below 128 px;
- five-plus unrelated accent colors.

If a proposed character requires a complex skeleton to look acceptable, simplify the design before adding a more complex animation system.

---

## 5. Face-first design

The face is the primary emotional engine.

### Base semantic expressions

A reusable character should provide a clear path to:

```text
neutral
happy
excited
surprised
sleepy
sad_gentle
thinking
proud
silly
```

`blink` is a transient micro-state rather than a persistent emotion.

Normal educational mistakes must not use anger, shame or disappointed-at-the-child expressions.

**Important face-review lesson:** `sad_gentle` must not use brow angles or eye treatment that can be misread as irritation, accusation or disappointment. Prefer softened/smaller eyes, a shallow sad mouth and low-energy posture.

### Expression ingredients

Prefer:

- large eye shapes;
- eyelids;
- pupil direction;
- simple mouth variants;
- cheeks/blush;
- brow-like upper-eye shaping only when it cannot produce an angry reading;
- tiny ear/tuft/antenna changes;
- slight whole-body tilt/squash.

Do not compensate for an unreadable face with tiny decorative lines.

### Small-size test

At 128 px, the intended expression must remain obvious. At 64 px, the face/silhouette must still read where 64 px is a supported usage size.

---

## 6. Core static style anchors

The owner-reviewed initial style anchors are:

- **Lilli** — unicorn Puff: cream body, localized rainbow cue, horn, wonder/kindness;
- **Nino** — owl Bean: observation, books, thoughtfulness;
- **Tito** — fox Puff: curiosity, exploration, playful cleverness;
- **Momo** — friendly monster Puff: humor, emotion, experimentation.

Their approval scope is **static style anchor / design grammar**. It does not mean their current SVG files are immutable release art or runtime-integrated character packages.

Use them as evidence of the family resemblance, not as templates to copy mechanically. A new character should feel like it belongs beside them without merely recoloring one of them.

The names are intentionally short Italian names that are also easy for many foreign children to pronounce.

---

## 7. Motion selection

Use the semantic base motions before inventing bespoke choreography.

### Base Animation Set v0.1

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Canonical candidate timing/phase rules live in:

```text
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
assets/visual/specimens/a2/base_motion_v0.1.toml
```

Current nominal values:

- `idle_bounce`: 2.0 s loop; vertical <= ~3.5% body height; rotation <= 2°;
- `blink`: 0.22 s; close 0–35%, hold 35–55%, reopen 55–100%;
- `happy_hop`: 0.90 s; anticipation 0–18%, launch/apex/fall, settle 78–100%; hop <= ~22%;
- `celebrate_pop`: 1.15 s; pop + bounded FX; travel <= ~28%;
- `surprised_wobble`: 0.72 s; recoil + damped alternating rotation <= 7°;
- `sleepy_sway`: 2.4 s loop; low-energy sway/compression.

These motions should work mostly through:

- whole-body translation/rotation;
- squash/stretch;
- face state;
- tiny appendage response;
- tail/tuft/antenna lag;
- bounded particles/effects.

A semantic motion description must not assume a horse knee, human elbow or species-specific skeleton.

### Static fallbacks are mandatory

```text
idle_bounce      -> neutral
blink            -> neutral
happy_hop        -> happy
celebrate_pop    -> happy or excited
surprised_wobble -> surprised
sleepy_sway      -> sleepy
```

Meaning must remain clear when animation is disabled.

### Candidate v0.2

```text
think
yes_nod
no_wobble
look_or_point
reward_sparkle
enter_pop
exit_pop
listen
```

Do not proliferate names until the base set is accepted across multiple archetypes.

---

## 8. Motion character mapping

Different characters may express the same semantic motion differently.

### `celebrate_pop`

- Puff: body hop + stub arms/ears/tuft response + happy eyes + bounded sparkles;
- Bean owl: body hop + optional wing-flap response + happy eyes;
- Object Friend: conservative squash/pop + face brighten + optional stars;
- Monster: body wobble + antenna response + optional stub-arm flap.

### `surprised_wobble`

- ears may rise;
- owl wings may open slightly;
- antennae may spring apart;
- Object Friend may simply recoil and widen eyes.

### Object Friend distortion rule

Protect the pedagogical silhouette. Rotation and squash/stretch should be **more conservative** than on an ordinary Puff/Bean whenever deformation could make a number, letter or object harder to recognize.

Preserve semantic consistency without forcing identical anatomy.

---

## 9. Runtime boundary for motion

`src/greia_platform/ui_motion.py` is the current architectural precedent for cheap renderer-neutral mathematical motion. It uses immutable samples and bounded transforms without a heavyweight retained animation framework.

Do **not** create a parallel per-Activity character animation engine.

The current UI-oriented `MotionSample` does not yet carry character rotation, anisotropic squash/stretch, face state, attachment cues or FX. Any future runtime-facing character-motion seam must be reviewed in the accepted architecture phase and should extend/reuse the same lightweight philosophy rather than silently turning the A2 design harness into runtime authority.

---

## 10. Scene design

Preferred environment logic:

- storybook diorama;
- felt-board/paper-cut layering;
- cozy toy-world composition;
- large background/midground/foreground masses;
- chunky readable props;
- intentional quiet play area.

A scene should normally establish:

1. background atmosphere/sky/wall;
2. distant simple shapes;
3. middle scene/ground/playfield;
4. interactive props/entities;
5. foreground framing/decorations only where they do not obstruct play;
6. platform-owned system-safe region untouched.

Avoid giant accidental empty regions caused by weak composition. Empty space is fine when it deliberately supports focus.

Raw rectangles/circles/polygons are acceptable for hitboxes, debug bounds, prototype layout and intentionally geometric pedagogy. They are not normally sufficient final representations of trees, animals, rivers, clinics, houses, bushes, bridges, furniture or vehicles.

---

## 11. Prop design

Props should use:

- strong silhouette;
- few large shapes;
- rounded/tactile construction where appropriate;
- restrained internal detail;
- soft depth/shadow;
- clear interaction state.

Prefer one well-designed reusable bush/log/bridge/tool over ten slightly different raw geometry versions.

Props used as interaction targets must remain distinct from purely decorative scenery.

---

## 12. Effects design

Common Greia effects:

```text
sparkles
stars
hearts
dust_puff
impact_puff
glow_ring
sleepy_z
discovery_rays
confetti
```

Rules:

- bounded count;
- short lifetime;
- never required for meaning;
- do not cover critical controls;
- do not create constant visual noise;
- prefer one coherent effect vocabulary across Activities.

---

## 13. UI illustration rules

The semantic UI architecture remains platform-owned. Visual authoring should make it feel coherent, not replace its contracts.

Target feel:

- rounded;
- tactile;
- warm;
- large;
- stable;
- slightly toy-like;
- soft depth rather than flat enterprise-dashboard styling.

Use the same family of motion cues as characters:

- hover/focus: tiny lift/glow;
- press: squash/depress + release;
- selected: clear border/depth/emphasis;
- popup: pop-in with restrained overshoot;
- error/gentle wrong choice: wobble rather than alarming shake;
- reward: bounce/sparkle.

Do not restyle or impersonate Greia’s protected system Home/Back controls inside Activity content.

---

## 14. Color and detail

`runtime/theme-defaults.toml` owns the implemented core theme palette. Character/content art may use thematic colors, but it should remain harmonious with Greia’s warm backgrounds and accents.

Default character color discipline:

```text
1 main body color
1–2 identity/accent colors
optional 1 highlight color
cheek/blush tone where useful
dark readable eye/mouth tone
subtle shadow tone
```

Avoid uncontrolled rainbow palettes unless the identity specifically calls for them (for example Lilli’s localized rainbow cue).

Prefer large readable detail to tiny texture noise.

---

## 15. Names and child-facing identity

Recurring Greia character names should generally be:

- short;
- easy to hear;
- easy to pronounce in Italian;
- reasonably pronounceable by children in other supported languages;
- not dependent on a difficult English pun;
- visually/sound-wise distinct from one another.

Do not create dozens of named mascots when a generic reusable creature/object can do the job.

---

## 16. Asset reuse before creation

Before creating a new character, prop, scene element or effect:

1. inspect the current Greia asset catalogues/library;
2. reuse an existing semantic asset if it fits;
3. recolor/compose only where the asset contract permits it;
4. create a new asset only when it adds a real semantic/visual need;
5. record provenance/status according to the library contract.

Never create a parallel private copy of a shared asset merely because it is easier in the moment.

---

## 17. Evidence/review checklist

### Character

- [ ] silhouette reads at 256 px;
- [ ] silhouette/face still reads at 128 px;
- [ ] 64 px usage is acceptable where required;
- [ ] face is not dominated by ornament;
- [ ] expression states are distinguishable;
- [ ] body does not require complex anatomy to animate;
- [ ] neutral pose works as a static fallback;
- [ ] color contrast survives the intended scene background.

### Motion

- [ ] semantic meaning is clear on Puff, Bean and Object Friend as applicable;
- [ ] static fallback communicates the state;
- [ ] amplitude stays within the shared design bounds unless a documented exception exists;
- [ ] Object Friend deformation does not damage pedagogical recognition;
- [ ] `sad_gentle` or wrong-choice feedback cannot read as anger/shame/disappointment;
- [ ] no anatomy-specific rig was introduced merely to make the animation work.

### Scene/prop

- [ ] interactive object is recognizable;
- [ ] decoration does not compete with interaction;
- [ ] composition works at 800×600 / 1024×600 where applicable;
- [ ] no accidental giant dead areas;
- [ ] no final debug/prototype art remains;
- [ ] safe system region remains clear.

### UI

- [ ] child target remains large;
- [ ] state is readable without color alone;
- [ ] typography follows Greia roles;
- [ ] depth/shadow does not obscure text/icons;
- [ ] motion is optional enrichment, not essential meaning.

Label review accurately as DESIGN SPEC, SOURCE, DESKTOP VISUAL REVIEW, SIMULATOR VISUAL REVIEW or PHYSICAL VISUAL REVIEW. A local HTML mockup is not physical Greia acceptance.

---

## 18. Explicit failure patterns to avoid

Do not repeat these default approaches without new evidence:

- one-shot AI 8×8 sprite sheet assumed to be a usable animation;
- complex detailed quadruped automatically exploded into precise rig parts;
- programmatic recreation of a beautiful generated animal into visibly unrelated vector geometry;
- generic Pygame tutorial art as final production presentation;
- random new visual language per Activity;
- solving visual quality by assuming a professional art/animation team will appear later;
- adding many animation bones merely because a rigging library permits them;
- judging beauty through deterministic regex/shape-count rules and treating that as a substitute for visual review.

---

## 19. Working process for model-assisted art

When asked to create/refine Greia visuals:

1. identify the semantic role;
2. check asset reuse first;
3. select archetype/style family;
4. write a tiny visual brief: silhouette, face, identity cues, palette, required states;
5. produce the smallest viable component set;
6. inspect neutral/static quality before animation;
7. inspect required expression states;
8. apply existing semantic motions rather than inventing anatomy-specific choreography;
9. check 256/128/64 where relevant;
10. check scene composition at reference viewports;
11. reject visually poor work rather than polishing a broken construction indefinitely;
12. update the active art plan progress ledger after substantive work;
13. commit coherent accepted/reviewable work to GitHub.

The goal is not “fewest shapes possible.” The goal is **the smallest construction that still looks charming, intentional and recognizably Greia**.
