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

## 2. What the completed benchmark established

The Forest/Meadow comparison showed that the local maintainer agent can produce noticeably stronger representative environment masters than the earlier baseline in several categories, especially:

- trees;
- bushes;
- rocks;
- clouds;
- grass edges;
- atmosphere/light assets.

That is enough to justify using the agent to attempt **pack-level reauthoring**.

The later v0.1/v0.2/v0.3/hero-tree sequence became too specimen-focused. Those files remain provenance/evidence, but **no further hero-tree optimization is a milestone of this plan**.

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

Recommended order:

1. **Forest / Meadow**
2. **Workshop**
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

Do not overwrite the currently accepted/candidate pack during creation.

Create a new reauthoring candidate directory with clear provenance.

### 5.2 Inventory roles

Read the current pack README/catalogue and list its role coverage.

The reauthoring pass should preserve or improve useful coverage rather than merely create prettier hero objects.

### 5.3 Recreate the pack at pack scale

Reauthor a coherent representative set in one substantial pass.

Do not spend several iterations perfecting one tree, chair, lamp, shelf, or rock while the rest of the pack remains untouched.

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

### 5.5 Include authoring ingredients where valuable

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

### 5.6 Runtime-size review

Test representative masters at likely runtime sizes. Fine source detail may disappear; silhouette, value hierarchy and material identity should survive.

### 5.7 Composition proof

Produce at least one representative scene/composition using the candidate pack so we can judge whether the assets work together.

A composition is evidence of pack coherence, not a substitute for individual asset review.

---

## 6. Visual quality requirement

The local agent must aim high, but the project must judge the pixels rather than self-description.

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
- pack scenes that look like unrelated icons placed together;
- clipped review evidence;
- prose claiming quality that the screenshots do not show.

---

## 7. Review/evidence contract

Every pack reauthoring pass must produce a curated owner-review package.

Required evidence should normally include:

- baseline-vs-candidate contact sheet(s);
- candidate asset overview;
- representative detail crops;
- representative runtime-size sheet;
- baseline composition;
- candidate composition;
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
→ limited correction if needed
→ accepted assets promoted
→ manifests/docs updated
```

Rejected assets remain provenance but are not exposed as preferred authoring references.

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

## 10. Exact next action

Stop all further hero-oak refinement.

The next maintainer-side visual-content task is:

> **Reauthor the complete Forest/Meadow base pack as a coherent candidate pack, using the quality lessons from the comparison benchmark but working at pack scale rather than specimen scale.**

The run must preserve the current Forest/Meadow pack, produce a complete candidate inventory and prepare an owner-review ZIP.

After Forest/Meadow owner review, move to the next pack rather than returning to indefinite optimization of one asset.
