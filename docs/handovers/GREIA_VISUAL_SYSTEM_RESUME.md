# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-21  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Visual-authoring architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`  
**Base-pack plan:** `docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md`  
**Scene-runtime plan:** `docs/plans/2026-08-21_GREIA_SCENE_COMPOSITION_RUNTIME.md`

---

# 1. Resume order

Read:

```text
1. AGENTS.md
2. docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
3. docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
4. skills/greia-visual-authoring/SKILL.md
5. docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md
6. docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md
7. this file
8. HANDOVER.md
```

Do not resume from chat memory alone.

---

# 2. Two-track architecture — do not conflate again

## Track A — maintainer-side base art packs

Goal: improve the bundled Greia art packs themselves.

The owner's local agent is used only as a maintainer-side art-production tool. Its performance is **not evidence about arbitrary future Activity-authoring agents** and must not become a Greia model dependency.

Current established content state:

- **Forest/Meadow v0.3 promoted**: 28 semantic roles = 23 reauthored candidate roles + 5 deliberately retained v0.2 roles; 2 preferred authoring ingredients.
- **Workshop v0.2 promoted**: 24 finished semantic assets = 14 direct candidate replacements + 5 retained baseline variants + 5 candidate coexistence variants; 2 preferred authoring ingredients; v0.1 preserved as provenance.
- **Clinic / Care candidate owner-reviewed**: clearly stronger overall than v0.1, but the proposed 17/17 direct replacement is rejected because several old/new pairs are likely useful distinct objects/states.
- **Clinic / Care bounded finalization is now the exact task** via `docs/testing/2026-08-21_CLINIC_CARE_PACK_FINALIZATION.md`.

No more hero-tree/specimen optimization is a milestone.

## Track B — generic Activity visual-authoring skill

Goal: teach arbitrary Activity-authoring models/agents how to use the Greia visual ecosystem.

The model-agnostic workflow is:

```text
inspect available art packs
→ identify Activity visual needs
→ REUSE, COMPOSE/ADAPT, or CREATE ORIGINAL
→ create Activity-local final art where needed
→ follow Greia style/readability/grounding rules
→ flatten rich source work into efficient runtime assets
→ integrate through existing package/scene/runtime boundaries
→ visually review actual pixels
```

Authority:

```text
skills/greia-visual-authoring/SKILL.md
```

---

# 3. Stable production direction

Greia visual production remains asset-first, but reuse does not mean clone-everywhere reuse.

Coherence comes from shared style, material treatment, lighting, grounding, typography, visual density and runtime conventions. Variety comes from selective reuse, authoring-time composition/adaptation and original Activity-local assets.

Key principle:

> **rich composition at authoring time; economical composition at runtime.**

Do not create a giant runtime warehouse containing every conceivable final tree, cave, shelf, animal pose or puzzle prop.

---

# 4. Permanent pack-promotion rules now established

Owner-reviewed pack work has established the promotion policy:

1. **Newer does not automatically win.** Retain a legacy asset when it is visibly stronger for its role.
2. **The goal is the strongest toolbox, not the highest replacement percentage.** Preserve old/new variants together when they are genuinely different useful objects or scale/use cases.
3. Distinct coexisting assets must receive distinct semantic IDs.
4. Useful state variants may coexist when they enable Activity authoring (for example empty versus prepared props).
5. Authoring ingredients are promoted selectively, not automatically.
6. Source-pack promotion does not imply every asset becomes a shared runtime asset.

Use these dispositions during review:

```text
CANDIDATE_REPLACES
BASELINE_RETAINS
KEEP_BOTH_DISTINCT
UNRESOLVED
```

---

# 5. Current bundled source coverage

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

Forest/Meadow v0.3 is the current preferred promoted Forest/Meadow authoring pack. v0.2 remains provenance.

Workshop v0.2 is the current preferred promoted Workshop authoring pack. v0.1 remains provenance.

Clinic / Care v0.1 remains the baseline while the stronger 2026-08-21 candidate undergoes one bounded semantic/evidence finalization.

---

# 6. Runtime foundation remains preserved

Current useful runtime architecture includes:

```text
explicit semantic asset catalogues
build-time SVG/source → runtime PNG renditions
bounded Pygame visual cache
SceneDefinition / SceneNode / SceneCamera
PygameSceneRenderer
SceneActorDefinition / actor_scene_sample
```

Runtime rules remain:

- no arbitrary runtime source-directory scanning;
- no ordinary target SVG rasterization;
- no per-frame disk decode/scale;
- bounded caches;
- explicit semantic/shared assets;
- Activity-local assets remain inside the Activity package;
- extend existing package/scene seams rather than inventing parallel loaders.

The current content-production work must not redesign runtime merely to prove source art.

---

# 7. Nascondino lesson

Nascondino proved useful scene-runtime plumbing but also exposed a visual-authoring failure: the background improved while old primitive gameplay assets remained.

The correct lesson is not to globally ship every possible final prop. Activity-authoring agents should use the packs/skill to reuse, compose/adapt, or create Activity-local gameplay art so environment, interactive objects, characters, feedback and UI belong to one visual language.

Do not resume Nascondino migration until the toolbox/user-agent workflow is mature enough to make that work meaningful.

---

# 8. Visual evidence rule

The producing agent's prose is not evidence.

For meaningful visual work:

- inspect actual screenshots;
- use `docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`;
- prepare owner-review ZIPs when required;
- do not infer visual approval from metadata or self-assessment.

---

# 9. Exact current action

Execute:

```text
docs/testing/2026-08-21_CLINIC_CARE_PACK_FINALIZATION.md
```

This is a bounded semantic/evidence pass only. It must:

1. resolve likely coexistence/state pairs for cushion, window, window light, bandage container and basin;
2. assign distinct semantic IDs where both old/new assets survive;
3. directly show and evaluate both proposed authoring ingredients;
4. correct the crowded candidate room-composition evidence without reopening strong assets;
5. produce an exact promotion map and owner-review ZIP;
6. stop Clinic/Care work and wait for owner promotion review.

After Clinic/Care promotion, move immediately to Reading / Classroom pack reauthoring.

---

# 10. User-agent capability track

Separately:

1. keep `skills/greia-visual-authoring/SKILL.md` model/tool agnostic;
2. improve pack metadata/previews so arbitrary agents can discover useful assets by semantic role;
3. close Activity-local visual integration gaps through existing package/scene architecture;
4. later validate the skill across multiple different agents/models as a separate compatibility exercise.

Do not use maintainer-agent pack-production performance as evidence for this track.

---

# 11. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual authoring/content work closes, reorders or bypasses R7.

No physical Acer/Pi acceptance should be claimed unless actually performed.

---

# 12. Do not resume these drift directions

- endless per-tree/per-object optimization;
- treating the local agent as representative of user agents;
- deriving general architecture from one maintainer agent's drawing quirks;
- building a giant shared runtime warehouse of every final prop;
- forced one-for-one pack replacement;
- background-only Activity polish while gameplay remains primitive;
- rigid geometric authoring templates;
- arbitrary runtime asset discovery;
- second visual catalogue/cache framework;
- Shell/category micro-polish as a substitute for the actual visual-authoring system.
