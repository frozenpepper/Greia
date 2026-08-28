# Greia Encyclopedia v0.1 — 43-page mechanical traversal acceptance

**Date:** 2026-08-28  
**Owner-machine tested SHA:** `8cda9cbaa4beb4f5c38a9945479f0f4c88f8ee65`  
**Disposition:** **MECHANICAL TRAVERSAL PASS / VISUAL-SIGNATURE REVIEW PENDING**

## Evidence

Owner-machine evidence directory:

```text
tmp/encyclopedia-v01-acceptance/20260828_074819-mechanical-traversal/
```

Evidence archive:

```text
tmp/encyclopedia-v01-acceptance/20260828_074819-mechanical-traversal.zip
```

The archive is evidence-only and is not a project package.

## Proven by this run

Focused traversal/Simulator tooling tests:

```text
53 / 53 PASS
```

Mechanical traversal:

```text
MECHANICAL_TRAVERSAL_RC=0
real Shell -> Encyclopedia                       PASS
sections captured                               6 / 6
factual entries reached                        36 / 36
bounded semantic ACTIVATE interactions         36 / 36
before/after entry screenshot pairs            36 / 36
internal semantic Back returns                 36 / 36
all sections return to Encyclopedia home       PASS
protected Greia Home -> real Shell             PASS
traversal-summary.json status                  PASS
worktree after run                             clean
```

The real child-visible Shell route was:

```text
home[2]=learn -> activity[4]=org.greia.enciclopedia
```

The run produced 82 PNG screenshots in 91 total evidence files, approximately 3.2 MiB uncompressed. The evidence ZIP is approximately 2.8 MiB.

The capture set includes:

```text
Shell profile picker
Encyclopedia home before traversal
all 6 section pages
36 factual-entry before frames
36 factual-entry after frames
Encyclopedia home after traversal
returned Shell
```

## What this proves

This is the first complete runtime breadth proof for the frozen 43-page v0.1 Encyclopedia through the real Greia Shell and Simulator bridge.

It establishes that:

- every planned runtime page is reachable through child-visible navigation;
- every factual entry accepts a bounded semantic primary interaction;
- every entry can return through Encyclopedia-internal Back;
- every section can return to Encyclopedia Home;
- protected Greia Home returns to the real Shell;
- one continuous mechanical traversal can complete without source mutation or runtime crash.

## What this does **not** prove

A nonzero `changed_pixel_fraction` is only evidence that pixels changed between the captured frames. It is **not** evidence that the intended educational/signature interaction is visually correct, understandable, attractive, or pre-reader friendly.

Still pending:

```text
visual/signature-interaction review of the captured frames
pointer vs semantic-keyboard parity sample
pre-reader/no-reading UX review
responsive viewport/profile matrix
narration owner acceptance/integration
physical low-end hardware acceptance
```

No source-gate rerun is required merely because this traversal passed.
No mechanical traversal rerun is required merely to begin visual review.

## Diagnostic warning retained

The child log contained exactly:

```text
libpng error: bad adaptive filter value
```

The run nevertheless completed and all expected screenshot evidence was produced. The warning remains diagnostically unresolved. Do not claim it comes from the screenshot encoder; it may instead indicate a PNG asset decode that fell back visually. The visual evidence review should explicitly look for missing/fallback imagery that could explain it.

## Current truthful status

```text
SOURCE-VERIFIED
HEADLESS-LIFECYCLE-SMOKE-PASS
43-PAGE-MECHANICAL-TRAVERSAL-PASS
VISUAL/SIGNATURE REVIEW PENDING
POINTER PARITY PENDING
PRE-READER UX PENDING
RESPONSIVE MATRIX PENDING
NARRATION ACCEPTANCE PENDING
```

Only after the visual/input/pre-reader/responsive Simulator gates pass may the Encyclopedia be labeled:

```text
SOURCE + SIMULATOR ACCEPTED / NARRATION ACCEPTANCE PENDING
```
