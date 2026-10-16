# Primary Review — Workshop Base Art Pack Reauthoring

**Date:** 2026-08-21  
**Reviewed candidate commit:** `974965aa3d9fb8934f726a7c03a25731ec2f145a`  
**Evidence inspected:** owner attachment ZIP `GREIA_VISUAL_REVIEW_WORKSHOP_BASE_PACK_REAUTHORING_2026-08-21.zip`  
**Candidate pack:** `assets/visual/pack_candidates/workshop/2026-08-21/`

## Disposition

**PACK-SCALE RESULT: CLEARLY STRONGER THAN WORKSHOP v0.1 OVERALL, BUT NOT A 19-FOR-19 REPLACEMENT.**

The candidate proves the local maintainer agent can also materially improve the Workshop pack at useful pack scale. Furniture/material treatment, room coherence, lighting, rug, window, crate, palette, jars and pencil-cup work are visibly stronger overall than the old baseline.

However, several candidate assets are not actually replacements for the old semantic role; they are different useful objects. For a toolbox, deleting the baseline variant would reduce useful coverage. Workshop v0.2 should therefore be a deliberate promoted toolbox, not a forced one-file-for-one-file swap.

This is again a maintainer-side content-production conclusion only. It is not evidence about arbitrary Activity-authoring agents.

## What is clearly improved

Candidate assets that are visually stronger for their present role include:

- `workshop.workbench` — substantially better construction, grounding and furniture anatomy;
- `workshop.stool` — more believable furniture construction;
- `workshop.easel` — stronger structural anatomy and better scene integration;
- `workshop.pegboard` — cleaner material/functional read;
- `workshop.storage.box` — clearly better crate/box construction;
- `workshop.paint.palette` — stronger material and dimensional read;
- `workshop.pencil.cup` — much better object identity and material distinction;
- `workshop.paint.jars` — clearer glass/container treatment and stronger color presence;
- `workshop.rug` — substantially richer textile read;
- `workshop.window` — stronger architectural identity and more useful storybook presence;
- `workshop.wall.base` and `workshop.floor.base` — materially richer room foundations.

The 1024×600 candidate composition is substantially more convincing and cohesive than the baseline composition. The room now reads as an authored workshop rather than a collection of unrelated icons.

## Roles that must not be treated as simple replacements

### 1. Wall shelf

The v0.1 asset is a compact cubby/cabinet-like wall storage unit. The candidate is an open single-plank bracket shelf. Both are useful and visually distinct.

**Direction:** keep both under distinct semantic roles rather than deleting one.

Suggested semantics:

```text
workshop.shelf.open
workshop.shelf.cubby
```

### 2. Toy blocks

The baseline is a loose stack/pile of blocks. The candidate is a deliberately assembled little house/arch construction. Those are different authoring needs.

**Direction:** keep both as distinct assets.

Suggested semantics:

```text
workshop.blocks.loose
workshop.blocks.house
```

### 3. Pinboard note

The baseline is a lightweight pinned/sticky note. The candidate is effectively a small framed/cork-backed note tile. Both are useful.

**Direction:** keep both if the candidate remains, with distinct IDs.

### 4. Window light

The baseline is a narrower layered beam; the candidate is a broad simple shaft with motes. They provide different composition behavior rather than a clear winner.

**Direction:** retain both as light variants if they remain visually clean.

## Candidate roles that need one bounded correction or deliberate baseline retention

### Brush bundle

The candidate no longer reads as a **bundle**. It is three separate floating/leaning brushes with a shadow beneath them. The baseline, while simpler, actually reads as a contained bundle.

**Direction:** either:

- revise the candidate once so it genuinely reads as a coherent brush bundle/container; or
- keep v0.1 for `workshop.brush.bundle` and expose the candidate under a different role such as `workshop.brush.loose` only if useful.

Do not promote the current candidate as `workshop.brush.bundle` unchanged.

### Paper stack

The candidate reads more like one or two sketch sheets than a stack. The v0.1 role is immediately legible as layered paper.

**Direction:** either:

- strengthen the candidate stack silhouette once; or
- retain the baseline for `workshop.paper.stack` and optionally keep the candidate as a separate `workshop.paper.sketch`/sheet role.

### Desk lamp

The articulated candidate is visually more sophisticated at large size, but the runtime-size sheet shows it becoming extremely thin and nearly disappearing at 64 px. The baseline has much stronger compact readability.

**Direction:** do not declare a universal replacement. Finalization must either:

- prove an appropriate minimum intended display size and keep both simple/articulated variants; or
- retain v0.1 as the compact/default role and keep the candidate as an articulated authoring variant.

## Authoring ingredients

The candidate ingredients should also be selective.

Likely useful:

- `ingredient_wood_joint.svg` — materially useful construction reference/ingredient;
- `ingredient_paint_dabs.svg` — useful painterly/creative-prop ingredient.

The pinned-note and light-shaft ingredients should be retained only if finalization demonstrates that they add reusable value beyond the finished assets themselves.

## Pack-level conclusion

The important pack question is answered positively: **the local maintainer agent is producing a better Workshop art family than the old v0.1 baseline overall.**

The final pack should now optimize the **toolbox**, not a replacement percentage.

A good Workshop v0.2 may contain more than 19 finished assets because meaningful old/new variants can coexist where their semantic function differs. That is preferable to discarding a useful cubby shelf, loose blocks or compact lamp merely because a newer drawing exists.

The correct continuation is exactly one bounded finalization/promotion-candidate pass:

```text
strong direct candidate replacements
+ meaningful baseline variants retained under distinct semantic IDs
+ one correction/decision for brush bundle, paper stack and lamp
+ selective authoring ingredients
→ owner promotion review
→ Workshop v0.2
→ move to Clinic/Care
```

Do not start a specimen optimization loop.

## Status

- Workshop candidate overall versus v0.1: **DECIDED — CANDIDATE FAMILY STRONGER OVERALL**.
- 19/19 candidate replacement: **REJECTED**.
- Meaningful baseline/candidate coexistence: **REQUIRED WHERE SEMANTICS DIFFER**.
- Next action: **one bounded Workshop finalization gate, then promotion decision**.
