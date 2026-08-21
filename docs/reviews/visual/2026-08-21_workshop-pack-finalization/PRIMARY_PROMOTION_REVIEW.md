# Primary Promotion Review — Workshop Base Art Pack

**Date:** 2026-08-21  
**Reviewed finalization commit:** `e3954b7dd6cb9bb6913db7f0621cb6a2f84487a5`  
**Evidence inspected:** owner attachment ZIP `GREIA_VISUAL_REVIEW_WORKSHOP_PACK_FINALIZATION_2026-08-21.zip`  
**Candidate:** `assets/visual/pack_candidates/workshop/2026-08-21/`

## Disposition

**AUTHORIZED FOR WORKSHOP v0.2 PROMOTION AS A 24-ASSET TOOLBOX WITH 5 DELIBERATE COEXISTENCE PAIRS AND 2 AUTHORING INGREDIENTS.**

The finalization pass resolves the specific defects identified in primary review without reopening the whole pack. The correct promotion is not a 19-for-19 replacement; it is the strongest practical Workshop toolbox.

## Pixel review findings

The final evidence was inspected directly.

### Bounded corrections are accepted

- `workshop.brush.bundle`: the revised five-brush group now reads as a genuine bundled object rather than three unrelated brushes.
- `workshop.paper.stack`: the revised heavy ream now reads as paper volume rather than a single loose sheet.
- Desk lamps: retaining both is correct. The simple baseline lamp keeps a stronger compact silhouette, while the articulated candidate is useful in larger scene contexts.

### Meaningful distinct variants are accepted

Keep both under distinct semantic IDs:

1. `workshop.shelf.open` + `workshop.shelf.cubby`
2. `workshop.blocks.house` + `workshop.blocks.loose`
3. `workshop.note.cork_tile` + `workshop.note.pinned`
4. `workshop.desk_lamp.articulated` + `workshop.desk_lamp.simple`
5. `workshop.window_light.wide` + `workshop.window_light.narrow`

These pairs are not duplicate-quality indecision. They represent genuinely different useful authoring objects or scale/use cases.

### Direct candidate replacements accepted

Promote the 14 proposed direct candidate roles:

- `workshop.workbench`
- `workshop.stool`
- `workshop.easel`
- `workshop.pegboard`
- `workshop.storage.box`
- `workshop.paint.palette`
- `workshop.brush.bundle`
- `workshop.pencil.cup`
- `workshop.paint.jars`
- `workshop.paper.stack`
- `workshop.rug`
- `workshop.window`
- `workshop.wall.base`
- `workshop.floor.base`

### Authoring ingredients accepted

Promote exactly:

- `ingredient.wood` → `ingredients/ingredient_wood_joint.svg`
- `ingredient.paint` → `ingredients/ingredient_paint_dabs.svg`

The wood-joint ingredient is primarily an authoring/reference component, not a requirement that Activities render it directly. The paint-dab ingredient is a useful reusable material accent.

## Promotion shape

Workshop v0.2 should therefore contain:

```text
24 finished semantic assets
= 14 direct candidate replacements
+ 5 retained baseline variants
+ 5 candidate coexistence variants

2 preferred authoring ingredients

0 unresolved roles
```

Preserve Workshop v0.1 unchanged as provenance.

## Composition judgement

The proposed v0.2 room composition is visibly richer and more coherent than the baseline while still reading as an authoring toolbox composition rather than a baked mandatory room. Furniture, tools, window/light, floor/wall and creative props now share a stronger material and lighting language.

No additional Workshop art-refinement pass is authorized before promotion. Do not reopen individual object optimization unless a mechanical promotion defect is discovered.

## Next state

```text
Workshop v0.1 preserved
→ materialize authorized Workshop v0.2 toolbox
→ update pack indexes/docs only
→ do not change runtime consumers merely for source promotion
→ move immediately to Clinic / Care pack reauthoring
```

## Status

- Workshop finalization pixels: **OWNER/PRIMARY REVIEWED**.
- Workshop v0.2 toolbox inventory: **PROMOTION AUTHORIZED**.
- Further Workshop authoring refinement before promotion: **NOT AUTHORIZED / NOT NEEDED**.
- Next content-production family: **Clinic / Care**.
