# Greia Encyclopedia v0.1 — visual evidence review

**Date:** 2026-08-28  
**Evidence source:** `tmp/encyclopedia-v01-acceptance/20260828_074819-mechanical-traversal.zip`  
**Tested runtime SHA:** `8cda9cbaa4beb4f5c38a9945479f0f4c88f8ee65`  
**Disposition:** **43-page reachability/back PASS / visual repair required before Simulator acceptance**

## 1. Scope of this review

The uploaded evidence archive contained the complete mechanical traversal evidence set:

- Shell/profile frame;
- Encyclopedia Home;
- all six section pages;
- before/after files for all 36 factual entries;
- Encyclopedia Home after traversal;
- returned Shell;
- traversal summary and child log.

This review inspected the actual rendered screenshots. It does not infer visual correctness from `changed_pixel_fraction` alone.

## 2. What is visually strong

The v0.1 visual architecture is viable and coherent on the 1024×600 target:

- the six section worlds are visually distinct and immediately recognizable;
- large circular hotspots and yellow focus rings are consistent and easy to locate;
- protected Greia Home and Encyclopedia-internal Back are visually distinct;
- presenter characters render consistently in the captured states;
- the low-resource procedural illustration style is cohesive across the activity;
- most first ACTIVATE states create an understandable visible change;
- no global frame corruption or broad missing-character fallback was visible;
- the returned Shell frame presents the Encyclopedia normally with its package-owned icon.

Section-specific observations:

- **Animals:** clear 2×3 exhibit layout and strong selection affordance.
- **Space:** strong living Solar-System section with useful semantic selection label.
- **Earth:** particularly effective scene-based map; rain/tree/rainbow/volcano/ocean read spatially without requiring text.
- **Body:** friendly body schematic with concrete callout targets; one contrast defect is recorded below.
- **Machines:** recognizable workshop objects support pre-reader navigation without text labels.
- **History:** concrete timeline cards are much clearer than a taxonomy/list treatment.

## 3. Evidence defect — Sun and Neptune before/after pairs are not coherent

The files exist for all 36 pairs, but two pairs do not represent entry-before → entry-after interaction evidence:

```text
space.sun-before.png
space.neptune-before.png
```

Both `*-before.png` files still show the **Space section page** with the target selected. Their corresponding `*-after.png` files show the actual Sun/Neptune entry pages.

Therefore the very large changed-pixel fractions for these two pages are page-transition deltas, not signature-interaction deltas.

This does **not** invalidate 43-page reachability:

- Sun and Neptune entry pages are visibly reached in the `after` frames;
- the traversal continued successfully afterward;
- internal Back remained functional.

It **does** mean the visual evidence set contains only **34/36 coherent entry-before → entry-after interaction pairs**. Existing wording that mechanically says `36/36 before/after files captured` remains literally true, but it must not be interpreted as `36/36 visually valid interaction comparisons`.

### Likely harness cause

`tools/encyclopedia_v01_headless_traversal.py` currently treats the first later global `frame_count` as sufficient evidence that a semantic key has taken effect. On an animated section such as Space, a fresh section frame can arrive before the posted RETURN has been consumed by the Activity event loop.

The harness should add a bounded post-navigation settle contract for page transitions before capturing the destination frame. This should be implemented and regression-tested in the acceptance helper, not by adding hidden runtime hooks to Encyclopedia pages.

## 4. Runtime visual defect — Pyramids intro caption overflows

`history.pyramids-before.png` visibly renders the Italian intro caption beyond the horizontal bounds of its rounded caption panel.

The authoritative wording must not be shortened merely to hide the layout problem.

Current `history.pyramids` rendering only retries the whole sentence at 15 px if 18 px is too wide; it does not continue fitting or wrap the line. The fix should preserve wording and make the renderer fit or wrap safely inside the 400×68 panel at 1024×600.

Severity: **visual acceptance blocker at reference viewport**.

## 5. Runtime pre-reader affordance defect — Body Teeth target has insufficient contrast

In `sections/04-body.png`, the top-right Teeth target is nearly blank at normal viewing scale.

The tooth shapes are drawn in a very light cream on a nearly identical light target disk. For a pre-reader, this materially weakens the semantic affordance even though the target remains mechanically selectable.

The fix should strengthen the tooth glyph contrast, preferably with a darker outline and/or stronger fill while preserving the pastel body-section palette.

Severity: **pre-reader visual acceptance blocker**.

## 6. Non-blocking UX notes to retain for later review

These are observations, not source defects established by this evidence:

- the Home `TANTO TEMPO FA` portal uses an abstract ascending-bars motif; a more historical/pre-reader-concrete symbol may eventually be stronger;
- several first default-focus interactions are intentionally subtle (for example bee, rain, volcano, bones, gears, fossils); the mechanical run exercises only the initial ACTIVATE, not every discovery/hotspot or complete planned signature sequence;
- consequently this archive is not sufficient to certify every planned signature interaction even where the before/after pair is coherent.

The remaining signature-interaction gate should inspect the intended multi-step behavior where the authoring catalogue specifies more than one discovery/state.

## 7. `libpng` warning

The child log again contains exactly:

```text
libpng error: bad adaptive filter value
```

No broad missing presenter, broken section composition, or obvious blank asset placeholder was visible in the reviewed screenshots. This weakens—but does not eliminate—the hypothesis that the warning corresponds to an important Encyclopedia visual asset decode failure.

The warning remains unresolved diagnostic evidence. Do not attribute it to the screenshot encoder or to a particular asset without direct evidence.

## 8. Corrected acceptance interpretation

The existing run establishes:

```text
SOURCE-VERIFIED
HEADLESS-LIFECYCLE-SMOKE-PASS
43-PAGE REACHABILITY/BACK PASS
34/36 COHERENT FIRST-INTERACTION VISUAL PAIRS
VISUAL REPAIR REQUIRED
POINTER PARITY PENDING
PRE-READER UX FINAL ACCEPTANCE PENDING
RESPONSIVE MATRIX PENDING
NARRATION ACCEPTANCE PENDING
```

It must **not** yet be labeled `SOURCE + SIMULATOR ACCEPTED`.

## 9. Required next repair tranche

One targeted owner-machine tranche should:

1. fix page-transition settling in `tools/encyclopedia_v01_headless_traversal.py` so destination screenshots cannot be captured from the previous animated page;
2. add regression coverage for that settle behavior;
3. fix Pyramids caption fitting without changing approved wording;
4. improve Body Teeth target contrast;
5. run focused tests once;
6. because Activity runtime source changes, run the Encyclopedia source gate exactly once;
7. run one fresh mechanical traversal exactly once to regenerate coherent visual evidence;
8. preserve/report the `libpng` warning without speculative repair.

Only after that repair/recapture should pointer parity and responsive acceptance be advanced.
