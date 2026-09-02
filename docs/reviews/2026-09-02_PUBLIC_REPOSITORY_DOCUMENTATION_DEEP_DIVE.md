# Greia Public-Repository Documentation Deep Dive — 2026-09-02

**Status:** first documentation/release-readiness cleanup tranche  
**Evidence class:** repository/source documentation review; no new runtime or physical claim  
**Reviewed main:** `a893654cfc95d816dbdbdfc0f3060b8c0fc6daa8`  
**Release authority:** `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md`

## 1. Purpose

Greia is approaching the point where repository presentation itself becomes part of release quality. This review examines whether a new contributor can distinguish stable architecture, current implementation state, current evidence, historical evidence, operator procedures and future release work without reconstructing project history from dozens of dated files.

The goal is **not** to delete useful engineering history or flatten Greia into a tiny README. The goal is to make each document class do one job and make stale documents stop presenting themselves as current authority.

## 2. Executive result

The repository has a stronger documentation foundation than most projects at this stage: there is an explicit authority model, accepted ADRs, product requirements, an active implementation plan, exact operator protocols and a serious public-release readiness gate.

The main problem is **documentation state accumulation**. Several living entry points have absorbed historical evidence or were never retired after later gates superseded them. As a result, a contributor can encounter multiple incompatible definitions of “current”.

Highest-priority findings:

1. `HANDOVER.md` had grown into an archive and still contained obsolete exact-candidate instructions (`1edb22ce`) after later runtime candidates existed.
2. `docs/testing/LOCAL_AGENT_START_HERE.md` still called an August 18 omnibus procedure the current operator entry point and advertised a 679-test evidence boundary, despite current history being far beyond that state.
3. root `LOCAL_AGENT_RESULT.md` was a 63 KB historical result accumulator, not a public-project entry point.
4. voice/setup documentation contradicted accepted repository assets: `assets/audio/characters/shared/v0.2/` contains the owner-accepted 180 shared reactions plus 12 introductions, while several living docs still called production/listening pending.
5. `docs/DOCUMENTATION.md` is stale relative to ADR 0034 and newer implemented source owners such as child text, launcher spoken labels and system controls.
6. `skills/greia-os-work/SKILL.md` contains a broken ADR 0013 filename (`0013-image-composition-and-package-architecture.md`); the real file is `0013-declarative-image-profiles-and-composable-build-artifacts.md`.
7. `README.md` was last reviewed on 2026-08-19 and had become an engineering overview rather than the smallest useful public/contributor front door.
8. the public-source legal/community surface remains intentionally incomplete: the release gate still requires the licensing/provenance audit and standard public files (`LICENSE`, notices, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, privacy/release-history surfaces as appropriate).

## 3. Authority model — keep it

The existing hierarchy remains sound:

```text
AGENTS.md
  repository-wide contributor/non-negotiable rules

docs/product/*
  accepted child/parent/ecosystem behavior

docs/adr/*
  normative architecture

source/runtime declarations
  exact implemented APIs/schemas/limits

docs/engineering/*
  implementation guidance

active plan
  sequencing + append-only progress history

HANDOVER.md
  short current continuation/evidence boundary

docs/testing/*
  exact named procedures

docs/reviews/*
  dated analysis/evidence/history

skills/* and docs/agents/*
  derived practical contributor/agent guidance
```

Cleanup should reinforce this model rather than invent another documentation layer.

## 4. Current-source/evidence distinction that must be preserved

At the start of this review, branch head was `a893654c...`. The latest runtime-affecting commit before that docs-only Home report is `138116186b7731264aedf92a898558984432d4e9` (live Greia volume controls through the Parent API), with several system-control/hardware-session commits between the physically tested Home candidate and current source.

The Home regression was physically proven at:

```text
57626d3f65a8bf3ae074eee15b00ee32ba3277bd
```

That proof remains valid for the Home lane, but it must not be silently promoted to full physical certification of later system-control source. Current documentation must say this explicitly.

## 5. First cleanup tranche

This tranche intentionally focuses on high-confidence documentation-only corrections:

- replace `HANDOVER.md` with a short current continuation contract and move historical detail back to dated reviews/active-plan history;
- replace `docs/testing/LOCAL_AGENT_START_HERE.md` with a living router that follows `HANDOVER.md` rather than freezing one old omnibus test session;
- remove root `LOCAL_AGENT_RESULT.md`; Git history preserves it and future retained evidence summaries belong in dated reviews/active plan/HANDOVER, while bulky evidence stays outside Git;
- simplify/freshen `README.md` as the repository/public front door;
- refresh `SETUP.md` and voice-design status to reflect the actual owner-accepted `shared/v0.2` asset set while keeping runtime-resolver completion separate;
- preserve all runtime/source/asset bytes unchanged.

## 6. Findings intentionally queued for the next documentation tranche

### 6.1 Refresh `docs/DOCUMENTATION.md`

Required changes:

- add ADR 0034 to the accepted cross-cutting ADR list;
- add exact owner rows for `src/greia_platform/child_text.py`, `src/greia_launcher/spoken_labels.py`, `src/greia_platform/system_controls.py` / `system_controls_legacy_x.py`, and relevant Parent API exposure;
- state explicitly that dated runbooks/results are historical unless the current handover or active plan names them;
- review the source-owner matrix for files renamed since 2026-08-24.

This should be done as a matrix audit, not a blind date bump.

### 6.2 Repair derived routers and manuals

At minimum:

- fix the broken ADR 0013 path in `skills/greia-os-work/SKILL.md`;
- audit every task-router path against the current tree;
- audit `docs/agents/GREIA_AGENT_OPERATIONS.md` for old “current” evidence claims and obsolete operator entry points;
- mark completed one-off agent runbooks clearly as historical/completed instead of leaving them visually equivalent to living manuals.

### 6.3 Public source legal/community gate

Do **not** solve this by dropping generic templates into the repository and calling the gate complete.

Before public visibility, complete the licensing/provenance work in `docs/governance/LICENSING_AND_TRADEMARK.md` and `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md`, then add the correct root/public files with reviewed scope. At minimum the release gate currently expects discoverable license/notices, security reporting, contribution guidance, code of conduct, privacy information and release history/known-status surfaces as appropriate.

### 6.4 Historical-document classification

The repository contains many valuable dated reviews, runbooks and plans. They should remain, but readers need a reliable signal:

```text
LIVING        may state current truth
ACTIVE        currently controls sequencing/procedure
HISTORICAL    evidence/context only; never current state by itself
SUPERSEDED    preserved for history; replacement named
```

A later mechanical audit should add/normalize these labels where ambiguity is material. Do not rewrite old evidence text merely to make history look cleaner.

### 6.5 Link/path validator

Before source publication, add a provider-free documentation path/link audit that checks repository-relative Markdown references and known canonical source-owner paths. Broken task-router paths are exactly the kind of failure this should catch.

Avoid a fragile full Markdown parser if unnecessary; the validator should be deterministic, bounded and scoped to repository-relative links/declared path blocks that Greia treats as navigation contracts.

## 7. Release-readiness priorities after documentation cleanup

Documentation cleanup improves Threshold A public-source readiness, but it does not make Greia family-release ready.

Major release gates remain, including:

- R7 display/session/input closure and exact-current physical evidence;
- safe production Greia Parents pairing/encrypted transport;
- rollback-safe Greia OS update activation;
- portable backup/restore/recovery;
- final Activity/content release inventory and human acceptance;
- hardware certification and resource acceptance;
- security/threat-model/history-secret review;
- licensing/provenance/trademark/privacy completion;
- public parent/user documentation and ordinary-parent/child usability acceptance.

See `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md`; do not duplicate that checklist into this review.

## 8. Documentation rule going forward

A useful maintenance rule is:

> **Current-state documents should contain current state; historical evidence should be linked, not recopied.**

Specifically:

- `HANDOVER.md` should normally stay short enough to read in one sitting;
- the active plan may remain long because its progress ledger is intentionally append-only;
- dated reviews may be detailed;
- testing routers should select the current named gate, not embed old test counts indefinitely;
- README/SETUP should never carry exact PASS counts or candidate SHAs except where they are part of an immutable release record;
- source/runtime declarations remain the owner of exact implemented contracts.

## 9. Verdict

**Documentation architecture: GOOD FOUNDATION / NEEDS CONSOLIDATION.**

The problem is not lack of documentation. It is too many documents still presenting historical state as live state. The correct release-preparation direction is to simplify the public and current entry points while retaining the detailed engineering record underneath them.
