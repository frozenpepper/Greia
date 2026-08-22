# Shape Garden — Real Visual-Authoring Workflow Exercise

**Status:** EXECUTE  
**Date:** 2026-08-22  
**Owner prerequisite:** `docs/reviews/visual/2026-08-22_canonical-cast-v01-final-capture/OWNER_REVIEW.md`  
**Activity:** `activities/shape_garden/` (`org.greia.shape-garden`)  
**Visual-authoring skill:** `skills/greia-visual-authoring/SKILL.md`  
**Activity-authoring skill:** `skills/greia-activity-authoring/SKILL.md`  
**Generic discovery helper:** `tools/visual_authoring_library.py`  
**Evidence class if accepted:** `SIMULATOR VISUAL REVIEW`

## 1. Goal

Exercise Greia's visual-authoring system on a **real existing first-party Activity**, not another proof fixture.

Use Shape Garden to answer the practical question:

> Can an Activity author start from a visual need, discover Greia's generic source toolbox, choose intelligently between reuse/adaptation/original art, use the canonical cast where it genuinely helps, produce economical Activity-local runtime art, and end with a visibly better child-facing Activity through the existing Greia runtime and Simulator?

The outcome must be a materially more polished, coherent, Greia-native Shape Garden while preserving the Activity's intentionally simple geometry/creative interaction.

This is an authoring-workflow exercise and a real product improvement at the same time.

## 2. Why Shape Garden

Current Shape Garden already provides useful constraints:

- real first-party Activity, not test-only code;
- `create` + `learn` presentation membership;
- creativity / geometry / fine-motor education semantics;
- one existing shared semantic visual use (`ui.shadow.soft`);
- intentionally minimal background/soil presentation;
- intentionally simple geometric child-created shapes.

That makes it a clean test of the authoring architecture without requiring new gameplay.

## 3. Read before changing anything

Read in repository-authority order, including at minimum:

```text
AGENTS.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_CANONICAL_CAST_SYSTEM.md
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
skills/greia-visual-authoring/SKILL.md
skills/greia-activity-authoring/SKILL.md
activities/shape_garden/activity.toml
activities/shape_garden/main.py
```

Also inspect the exact generic authoring-library index entries selected during discovery rather than relying on filenames alone.

## 4. Hard boundaries

Do **not**:

- change Shape Garden's educational purpose into a different game;
- add reading requirements to basic child play;
- replace the child's geometric creations with decorative sprites;
- turn the Activity into a complex editor/tool palette;
- implement `lead_character` / `supporting_characters` manifest fields;
- add another generic asset batch merely because a desired prop is absent;
- modify shared generic/canonical source files in place from the Activity;
- make `candidate_reference` art a direct final reuse merely to increase reuse counts;
- introduce runtime SVG rasterization;
- scan source/library directories at Activity runtime;
- add another visual catalogue/cache/renderer;
- continuously resize/rotate raster assets per frame;
- make simulator-only branches in shipping Activity code;
- claim physical Acer/Pi evidence;
- query/run GitHub Actions.

The child-created circles/squares/polygons are **educational content** and may remain clean Pygame geometry. The rule against programmer primitives applies to represented decorative art, not to the actual geometry-learning medium.

## 5. Preserve current functional contracts

At minimum preserve:

- pointer-driven shape placement;
- safe protected Home behavior;
- bounded shape history/current memory behavior;
- language-neutral core interaction;
- current Activity lifecycle/readiness behavior;
- current runtime/API trust boundary;
- responsive reference-canvas behavior;
- low-resource intent;
- current manifest education semantics unless a separate product defect is discovered and documented.

Do not casually add persistence, scoring, menus, text instructions, progression mutation, or new permissions in this visual tranche.

## 6. Baseline evidence before authoring

Before edits:

1. synchronize clean `main`;
2. run the existing relevant validation required by the Activity-authoring skill;
3. load current Shape Garden through the real Activity Simulator;
4. capture baseline pixels at minimum:

```text
tmp/shape-garden-visual-authoring/baseline-1024x600-normal.png
tmp/shape-garden-visual-authoring/baseline-1366x768-compact.png
```

Exercise enough shape placement to make the present visual strengths/weaknesses obvious.

Create a short baseline inventory in the evidence workspace covering:

```text
background / environment
playfield / soil / ground
child-created shapes
shape grounding
ambient detail
canonical-character opportunity (if any)
feedback / delight
Activity-local UI/chrome
launcher icon relevance
```

Do not improve art before this baseline is recorded.

## 7. Mandatory discovery-first workflow

Use the actual discovery helper rather than manually browsing source folders first.

Start with:

```bash
python3 tools/visual_authoring_library.py validate --json
python3 tools/visual_authoring_library.py collections --json
```

Then search based on the baseline visual-needs inventory.

Queries must arise from needs, not from a preselected source pack. Likely semantic needs may include concepts such as:

```text
ground / grass / garden edge
small flowers / foliage / nature detail
sunlight / soft atmosphere
contact / soft shadow
simple framing / container detail
```

These examples are not mandatory asset choices. Search differently if the Activity analysis indicates better needs.

Record every meaningful discovery query and result set in:

`tmp/shape-garden-visual-authoring/discovery-log.json`

For each major visual role, record a decision:

```text
REUSE
COMPOSE_ADAPT
CREATE_ORIGINAL
KEEP_EXISTING_INTENTIONAL
```

Record:

- visual role;
- search query/queries;
- selected semantic asset IDs if any;
- `library_status`;
- source path(s);
- decision;
- short reason;
- whether the resulting runtime art is shared semantic runtime art or Activity-local final art.

### Admission-state enforcement

- `preferred` may be chosen for direct reuse when it genuinely fits;
- `candidate_reference` is reference/adaptation material, not automatic direct final art;
- absence of a perfect asset does **not** authorize a new generic Batch B;
- create Activity-local art when that is the better design choice.

## 8. Visual design objective

The finished Activity should feel like a small **shape garden / playful creative patch**, not flat programmer geometry floating over two solid color bands.

The exact design is for the authoring process to determine, but acceptance expects improvements in several of these dimensions:

- a more convincing but restrained garden/playfield setting;
- better grounding and composition for child-created shapes;
- coherent depth without cluttering the free creative area;
- subtle environmental detail around the edges rather than beneath every shape;
- better use of Greia palette/material/shadow relationships;
- clear visual hierarchy preserving a large uncluttered creation field;
- delightful but cheap ambient life where appropriate;
- a canonical character only if it improves the Activity rather than acting as a compulsory mascot sticker.

Do not fill the screen with generic library clip art. The creative field remains primary.

## 9. Canonical cast exercise — choose, do not force

Inspect `GREIA_CANONICAL_CAST_SYSTEM.md` and decide whether Shape Garden benefits from **one** canonical character as a gentle companion/feedback presence.

Possible semantic fits include:

- Lilli for create/imagination;
- Dani for geometry/patterns;

but the authoring agent must make the decision from the Activity experience.

Rules:

- no manifest lead/support metadata in this gate;
- no character-category ownership rule;
- use existing `character.*` semantic runtime IDs/states/motions if a character is used;
- no new character art;
- no permanent animated obstruction of the creation field;
- reactions should be sparse and meaningful, not constant bouncing noise;
- the Activity remains complete if character motion is disabled.

If no character meaningfully improves Shape Garden, record `NO_CHARACTER_JUSTIFIED` in the authoring audit rather than forcing one.

This decision is evidence for whether package-level character metadata is useful later.

## 10. Activity-local art production

When adapting/creating Activity-specific artwork:

- keep source authoring files inside an appropriate Activity-local source location if the repository convention supports it;
- generate/flatten economical runtime PNG/WebP assets for normal runtime consumption;
- do not rasterize SVG during Activity runtime;
- do not read generic authoring-library TOML/source paths at runtime;
- do not modify shared source masters merely to suit Shape Garden;
- keep provenance/derivation notes sufficient for future maintainers to understand which generic sources informed Activity-local art;
- keep final runtime dimensions and count appropriate to the reference low-resource hardware.

Inspect existing Activity packaging/validation rules before choosing exact local asset paths and loaders. Use an already accepted package-relative mechanism; do not invent a privileged host-path API.

## 11. Runtime architecture

Prefer existing platform primitives and seams:

```text
PygameReferenceCanvas
PygameSceneRenderer / SceneDefinition where layered scene composition is appropriate
semantic shared visual API for already-runtime-shared assets
canonical character SceneActorDefinition where a character is justified
Activity-local flattened runtime art for bespoke/adapted scenery
```

Do not force everything through `SceneDefinition` if a simpler existing Activity-local draw is clearer and cheaper. Conversely, do not manually reproduce a scene/cache subsystem already provided by the platform.

No per-frame file decode/scale.

## 12. Before/after authoring audit

Create:

`docs/reviews/visual/2026-08-22_shape-garden-visual-authoring-workflow/`

The committed review must include an `AUTHORING_AUDIT.md` explaining:

1. baseline weaknesses;
2. discovery queries actually run;
3. selected preferred assets;
4. candidate references used only for adaptation/reference;
5. Activity-local originals/adaptations created;
6. assets deliberately rejected and why;
7. canonical-character decision and rationale;
8. runtime integration path;
9. source-to-runtime flattening/build path;
10. resource/cache/per-frame behavior;
11. whether the real workflow exposed missing discovery metadata, poor taxonomy, or genuine generic-library gaps;
12. whether any discovered gap is `TRUE_MISSING`, `QUALITY_GAP`, `VARIETY_GAP`, or `NO_GAP`;
13. whether `lead_character` / `supporting_characters` metadata now has a concrete use case or remains unnecessary.

Also include machine-readable:

`authoring-audit.json`

with the discovery/decision records.

## 13. Automated verification

Before simulator acceptance run at minimum:

```bash
python3 tools/visual_authoring_library.py validate --json
PYTHONPATH=src python3 tools/validate_activity.py activities/shape_garden
make visual-assets-check
```

Run focused tests for all touched platform modules and Shape Garden-related behavior. If touched code crosses broader Activity/platform contracts, run the corresponding broader tests from `skills/greia-activity-authoring/SKILL.md`.

Before final commit, run:

```bash
make validate
```

Do not claim full project `make verify` unless it is actually run. Record exact commands and exact results.

## 14. Activity Simulator acceptance

Use the **real Greia Activity Simulator** and launch Shape Garden through the normal Shell/Activity lifecycle path.

Required acceptance configurations:

```text
1024×600 normal
1024×600 large
1366×768 compact
1280×800 normal
```

At minimum verify:

- Activity launches/returns cleanly;
- protected Home remains unobstructed and functional;
- pointer placement works across the usable creation field;
- multiple shapes can be placed without visual/input drift;
- no artwork intercepts input unexpectedly;
- composition remains clear before any shapes are placed;
- composition remains usable with many shapes placed;
- character presence/reaction, if used, does not obscure creation;
- motion-disabled/static presentation remains complete;
- no text is required to understand basic play;
- no stretched/cropped Activity-local art;
- no per-frame decode/scale storm;
- no runtime SVG/source-directory dependency;
- frame/cache behavior remains bounded at simulator scope.

## 15. Required visual evidence

Commit 8–12 curated images under the review directory, including at least:

```text
01-before-1024x600.png
02-after-empty-1024x600.png
03-after-active-1024x600.png
04-after-many-shapes-1024x600.png
05-character-or-no-character-proof.png
06-large-1024x600.png
07-compact-1366x768.png
08-normal-1280x800.png
09-motion-disabled.png                 # if character/ambient motion exists
10-runtime-fallback.png                # if a newly added optional visual has a meaningful fail-soft path
```

Do not manufacture a fallback test for art that is deliberately required and has no separate safe optional path. The evidence set should correspond to the actual implementation.

The before/after comparison must make the product improvement visible without relying on prose.

## 16. Owner transfer bundle

Create an uncommitted root ZIP:

`GREIA_VISUAL_REVIEW_SHAPE_GARDEN_AUTHORING_WORKFLOW_2026-08-22.zip`

Include only:

- curated before/after/runtime PNGs;
- `AUTHORING_AUDIT.md`;
- `authoring-audit.json`;
- concise simulator trace/results needed for owner review.

Do not include the whole project, source-library dump, generated caches, or unrelated logs.

## 17. Documentation corrections required in this tranche

The visual plans currently contain stale sequencing because the generic discovery helper and skill integration already exist.

As part of this tranche, update the living documents accurately:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

Required corrections:

- mark canonical cast v0.1 simulator runtime acceptance closed via the owner review;
- mark Batch A selective admission / discovery helper / skill integration complete where source truth supports it;
- make this Shape Garden workflow exercise the exact current visual-authoring gate until owner-reviewed;
- keep **Generic Batch B unauthorized** unless the exercise demonstrates a specific real gap;
- append progress rather than rewriting historical failed experiments into success.

Update `skills/greia-visual-authoring/SKILL.md` only if the real exercise exposes guidance that is genuinely missing or misleading. Do not edit it merely to create churn.

## 18. Stop conditions

Stop and report rather than improvising if:

- the generic discovery helper cannot validate the current library;
- Shape Garden can only use selected generic assets by introducing runtime source scanning/SVG rasterization;
- package validation rejects the intended Activity-local asset structure and no existing accepted pattern resolves it;
- the visual redesign materially changes the educational mechanics;
- the only way to include a canonical character is to add package metadata or a new runtime architecture;
- responsive presentation cannot keep the creative field usable;
- an asset fault remains unrecovered after testing;
- the Simulator cannot load the updated Activity through the canonical lifecycle path.

Preserve evidence and record the blocker instead of writing a PASS narrative.

## 19. Git completion

Work on canonical `main`; do not create a feature branch.

Do not query/use GitHub Actions.

Commit coherent work as it becomes stable so visual/source work is not lost. Before final push:

```bash
git status --short
python3 tools/visual_authoring_library.py validate --json
PYTHONPATH=src python3 tools/validate_activity.py activities/shape_garden
make visual-assets-check
make validate
# plus focused tests required by touched modules
git status --short
```

Pull/rebase and push without force.

Return only a concise completion summary, final pushed SHA, exact test results, review directory, and:

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_SHAPE_GARDEN_AUTHORING_WORKFLOW_2026-08-22.zip
```

The owner decision will be based on the actual before/after/runtime evidence and authoring audit, not a prose claim that the workflow succeeded.
