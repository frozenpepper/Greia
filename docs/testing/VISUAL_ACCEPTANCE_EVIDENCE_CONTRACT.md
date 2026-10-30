# Greia Visual Acceptance Evidence Contract

**Status:** mandatory for visual/UI simulator gates  
**Date:** 2026-08-21  
**Scope:** child Shell, first-party Activities, shared scene/composition runtime, visual assets, responsive UI

## Why this exists

A simulator status file can prove that a frame rendered. It cannot prove that the frame is good.

A visual gate is not accepted merely because controls respond, FPS is stable, or a local agent writes `PASS`. Greia must not accumulate technically functional screens with clipped labels, tiny child text, awkward whitespace, overlapping controls, distorted artwork, or broken visual hierarchy.

Therefore every visual acceptance gate must leave a **small reviewable screenshot set in Git**, in addition to any larger project-local temporary evidence set.

For owner-driven visual work, that committed set must also be packaged into a **small non-committed transfer ZIP** so the owner can attach the actual PNGs to the primary reviewer when repository tooling cannot display private-repository image bytes directly.

## Evidence locations

The full run may keep detailed evidence under a project-local temporary directory such as:

```text
tmp/<gate>-evidence/
```

That directory does not need to be committed.

The local agent must also create a curated review set under the external evidence root (not committed to the public repository tree):

```text
<evidence-root>/visual/<YYYY-MM-DD>_<gate>/
```

Keep only the small curated set, normally **4–6 screenshots maximum**, plus the review metadata below. Do not commit hundreds of simulator frames.

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

A local-agent `REVIEW.md` is evidence, not authority over the source. A later reviewer must cross-check claims that can be derived objectively from source/runtime state. If the review says `22 px` while source renders `18 px`, or says `pillarbox` while the scene declares `cover`, the evidence is internally inconsistent and the visual gate is not closed until corrected.

## Typography guardrail

Follow `docs/design/GREIA_VISUAL_STYLE_GUIDE.md`.

At the 1024×600 reference size, meaningful child-facing text should generally not fall below about **18 px**. Primary controls normally target the larger documented control scale. If a rendered screen violates that guidance, `REVIEW.md` must identify the exact reason and the gate must not silently call the result acceptable.

For new or substantially revised child-facing HUD/navigation work, **18 px is a lower emergency floor rather than a design target**. Prefer the documented ~21–24 px ordinary child-text range and larger primary-control scale when geometry permits. Do not shrink important labels merely to preserve an undersized container.

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

**Do not hand-transcribe geometry that the program can report.** The audit must be generated from the same runtime/source values that actually produced the captured frame. At minimum, the local agent must show how each recorded font size/control rectangle was obtained. A manually invented audit that disagrees with source invalidates that portion of the evidence.

For fixed-reference-canvas Activities, distinguish profile `InterfaceSize` scaling from physical viewport scaling. If the Activity canvas already handles physical scaling, do not claim that a HUD responds to `large`/`compact` merely because the final screenshot was resized by the canvas.

## Mandatory owner-transfer archive

When a visual gate is being reviewed through a local agent and a separate primary reviewer, the local agent must create a small transfer archive after the curated review directory is final.

The archive must:

- contain the curated 4–6 PNGs plus `REVIEW.md` and `layout-audit.json`;
- be created in the Greia project root with a clear name such as `GREIA_VISUAL_REVIEW_<GATE>.zip`;
- **not** be committed to Git;
- remain on disk after the agent pushes its source/documentation changes;
- be reported with an exact project-relative path in the final local-agent response so the owner can attach it directly to ChatGPT or another primary reviewer.

Preferred implementation is Python stdlib `zipfile` so the workflow does not depend on a particular host `zip` utility. The exact gate runbook should provide the ready-to-run packaging command and exact expected archive name.

The final local-agent response for a visual gate must include a line in this form:

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_<GATE>.zip
```

The purpose is simple: if repository tooling exposes private PNGs only as encoded bytes, the owner can transfer the actual files as an attachment and the primary reviewer can truly inspect the pixels. Do not treat the local agent's textual `PASS` as a substitute for that independent view.

## Acceptance rule

A visual gate may be recorded as `SIMULATOR VISUAL REVIEW` locally only when all of the following are true:

- the simulator/runtime cases passed;
- the curated screenshots exist in the committed review directory;
- `REVIEW.md` records an actual pixel-level visual inspection;
- source/runtime cross-checks do not contradict the review/audit;
- layout audit does not reveal an unaddressed clipping/overlap/text-size defect;
- fail-soft behavior remains usable where the gate requires it;
- evidence scope is not overstated as physical-hardware approval;
- the mandatory owner-transfer ZIP has been created and its exact path reported when the gate is owner-driven.

When a subsequent reviewer has repository access, they should review the committed curated screenshots before treating the visual result as closed. If that review environment cannot directly display private-repository PNG bytes, it must say so explicitly and use the owner-transfer ZIP rather than pretending to have independently inspected the pixels.

## Repository-size rule

Keep this disciplined:

- commit only the curated 4–6 review images;
- keep raw/full-matrix evidence project-local unless a specific failure requires preservation;
- prefer PNG for pixel-exact low-resolution evidence;
- do not commit the owner-transfer ZIP;
- do not create a new screenshot directory for every trivial code edit — one directory per substantive visual gate.

The goal is **reviewability**, not evidence-volume inflation.
