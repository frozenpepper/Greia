# Clinic / Care Base Art Pack — Finalization and Promotion-Candidate Gate

**Date:** 2026-08-21  
**Purpose:** perform one bounded semantic/evidence finalization pass on the already-strong Clinic/Care candidate, then prepare an exact promotion proposal.  
**Primary review:** `docs/reviews/visual/2026-08-21_clinic-care-base-pack-reauthoring/PRIMARY_REVIEW.md`  
**Candidate:** `assets/visual/pack_candidates/clinic/2026-08-21/`

## 1. Scope

This is the **last Clinic/Care authoring pass before owner promotion review**.

Do not reauthor the whole pack. Do not polish already-good assets merely because more detail is possible. Do not modify runtime consumers, Activities, the compositor, or shared runtime catalogues.

The owner has already concluded that the Clinic/Care candidate is clearly stronger overall than v0.1.

Your job is only to:

1. resolve the old/new pairs that are actually distinct useful toolbox objects/states;
2. show both proposed authoring ingredients directly;
3. correct the crowded candidate composition evidence;
4. produce an exact role-by-role promotion map;
5. prepare a complete owner-review ZIP.

After this gate, stop Clinic/Care work and wait for owner promotion review.

---

## 2. Read first

Read:

```text
AGENTS.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md
docs/reviews/visual/2026-08-21_clinic-care-base-pack-reauthoring/PRIMARY_REVIEW.md
assets/visual/environments/clinic/v0.1/catalog.toml
assets/visual/pack_candidates/clinic/2026-08-21/catalog.toml
```

Inspect the committed candidate sources and existing nine review sheets before changing anything.

---

## 3. Do not reopen already-good families without a real defect

Do not spend this pass cosmetically refining these roles:

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

Only touch them if you discover a genuine source/rendering defect.

---

## 4. Required semantic/toolbox decisions

For every baseline/candidate relationship use exactly one disposition:

```text
CANDIDATE_REPLACES
BASELINE_RETAINS
KEEP_BOTH_DISTINCT
UNRESOLVED
```

The strongest toolbox is the objective. Do not optimize for replacement percentage.

The owner review identified five likely `KEEP_BOTH_DISTINCT` cases. You must inspect and decide each one explicitly.

### 4.1 Cushion

Compare:

- baseline soft heart cushion;
- candidate yellow tufted/button cushion.

If both remain useful, preserve both with semantic IDs describing the objects, e.g. heart cushion vs tufted cushion. Do not use `legacy`/`candidate` in final IDs.

### 4.2 Care window

Compare:

- baseline compact/square meadow window;
- candidate tall arched orchard window.

If both remain useful room features, keep both under distinct semantic IDs.

### 4.3 Window light

Compare over the **same neutral room values**:

- baseline layered/narrow light shaft;
- candidate broader warm shaft with motes.

Keep both if they provide genuinely different compositional uses.

### 4.4 Bandage container

The baseline visually reads as a compact rectangular care/first-aid box. The candidate visually reads as a vertical lidded bandage tin/container.

Do not pretend they are the same object merely to retain `clinic.bandage.box` one-to-one mapping.

If both survive, give them distinct semantic IDs such as box versus tin/container.

### 4.5 Care basin

Compare:

- baseline empty basin;
- candidate prepared wash basin with water/sponge.

These may be useful Activity states. If both survive, give them state/function IDs such as empty versus prepared/wash rather than provenance names.

---

## 5. Authoring ingredient evidence

The candidate proposes:

```text
ingredient.patch
ingredient.bandage
```

The previous curated sheets visibly demonstrated the fabric heart patch but did not directly prove the bandage strip well enough for owner promotion.

Create direct neutral-background evidence for **both** ingredients at source/useful size.

For each ingredient answer:

- Is it genuinely useful for future Activity authoring/composition?
- Is it distinct enough from finished assets to justify ingredient status?
- Would an arbitrary Activity-authoring agent understand its intended use from catalogue metadata?

Do not promote an ingredient solely because it already exists.

---

## 6. Candidate composition correction

Regenerate the 1024×600 proposed Clinic/Care composition once.

Correct the evidence issues without redesigning the pack:

- do not let the heart rug dominate the entire center/bottom or clip heavily off-screen;
- reduce accidental congestion between bed, rug and basin;
- establish clear floor zones and readable grounding;
- keep the cabinet/window/bed proportions plausible relative to one another;
- preserve the warm reassuring care-room mood;
- use enough assets to demonstrate coherence without turning the room into an inventory dump.

This is an evidence/composition correction, not a new art pass.

---

## 7. Runtime-size evidence

Do not claim every Clinic asset must work equally at 64 px.

Create direct useful-size proof for the semantically disputed finished assets/variants:

```text
cushion variants
bandage box/tin variants
basin variants
```

Use sensible size tiers. For room windows and light overlays, composition-scale proof is more meaningful than a 64 px icon test.

The existing bear/stethoscope/care-kit small-size proof may be reused by reference; do not redraw those assets.

---

## 8. Exact promotion proposal

Create:

```text
docs/reviews/visual/2026-08-21_clinic-care-pack-finalization/PROMOTION.md
docs/reviews/visual/2026-08-21_clinic-care-pack-finalization/promotion-map.json
```

For every baseline role and every candidate role/variant proposed for the new toolbox, record:

- final semantic ID;
- source file;
- source provenance (`v0.1_baseline` or `2026-08-21_candidate`);
- disposition;
- one-sentence rationale when retaining baseline or keeping both;
- recommended minimum display size where useful.

The proposed new pack may contain **more than 17 roles** if useful distinct variants/states survive.

Do not manufacture variants merely to increase count.

---

## 9. Required finalization review directory

Create:

```text
docs/reviews/visual/2026-08-21_clinic-care-pack-finalization/
```

Required files:

```text
01-final-inventory-a.png
02-final-inventory-b.png
03-distinct-variants.png
04-bandage-basin-decisions.png
05-window-light-variants.png
06-ingredient-review.png
07-final-baseline-composition.png
08-final-proposed-v02-composition.png
09-promotion-summary.png
PROMOTION.md
promotion-map.json
REVIEW.md
audit.json
```

The inventory sheets together must visibly show every finished asset proposed for promotion with readable labels.

---

## 10. Review-sheet rules

- Use comparable neutral backgrounds.
- Do not label your own work `SUPERIOR`, `MASTER`, `CLEARLY BETTER`, etc.
- No clipped labels or text.
- Show old/new variants at comparable useful sizes.
- Do not hide weak variants inside a busy composition.
- Prose cannot substitute for pixels.

---

## 11. REVIEW.md

Answer conservatively:

1. Which candidate roles directly replace baseline?
2. Which baseline roles remain as distinct variants/states?
3. Which candidate roles coexist as distinct variants/states?
4. Which roles, if any, remain unresolved?
5. Which authoring ingredients are proposed for promotion and why?
6. Does every proposed finished asset/ingredient have direct visual evidence?
7. Is the proposed Clinic/Care v0.2 toolbox ready for owner promotion review?

Do not infer owner approval.

---

## 12. No promotion/materialization in this gate

Do not create `assets/visual/environments/clinic/v0.2/` yet.

Do not update preferred pack indexes yet.

This gate prepares the exact owner promotion proposal only.

After owner review, a separate mechanical promotion runbook will materialize the authorized v0.2 toolbox.

---

## 13. Mandatory owner attachment ZIP

Create at project root:

```text
./GREIA_VISUAL_REVIEW_CLINIC_CARE_PACK_FINALIZATION_2026-08-21.zip
```

Include:

- all nine PNG review sheets;
- `PROMOTION.md`;
- `promotion-map.json`;
- `REVIEW.md`;
- `audit.json`.

Do not commit the ZIP itself. Commit the underlying candidate corrections (if any) and finalization evidence.

Final response must include exactly:

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_CLINIC_CARE_PACK_FINALIZATION_2026-08-21.zip
```

---

## 14. Return

Commit and push to canonical `main`:

- only bounded candidate changes that are objectively needed;
- finalization review evidence;
- exact promotion map/audit.

Return:

- exact commit SHA;
- final proposed finished-asset count;
- direct replacement count;
- retained baseline/distinct-variant count;
- unresolved count;
- ingredient count;
- review directory;
- exact owner ZIP path.

Then stop Clinic/Care work and wait for owner promotion review.
