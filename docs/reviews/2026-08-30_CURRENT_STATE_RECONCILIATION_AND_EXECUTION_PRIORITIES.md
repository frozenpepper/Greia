# Greia — Current State Reconciliation and Execution Priorities

**Date:** 2026-08-30  
**Document class:** dated execution snapshot/review — not a competing active implementation plan  
**Observed `main`:** `3d2d29d57f5bbf2c1a4d2554117f21247ba19df4`  
**Blocking authority remains:** `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`

## Current reconciliation

Recent history contains three overlapping lanes:

1. **R7.3 trusted system-chrome migration** — the strict first-party Activity Home/chrome source migration reached zero blockers and a green source gate before the later refactor wave.
2. **Activity architecture modernization** — large Activities are being decomposed into thinner composition roots and cohesive model/app/renderer/audio/content owners; several brittle source-shape/smoke tests and bootstrap compatibility shims were removed or redirected toward real owners/behavior.
3. **Encyclopedia E3** — E3 is accepted on exact SHA `03bf76acb3e4c3f6d40b346d510f55a4763efc2d`; E4 is unblocked.

The root `HANDOVER.md`, the old flat R7.3 queue, and some visual continuation prose still lag behind those facts.

## Current status

```text
Architecture remediation plan:       ACTIVE / BLOCKING

R7.1 Activity backend independence:  SOURCE-INTEGRATED
R7.2 Legacy-X containment:           SOURCE-INTEGRATED / ACER ACCEPTANCE PENDING
R7.3 trusted system chrome:           SOURCE-INTEGRATED / ACER ACCEPTANCE PENDING
R7.3 strict Activity migration:       COMPLETE
Activity lighter modernization pass: PARTIAL / ONGOING
R7.4 controller/system input:         NEXT AFTER R7.3 PHYSICAL ACCEPTANCE
ADR-0014 final direct/compositor path: OPEN

Encyclopedia E1:                      COMPLETE
Encyclopedia E2/E2R:                  APPROVED
Encyclopedia E3:                      COMPLETE / ACCEPTED
Encyclopedia E4:                      UNBLOCKED

Current-main aggregate source gate:   RE-BASELINE REQUIRED AFTER LATEST MERGE/REFACTOR WAVE
```

Accepted Encyclopedia E3 evidence:

```text
11/11 deterministic SVG -> runtime PNG PASS
59/59 focused Encyclopedia tests PASS
repository verify PASS at exact E3 SHA
7/7 real Greia Simulator section-family sessions PASS
11/11 runtime-art SHA-256 entries
11/11 committed Git-blob bindings
visual review ACCEPTED
```

E3 must not be reopened merely because unrelated Activities or platform code later change.

## Scheduling decision — bounded stabilization window

The next objective is **not another broad refactor**.

Use a short stabilization window:

> stabilize current `main` -> prove current source -> deploy one exact SHA to the Acer -> complete R7.2 + R7.3 physical acceptance -> resume feature/refactor churn.

Physical R7 evidence is exact-source evidence. Continuing to merge Activity decompositions or E4 visual work while preparing the physical gate continuously invalidates the target SHA.

## P0 — Reconcile authority documents

Update:

```text
HANDOVER.md
encyclopedia/HANDOVER.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/plans/2026-08-29_R7_R73_ACTIVITY_MODERNIZATION.md
docs/plans/2026-08-29_R7_R73_ACTIVITY_QUEUE.md
```

Required state:

```text
Encyclopedia E3 -> COMPLETE / ACCEPTED
Encyclopedia E4 -> UNBLOCKED / NEXT
accepted E3 SHA -> 03bf76ac...

R7.3 strict migration -> COMPLETE
old 62-blocker queue -> HISTORICAL / CLOSED
lighter architecture/performance pass -> PARTIAL / ONGOING
R7.3 physical acceptance -> PENDING
```

The root handover should make the order explicit:

```text
1. current-main source re-baseline
2. exact-SHA R7.2 + R7.3 Acer acceptance
3. R7.4 / direct-backend work
4. resume bounded Activity modernization and Encyclopedia E4
```

## P1 — Current-main source stabilization gate

Work from one clean current SHA and do not modify source during the gate.

Run:

```bash
make verify
PYTHONPATH=src python3 tools/audit_activity_backend_independence.py activities
PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict
```

Required:

```text
make verify PASS
backend blockers=0
chrome blockers=0
```

Also run the exact focused suites from:

```text
docs/testing/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_SOURCE_AND_ACER_ACCEPTANCE.md
docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md
```

Because the latest decompositions landed after the prior green gate, explicitly spot-check the recently changed Activities:

```text
acquario_magico
teatrino_fiabe
sillabe_magiche
costruiamo_ponti
treno_numeri
piccola_serra
foresta_parole
cucciolo_mio
pasticceria_magica
```

Where obsolete bootstrap compatibility was intentionally removed, validate the new owner module/API rather than recreating retired exports.

P1 closes only with one exact clean SHA where all listed gates pass. Freeze that SHA for P2.

## P2 — Combined R7.2 + R7.3 Acer acceptance

Use the same exact deployed SHA where practical.

### R7.2

Authority:

```text
docs/testing/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_SOURCE_AND_ACER_ACCEPTANCE.md
```

Must prove:

```text
Shell boot/focus/input
Writing real path
Painting sustained pointer path
abrupt Activity crash recovery
20/20 mixed Shell -> Activity -> Shell cycles
no direct DRM requirement
no raw /dev/input requirement
no child-visible Linux surface
no material performance regression
```

### R7.3

Authority:

```text
docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md
```

Must prove:

```text
trusted Home over Writing/Painting
protected Home activation does not leak into Activity input
hostile non-cooperative fixture
10/10 hostile forced returns without launcher restart
0 stale chrome windows
0 stuck Activity processes
crash cleanup
next Activity launch after recovery
acceptable Acer performance
```

R7.3 requires compatible R7.2 evidence.

Collect bounded measurements/observations for Shell idle, Writing, Painting, one static Activity, one animated Activity, launch->READY, Home->Shell, hostile forced return, and CPU/RSS/PSS where practical.

## P3 — Post-R7.3 cleanup

Only after R7.3 physical acceptance:

1. promote the zero-debt system-chrome rule into normal Activity validation;
2. remove remaining temporary ignored cooperative-chrome compatibility APIs after proving zero callers;
3. preserve safe/protected geometry;
4. keep Legacy-X adapters until a replacement backend has evidence;
5. rerun focused tests, audits, and `make verify`.

## P4 — R7.4 controller/system-input ownership

Goals:

```text
controller discovery/normalization platform-owned
runtime-neutral input profiles
reserved Greia system input consumed before Activity delivery
no raw /dev/input for normal Activities
virtual pointer bounded and low-latency
keyboard/pointer/touch/controller coexist
```

Do not create per-Activity controller mappings.

## P5 — Final R7 direct/compositor evidence

Legacy-X success does not close R7.

Use the existing `DisplaySessionCoordinator` / `DisplaySessionBackend` seam to evaluate:

```text
direct DRM/KMS
or
minimal compositor if measurement proves it is the thinner practical solution
```

Constraints:

```text
zero Activity backend changes
no Python framebuffer proxy
no avoidable full-screen copy/composition tax
no high-rate input IPC
trusted Home/system input outside Activity authority
Writing/Painting remain responsive
Acer remains viable
```

Select from evidence, then remove migration plumbing.

## P6 — Resume Activity modernization selectively

The strict R7.3 migration is already complete. Do not keep refactoring everything because a file is large.

For each remaining Activity choose:

```text
KEEP
REFINE
DECOMPOSE
```

Refactor only for concrete mixed ownership, hot-path cost, testability debt, or pre-reader UX risk.

Recent decompositions already include:

```text
acquario_magico
teatrino_fiabe
sillabe_magiche
costruiamo_ponti
treno_numeri
piccola_serra
foresta_parole
cucciolo_mio
pasticceria_magica
```

Likely next review candidates:

```text
baia_delle_orche
bottega_delle_misure
casa_del_dieci
festa_delle_rime
morbidi_mostriciattoli
nanna_delle_nuvolette
shape_garden
stelle_incantate
storie_della_mia_voce
volo_draghetto
writing
painting
```

Healthy Activities should explicitly be marked KEEP.

## P7 — Encyclopedia E4

E4 is unblocked, but defer its first commits until the P2 stabilization window ends unless the owner explicitly accepts restarting the R7 source gate afterward.

Sequence:

```text
E4-A Organic / Nature
E4-B Space
E4-C Body
E4-D Machines
E4-E History
```

E4-A:

```text
lion
elephant
octopus
bee
penguin
frog
volcano
rain
ocean
tree
rainbow
```

Use the accepted E3 bar: immediate recognition, coherent anatomy, no programmer primitives as final hero art, a small number of meaningful discoveries, visual teaching payoff, integrated presenter, no text rescue, build-time PNGs and bounded runtime cache.

Use bounded batch contact-sheet/Simulator review; do not rerun all 43 pages after every entry.

## Monitoring rule

Classify each new commit as:

```text
PLATFORM-R7
ACTIVITY-MODERNIZATION
ENCYCLOPEDIA-VISUAL
TEST/TOOLING
DOCS
OTHER
```

For each commit ask:

1. Did it touch the P1/P2 acceptance path?
2. Did it invalidate the exact acceptance SHA?
3. Did it change Activity authority or only internal architecture?
4. If it removed a test, what behavior/owner-level coverage remains?
5. Did it modify accepted Encyclopedia source/runtime art?
6. Did it make `HANDOVER.md` stale?

Once P1 selects the acceptance SHA, any PLATFORM-R7, ACTIVITY-MODERNIZATION, or ENCYCLOPEDIA-VISUAL source commit must either wait until P2 finishes or explicitly restart P1 on the new SHA.

## Immediate next three tranches

### A — documentation reconciliation

```text
current HANDOVER
E3 accepted / E4 unblocked
old R7.3 strict queue marked completed/historical
modernization plan split into completed strict migration + ongoing lighter pass
```

### B — current-main green source freeze

```text
exact SHA
clean tree
make verify PASS
backend blockers=0
chrome blockers=0
R7.2 focused PASS
R7.3 focused PASS
recent decomposition spot-check PASS
```

### C — Acer physical acceptance

```text
R7.2 physical verdict
R7.3 physical verdict
Writing evidence
Painting evidence
20/20 normal durability cycles
10/10 hostile forced-return cycles
crash recovery
performance evidence
no child-visible Linux surface
```

Only after C should broad implementation churn resume.

## Recommendation

The project does not currently need another broad architectural rewrite.

The next objective is:

> **stabilize current main -> re-prove the current source -> physically accept R7.2/R7.3 on the Acer -> then resume R7.4, selective Activity modernization, and Encyclopedia E4.**
