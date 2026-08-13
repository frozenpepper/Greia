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

`AGENTS.md` owns mandatory contributor/agent behavior and non-negotiable repository/product constraints, including required read/update duties, Git/GitHub persistence rules, hosted-execution restrictions, product contracts, engineering expectations, continuity, and evidence terminology.

A narrower document may strengthen but must not weaken `AGENTS.md`.

### 2.2 Product requirements — `docs/product/*`

Product requirement documents own explicitly accepted child-facing scope and UX requirements. They constrain design but do not override accepted ADRs, security boundaries, or source-owned API contracts.

Example: `docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md` owns the mandatory Phase-0 Writing/Painting product scope and acceptance intent.

### 2.3 Normative architecture — accepted ADRs

Accepted ADRs own architecture decisions. Important current examples include ADR 0012 (platform constitution), ADR 0013 (declarative image composition), ADR 0014 (identity/ARM/direct-graphics direction), and ADR 0018 (lightweight Screen/Overlay/Collection UI foundation).

A newer ADR supersedes an older one only where it explicitly says so. `docs/architecture/GREIA_ARCHITECTURE.md` is the living cross-cutting synthesis, not a second ADR system.

### 2.4 Repository engineering guidance — `docs/engineering/ENGINEERING_FOUNDATIONS.md`

This mandatory guide owns repository-wide implementation guidance for strong OOP structure, purposeful polymorphism, composition versus inheritance, dependency direction, explicit ownership/lifecycle, bounded-resource engineering, documentation and testability expectations.

It does **not** override accepted ADRs or exact source contracts.

### 2.5 Exact implemented contracts — source/runtime declarations

For exact currently implemented APIs, schemas, command vocabularies and limits, source/runtime declarations are authoritative.

| Fact | Canonical implementation owner |
|---|---|
| Activity manifest parser/validation | `src/greia_platform/activities.py` |
| Activity runtime/capability/permission/package policy | `runtime/child-runtime.toml` |
| Python Activity SDK helpers | `src/greia_platform/activity_api.py` |
| renderer-neutral UI semantics/navigation/resource primitives | `src/greia_platform/ui_core.py` |
| platform-wide Pygame UI import surface for new shared consumers | `src/greia_platform/pygame_ui.py` |
| existing Activity Pygame helper implementation/compatibility surface | `src/greia_platform/activity_ui.py` |
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

`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` owns active ordering, prerequisites, closure criteria, and append-only progress history while active.

Historical progress entries remain historical; current continuation/evidence belongs in `HANDOVER.md`.

### 2.7 Current branch/evidence state — `HANDOVER.md`

`HANDOVER.md` owns the current branch/PR, blocking phase, implemented state, actually executed tests, unproven work, hardware evidence boundaries, and exact next legitimate step.

Transient SHAs, test counts and blockers should normally live there rather than in durable architecture documents.

### 2.8 Exact test/operator procedures — `docs/testing/*`

Named test protocols own prerequisites, commands, stop conditions, evidence to preserve, and what a PASS does not prove. They may be stricter than general guidance but may not weaken repository or architecture safety rules.

### 2.9 Agent/developer manuals — `docs/agents/*` and `skills/*`

`docs/agents/GREIA_AGENT_OPERATIONS.md` is the operational entry point for project/build/test-hardware work. `skills/greia-activity-authoring/SKILL.md` is the living authoring guide for Activities.

These are derived manuals. They must track source/ADRs/product rules and never outrank them.

### 2.10 Reviews/evidence — `docs/reviews/*`

Reviews are dated analysis/evidence snapshots unless explicitly promoted into an ADR, product requirement, or active-plan decision. Do not silently rewrite historical evidence to match later reality.

---

## 3. Status vocabulary

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

Architecture examples communicate semantics; they are not automatically current APIs.

In particular:

- conceptual YAML manifests do not replace `activity.toml`;
- conceptual storage snippets do not replace the current Storage client;
- `.greiaactivity` / `.greiabackup` remain directions until their implementation phases close;
- Web SDK/runtime examples remain future-facing until implemented;
- capability classes remain semantic until measured/versioned;
- ADR 0018 terms are renderer-neutral; `pygame_ui.py` is the shared Pygame import surface and `activity_ui.py` remains the current compatibility implementation for existing first-party Activities.

Activity authors use the Activity skill plus the implementation owners above.

---

## 5. Freshness rules

Keep transient execution facts out of durable files such as README, AGENTS, accepted ADRs, product requirements, architecture synthesis, engineering foundations and this map.

Current state belongs in `HANDOVER.md`, active-plan progress, active test procedures, and dated evidence/review reports.

Do not rewrite historical evidence/progress to make history cleaner; append corrections or add a superseding dated review.

---

## 6. Required update triggers

| Change | Required documentation update |
|---|---|
| repository workflow / hardware operation | `docs/agents/GREIA_AGENT_OPERATIONS.md` |
| repository-wide OOP/dependency/performance/maintainability rules | engineering foundations; `AGENTS.md` when non-negotiable |
| Activity manifest/API/runtime/trust/assets/theme/UI/performance/deploy flow | Activity authoring skill |
| child-facing accepted product scope/acceptance | relevant `docs/product/*`; `AGENTS.md` when non-negotiable |
| architectural decision | ADR + architecture overview when cross-cutting |
| renderer-neutral UI architecture/semantics | ADR 0018 + `ui_core.py` + affected living manuals |
| renderer-specific shared Pygame implementation/import ownership | `pygame_ui.py` / `activity_ui.py` + affected living manuals |
| active ordering/closure criteria | active plan |
| current implementation/evidence/blocker | `HANDOVER.md` |
| test command/stop/evidence protocol | applicable `docs/testing/*` |

A source change that leaves a mandated living manual materially wrong is incompletely documented.

---

## 7. Avoid duplication

Link to the owner of a fact instead of copying transient details across files. Safety-critical rules may be intentionally duplicated, but duplicated safety language must remain semantically identical.

---

## 8. Review checklist

Check that paths exist, active plan references are current, durable docs avoid stale execution facts, implemented/future APIs are distinct, ADR 0018 semantics are not confused with Pygame helpers, engineering guidance does not override source/ADRs, hardware claims name evidence scope, developer-only behavior is not described as release behavior, destructive operations remain fail-closed, hosted execution is never implicitly authorized, dated reviews remain historical, and `HANDOVER.md` is sufficient to resume without chat history.

---

## 9. Navigation

- **New contributor/agent:** `AGENTS.md` → `README.md` → this file → architecture/ADRs → engineering foundations → product requirements → active plan → `HANDOVER.md`.
- **OS/platform implementation:** also read agent operations and relevant testing/review docs.
- **UI work:** ADR 0018 → `ui_core.py` → `pygame_ui.py` (or existing `activity_ui.py` compatibility consumer) → engineering foundations.
- **Activity implementation:** relevant product requirement → Activity skill → current runtime/API source owners.
- **Physical/VM evidence:** `HANDOVER.md` → exact applicable `docs/testing/*` protocol.

GitHub is the persistent project source of truth. Chat transcripts are context, not canonical documentation.
