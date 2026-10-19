# Voice corpus replacement tool — preparation evidence

**Date:** 2026-10-19. **Source base:** `b750e714eb1c6373d8fdcfa5bb4899e4b9a9e2a3`.
**Scope:** SOURCE + bounded AUTHORING smoke. Full corpus replacement UNEXECUTED.

## Implemented

`tools/regenerate_voice_corpus.py` is a thin command entry point over focused
inventory, SQLite replacement journal, derived-catalogue and serial-runner
modules. It uses the existing VoiceEngine and forces the selected VoxStage
provider with the six v0.2 references. Commands are `plan`, `resolve`, `run`,
`status`, `retry`, `restore`; the operator work order is
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`.

Tone/mood delivery is now a semantic `VoiceRequest.delivery_prompt` field,
supported by CLI, batch and warm service. Six editable defaults apply in the
VoxStage provider when omitted. The corpus plan snapshots explicit prompts;
provider provenance records the effective language/delivery direction. Explicit
unsupported prompts are rejected by Chatterbox/native. Saved masters remain
unchanged. The implementation adds no child-runtime speech generation.

The runner retains originals, new candidates, failed takes and a recoverable
audio/receipt/metadata transaction journal outside Git. It refuses source drift,
never auto-retries uncertain external synthesis, reports progress/heartbeats,
and leaves new receipts/shared rows human-review pending. Full restoration is
ordered newest first and refuses to erase later edits.

## Executed evidence

- **52 focused tests PASS:** `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tools:.
  python3 -m unittest discover -s tests -p 'test_greia_vo*.py' -v`.
  Coverage includes prompt transport/defaults/unsupported providers, replacement
  pairs, complete staged-candidate reuse, uncertain-job barriers, ASR-warning
  retention, missing receipts, changed destinations/references, metadata-only
  resolution, scope/letter exceptions, checksum refresh, shared metadata,
  partial transactions, ordered restore and protection of later edits.
- **Real read-only corpus planning/status:** 5,308 files inspected; 4,543 READY,
  167 BLOCKED_METADATA and 598 PRESERVED. The latter comprises 441 isolated
  letter/syllable files, 150 historical shared files, six canonical references
  and the boot chime. All READY requests have explicit prompts. The initial
  generic source census's 398 legacy Encyclopedia caption advisories remain
  recorded, while the full narration ledger resolves the actual scripts.
- **One real engine/provider smoke:** Lilli, English, custom unicorn delivery,
  OGG output, verification explicitly off. VoxStage job
  `20261019-100927-df5c3cf4` completed. Its persisted request segment delivery and
  resulting recording `spec.direction` both contain the exact requested
  language/performance prompt. Receipt identifies `voxstage-voxcpm2`,
  `greia.lilli.v2`, selected reference and `human_review=PENDING`. No claim about
  audible emotion, pronunciation or acceptance is made. The worker was unloaded
  afterward; no runtime corpus audio was replaced by this smoke.
- **First aggregate gate:** `make -k verify` executed 5,463 tests with 1 failure,
  4 errors, 8 skips. These are the same inherited build-profile/ARM64, executable
  CLI mode, macOS `lsblk` installer and MBR-message cases reproduced in the
  preceding provider migration review. Project validation also fails at the
  inherited ARM64 builder assumption. Shell/footprint steps executed.
- **Final aggregate gate on completed code:** 5,468 tests, 1 failure, 4 errors,
  8 skips (214.638 seconds). The five failing identities are unchanged from the
  first gate; project validation remains blocked by the ARM64 builder assumption.
  Shell and footprint steps ran. The aggregate is NOT GREEN. Exact output is
  external `make-verify-final.log`.

External preparation evidence:

```text
/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/
  plan.json, state.sqlite3, blocked.csv, overrides.template.json
/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-inventory-v3/
  voice-tests.log, make-verify.log, make-verify-final.log
  delivery-smoke.ogg, delivery-smoke.ogg.receipt.json, delivery-smoke.log
```

## Continuation limits

The 167 unresolved legacy files require exact recovered scripts/identities;
they are not silently skipped or guessed. `resolve` can fill their metadata
without regenerating completed work. No full production run, human listening,
release-image validation, Simulator playback or physical-speaker acceptance was
performed. No remediation/lifecycle phase is closed. Unrelated video work is
preserved. Canonical skills and ignored installed copies were refreshed.
