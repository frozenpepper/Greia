# Greia Documentation Map and Authority Model

**Status:** repository-wide documentation contract  
**Last reviewed:** 2026-08-13  
**Audience:** contributors, coding agents, reviewers, test operators, Activity authors

---

## 1. Purpose

Greia has several kinds of truth: repository rules, product requirements, accepted architecture, engineering guidance, implemented APIs, active sequencing, current evidence, test procedures, and historical reviews. These documents must not silently compete.

This file defines **which document class owns which fact**, how conflicts are resolved, and which documents must change when implementation changes. A contributor should be able to determine whether a statement is a durable rule, product requirement, selected architecture, implementation fact, current evidence, or historical context without chat history.

---

## 2. Authority and ownership

### 2.1 Repository-wide rules — `AGENTS.md`

`AGENTS.md` owns mandatory contributor/agent behavior and non-negotiable repository/product constraints, including:

- required read/update duties;
- Git/GitHub persistence rules;
- paid/hosted execution restrictions;
- non-negotiable product contracts;
- engineering expectations;
- continuity and evidence terminology.

A narrower document may strengthen but must not weaken `AGENTS.md`.

### 2.2 Product requirements — `docs/product/*`

Product requirement documents own explicitly accepted child-facing scope and UX requirements. They constrain design but do not override accepted ADRs, security boundaries, or source-owned API contracts.

Example: `docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md` owns the mandatory Phase-0 Writing/Painting product scope and acceptance intent.

### 2.3 Normative architecture — accepted ADRs

Accepted ADRs own architecture decisions. Important current examples include:

- ADR 0012 — platform architecture constitution;
- ADR 0013 — declarative image profiles/composable artifacts;
- ADR 0014 — Greia identity, ARM parity and direct-graphics direction;
- ADR 0018 — lightweight Screen/Overlay/Collection UI foundation.

A newer ADR supersedes an older one only where it explicitly says so.

`docs/architecture/GREIA_ARCHITECTURE.md` is the living cross-cutting synthesis of accepted architecture; it is not a second ADR system.

### 2.4 Repository engineering guidance — `docs/engineering/ENGINEERING_FOUNDATIONS.md`

This mandatory guide owns repository-wide implementation guidance for:

- strong OOP structure around real domain concepts;
- purposeful polymorphism at genuine variation points;
- composition versus inheritance;
- dependency direction and explicit ownership/lifecycle;
- bounded-resource and low-allocation engineering;
- documentation and testability expectations for extension points.

It does **not** override accepted ADRs or exact source contracts. If a rule becomes architectural rather than implementation guidance, record it in an ADR and keep this guide aligned.

### 2.5 Exact implemented contracts — source/runtime declarations

For exact currently implemented APIs, schemas, command vocabularies and limits, source/runtime declarations are authoritative.

| Fact | Canonical implementation owner |
|---|---|
| Activity manifest parser/validation | `src/greia_platform/activities.py` |
| Activity runtime/capability/permission/package policy | `runtime/child-runtime.toml` |
| Python Activity SDK helpers | `src/greia_platform/activity_api.py` |
| renderer-neutral UI semantics/navigation/resource primitives | `src/greia_platform/ui_core.py` |
| current Pygame child UI helpers | `src/greia_platform/activity_ui.py` |
| Activity storage operations | `src/greia_platform/storage_client.py` |
| Activity event protocol/client | `src/greia_platform/event_protocol.py`, `src/greia_platform/event_client.py` |
| shared semantic icons | `assets/catalog/core_icons_v1.toml` |
| theme defaults | `runtime/theme-defaults.toml` |
| resolved theme object | `src/greia_platform/customization.py` |
| developer remote client vocabulary | `tools/greia_remote.py` |
| privileged developer operations | `src/greia_platform/developer_control.py`, `src/greia_platform/developer_input.py` |
| image composition | `build/profiles/*.toml`, `build/package-sets/*.txt`, canonical builders |

Documentation may explain these contracts but must not invent a conflicting one. If implementation intentionally changes, update affected living manuals in the same tranche.

### 2.6 Active implementation sequencing — active plan

`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` owns active ordering, prerequisites, closure criteria, and its append-only progress history while active.

The plan does not override accepted architecture or accepted product requirements. Historical progress entries remain historical; current continuation/evidence belongs in `HANDOVER.md`.

### 2.7 Current branch/evidence state — `HANDOVER.md`

`HANDOVER.md` owns the current continuation snapshot:

- active branch/PR and blocking phase;
- what source is implemented now;
- which tests actually executed;
- what remains unexecuted/unproven;
- VM/physical-hardware evidence boundaries;
- exact next legitimate step.

Transient SHAs, test counts and blockers should normally live here rather than in durable architecture documents.

### 2.8 Exact test/operator procedures — `docs/testing/*`

Named test protocols own prerequisites, commands, stop conditions, evidence to preserve, and what a PASS does not prove. They may be stricter than general guidance but may not weaken repository or architecture safety rules.

### 2.9 Agent/developer manuals — `docs/agents/*` and `skills/*`

`docs/agents/GREIA_AGENT_OPERATIONS.md` is the operational entry point for project/build/test-hardware work.

`skills/greia-activity-authoring/SKILL.md` is the canonical living authoring guide for Activities.

These are derived manuals. They must track source/ADRs/product rules and never outrank them.

### 2.10 Reviews/evidence — `docs/reviews/*`

Reviews are dated analysis/evidence snapshots unless explicitly promoted into an ADR, product requirement, or active-plan decision. Do not silently rewrite historical evidence to match later reality.

---

## 3. Status vocabulary

Use these repository terms consistently:

- **CONSTITUTIONAL** — durable platform/product invariant.
- **SELECTED** — implementation/design selected by accepted decision.
- **PROVISIONAL** — current implementation while architecture/evidence remains open.
- **SOURCE-CLOSED** — required source scope closed at the named boundary; runtime/hardware evidence may remain.
- **UNPROVEN** — designed/implemented but lacking required execution/runtime/hardware evidence.
- **DEFERRED** — intentionally outside the current phase.
- **HISTORICAL** — retained provenance, not current instruction.
- **COMPLETE** — all explicitly named closure criteria satisfied.

Never use `PASS`, `accepted`, `complete`, or `supported` without naming the scope when ambiguity is possible.

---

## 4. Implemented versus conceptual examples

Architecture documents often use conceptual examples to communicate semantics. They are not automatically current APIs.

In particular:

- conceptual YAML manifests do not replace the implemented `activity.toml` parser;
- conceptual storage snippets do not replace the current Activity Storage client;
- `.greiaactivity` and `.greiabackup` remain architectural directions until their implementation phases close;
- Web SDK/runtime examples remain future-facing until implemented;
- capability-class examples remain semantic until measured/versioned;
- UI terms in ADR 0018 are renderer-neutral semantics; current Pygame helpers in `activity_ui.py` are one implementation layer, not the permanent universal renderer contract.

Activity authors use the Activity skill plus the implementation owners above.

---

## 5. Freshness rules

### Durable

Keep transient execution facts out of:

- `README.md`;
- `AGENTS.md`;
- accepted ADRs;
- `docs/product/*` requirement documents;
- `docs/architecture/GREIA_ARCHITECTURE.md`;
- `docs/engineering/ENGINEERING_FOUNDATIONS.md`;
- this documentation map.

### Frequently updated

Current state belongs in:

- `HANDOVER.md`;
- active-plan progress log;
- active test protocols;
- dated evidence/review reports.

### Historical

Do not rewrite old evidence/progress entries to make history cleaner. Append corrections or add a superseding dated review.

---

## 6. Required update triggers

| Change | Required documentation update |
|---|---|
| repository workflow / hardware operation | `docs/agents/GREIA_AGENT_OPERATIONS.md` |
| repository-wide OOP/dependency/performance/maintainability rules | `docs/engineering/ENGINEERING_FOUNDATIONS.md`; `AGENTS.md` when non-negotiable |
| Activity manifest/API/runtime/trust/assets/theme/UI/performance/deploy flow | `skills/greia-activity-authoring/SKILL.md` |
| child-facing accepted product scope/acceptance | relevant `docs/product/*`; `AGENTS.md` when non-negotiable |
| architectural decision | ADR + architecture overview when cross-cutting |
| renderer-neutral UI architecture/semantics | ADR 0018 + `ui_core.py` + affected living manuals |
| active ordering/closure criteria | active plan |
| current implementation/evidence/blocker | `HANDOVER.md` |
| test command/stop/evidence protocol | applicable `docs/testing/*` |
| reference hardware/resource requirement | `AGENTS.md`/ADR as appropriate + authoring guidance when relevant |

A source change that leaves a mandated living manual materially wrong is incompletely documented.

---

## 7. Avoid duplication

Link to the owner of a fact instead of copying transient details across many files. Safety-critical rules may be intentionally duplicated, but duplicated safety language must remain semantically identical.

Prefer:

> Current executed verification and unproven hardware gates are recorded in `HANDOVER.md`.

Avoid copying the same branch SHA/test count into README, architecture, testing guides, plan headers, and PR descriptions.

---

## 8. Review checklist

A documentation review should verify at least:

1. paths point to real canonical files;
2. active plan references are current;
3. durable docs do not present stale SHAs/test counts as current truth;
4. implemented and future APIs are distinguished;
5. product requirements are separate from exact implementation;
6. ADR 0018/UI-core semantics are not confused with Pygame-only helpers;
7. engineering guidance does not override source/ADRs;
8. hardware claims identify source/VM/physical evidence scope;
9. developer-only behavior is not described as release behavior;
10. trust/permission/capability language matches implementation;
11. destructive operations remain fail-closed;
12. no document implies GitHub-hosted execution is implicitly authorized;
13. dated reviews remain historical;
14. `HANDOVER.md` is sufficient to resume without chat history.

---

## 9. Navigation

- **New contributor/agent:** `AGENTS.md` → `README.md` → this file → architecture/ADRs → `docs/engineering/ENGINEERING_FOUNDATIONS.md` → product requirements → active plan → `HANDOVER.md`.
- **OS/platform implementation:** also read `docs/agents/GREIA_AGENT_OPERATIONS.md` and relevant testing/review docs.
- **UI work:** read ADR 0018, `src/greia_platform/ui_core.py`, the relevant renderer implementation, and the engineering foundations.
- **Activity implementation:** read the relevant product requirement, Activity skill, and current runtime/API source owners.
- **Physical/VM evidence:** start with `HANDOVER.md`, then the exact applicable `docs/testing/*` protocol.
- **Why was architecture chosen?** read the accepted ADR and relevant dated review/evidence.
- **What should the child experience do?** read the product requirement first, then source/implementation docs.

GitHub is the persistent project source of truth. Chat transcripts are context, not canonical documentation.
