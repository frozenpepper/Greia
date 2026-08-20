---
name: greia-visual-authoring
description: Canonical practical guide for model-assisted Greia character, scene, prop, FX and UI visual design using the constraint-native Greia visual language.
---

# Greia Visual Authoring Skill

**Status:** living derived visual-authoring guide  
**Reviewed:** 2026-08-20  
**Active art plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`

This skill teaches models and contributors how to create Greia visuals without reinventing the art direction for each Activity. It is practical guidance, not a runtime API. Exact implemented asset/runtime contracts remain source-owned; accepted ADRs own architecture/trust boundaries; `docs/design/GREIA_VISUAL_STYLE_GUIDE.md` owns the overall visual language and typography direction.

---

## 1. Mandatory context before visual work

Read, as relevant:

```text
AGENTS.md
docs/DOCUMENTATION.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md
runtime/theme-defaults.toml
assets/catalog/core_icons_v1.toml
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

- one round/oval primary body mass;
- large face area;
- zero/two tiny feet;
- zero/two stub arms/flaps;
- up to three identity attachments.

Good species cues: ears, horn, tuft, tail, markings, whiskers, tiny wing, antennae.

### Bean

Use for upright compact characters such as owls, penguin-like creatures, little helpers or robots.

Construction target:

- one vertical bean/drop mass;
- face in upper half;
- tiny feet;
- optional flap/wing/arm shapes.

### Cutout Critter

Use when a flatter sticker/felt/paper-cut visual is appropriate.

Construction target:

- very few large layers;
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

Prefer Object Friend over inventing an unnecessary animal mascot when the object itself can carry the interaction.

---

## 4. Character complexity limits

Default character budget:

```text
1 main body mass
1 face region
0–2 tiny feet
0–2 tiny arms/wings/flaps
0–3 identity attachments
```

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

### Base face requirements

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

Normal educational mistakes must not use anger, shame or disappointed-at-the-child expressions.

### Expression ingredients

Prefer:

- large eye shapes;
- eyelids;
- pupil direction;
- simple mouth variants;
- cheeks/blush;
- brows or brow-like upper-eye shapes where useful;
- tiny ear/tuft/antenna changes;
- slight whole-body tilt/squash.

Do not compensate for an unreadable face with tiny decorative lines.

### Small-size test

At 128 px, the intended expression must remain obvious. At 64 px, the face/silhouette must still read where 64 px is a supported usage size.

---

## 6. Working core cast anchors

Use these as **style anchors**, not templates to copy mechanically:

- **Lilli** — unicorn Puff: cream body, rainbow cue, horn, wonder/kindness;
- **Nino** — owl Bean: observation, books, thoughtfulness;
- **Tito** — fox Puff: curiosity, exploration, playful cleverness;
- **Momo** — friendly monster fluff: humor, emotion, experimentation.

The names are intentionally simple Italian names that are also easy for many foreign children to pronounce.

A new character should feel like it belongs beside these anchors without merely recoloring one of them.

---

## 7. Motion selection

Use the semantic base motions from the active art plan before inventing bespoke choreography.

### Base Animation Set v0.1

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

These motions should work mostly through:

- whole-body translation/rotation;
- squash/stretch;
- face state;
- tiny appendage response;
- tail/tuft/antenna lag;
- bounded particles/effects.

A motion description should not assume a horse knee, human elbow or species-specific skeleton.

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

Do not proliferate names until the base set is validated across multiple archetypes.

---

## 8. Motion character mapping

Different characters may express the same semantic motion differently.

Examples:

### `celebrate_pop`

- Puff: body hop + stub arms up + happy eyes + sparkles;
- Bean owl: body hop + wings flap + happy eyes;
- Object Friend: squash/pop + face brighten + stars;
- Monster: wobble + antenna bounce + arms flap.

### `surprised_wobble`

- ears may rise;
- owl wings may open slightly;
- antennae may spring apart;
- Object Friend may simply recoil and widen eyes.

Preserve semantic consistency without forcing identical anatomy.

---

## 9. Scene design

Preferred environment logic:

- storybook diorama;
- felt-board/paper-cut layering;
- cozy toy-world composition;
- large background/midground/foreground masses;
- chunky readable props;
- intentional quiet play area.

### Scene hierarchy

A scene should normally establish:

1. background atmosphere/sky/wall;
2. distant simple shapes;
3. middle scene/ground/playfield;
4. interactive props/entities;
5. foreground framing/decorations only where they do not obstruct play;
6. platform-owned system-safe region untouched.

Avoid giant accidental empty regions caused by weak composition. Empty space is fine when it deliberately supports focus.

### Do not ship prototype geometry as represented art

Raw rectangles/circles/polygons are acceptable for:

- hitboxes;
- debug bounds;
- prototype layout;
- intentionally geometric pedagogy.

They are not normally sufficient final representations of:

- trees;
- animals;
- rivers;
- clinics;
- houses;
- bushes;
- bridges;
- furniture;
- vehicles.

Use shared Greia assets/components or create an intentional simple illustration.

---

## 10. Prop design

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

## 11. Effects design

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

## 12. UI illustration rules

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

## 13. Color and detail

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

Avoid uncontrolled rainbow palettes unless the identity specifically calls for them (for example Lilli’s rainbow cue), and even then keep the rainbow localized rather than covering every surface.

Prefer large readable detail to tiny texture noise.

---

## 14. Names and child-facing identity

Recurring Greia character names should generally be:

- short;
- easy to hear;
- easy to pronounce in Italian;
- reasonably pronounceable by children in other supported languages;
- not dependent on a difficult English pun;
- visually/sound-wise distinct from one another.

Do not create dozens of named mascots when a generic reusable creature/object can do the job.

---

## 15. Asset reuse before creation

Before creating a new character, prop, scene element or effect:

1. inspect the current Greia asset catalogues/library;
2. reuse an existing semantic asset if it fits;
3. recolor/compose only where the asset contract permits it;
4. create a new asset only when it adds a real semantic/visual need;
5. record provenance/status according to the library contract.

Never create a parallel private copy of a shared asset merely because it is easier in the moment.

---

## 16. Evidence/review checklist

For a reusable visual asset, inspect at minimum:

### Character

- [ ] silhouette reads at 256 px;
- [ ] silhouette/face still reads at 128 px;
- [ ] 64 px usage is acceptable where required;
- [ ] face is not dominated by ornament;
- [ ] expression states are distinguishable;
- [ ] body does not require complex anatomy to animate;
- [ ] neutral pose works as a static fallback;
- [ ] color contrast survives the intended scene background.

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

### Evidence language

Label review accurately as DESIGN SPEC, SOURCE, DESKTOP VISUAL REVIEW, SIMULATOR VISUAL REVIEW or PHYSICAL VISUAL REVIEW. A local HTML mockup is not physical Greia acceptance.

---

## 17. Explicit failure patterns to avoid

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

## 18. Working process for model-assisted art

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
