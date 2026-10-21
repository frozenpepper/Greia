# Greia Voice Production Engine

**Status:** canonical authoring-time subsystem; VoxStage/VoxCPM2 selected default
**Reviewed:** 2026-10-19
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

## 2. Composition and source owners

```text
semantic CLI / batch / warm service / repository producers
  -> greia_voice.build_engine
  -> composition.build_providers (one operator-selected character backend)
  -> VoiceEngine
       |-- VoiceRegistry: active v0.2 identities and reviewed references
       |-- VoiceProvider
       |     |-- VoxStageProvider (default, all six characters)
       |     |     -> VoxStageClient -> shared loopback VoxStage worker
       |     |-- ChatterboxMLXProvider (explicit retained alternative)
       |     |-- MacOSNativeSpeechProvider (pedagogical, legacy system profiles)
       |     `-- UnsupportedNativeSpeechProvider (honest unavailable result)
       |-- SpeechVerifier / optional advisory WhisperVerifier
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

`assets/audio/characters/canonical/v0.2/manifest.toml` is the active registry.
Canonical IDs are `greia.{lilli,leo,flash,dani,tito,momo}.v2`. Every character now
has a reviewed cloning reference, including Dani. The complete selected WAV is
copied unchanged as both source master and canonical reference; it is not
truncated, resampled or regenerated during promotion.

`assets/source/audio/character-voice-masters/v0.2/provenance.json` records the
owner's selections, exact transcripts, original design descriptions, seeds,
source job IDs and model/runtime identity. The owner accepted the six masters
and all 24 four-language comparison samples on 2026-10-19. New generations still
start with human review pending. v0.1 is historical; earlier accepted shipping
recordings and their receipts remain valid and unchanged.

`VoiceRegistry` verifies the existing authoring reference hash before generation.
This preserves the selected speaker identity; it is not runtime anti-tampering,
asset signing or a restriction on users editing their installed files.

## 4. Routing and operator configuration

| Semantic request | Default |
|---|---|
| Any of six speakers + `character_dialogue` | VoxStage/VoxCPM2 with that speaker's v0.2 master |
| Any of six speakers + `shared_character_utterance` | same cloned-character provider |
| Dani + `dani_system_speech` | same provider, Dani's v0.2 master |
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
for this default route. `VoxStageProvider.close()` does not unload or shut down a
service used by other projects. The operator uses `voxstage unload` after
production to free model memory, or `voxstage stop` to drain/stop the service.

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
It uses the active v0.2 references, including Dani, and retains warm model reuse,
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

Optional Whisper remains advisory for suitable multi-word character lines.
Dani keeps the existing human-review-only ASR policy, and letters/syllables are
never accepted through ASR. Unavailable optional Whisper is reported; it does not
change the selected synthesis backend. `--verification off` performs no ASR.

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
The runner submits semantic requests to this engine with the selected v0.2
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
