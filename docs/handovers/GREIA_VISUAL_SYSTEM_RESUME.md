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

The generic library is mature enough that raw asset count is not the current bottleneck.

Current indexed state after Batch A admission/discovery tooling:

```text
57 preferred finished assets
37 candidate-reference finished assets
7 preferred authoring ingredients
101 indexed reusable visual resources
```

Discovery helper:

```text
tools/visual_authoring_library.py
```

Focused tests:

```text
tests/test_visual_authoring_library.py
```

No generic Batch B is authorized merely to increase counts.

Promoted source pools include Forest/Meadow v0.3 and Workshop v0.2. Clinic/Reading/Fantasy/Water remain source/provenance pools where appropriate; theme-by-theme production is not the roadmap.

Permanent generic rule:

> **Generic assets encode reusable form; Activity-specific meaning and contents remain separable whenever practical.**

---

# 3. Four-character reauthoring result

Candidate commit:

`59336d1c34e119e04c40b32f2c1901e1dbfb1b60`

Candidate source:

`assets/visual/pack_candidates/canonical_characters/2026-08-22/`

Owner-transfer evidence was inspected at actual pixel level (13 PNGs + review/audit).

Primary review:

`docs/reviews/visual/2026-08-22_canonical-character-cast-reauthoring/PRIMARY_REVIEW.md`

Disposition:

- **Lilli** current candidate → carry forward as stable full-cast anchor;
- **Tito** current candidate → carry forward as stable full-cast anchor;
- **Momo** current candidate → carry forward as stable full-cast anchor;
- **Nino** current owl art → useful source/provenance only; current cast direction supersedes the identity with **Leo**.

The five-state system is accepted as a good design/source foundation:

```text
neutral
blink
happy
surprised
sleepy
```

The six motion storyboards are accepted only as design semantics, not runtime proof:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Important pixel observation: the current owl's large white eye disks/rings dominate the face. Leo's glasses must be integrated into the eye-mask architecture rather than simply layered over the old rings, especially for 64 px readability.

Do not promote the old four-character lineup as the final canonical family before the expanded-cast review.

---

# 4. Current target canonical cast

Current accepted design direction:

```text
Lilli — unicorn      → creativity / stories / art / imagination
Leo   — owl+glasses  → learning / reading / language / knowledge
Flash — rabbit       → games / speed / action / playful challenge
Dani  — robot        → math / logic / patterns / sequencing
Tito  — fox          → exploration / nature / discovery / investigation
Momo  — monster      → emotion / music / silly play / celebration
```

Authority:

`docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`

This is a **soft lead-mascot system**, not six hard silos.

Relationship to the platform-owned Collection-first Home:

```text
create  → Lilli often leads
play    → Flash often leads
learn   → Leo often leads
explore → Tito often leads
```

Dani and Momo are deliberately cross-cutting. `my_greia` remains child/profile-owned and should not be permanently assigned to one mascot.

Do not create six new Home Collections.

---

# 5. Exact current maintainer task

Execute:

```text
docs/testing/2026-08-22_CANONICAL_CAST_EXPANSION_LEO_FLASH_DANI.md
```

This gate must:

1. create **Leo** from the useful owl foundation, with simple signature glasses integrated into the eye-mask/eye treatment;
2. create **Flash** as a silhouette-distinct rabbit, not a Tito recolor or hornless Lilli;
3. create **Dani** as a friendly rounded toy-like robot with readable face first and machine details second;
4. author the same five complete states for Leo/Flash/Dani;
5. preserve Lilli/Tito/Momo candidate art unless a concrete six-cast collision is demonstrated;
6. review all six at 256/128/64 px plus silhouette-only 128/64 proof;
7. show shared motion vocabulary across all six at storyboard/design scope;
8. stop for owner pixel review before runtime promotion or ID migration.

Candidate workspace:

```text
assets/visual/pack_candidates/canonical_cast_expansion/2026-08-22/
```

Required owner ZIP:

```text
GREIA_VISUAL_REVIEW_CANONICAL_CAST_EXPANSION_2026-08-22.zip
```

---

# 6. Character architecture rule

Use:

> **complete authored state art + authoring-time semantic source components + simple whole-character runtime transforms**

Avoid:

- skeletal/bone rigs;
- runtime limb/body-part composition;
- frame-by-frame sprite explosions;
- cloned one-body formulas for every character.

The authoring components are source-authoring resources only.

---

# 7. Runtime boundary and later gate

Do **not** modify runtime manifests/Activities/SceneActor during the current art gate.

After six-cast owner visual acceptance, a separate gate may:

1. promote accepted canonical source states under stable identities;
2. migrate the owl identity from historical `character.nino` to current `character.leo` explicitly and safely;
3. add Leo/Flash/Dani plus accepted states to the explicit build-time rendition manifest;
4. extend renderer-neutral `SceneActorDefinition` only as needed for semantic state/motion selection with whole-body transforms;
5. exercise all runtime/fallback/responsive behavior through the Activity Simulator;
6. consider optional Activity presentation metadata such as lead/supporting canonical characters without changing Collection/package authority.

No runtime skeleton or second visual catalogue is authorized.

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
- generic authoring indexes/tooling are authoring-time facilities, not a second runtime catalogue.

---

# 9. Drift to avoid

- no theme-by-theme pack roadmap;
- no generic Batch B merely to increase counts;
- no hero-tree optimization;
- no Clinic finalization;
- no detailed skeletal character rig;
- no automatic promotion of Nino before Leo review;
- no six-character → six-Home-category mapping;
- no treating maintainer-agent drawing ability as arbitrary-agent evidence;
- no second runtime asset system;
- no background-only Activity polish while gameplay remains primitive.

---

# 10. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual/cast work closes, reorders, or bypasses R7.

No physical Acer/Pi acceptance should be claimed without actual hardware evidence.
