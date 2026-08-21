# Greia Base Art Pack Reauthoring — Maintainer-Side Plan

**Status:** ACTIVE CONTENT-PRODUCTION TRACK  
**Date:** 2026-08-21  
**Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`

## 1. Why this plan exists

The owner originally asked whether the local maintainer agent could recreate Greia's existing basic visual packs at higher quality than the earlier baseline.

That is the purpose of this track.

The local agent is being used here as a **maintainer-side art-production tool**. Its behavior is not a dependency of Greia and is not evidence about arbitrary future Activity-authoring agents.

The generic Activity-agent workflow is owned separately by:

```text
skills/greia-visual-authoring/SKILL.md
```

Do not conflate the two tracks again.

---

## 2. Current established state

### Forest / Meadow

Forest/Meadow v0.3 is promoted and closed for this content-authoring pass:

```text
23 reauthored candidate roles
+ 5 deliberately retained v0.2 roles
+ 2 preferred authoring ingredients
= 28 promoted semantic roles
```

The retained legacy roles establish the first permanent promotion rule: **newer does not automatically win**. Owner pixel review determines the strongest role-by-role toolbox.

### Workshop

Workshop v0.2 has now been mechanically promoted and is closed for this content-authoring pass.

Promoted toolbox:

```text
24 finished semantic assets
= 14 direct candidate replacements
+ 5 retained baseline variants
+ 5 candidate coexistence variants

2 preferred authoring ingredients
0 unresolved roles
```

The five coexistence pairs establish the second permanent promotion rule: **the strongest toolbox may preserve both old and new assets when they are genuinely different useful objects or scale/use variants.**

### Clinic / Care

Clinic/Care pack-scale reauthoring is complete and owner pixel review has established that the candidate is clearly stronger overall than v0.1.

The producing agent's proposed 17/17 direct replacement is **not accepted**. Owner review identified likely useful coexistence/state pairs for:

```text
heart cushion vs tufted cushion
compact/square window vs arched window
layered/narrow window light vs broad window light
care/first-aid box vs bandage tin
empty basin vs prepared wash basin
```

The current exact task is one bounded Clinic/Care finalization via:

```text
docs/testing/2026-08-21_CLINIC_CARE_PACK_FINALIZATION.md
```

That gate must resolve the semantic toolbox map, directly review both proposed authoring ingredients, correct the crowded composition evidence, and then stop Clinic/Care work for owner promotion review.

The historical v0.1/v0.2/v0.3/hero-tree experiment remains provenance only. No further hero-tree optimization is a milestone of this plan.

---

## 3. Goal

Produce stronger Greia bundled base art packs with:

- better individual asset quality;
- broader useful visual variation;
- strong low-resolution readability;
- good composability;
- coherent Greia style;
- sufficient reusable primitives/references for Activity-authoring agents;
- efficient runtime renditions.

The result should be a better toolbox for future Activity authors, not a giant library containing every possible final object.

---

## 4. Pack order

Current order:

1. **Forest / Meadow** — promoted as v0.3; content-authoring pass closed
2. **Workshop** — promoted as v0.2; content-authoring pass closed
3. **Clinic / Care** — stronger candidate owner-reviewed; bounded finalization active
4. **Reading / Classroom**
5. **Fantasy / Village / Night**
6. **Water / Pond**
7. **Shared UI** — separate, stricter functional review because exact consistency/reuse matters more here
8. cross-pack FX / shadow / light support where genuine gaps remain

Character packs are not part of this environment-pack reauthoring sequence unless separately requested.

---

## 5. Per-pack workflow

### 5.1 Preserve baseline

Do not overwrite the current baseline during candidate creation.

Create a new reauthoring candidate directory with clear provenance.

### 5.2 Inventory roles

Read the current pack README/catalogue and list its role coverage.

The reauthoring pass should preserve or improve useful coverage rather than merely create prettier hero objects.

### 5.3 Recreate the pack at pack scale

Reauthor a coherent representative set in one substantial pass.

Do not spend several iterations perfecting one tree, chair, lamp, shelf or rock while the rest of the pack remains untouched.

Individual fixes are allowed only for obvious defects discovered during visual review.

### 5.4 Preserve variety

A pack should provide useful variation where literal reuse would otherwise become repetitive.

Do not manufacture dozens of near-duplicates merely to inflate the catalogue.

### 5.5 Distinguish replacement from useful coexistence

For every old/new relationship, decide whether the strongest toolbox outcome is:

```text
CANDIDATE_REPLACES
BASELINE_RETAINS
KEEP_BOTH_DISTINCT
UNRESOLVED
```

`KEEP_BOTH_DISTINCT` is appropriate when old and new assets represent meaningfully different authoring objects or useful states/scale roles.

When both survive, give them clear distinct semantic IDs. Do not keep ambiguous duplicate IDs.

The promoted pack may contain more roles than the baseline if the added roles are genuinely useful.

### 5.6 Include authoring ingredients where valuable

A pack may include a small curated set of reusable source-level ingredients/reference pieces when they materially help Activity authors compose bespoke work.

Promote ingredients selectively. A fragment does not become valuable merely because it was created during the pass.

### 5.7 Runtime-size review

Test representative masters at likely runtime sizes. Fine source detail may disappear; silhouette, value hierarchy and material identity should survive.

Where a detailed variant has a larger intended minimum display size, state that explicitly instead of pretending every asset must work equally at 64 px.

### 5.8 Composition proof

Produce at least one representative scene/composition using the candidate/proposed toolbox so we can judge whether the assets work together.

A composition is evidence of pack coherence, not a substitute for individual asset review.

---

## 6. Visual quality requirement

The project judges pixels rather than self-description.

Target:

- polished storybook / toy-diorama quality;
- richer material treatment than the old baseline;
- multiple useful color/value shades;
- believable grounding;
- coherent lighting;
- child-readable silhouettes;
- clean alpha;
- controlled detail;
- visual variety without style drift.

Reject:

- crude primitives;
- obvious floating objects;
- repetitive inflated/blob formulas;
- one generic material gradient applied to everything;
- semantically mislabeled assets merely to preserve one-for-one mapping;
- useful legacy variants discarded solely because a candidate exists;
- pack scenes that look like unrelated icons placed together;
- clipped review evidence;
- prose claiming quality that the screenshots do not show.

---

## 7. Review/evidence contract

Every pack reauthoring/finalization pass must produce a curated owner-review package.

Required evidence should normally include:

- baseline-vs-candidate contact sheet(s);
- candidate/proposed inventory;
- representative detail crops;
- representative runtime-size sheet;
- baseline composition;
- candidate/proposed composition;
- explicit role/promotion map where promotion is being proposed;
- `REVIEW.md`;
- machine-readable audit/manifest.

The local agent must create a project-root ZIP for owner attachment. The ZIP itself is not committed; the underlying curated evidence is committed.

Owner/primary visual review determines promotion.

---

## 8. Promotion

Promotion flow:

```text
baseline pack
→ reauthored candidate pack
→ owner pixel review
→ one bounded finalization if needed
→ exact role/variant promotion map
→ promoted versioned pack
→ manifests/docs updated
```

Rejected assets remain provenance but are not exposed as preferred authoring references.

Legacy assets may be copied into the new promoted pack when owner review deliberately retains them for a role or a distinct semantic variant.

Source-pack promotion does not automatically mean every source asset becomes a shared runtime asset.

---

## 9. Relationship to the user-agent visual skill

This track produces the **better toolbox**.

The generic skill teaches arbitrary Activity-authoring agents **how to use the toolbox**:

```text
inspect pack
→ identify Activity need
→ REUSE, COMPOSE/ADAPT, or CREATE ORIGINAL
→ create Activity-local final art
→ flatten/build efficient runtime asset
→ integrate through Greia runtime boundaries
→ visually review
```

Do not encode local-agent-specific SVG tricks or benchmark behavior into the user skill.

---

## 10. Current exact action

Execute:

```text
docs/testing/2026-08-21_CLINIC_CARE_PACK_FINALIZATION.md
```

This is a bounded semantic/evidence pass only. It must:

- resolve the likely cushion/window/light/bandage-container/basin coexistence decisions;
- directly review both proposed authoring ingredients;
- correct the crowded Clinic composition evidence;
- produce an exact promotion map and owner-review ZIP;
- stop Clinic/Care work for owner promotion review.

After owner promotion review, materialize the strongest Clinic/Care v0.2 toolbox and move immediately to Reading / Classroom rather than reopening Clinic specimen optimization.
