# Greia Documentation Deep Review — 2026-08-10

**Scope:** repository documentation architecture, current-vs-historical status, agent operations, Activity authoring, architecture overview, developer remote/testing guidance, and cross-checks against implemented source contracts  
**Result:** major documentation-structure and drift corrections applied  
**Implementation impact:** documentation/governance only; no product source behavior changed  
**Verification impact:** no source/VM/hardware test result changed or was newly claimed

---

## 1. Review goal

The review was not limited to grammar or formatting. It tested whether a new agent could answer, without chat history:

1. Which document owns a given kind of truth?
2. What is architecture versus current implementation?
3. What is current versus historical state?
4. Which Activity APIs/schema actually exist today?
5. How does an agent safely connect to and test physical Greia hardware?
6. Which claims are source-only, VM/image, or physical-hardware evidence?
7. Which developer conveniences are forbidden from leaking into normal/release Greia?
8. How are documentation changes kept synchronized with source changes?

---

## 2. Files/source contracts reviewed

Primary documentation:

```text
README.md
AGENTS.md
HANDOVER.md
docs/architecture/GREIA_ARCHITECTURE.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
docs/agents/GREIA_AGENT_OPERATIONS.md
skills/greia-activity-authoring/SKILL.md
```

Implementation contracts cross-checked:

```text
runtime/child-runtime.toml
runtime/theme-defaults.toml
runtime/progression-policy.toml
assets/catalog/core_icons_v1.toml
src/greia_platform/activities.py
src/greia_platform/activity_api.py
src/greia_platform/storage_client.py
src/greia_platform/event_client.py
src/greia_platform/event_protocol.py
src/greia_platform/customization.py
src/greia_platform/assets.py
src/greia_platform/developer_control.py
tools/validate_activity.py
tools/greia_remote.py
activities/shape_garden/activity.toml
activities/shape_garden/main.py
```

---

## 3. Findings and corrections

### D-01 — Documentation authority was implicit — HIGH drift risk

**Problem:** README, `AGENTS.md`, architecture, ADRs, active plan, handover, test protocols and agent manuals repeated overlapping facts without one explicit ownership/precedence model.

This makes normal drift dangerous: a stale test count or conceptual schema can appear as authoritative merely because it is written confidently in several places.

**Correction:** added:

```text
docs/DOCUMENTATION.md
```

It defines:

- repository work-rule authority;
- ADR authority;
- implemented source/runtime authority;
- active-plan authority;
- handover/current-state authority;
- test-protocol authority;
- derived agent-manual authority;
- historical review/evidence status;
- status vocabulary;
- update triggers;
- freshness rules;
- a documentation-review checklist.

**Decision:** durable overview docs should link to current state rather than copy transient SHAs/test counts everywhere.

---

### D-02 — README contained stale current-state claims — HIGH

**Problem:** the previous README:

- still described the old `2026-08-06_PHASE0_BOOTABLE_VERTICAL_SLICE.md` as the active plan;
- repeated the early Greia-migration `140/140` test snapshot as if it were the useful current verification reference;
- listed platform-owned watchdog/forced return as an open baseline item despite later source closure;
- described Xorg largely as historical source while the current installed production path actually remains the provisional Xorg/xinit compatibility backend.

**Correction:** rewrote README as a durable entry point.

It now:

- points at the real active remediation plan;
- sends exact current verification/hardware state to `HANDOVER.md`;
- removes obsolete current test-count duplication;
- correctly labels current installed Xorg/xinit as **PROVISIONAL**;
- explains current versus future Activity authoring;
- links the documentation authority model.

---

### D-03 — Architecture overview competed semantically with ADR 0012 — MEDIUM-HIGH

**Problem:** `docs/architecture/GREIA_ARCHITECTURE.md` was titled **Greia Architecture Constitution**, while ADR 0012 is the actual platform architecture constitution. The overview also contained future YAML/Web/storage/package examples that could be mistaken for current APIs.

**Correction:** renamed/reframed the document internally as:

```text
Greia Architecture — Living Overview
```

The file now explicitly says:

- accepted ADRs are normative;
- exact implementation schemas/APIs are source-owned;
- the overview is cross-cutting synthesis;
- conceptual YAML/storage/Web/package examples are not current copy-paste APIs;
- current Xorg/xinit is a provisional compatibility implementation;
- `.greiaactivity`, `.greiabackup`, Web SDK and capability-class numeric thresholds remain future/unfinalized until their implementation phases close.

---

### D-04 — Activity skill mixed strong guidance with insufficient implementation/future separation — HIGH ecosystem risk

**Problem:** the first Activity skill was useful but still required an agent to infer which portions were implemented today and which were architectural direction.

**Source facts verified:** current runtime API `0.1`; development package is a directory with `activity.toml`; current runtime is Python/Pygame; hard package ceiling is 50 MiB; current capability/permission vocabularies come from `runtime/child-runtime.toml`; `GREIA_ACTIVITY_CAPABILITIES` is not a security authority; current event protocol is JSON and capped at 64 KiB; current `ResolvedTheme` has concrete RGB/theme fields; core semantic icons are catalogue-backed; no general Activity widget toolkit exists.

**Correction:** substantially rewrote `skills/greia-activity-authoring/SKILL.md` with:

- implemented-now versus future matrix;
- exact source-of-truth read set;
- current TOML manifest example;
- exact capability/permission vocabulary snapshot with source-owner warning;
- lifecycle READY/STOP guidance and a minimal Pygame loop;
- exact storage methods;
- exact event protocol limit and receipt semantics;
- exact theme fields;
- real `shape_garden` reference pointers;
- stronger asset/memory/hot-loop guidance;
- explicit no-fabricated-widget-toolkit rule;
- definitions of done and maintenance triggers.

---

### D-05 — Hardware/operator manual lacked enough first-connection and identity-recovery detail — HIGH operational risk

**Problem:** the first agent operations manual explained the remote commands but not enough of the operator environment and SSH identity lifecycle. An intentional reimage can legitimately change the target host key; treating that as either always-dangerous or blindly-disabling verification are both bad outcomes.

**Correction:** rewrote `docs/agents/GREIA_AGENT_OPERATIONS.md` to add:

- start-of-task classification;
- source vs VM/image vs physical evidence;
- operator prerequisites (`python3`, `ssh`, `scp`, `ssh-keygen`);
- exact developer-vs-normal security model;
- first wired network acceptance;
- first connection workflow;
- dedicated `~/.greia/known_hosts` behavior;
- bounded intentional-reimage host-key rollover procedure;
- prohibition on `StrictHostKeyChecking=no` shortcuts;
- stable remote-control commands vs investigative shell;
- trust-preserving developer Activity deployment;
- physical evidence record requirements;
- stronger stop conditions;
- source files that must trigger manual drift review.

---

### D-06 — Hosted execution rule did not explicitly cover metadata/log/artifact queries — HIGH governance clarity

**Problem:** the project rule clearly prohibited unapproved hosted execution but was less explicit about using the GitHub Actions execution service for run/status/log/artifact queries.

During this documentation audit the assistant mistakenly issued read-only workflow-run metadata queries. They returned no runs and did not trigger/rerun execution, but they were outside the intended project boundary.

**Correction:** `AGENTS.md` and the agent operations manual now explicitly prohibit, without specific owner authorization:

```text
trigger/rerun/dispatch
automatic hosted triggers
Actions run/status/job/step/log/artifact queries
hosted artifact downloads
```

Reading/editing `.github/workflows/*` as ordinary repository source remains allowed when needed.

This correction makes the written rule match the intended project policy instead of relying on interpretation.

---

### D-07 — Status vocabulary was incomplete — MEDIUM

**Problem:** `CONSTITUTIONAL`, `SELECTED`, `PROVISIONAL`, `DEFERRED`, `UNPROVEN` were useful but did not cleanly express “source work closed but hardware evidence open” or “dated snapshot retained for provenance”.

**Correction:** documentation vocabulary now also defines:

```text
SOURCE-CLOSED
HISTORICAL
COMPLETE
```

and requires scope when using PASS/accepted/complete/supported.

---

### D-08 — Active plan has historical/current status readability debt — MEDIUM

**Problem:** the active plan is deliberately append-only, but some early phase-body status lines remain visually prominent even though later progress entries close those phases. For example, an early body can say a phase is in progress while the current handover/later log records it source-closed.

**Decision in this review:** do **not** rewrite old progress/history to make it look current. `docs/DOCUMENTATION.md` now says current state is owned by `HANDOVER.md` plus latest progress entries.

**Recommended future cleanup:** add a small generated/maintained current phase-status index near the top of the active plan without altering historical entries. This should be done when the plan next receives an implementation-state update, not by rewriting historical evidence during a documentation-only audit.

---

### D-09 — Developer remote protocol is narrow but materially consistent — NO BLOCKING DEFECT

The dedicated remote-control test protocol was cross-checked against the current remote client/control source. Its security boundary and command model remain materially consistent.

General operator/reimage/known-host procedure now lives in the agent operations manual rather than duplicating the full procedure into the feature-specific acceptance document.

---

## 4. Documentation architecture after the review

```text
AGENTS.md
  repository-wide rules / non-negotiables
        │
        ├── docs/DOCUMENTATION.md
        │     ownership / precedence / freshness
        │
        ├── accepted ADRs
        │     normative architecture decisions
        │
        ├── docs/architecture/GREIA_ARCHITECTURE.md
        │     living synthesis / conceptual model
        │
        ├── source + runtime declarations
        │     exact implemented APIs / schemas / commands
        │
        ├── active remediation plan
        │     ordering / closure / append-only progress
        │
        ├── HANDOVER.md
        │     current branch / evidence / next step
        │
        ├── docs/testing/*
        │     exact named procedures
        │
        ├── docs/agents/GREIA_AGENT_OPERATIONS.md
        │     derived agent/project/hardware operations
        │
        └── skills/greia-activity-authoring/SKILL.md
              derived Activity authoring playbook
```

---

## 5. Commits created by this documentation audit

### Active branch `r7-direct-graphics`

```text
3f44690a4066d80aeceec3e4dfdb6feeb477ef63  docs/DOCUMENTATION.md
54c04b43fdbe12dad72875f3654219703362ca3e  durable README rewrite
376a2a2dc9d79f1f20cda2919530bc3142d99e3e  AGENTS authority/Actions clarification
950289ad4dd07861ebe4545ebecdd56bf387afd3  agent operations deep rewrite
428ad0da818060df3f78c231feb1ff5c9352b273  Activity skill deep rewrite
ddd9347ee596dc9f98429f4db68a84b53dcaee2a  architecture overview clarification
```

### `main` synchronized repository-wide documentation

```text
0c59799987f090b0f3e9e1d92cd801a943d1fc61  docs/DOCUMENTATION.md
5c6f948f730a2c22155881a67adcfb748bc42ea5  durable README rewrite
89843608d1433564cc959aeb3bd570884cffbe1c  AGENTS authority/Actions clarification
39ad96edc4cf045a37d327d3be05fda52aab7942  agent operations deep rewrite
65bbc04b5409fe5a201e5a6744ad23c728692472  Activity skill deep rewrite
86783af9c10ca9262ce665cc57282c75b40723fd  architecture overview clarification
```

The long-lived repository-wide documents were intentionally synchronized on `main` and the active branch so they do not depend on PR #4 merging.

---

## 6. Verification/evidence boundary

This was a **documentation/source-reading audit**.

No product source behavior was changed and no source/unit/VM/hardware verification command was executed as part of this audit.

Therefore this review does **not** change the existing verification boundary recorded in `HANDOVER.md`.

In particular, do not infer from this review any new claim for:

- current full `make verify`;
- developer-remote regression execution;
- developer image build;
- SSH/mDNS/screenshot/input hardware acceptance;
- remote Activity deployment acceptance;
- active or serial QEMU KMSDRM;
- active seat/input;
- physical Acer;
- physical Raspberry Pi.

---

## 7. Ongoing maintenance rule

The documentation system is now designed to reduce drift, but it still requires discipline:

- implementation schemas/APIs change → update derived skill/manual in the same tranche;
- implementation/phase state changes → update plan + handover;
- test procedure changes → update exact test protocol;
- architecture decision changes → ADR first, overview second;
- durable overview docs should link to current state rather than copy transient test counts/SHAs.

A documentation review should be repeated whenever a major architecture phase closes or a new runtime/package/backup ecosystem surface becomes implemented.
