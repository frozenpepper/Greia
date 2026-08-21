# Visual Review — Workshop Base Pack Reauthoring

**Date:** 2026-08-21  
**Gate:** Maintainer-Side Base Pack Reauthoring Gate  
**Reference Runbook:** `docs/testing/2026-08-21_WORKSHOP_BASE_PACK_REAUTHORING.md`  
**Candidate Directory:** `assets/visual/pack_candidates/workshop/2026-08-21/`  
**Baseline Directory:** `assets/visual/environments/workshop/v0.1/`  
**Review Evidence Directory:** `docs/reviews/visual/2026-08-21_workshop-base-pack-reauthoring/`

---

## 1. Conservative Self-Assessment (Runbook Section 12)

### 1. Which candidate families are visibly stronger than Workshop v0.1?
- **Furniture (Workbench, Shelf, Stool, Easel, Storage Crate, Pegboard):** Every furniture piece now has distinct structural anatomy (chamfered slab top, splayed legs with footrest stretchers, drawer with turned brass knob, scrollwork brackets on shelf, perforated pegboard with hanging wooden tools).
- **Creative Tools & Materials (Palette, Brushes, Pencil Cup, Jars, Paper Stack):** Replaced flat geometric shapes with tactile storybook materials: volumetric glossy paint dollops, turned wood brush handles with aluminum ferrules, glazed teal ceramic mug with terracotta base, and layered cream art paper with a curled sketch sheet.
- **Lighting & Atmosphere (Window, Window Light, Desk Lamp):** The arched wooden window provides an authentic exterior connection to the meadow world, the sunbeam light has soft warm morning diffusion with subtle dust motes, and the desk lamp has believable articulated metal hinges with mint enamel finish.
- **Room Bases (Wall, Floor, Rug):** Wainscot molding on the wall base, wide-plank oak flooring with subtle butt joints, and a braided concentric wool rug provide a cozy, cohesive studio environment.

### 2. Which candidate roles are weaker or unresolved?
- **All 19 baseline roles are resolved and functional.** No roles are broken or missing. 
- *Subtle Note for Owner Review:* The `shelf.svg` candidate opts for an open single-plank bracket shelf with jars/scrolls instead of the baseline closed cabinet cubby; this allows more versatile wall placement and layering behind props.

### 3. Did one repeated material/formula infect too much of the pack?
- **No.** The pack strictly avoids a single universal wood gradient or generic linear fill. Honey-oak workbench wood differs from birch pegboard wood, pine easel struts, dark turned stool legs, and plywood crate edges. Non-wood materials (glazed ceramic, brass, glass, enamel, wool, paper) have material-specific specular highlights, edge bevels, and tactile textures.

### 4. Do wood, paper, paint, metal/textile/light actually read as different materials?
- **Yes.**
  - *Wood:* Defined by grain direction, mortise/tenon joints, chamfered bevels, and warm amber/honey tones.
  - *Paper:* Layered cream sheets with soft drop shadow, curling corner, and graphite sketch doodle.
  - *Paint:* High-contrast specular highlights creating wet, 3D volumetric dollops on palette and glass jars.
  - *Metal/Enamel:* Articulated joints, brass knurling, and smooth sage enamel on desk lamp and knobs.
  - *Textile:* Concentric braided rings with dashed stitching on wool rug.
  - *Light:* Semi-transparent soft golden gradient with floating motes.

### 5. Does the candidate provide useful variation without style drift?
- **Yes.** All assets maintain child-friendly rounded silhouettes, warm storybook color harmony, and clear iconographic clarity matching Greia design grammar.

### 6. Which baseline assets, if any, should remain instead of candidate replacements?
- In our assessment, none of the baseline v0.1 assets outperform the candidate counterparts. However, legacy v0.1 remains preserved under `assets/visual/environments/workshop/v0.1/` for provenance.

### 7. Which new authoring ingredients, if any, are genuinely useful to future Activity authors?
- `ingredient_wood_joint.svg` (mortise & tenon dowel joint) and `ingredient_paint_dabs.svg` (glossy paint dollop cluster) provide high-value modular building blocks for bespoke crafts and UI props.

### 8. Is the whole pack ready for owner promotion review, or should specific roles remain experimental?
- **The candidate pack is complete and ready for owner promotion review.**

---

## 2. Review Sheets Index

- [`01-pack-overview-baseline.png`](01-pack-overview-baseline.png): Complete inventory of all 19 baseline assets.
- [`02-pack-overview-candidate.png`](02-pack-overview-candidate.png): Complete inventory of all 19 candidate assets + ingredients.
- [`03-furniture-comparison.png`](03-furniture-comparison.png): Side-by-side comparison of all 6 furniture assets.
- [`04-tools-creative-props-comparison.png`](04-tools-creative-props-comparison.png): Side-by-side comparison of 7 creative tool and tabletop props.
- [`05-room-light-background-comparison.png`](05-room-light-background-comparison.png): Side-by-side comparison of room bases, lighting, and textiles.
- [`06-runtime-sizes.png`](06-runtime-sizes.png): Multi-scale durability proof (512px, 256px, 128px, 64px).
- [`07-baseline-composition.png`](07-baseline-composition.png): Full 1024x600 scene using baseline v0.1 assets.
- [`08-candidate-composition.png`](08-candidate-composition.png): Full 1024x600 scene using reauthored candidate assets.
- [`09-detail-crops.png`](09-detail-crops.png): High-resolution close-ups of oak joinery, enamel lamp, glazed ceramic, and 3D paint gloss.