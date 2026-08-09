# Greia Documentation Deep Review — 2026-08-10

**Scope:** repository documentation architecture, current-vs-historical state, agent operations, Activity authoring, architecture overview, developer remote/testing guidance, and cross-checks against implemented source contracts  
**Result:** major documentation-structure and drift corrections applied  
**Implementation impact:** documentation/governance only; no product behavior changed  
**Verification impact:** no source/VM/hardware result changed or was newly claimed

---

## 1. Review goal

This was a structural documentation audit, not a grammar pass. It asked whether a new agent could determine, without chat history:

1. which document owns a fact;
2. architecture versus current implementation;
3. current versus historical state;
4. the Activity APIs/schema that actually exist today;
5. how to safely build/connect/test Greia hardware;
6. source versus VM/image versus physical evidence;
7. developer-only versus release behavior;
8. how documentation stays synchronized with source.

---

## 2. Documentation and source contracts reviewed

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

README, `AGENTS.md`, architecture, ADRs, the plan, handover, test protocols and manuals repeated overlapping facts without one explicit ownership/precedence rule.

**Correction:** added `docs/DOCUMENTATION.md`, defining:

- repository work-rule authority;
- ADR authority;
- implemented source/runtime authority;
- active-plan authority;
- current-state/handover authority;
- test-protocol authority;
- derived agent-manual authority;
- historical review/evidence status;
- freshness/update rules;
- status vocabulary and audit checklist.

**Rule:** durable overview docs link to current state instead of copying transient SHAs/test counts everywhere.

---

### D-02 — README had stale current-state claims — HIGH

The old README still named the 2026-08-06 Phase-0 plan as active, repeated the early 140/140 migration snapshot, listed already-source-closed lifecycle work as open, and described Xorg as mainly historical rather than the current provisional installed compatibility path.

**Correction:** README on the active branch is now a durable project entry point:

- correct remediation plan;
- exact state delegated to `HANDOVER.md`;
- stale test-count duplication removed;
- current Xorg/xinit labelled **PROVISIONAL**;
- current/future Activity authoring separated;
- documentation authority model linked.

---

### D-03 — Architecture overview competed with ADR 0012 — MEDIUM-HIGH

`docs/architecture/GREIA_ARCHITECTURE.md` called itself the “Architecture Constitution”, while ADR 0012 is the actual architecture constitution. It also contained conceptual YAML/Web/storage/package examples without enough warning that they are not the current API.

**Correction:** it is now **Greia Architecture — Living Overview** and explicitly states:

- accepted ADRs are normative;
- source/runtime declarations own exact current schemas/APIs;
- the overview is synthesis;
- conceptual YAML/storage/Web/package examples are not copy-paste authoring specifications;
- current installed Xorg/xinit is provisional compatibility;
- `.greiaactivity`, `.greiabackup`, Web SDK and numeric capability thresholds remain future/unfinalized until implemented.

---

### D-04 — Activity skill needed stronger implemented/future separation — HIGH ecosystem risk

Source cross-check established the current authoring facts:

```text
runtime API:                 0.1
development package:         directory + activity.toml
runtime:                     Python/Pygame
package hard ceiling:        50 MiB
capabilities/permissions:    runtime/child-runtime.toml
capability env string:       usability hint, not security authority
event protocol:              JSON, 64 KiB encoded-message ceiling
shared graphics:             semantic icon catalogue + theme API
general widget toolkit:      not implemented
```

**Correction:** `skills/greia-activity-authoring/SKILL.md` now includes:

- implemented-now versus future table;
- exact source-owner read set;
- current TOML manifest pattern;
- exact capability/permission vocabulary snapshot with source-owner warning;
- READY/STOP + minimal Pygame lifecycle loop;
- exact storage methods;
- event ceiling/receipt semantics;
- concrete `ResolvedTheme` fields;
- real `shape_garden` references;
- low-end rendering/asset/hot-loop guidance;
- explicit no-fabricated-widget-toolkit rule;
- source-ready definitions of done and maintenance triggers.

---

### D-05 — Hardware/operator manual lacked identity/reimage detail — HIGH operational risk

The initial operations manual documented remote commands but not enough operator prerequisites and SSH identity lifecycle.

**Correction:** `docs/agents/GREIA_AGENT_OPERATIONS.md` now covers:

- source/VM/physical evidence classification;
- Python/OpenSSH operator prerequisites;
- developer versus normal image security;
- first wired-network acceptance;
- first connection;
- dedicated `~/.greia/known_hosts` handling;
- bounded intentional-reimage host-key rollover using `ssh-keygen -R` only after confirming the reimage;
- explicit rejection of `StrictHostKeyChecking=no` shortcuts;
- stable bounded remote controls versus investigative SSH shell;
- Activity trust-preserving deployment;
- physical evidence records;
- performance evidence and stop conditions;
- exact source files that trigger manual drift review.

---

### D-06 — Hosted-execution rule did not explicitly cover queries — HIGH governance clarity

The project already prohibited unapproved hosted Actions execution, but the wording did not explicitly cover using the Actions service for run/status/log/artifact queries.

During this audit the assistant mistakenly made read-only workflow-run metadata queries. They returned no runs and did not trigger/rerun execution or create hosted work, but they were still outside the intended project boundary.

**Correction:** active-branch `AGENTS.md` and the operations manual now explicitly prohibit, without specific owner authorization:

```text
trigger / rerun / dispatch
automatic hosted triggers
Actions run/status/job/step/log/artifact queries
hosted artifact downloads
```

Reading/editing `.github/workflows/*` as ordinary repository source remains allowed.

---

### D-07 — Status vocabulary was incomplete — MEDIUM

Added/standardized:

```text
CONSTITUTIONAL
SELECTED
PROVISIONAL
SOURCE-CLOSED
UNPROVEN
DEFERRED
HISTORICAL
COMPLETE
```

PASS/accepted/complete/supported must name the scope when ambiguity is possible.

---

### D-08 — Active plan has current-status readability debt — MEDIUM

The active plan is append-only, so early phase-body status lines can remain visually stale after later progress entries source-close those phases.

**Decision:** do not rewrite historical progress during this documentation-only audit. Current state is owned by `HANDOVER.md` plus latest progress entries.

**Future improvement:** when the plan next receives a real implementation-state update, add a small current phase-status index near the top without changing historical entries.

---

### D-09 — Developer remote acceptance protocol remains materially consistent — NO BLOCKING DEFECT

The dedicated remote-control test protocol was cross-checked against `tools/greia_remote.py` and `developer_control.py`. Its command/security model remains materially consistent.

General connection/reimage/known-host procedure belongs in the operations manual rather than being duplicated into every feature-specific protocol.

---

## 4. Resulting documentation ownership model

```text
AGENTS.md
  repository-wide rules / non-negotiables
        │
        ├── docs/DOCUMENTATION.md
        │     ownership / precedence / freshness
        │
        ├── accepted ADRs
        │     normative decisions
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

## 5. Integration history and commits

### Active branch audit commits

```text
3f44690a4066d80aeceec3e4dfdb6feeb477ef63  add documentation ownership model
54c04b43fdbe12dad72875f3654219703362ca3e  rewrite README as durable entry point
376a2a2dc9d79f1f20cda2919530bc3142d99e3e  clarify AGENTS authority/Actions boundary
950289ad4dd07861ebe4545ebecdd56bf387afd3  deepen agent operations manual
428ad0da818060df3f78c231feb1ff5c9352b273  deepen Activity authoring skill
ddd9347ee596dc9f98429f4db68a84b53dcaee2a  clarify architecture overview authority
6f53c651265810df13ec9829779348831107c51e  add this review
42befb3441e6021c5ec853d95230b0a81d51a28e  refresh standalone handover
```

The audit versions were initially also committed independently to `main`. That produced a Git history conflict with PR #4 even where final file bytes matched.

To preserve a clean feature integration without force-pushing or weakening the manual-only workflow:

1. the **audit-only duplicate `main` tree changes were explicitly reverted** in main commit `06590b484e091617cc96583fb9291034509b7990`;
2. the newer audited documentation remained on `r7-direct-graphics`;
3. a true two-parent reconciliation commit, `ea5c68953c73571a5d2ab5f73f0638428c7b25c8`, merged current `main` history into the R7 branch while retaining the R7 tree as the explicit conflict resolution;
4. temporary sync PR #5 was closed unmerged;
5. PR #4 returned to **mergeable=true**.

Therefore the **current audited versions live on `r7-direct-graphics` / PR #4**. `main` retains its pre-audit documentation state until PR #4 or a later deliberate documentation integration brings the reviewed versions across.

No branch was force-reset and no R7 implementation content was discarded.

---

## 6. Verification/evidence boundary

This was a documentation/source-reading audit.

No product source behavior changed and no source/unit/VM/hardware verification command was executed as part of the audit.

It does **not** change the existing verification boundary in `HANDOVER.md` and provides no new claim for:

- current full `make verify`;
- developer-remote regression execution;
- developer image build;
- SSH/mDNS/screenshot/input hardware acceptance;
- remote Activity deployment acceptance;
- active/serial QEMU KMSDRM;
- active seat/input;
- physical Acer;
- physical Raspberry Pi.

---

## 7. Ongoing maintenance rule

- implementation schema/API changes → update the affected derived skill/manual in the same tranche;
- implementation/phase state changes → update plan + handover;
- test procedure changes → update the exact test protocol;
- architecture decision changes → ADR first, overview second;
- durable overview docs should link to current evidence instead of copying transient test counts/SHAs;
- repeat a documentation audit after major architecture-phase closures or when a new runtime/package/backup ecosystem surface becomes real.
