# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-22  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Visual-authoring architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Generic art taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**Character grammar:** `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`  
**Character motion:** `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`  
**Maintainer toolbox plan:** `docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md`

---

# 1. Current architecture

There are two separate tracks.

## Track A — maintainer-side visual source/toolbox production

The owner's local agent is used to create/improve Greia source art. Its capabilities are not evidence about arbitrary user agents.

Theme/source bundles are provenance pools. Generic environment/prop discovery uses the semantic authoring library:

```text
Nature & Landscape
Interiors & Architecture
Furniture & Storage
Everyday Props & Containers
Making, Learning & Play
Lighting, Atmosphere, FX & Shadows
```

Shared UI and Canonical Characters remain separate stronger-consistency families.

## Track B — arbitrary Activity-authoring agents

The model/tool-agnostic workflow is:

```text
inventory Activity needs
→ query/search generic semantic authoring library
→ use canonical Greia character identities/states where appropriate
→ prefer reviewed/preferred resources where they fit
→ inspect candidate/source references as needed
→ REUSE / COMPOSE-ADAPT / CREATE ORIGINAL
→ create Activity-local final art
→ flatten/build efficient runtime rendition
→ integrate through existing Greia package/scene boundaries
→ inspect actual pixels
```

Authority:

`skills/greia-visual-authoring/SKILL.md`

---

# 2. Generic source-art state

## Forest / Meadow v0.3

Promoted source pool: 28 semantic roles = 23 reauthored + 5 retained legacy; 2 preferred authoring ingredients.

## Workshop v0.2

Promoted source pool: 24 finished assets = 14 direct replacements + 5 retained baseline variants + 5 coexistence variants; 2 preferred ingredients.

## Clinic / Care candidate

Reviewed source pool only. Generic furniture/interior/comfort/container assets may be indexed; medical-specific props remain specialized. Do not create `clinic/v0.2` merely because the candidate exists.

## Reading / Classroom, Fantasy / Village / Night, Water / Pond

Harvested as source pools. They are not current core theme-pack roadmaps.

---

# 3. Generic authoring library — current state

`assets/visual/authoring_library/` is the canonical generic discovery/index layer.

Full-source harvest commit `2dcf306` was followed by Core Essentials Batch A and selective admission.

Current indexed state after commit `de37aad978c57b3de88a64ffb1f6cf70c5a89c5b`:

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

The helper supports authoring-time `collections`, `list`, `search`, `show`, `validate`, and `--json` output. It is not a runtime catalogue.

Permanent generic rule:

> **Generic assets encode reusable form; Activity-specific meaning and contents remain separable whenever practical.**

No generic Batch B is authorized merely to increase counts.

---

# 4. Canonical character state — important remaining gap

The four recurring characters are:

```text
Lilli — unicorn Puff
Nino  — owl Bean
Tito  — fox Puff
Momo  — friendly monster Puff
```

Current repository character state is incomplete:

- `assets/visual/specimens/a1/` contains the neutral A1 specimens; they are accepted static style anchors, not frozen final release art;
- `assets/visual/library/catalog.toml` remains `status = "candidate"` and `runtime_consumed = false`;
- each character currently has only one additional authored source state under `assets/visual/characters/<name>/blink.svg`;
- `assets/visual/library/animations.toml` already defines shared semantic motions `idle_bounce`, `blink`, `happy_hop`, `celebrate_pop`, `surprised_wobble`, `sleepy_sway`;
- `GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md` already names first useful visual states `neutral`, `blink`, `happy`, `surprised`, `sleepy`;
- only `character.lilli/default|blink` is currently selected into `assets/catalog/shared_visuals_v1_source.toml` for build-time runtime rendition;
- `SceneActorDefinition` currently supports cheap whole-character idle + blink and deliberately avoids a detailed rig.

This makes the canonical cast a justified maintainer-side art target before producing more generic nouns.

---

# 5. Exact current maintainer task

Execute:

```text
docs/testing/2026-08-22_CANONICAL_CHARACTER_CAST_REAUTHORING_AND_STATE_SET.md
```

This gate is **candidate character art + state + motion-design evidence only**.

Required output:

```text
4 characters × 5 states = 20 complete state SVGs
```

States:

```text
neutral
blink
happy
surprised
sleepy
```

The candidate source masters should expose useful semantic source groups/components while keeping finished states as complete whole-character SVGs.

Motion storyboard evidence must target the existing shared vocabulary:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Do **not** change runtime manifests, Activities or `SceneActorDefinition` during this first art gate.

Owner-transfer ZIP required:

```text
GREIA_VISUAL_REVIEW_CANONICAL_CHARACTER_CAST_2026-08-22.zip
```

After owner pixel review, a separate runtime gate may promote accepted character states and expand renderer-neutral SceneActor semantics through the Activity Simulator.

---

# 6. Character architecture rule

Use:

> **full authored state art + authoring-time semantic source components + simple whole-body runtime transforms**

Avoid:

- skeletal/bone rigs;
- dozens of runtime limb fragments;
- frame-by-frame sprite explosions;
- one cloned body/face formula for all four characters.

The accepted character grammar remains:

> **identity from silhouette + face + two or three strong cues; life from expression + whole-body motion.**

---

# 7. Stable runtime foundation

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

# 8. What follows character art review

If the candidate cast is visually accepted:

1. promote approved canonical state sources under a stable character source location;
2. select all four approved characters/states into the explicit build-time visual rendition manifest;
3. extend `SceneActorDefinition` only as much as needed for semantic state/motion selection using whole-body transforms;
4. exercise state changes and motions through the Greia Activity Simulator;
5. then return to exercising the **user-facing visual-authoring skill/toolbox in a real Activity-authoring workflow**.

Do not use the maintainer character benchmark as proof of arbitrary-agent drawing capability.

---

# 9. Do not resume drift

- no theme-by-theme pack roadmap;
- no Clinic finalization;
- no hero-tree optimization;
- no generic Batch B merely to increase counts;
- no per-object redraw loop for every candidate reference;
- no giant generic noun warehouse;
- no baked arbitrary contents/text in generic bases;
- no treating maintainer-agent performance as user-agent evidence;
- no detailed skeletal character rig;
- no second runtime asset system;
- no background-only Activity polish while gameplay stays primitive.

---

# 10. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual-content/authoring-tooling/character work closes, reorders, or bypasses R7.

No physical Acer/Pi acceptance should be claimed without actual hardware evidence.
