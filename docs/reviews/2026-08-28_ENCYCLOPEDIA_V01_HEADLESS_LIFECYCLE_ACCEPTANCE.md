# Encyclopedia v0.1 — Headless lifecycle acceptance

**Date:** 2026-08-28  
**Disposition:** `SOURCE-VERIFIED / HEADLESS-LIFECYCLE-SMOKE-PASS / 43-PAGE-MECHANICAL-TRAVERSAL-PENDING`

## Evidence identity

Owner-machine starting SHA:

```text
621c1950133151b9c89c14ec74e4628e4c665147
```

Evidence directory:

```text
tmp/encyclopedia-v01-acceptance/20260828_070951-headless-route-smoke/
```

Previously accepted source-gate evidence:

```text
tmp/encyclopedia-v01-acceptance/20260828_044052/
```

## Result

The corrected terminal-only headless Simulator lane completed end to end:

```text
FOCUSED_SIMULATOR_TESTS                  PASS (45/45)
HEADLESS_BUILTIN_DETECTION               PASS
COLLECTION_FIRST_ROUTE_RESOLVED          PASS
ROUTE                                    home[2]=learn -> activity[4]=org.greia.enciclopedia
SHELL_FIRST_FRAME                        PASS
PROFILE_TO_COLLECTION_HOME               PASS
COLLECTION_ROUTE_NAVIGATION              PASS
ENCYCLOPEDIA_LAUNCH_VIA_REAL_SHELL       PASS
ENCYCLOPEDIA_FIRST_ACTIVITY_FRAME        PASS
SURVIVAL_12S                             PASS
BOUNDED_RETURN_INTERACTION               PASS
PROTECTED_HOME_RETURN_TO_SHELL           PASS
HEADLESS_SMOKE_RC                        0
WORKTREE_AFTER                           clean
```

The remote bridge reported a real `mode=activity` frame at 1024x600. After a 12-second survival window and a semantic `RETURN`, Greia's protected Home hitbox returned the session to real Shell `mode=activities`. The child Shell then exited cleanly with rc=0.

## Produced evidence

```text
enciclopedia-01-shell-frame.png
enciclopedia-02-activity-first-frame.png
enciclopedia-03-post-interaction.png
enciclopedia-04-returned-shell.png
enciclopedia-child.log
headless-smoke.txt
```

All four reported PNGs were valid 1024x600 screenshots.

## What this proves

This evidence establishes the real lifecycle path:

```text
real child profile picker
→ Collection-first Greia Home
→ Learn Collection
→ Enciclopedia Greia Activity card
→ production supervisor launch
→ real Encyclopedia frame
→ semantic input delivery
→ sustained runtime survival
→ protected platform Home
→ real Shell return
```

It also proves the earlier duplicate-identity and raw-registry-index failures were Simulator-harness defects rather than Encyclopedia runtime failures.

## What this does not prove

This smoke does **not** establish:

```text
all 43 Encyclopedia pages reachable
all 36 signature interactions visually correct
pointer/semantic-keyboard parity
pre-reader/no-reading UX quality
responsive-layout matrix
narration acceptance
physical Acer/Pi acceptance
```

Those remain distinct gates.

## libpng diagnostic warning

The child log contained:

```text
libpng error: bad adaptive filter value
```

The smoke still completed and all reported evidence screenshots were valid. The warning is therefore non-blocking for this lifecycle checkpoint, but its origin is unresolved. It must not be casually attributed to screenshot encoding; a failed runtime PNG asset decode with fail-soft visual fallback is also plausible.

The next 43-page traversal captures the child warnings again while validating every produced evidence PNG. If the warning persists, later visual review should identify whether any expected visual asset is absent or replaced by fallback artwork.

## Next gate

Mechanical traversal tooling:

```text
tools/encyclopedia_v01_headless_traversal.py
tests/test_encyclopedia_v01_headless_traversal.py
```

Operator prompt:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

The mechanical pass must capture all six section pages plus before/after evidence for all 36 factual entries, exercise semantic Back throughout, and return via protected Home. A changed frame is treated only as mechanical evidence; subjective signature/pre-reader acceptance remains a separate visual review.
