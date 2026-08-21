# Greia Visual Authoring Library Comparison — Local Agent Benchmark

**Date:** 2026-08-21  
**Evidence class:** AUTHORING COMPARISON / OWNER VISUAL REVIEW REQUIRED  
**Architecture authority:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Main visual authority:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`

## Purpose

Determine whether the local authoring agent can create a **better base Greia Visual Authoring Kit** than the current Forest/Meadow source assets.

This is a focused source-art quality benchmark.

It is **not**:

- a runtime integration task;
- a Nascondino rewrite;
- a scene-compositor task;
- a Shell UI task;
- a mass asset-generation task.

The question is simple:

> Can the local agent recreate/reinterpret representative Greia library assets with materially higher visual quality while preserving the Greia visual language and composability?

The answer must come from comparative pixels, not optimistic prose.

---

## 1. Read before doing anything

Read, in order:

```text
AGENTS.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md
skills/greia-visual-authoring/SKILL.md
assets/visual/environments/forest_meadow/v0.2/README.md
assets/visual/environments/forest_meadow/v0.2/REVIEW.md
assets/visual/environments/forest_meadow/v0.2/catalog.toml
```

Inspect the actual current source SVGs before drawing replacements.

Do not infer their appearance from filenames alone.

---

## 2. Do not overwrite the current baseline

The existing pack remains intact:

```text
assets/visual/environments/forest_meadow/v0.2/
```

Create the challenger source pack under:

```text
assets/visual/authoring_candidates/2026-08-21_forest_meadow_comparison/
```

Do not modify or replace the approved/baseline SVG files during this benchmark.

---

## 3. Required comparison assets

Recreate/reinterpret these representative baseline roles.

### A — Hero tree
Baseline:

```text
assets/visual/environments/forest_meadow/v0.2/tree_hero.svg
```

Challenger target:

```text
assets/visual/authoring_candidates/2026-08-21_forest_meadow_comparison/tree_hero.svg
```

### B — Secondary tree
Baseline:

```text
assets/visual/environments/forest_meadow/v0.2/tree_secondary.svg
```

Challenger target:

```text
assets/visual/authoring_candidates/2026-08-21_forest_meadow_comparison/tree_secondary.svg
```

### C — Foliage / bush
Use the current flowering bush as the principal baseline:

```text
assets/visual/environments/forest_meadow/v0.2/bush_flowering.svg
```

Challenger:

```text
assets/visual/authoring_candidates/2026-08-21_forest_meadow_comparison/bush_flowering.svg
```

### D — Rock cluster
Baseline:

```text
assets/visual/environments/forest_meadow/v0.2/rock_cluster_large.svg
```

Challenger:

```text
assets/visual/authoring_candidates/2026-08-21_forest_meadow_comparison/rock_cluster_large.svg
```

### E — Large cloud
Baseline:

```text
assets/visual/environments/forest_meadow/v0.2/cloud_large.svg
```

Challenger:

```text
assets/visual/authoring_candidates/2026-08-21_forest_meadow_comparison/cloud_large.svg
```

### F — Grass / ground edge
Baseline:

```text
assets/visual/environments/forest_meadow/v0.2/grass_edge.svg
```

Challenger:

```text
assets/visual/authoring_candidates/2026-08-21_forest_meadow_comparison/grass_edge.svg
```

### G — Atmosphere
Recreate **one** of these:

```text
assets/visual/environments/forest_meadow/v0.2/fog_strip.svg
assets/visual/environments/forest_meadow/v0.2/sunlight_rays.svg
```

Prefer the one where you believe a materially better authoring treatment can be demonstrated.

### H — Optional interactive authoring study
Only after A–G are genuinely strong, create one **new** forest interaction asset demonstrating the clarified Authoring Kit concept, for example:

```text
hollow_tree_study.svg
```

This should be a bespoke tree/prop assembled in the same visual language, not merely a circular hole pasted onto `tree_hero.svg`.

This optional study is valuable because it demonstrates whether the library can support Activity-specific derivation rather than just exact finished-asset reuse.

---

## 4. Artistic quality requirement — extremely high

This benchmark is specifically intended to test **who is better at creating the base visual library**.

Do not produce placeholders or “good enough” vectors.

Do not optimize for finishing quickly.

For every challenger asset, target **materially higher quality than the baseline**.

### 4.1 Shape and silhouette

Require:

- appealing, intentional silhouette;
- asymmetry and organic variation where appropriate;
- no obvious programmer-art geometry;
- no stack of generic circles pretending to be foliage;
- clear mass hierarchy at small sizes;
- distinctive character without drifting outside Greia.

### 4.2 Color richness

Do **not** use one flat green for a tree or one flat gray for rocks.

Use controlled families of related shades:

- base color;
- lighter local planes / lit areas;
- darker sheltered areas;
- restrained hue variation;
- small warm/cool shifts where appropriate;
- local accents that make the asset feel authored rather than mechanically filled.

Color variation must remain coherent and child-friendly, not muddy or realistic-photo brown/gray noise.

### 4.3 Shading and depth

Target shallow storybook/toy-diorama depth:

- contact/shallow cast shadow where appropriate;
- local form shading;
- edge highlights where useful;
- subtle overlap shadows between major pieces;
- clear front/back relationships;
- no generic glossy SaaS gradients;
- no excessive blur that destroys readability.

### 4.4 Detail

Add **meaningful** detail:

Trees may use:

- bark planes/patches;
- branch hints;
- multiple foliage groups;
- varied leaf masses;
- selective highlights;
- small notches/organic contour variation.

Rocks may use:

- plane separation;
- varied stone shapes;
- restrained cracks/lichen/moss accents;
- distinct light/shadow sides.

Bushes may use:

- multiple leaf masses;
- depth layering;
- controlled flowers/berries;
- internal shade separation.

Do not fill assets with decorative noise just to increase detail count.

### 4.5 Finish quality

Inspect for:

- accidental tangent collisions;
- ugly joins;
- inconsistent stroke weights;
- visibly clipped shadows;
- alpha artifacts;
- tiny meaningless detail;
- inconsistent lighting direction;
- asymmetry that looks accidental rather than organic;
- stretched or squashed primitive reuse.

The challenger should feel like a deliberate illustration asset, not a quick SVG exercise.

---

## 5. Preserve Greia identity

Higher detail is not permission to change the project into another style.

Maintain:

- storybook / felt-board / toy-diorama character;
- warm, playful, child-readable palette;
- clear silhouettes;
- shallow tactile depth;
- restrained outlines where they help readability;
- compatibility with Nunito-based UI and the existing Greia characters;
- visual clarity at 800×600 / 1024×600-class presentations.

Avoid:

- photorealism;
- painterly raster noise;
- dark fantasy rendering;
- hyper-detailed botanical realism;
- generic mobile-game candy gloss;
- flat programmer primitives;
- arbitrary style changes per asset.

---

## 6. Think like an Authoring Kit builder

While creating each challenger, identify reusable ingredients that another Activity-authoring agent could plausibly reuse.

Examples:

```text
canopy cluster language
bark patch treatment
branch/trunk construction grammar
flower cluster treatment
rock-plane treatment
cloud puff construction
edge grass treatment
highlight/shadow recipe
```

Do not necessarily split every ingredient into separate files in this benchmark. But `REVIEW.md` must state which aspects could later become Authoring Kit primitives/recipes.

The goal is not merely “make seven nicer SVGs.”

The goal is to test whether the agent can help build a source system that other agents can derive from.

---

## 7. Render comparable review images

Create review output under:

```text
docs/reviews/visual/2026-08-21_authoring-library-comparison/
```

### 7.1 Individual comparison sheet

Required:

```text
comparison_contact_sheet.png
```

The sheet must show each baseline directly beside its challenger.

Use a consistent neutral/light background and comparable rendered sizes.

For each row/asset include a simple label:

```text
BASELINE
CHALLENGER
```

Do not beautify the challenger with a better background than the baseline.

Do not present them at unequal scales that unfairly favor one version.

### 7.2 Runtime-size comparison sheet

Required:

```text
comparison_runtime_sizes.png
```

Show representative baseline/challenger assets at approximate usage sizes such as:

```text
64 px
128 px
256 px
```

Use the same logical size for baseline and challenger.

This is critical: intricate source art that collapses into visual mush at actual child-facing sizes is not an improvement.

### 7.3 Composition comparison

Create two comparable simple forest compositions:

```text
preview_baseline_scene.png
preview_challenger_scene.png
```

Use approximately the **same composition/layout**, same viewport, same background treatment, and equivalent object roles.

The point is to compare how the asset families work together, not to give the challenger a more favorable scene design.

The preview should be rich enough to expose:

- repeated-shape boredom;
- palette cohesion;
- depth compatibility;
- scale relationships;
- whether details survive in a scene;
- whether the assets feel like one world.

Do not turn this into a complete game scene or runtime integration.

### 7.4 Optional detail sheet

If important differences are hard to see at normal size, create:

```text
comparison_detail_crops.png
```

Use equal magnification for baseline and challenger.

---

## 8. Independent critique before calling anything better

Create:

```text
docs/reviews/visual/2026-08-21_authoring-library-comparison/REVIEW.md
```

For every asset role, write:

- what changed;
- where the challenger is better;
- where it is worse;
- whether extra detail survives at runtime sizes;
- whether style drift occurred;
- whether the challenger is more useful as an Authoring Kit reference/ingredient;
- any concerns about source complexity or runtime flattening.

Do not declare the challenger winner merely because you created it.

Use one of these honest dispositions per asset:

```text
CHALLENGER CLEARLY BETTER
CHALLENGER SLIGHTLY BETTER
ROUGHLY EQUIVALENT
BASELINE BETTER
INCONCLUSIVE
```

The owner/reviewer makes the final decision after examining the ZIP.

---

## 9. Audit file

Create:

```text
docs/reviews/visual/2026-08-21_authoring-library-comparison/audit.json
```

Include at minimum:

- baseline source path;
- challenger source path;
- SVG viewBox / source dimensions;
- rendered comparison sizes;
- review image paths;
- source file byte sizes;
- whether the asset uses gradients/filters/masks;
- any external dependencies (normally none);
- whether it is intended as a finished example, reusable primitive candidate, recipe reference, or a mixture.

This is descriptive metadata, not an automatic quality score.

---

## 10. Quality stop conditions

Do **not** call this benchmark successful if any of these apply:

- challenger tree still looks like circles stacked on a rectangle;
- asset has fewer meaningful shades/depth cues than baseline;
- details become unreadable mush at 128 px;
- challenger is merely baseline traced with extra decorative shapes;
- lighting is internally inconsistent;
- colors become muddy or dull;
- assets cease to feel like Greia;
- source has accidental clipping/alpha defects;
- composition looks less coherent than baseline;
- the challenger is technically complex but not visibly better.

If an asset is weak, revise it substantially before final packaging.

If after serious revision you still cannot improve it, retain the honest `BASELINE BETTER` or `INCONCLUSIVE` judgement. Evidence is more valuable than fake success.

---

## 11. Do not modify runtime/product code

For this benchmark, do not modify:

```text
src/greia_platform/scene.py
src/greia_platform/pygame_scene.py
src/greia_launcher/*
activities/nascondino_bosco/*
```

unless a tiny **review-generation-only** helper is genuinely required, in which case keep it under tooling/review scope and document why.

Do not promote challenger assets into the generated runtime catalogue yet.

This test chooses the better authoring source direction first.

---

## 12. Commit source and curated review evidence

Commit:

```text
assets/visual/authoring_candidates/2026-08-21_forest_meadow_comparison/
docs/reviews/visual/2026-08-21_authoring-library-comparison/
```

Update the relevant visual plan/resume/HANDOVER only with truthful benchmark status.

Do not mark current production assets replaced merely because challenger files exist.

Do not mark the benchmark accepted until owner review has occurred.

---

## 13. Create the owner attachment ZIP — mandatory

After the review files are complete, create this project-root ZIP:

```text
./GREIA_VISUAL_REVIEW_AUTHORING_LIBRARY_COMPARISON_2026-08-21.zip
```

The ZIP must include at least:

```text
comparison_contact_sheet.png
comparison_runtime_sizes.png
preview_baseline_scene.png
preview_challenger_scene.png
REVIEW.md
audit.json
```

Include `comparison_detail_crops.png` if produced.

Use this command from the Greia repository root:

```bash
python3 - <<'PY'
from pathlib import Path
import zipfile

root = Path("docs/reviews/visual/2026-08-21_authoring-library-comparison")
out = Path("GREIA_VISUAL_REVIEW_AUTHORING_LIBRARY_COMPARISON_2026-08-21.zip")

required = [
    "comparison_contact_sheet.png",
    "comparison_runtime_sizes.png",
    "preview_baseline_scene.png",
    "preview_challenger_scene.png",
    "REVIEW.md",
    "audit.json",
]
optional = ["comparison_detail_crops.png"]

missing = [name for name in required if not (root / name).is_file()]
if missing:
    raise SystemExit(f"missing required review files: {missing}")

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for name in required + optional:
        path = root / name
        if path.is_file():
            zf.write(path, arcname=name)

print(out)
PY
```

Do **not** commit this transfer ZIP to Git. The curated source/review files themselves are what belong in Git.

The ZIP exists specifically so the owner can attach the actual screenshots to the primary reviewer for independent pixel inspection.

---

## 14. Final response format

Return:

1. exact commit SHA pushed to `origin/main`;
2. candidate source directory;
3. review directory;
4. concise honest summary of which assets you believe improved and which did not;
5. exact ZIP path.

Your response must contain exactly this line:

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_AUTHORING_LIBRARY_COMPARISON_2026-08-21.zip
```

Do not call the challenger library accepted. Final visual judgement occurs after the owner sends the ZIP to the primary reviewer.
