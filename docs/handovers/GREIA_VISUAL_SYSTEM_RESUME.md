# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-22  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Visual-authoring architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Generic art taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**Canonical cast system:** `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`  
**Character grammar:** `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`  
**Character motion:** `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`  
**Maintainer toolbox plan:** `docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md`

---

# 1. Architecture

There are two separate visual-authoring tracks.

## Track A — maintainer-side source/toolbox/canonical-cast production

The owner's local maintainer agent may create/improve Greia source art. Its drawing ability is not a product dependency and is not evidence about arbitrary future Activity-authoring agents.

Generic object/environment discovery uses six semantic authoring-library indexes. Shared UI and Canonical Characters remain stronger-consistency families.

## Track B — arbitrary Activity-authoring agents

The model/tool-agnostic workflow remains:

```text
inventory Activity needs
→ query/search generic semantic library
→ use canonical Greia characters/states where appropriate
→ prefer reviewed/preferred resources where they fit
→ inspect candidate/source references as needed
→ REUSE / COMPOSE-ADAPT / CREATE ORIGINAL
→ create Activity-local final art
→ flatten/build efficient runtime rendition
→ integrate through existing Greia package/scene boundaries
→ inspect actual pixels
```

---

# 2. Generic authoring toolbox state

Current indexed state:

```text
57 preferred finished assets
37 candidate-reference finished assets
7 preferred authoring ingredients
101 indexed reusable visual resources
```

Discovery helper:

`tools/visual_authoring_library.py`

No generic Batch B is authorized merely to increase counts.

Permanent rule:

> **Generic assets encode reusable form; Activity-specific meaning and contents remain separable whenever practical.**

---

# 3. Canonical character work completed so far

## Four-character state-system foundation

Candidate commit:

`59336d1c34e119e04c40b32f2c1901e1dbfb1b60`

Primary review:

`docs/reviews/visual/2026-08-22_canonical-character-cast-reauthoring/PRIMARY_REVIEW.md`

Accepted foundation:

```text
neutral
blink
happy
surprised
sleepy
```

and storyboard/design motion vocabulary:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Lilli/Tito/Momo carry forward. Historical Nino source remains provenance; current owl identity is Leo.

## Six-character expansion

Candidate commit:

`cfbb9512723353dd34f6081c174410401e290ca8`

Candidate source:

`assets/visual/pack_candidates/canonical_cast_expansion/2026-08-22/`

Owner-transfer ZIP was inspected at actual pixel level.

Primary review:

`docs/reviews/visual/2026-08-22_canonical-cast-expansion/PRIMARY_REVIEW.md`

Accepted without another art pass:

- **Lilli** — current candidate anchor;
- **Leo** — integrated glasses/eye-mask identity works;
- **Dani** — friendly toy-robot identity works;
- **Tito** — current candidate anchor;
- **Momo** — current candidate anchor.

Flash's **structure** also works:

- rabbit silhouette;
- long ears;
- pom tail;
- spring-loaded posture;
- five-state system;
- motion compatibility;
- separation from Tito/Lilli in silhouette proof.

One owner-directed identity correction remains: current raspberry fur reads too much like a colored mascot rather than an immediately familiar rabbit.

---

# 4. Current canonical cast target

```text
Lilli — unicorn                        → creativity / stories / art / imagination
Leo   — owl with integrated glasses   → learning / reading / language / knowledge
Flash — white rabbit + lightning top  → games / speed / action / playful challenge
Dani  — friendly robot                → math / logic / patterns / sequencing
Tito  — fox                           → exploration / nature / discovery / investigation
Momo  — monster                       → emotion / music / silly play / celebration
```

This is a **soft lead-mascot system**, not six hard silos.

Platform-owned Home remains:

```text
create
play
learn
explore
my_greia
```

Do not create six Home Collections.

---

# 5. Exact current maintainer task

Execute:

```text
docs/testing/2026-08-22_FLASH_WHITE_RABBIT_IDENTITY_REVISION.md
```

This is the **last intended pure-art cast correction before promotion**.

Required Flash direction:

```text
white / warm-white rabbit fur
+ pink inner ears
+ simple coral/raspberry shirt or sleeveless top
+ one large yellow/gold lightning bolt
+ preserve long ears / pom tail / spring-loaded posture / five states
```

Do not add racing numbers, controllers, stopwatch props, shoes, shorts, gloves, headbands, helmets, capes, permanent speed trails or other costume clutter.

Do not alter Lilli, Leo, Dani, Tito or Momo during this gate unless a concrete owner-visible blocker makes that unavoidable.

Required owner ZIP:

```text
GREIA_VISUAL_REVIEW_FLASH_WHITE_RABBIT_REVISION_2026-08-22.zip
```

---

# 6. Character architecture rule

Use:

> **complete authored state art + authoring-time semantic source components + simple whole-character runtime transforms**

Avoid:

- skeletal/bone rigs;
- runtime limb/body-part composition;
- runtime clothing systems;
- frame-by-frame sprite explosions;
- cloned one-body formulas.

Flash's shirt/bolt may be source-master groups. They are not runtime wardrobe pieces.

---

# 7. Immediate gate after Flash approval

If the revised Flash pixels are owner-approved, **do not create another pure-art cast gate** unless a concrete visual blocker is identified.

Move directly to:

1. stable six-character source promotion;
2. explicit Nino→Leo current-identity migration while preserving historical provenance;
3. build-time PNG rendition selection for all accepted states;
4. renderer-neutral semantic state/motion support using whole-body transforms;
5. Activity Simulator acceptance for state changes, motions, responsive behavior and fail-soft cases;
6. only then consider optional `lead_character` / `supporting_characters` Activity presentation metadata.

---

# 8. Stable runtime foundation

Preserve:

```text
explicit semantic asset catalogues
build-time SVG/source → runtime PNG renditions
bounded Pygame visual cache
SceneDefinition / SceneNode / SceneCamera
PygameSceneRenderer
SceneActorDefinition / actor_scene_sample
```

Runtime rules remain:

- no arbitrary runtime source scanning;
- no normal runtime SVG rasterization;
- no per-frame disk decode/scale;
- bounded caches;
- Activity-local assets remain inside Activity packages;
- generic authoring indexes/tooling remain authoring-time facilities, not a second runtime catalogue.

---

# 9. Drift to avoid

- no theme-by-theme pack roadmap;
- no generic Batch B merely to increase counts;
- no hero-tree optimization;
- no Clinic finalization;
- no detailed skeletal character rig;
- no runtime wardrobe system;
- no six-character → six-Home-category mapping;
- no treating maintainer-agent drawing ability as arbitrary-agent evidence;
- no second runtime asset system;
- no background-only Activity polish while gameplay remains primitive.

---

# 10. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual/cast work closes, reorders, or bypasses R7.

No physical Acer/Pi acceptance should be claimed without actual hardware evidence.
