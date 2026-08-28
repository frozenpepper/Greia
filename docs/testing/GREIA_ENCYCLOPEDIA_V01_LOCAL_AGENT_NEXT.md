# Greia Encyclopedia v0.1 — LOCAL AGENT NEXT TASK

The visual evidence review of the green 43-page mechanical traversal is complete.

Authoritative review:

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_VISUAL_EVIDENCE_REVIEW.md
```

It found:

```text
43-page reachability/back                 PASS
coherent first-interaction visual pairs   34 / 36
space.sun before/after                     capture race
space.neptune before/after                 capture race
history.pyramids intro caption             overflow defect
Body Teeth section target                  low-contrast defect
```

The primary agent has already fixed the Pyramids caption rendering and Body Teeth affordance on `main`.

The next owner-machine task is now the **traversal transition-settle repair + verification + fresh evidence recapture**.

Follow exactly:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_VISUAL_REPAIR_LOCAL_AGENT.md
```

Do not use an older cached copy of this rolling file.
Do not use the broad consolidated acceptance runbook.
Do not generate or integrate narration.
Do not start pointer/responsive acceptance yet.

This tranche is allowed to change only the traversal helper/test required to fix the generic page-transition capture race. The runtime Pyramids/Body fixes are already landed and must not be casually rewritten.

Required sequence is exactly:

```text
safe update
→ implement generic traversal transition-settle contract + regression
→ focused tests once
→ commit/push harness/test fix
→ Encyclopedia source gate once (runtime source changed)
→ fresh 43-page mechanical traversal once
→ evidence ZIP
→ stop for primary visual review
```

Current truthful state:

```text
SOURCE-VERIFIED AT PRIOR SHA
HEADLESS-LIFECYCLE-SMOKE-PASS
43-PAGE REACHABILITY/BACK PASS
34/36 COHERENT FIRST-INTERACTION VISUAL PAIRS
VISUAL REPAIRS LANDED / REVERIFY PENDING
POINTER PARITY PENDING
PRE-READER FINAL ACCEPTANCE PENDING
RESPONSIVE MATRIX PENDING
NARRATION ACCEPTANCE PENDING
```
