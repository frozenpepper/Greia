# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-22  
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

The model/tool-agnostic workflow is:

```text
inventory Activity needs
→ query/search generic semantic authoring library
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

# 3. Generic library state before Batch A admission

`assets/visual/authoring_library/` is the canonical generic discovery/index layer.

Full-source harvest commit `2dcf306` reported:

```text
52 preferred finished assets
32 candidate-reference finished assets
5 authoring ingredients
89 total indexed reusable resources
```

Full-harvest owner review:

`docs/reviews/visual/2026-08-21_generic-authoring-library-full-source-harvest/PRIMARY_REVIEW.md`

Permanent rule:

> **Generic assets encode reusable form; Activity-specific meaning and contents remain separable whenever practical.**

Do not confuse `QUALITY_GAP` with missing inventory.

---

# 4. Generic Core Essentials Batch A — completed and owner-reviewed

Candidate commit:

`574f19530ee292a81225ff14c09ad8b35f6cf933`

The actual owner-transfer ZIP PNGs were inspected.

Primary review:

`docs/reviews/visual/2026-08-21_generic-core-essentials-batch-a/PRIMARY_REVIEW.md`

Owner disposition:

```text
9 finished assets → preferred
7 finished assets → candidate_reference
2 authoring ingredients → preferred
```

Preferred finished assets:

```text
interior.door.timber.closed
interior.opening.arch.simple
furniture.seating.chair.spindle_wood
furniture.storage.bookcase.tall_open
prop.storage.basket.woven_empty
prop.tableware.bowl.ceramic_empty
prop.tableware.cup_saucer.ceramic
component.mechanical.gears.interlocking_pair
component.mechanical.dial_hands.blank
```

Preferred ingredients:

```text
ingredient.hardware.door_hinge_handle
ingredient.mechanical.axle_hands
```

Keep as candidate references without redraw:

```text
interior.door.timber.ajar
furniture.seating.armchair.soft_reading
prop.book.open.picture_book
prop.books.stack.mixed
prop.decor.plant.potted_fern
prop.tableware.plate.ceramic_empty
component.mechanical.gear.wooden
```

Important visual observations:

- armchair still reads as smooth enlarged-vector/icon furniture;
- potted "fern" is too sparse/spiky to close the botanical quality gap;
- books are useful but still comparatively flat/icon-like;
- plate is semantically correct but too pale at small size;
- single gear's claimed wooden material is not convincing;
- ajar door has useful perspective but a less composition-neutral built-in room reveal.

Do **not** run a Batch A redraw/finalization loop.

---

# 5. Exact maintainer task state

`docs/testing/2026-08-22_GENERIC_VISUAL_LIBRARY_ADMISSION_AND_DISCOVERY_TOOLING.md` is **EXECUTED**.

Delivered:

1. Materialized exactly the 9 preferred finished assets + 2 preferred ingredients as stable generic source under `assets/visual/generic/core_essentials/v0.1/`;
2. Kept the 7 weaker Batch A assets as candidate references pointing to `assets/visual/pack_candidates/generic_core_essentials/2026-08-21/`;
3. Updated the six generic semantic indexes under `assets/visual/authoring_library/` (totaling 55 preferred finished assets, 37 candidate references, and 7 preferred ingredients = 99 reusable visual resources);
4. Added the deterministic authoring-time discovery helper `tools/visual_authoring_library.py` supporting `collections`, `list`, `search`, `show`, and `validate` with `--json`;
5. Added unit/integration tests under `tests/test_visual_authoring_library.py`;
6. Updated `skills/greia-visual-authoring/SKILL.md` to teach arbitrary Activity-authoring agents how to use the discovery helper and respect admission states.

**No Batch B is currently authorized.**

---

# 6. Why tooling comes before more art

The generic toolbox now has enough breadth that raw asset count is no longer the immediate bottleneck.

An arbitrary Activity-authoring agent should not have to know historical theme folders or manually grep six TOMLs. The next product value is making the existing library discoverable by semantic need and exposing which resources are preferred versus candidate references.

After the admission/discovery gate, the next milestone is to exercise the user-facing visual-authoring skill/toolbox in a real Activity-authoring workflow. That future exercise must not be misrepresented as proof that all arbitrary agents have the same drawing capability as the maintainer's local agent.

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

# 8. Do not resume drift

- no theme-by-theme pack roadmap;
- no Clinic finalization;
- no hero-tree optimization;
- no Batch B merely to increase counts;
- no per-object redraw loop for every candidate reference;
- no giant generic noun warehouse;
- no baked arbitrary contents/text in generic bases;
- no treating maintainer-agent performance as user-agent evidence;
- no second runtime asset system;
- no background-only Activity polish while gameplay stays primitive.

---

# 9. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual-content/authoring-tooling work closes, reorders, or bypasses R7.

No physical Acer/Pi acceptance should be claimed without actual hardware evidence.
