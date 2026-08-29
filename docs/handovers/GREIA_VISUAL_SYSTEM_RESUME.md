# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-29  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Active visual plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Current Activity visual subplan:** `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md`  
**Current direct repair review:** `docs/reviews/visual/2026-08-29_encyclopedia_owner_direct_repairs/REVIEW.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`

---

# 1. Current focus — Encyclopedia owner-directed golden-master repair

The owner rejected both the original Encyclopedia graphics and the later E2R golden-master visual package after reviewing the actual Simulator pixels.

The E2R run remains valid technical evidence for its exact SHA, but **it is not aesthetic approval and must not be propagated**.

Owner-identified E2R failures:

```text
Home      category worlds did not fit naturally inside the illustrated book
Lion      face/head/mane looked disconnected; tail looked detached
Animals   elephant was not recognizable; adjacent lion was also ambiguous
Gears     wheels did not convincingly look like gears and did not physically mesh
```

The owner explicitly requested that the primary agent make these corrections directly and slowly rather than delegate another visual-authoring pass.

Current rule:

> **Repair only the rejected golden-master source art, inspect actual 1024×600 source renders, and keep E3/E4 blocked. Do not hand the aesthetic work to the local agent.**

Rolling local-agent pointer is intentionally a HOLD notice:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

---

# 2. E1 architecture remains valid

Activity-local source owners:

```text
activities/enciclopedia_greia/enciclopedia_presentation.py
activities/enciclopedia_greia/enciclopedia_services.py
```

Preserve:

```text
PageShellLayout safe zones
bounded VisualLibrary
explicit semantic-id -> runtime PNG mapping
source SVG -> authoring-time PNG build
no runtime SVG
no page-hot-path image decode / smoothscale
semantic PageCommand input
protected Greia Home ownership
```

The owner rejected the artwork, not these boundaries.

---

# 3. Direct corrections now on main

## Home

Commit:

```text
46a937616610b3ce8c089ef8a1f0dc835373b36e
```

The six existing miniature category worlds and their semantic centers were preserved. The illustrated book spread was simply enlarged from roughly `x=120..904 / bottom≈488` to `x=78..946 / bottom≈520`, with a larger grounding shadow and lower bookmark. This directly addresses the owner's instruction that the current cards would fit if the book were wider and slightly taller.

## Animals

Commit:

```text
51f20f0ae6fbf204a155bdf96962d2330985195c
```

The continuous habitat composition and exact selection centers remain unchanged. The weak top-row lion/elephant were redrawn for immediate recognition:

```text
lion      full body + mane/head + legs + attached tail
elephant  large body + oversized ear + attached curved trunk + tusks + four legs + tail
```

## Lion entry

Commits:

```text
a7b8840528118f393aad91bb5b5692d6149799cf
e955d3e3d662d45ff53018a6197a4ed21f659cef
```

The face is nested into one head/mane mass, the muzzle anchors the face, the tail grows continuously from the rump, and visible connected legs/paws make the animal read as one standing lion rather than disconnected pieces.

## Gears

Commits:

```text
bbc3ca209a471202e57adc6630ee79e65da734f0
eab952ea75f6b0d4b67ec27b82ccf27d8bbde39f
```

The separated disc-like wheels were replaced by a compact three-gear train with 12 visible teeth per gear. Adjacent tooth envelopes overlap at two real mesh boundaries. The runtime teaching overlays were moved to those same contacts and the new gear centers.

Current approximate authored mechanism geometry:

```text
blue   center=(385,318), outer radius≈70
orange center=(500,318), outer radius≈56
green  center=(592,318), outer radius≈46

blue↔orange overlap ≈11 px
orange↔green overlap ≈10 px
```

---

# 4. Current source evidence

The four corrected SVGs were rendered locally at 1024×600 using CairoSVG and inspected as actual source art.

Static checks performed:

```text
Home XML parse                         PASS
Animals XML parse                      PASS
Lion XML parse                         PASS
Gears XML parse                        PASS
Home data-target centers               MATCH page semantic centers
Animals data-target centers            MATCH page semantic centers
Gear mesh geometry                     PASS
```

This is **SOURCE/STATIC evidence only**.

Correction record:

```text
docs/reviews/visual/2026-08-29_encyclopedia_owner_direct_repairs/REVIEW.md
```

---

# 5. Critical runtime evidence boundary

The committed runtime PNG pack still corresponds to the rejected E2R source state for Home, Animals, Lion and Gears.

Therefore current truth is:

```text
EDITABLE SOURCE:                         NEWER / OWNER-DIRECTED CORRECTIONS PRESENT
HOME/ANIMALS/LION/GEARS RUNTIME PNGS:    STALE
build_encyclopedia_visual_assets.py --check: EXPECTED TO FAIL UNTIL REBUILD
PREVIOUS E2R SIMULATOR CAPTURES:         STALE FOR CURRENT SOURCE
FINAL-SHA SIMULATOR ACCEPTANCE:          PENDING
OWNER DIRECTION APPROVAL:                NOT GRANTED
E3/E4:                                   BLOCKED
```

Do not call the repaired screens complete/accepted until the runtime pack is regenerated and fresh final-SHA Greia Simulator pixels are reviewed.

---

# 6. Stable generic visual foundation to preserve

Generic toolbox remains:

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

Permanent rules:

- `preferred` is first-choice direct reuse;
- `candidate_reference` is primarily reference/adaptation material;
- Activity-specific hero subjects may remain Activity-local;
- Generic Batch B remains unauthorized unless real demand proves a concrete generic gap.

Canonical cast remains the accepted six-member family:

```text
Lilli
Leo
Flash
Dani
Tito
Momo
```

Stable source:

```text
assets/visual/characters/canonical/v0.1/
```

---

# 7. Stable runtime foundation to preserve

```text
explicit semantic visual catalogues
build-time source/SVG -> runtime PNG renditions
bounded Pygame visual cache
bounded failed-rendition memory
SceneDefinition / SceneNode / SceneCamera
PygameSceneRenderer
SceneActorDefinition / actor_scene_sample
Greia Activity Simulator real Shell/runtime composition
```

Runtime rules:

- no arbitrary runtime source scanning;
- no normal runtime SVG rasterization;
- no per-frame disk decode/scale;
- bounded caches;
- Activity-local assets remain inside Activity packages;
- generic authoring indexes remain authoring-time facilities;
- rich authored art should be flattened/cropped into economical runtime surfaces.

---

# 8. Existing accepted visual work remains valid

The Encyclopedia failure does not invalidate earlier accepted/reviewed visual work, including:

- canonical cast v0.1 runtime acceptance;
- Shape Garden authoring workflow;
- Costruiamo Ponti stress exercise;
- Painting productization;
- launcher Shell/category-navigation work;
- first-party Batch 1 productization (`treno_numeri`, `labirinto_magico`, `acquario_magico`).

The Encyclopedia lesson remains: **mechanical completion and green tests do not establish visual quality.**

---

# 9. Immediate next action

Continue direct owner/primary-agent inspection of the corrected Home, Animals, Lion and Gears source renders.

Do not broaden the page set yet.

When the corrected source-art tranche is worth runtime review:

```text
rebuild canonical six-PNG pack
→ build --check
→ focused Encyclopedia tests
→ required local verification
→ commit/push runtime assets
→ fresh final-SHA real Greia Simulator launch
→ capture only the relevant golden masters
→ owner visual review
```

**No E3/E4 migration before explicit owner approval.**

---

# 10. Drift to avoid

- no 43-page bulk redraw/recapture before golden-master approval;
- no local-agent aesthetic delegation while the current HOLD is active;
- no generated mockup substituted for real repository source art;
- no second runtime asset/cache/scene system;
- no runtime SVG/CairoSVG;
- no generic Batch B by inertia;
- no narration integration in this visual gate;
- no R7/hardware claims from Activity visual work.
