# Visual Review — Authoring Kit Variation Benchmark

**Date:** 2026-08-21  
**Runbook Authority:** `docs/testing/2026-08-21_VISUAL_AUTHORING_KIT_VARIATION_BENCHMARK.md`  
**Parent Architecture Authority:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Primary Review Authority:** `docs/reviews/visual/2026-08-21_authoring-library-comparison/PRIMARY_REVIEW.md`  
**Evidence Class:** `AUTHORING VARIATION / OWNER VISUAL REVIEW REQUIRED`

---

## 1. Executive Summary: Proving Coherence Without Sameness

This benchmark establishes that the **Greia Visual Authoring Kit** successfully functions as a generative creative grammar rather than a static asset warehouse:

1. **Three Genuinely Distinct Trees from One Kit:**
   - **Broad Old Oak (`tree_broad_oak.svg`):** Heavy, wide asymmetrical trunk with outward buttress root flare ($x=165..415$) supporting a broad, low sheltering canopy.
   - **Slender Young Birch (`tree_slender_birch.svg`):** Graceful, slender bowed trunk with natural bough offshoots supporting upright, airy foliage masses with visible sky windows.
   - **Interactive Hollow Tree (`tree_interactive_hollow.svg`):** Ancient gnarled woodland tree deformed organically around an inviting, thick-rimmed interactive hollow cavity with internal depth shading and a grounded wooden seating floor.
   - *Verdict:* All three read immediately as distinct species with unique silhouettes and roles, while sharing identical warm storybook lighting, bark palette families, and leaf value hierarchies.

2. **Foliage & Rock Variation:**
   - **Bushes:** The low, rounded *Plump Berry Bush* (`bush_plump_berry.svg`) contrasts completely with the upright, tiered *Tall Bramble Bush* (`bush_tall_bramble.svg`) with its visible woody stems and buttercup blossoms.
   - **Rocks:** The rounded *Glacial Boulder Cluster* (`rock_boulder_cluster.svg`) contrasts with the horizontal stepped *Layered Shelf Outcrop* (`rock_shelf_outcrop.svg`), sharing cohesive riverstone tones and integrated velvet moss.

3. **Correction of Primary Review Weaknesses:**
   - **Matte Shading vs. Glossy Inflatable Plastic:** All large, pale specular highlight ellipses have been eliminated. Foliage now uses soft, broad diffuse form shading (`#D5F7C8`, opacity 0.45) consistent with storybook felt-board / matte Gouache painting.
   - **Solid Contact Grounding:** Inward-tapering bases have been eliminated. All ground objects feature flat bases resting solidly in dual-pass contact occlusion shadows.
   - **Architectural Hollow Depth:** The hollow tree features outward trunk deformation, a thick wooden outer rim, a beveled sunlit upper lip highlight, a bottom seating shelf, and a dark vertical cavity gradient (`#241005` down to `#040101`).

---

## 2. Answers to Specific Review Questions

### 1. Do the three trees look genuinely different?
**Yes, unmistakably.** 
- Tree A has a heavy horizontal aspect (~1.3:1) with a thick, grounded buttress trunk and low broad sheltering canopy.
- Tree B has a vertical, airy aspect (~0.8:1) with a slender trunk, natural bow, and separated leaf puffs revealing branch structures and sky windows.
- Tree C is heavily deformed around its interactive hollow cavity, featuring ancient knotted wood grain and a framing canopy tailored for gameplay visibility.
- None look like rescaled clones of each other.

### 2. Is Greia coherence still obvious?
**Yes.** All assets share:
- Consistent top-left diffuse daylight direction;
- Warm cedar/chestnut bark and natural forest green palettes;
- Shallow tactile storybook depth;
- Harmonious integration when composed together on a single 1024×600 canvas (`04-composed-scene.png`).

### 3. Where does the kit still create unwanted sameness?
Canopy billow radii across the oak and hollow tree still share similar arc curvatures in their upper crown crests. The guidance in `materials/foliage.md` has been updated to encourage varying lobe counts and asymmetrical mass weighting across activities.

### 4. Do foliage highlights still feel plastic/glossy?
**No.** Replacing sharp specular ellipses with soft diffuse form shading preserves three-dimensional volume without synthetic shine.

### 5. Do rocks and moss feel integrated?
**Yes.** Moss caps follow stone ledge geometry and creep into crevices naturally rather than sitting as detached green blobs. Crease line opacities have been softened to graphite/slate tones (`#2C373A` opacity 0.40).

### 6. Does the hollow read as a constructed cavity rather than a pasted hole?
**Yes.** The combination of trunk contour bulging, thick outer wooden rim bevel (`#2E1405` / `#52280E`), sunlit upper lip highlight (`#C88E5E`), bottom seating platform (`#754320`), and inner dark falloff creates genuine architectural depth that reads clearly even down to 64px (`03-runtime-sizes.png` and `05-hollow-closeup.png`).

### 7. Which recipes/primitives are actually useful enough to keep?
- `recipes/contact_grounding.md`: Essential guardrail formula across all environment objects.
- `recipes/interactive_hollow.md`: Master pattern for Activity interactive targets.
- `recipes/tree_construction.md`: Highly effective step-by-step assembly guide.
- `materials/foliage.md` & `materials/wood_bark.md`: Core palette and shading standards.

---

## 3. Curated Review Evidence

Committed under `docs/reviews/visual/2026-08-21_authoring-kit-variation/`:
- `01-three-trees.png` (Broad Oak, Slender Birch, Interactive Hollow Tree)
- `02-bush-rock-variation.png` (Plump Berry Bush, Tall Bramble, Boulder Cluster, Shelf Outcrop)
- `03-runtime-sizes.png` (256px, 128px, 64px scale legibility matrix)
- `04-composed-scene.png` (1024×600 cohesive forest meadow composition)
- `05-hollow-closeup.png` (Interactive cavity closeup with authoring callouts)
- `06-material-detail.png` (2.5x close-up inspection of matte foliage, bark flare, moss, and grounding)
- `REVIEW.md`
- `audit.json`

Transfer package assembled at `./GREIA_VISUAL_REVIEW_AUTHORING_KIT_VARIATION_2026-08-21.zip` for owner attachment to ChatGPT for independent pixel inspection.