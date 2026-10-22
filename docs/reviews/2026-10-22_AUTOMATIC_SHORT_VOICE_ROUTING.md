# Automatic short-voice routing — 2026-10-22

## Implemented boundary

Normal VoiceEngine VoxStage speech defaults to automatic wrapping at ≤4 Unicode
words, optional additional AND alphanumeric limit, including Dani/single words.
CLI, JSONL, Python and localhost service share selection. Native pedagogical
speech is excluded. Chatterbox remains ordinary in auto mode; forced on rejects
unsupported providers. Per-request auto/off/on and thresholds are documented in
[the usage README](../../tools/greia_voice_core/README.md).

Policy, bounded lifecycle, safe delivery preparation and final screening have
separate collaborators. Existing providers, exact masters, extractor v6 and
AudioPipeline are reused. Corpus explicit raw requests disable wrapping; its
frozen selection/cumulative attempt budgets are not expanded. No shared queue
scheduler or new synthesis stack is introduced.

## Correctness and failure boundaries

- Three total automatic short takes by default; optional lower limit honored.
- Preflight alignment readiness before synthesis, even if final quality disabled.
- Disposable intro is not scored. Target-only alignment/PCM checks remain active.
- Delivered target: Base score >0.8, same normalized word count, no signal flags.
- Only cut/quality/generated-audio failures spend another take. Provider/ASR/IO
  faults retain evidence and stop; no speculative external job retry.
- Quality exhaustion returns no output path; prior destination is preserved.
- Final-score off still uses ASR for safe extraction. Off wrapping plus off
  verification bypasses ASR. No automatic human acceptance.
- Delivery advances only within the already measured silent run, retaining 100 ms;
  original midpoint extraction is unchanged and separately retained/hashed.

## Executed evidence

110 focused tests PASS in prepared voice Python. Includes a 6-actor × 4-language
matrix through real VoiceEngine/cutter/FFmpeg with synthetic provider/ASR fixtures,
real localhost socket transport, JSON/CLI forwarding, overrides/exclusions,
three-take exhaustion preserving previous bytes, infrastructure failures,
actual corpus/engine no-double-wrap and exact PCM delivery suffix preservation.

24 previously generated real sources were replayed through the automatic engine
with an explicitly labeled fixture provider, not new synthesis. Exact source
hashes/master provenance retained. Before delivery preparation, 10 published;
after, 15 published/9 rejected, with a success in each released language. Used 48
exact-byte cached Base observations and 24 new Base calls on final delivery PCM.
No new provider jobs or runtime installation occurred in this replay. This is
saved-audio/route proof, not fresh-generation or owner-listening approval.

Full make verify with /opt/anaconda3/bin/python3 and dummy SDL drivers during
development ran 5,672 tests: one failure, three errors, eight skips; NOT GREEN.
Failures: ARM64 target-builder profile, two macOS lsblk installer tests, MBR
exception-message expectation. Final focused tests were run after helper changes;
the full run does not certify later edits. Logs, manifests and replay artifacts:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-automatic-short-routing/`.

## Production continuity

Old priority PID 87089 stopped for delivery preparation adoption. Completed ask_Y
job 20261022-015655-3cf72c6f was retained with real provider provenance. New external
continuation reuses the same 667 priority paths, exact selected masters and
maximum historical counts. Previous 78 installs/167 kept are not discarded.
Continuation started as PID 17915 (exec session 64973), reusing 1,298 exact-byte
ASR cache entries; startup audit was progressing. Existing Luna monitor resumed.
Whale reconciliation is included here; no separate follow-up producer.
See HANDOVER/live journals; never launch a duplicate producer. The shared durable
asynchronous programme remains proposed, separately documented in its plan.
