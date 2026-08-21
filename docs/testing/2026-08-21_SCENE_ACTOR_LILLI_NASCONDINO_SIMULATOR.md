# Greia Scene Actor + Nascondino HUD Correction — Activity Simulator Protocol

**Date:** 2026-08-21  
**Evidence path:** Greia Activity Simulator only  
**Preferred mode:** non-intrusive headless  
**Target Activity:** `org.greia.nascondino-bosco`  
**Parent architecture:** `docs/design/GREIA_SCENE_COMPOSITION_RUNTIME.md`  
**Visual evidence contract:** `docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`

## Purpose

Advance the graphics engine beyond static environment composition by proving the first shared Greia character as a renderer-neutral scene actor, while correcting factual/layout defects found in the first Nascondino evidence review.

This is **one coherent gate**, not another standalone micro-validation cycle:

```text
shared scene
+ shared character actor
+ contact shadow
+ deterministic idle/blink
+ corrected child HUD sizing
+ truthful responsive evidence
```

Read first:

```text
docs/reviews/visual/2026-08-21_scene-compositor-nascondino/PRIMARY_REVIEW.md
```

Do not copy the previous `REVIEW.md` claims forward; several were source-inaccurate.

---

## 1. Sync and prerequisites

Work on canonical `main` only.

Confirm the checkout includes at least:

```text
src/greia_platform/scene_actor.py
src/greia_platform/pygame_scene.py
assets/catalog/shared_visuals_v1_source.toml
```

Generate the new explicit runtime renditions:

```bash
make visual-assets
```

This must produce, through the normal explicit build path:

```text
assets/visual/runtime/v1/characters/lilli_neutral.png
assets/visual/runtime/v1/characters/lilli_blink.png
assets/visual/runtime/v1/shared/shadow_contact_small.png
```

and matching generated-catalogue entries:

```text
character.lilli/default
character.lilli/blink
shadow.contact.small.01/default
```

Do not introduce runtime SVG rendering, source-directory scanning, or another image cache.

---

## 2. Integrate Lilli through the scene actor contract

Use:

```python
SceneActorDefinition
actor_scene_sample(...)
```

from:

```text
src/greia_platform/scene_actor.py
```

Render the sampled actor with the **existing `PygameSceneRenderer` instance** and therefore the existing bounded semantic surface cache.

Do not hand-load Lilli's PNGs in the Activity.

Do not create a second character renderer/cache.

### Initial placement

Use a calm guide placement in the left-upper playfield region, approximately:

```text
body rect   ≈ [50, 105, 150, 150]
shadow rect ≈ [78, 232, 96, 24]
z           ≈ 55–58
parallax     ≈ 0.25–0.32
```

Exact geometry may be adjusted after looking at the actual pixels. The important constraints are:

- no overlap with protected Home chrome;
- no overlap with the star pill;
- no obstruction of the central target/search HUD;
- no material obstruction of the tree-hollow gameplay target below;
- character reads as grounded in the scene rather than floating over the UI.

Render actor + shadow after the environment background pass and before interactive hiding-spot/gameplay drawing, so foreground/gameplay can naturally occlude the guide where appropriate.

### Required visible states

Verify at least:

```text
neutral/default
blink
idle vertical motion
contact shadow grounding
motion disabled / static neutral
```

Blink must visibly close Lilli's eyes; it is not accepted merely because the `blink` variant ID was selected.

Idle movement must remain subtle. No skeletal/gait animation is wanted.

---

## 3. Correct the Nascondino child HUD before visual acceptance

The previous evidence incorrectly claimed a 22 px animal label while source rendered 18 px and incorrectly claimed Large-interface scaling.

Fix the real Activity, not the evidence file.

### Target animal/search card

Requirements on the 1024×600 reference canvas:

- ordinary target animal name should normally render around **22–24 px**;
- Compact must not push meaningful target text below **20 px**;
- Large should visibly increase target HUD text/control sizing, normally around **26 px** for the animal name;
- `SCOIATTOLO` must fit without clipping, geometric squashing, overlap with progress dots, or silent ellipsis;
- widen/reflow the search card if needed instead of shrinking important text;
- the card remains centered and must not collide with Home/star UI.

Because Nascondino draws onto the fixed 1024×600 `PygameReferenceCanvas`, compose **profile `InterfaceSize` preference only** into reference-canvas HUD geometry. Do not multiply physical viewport scaling a second time; the canvas already handles physical presentation.

Use Greia's semantic UI preference API rather than reading an arbitrary custom pixel-size setting.

### Runtime-derived audit

The new `layout-audit.json` must be populated from the actual values used to render the frame, not manually guessed.

At minimum record for Normal / Large / Compact where exercised:

```text
target-card rect
animal-name requested font px
animal-name rendered rect
animal-name available text region
progress region
clipped/overlap boolean
star-pill rect
protected Home rect
actor body rect
actor shadow rect
```

If the local simulator bridge cannot expose a value automatically, add a **small test-only/simulator inspection hook outside production rendering semantics** or derive it directly from the same layout function used by production. Do not hand-enter different numbers in JSON.

---

## 4. Scene fit semantics must be reported correctly

`forest_meadow_day_v1.toml` uses:

```text
fit = "cover"
```

Therefore differing aspect ratios use centered crop, not letterbox/pillarbox.

The visual review must explicitly inspect that critical gameplay/HUD content remains safe under that crop.

Do not describe a COVER screenshot as pillarboxed unless the source policy was deliberately changed and reviewed.

---

## 5. Optional corrupt asset regression

The current `PygameSceneRenderer` remembers failed optional visual realizations until explicit `clear()`.

Through the simulator, corrupt one optional scene PNG such as:

```text
fog_strip.png
```

and verify:

- the Activity remains playable;
- only that optional visual disappears;
- the renderer does not repeatedly retry/decode the same corrupt optional asset every frame;
- restoring/restarting or explicit renderer invalidation allows normal loading again.

Do not instrument production with unbounded debug logging to prove this. A bounded simulator diagnostic/count is enough.

---

## 6. Simulator scenarios

Use an isolated state root, for example:

```bash
export GREIA_SIMULATOR_HEADLESS=1
python3 tools/greia_simulator.py --state-dir "$HOME/.greia-simulator-scene-actor"
```

All runtime/visual acceptance is through the Activity Simulator at the established loopback bridge.

Required cases:

1. **1024×600 Normal baseline** — scene + Lilli + corrected HUD.
2. **Visible blink state** — capture Lilli with eyes physically closed.
3. **Idle displaced state** — body offset visible while contact shadow stays grounded.
4. **Motion-disabled state** — complete static scene + neutral Lilli.
5. **1024×600 Large** — HUD visibly larger, no clipping/overlap.
6. **1366×768 Compact** — child text remains readable; COVER crop remains safe.
7. **1920×1080 Normal** — centered COVER behavior remains balanced.
8. **Optional corrupt fog** — narrow failure isolation and no per-frame retry storm.
9. **Required scene asset failure** — established deliberate legacy background fallback still works.
10. **Activity lifecycle** — launch, play, Greia Home/return behavior unchanged.

Do not run or cite GitHub Actions.

Do not promote standalone `pytest`, `unittest`, `make test` or `make verify` as the acceptance evidence for this visual tranche. Source tests may remain committed for later aggregate gates; the owner-directed visual/runtime evidence here is the Activity Simulator.

---

## 7. Curated visual evidence

Commit a maximum of six screenshots under:

```text
docs/reviews/visual/2026-08-21_scene-actor-lilli-nascondino/
```

Required set:

```text
01-reference.png          # 1024×600 normal scene + actor + HUD
02-blink.png              # physically closed-eye blink
03-large.png              # 1024×600 Large interface
04-compact.png            # constrained/compact responsive state
05-large-viewport.png     # 1920×1080 COVER composition
06-fallback.png           # meaningful fail-soft state
REVIEW.md
layout-audit.json
```

`REVIEW.md` must assess actual pixels according to `VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md` and must cross-check all numeric claims against the runtime-derived audit/source.

Do not say `PASS` for a text size or fit mode that differs from the source.

---

## 8. Performance sanity

Measure a 10-second steady scene with Lilli idle/blink active.

Report:

```text
frames
elapsed seconds
average FPS
```

Use neutral wording. A measured value below the 30 Hz clock target is a measured value, not automatically "rock-solid".

This remains simulator regression sanity, not physical Acer/Pi performance evidence.

---

## 9. Stop/fix conditions

Fix before accepting if any of these occur:

- meaningful text <20 px in the reference/compact HUD without a documented exceptional reason;
- `SCOIATTOLO` clipping, collision or ellipsis;
- Large preference does not materially change the HUD while evidence claims it does;
- Lilli overlaps Home/star/search UI or hides a gameplay target;
- blink does not visibly close the eyes;
- character appears ungrounded/floating;
- actor implementation bypasses semantic assets or shared cache;
- optional corrupt art causes repeated load/exception work every frame;
- COVER crop removes critical content;
- fallback breaks game lifecycle/input;
- screenshot review and source/runtime audit disagree.

Fix the shared/root cause, rerun affected simulator cases, and update the curated review set.

---

## 10. Mandatory transfer ZIP for independent pixel review

The committed PNGs are not sufficient for the primary reviewer because the private-GitHub connector may expose repository PNGs only as encoded bytes rather than a directly viewable image surface.

Therefore this visual gate is **not complete for return to the owner** until you create one small project-root ZIP that the owner can attach directly to ChatGPT for independent pixel inspection.

Create it **after** the curated review set is final and before reporting completion. Do **not** commit this ZIP to Git.

Run from the Greia repository root:

```bash
python3 - <<'PY'
from pathlib import Path
import zipfile

review_dir = Path("docs/reviews/visual/2026-08-21_scene-actor-lilli-nascondino")
zip_path = Path("GREIA_VISUAL_REVIEW_SCENE_ACTOR_LILLI_2026-08-21.zip")

required = [
    "01-reference.png",
    "02-blink.png",
    "03-large.png",
    "04-compact.png",
    "05-large-viewport.png",
    "06-fallback.png",
    "REVIEW.md",
    "layout-audit.json",
]

missing = [name for name in required if not (review_dir / name).is_file()]
if missing:
    raise SystemExit("Cannot package visual review; missing: " + ", ".join(missing))

zip_path.unlink(missing_ok=True)
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for name in required:
        source = review_dir / name
        archive.write(source, arcname=name)

print(zip_path.resolve())
PY
```

Then verify the archive exists and is non-empty:

```bash
ls -lh GREIA_VISUAL_REVIEW_SCENE_ACTOR_LILLI_2026-08-21.zip
```

The final local-agent report must include this exact line, with the actual project-relative path:

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_SCENE_ACTOR_LILLI_2026-08-21.zip
```

Do not delete the ZIP after pushing Git changes. The owner will attach it to ChatGPT so the primary reviewer can actually open and inspect the screenshots. A local-agent `PASS`, `REVIEW.md`, or GitHub-hosted PNG alone does **not** substitute for that independent pixel review.

---

## 11. Return

Update:

```text
LOCAL_AGENT_RESULT.md
docs/plans/2026-08-21_GREIA_SCENE_COMPOSITION_RUNTIME.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

Commit and push to `origin/main`.

Report:

- the exact commit SHA;
- the measured FPS;
- the exact `VISUAL REVIEW ZIP FOR OWNER ATTACHMENT` project-relative path.

Keep evidence claims at simulator scope only. Do not call the visual gate independently reviewed by the primary reviewer until the owner has attached the ZIP and that review has happened.
