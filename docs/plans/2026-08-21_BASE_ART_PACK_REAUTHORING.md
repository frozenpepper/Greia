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

## 2. What the completed work established

The Forest/Meadow pack-scale comparison established that the local maintainer agent can produce a materially stronger environment toolbox than the earlier baseline overall.

Forest/Meadow v0.3 has now been selectively promoted with:

```text
23 candidate roles
+ 5 deliberately retained v0.2 roles
+ 2 preferred authoring ingredients
```

The retained v0.2 roles demonstrate an important promotion rule: **a candidate does not win merely because it is newer.** Owner pixel review determines the strongest role-by-role toolbox.

The later v0.1/v0.2/v0.3/hero-tree experiment remains provenance only. No further hero-tree optimization is a milestone of this plan.

Workshop pack-scale reauthoring has also now demonstrated a stronger candidate family overall, but it exposed a second important rule: some candidate assets are not true replacements at all. A new open shelf is not the same authoring object as an old cubby shelf; an assembled block house is not the same authoring object as loose blocks.

Therefore pack promotion must preserve useful semantic variation instead of forcing replacement percentages.

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

Work pack-by-pack.

Current order:

1. **Forest / Meadow** — promoted as v0.3; content-authoring pass closed
2. **Workshop** — reauthored candidate complete; finalization/promotion review active
3. **Clinic / Care**
4. **Reading / Classroom**
5. **Fantasy / Village / Night**
6. **Water / Pond**
7. **Shared UI** — separate, stricter functional review because exact consistency/reuse matters more here
8. cross-pack FX / shadow / light support where genuine gaps remain

Character packs are not part of this environment-pack reauthoring sequence unless separately requested.

---

## 5. Per-pack workflow

For each pack:

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

Examples:

```text
more than one tree silhouette
more than one bush/growth habit
multiple rock/log/detail forms
foreground and midground roles
large and small room props
quiet support pieces plus hero pieces
```

Do not manufacture dozens of near-duplicates merely to inflate the catalogue.

### 5.5 Distinguish replacement from useful coexistence

Do not assume each candidate file must replace exactly one baseline file.

For every old/new pair, decide whether the strongest toolbox outcome is:

```text
CANDIDATE_REPLACES
BASELINE_RETAINS
KEEP_BOTH_DISTINCT
UNRESOLVED
```

`KEEP_BOTH_DISTINCT` is appropriate when old and new assets represent meaningfully different authoring objects or useful states, for example:

```text
open shelf vs cubby shelf
loose blocks vs assembled block house
simple compact lamp vs articulated studio lamp
narrow light beam vs wide light shaft
```

When both survive, give them clear distinct semantic IDs. Do not keep ambiguous duplicate IDs.

The promoted pack may contain more roles than the baseline if the added roles are genuinely useful. This is preferable to deleting useful variety merely to report a high replacement percentage.

### 5.6 Include authoring ingredients where valuable

In addition to polished finished assets, a pack may include reusable source-level ingredients/reference pieces when they materially help Activity authors compose bespoke work.

Examples:

- foliage clumps;
- trunk/branch pieces;
- stone/moss detail pieces;
- grass/flower groups;
- shelf/content pieces;
- window-light overlays;
- water/reed groups;
- generic shadows/FX.

These are authoring resources, not necessarily direct runtime objects.

Promote ingredients selectively. A source fragment does not become useful merely because it was created during the pack pass.

### 5.7 Runtime-size review

Test representative masters at likely runtime sizes. Fine source detail may disappear; silhouette, value hierarchy and material identity should survive.

Where a detailed variant has a larger intended minimum display size, state that explicitly instead of pretending every asset must work equally at 64 px.

### 5.8 Composition proof

Produce at least one representative scene/composition using the candidate/proposed toolbox so we can judge whether the assets work together.

A composition is evidence of pack coherence, not a substitute for individual asset review.

---

## 6. Visual quality requirement

The local agent must aim high, but the project judges pixels rather than self-description.

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
- explicit role/promotion map;
- `REVIEW.md`;
- machine-readable audit/manifest.

The local agent must create a project-root ZIP for owner attachment. The ZIP itself is not committed; the underlying curated evidence is committed.

Owner/primary visual review determines promotion.

---

## 8. Promotion

Do not automatically overwrite old packs after a candidate pass.

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

---

## 9. Relationship to the user-agent visual skill

This track produces the **better toolbox**.

The generic skill teaches arbitrary Activity-authoring agents **how to use the toolbox**.

The skill must remain model-agnostic even if the owner's local agent happens to create much of the bundled artwork.

The skill should teach:

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

Forest/Meadow source promotion is complete as v0.3 and no longer consumes this content-authoring track.

Workshop candidate review is recorded in:

```text
docs/reviews/visual/2026-08-21_workshop-base-pack-reauthoring/PRIMARY_REVIEW.md
```

The exact current maintainer-side task is:

```text
docs/testing/2026-08-21_WORKSHOP_PACK_FINALIZATION.md
```

This is one bounded pass to:

- resolve brush bundle, paper stack and desk-lamp decisions;
- preserve meaningful shelf/blocks/note/light variants;
- select useful authoring ingredients;
- produce an exact proposed Workshop v0.2 inventory and owner-review ZIP.

After owner promotion review, materialize Workshop v0.2 and move immediately to Clinic/Care rather than reopening Workshop specimen optimization.
