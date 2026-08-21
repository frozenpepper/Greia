# Forest / Meadow Base Art Pack — Finalization and Promotion-Candidate Gate

**Date:** 2026-08-21  
**Purpose:** perform one bounded correction/evidence pass on the already-strong Forest/Meadow reauthoring candidate, then prepare a complete promotion decision.  
**Primary review:** `docs/reviews/visual/2026-08-21_forest-meadow-base-pack-reauthoring/PRIMARY_REVIEW.md`  
**Candidate:** `assets/visual/pack_candidates/forest_meadow/2026-08-21/`

## 1. Scope

This is the **last Forest/Meadow authoring pass before promotion review**.

Do not rework the whole candidate pack. Do not return to hero-tree optimization. Do not create another Authoring Kit version.

The owner has already concluded that the candidate is clearly stronger overall than the legacy v0.2 pack. Your job now is only to:

1. close missing owner-review coverage;
2. fix or reject the few weak roles identified in primary review;
3. produce an explicit role-by-role promotion map;
4. prepare complete owner evidence.

After this gate, Forest/Meadow should either be promoted as a deliberate hybrid/new v0.3 or have a very small list of explicitly unresolved roles. Then the content-production track moves to Workshop.

---

## 2. Read first

Read:

```text
AGENTS.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md
docs/reviews/visual/2026-08-21_forest-meadow-base-pack-reauthoring/PRIMARY_REVIEW.md
assets/visual/environments/forest_meadow/v0.2/catalog.toml
assets/visual/pack_candidates/forest_meadow/2026-08-21/catalog.toml
```

Inspect the existing candidate and committed review images before changing anything.

---

## 3. Do not touch already-good families without a real defect

Do not spend this pass refining:

- hero oak merely for more detail;
- granite outcrop merely for more facets;
- log/stump merely for more texture;
- mushrooms merely for more decoration;
- bramble merely for stylistic experimentation.

Those families already establish that the pack-level reauthoring is better than baseline.

Only modify them if you discover an objective packaging/rendering defect.

---

## 4. Roles requiring direct final visual evidence

The previous ZIP mapped these roles but did not show them clearly enough for whole-pack owner promotion.

Create direct neutral-background evidence for at least:

```text
tree.willow.01
ground.grass_edge.01
ground.dirt_patch.01
atmosphere.fog_strip.01
shadow.contact.small.01
shadow.contact.wide.01
fx.fireflies.01
fx.dust_motes.01
fx.falling_leaves.01
```

Show both baseline and candidate at comparable useful size where a baseline exists.

For atmosphere/FX that are hard to judge on white, also show them over an appropriate dark/mid-value neutral scene patch.

---

## 5. Weak roles requiring one decision

### 5.1 Distant treeline

Current concern: candidate is too featureless/smooth relative to the legacy treeline.

Choose exactly one:

- revise candidate once so it has enough crown/rhythm articulation while remaining a quiet far layer; or
- retain the legacy v0.2 asset for this role in the proposed promotion map.

Do not force candidate replacement merely for consistency.

### 5.2 Flower patch

Current concern: candidate is too sparse and line-thin for strong child-scale presence.

Choose exactly one:

- revise candidate once with a stronger grouped patch silhouette while preserving tasteful botanical variety; or
- retain legacy v0.2 for this role.

### 5.3 Fern cluster

Current concern: candidate is botanically better but thin.

Prove it at representative small sizes. If it collapses, revise once or retain baseline.

---

## 6. Composition evidence correction

Regenerate the final candidate 1024×600 composition so:

- no tree appears to grow out of / sit on a foreground rock by accidental overlap;
- foreground/midground grounding is unambiguous;
- sunlight rays remain subtle enough not to dominate the scene;
- comparison intent remains comparable with baseline;
- the scene demonstrates multiple candidate families without becoming a clutter dump.

This is an evidence correction, not an invitation to redesign the pack.

---

## 7. Complete role-by-role promotion map

Create:

```text
docs/reviews/visual/2026-08-21_forest-meadow-pack-finalization/PROMOTION.md
```

and machine-readable:

```text
docs/reviews/visual/2026-08-21_forest-meadow-pack-finalization/promotion-map.json
```

For **every semantic role in the baseline/candidate catalogue**, record exactly one disposition:

```text
CANDIDATE
LEGACY_V0_2
UNRESOLVED
```

For `LEGACY_V0_2` or `UNRESOLVED`, give a one-sentence reason.

The goal is not 100% candidate replacement. The goal is the strongest coherent promoted toolbox.

---

## 8. Complete visual inventory evidence

Create:

```text
docs/reviews/visual/2026-08-21_forest-meadow-pack-finalization/
```

Required outputs:

```text
01-complete-candidate-inventory-a.png
02-complete-candidate-inventory-b.png
03-missing-support-roles-comparison.png
04-treeline-flower-fern-decision.png
05-runtime-support-role-sizes.png
06-final-baseline-composition.png
07-final-candidate-composition.png
08-promotion-summary.png
PROMOTION.md
promotion-map.json
REVIEW.md
audit.json
```

The two complete inventory sheets together must visibly show **every candidate role proposed for promotion** with readable labels. Do not call a sheet “complete” while omitting mapped roles.

---

## 9. REVIEW.md requirements

Answer conservatively:

1. Which roles were revised in this finalization pass?
2. Which roles deliberately retain v0.2 and why?
3. Which roles, if any, remain unresolved?
4. Do all proposed candidate roles now have direct visual evidence?
5. Is the final candidate/hybrid pack ready to promote as Forest/Meadow v0.3?

Do not claim owner approval.

---

## 10. No runtime promotion yet

Do not overwrite `assets/visual/environments/forest_meadow/v0.2/` and do not change runtime catalogues in this gate.

This gate prepares the owner promotion decision only.

After owner review, the primary maintainer will either:

- authorize promotion to a new `v0.3/`; or
- identify a small explicit unresolved list.

---

## 11. Owner attachment ZIP

Create at project root:

```text
./GREIA_VISUAL_REVIEW_FOREST_MEADOW_PACK_FINALIZATION_2026-08-21.zip
```

Include the eight PNGs plus `PROMOTION.md`, `promotion-map.json`, `REVIEW.md`, and `audit.json`.

Do not commit the ZIP itself. Commit the review files and any candidate corrections.

Final response must include exactly:

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_FOREST_MEADOW_PACK_FINALIZATION_2026-08-21.zip
```

---

## 12. Return

Commit and push to canonical `main`:

- only the bounded candidate corrections actually needed;
- complete finalization review evidence;
- promotion map and audit.

Return:

- exact commit SHA;
- roles revised;
- candidate vs legacy retention count;
- unresolved count;
- final review directory;
- exact owner ZIP path.

Then stop Forest/Meadow work and wait for owner promotion review.
