# 2026-08-22 — First-Party Activity Visual Audit and Batch 1 Productization

## Status

**ACTIVE LOCAL-AGENT GATE**

This is the next visual-workstream tranche after acceptance of:

- canonical cast v0.1 runtime;
- Shape Garden authoring workflow;
- Costruiamo Ponti authoring stress exercise;
- Painting visual productization;
- Activity title + unique icon contract;
- launcher-shell productization.

The visual system is now sufficiently proven. The next task is to **scale it across the remaining first-party Activities based on measured visual debt**, not to create another proof-only fixture or speculative generic art batch.

---

# 1. Goal

Perform a real Simulator-based visual audit of **all 19 first-party Activities**, then select and productize the **three weakest remaining Activities** in one coherent Batch 1.

Already owner-accepted productization references:

- `activities/shape_garden/`
- `activities/costruiamo_ponti/`
- `activities/painting/`

These three must still appear in the audit matrix as quality references, but **do not re-productize them** unless you discover a concrete regression.

The other first-party Activities are candidates for Batch 1.

---

# 2. Read authorities first

Before making changes, read at minimum:

```text
AGENTS.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
skills/greia-visual-authoring/SKILL.md
skills/greia-activity-authoring/SKILL.md
```

Also inspect the current source/runtime of every Activity before scoring it.

Do not use old screenshots as a substitute for the current Simulator state.

---

# 3. Phase A — Whole-catalogue visual audit

## 3.1 Capture current real pixels

Launch every one of the 19 first-party Activities through the real Greia Activity Simulator / Shell path and capture at least one representative current-state screenshot at **1024×600 NORMAL**.

For Activities with multiple materially different screens/modes, inspect enough states to score them fairly even if only one screenshot is kept in the compact owner contact sheet.

Do not modify Activity visuals until this audit is complete.

## 3.2 Score every Activity

Create:

`docs/reviews/visual/2026-08-22_first-party-activity-visual-audit/visual-audit.json`

and a human-readable:

`docs/reviews/visual/2026-08-22_first-party-activity-visual-audit/VISUAL_AUDIT.md`

For every Activity record:

- Activity ID;
- localized Italian title;
- primary Collection(s);
- screenshot/evidence reference;
- current visual architecture summary;
- strongest visual qualities;
- concrete weaknesses;
- use of shared/generic visuals;
- presence/absence and suitability of canonical character use;
- major `REUSE`, `COMPOSE_ADAPT`, `CREATE_ORIGINAL`, `KEEP_EXISTING_INTENTIONAL` opportunities;
- whether any genuine generic-library gap appears.

Score each Activity **1–5** on these dimensions:

1. `visual_coherence`
2. `depth_and_grounding`
3. `gameplay_entity_quality`
4. `ui_quality`
5. `feedback_and_delight`
6. `greia_style_alignment`
7. `responsive_quality`
8. `overall_product_readiness`

Use actual pixels, not source-code complexity, as the primary quality evidence.

## 3.3 Produce an owner contact sheet

Create one or more compact contact sheets showing all 19 current Activities with title + overall score.

The contact sheet is for rapid owner review, not a substitute for the structured audit.

---

# 4. Select Batch 1 objectively

After the whole-catalogue audit, select the **three weakest remaining Activities** by visual/product readiness.

Selection rules:

- exclude Shape Garden, Costruiamo Ponti, and Painting unless a real regression is found;
- prefer the objectively weakest Activities rather than personal thematic preference;
- if scores are effectively tied, prefer a batch that spans more than one Collection / interaction style so the system is stressed broadly;
- document the exact reason each selected Activity entered Batch 1.

Do **not** choose the three targets before the audit is complete.

Record the selected IDs in:

`docs/reviews/visual/2026-08-22_first-party-activity-visual-audit/BATCH_1_SELECTION.md`

---

# 5. Phase B — Productize the selected three Activities

For each selected Activity independently follow the canonical authoring flow:

```text
visual-needs inventory
→ query generic discovery helper first
→ inspect preferred/candidate references as needed
→ choose REUSE / COMPOSE_ADAPT / CREATE_ORIGINAL / KEEP_EXISTING_INTENTIONAL per role
→ author Activity-local source art where required
→ bake efficient PNG/WebP runtime assets
→ integrate through existing Greia runtime seams
→ inspect actual Simulator pixels
→ refine until clearly improved
```

Use:

```bash
python3 tools/visual_authoring_library.py search ...
python3 tools/visual_authoring_library.py show ...
```

Do not manually browse themed packs first when semantic discovery can answer the need.

## 5.1 Preserve mechanics

Visual productization must not casually rewrite gameplay.

Preserve:

- Activity identity;
- storage/progress/event semantics;
- input behavior;
- platform Home/navigation safety;
- learning/gameplay objectives;
- existing useful mechanics.

Small presentation-tied gameplay-feedback improvements are allowed when they are clearly justified and covered by tests.

## 5.2 Characters

Canonical characters are optional, not mandatory.

Use a mascot only when it adds genuine feedback, storytelling, or affordance without stealing focus.

Do not add character package metadata merely to support this batch.

## 5.3 Activity icon contract

All selected Activities must retain their unique package-owned icon contract.

If the productization changes the Activity's visual identity enough that the existing icon becomes materially misleading, update the icon coherently using the accepted SVG-master → baked PNG path.

Do not regress launcher icon safe padding or title behavior.

---

# 6. Generic-library gap rule

**Generic Batch B remains unauthorized by default.**

A gap may be proposed only if the Batch 1 work demonstrates a genuinely reusable need that cannot reasonably be solved by:

- existing preferred resources;
- candidate references + adaptation;
- Activity-local original art.

A stronger signal is required if the same missing reusable visual role appears independently in **at least two of the three selected Activities**.

If that happens, document it as `GAP_IDENTIFIED`; do not start a new generic batch automatically.

Otherwise end with `NO_GAP`.

---

# 7. Required per-Activity evidence

Create one review directory per selected Activity under:

`docs/reviews/visual/2026-08-22_first-party-batch-1/<activity-folder>/`

For each selected Activity include at minimum:

1. `01-before-1024x600.png`
2. `02-after-main-1024x600.png`
3. `03-after-active-state.png`
4. `04-best-product-proof.png`
5. `05-responsive-1366x768-compact.png`
6. `06-responsive-1280x800-normal.png`
7. `07-static-or-motion-disabled.png` if motion exists; otherwise a meaningful alternate-state proof
8. `08-fail-soft-proof.png`
9. `AUTHORING_AUDIT.md`
10. `authoring-audit.json`
11. `simulator-trace.json`

Add extra screenshots only when they prove a materially different state. Keep the package high-signal.

---

# 8. Batch-level owner review bundle

Create:

`docs/reviews/visual/2026-08-22_first-party-batch-1/OWNER_RECHECK.md`

It must summarize:

- the whole-catalogue audit result;
- selected three targets and why;
- before/after score deltas;
- per-Activity authoring decisions;
- verification results;
- generic gap conclusion.

Create a single root transfer ZIP named exactly:

`GREIA_VISUAL_REVIEW_FIRST_PARTY_ACTIVITY_BATCH_1_2026-08-22.zip`

Include only:

- whole-catalogue audit docs/contact sheet(s);
- `BATCH_1_SELECTION.md`;
- curated evidence for the three selected Activities;
- batch `OWNER_RECHECK.md`.

Do not include the entire project or huge source/runtime dumps in this owner-review ZIP.

---

# 9. Verification

Run relevant focused tests for every modified Activity plus platform visual tests if shared code changes.

At minimum run:

```bash
python3 tools/visual_authoring_library.py validate --json
make visual-assets-check
make validate
```

Also run focused Activity contract tests for all three selected Activities.

If no focused test exists for a selected Activity, add meaningful contract coverage rather than skipping verification.

If shared launcher/platform visual code is touched, run its relevant test suite too.

Report exact test counts/results.

---

# 10. Documentation synchronization — mandatory

The active visual plan currently contains stale historical checkpoint/checklist entries even though later work has already completed them.

At the end of this tranche, reconcile the living visual authorities so another agent sees the actual current state.

Update as appropriate:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

Specifically ensure the plan no longer claims that these are still pending when they are already complete:

- generic discovery helper;
- visual-authoring skill integration;
- real Activity-authoring exercise;
- Shape Garden Simulator acceptance;
- launcher title/icon gate;
- launcher-shell productization.

Do not rewrite history; preserve accepted evidence references and simply bring the active checkpoint/milestone state forward.

---

# 11. Stop conditions

Stop and report rather than forcing through if:

- the audit cannot be completed through the real Simulator path;
- a selected Activity requires unrelated platform architecture work;
- visual changes would break core gameplay semantics;
- a package cannot remain within runtime asset/performance rules;
- the same generic visual gap appears across multiple targets and requires owner authorization before global production.

Partial work must still be committed with an explicit incomplete status and exact evidence/state.

---

# 12. Return contract

When complete, report only:

1. whole-catalogue audit summary and the three selected Activities;
2. concise per-Activity completed-work summary;
3. exact verification results;
4. exact review-directory paths;
5. exact root transfer ZIP name/path;
6. exact commit SHA pushed to `origin/main`.

Do **not** paste this protocol back to the owner.
