# Primary Review — Clinic / Care Base Art Pack Reauthoring

**Date:** 2026-08-21  
**Reviewed candidate commit:** `e8cdf2f`  
**Evidence inspected:** owner attachment ZIP `GREIA_VISUAL_REVIEW_CLINIC_CARE_BASE_PACK_REAUTHORING_2026-08-21.zip`  
**Candidate pack:** `assets/visual/pack_candidates/clinic/2026-08-21/`

## Disposition

**PACK-SCALE RESULT: CLEARLY STRONGER THAN CLINIC/CARE v0.1 OVERALL, BUT THE PROPOSED 17/17 DIRECT-REPLACEMENT MODEL IS NOT ACCEPTED.**

The candidate establishes a substantially better Clinic/Care visual family: warmer, richer, more tactile and more useful as a Greia authoring toolbox. The candidate room composition is materially stronger than the legacy composition, and the plush bear, cabinet, bed, side table, rug, care kit, bottles, basin treatment, room bases and most other candidate roles are visibly stronger than baseline.

However, the producing agent again treated every candidate as a direct one-for-one replacement. Owner pixel review shows that several old/new pairs are actually **different useful authoring objects or useful states**. The Workshop lesson applies here too: the strongest Greia toolbox is not the one with the highest replacement percentage.

Perform one bounded Clinic/Care finalization pass, then promotion review. Do not reopen already-good assets for aesthetic micro-optimization.

---

## What is clearly improved

The candidate is visibly stronger overall in:

- **Plush bear:** more dimensional, expressive and materially readable while still surviving small sizes.
- **Care bed/daybed:** reads as an actual warm child-scale daybed rather than a minimal placeholder.
- **Cabinet:** much stronger furniture construction, glazing, shelves and visual depth.
- **Side table:** better furniture silhouette and grounding.
- **Heart rug:** substantially stronger textile/felt treatment and presence.
- **Care kit:** clearer friendly pretend-care object with much stronger volume and finish.
- **Toy stethoscope:** playful, colorful and still recognizable through the supplied 64 px proof.
- **Bottle set:** materially richer and more legible as a set of pretend care bottles.
- **Room wall/floor bases:** much stronger material identity and scene value separation.
- **Candidate composition:** far richer and more coherent than baseline overall.

The care direction remains reassuring rather than clinical/scary. That is correct for Greia.

---

## Where the 17/17 direct-replacement claim is wrong

### 1. Cushion — likely KEEP_BOTH_DISTINCT

The baseline cushion and candidate cushion are not the same useful authoring object:

- baseline: soft pink oval heart cushion;
- candidate: yellow round/tufted button cushion.

The candidate is more dimensional, but the baseline heart cushion is still a useful soft care-themed prop. Do not delete useful variety merely because a richer drawing exists.

Finalization should propose distinct semantic IDs, for example a heart cushion variant and a tufted cushion variant.

### 2. Care window — likely KEEP_BOTH_DISTINCT

The baseline and candidate windows are meaningfully different room features:

- baseline: compact square/rectangular meadow window;
- candidate: tall arched orchard window.

Both are useful for Activity authoring. Preserve both if their source quality is acceptable under distinct semantic IDs.

### 3. Window light — likely KEEP_BOTH_DISTINCT

The evidence shows two meaningfully different light-shaft treatments:

- baseline: layered/narrower shafts;
- candidate: broader single warm shaft with motes.

These can serve different compositions. Finalization should compare them explicitly over the same room value and keep both if they remain useful.

### 4. Bandage container — likely KEEP_BOTH_DISTINCT

The baseline is visually a compact rectangular care/first-aid box; the candidate is visually a vertical lidded bandage tin/container. Calling both `clinic.bandage.box` hides a real semantic difference.

The candidate is stronger as a crafted object, but the baseline box remains a different useful prop. Prefer distinct semantic IDs rather than silently replacing one with the other.

### 5. Care basin — likely KEEP_BOTH_DISTINCT as useful states

The baseline basin is a simple empty basin. The candidate is a prepared wash basin containing water and a sponge.

Those are not redundant drawings: they are useful **states** for Activity authoring. Preserve both if the finalization confirms the baseline empty basin remains visually adequate.

Suggested semantic distinction should express state/function rather than provenance, e.g. empty basin versus wash/prepared basin.

---

## Evidence and presentation issues to correct once

### 1. Candidate composition is too crowded at the center/bottom

The proposed scene is much better overall, but the current evidence has composition defects:

- the heart rug is oversized and heavily clipped at the bottom;
- the basin overlaps the rug/bed focal area and contributes to visual crowding;
- several large props compete in a narrow central band.

This is primarily a **composition-evidence defect**, not a reason to redraw the strong individual assets. Regenerate one cleaner candidate room proof with clearer floor zones and less accidental overlap.

### 2. The bandage authoring ingredient is not directly shown in the curated evidence

`catalog.toml` proposes two ingredients:

- `ingredient.patch`
- `ingredient.bandage`

The fabric heart patch is shown. The bandage strip is not directly visible enough in the curated review set to authorize promotion from prose alone.

Finalization must show both ingredients directly at useful source size before owner promotion review.

### 3. Runtime proof is representative, not complete

The 64 px sheet convincingly covers bear, stethoscope, care kit and bandage tin. That is enough to show the candidate family can survive small usage, but finalization should not claim every asset has identical small-size behavior. Large room features and detailed props may legitimately carry higher recommended minimum sizes.

---

## Candidate roles that should not be reopened without an objective defect

Do not spend the finalization pass reauthoring these merely for extra polish:

```text
clinic.plush.bear
clinic.care.bed
clinic.cabinet
clinic.side.table
clinic.heart.rug
clinic.curtain.pair
clinic.care.kit
clinic.toy.stethoscope
clinic.bottle.set
clinic.room.wall.base
clinic.room.floor.base
clinic.heart.fx
```

The finalization task is semantic/toolbox cleanup, direct evidence, and composition correction — not another specimen-optimization loop.

---

## Finalization target

For every old/new role, choose exactly one of:

```text
CANDIDATE_REPLACES
BASELINE_RETAINS
KEEP_BOTH_DISTINCT
UNRESOLVED
```

Where `KEEP_BOTH_DISTINCT` is chosen, assign distinct semantic IDs that describe the actual object/state rather than `legacy`/`candidate` provenance.

The most likely coexistence decisions requiring explicit final proof are:

```text
cushion: heart vs tufted
window: compact/square vs arched
window light: narrow/layered vs broad
bandage container: box vs tin
care basin: empty vs prepared wash basin
```

These are proposals for finalization, not pre-authorized promotion counts.

---

## Status

- Clinic/Care candidate overall versus v0.1: **OWNER-REVIEWED / CLEARLY STRONGER OVERALL**.
- Proposed 17/17 direct replacement: **REJECTED**.
- One bounded semantic/evidence finalization: **REQUIRED**.
- Further broad Clinic art refinement: **NOT A MILESTONE**.
- Runtime catalogue/Activities/compositor: **DO NOT TOUCH for source-pack finalization**.
