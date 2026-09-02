# Greia Public Documentation Router Reconciliation — 2026-09-02

**Status:** DOCUMENTATION-ONLY CLEANUP  
**Evidence class:** SOURCE DOCUMENTATION REVIEW  
**Runtime claim:** none  
**Physical claim:** none

## 1. Why this pass was needed

The first public-repository deep dive correctly identified stale living documentation, but several queued findings had already been fixed by later commits while `HANDOVER.md` still described them as pending.

That created a second-order drift problem: the cleanup checklist itself was no longer an accurate continuation contract.

This pass therefore reconciled the **living routers** against current repository state instead of repeating already-completed work.

## 2. Findings

### 2.1 Activity inventory drift

`HANDOVER.md` still stated a 34-Activity inventory in one section while the same file later described the two newly added toddler Activities and current audits over 36 Activities.

Current living state is 36 built-in Activities.

### 2.2 Documentation-map work was already complete

The deep-dive review queued these changes for `docs/DOCUMENTATION.md`:

- ADR 0034;
- child-text owner;
- launcher spoken-label owner;
- system-control owners;
- Parent system-control exposure;
- explicit historical-vs-current procedure rules.

Current `docs/DOCUMENTATION.md` already contains those updates. They are no longer pending work.

### 2.3 OS router ADR path was already repaired

The deep-dive review recorded a broken ADR 0013 filename in `skills/greia-os-work/SKILL.md`.

The living router now correctly references:

```text
docs/adr/0013-declarative-image-profiles-and-composable-build-artifacts.md
```

That item is closed.

### 2.4 Agent operations manual was still stale

`docs/agents/GREIA_AGENT_OPERATIONS.md` remained an August-era long-form manual. Material drift included:

- branch guidance phrased as “branch named by handover” rather than repository-wide `main`-by-default policy;
- old R7 Linux-evidence routing presented more directly than the current handover-selected exact-candidate procedure;
- duplicated current-state and remote-control details better owned by `HANDOVER.md`, `docs/testing/*`, source and narrower skills.

The manual was replaced with a compact living operating router that preserves:

- mandatory read order;
- `main`/concurrent-work discipline;
- hosted-execution prohibition;
- SOURCE / AUTHORING+HUMAN / SIMULATOR / VM / PHYSICAL evidence separation;
- current R7 authority boundaries;
- Simulator non-drift rules;
- developer-remote security boundary;
- exact-candidate physical testing discipline;
- failure preservation;
- explicit local-agent instruction requirements;
- source verification defaults;
- end-of-turn handoff expectations.

Commit:

```text
17ab93218c24029a911c64a566a7fcf912eb4bbb
Docs: compact Greia agent operations into current router
```

## 3. Handover corrections

`HANDOVER.md` was reconciled in two documentation-only commits:

```text
8c4ddec0d4cf5d16613f40a8daad35758de56088
Docs: reconcile current R7 and public-source handover

f67f6454ed4778b408ba2a9204ccf7cd0449e790
Docs: mark agent-operations reconciliation complete
```

The living handover now:

- records 36 built-in Activities;
- records the post-physical system-control corrections as SOURCE-only, not PASS evidence;
- points to the exact-candidate R7 gate;
- keeps R7.4 blocked until the required physical closure;
- removes already-completed documentation-map/router items from the pending list;
- identifies the deterministic documentation path/link audit as the next bounded public-source cleanup item.

## 4. What was deliberately not changed

This pass did **not**:

- change runtime/platform source;
- change Activity source/assets;
- execute or query GitHub Actions;
- claim new source test results;
- claim new Simulator evidence;
- claim new Acer/physical evidence;
- rewrite the historical deep-dive review to make its original findings disappear.

The earlier review remains accurate evidence of what was stale at its review point. The living documents, not the historical review, were corrected.

## 5. Next documentation/public-source step

The next bounded implementation should be the provider-free living-document path/link audit described by `docs/DOCUMENTATION.md` and the public-repository deep dive.

Design constraints:

- deterministic and local;
- no hosted service/provider dependency;
- validate only repository navigation contracts that are intended to resolve;
- avoid a fragile full-Markdown-parser dependency;
- distinguish real repository-relative paths from examples, globs and conceptual placeholders;
- prioritize living entry points/routers before historical evidence documents;
- produce precise file/line/reference failures;
- use behavior tests, not source-string assertions.

Because that next step adds executable tooling/tests, it is an implementation tranche and must receive the normal active-plan/HANDOVER updates and real local verification before being called complete.

## 6. Verdict

**Living documentation/router reconciliation: COMPLETE for this tranche.**

**Runtime/R7 evidence state: unchanged.**

**Next public-source cleanup:** deterministic living-document path/link audit, then licensing/provenance/security/community-file review.
