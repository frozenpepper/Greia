# Greia Visual Authoring Kit — v0.3 Corrective Craft Benchmark

**Purpose:** run a narrow corrective benchmark on the current Authoring Kit candidate.  
**This is not a broad expansion task.**  
You are fixing the most important remaining craft failures from v0.2 before more assets are added.

---

## 1. Mission

The v0.2 benchmark showed **real progress**, but it is **not yet acceptable as a Greia master standard**.

Your task is to create a **v0.3 corrective candidate** focused on only the key remaining weak points.

You must improve:

1. **Mature Oak**
2. **Interactive Hollow Tree**
3. **Upright Bramble**
4. **One secondary foliage / bush asset** (create or refine one supporting foliage asset that helps prove the corrected foliage grammar)

Do **not** broaden scope beyond this unless something tiny is required for the comparison sheets.

---

## 2. Read first

Before doing any work, read:

- `AGENTS.md`
- `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`
- `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`
- `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`
- `docs/reviews/visual/2026-08-21_authoring-library-comparison/PRIMARY_REVIEW.md`
- `docs/reviews/visual/2026-08-21_authoring-kit-variation/PRIMARY_REVIEW.md`
- `docs/testing/2026-08-21_VISUAL_AUTHORING_KIT_CRAFT_QUALITY_BENCHMARK.md`

Also inspect the current candidate assets and current review sheets.

---

## 3. Historical context you must preserve

You are working after these stages:

- baseline
- v0.1 candidate
- v0.2 candidate

Do **not** erase provenance.  
The review outputs must preserve progression and clearly show what changed.

---

## 4. Main findings from owner review that you must address

The owner review found:

### 4.1 Mature Oak
- improved from earlier versions but still too dependent on **smooth rounded balloon-like foliage masses**;
- too “clean vector asset” in feel;
- not yet rich enough as source art.

### 4.2 Interactive Hollow Tree
- improved, but still too close to the oak;
- still reads too much like **“big round tree with a hole”**;
- cavity still too regular; still too close to a designed opening instead of a naturally grown hollow;
- needs stronger first-glance identity difference.

### 4.3 Upright Bramble
- correct conceptual direction;
- fails badly at **64 px**;
- too thin / fragile at small sizes;
- needs a stronger grouped silhouette strategy.

### 4.4 Overall
- scene still feels like **assembled vector assets**, not yet truly rich storybook source art;
- foliage language still too smooth / inflated;
- self-review text has been too flattering; final review must be more rigorous and conservative.

---

## 5. Hard benchmark goals

### Goal A — Oak / Hollow differentiation
The oak and hollow tree must be clearly different **at a glance**.

Not subtly different.  
Not “same tree family + minor edits.”  
They must have distinctly different:

- silhouette;
- posture;
- canopy organization;
- age / character;
- emotional read.

### Goal B — Natural hollow
The hollow must no longer feel like a “door opening” or neat installed aperture.

It must feel **grown into the tree**.

That means:
- irregular deformation;
- asymmetric wood response;
- non-uniform rim behavior;
- visible growth stress around the cavity;
- believable internal depth.

### Goal C — Better foliage grammar
Foliage must stop relying primarily on:
- circles;
- ellipses;
- big smooth glossy blob highlights.

Foliage must instead show:
- larger silhouette rhythm;
- mid-scale internal structure;
- more organic edge behavior;
- less inflatable / plastic read.

### Goal D — Bramble survives at 64 px
The bramble must still read as a usable prop at:
- 256 px;
- 128 px;
- 64 px.

At 64 px it does not need full detail, but it must not collapse into a few stray sticks and dots.

### Goal E — Richer scene impression
When composed together, the v0.3 assets should feel more like:
- a storybook source-art family;

and less like:
- enlarged vector icons.

---

## 6. Strict scope

You must work on **only these four asset targets**:

1. `tree_mature_oak.svg`
2. `tree_interactive_hollow.svg`
3. `bush_upright_bramble.svg`
4. one supporting foliage / bush asset
   - either refine an existing foliage-support asset;
   - or create one small new asset specifically to prove the improved foliage grammar.

Optional tiny support edits are allowed only if required for coherent review sheets.

Do **not** add whole new asset families.  
Do **not** spend time on runtime integration.  
Do **not** drift into scene-system coding.  
Do **not** attempt another benchmark explosion.

Quality over breadth.

---

## 7. Authoring constraints

### 7.1 Oak constraints
The mature oak should feel:
- load-bearing;
- weighty;
- old;
- broad;
- sheltering.

It must avoid:
- canopy built mostly from rounded bubble groups;
- smooth identical highlight patches;
- over-clean symmetry.

It should have:
- stronger trunk / bough relation;
- richer bough emergence;
- more convincing canopy layering;
- irregular edge rhythm;
- more varied internal value structure.

### 7.2 Hollow tree constraints
The hollow tree must not be “oak + hole”.

It should likely feel:
- older;
- stranger;
- more expressive;
- more narratively charged;
- more asymmetrical.

Possible directions:
- drooping or weeping canopy behavior;
- trunk twist or torsion;
- visible age deformation;
- one side heavier than the other;
- more pronounced characterful posture.

The cavity must:
- feel naturally formed;
- be visibly supported by trunk deformation;
- be readable for gameplay;
- not become a clean geometric portal.

### 7.3 Bramble constraints
The bramble must clearly read as:
- grouped woody growth;
- cane-based structure;
- clustered leaf masses.

It must not:
- become a pile of thin lines;
- disappear at small size;
- become visually noisy;
- revert to green blob bush.

Use grouped clustering and silhouette simplification so the 64 px version still reads.

### 7.4 Supporting foliage / bush asset
This asset exists to prove your improved foliage grammar.

It should demonstrate:
- less balloon-like foliage;
- stronger grouping logic;
- believable massing;
- readable silhouette;
- consistency with Greia style.

---

## 8. Required craft standard

These are **source masters**, not low-effort placeholders.

Every master should visibly include three information scales:

### 8.1 Large-scale read
- silhouette;
- posture;
- main massing.

### 8.2 Mid-scale read
- branch / canopy structure;
- foliage grouping;
- cavity deformation;
- major surface planes.

### 8.3 Fine-scale read
- restrained bark / edge / growth nuance;
- localized material variation;
- subtle detail that supports the form.

Do not use noisy detail spam.

A 512 px master that still looks like a 64 px icon enlarged is a failure.

---

## 9. Output locations

Use:

### Candidate workspace
`assets/visual/authoring_kit/v0.3-candidate/`

### Review evidence
`docs/reviews/visual/2026-08-21_authoring-kit-v03-corrective/`

Do not overwrite old review directories.

---

## 10. Required review outputs

Create all of the following:

### 10.1 `01-oak-progression.png`
Show:
- baseline / earlier useful reference if needed;
- v0.2 oak;
- v0.3 oak.

This must clearly demonstrate why v0.3 is better.

### 10.2 `02-hollow-progression.png`
Show:
- v0.2 hollow tree;
- v0.3 hollow tree;
- v0.3 hollow close-up.

The close-up must make the cavity feel natural, not installed.

### 10.3 `03-bramble-progression.png`
Show:
- v0.2 bramble;
- v0.3 bramble;
- runtime-scale comparison emphasis.

### 10.4 `04-foliage-grammar-proof.png`
Show the new supporting foliage / bush asset and how its foliage grammar differs from the older balloon-lobe tendency.

### 10.5 `05-runtime-sizes.png`
Show v0.3 assets at:
- 256 px;
- 128 px;
- 64 px.

Include:
- oak;
- hollow tree;
- bramble;
- supporting foliage / bush.

This sheet is very important.

### 10.6 `06-composed-scene.png`
Create one simple restrained composition using only the corrected v0.3 family.

The goal is to judge:
- coherence;
- difference between oak and hollow;
- bramble readability;
- whether the whole thing still feels like giant vector icons or is moving toward source-art quality.

### 10.7 `07-detail-crops.png`
Close-up detail crops proving:
- oak trunk / bough junction;
- hollow deformation / rim / inner depth;
- bramble grouped stem/leaf logic;
- improved foliage grouping.

### 10.8 `REVIEW.md`
Write a conservative, truthful review.

It must explicitly answer:

1. Is the oak still too balloon-like anywhere?
2. Does the hollow still feel like an installed opening anywhere?
3. Do oak and hollow now differ strongly enough at first glance?
4. Does the bramble remain readable at 64 px?
5. Which asset is still weakest?
6. Is v0.3 good enough for provisional use as an Activity-authoring reference, or still experimental?

### 10.9 `audit.json`
List:
- source asset paths;
- review output paths;
- which prior versions were referenced;
- timestamp / provenance data.

---

## 11. Mandatory anti-failure rules

If any of these are true, the benchmark is not ready to present:

- oak canopy still mostly reads as simple rounded balls;
- hollow still reads like a door in a tree;
- hollow too close to oak at a glance;
- bramble collapses at 64 px;
- review sheets have clipped text;
- review prose overclaims what the pixels do not show;
- scene looks like enlarged icons rather than improved source art.

You must visually inspect your own outputs before finalizing.

If an asset is still weak, say so explicitly.

---

## 12. Final judgement standard

You are not trying to prove perfection.  
You are trying to prove **clear corrective movement** against the specific owner review.

If one asset remains weak, be honest.

The benchmark succeeds only if the direction is unmistakably better and more usable.

---

## 13. ZIP packaging requirement

Create exactly:

`./GREIA_VISUAL_REVIEW_AUTHORING_KIT_V03_CORRECTIVE_2026-08-21.zip`

It must contain:

- `01-oak-progression.png`
- `02-hollow-progression.png`
- `03-bramble-progression.png`
- `04-foliage-grammar-proof.png`
- `05-runtime-sizes.png`
- `06-composed-scene.png`
- `07-detail-crops.png`
- `REVIEW.md`
- `audit.json`

Example packaging command:

```bash
python3 - <<'PY'
import zipfile
from pathlib import Path

root = Path("docs/reviews/visual/2026-08-21_authoring-kit-v03-corrective")
zip_path = Path("./GREIA_VISUAL_REVIEW_AUTHORING_KIT_V03_CORRECTIVE_2026-08-21.zip")

wanted = [
    "01-oak-progression.png",
    "02-hollow-progression.png",
    "03-bramble-progression.png",
    "04-foliage-grammar-proof.png",
    "05-runtime-sizes.png",
    "06-composed-scene.png",
    "07-detail-crops.png",
    "REVIEW.md",
    "audit.json",
]

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for name in wanted:
        p = root / name
        if p.exists():
            zf.write(p, arcname=p.name)

print(zip_path)
PY
```

---

## 14. Final response format

Your final response must include:

- pushed commit SHA;
- candidate workspace path;
- review evidence path;
- concise self-assessment;
- exact ZIP path.

And must include exactly this line:

`VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_AUTHORING_KIT_V03_CORRECTIVE_2026-08-21.zip`

---

## 15. Non-goals

Do not:
- touch Nascondino;
- touch runtime compositor code;
- expand into new packs;
- create lots of extra environment assets;
- hide weak output behind positive prose.

Stay focused.
