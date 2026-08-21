# Greia Visual Acceptance Evidence Contract

**Status:** mandatory for visual/UI simulator gates  
**Date:** 2026-08-21  
**Scope:** child Shell, first-party Activities, shared scene/composition runtime, visual assets, responsive UI

## Why this exists

A simulator status file can prove that a frame rendered. It cannot prove that the frame is good.

A visual gate is not accepted merely because controls respond, FPS is stable, or a local agent writes `PASS`. Greia must not accumulate technically functional screens with clipped labels, tiny child text, awkward whitespace, overlapping controls, distorted artwork, or broken visual hierarchy.

Therefore every visual acceptance gate must leave a **small reviewable screenshot set in Git**, in addition to any larger project-local temporary evidence set.

## Evidence locations

The full run may keep detailed evidence under a project-local temporary directory such as:

```text
tmp/<gate>-evidence/
```

That directory does not need to be committed.

The local agent must also create a curated review set under:

```text
docs/reviews/visual/<YYYY-MM-DD>_<gate>/
```

Commit only the small curated set, normally **4–6 screenshots maximum**, plus the review metadata below. Do not commit hundreds of simulator frames.

Required files:

```text
REVIEW.md
layout-audit.json
01-reference.png
02-interaction.png
03-low-resolution.png
04-large-or-compact.png
```

A gate may use one or two additional screenshots when a fallback/error/animation state is visually important.

## Mandatory screenshot choices

Every curated set must include:

1. **1024×600 normal** — the primary low-resource reference view;
2. the most visually important interaction state for the gate (selected/hovered/open/launch/etc.);
3. one constrained/responsive state that is likely to expose layout problems (`1024×600 large` or the compact matrix row, as appropriate);
4. one larger viewport so scaling balance can be reviewed rather than merely assumed.

For scene/composition gates also include one frame where ambient motion/parallax is visibly displaced from the neutral frame when possible.

## Human visual-review requirements

The local agent must inspect the actual pixels, not only simulator state JSON.

`REVIEW.md` must explicitly assess:

- text clipping or truncation;
- tiny child-facing labels;
- button/control proportions;
- artwork distortion;
- overlap/collision;
- content touching panel/window edges;
- inconsistent margins or alignment;
- selection/focus visibility without relying on pointer position;
- hierarchy: the intended primary object must actually read as primary;
- whether decorative art obscures interaction content;
- whether low-resolution rendering still looks intentional rather than merely fitting;
- whether large displays become sparse, comically oversized, or visually unbalanced.

Any visible defect above is a **FAIL to fix**, not a note to ignore because the interaction technically works.

## Typography guardrail

Follow `docs/design/GREIA_VISUAL_STYLE_GUIDE.md`.

At the 1024×600 reference size, meaningful child-facing text should generally not fall below about **18 px**. Primary controls normally target the larger documented control scale. If a rendered screen violates that guidance, `REVIEW.md` must identify the exact reason and the gate must not silently call the result acceptable.

Activity-name ellipsis remains an intentional last-resort behavior where the Activity-card contract allows it. Ordinary button labels must not be silently clipped to make geometry pass.

## Machine-readable layout audit

`layout-audit.json` is supplemental evidence, not a replacement for looking at screenshots.

Where the renderer can expose the information, record at least:

```json
{
  "viewport": [1024, 600],
  "interface_size": "normal",
  "text": [
    {
      "label": "example",
      "font_px": 24,
      "rendered_rect": [0, 0, 100, 28],
      "container_rect": [0, 0, 140, 52],
      "clipped": false
    }
  ],
  "controls": [
    {
      "id": "example-control",
      "visual_rect": [0, 0, 140, 52],
      "hit_rect": [0, 0, 140, 52],
      "overlap": false
    }
  ]
}
```

The exact schema may grow, but the intent is stable: make clipping, text size and accidental geometry regressions visible to tooling as well as reviewers.

## Acceptance rule

A visual gate may be recorded as `SIMULATOR VISUAL REVIEW` only when all of the following are true:

- the simulator/runtime cases passed;
- the curated screenshots exist in the committed review directory;
- `REVIEW.md` records an actual pixel-level visual inspection;
- layout audit does not reveal an unaddressed clipping/overlap/text-size defect;
- fail-soft behavior remains usable where the gate requires it;
- evidence scope is not overstated as physical-hardware approval.

When a subsequent reviewer has repository access, they should review the committed curated screenshots before treating the visual result as closed.

## Repository-size rule

Keep this disciplined:

- commit only the curated 4–6 review images;
- keep raw/full-matrix evidence project-local unless a specific failure requires preservation;
- prefer PNG for pixel-exact low-resolution evidence;
- do not create a new screenshot directory for every trivial code edit — one directory per substantive visual gate.

The goal is **reviewability**, not evidence-volume inflation.
