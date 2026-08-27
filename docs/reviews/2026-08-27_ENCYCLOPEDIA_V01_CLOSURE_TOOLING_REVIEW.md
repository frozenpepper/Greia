# Greia Encyclopedia v0.1 — Closure Tooling Review

**Date:** 2026-08-27  
**Scope:** deterministic pre-Simulator closure tooling only  
**Runtime Activity:** `activities/enciclopedia_greia/`  
**Evidence boundary:** source reviewed; local tests and Simulator not executed in this GitHub-only review

## 1. Purpose

After the 43-page v0.1 source freeze and post-build drift review, the next risk was no longer topic breadth. It was coordination drift between:

```text
research authority
→ voice ledger
→ Greia Voice Production Engine request
→ local review staging
→ human acceptance
→ runtime audio integration
→ source gate
→ Simulator acceptance
```

This review covers the source tooling added/hardened to make that path deterministic without creating another request authority or weakening Greia's existing evidence rules.

## 2. Ledger → Voice Production Engine adapter

Added:

```text
encyclopedia/export_voice_batch.py
```

The Markdown ledger remains the sole Encyclopedia recording/review authority. The adapter performs no synthesis and changes no status. It translates eligible ledger rows into the provider-neutral request schema consumed by `tools/greia_voice.py`.

Preserved request semantics:

```text
speaker
speech kind
locale
exact reviewed text
semantic cue ID
staging output path
```

Derived provider-independent fields are limited to verification mode and bounded attempt count.

### Safety boundaries

The exporter fails closed when:

- the staging path is absolute or escapes via `..`;
- output is not OGG;
- `FINAL_FILENAME` disagrees with `FINAL_PATH`;
- the path is outside `encyclopedia/pages/**/assets/audio/<locale>/`;
- locale and path disagree;
- an unsupported semantic speech kind/speaker is requested;
- Dani is mislabeled as cloned character dialogue;
- a `REQUESTED` output already exists;
- a sibling Voice Engine receipt already exists even if the OGG was deleted.

The last rule is deliberate: deleting only a review OGG must not make earlier generation evidence disappear and permit silent overwrite. The operator must inspect the take/receipt and reconcile recorder status first.

`--allow-existing` is an explicit operator escape hatch for deterministic re-export only. It does not confer acceptance and the Voice Engine still writes only review assets.

## 3. Voice Production Engine boundary

Current provider implementation lives under:

```text
tools/greia_voice.py
tools/greia_voice_core/
```

The Encyclopedia adapter intentionally does not import provider/model classes. It stops at the stable JSONL request seam.

Actual batch generation remains gated by the Voice Production Engine's separate owner-controlled local provider acceptance. Until that passes, the established direct recording workflow remains valid.

Human listening remains authoritative. Whisper verification cannot set `OWNER_ACCEPTED`.

## 4. Deterministic source-gate helper review

Concurrent work added:

```text
tools/encyclopedia_v01_source_gate.py
tests/test_encyclopedia_v01_source_gate.py
```

The helper automates only the non-interactive pre-Simulator portion of:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

Its intended sequence is:

1. branch/worktree preflight;
2. voice-ledger synchronization;
3. sync check + independent 378-row validation;
4. focused provider-free contracts;
5. `make verify`;
6. OWNER_ACCEPTED integration check;
7. integrate only if deterministic drift exists;
8. rerun focused Encyclopedia contracts after audio-resource changes;
9. `git diff --check`;
10. strict worktree postflight;
11. evidence summary and stop with Simulator still pending.

It never generates speech, changes recorder status, repairs source, launches Simulator, commits/pushes or uses hosted CI.

## 5. Postflight gap found and repaired

The first helper version recorded final `git status` but could still print `SOURCE GATE PASS` if a test/tool unexpectedly modified unrelated source.

That was a real fail-closed defect.

The helper now classifies allowed final mutations explicitly.

Always permitted workflow state:

```text
encyclopedia/VOICE_RECORDING_REQUESTS.md
encyclopedia/pages/**/assets/audio/**     # local recorder staging
tmp/encyclopedia-v01-acceptance/**        # evidence
```

Permitted only when OWNER_ACCEPTED integration actually ran:

```text
activities/enciclopedia_greia/assets/audio/**
activities/enciclopedia_greia/locales/it.json
activities/enciclopedia_greia/locales/en.json
```

Anything else causes a `worktree-postflight` failure rather than PASS.

Focused tests cover both the allowed and rejected cases.

## 6. Local requested-state guard

Added:

```text
tests/test_encyclopedia_voice_batch_state.py
```

This contract runs the synchronized ledger through the exporter's default overwrite protection. Therefore a generated review take that remains incorrectly marked `REQUESTED` becomes a source-gate failure before Simulator work begins.

It also unit-tests orphaned receipt protection and the explicit `reject_existing=False` translation escape hatch.

## 7. Documentation/handover reconciliation

The previous root `HANDOVER.md` had grown into a large chronology despite declaring itself a current continuation contract. It was preserved verbatim at:

```text
docs/handovers/GREIA_ROOT_HANDOVER_ARCHIVE_2026-08-27.md
```

The root handover is now short and current. It records:

- R7 remains the primary blocking platform phase;
- Encyclopedia is a parallel 43-page Activity closure lane;
- the exact post-build review and consolidated acceptance authority;
- the Voice Production Engine remains authoring-only and provider-acceptance-pending;
- `tools/greia_voice_core/` is the actual core package location;
- no source/Simulator/device PASS is inferred from GitHub source review.

The Encyclopedia `README.md` and `HANDOVER.md` document the ledger adapter, staging-vs-runtime audio distinction and acceptance boundaries.

## 8. Evidence status

Nothing in this tooling review changes the evidence label by itself.

Current truthful state remains:

```text
SOURCE-REVIEWED / TESTS-UNEXECUTED / SIMULATOR-UNVERIFIED
```

The checked-in ledger remains the old 176-row snapshot until the local synchronizer actually executes and proves the 378-row result.

No physical Acer/Pi result is claimed for the Encyclopedia.

## 9. Next exact execution

On the owner-controlled current checkout:

```bash
python3 tools/encyclopedia_v01_source_gate.py --plan-only
python3 tools/encyclopedia_v01_source_gate.py
```

The handwritten consolidated runbook remains authoritative:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

If the source helper fails, preserve its project-local evidence and return the first real failure. Do not repair during the acceptance attempt.

Only after a genuine source-gate PASS may the label advance to:

```text
SOURCE-VERIFIED / SIMULATOR-UNVERIFIED
```

The full 43-page Simulator reachability/signature-interaction/input-parity/no-reading/responsive pass remains mandatory afterward.

Voice generation can proceed independently only after the Voice Production Engine's separate local provider acceptance, or through the previously accepted direct production workflow. In both cases, only human-reviewed `OWNER_ACCEPTED` audio may enter the runtime package.

## 10. Platform-plan boundary

This is parallel Activity/authoring work. It does not advance or close R7. The primary platform continuation remains:

```text
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
```
