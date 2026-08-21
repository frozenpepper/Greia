# Workshop Base Art Pack Reauthoring — Local Maintainer Agent Runbook

**Date:** 2026-08-21  
**Purpose:** reauthor the complete Workshop base art pack at pack scale, using the owner's local agent as a maintainer-side art-production tool.  
**Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Parent plan:** `docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md`

## 1. Scope and intent

This is the next maintainer-side base-pack task after Forest / Meadow.

It is **not** a benchmark of arbitrary future Activity-authoring agents.

Your job is to answer only:

> can you produce a substantially stronger complete Workshop source pack than the existing Workshop v0.1 baseline, while preserving useful role coverage and creating a better toolbox for future Activity authors?

Do not generalize your particular drawing technique into universal Activity-agent rules.

Work at **pack scale**, not specimen scale.

## 2. Read first

Read:

```text
AGENTS.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md
skills/greia-visual-authoring/SKILL.md
assets/visual/environments/workshop/v0.1/README.md
assets/visual/environments/workshop/v0.1/catalog.toml
assets/visual/environments/workshop/v0.1/COMPOSITION.md
assets/visual/environments/workshop/v0.1/REVIEW.md
```

Inspect every actual Workshop v0.1 source asset before creating replacements.

## 3. Preserve provenance

Do not overwrite:

```text
assets/visual/environments/workshop/v0.1/
```

Create the candidate under:

```text
assets/visual/pack_candidates/workshop/2026-08-21/
```

## 4. Baseline semantic roles

Preserve or improve the useful coverage represented by the current catalogue:

```text
workshop.workbench
workshop.shelf
workshop.paint.palette
workshop.brush.bundle
workshop.pencil.cup
workshop.blocks
workshop.storage.box
workshop.paper.stack
workshop.rug
workshop.desk.lamp
workshop.window
workshop.window.light
workshop.paint.jars
workshop.wall.base
workshop.floor.base
workshop.stool
workshop.pegboard
workshop.easel
workshop.pinboard.note
```

Do not silently drop a role because it is less visually exciting than the hero furniture.

You may add a small number of genuinely useful new source roles or authoring ingredients, but do not inflate the pack with near-duplicates.

## 5. Artistic target

The Workshop should feel like a warm, tactile, creative child's workshop / studio in the Greia world — not a sterile classroom, generic office, vector-icon sheet, or toy catalogue.

Aim for:

- polished storybook / toy-diorama presentation;
- warm, varied wood tones with believable joinery and edge wear where appropriate;
- painted / coated surfaces with material-specific shading;
- paper that reads as layered paper, not white rectangles;
- paint that reads as paint, with color richness and slight irregularity;
- metal lamp parts that read differently from wood and paper;
- textile/rug treatment with soft depth rather than a flat colored oval/rectangle;
- coherent warm light direction;
- grounded furniture and props;
- strong child-readable silhouettes;
- source-scale detail that does not turn into noise at runtime sizes;
- clean alpha on composable props.

Use several color/value shades where the material benefits from them. Avoid one generic linear gradient applied to every object.

## 6. Variety and coherence

The pack should provide a useful toolbox, not one repeated formula.

Examples:

- workbench and shelf should not feel like the same rectangular furniture asset resized;
- pencil cup, paint jars and storage box should have distinct materials/forms;
- stool, easel and desk lamp should have clearly different silhouettes and structures;
- paper, brushes, blocks and palette should be legible at child-facing sizes;
- pegboard and pinboard should be visually useful as mid-background composition elements without becoming clutter walls;
- window light should integrate naturally with the window and room-base language.

Do not force artificial visual variation that breaks the Greia style.

## 7. Composition / derivation value

Remember why these packs exist.

They are not only direct-use finished assets. They are also visual references and ingredients for arbitrary Activity-authoring agents following:

```text
skills/greia-visual-authoring/SKILL.md
```

Where genuinely useful, add a **small curated set of source-level authoring ingredients** such as:

- a good wood joint / edge / bracket treatment;
- shelf-content cluster or container grouping;
- paper-edge / pinned-note treatment;
- paint smear / paint dab source element;
- warm window-light patch or shadow support element.

Only add ingredients that would help an Activity author compose a bespoke object or room element. Do not make an ingredient library for its own sake.

## 8. Runtime-size review

Review representative assets at useful scale tiers, including small child-facing sizes.

At minimum include representatives from:

- large furniture;
- medium prop;
- small tabletop prop;
- room/background element;
- light/atmosphere element.

Fine detail may disappear; silhouette, role, material identity and main value structure must remain.

## 9. Composition proof

Create comparable 1024×600 baseline and candidate Workshop compositions.

The candidate composition should demonstrate a believable room using multiple pack roles, but it is evidence of pack coherence, not a substitute for individual-asset review.

Avoid:

- furniture floating above the floor;
- objects intersecting implausibly;
- light shafts disconnected from the window;
- unreadably tiny tabletop clutter;
- a composition that merely places every asset on screen at once.

## 10. Required review evidence

Create:

```text
docs/reviews/visual/2026-08-21_workshop-base-pack-reauthoring/
```

Required files:

```text
01-pack-overview-baseline.png
02-pack-overview-candidate.png
03-furniture-comparison.png
04-tools-creative-props-comparison.png
05-room-light-background-comparison.png
06-runtime-sizes.png
07-baseline-composition.png
08-candidate-composition.png
09-detail-crops.png
REVIEW.md
audit.json
```

If all roles cannot be shown legibly in these sheets, add at most one extra inventory sheet. Do not omit roles while claiming complete coverage.

## 11. Evidence fairness

Comparison sheets must:

- show baseline and candidate at comparable display sizes;
- use neutral grounds appropriate to the asset;
- label versions without marketing language;
- avoid clipped text;
- expose enough source detail to permit real owner pixel review;
- not hide a weak candidate behind a busy room composition.

## 12. REVIEW.md

Answer conservatively:

1. Which candidate families are visibly stronger than Workshop v0.1?
2. Which candidate roles are weaker or unresolved?
3. Did one repeated material/formula infect too much of the pack?
4. Do wood, paper, paint, metal/textile/light actually read as different materials?
5. Does the candidate provide useful variation without style drift?
6. Which baseline assets, if any, should remain instead of candidate replacements?
7. Which new authoring ingredients, if any, are genuinely useful to future Activity authors?
8. Is the whole pack ready for owner promotion review, or should specific roles remain experimental?

Do not infer owner approval.

## 13. audit.json

Record at least:

- baseline directory;
- candidate directory;
- every baseline semantic role;
- candidate file serving that role;
- any new roles/ingredients;
- any deliberately unchanged or unresolved roles;
- review output paths;
- source dimensions/representation where relevant;
- final pushed commit SHA.

## 14. Owner attachment ZIP

Create at project root:

```text
./GREIA_VISUAL_REVIEW_WORKSHOP_BASE_PACK_REAUTHORING_2026-08-21.zip
```

Include the curated PNGs, `REVIEW.md`, and `audit.json`.

Do not commit the ZIP itself. Commit the candidate pack and underlying review evidence.

Final response must include exactly:

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_WORKSHOP_BASE_PACK_REAUTHORING_2026-08-21.zip
```

## 15. Non-goals

Do not:

- modify Activities;
- modify the scene compositor;
- modify Shell UI;
- change runtime catalogues;
- create a generic Authoring Kit version;
- continue Forest / Meadow art optimization;
- spend the pass perfecting one workbench while the rest stays legacy quality;
- claim your behavior represents arbitrary user agents;
- run GitHub-hosted Actions.

## 16. Return

Commit and push:

- candidate Workshop sources;
- candidate metadata;
- curated review evidence;
- review/audit.

Return:

- exact commit SHA;
- candidate pack path;
- review path;
- concise conservative self-assessment;
- exact owner ZIP path.
