# Painting — Visual Productization Exercise (2026-08-22)

**Status:** ACTIVE TEST / LOCAL-AGENT EXECUTION REQUIRED  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`

## Goal

Execute the third real first-party visual-authoring exercise on `activities/painting/`.

The previous two exercises proved different parts of the authoring system:

- `shape_garden` proved disciplined **REUSE** and gentle canonical-character integration;
- `costruiamo_ponti` proved **COMPOSE_ADAPT** and **CREATE_ORIGINAL** in a scenic puzzle/game.

This gate must now prove the visual-authoring workflow on a **UI-heavy Phase-0 creation Activity**.

The objective is to make Painting feel cute, clear, child-sized, and intentionally designed while preserving its role as a simple fast built-in drawing tool.

## Mandatory read order

Before modifying source, read the repository rules and the relevant visual/product authorities, at minimum:

1. `AGENTS.md`
2. `docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md`
3. `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`
4. `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`
5. `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`
6. `skills/greia-activity-authoring/SKILL.md`
7. `skills/greia-visual-authoring/SKILL.md`
8. `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`
9. the current `activities/painting/` manifest, code, tests, and assets.

## Hard constraints

### Preserve the product role

Painting is a Phase-0 core creation Activity. Keep it:

- simple;
- fast;
- uncluttered;
- child-sized;
- visually delightful;
- faithful to existing creation behavior.

Do **not** turn it into a desktop graphics editor or expand the feature set merely because there is screen space.

### Preserve platform/runtime contracts

Preserve:

- platform-owned Home/system navigation protection;
- Activity identity and package boundaries;
- profile-scoped storage/autosave behavior;
- existing drawing semantics unless a tiny visual-integration adjustment is necessary;
- current trust/input/runtime boundaries;
- low-resource responsiveness.

### Runtime discipline

- no runtime SVG rasterization;
- no arbitrary source-directory scanning at runtime;
- no per-frame disk decode/scale;
- no unbounded caches;
- Activity-local assets stay inside the Activity package;
- reusable shared visuals must be consumed through existing semantic runtime seams;
- any new Activity-local art should use source masters plus build-time runtime renditions where appropriate.

### Mascot use is optional

Do not force a canonical character into Painting. Use one only if it materially improves the child experience without stealing canvas space or cluttering the tool UI. A strong result with no mascot is fully acceptable.

## Required workflow

Use the real visual-authoring workflow, not ad-hoc drawing:

```text
baseline simulator pixels
→ visual-needs inventory
→ query tools/visual_authoring_library.py first
→ inspect preferred/candidate resources only as needed
→ classify major visual roles as REUSE / COMPOSE_ADAPT / CREATE_ORIGINAL / KEEP_EXISTING_INTENTIONAL
→ author Activity-local art where required
→ integrate through existing Greia seams
→ inspect actual Activity Simulator pixels
```

Record the decision class for every major visual role.

## Product-quality targets

Use judgment. Do not blindly implement every item below. The finished Activity should keep the child's drawing as the hero while improving areas such as:

- canvas framing and visual grounding;
- surrounding background/support area;
- clarity and charm of brush/tool/color controls;
- selected/pressed/active states;
- child-readable color affordances;
- subtle visual feedback when selecting a color/tool or beginning a stroke;
- empty-canvas readiness;
- restrained delight that does not compete with artwork;
- responsive presentation across the reference viewports;
- complete static presentation when optional motion is disabled.

Avoid decorative UI that consumes excessive drawing area.

## Baseline requirement

Before changing Painting, capture the current real Activity Simulator baseline at 1024×600 and record concrete weaknesses. Do not reconstruct a fake baseline after implementation.

## Required evidence

Create:

`docs/reviews/visual/2026-08-22_painting-visual-productization/`

Return a curated evidence suite of **at least 12 PNGs** unless a documented legitimate reason makes one scenario impossible.

Required scenarios:

1. `01-before-1024x600.png` — genuine pre-change baseline.
2. `02-after-empty-1024x600.png` — improved empty/ready canvas.
3. `03-after-drawing-in-progress.png` — normal active drawing state.
4. `04-after-rich-drawing.png` — multiple colors/tools/strokes showing the product in real use.
5. `05-tool-palette-selection.png` — selected/active tool and color affordance proof.
6. `06-best-product-proof.png` — strongest screenshot demonstrating the finished child-facing product.
7. `07-responsive-large-1024x600.png` — real `LARGE` interface-size setting.
8. `08-responsive-compact-1366x768.png` — real 1366×768 `COMPACT` presentation.
9. `09-responsive-normal-1280x800.png` — additional responsive proof.
10. `10-static-motion-disabled.png` — if optional animation/delight exists, prove a complete static mode; otherwise document that no optional motion exists and use this slot for another useful product state.
11. `11-optional-visual-fallback.png` — fail-soft proof for one optional authored/shared visual, preferably with full Shell/system context visible.
12. `12-save-resume-or-persistence-proof.png` — visual proof that the visually modified Activity still preserves its core creation/persistence behavior where simulator tooling permits.

If a canonical character is used, add a character-use proof and explain why it improves the Activity. Do not omit another required scenario to make room for it.

## Review documents

The review directory must also contain:

- `AUTHORING_AUDIT.md`
- `authoring-audit.json`
- `simulator-trace.json`
- `OWNER_RECHECK.md` — factual local-agent summary only; final owner acceptance is separate.

Package one root transfer bundle exactly named:

`GREIA_VISUAL_REVIEW_PAINTING_PRODUCTIZATION_2026-08-22.zip`

The ZIP must contain only the curated screenshots and these review documents. Do not dump source trees or generated caches into the review ZIP.

## Mandatory audit content

The audit must state:

- baseline weaknesses;
- exact discovery queries;
- resources inspected;
- final major visual-role classifications;
- generic assets reused;
- candidate-reference assets adapted, if any;
- Activity-local source masters/renditions created;
- canonical-character decision and rationale;
- runtime/cache/rendition strategy;
- focused verification commands and exact results;
- fail-soft/fault-injection procedure and restoration;
- responsive configurations actually run;
- whether product behavior/storage/autosave remained intact;
- explicit generic-library gap assessment.

End the gap assessment with exactly one of:

```text
NO_GAP
```

or

```text
GAP_IDENTIFIED
```

Do not authorize or produce Generic Batch B from this gate. If a genuine reusable gap is identified, document it for owner review instead.

## Verification

Run all relevant focused verification. At minimum:

```bash
python3 tools/visual_authoring_library.py validate --json
PYTHONPATH=src python3 tools/validate_activity.py activities/painting
make visual-assets-check
make validate
```

Also run the closest legitimate focused Painting tests and any tests for touched shared visual/runtime seams. If no Painting-specific test currently exists, say so and add appropriate focused contract coverage rather than pretending it exists.

Do not claim aggregate/full-project PASS for commands you did not actually run.

## Simulator acceptance

Use the real Greia Activity Simulator / child-shell capture path used by the accepted prior visual gates. Screenshots must be real rendered surfaces, not manually reconstructed composites.

For responsive proofs, verify the output dimensions and active interface-size setting before packaging.

For fail-soft proof:

- isolate one optional visual failure;
- do not corrupt unrelated assets;
- verify the Activity remains usable;
- restore/rebuild the asset immediately afterward;
- rerun the relevant validation after restoration.

## Stop conditions

Stop and report rather than improvising if:

- visual improvement would require an unrelated platform architecture change;
- the design becomes more cluttered or meaningfully reduces usable canvas area;
- the protected Home/system region cannot remain untouched;
- the solution requires runtime SVG parsing/source scanning/per-frame asset churn;
- a genuine generic-library gap appears necessary for completion;
- storage/autosave/core drawing behavior regresses.

A stopped run must still leave a project-local review note explaining the blocker.

## Documentation and Git

After successful implementation/review packaging:

1. update `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md` current checkpoint and append-only progress ledger;
2. update `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` with the exact completed/next state;
3. update `HANDOVER.md` where project continuation facts changed;
4. update visual/activity skills only if this exercise exposes a genuinely reusable authoring rule;
5. commit coherent work to `main` and push to `origin/main`.

Do not rewrite prior progress history.

## Return contract

Return only:

1. concise completed-work summary;
2. exact verification results;
3. exact review directory path;
4. exact transfer ZIP path/name;
5. exact commit SHA pushed to `origin/main`.

Do **not** paste this runbook back into chat.
