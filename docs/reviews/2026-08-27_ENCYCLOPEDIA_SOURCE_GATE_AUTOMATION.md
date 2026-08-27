# Greia Encyclopedia v0.1 — deterministic source-gate automation review

**Date:** 2026-08-27  
**Workstream:** `org.greia.enciclopedia`  
**Status:** source helper authored; local execution pending  
**Evidence boundary:** SOURCE REVIEW ONLY — no test/Simulator/hardware PASS is claimed

## Purpose

The canonical closure authority remains:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

That runbook deliberately contains explicit shell commands and manual Simulator review. The deterministic pre-Simulator half had become long enough that an operator could make bookkeeping mistakes while still following the intended policy. `tools/encyclopedia_v01_source_gate.py` now wraps that deterministic portion without changing the acceptance semantics.

## What the helper owns

In one fail-closed invocation it:

1. requires `main`;
2. refuses unexpected dirty source while allowing the voice ledger, recorder staging and prior encyclopedia evidence state;
3. creates a timestamped project-local evidence directory;
4. runs `encyclopedia/sync_voice_requests.py`;
5. runs `sync_voice_requests.py --check`;
6. independently parses the ledger and requires exactly 378 rows while recording real status counts;
7. runs the focused provider-free Encyclopedia/project contracts;
8. runs `make verify`;
9. runs `integrate_voice_assets.py --check` and interprets its documented 0=in-sync, 1=deterministic drift, other=failure contract;
10. if and only if accepted-audio drift exists, runs the integrator, rechecks it and reruns the Encyclopedia-specific tests;
11. runs `git diff --check`;
12. records final worktree state and `source-gate-summary.json`;
13. stops explicitly with Simulator acceptance still pending.

On the first real failure it records `FIRST_FAILURE.txt`, preserves the current worktree/evidence and exits non-zero. It does not fix-and-rerun.

## What it deliberately does not own

It does not:

- generate narration;
- call Chatterbox, native TTS, Whisper, LLMs or network providers;
- set recorder rows to `RECORDED_UNREVIEWED` or `OWNER_ACCEPTED`;
- overwrite an existing recording take;
- launch or control the Greia Simulator;
- perform the 43-page visual/signature-interaction review;
- decide pre-reader usability;
- claim physical Acer/Pi evidence;
- repair source;
- commit or push;
- use GitHub-hosted Actions.

The Simulator and human-review portions remain intentionally manual because visual discoverability, child-sized targets, no-reading behavior, animation quality and listening acceptance are semantic/human evidence rather than deterministic source checks.

## Testability correction made during source review

The first test version imported the helper as `tools.encyclopedia_v01_source_gate`. `tools/` is an executable-tool directory rather than an explicit Python package, so the test was changed to load the exact tool file through `importlib.util.spec_from_file_location`. This removes reliance on namespace-package behavior and tests the artifact the operator will actually execute.

Provider-free regression coverage currently includes:

- plain/untracked/rename Git porcelain path parsing;
- allowed initial recorder/evidence dirt;
- rejection of runtime/unrelated source dirt;
- explicit accepted-audio integration exit semantics;
- malformed status rows failing closed.

Those tests are authored but **not executed in this GitHub-only environment**.

## Local execution order

Before trusting the helper, run its focused regression first:

```bash
python3 -m unittest tests.test_encyclopedia_v01_source_gate -v
```

If that passes, inspect the non-mutating plan:

```bash
python3 tools/encyclopedia_v01_source_gate.py --plan-only
```

Then run the source gate exactly once:

```bash
python3 tools/encyclopedia_v01_source_gate.py
```

Stop on its first real failure. Do not repair inside that evidence run.

A successful helper run permits only:

```text
SOURCE-VERIFIED / SIMULATOR-UNVERIFIED
```

Then continue with the Simulator sections of the canonical consolidated-acceptance runbook.

## Relationship to the Voice Production Engine

The concurrently added `encyclopedia/export_voice_batch.py` is compatible with this closure architecture but remains a separate authoring workflow. The source gate validates its provider-neutral mapping through `tests/test_encyclopedia_authoring_tools.py`; it does **not** execute the Voice Production Engine or generate clips.

The ledger remains the encyclopedia coordination authority and the owner listening gate remains the only authority that promotes a recording to `OWNER_ACCEPTED`.

## Current next step

Execute the three local commands above on the owner-controlled checkout. If green, proceed immediately to the real 1024×600 Simulator traversal/no-reading/input-parity/responsive pass in `docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md`.
