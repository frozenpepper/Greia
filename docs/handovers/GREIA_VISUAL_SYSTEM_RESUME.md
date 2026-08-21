# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-21  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Visual-authoring architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Generic art taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`  
**Maintainer toolbox plan:** `docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md`

---

# 1. Current architecture

There are two separate tracks.

## Track A — maintainer-side generic visual toolbox

The owner's local agent is used to create/improve Greia source art. Its capabilities are not evidence about arbitrary user agents.

Theme/source bundles are provenance pools. The primary authoring-discovery layer is the generic semantic library:

```text
Nature & Landscape
Interiors & Architecture
Furniture & Storage
Everyday Props & Containers
Making, Learning & Play
Lighting, Atmosphere, FX & Shadows
Shared UI
Canonical Characters
```

## Track B — arbitrary Activity-authoring agents

The model/tool-agnostic workflow remains:

```text
inventory Activity needs
→ search generic semantic authoring library
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

# 2. Source-art state

## Forest / Meadow v0.3

Promoted source pool: 28 semantic roles = 23 reauthored + 5 retained legacy; 2 preferred authoring ingredients.

## Workshop v0.2

Promoted source pool: 24 finished assets = 14 direct replacements + 5 retained baseline variants + 5 coexistence variants; 2 preferred ingredients.

## Clinic / Care candidate

Reviewed source pool only. Generic furniture/interior/comfort/container assets may be indexed; medical-specific props remain specialized. Do not create `clinic/v0.2` merely because the candidate exists.

## Reading / Classroom, Fantasy / Village / Night, Water / Pond

Harvested as source pools. They are not current core theme-pack roadmaps.

---

# 3. Generic library state

`assets/visual/authoring_library/` is the canonical generic discovery/index layer.

Full-source harvest commit `2dcf306` reports:

```text
52 preferred finished assets
32 candidate-reference finished assets
5 authoring ingredients
89 total indexed reusable resources
```

The full harvest classified remaining Reading, Fantasy and Water sources and corrected false inventory-gap assumptions.

Owner review:

`docs/reviews/visual/2026-08-21_generic-authoring-library-full-source-harvest/PRIMARY_REVIEW.md`

Important quality observation from actual screenshots:

- Reading books/chair/plant/basket/bookcase exist but are visibly weak `QUALITY_GAP` sources;
- Fantasy bridge/sign/well/lantern roles exist but need reauthoring; night sky/moon/light/sparkles can remain candidate references;
- Water/Pond has useful candidate surface/FX references, while reeds/lily pads/dock/stepping stones are quality gaps;
- several candidate references are intentionally **not** preferred finished assets.

---

# 4. Permanent generic-asset rule

The toolbox must not become a giant clip-art noun warehouse.

> **Generic assets encode reusable form; Activity-specific meaning and contents remain separable whenever practical.**

Examples:

- empty plate/bowl as generic bases rather than food permanently baked in;
- books without readable titles or one fixed story;
- blank signs/boards where Activity/localization should own text;
- general mechanical components rather than one narrowly themed mechanism.

This is an authoring/source-art composability rule. Runtime economy remains: rich source work may be flattened into efficient final runtime assets.

---

# 5. Current accepted gap state

Current important gaps include:

```text
doors / room openings                 TRUE_MISSING
standard dining/desk chair            TRUE_MISSING
books / storybooks                    QUALITY_GAP
soft reading chair / tall bookcase    QUALITY_GAP
potted plant / woven basket           QUALITY_GAP
water botanical/structure roles       QUALITY_GAP
bridge/sign/well/lantern               QUALITY_GAP
basic neutral tableware               TRUE_MISSING
mechanical/manipulative components    TRUE_MISSING / materially under-covered
```

Do not confuse `QUALITY_GAP` with missing inventory.

---

# 6. Exact current maintainer task

Execute:

`docs/testing/2026-08-21_GENERIC_CORE_ESSENTIALS_BATCH_A.md`

This is the first authorized new generic art-production batch after full consolidation.

It contains 16 finished assets across:

- doors/openings;
- standard + soft seating;
- bookcase/books;
- plant/basket;
- **neutral** tableware;
- generic mechanical components.

It is deliberately cross-category and must not turn into a kitchen/classroom/clinic themed pack.

Owner-review ZIP required:

`GREIA_VISUAL_REVIEW_GENERIC_CORE_ESSENTIALS_BATCH_A_2026-08-21.zip`

---

# 7. Generic-library admission

Index structure is canonical. Individual assets use:

```text
preferred
candidate_reference
```

New Batch A assets must remain `candidate_reference` until actual owner pixel review.

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
- generic authoring indexes are an authoring/discovery layer, not a second runtime catalogue.

---

# 9. Do not resume drift

- no theme-by-theme pack roadmap;
- no Clinic finalization;
- no hero-tree optimization;
- no giant generic noun inventory for its own sake;
- no baked arbitrary contents/text in generic bases;
- no treating maintainer-agent performance as user-agent evidence;
- no second runtime asset system;
- no background-only Activity polish while gameplay stays primitive.

---

# 10. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual-content work closes, reorders, or bypasses R7.

No physical Acer/Pi acceptance should be claimed without actual hardware evidence.
