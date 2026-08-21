# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-21  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Visual-authoring architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`  
**Base-pack reauthoring plan:** `docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md`  
**Scene-runtime plan:** `docs/plans/2026-08-21_GREIA_SCENE_COMPOSITION_RUNTIME.md`  
**Parent visual plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`

---

# 1. Resume order

Read:

```text
1. AGENTS.md
2. docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
3. docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
4. skills/greia-visual-authoring/SKILL.md
5. docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md
6. docs/design/GREIA_SCENE_COMPOSITION_RUNTIME.md
7. docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md
8. this file
9. HANDOVER.md
```

Do not resume from chat memory alone.

---

# 2. Critical architectural correction — two tracks

The visual workstream has two different concerns. They must not be conflated again.

## Track A — maintainer-side base art packs

Goal: improve the bundled Greia art packs themselves.

The owner's local agent was benchmarked only to answer:

> can this maintainer-side agent recreate the existing basic art packs at higher quality than the earlier baseline?

The initial Forest/Meadow comparison provided useful evidence that it can improve several environment asset categories.

This is **not evidence about arbitrary future user agents** and must not become a model dependency of Greia.

The later v0.1/v0.2/v0.3/hero-tree refinement loop became too specimen-focused. Preserve it as provenance, but **do not continue hero-tree optimization as a milestone**.

Current maintainer-side next action:

> reauthor the complete Forest/Meadow base pack at pack scale, preserve the old pack, produce comparative evidence, obtain owner pixel review, then move to the next pack.

Plan:

```text
docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md
```

## Track B — generic Activity visual-authoring skill

Goal: teach **arbitrary Activity-authoring agents/models** how to use the Greia visual ecosystem.

The skill must be model/tool agnostic and teach:

```text
inspect available art packs
→ identify Activity visual needs
→ choose REUSE, COMPOSE/ADAPT, or CREATE ORIGINAL
→ create Activity-local final art where needed
→ follow Greia style/readability/grounding rules
→ flatten rich source work into efficient runtime assets
→ integrate through existing Greia package/scene/runtime boundaries
→ visually review actual pixels
```

The skill must not assume the owner's local agent or encode its SVG tricks.

Authority:

```text
skills/greia-visual-authoring/SKILL.md
```

---

# 3. Stable production direction

Greia visual production remains asset-first, but `reuse` does not mean literal clone-everywhere reuse.

Coherence comes from shared style, material treatment, lighting, grounding, typography, visual density and runtime conventions. Variety comes from selective reuse, authoring-time composition/adaptation and original Activity-local assets.

Key principle:

> **rich composition at authoring time; economical composition at runtime.**

Do not create a giant runtime warehouse containing every conceivable final tree, cave, shelf, animal pose or puzzle prop.

---

# 4. Current bundled source coverage

Broad source coverage exists under:

```text
assets/visual/environments/forest_meadow/
assets/visual/environments/workshop/
assets/visual/environments/clinic/
assets/visual/environments/reading_classroom/
assets/visual/environments/fantasy_village_night/
assets/visual/environments/water_pond/
assets/visual/ui/
assets/visual/library/
```

The current legacy packs remain provenance/baseline until stronger candidates are independently reviewed and promoted.

Do not overwrite accepted/current pack sources during candidate creation.

---

# 5. Proven runtime foundation

The runtime side remains useful and should be preserved.

Current architecture includes:

```text
explicit semantic asset catalogues
build-time SVG/source → runtime PNG renditions
bounded Pygame visual cache
SceneDefinition / SceneNode / SceneCamera
PygameSceneRenderer
SceneActorDefinition / actor_scene_sample
```

Important source owners include:

```text
src/greia_platform/assets.py
src/greia_platform/activity_api.py
src/greia_platform/pygame_visual_assets.py
src/greia_platform/scene.py
src/greia_platform/pygame_scene.py
src/greia_platform/scene_actor.py
```

Runtime rules remain:

- no arbitrary runtime source-directory scanning;
- no ordinary target SVG rasterization;
- no per-frame disk decode/scale;
- bounded caches;
- explicit semantic/shared assets;
- Activity-local assets remain contained inside the Activity package;
- extend existing package/scene seams rather than inventing parallel asset loaders.

The runtime architecture is not the current conceptual problem; visual authoring/content organization is.

---

# 6. Nascondino lesson

Nascondino proved scene-runtime plumbing, but also exposed an important visual-authoring failure:

- the shared background improved;
- old primitive gameplay assets remained;
- the result looked like two unrelated visual systems glued together.

The lesson is **not** that Greia must globally ship every possible hollow tree, bush, cave, reed bed or animal asset.

The correct lesson is that an Activity-authoring agent should use the art packs and visual skill to:

- reuse what genuinely fits;
- compose/adapt useful pack pieces;
- create original Activity-local gameplay art where the exact object does not exist;
- integrate all major gameplay visuals into the same visual language.

Do not resume Nascondino migration until the base-art/toolbox and user-agent workflow are ready enough to make that work meaningful.

---

# 7. Local-agent benchmark evidence — correct interpretation

Useful finding:

- the owner's local agent can produce stronger representative Forest/Meadow masters than the original baseline in multiple categories.

Not established:

- that arbitrary other agents can do the same;
- that the owner's agent's exact geometric/SVG techniques should become universal rules;
- that a repeatedly refined hero tree predicts Activity-authoring performance;
- that the candidate Authoring Kit versions are final standards.

The tree benchmark chain is now closed as a workstream.

Preserve these folders as evidence/provenance only:

```text
assets/visual/authoring_candidates/
assets/visual/authoring_kit/*-candidate/
docs/reviews/visual/2026-08-21_authoring-*/
docs/reviews/visual/2026-08-21_hero-tree-quality-ceiling/
```

Do not let them become the main architecture.

---

# 8. Generic user-agent authoring workflow

The user-agent skill now owns the stable Activity authoring decision:

### REUSE
Use a finished art-pack/shared asset directly when it fits.

### COMPOSE / ADAPT
Use pack assets/primitives/style as ingredients for a bespoke Activity-local master.

### CREATE ORIGINAL
Create new Activity-local art when the library does not provide a good fit.

Then:

```text
review source asset
→ flatten/build efficient runtime rendition
→ integrate through Greia runtime/package seams
→ inspect complete Activity screenshots
```

This is the intended path for people using many different LLMs/agents in the future.

---

# 9. Visual evidence rule

For significant visual work, the producing agent's prose is not evidence.

Use actual screenshots and follow:

```text
docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md
```

Owner-review ZIP packaging remains mandatory where the runbook requests owner/primary pixel review.

Numeric layout claims should come from runtime/source geometry when possible rather than hand transcription.

---

# 10. Current exact next actions

## Maintainer/content track

1. stop hero-tree work;
2. reauthor complete Forest/Meadow candidate pack;
3. produce baseline-vs-candidate pack evidence and owner ZIP;
4. owner reviews actual pixels;
5. promote accepted assets;
6. continue pack-by-pack according to `2026-08-21_BASE_ART_PACK_REAUTHORING.md`.

## User-agent capability track

1. keep `skills/greia-visual-authoring/SKILL.md` model agnostic;
2. improve pack metadata/previews so arbitrary agents can discover useful assets by role;
3. make Activity-local visual integration clean where current runtime/package APIs have gaps;
4. later validate the skill with multiple different agents/models — as a separate compatibility test, not as part of the local-agent pack-production benchmark.

---

# 11. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual authoring correction closes, reorders or bypasses R7.

No physical Acer/Pi acceptance should be claimed unless actually performed.

---

# 12. Do not resume these drift directions

- endless per-tree/per-object optimization;
- treating the local agent as representative of user agents;
- deriving general architecture from one maintainer agent's output quirks;
- building a giant shared runtime warehouse of every final prop;
- background-only Activity polish while gameplay visuals remain primitive;
- rigid geometric authoring templates;
- arbitrary runtime asset discovery;
- second visual catalogue/cache framework;
- more Shell/category micro-polish as a substitute for the actual visual authoring system.
