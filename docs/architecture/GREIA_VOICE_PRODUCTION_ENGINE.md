# Greia Voice Production Engine

**Status:** canonical authoring-time subsystem; VoxStage/VoxCPM2 synthesis and local Parakeet-TDT verification defaults
**Reviewed:** 2026-10-23
**Runtime boundary:** no synthesis model, worker, reference master or authoring dependency ships to the child device.

## 1. Ownership and semantic boundary

All Activity, OS/shared-library and Encyclopedia prerecorded speech production
enters through `tools/greia_voice.py` or the same `VoiceEngine` core. “Voice Studio”
is this authoring workflow, not another content-facing synthesis API.

Callers supply speaker, speech kind, BCP-47 locale, exact text, cue ID and output.
They may supply a separate `delivery_prompt` for acting tone/mood; it is never
concatenated into spoken text. VoxStage supports it; unsupported providers reject
an explicit prompt. The saved reference remains the speaker identity.
They never operate model imports, reference files, native voice names, trimming,
Whisper or FFmpeg directly. Provider choice is an operator configuration below
semantic content requests.

Speech kinds remain `character_dialogue`, `shared_character_utterance`,
`pedagogical_speech` and `dani_system_speech`. Shared production creates reviewed
static library assets; children resolve those assets rather than synthesize.
Pedagogical means the sound itself is the pronunciation truth being taught.

**Owner correction 2026-10-21:** permanent voice attributes (register/pitch,
timbre, vocal age/texture and characteristic identity) are master-design inputs.
Per-recording direction owns only the line's delivery/acting and locale cue.
The six default delivery entries now share warm, calm, clear reading with careful
natural pronunciation (owner direction2026-10-22);
callers must not prepend a fixed persona to every recording. V2 frozen requests
retain their original prompts as provenance. A new replacement plan is required
for selected new masters and corrected per-cue acting.

## 2. Composition and source owners

```text
semantic CLI / batch / warm service / repository producers
  -> greia_voice.build_engine
  -> composition.build_providers (one operator-selected character backend)
  -> VoiceEngine
       |-- VoiceRegistry: active v0.3 identity set and reviewed references
       |-- VoiceProvider
       |     |-- VoxStageProvider (default, all six characters)
       |     |     -> VoxStageClient -> shared loopback VoxStage worker
       |     |-- ChatterboxMLXProvider (explicit retained alternative)
       |     |-- MacOSNativeSpeechProvider (pedagogical, legacy system profiles)
       |     `-- UnsupportedNativeSpeechProvider (honest unavailable result)
       |-- SpeechVerifier / pinned local Parakeet-TDT v3 verifier
       |-- AudioPipeline: bounded WAV checks and WAV/OGG packaging
       `-- InterprocessGenerationLock: one Greia generation owner
```

Exact owners:

- `models.py`: typed requests, profiles, results and receipts.
- `registry.py`: active registry location and reference identity.
- `composition.py`: one default/alternative selection policy for all producers.
- `voxstage_provider.py`: semantic-to-VoxStage adaptation, voice import/reuse,
  result identity, full-mix selection and Greia generation provenance.
- `voxstage_client.py`: bounded loopback HTTP, job wait and artifact transfer.
- `providers.py`: retained Chatterbox and native adapters.
- `engine.py`: semantic routing, availability, bounded ASR retries, packaging,
  pending-review receipts and temporary-file cleanup.
- `review_policy.py`: owner-selected v4 comparison policy and thresholds shared by live and saved-evidence screening (ASR >0.8; tail/internal pause warnings ≥1.5s).
- `audio.py`: bounded WAV validation and 22,050 Hz mono WAV/OGG packaging.
  WAV is PCM16; OGG uses Vorbis quality 5 by default. An explicit
  `AudioPipeline(ogg_quality=0..10)` can select a different bounded quality
  for a corpus-specific package-footprint constraint without changing the
  frozen speech request or human-review state.
- `service.py`: localhost semantic service and client transport.
- `review.py`: bounded installed-audio signal screening and the existing
  `SpeechVerifier`, including offline/cached-weight-only ASR readiness.
- `greia_voice_corpus/review.py`: frozen-request/receipt consistency, external
  resumable review records, coverage and listening queue; journal opened read-only.
- `direction.py` / `character_delivery.json`: editable six-character performance
  defaults; VoxStage stores the effective prompt in generation parameters.
- `tools/greia_voice_corpus/`: inventory, serial runner, replacement/restore
  journal and derived catalogue updates for the owner-authorized corpus migration;
  `tools/regenerate_voice_corpus.py` is its thin command entry point.

These are authoring modules under `tools/greia_voice_core/`, not platform runtime
services. Content scripts do not acquire a second provider architecture.

## 3. Current canonical identities

### Versioned spoken-target replacement path (2026-10-23)

The owner-authorized unresolved-corpus continuation uses the existing
`NaturalCarrierPolicy` variation seam to retain semantic request text while
providing a separately recorded locale-spelled speech target to the normal
short-phrase extractor and packaged-audio verifier. Policy
`automatic-natural-context-parakeet-v4-spoken-target-v1` pins
`locale-number-tokens-v4-spoken-target-v1`; legacy and v3 plans keep their
original comparison identities. The spelling collaborator recognizes only
standalone digits in the existing 0–100 locale lexicon and explicit letter
example syntax, failing closed on codes, dates, signed values and decimals.
Target comparison preserves numeric sequence and word count and has a hard
letter-identity guard; the owner-approved C/K/CH glyph equivalence is confined
to the corresponding letter-example token. Exact human-review evidence for
saved cut installs remains separate from automatic Parakeet status.

`assets/audio/characters/canonical/v0.3/manifest.toml` is the active registry.
Dani, Momo and Tito use `greia.{dani,tito,momo}.v3`; Lilli, Leo and Flash retain
their `greia.{lilli,leo,flash}.v2` IDs and exact bytes. Every character has a
cloning reference. The complete selected WAV is copied unchanged as both source
master and canonical reference; it is not truncated, resampled or regenerated
during promotion.

`assets/source/audio/character-voice-masters/v0.3/provenance.json` records the
active source set and exact selection evidence. The v0.2 registry and its accepted
four-language comparison samples remain historical. No v0.3 multilingual cloned
line comparison is claimed as accepted. New generations still start with human
review pending; earlier accepted shipping recordings and their receipts remain
unchanged.

`VoiceRegistry` verifies the existing authoring reference hash before generation.
This preserves the selected speaker identity; it is not runtime anti-tampering,
asset signing or a restriction on users editing their installed files.

## 4. Routing and operator configuration

| Semantic request | Default |
|---|---|
| Any of six speakers + `character_dialogue` | VoxStage/VoxCPM2 with that speaker's active v0.3 registry reference |
| Any of six speakers + `shared_character_utterance` | same cloned-character provider |
| Dani + `dani_system_speech` | same provider, Dani's v0.3 master |
| `pedagogical` or `system` + `pedagogical_speech` | independent native/system pronunciation provider |

The Dani kind remains compatible; ordinary Dani `character_dialogue` is also
supported now that Dani has a cloned profile. Historical system-only profiles
still require their specific semantic route. A named character cannot impersonate
`pedagogical_speech`.

`GREIA_VOICE_CHARACTER_PROVIDER` defaults to `voxstage`; `chatterbox` selects the
retained alternative. `--character-provider` on `doctor`, `generate`, `batch` or
`serve` overrides the environment. Repository producers use the same composition
function, so its default applies to central shared-library production as well.
The warm server chooses once at startup; `request` does not change its backend.
If the selected provider is unavailable, the engine returns `UNAVAILABLE`. It
never silently substitutes Chatterbox, another character or native Dani speech.

## 5. Shared-worker VoxStage adapter

VoxStage is the existing shared local tool. It owns the serialized inference
worker, installed VoxCPM2/MLX model, immutable saved voice library and job records.
Greia uses standard-library HTTP and never imports or loads a second MLX model
for this default synthesis route. Pinned local Parakeet ASR can run in the Greia
verification process. `VoxStageProvider.close()` does not unload or shut down a
service used by other projects. The operator uses `voxstage unload` after
production to free model memory, or `voxstage stop` to finish the current recording and preserve queued jobs
for the next start. Do not stop a shared worker needed by another project.

Default origin: `http://127.0.0.1:8791`. `GREIA_VOXSTAGE_URL` accepts only a loopback
HTTP origin; proxies and redirects are not used. An optional `VOXSTAGE_API_KEY`
remains environment-only and is never written to a receipt. This is not a cloud
provider and makes no hosted GPU calls.

Before synthesis, the adapter reuses the registry's saved voice ID if its
reference and transcript match. On a fresh local workstation, it imports the
repository WAV and transcript under that ID. It never overwrites a conflicting
saved identity. Readiness probing performs no import or generation.

One semantic request becomes one one-take script in `reference` mode. The shared
tool splits longer text on natural boundaries. The adapter retrieves the full
`mix-take-01.wav`, preserving all chunks, rather than returning only the first
sentence. Settings are 10 steps, CFG 2, 300 tokens per chunk; this is a fixed
backend safety bound, not a word-count-derived acoustic-token heuristic.

The spoken text stays in its requested language. A concise native-language
instruction accompanies it; VoxCPM2 exposes no hard language selector. Identity,
accent, pronunciation and performance therefore remain listening predicates.
The adapter's language directions currently cover the four released Greia
languages (EN/IT/FR/ES); this mapping does not own the selectable locale registry.

POSTs are submitted once with a per-attempt idempotency key. Polls and downloads
are bounded. `GREIA_VOXSTAGE_TIMEOUT` controls the job wait (default 1,800 seconds,
allowed 1–7,200). A failed/interrupted job reports its ID; a timeout/connection
loss may leave the shared job running. Inspect that job before another submission;
never assume an uncertain response cancelled inference. Completed full-mix
identity and transfer hashes are checked before packaging.

## 6. Retained Chatterbox and native providers

Chatterbox remains the in-process Apple-Silicon alternative, selected explicitly.
It uses the active v0.3 references, including Dani, and retains warm model reuse,
transient MLX cleanup and edge-only silence trimming. Do not reintroduce short
word-count token caps or cut at internal pauses. Setup requirements remain in
`tools/greia_voice_requirements_mlx.txt`; its field guide is provider-specific.
Unload VoxStage before using this alternate multi-GB model on the same host.

`MacOSNativeSpeechProvider` remains the independent pedagogical provider with
bounded host voice/rate profiles in `native.py`. Native Dani profiles are retained
for historical compatibility, not default new character synthesis. Other hosts
report unavailable native routes until a provider implements them. Providers
are authoring-host adapters; no host command belongs in an Activity.

## 7. Verification, receipts and acceptance

The [usage README](../../tools/greia_voice_core/README.md) provides practical request,
CLI, result and recovery examples. New requests default to cached local multilingual
Parakeet-TDT v3 (`mlx-community/parakeet-tdt-0.6b-v3`, revision
`ed2b7e8c15f9aaa0b5772e2efb986255eaef7e15`) through the prepared voice Python.
Missing weights/dependencies are reported; no download or silent Whisper fallback
is performed. Whisper remains identifiable for historical receipts/replay and is
not used to reinterpret them. Ordinary requests default to verification `auto`,
three total takes (configurable 1–4), and accent-insensitive comparison. The
ordinary verifier retains its semantic eligibility rules; `verification=off` is
an explicit unverified opt-out. Verified outputs are checked after packaging.
Known quality WARNs can retry; exhausted or indeterminate results are not published
as accepted output, and infrastructure uncertainty stops for recovery. Human
listening is required after machine PASS.

One scoped exception is versioned for the owner-authorized native replacement
of the exact 52 unresolved v4 rows. `owner-2026-10-23-native-system-tts-missing-52`
forces the existing macOS native adapter ahead of the character provider only
for a one-call character request with a frozen `spoken_text`, `short_text_mode=off`
and `verification=off`. The adapter uses the installed locale voice and the
normal `AudioPipeline` packaging/validation path, while Parakeet is not probed
or run. Receipts identify the native voice, `verification=NOT_RUN`, and
`human_review=WAIVED_BY_OWNER`; none of these values is a machine or listening
PASS. This exact owner authorization does not change ordinary verification or
historical corpus plans.

Automatic short requests use `voice_carrier_search.extract` v7. Raw synthesis
verification is OFF; the disposable intro is never transcribed for alignment.
Bounded PCM quiet-run candidates are transcribed as independent target-only
suffixes with pinned Parakeet-TDT v3. New Parakeet verification and extraction
use `locale-number-tokens-v3-chck-orthographic` for the same target decision.
Exactly one must meet score >0.8, equal canonical unit count and an identical
numeric-token sequence. Exact locale number spellings/digits 0–100
compare equivalently via `number_comparison.py`; historical v6 receipts keep their
legacy comparison. The actual delivered target then passes shared
`TargetQualityChecker` with unchanged signal checks; changed/lossy PCM is checked
after packaging. `required` cutter mode is stricter canonical-token equality.
See the usage README for limits, overrides and retained evidence.

`ShortPhrasePolicy` selects fewer than five words by default for supported
VoxStage character providers, excluding pedagogical speech. It selects a safe
alternate intro if the complete target occurs in the standard intro.
`ShortPhrasePipeline` owns raw takes, extraction and at most three total provider
takes behind the same VoiceEngine entry point. Provider/ASR/IO uncertainty stops
for recovery rather than spending another take. `short_delivery.prepare_delivery`
preserves a v7 cut already 100 ms before the verified gap end.

The frozen corpus path remains explicitly v6 and is **stopped for rejection
diagnosis**. It must not inherit v7 by changing a historical plan in place.
A separately versioned recovery adapter must map extraction metadata and enforce
final word/numeric checks, saved-source provenance, installation transactions and
cumulative three-take budgets before resuming. `prepare_saved_candidate` is the
existing no-synthesis packaging seam; CorpusRunner owns recoverable installation.
Explicit corpus raw requests disable automatic wrapping to prevent double intros.

`finish_voice_priority.py` remains the coordinator for the frozen priority scope.
Generation and verification are still serial; separate durable shared queues
remain proposed. This change does not claim the proposed VoxStage scheduler/API
sessions are complete.

Every successful result contains pending-review audio and a `.receipt.json` with
semantic input, provider ID, canonical voice/registry version, reference identity,
backend job/model/settings/seeds, optional verifier result, attempts and output
hash. VoxStage job records retain the complete per-chunk history. Machine success,
ASR PASS and the previous reference's acceptance never accept a new recording.

The post-generation automated procedure is
`docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md`, exposed by
`tools/regenerate_voice_corpus.py review`. It screens installed renditions,
including final OGG packaging, without changing audio/receipts, plan or generation
state. It uses existing verifier eligibility and canonical transcript scoring;
unavailable ASR is blocked, excluded semantic classes are explicit, and waveform
thresholds are advisory versioned heuristics. Complete selected traversal,
full-corpus coverage and applicable-ASR completion are distinct report fields.
No voice-identity/acting/independent-language judge is claimed. Machine reports
and human listening remain separate from generation DONE and release authority.

Human listening verifies exact words and locale, character identity, pronunciation,
clipping/tails, delivery and small-speaker intelligibility. Only the owning workflow
promotes accepted output into runtime assets. Already accepted audio is not
regenerated just because the default provider or registry changes.

The owner's subsequent 2026-10-19 request explicitly authorizes the existing
corpus replacement described in `docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`.
The runner submits semantic requests to this engine with the active v0.3
masters, explicit character performance prompts and preserved deterministic
isolated letters/syllables. Former native whole words/numbers are deliberately
assigned to character voices for this operation only; ordinary pedagogical
routing remains unchanged. The inventory never invents missing transcripts.
Existing files are backed up outside Git, then replaced through a recoverable
audio/receipt/catalogue transaction, with receipts and shared rows still PENDING.
This authoring operation is separate from human acceptance and image release.

## 8. Warm service, readiness and extension

Greia holds its generation lock for a whole batch or warm service. VoxStage owns
its own serialized worker and global shared-tool lock. Do not launch parallel raw
models. `request` connects within ten seconds but waits separately for synthesis
(default 3,600 seconds, configurable by `--timeout`, allowed 1–7,200). An uncertain
client timeout does not cancel the server operation.

Start with `python3 tools/greia_voice.py doctor`. It reports the active registry,
all six anchor checks, selected/default provider, packaging, optional verifier
and retained alternative readiness, without importing voices or loading weights.
For exact workstation instructions use `docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md`
and `tools/greia_voice_core/README.md`.

Future synthesis systems implement `VoiceProvider`; future verifiers implement
`SpeechVerifier`. Keep HTTP/model/persistence concerns in focused collaborators.
Do not spread backend selection through Activities, OS code or content producers.

`doctor` exits 0 when the selected character provider, all active references and
FFmpeg are ready; otherwise it exits 2. Optional verifier/retained-alternative
status is reported independently. `selected_character_provider` records the
effective choice; `default_character_provider` records the built-in `voxstage` default.

## Shared human listening review integration (2026-10-21)

The project-neutral HTML listening desk is shared Takeboard, outside this
repository. `tools/export_voice_review_batch.py` is Greia's thin evidence adapter:
completed corpus reports + registry/receipt metadata → generic version-1 batch
manifest with canonical reference paths. It never initializes human approval
from machine scores. Takeboard owns file serving, players, review state/score/
notes editing and save/export/reload. Neither layer changes Greia audio,
production receipts or runtime acceptance; a later project workflow must own
explicit consumption of saved human decisions. Exact operation: automated review
procedure §6, shared Takeboard catalog/skill/README. No child-runtime dependency.

## Historical Whisper policy and preserved comparisons — 2026-10-22

`tools/greia_voice_core/asr_policy.py` retains the pinned multilingual Whisper Base
model/revision and comparison-only diacritic folding for explicitly versioned
historical tools and receipts. New-request generation verification uses
`parakeet_asr.py` as documented above. Existing Whisper observations remain tied
to their recorded verifier and are never reinterpreted as Parakeet. VoiceRequest.ignore_accents defaults true;
false is an explicit per-request strict override carried through CLI/JSON/service.
No authored script or audio is normalized or rewritten. Screen policy v4 can
rescore saved transcripts while retaining their original verifier provenance.
Carrier v6 freezes the model and accent policy; historical plans stay immutable.
Automatic short routing is implemented in the Greia engine; the separately
proposed shared asynchronous queue remains future work.


Saved v6 provider recovery uses `greia_voice_corpus.saved_recovery` and
`tools/recover_voice_candidates.py`. A new plan explicitly opts into
`target-only-v7-saved-v1`; historical row scripts and policies remain intact.
`prepare_saved_candidate` reuses existing provenance validation and packaging,
with v7 extraction and required final canonical guards. CorpusRunner requires
matching recovery metadata, recomputes the final text guards and forbids
synthesis for such plans. RunStore continues to own backups and atomic journal
recovery. The adapter is saved-only, with no fresh-generation mode.

### Period/warm automatic corpus continuation (2026-10-22)

`short_policy.py` owns normal-period intro composition and its receipt version.
`character_delivery.json` owns the warm clear pronunciation defaults; requests
may explicitly override delivery. Permanent voice traits remain in masters.
`GenerationResult.evidence_dir` points to retained short-pipeline lifecycle state.

`greia_voice_corpus.automatic_generation` adapts normal VoiceEngine results to a
separately versioned final-take corpus plan. CorpusRunner owns cumulative
reservation and installation, requires two previous takes, permits one normal
API take, preserves known exhausted quality failures and stops uncertain outcomes
for recovery. It validates actual automatic composition/master/raw evidence and
final canonical/signal checks instead of expecting a historical v6 carrier
receipt. `continue_voice_priority_v7.py` owns frozen-scope preparation and
operational traversal, reusing existing stores and cache. No separate verification
queue or shared-service scheduler change is claimed.

VoxStageClient now distinguishes configurable HTTP-response timeout (default120s)
from overall job wait. POSTs remain single submissions with exact-key recovery.


### Number comparison correction and stopped method experiments (2026-10-22)

`number_comparison.py` owns versioned comparison; `number_lexicon.py` supplies
bounded standard EN/IT/FR/ES cardinals0–100. Current v2 scores canonical digit
text without internal marker characters and keeps exact numeric identity,
including literal codes/signs/decimals. V1 retains its historical inventory and
score. The historical WhisperVerifier comparison and saved-reassessment policy retain this owner;
review/reassess v4 carries explicit locale and the same numeric guard. Missing
locale in old ad-hoc reports is not guessed. No dependency or runtime package
was added. Exact authored text, masters and audio are unchanged.

`carrier_source.CarrierSourcePreparation` is an experimental collaborator over
AudioPipeline, recording native/prepared source hashes. It is NOT wired into
normal automatic generation. Alternate natural-carrier/delivery experiments
likewise do not change the default prompt. Corpus production remains OWNER
STOPPED; see paired-method report and HANDOVER before any authoring operation.


Natural completion update2026-10-22: owner authorized a new bounded natural-
method run for247 unresolved priority cues. It injects NaturalCarrierPolicy and
MethodAttemptBudget into existing ShortPhrasePipeline, with up to3actual new
calls and historical counters retained. Existing transactions install only final
Base/count/number/signal passes, human pending. Initial real-corpus canary hit
METHOD_REVIEW_REQUIRED (2installed,3exhausted,242unstarted); do not blindly resume.
Read docs/agents/GREIA_NATURAL_VOICE_COMPLETION.md and HANDOVER for active method
repair. Alternate policy selection is explicit; normal API defaults unchanged.


### Explicit recorded-only contextual saved recovery (2026-10-22)

This is an opt-in authoring recovery path, not normal short-generation policy.
`target-only-v7-saved-wav-context-v1` composes the existing bounded extractor,
TargetQualityChecker, CorpusRunner and RunStore. `context_recovery` owns exact
original source/remaining scope/job/master/request admission and complete candidate
coverage; `context_evidence` owns read-only pinned ASR observations and physical/
clock/quality replay. Context may rescue lexical substitutions only after isolated
count/number/signal vetoes. Actual packaged WAV and fixed source suffix/prefix
are reproduced; final delivery is checked separately. No provider or recognizer
invocation is available in this recovery mode. Missing observations remain held.
Default v7, OGG and historical comparison policies remain unchanged. Runtime
children never use these authoring collaborators. Operator/API details live in
the core README; executed limited evidence is SAVED_CONTEXT_CORPUS_ADAPTER.

### Registered diagnostic saved-source reconciliation — 2026-10-23

`greia_voice_corpus.diagnostic_reconciliation` is a saved-only bridge for one
registered diagnostic result whose source layout differs from version-1 source
selection. It validates frozen source/priority/remaining state, exact Activity
family and semantic/request aliases, raw and receipt identity, completed provider
job and master, historical attempt ledgers, and the original destination pair.
It then reuses `prepare_saved_candidate`, `CorpusRunner`, and `RunStore`; no
provider or recognizer is available to the saved plan.

A literal target needs no new comparison behavior. Any spoken lexical equivalence
requires a separately pinned registered comparison policy. The current recovered
examples use the narrow Oscar/Oskar spelling policy and the pre-existing finite
English spoken-letter policy; ordinary/default and historical policies are
unchanged. Both installed clips remain human-listening-pending. See
`2026-10-22_SAVED_CONTEXT_CORPUS_ADAPTER.md` (archived; see git history) for exact installation
proof and current evidence boundaries.


### 2026-10-23 — Parakeet-TDT verification and bounded full-pipeline check

Current VoiceEngine verification defaults to local cached Parakeet-TDT v3 at
`ed2b7e8c15f9aaa0b5772e2efb986255eaef7e15`. Both ordinary and automatic-short
public routes check the delivered packaged result when verification is enabled;
short route also screens target-only PCM candidates. It retains actual model
timestamps only, without fabricated alignment, and preserves existing numeric,
count, score, and signal guards. Quality attempts are capped at three; provider,
recognizer, or I/O uncertainty is recoverable and not blindly retried. The explicit
public `verification=off` remains an unverified opt-out. Historical Whisper receipts
are not reinterpreted.

A registered ten-request run via public VoiceEngine produced 6 machine-checked
packaged passes and 4 quality rejections after 21 total jobs. The diagnostic
explicitly injected the natural-carrier recipe; it did not change production prompt
defaults or authorize frozen-corpus continuation. Listening is pending for every
new output. Exact evidence and the 51-item Takeboard batch are recorded in the
2026-10-23 review. This is authoring-source evidence, not child runtime/release
acceptance.


### 2026-10-23 — Parakeet lexical comparison version 3

Owner-approved spelling normalization is scoped to new Parakeet creation paths
under `locale-number-tokens-v3-chck-orthographic`. It recognizes localized
cardinals and numeric identities before lexical normalization, then maps `ch`
(longest first), `c` and `k` to `k` for comparison. This accepts exact C/K and
CH/K substitutions without mutating request text or the recognizer transcript.
Short extraction records the policy in each search result and receipt; the final
delivered checker consumes that same recorded policy. Previous v2/v1 and saved
comparison policies remain separately available for historical evidence. Existing
hyphen/space/punctuation/case/accent normalization already treats
`Raconte-moi` and `Raconte moi` equivalently; the recorded French failure also
had a leading extra word and lexical substitution and therefore remains rejected.
An unset ordinary request uses v3. Registered automatic/natural corpus plans pass
their pinned comparison policy explicitly (currently v2), so frozen plan and
receipt semantics remain stable when the engine default advances.

Read-only replay over the ten-request saved Parakeet run retains the six existing
final package PASS results. Two existing Italian `Trova Oscar` candidate
observations now meet the extraction text predicate against `Trova Oskar`; those
requests had stopped before package/final verification under v2, so they are not
full-pipeline passes. No ASR, TTS, package creation, installation or receipt
mutation was performed in the replay. Exact transcript strings, hashes and the
new full-text listening batch are in `2026-10-23_VOICE_CK_NORMALIZATION.md` (archived; see git history).

### 2026-10-23 — Owner-authorized versioned full-corpus execution

The owner subsequently authorized a separate fresh allowance for the exact 237
currently remaining priority cues. The new `automatic-natural-context-parakeet-v3-full237-v1`
plan preserves the earlier held Whisper/context plans and cumulative history,
pins Parakeet v3 plus `locale-number-tokens-v3-chck-orthographic`, reserves at
most three new actual provider calls per cue, and retains the natural carrier
recipe. One VoiceEngine verifier instance is shared by target extraction and
delivered-package verification. Completed rows resume only when their journal,
installed candidate/receipt and original backups agree; untouched rows must still
match the frozen pre-install pair. The active plan, full 667-pair snapshot and
progress path are recorded in HANDOVER and the current natural completion work
order. This run completed all 237 frozen rows: 147 replacements passed delivered
Parakeet verification and were installed with exact backups; 90 exhausted their
three-call quality allowance and retain their originals. There are no remaining
or blocked rows. The independent terminal audit confirms 430 other frozen pairs
are unchanged and every new receipt remains human-listening-pending. Neither
automated PASS nor a listening page implies owner acceptance or child-device/
release behavior.
