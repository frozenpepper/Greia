# Voice documentation consistency review — 2026-10-22

**Scope:** authoring usage and derived documentation; no implementation change.
**Primary reference:** [VoiceEngine README](../../tools/greia_voice_core/README.md).

## Source checked

`greia_voice.py`, `models.py`, `service.py`, `engine.py`, `verification.py`,
`asr_policy.py`, `review.py`/`review_policy.py`, `voxstage_provider.py`,
`voice_carrier.py`, `greia_voice_corpus/carriers.py`/`carrier_generation.py`/
`runner.py`/`store.py`, `finish_voice_priority.py`, and shared VoxStage lifecycle
CLI/README. The shared tool remains project-neutral; Greia owns its usage guide.

## Corrections

- Single, JSONL, Python and socket-service examples; exact fields/defaults,
  result/exit interpretation, model readiness and output receipts.
- Ordinary requests: auto verification, two total takes configurable 1–4,
  existing Dani/short eligibility exclusions, last-warning output retained.
- Scoped carrier corpus: raw intro ASR off; required delivered-target Base score
  >0.8 and signal gate, saved-source recovery, three cumulative fresh takes.
- Current short policy (1–3 words or 4 words/≤28 alphanumerics); no public
  configurable short-routing API or independent verification queue yet.
- Pinned cached Base and accent-insensitive defaults; strict overrides,
  source-preserving transcript comparison and historical verifier provenance.
- VoxStage stop preserves queued jobs, rather than draining them. Semantic
  Greia socket service and shared synthesis HTTP API are separate endpoints.
- Priority command templates, durable/pass-boundary progress, live journal
  counts, terminal statuses, uncertain provider jobs, restored original pairs,
  budget carry-forward and crash continuation without duplicate synthesis.
- Original accepted shared-library baseline is historical; current replacement
  acceptance is per cue. Library v0.2 and master registry v0.3 are different IDs.

## Executed documentation checks

39 command/example checks PASS: 15 real CLI help invocations, shell syntax,
Python syntax, JSON syntax and real request-mapping checks for documented JSONL.
All local Markdown links in the audited entry points resolved. No generation,
queue mutation, package installation or implementation tests were performed by
these checks. Focused Markdown diff checks are separate from active audio CSVs.

Detailed command/help outputs and SHA snapshots:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-voice-documentation-audit/`.
This is documentation proof; it does not certify new audio, full repository
verification or the proposed asynchronous implementation. The ongoing priority
producer/monitor was not interrupted.
