# Greia Documentation Map and Authority Model

**Status:** repository-wide documentation contract  
**Last reviewed:** 2026-08-10  
**Audience:** contributors, coding agents, reviewers, test operators, Activity authors

---

## 1. Why this file exists

Greia has several kinds of documentation because the project has several kinds of truth: product principles, explicit child-facing product requirements, accepted architecture decisions, implemented APIs, active work sequencing, current branch state, test procedures, and historical evidence.

Those documents must not silently compete with one another.

This file defines **which document class owns which fact**, how conflicts are resolved, and what must be updated when implementation changes.

The goal is simple: a future contributor should be able to determine whether a statement is a durable rule, a product requirement, a selected design, a current implementation fact, an unproven candidate, or historical evidence without reconstructing that distinction from chat history.

---

## 2. Authority order

When two repository documents appear to disagree, classify the disagreement before editing anything.

### 2.1 Repository work rules

`AGENTS.md` owns repository-wide contributor/agent operating constraints, including:

- mandatory read/update duties;
- Git/GitHub persistence rules;
- paid/hosted execution restrictions;
- non-negotiable product contracts;
- continuity requirements;
- evidence terminology.

A narrower procedure must not weaken `AGENTS.md`.

### 2.2 Explicit product/UX requirements

Files under `docs/product/` own detailed child-facing product requirements that have been explicitly accepted but do not themselves define low-level architecture or implementation APIs.

Example:

```text
docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md
```

owns the required Phase-0 Writing/Painting scope, UX intent and product acceptance criteria.

A product requirement may constrain architecture/implementation choices, but it does not authorize bypassing an accepted ADR, security boundary or active blocking prerequisite. Exact implementation schemas remain source-owned.

### 2.3 Accepted architectural decisions

Accepted ADRs own normative architecture decisions.

Important examples include:

- ADR 0012 — platform architecture constitution;
- ADR 0013 — declarative image profiles/composable artifacts;
- ADR 0014 — Greia identity, ARM parity, direct-graphics direction;
- later accepted ADRs that narrow or supersede earlier decisions.

When accepted ADRs conflict, the later explicitly superseding decision wins for the scope it supersedes. Do not infer supersession merely from a newer date.

`docs/architecture/GREIA_ARCHITECTURE.md` is a living synthesis of these decisions. It is explanatory and cross-cutting; it is **not a second ADR system**.

### 2.4 Implemented contract truth

For exact currently implemented schemas, command vocabularies and APIs, **source/runtime declarations are authoritative**.

Examples:

| Fact | Canonical implementation owner |
|---|---|
| Activity manifest parser/validation | `src/greia_platform/activities.py` |
| Activity runtime allow/deny lists, capability/permission vocabulary, package byte ceiling | `runtime/child-runtime.toml` |
| Python Activity SDK helpers | `src/greia_platform/activity_api.py` |
| shared child Activity UI primitives | `src/greia_platform/activity_ui.py` |
| Activity storage client operations | `src/greia_platform/storage_client.py` |
| Activity event client/protocol | `src/greia_platform/event_client.py`, `src/greia_platform/event_protocol.py` |
| shared icon IDs/paths | `assets/catalog/core_icons_v1.toml` |
| theme palette/defaults | `runtime/theme-defaults.toml` |
| resolved theme object | `src/greia_platform/customization.py` |
| developer remote client commands | `tools/greia_remote.py` |
| privileged developer operations | `src/greia_platform/developer_control.py`, `developer_input.py` |
| image composition | `build/profiles/*.toml`, `build/package-sets/*.txt`, canonical builders |

Documentation may explain these contracts but must not invent a conflicting schema for convenience.

If an implemented contract intentionally changes, update its agent-facing documentation in the same tranche.

### 2.5 Active implementation plan

`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` owns:

- active implementation ordering;
- phase prerequisites;
- phase closure criteria;
- append-only progress history while the plan remains active.

The plan does **not** override accepted architecture or explicitly accepted product requirements.

Individual historical progress entries remain historical snapshots. For the current phase/evidence state, use `HANDOVER.md` and the latest progress entry rather than an early log entry.

### 2.6 Current branch and evidence state

`HANDOVER.md` owns the current continuation snapshot:

- active branch/PR;
- blocking phase;
- what is implemented now;
- which tests actually executed;
- what remains unexecuted/unproven;
- hardware/VM evidence boundaries;
- exact next legitimate step.

It is expected to change frequently.

Do **not** copy current test counts, branch SHAs, temporary blockers or one-off evidence states into README/architecture unless there is a durable reason. Those copies become stale quickly.

### 2.7 Test/operator procedures

Files under `docs/testing/` own exact procedures for a named test or operator workflow.

A test protocol may specify stricter stop conditions than general documentation. It may not weaken `AGENTS.md`, architecture safety rules, or installer/device protections.

Test protocols must distinguish:

- prerequisites;
- exact commands;
- expected classifications;
- stop conditions;
- evidence to preserve/return;
- what a PASS does **not** prove.

### 2.8 Agent-facing operational manuals

`docs/agents/GREIA_AGENT_OPERATIONS.md` is the concise operational entry point for agents working on the project and test hardware.

`skills/greia-activity-authoring/SKILL.md` is the canonical agent skill for Activity creation/modification.

These are **derived living manuals**. They must track the implemented contracts they summarize. They do not outrank source schemas or accepted ADRs.

### 2.9 Reviews and evidence

Files under `docs/reviews/` are dated analyses/evidence snapshots unless explicitly promoted by an ADR, product requirement or active-plan decision.

A review can explain why a decision was made or preserve negative evidence. It is not automatically the current architecture just because it is detailed.

---

## 3. Status vocabulary

Use the repository status words consistently.

- **CONSTITUTIONAL** — durable product/platform invariant.
- **SELECTED** — implementation/design selected by accepted decision.
- **PROVISIONAL** — current implementation used while evidence/architecture remains open.
- **SOURCE-CLOSED** — required source work for that scope is complete at the recorded boundary; hardware/runtime evidence may still remain.
- **UNPROVEN** — source/design exists but required runtime, VM or physical evidence has not been obtained.
- **DEFERRED** — intentionally outside the current phase.
- **HISTORICAL** — retained for provenance; not current instructions.
- **COMPLETE** — closure criteria for the explicitly named scope are satisfied.

Never use `PASS`, `accepted`, `complete`, or `supported` without naming the scope when ambiguity is possible.

Examples:

```text
source unit tests: PASS
Acer direct scanout: UNPROVEN
R6 source scope: SOURCE-CLOSED
production display backend: PROVISIONAL Xorg compatibility
Writing first source tranche: implemented / unexecuted
Web runtime: DEFERRED / unimplemented
```

---

## 4. Implemented versus conceptual examples

Architecture documents often show conceptual future APIs or package layouts. Those examples communicate semantics; they are not automatically copy-paste authoring specifications.

In particular:

- conceptual YAML manifests in architecture documents do not replace the implemented `activity.toml` parser;
- conceptual `storage.get()` examples do not replace the current Python `ActivityStorageClient.kv_get()` API;
- `.greiaactivity` and `.greiabackup` are architectural format directions until their dedicated implementation phases close;
- Web SDK examples remain future-facing until the Web runtime is implemented and documented;
- capability-class examples such as C0/C1/C2/C3 remain semantic classes until thresholds are measured/versioned;
- a product UX document may require behavior such as large controls or automatic saving without prescribing an unsupported platform API.

Activity authors must use `skills/greia-activity-authoring/SKILL.md` plus the implementation owners listed above.

---

## 5. Freshness rules

### Durable documents

These should contain stable contracts and avoid transient execution facts:

- `README.md`;
- `AGENTS.md`;
- accepted ADRs;
- `docs/product/*` requirement documents;
- `docs/architecture/GREIA_ARCHITECTURE.md`;
- this documentation map;
- the Activity authoring skill, except where it clearly labels an implemented snapshot.

### Frequently updated documents

These may contain exact current state:

- `HANDOVER.md`;
- active plan progress log;
- active test protocols;
- dated evidence/review reports.

### Historical documents

Do not silently rewrite dated evidence to match current reality. Add a correction/superseding note or a new review instead.

A product requirement can update its explicit implementation-status line while preserving the accepted requirement itself; dated decision reviews remain historical snapshots of the decision moment.

---

## 6. Required update triggers

When changing the following, update the corresponding docs in the same work tranche.

| Change | Required documentation update |
|---|---|
| repository workflow / hardware test operation | `docs/agents/GREIA_AGENT_OPERATIONS.md` |
| Activity manifest/API/runtime policy/trust/assets/theme/UI/performance/deploy flow | `skills/greia-activity-authoring/SKILL.md` |
| child-facing accepted product scope/acceptance | relevant `docs/product/*`, plus `AGENTS.md` when non-negotiable |
| architectural decision | new/updated ADR + architecture overview if cross-cutting |
| active work ordering/closure criteria | active plan |
| actual current implementation/evidence/blocker | `HANDOVER.md` |
| test command/stop/evidence protocol | relevant `docs/testing/*` |
| developer remote command vocabulary | operator docs + agent operations manual |
| reference hardware/resource requirement | `AGENTS.md`/ADR as appropriate + Activity skill if author-facing |

A source change that makes a mandated living manual materially wrong is incompletely documented.

---

## 7. Avoid documentation duplication

Prefer linking to the owner of a fact instead of copying it.

Good:

> Current executed verification and unproven hardware gates are recorded in `HANDOVER.md`.

Bad:

> Copying a test count into README, architecture, the active plan header, three testing guides and the PR body.

Some duplication is intentionally useful for safety-critical rules (for example the paid-hosted-execution prohibition or destructive installer boundary), but duplicated safety rules must remain semantically identical.

---

## 8. Documentation review checklist

When doing a documentation review, check at least:

1. links/paths point to real canonical files;
2. active plan references are current;
3. no durable doc carries a stale branch SHA/test count as current truth;
4. implemented and future APIs are visibly distinguished;
5. product requirements are separated from implementation detail but reflected in current state;
6. hardware claims identify source/VM/physical evidence scope;
7. developer-only behavior is not described as release behavior;
8. trust/permission/capability language matches implementation boundaries;
9. destructive operations remain fail-closed;
10. no document implies GitHub-hosted execution is authorized;
11. Activity examples match current parser/SDK or are clearly labelled conceptual;
12. dated reviews remain historical rather than being silently repurposed;
13. `HANDOVER.md` still lets a new agent resume without chat history.

---

## 9. Navigation

Start here according to task:

- **New contributor/agent:** `AGENTS.md` → `README.md` → this file → architecture/ADRs/product requirements → active plan → `HANDOVER.md`.
- **OS/platform implementation:** add `docs/agents/GREIA_AGENT_OPERATIONS.md` and phase-specific review/testing docs.
- **Activity implementation:** add the relevant `docs/product/*` requirement, `skills/greia-activity-authoring/SKILL.md`, and current runtime/API source owners.
- **Physical/VM evidence:** start with `HANDOVER.md`, then use the exact applicable `docs/testing/*` protocol.
- **Why was this architecture chosen?** read the accepted ADR and relevant dated review/evidence.
- **What should the child experience do?** read the explicit product requirement first, then implementation/source docs.

GitHub is the persistent project source of truth. Chat transcripts are context, not canonical documentation.
