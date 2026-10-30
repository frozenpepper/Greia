# Greia Voice Production Engine

**Usage reference, reviewed 2026-10-23.** Run commands from the Greia repository
root. This is authoring software; models, masters, services and authoring Python
dependencies do not ship on child devices.

All new Greia speech enters through `tools/greia_voice.py` / `VoiceEngine`.
“Voice Studio” refers to this workflow. Activities and content producers supply
semantic requests; they do not invoke TTS, ASR or trimming tools themselves.

**Current verification default:** cached local multilingual Parakeet-TDT v3
(`mlx-community/parakeet-tdt-0.6b-v3`, revision
`ed2b7e8c15f9aaa0b5772e2efb986255eaef7e15`) in the prepared voice environment.
It checks applicable delivered audio and short-route target candidates. Missing
model/dependencies fail as unavailable; the engine does not download or silently
fall back to Whisper. Historical Whisper tools/receipts remain versioned and are
not relabeled. Machine PASS remains `human_review=PENDING`.

## Choose the right workflow

**Current owner-authorized corpus replacement (2026-10-23, v4 spoken-target run):** the prior v3 Parakeet run is terminal (147 installed automatic PASS, 90 preserved). Takeboard 8818 human approvals recovered 13 exact extracted target cuts through RunStore transactions; each receipt carries the unchanged automatic FAIL/WARN and separate human-review provenance. One additional approved cut corresponds to an already-DONE French alphabet E pair and was not installed. The new, separately versioned v4 plan covers the exact 77 unresolved rows after recovery (16 contextual letter-name cues, 7 already-worded number cues, 54 ordinary cues), uses locale-spelled spoken targets and `locale-number-tokens-v4-spoken-target-v1`, and keeps the three-fresh-call cap. No automated result is promoted to human acceptance. See the current v4 entry in HANDOVER for the external plan, producer state and verification evidence.

The v4 producer is now `BOUNDED_COMPLETE`: 25/77 generated requests installed
after final packaged Parakeet PASS, 52/77 originals preserved after quality
exhaustion, and 199 actual provider calls. All generated replacements remain
listening-pending. The separate 667-pair audit and 475-row review batch URL are
recorded in `HANDOVER.md`; this result does not rewrite historical plans or
automatically accept audio.

**Owner-directed native fallback (2026-10-23):** for the exact 52 preserved
v4 rows, the owner authorized deterministic macOS system speech and waived
listening review. This run uses the existing `MacOSNativeSpeechProvider`, with
the existing locale profiles Samantha/en, Alice/it, Mónica/es and Thomas/fr.
The versioned request authorization `owner-2026-10-23-native-system-tts-missing-52`
is accepted only for one character-dialogue request with exact frozen `spoken_text`,
verification OFF, short mode OFF and one attempt. The engine still packages and
validates the delivered WAV, but skips ASR and records `verification=NOT_RUN`,
`human_review=WAIVED_BY_OWNER`, and the actual native voice ID. This is an
owner-authorized recording/install, not an automatic Parakeet or listening PASS;
the old Parakeet plans and receipts remain unchanged.

| Need | Entry point | Implemented behavior |
|---|---|---|
| One new line, JSONL batch, or requests over time | `greia_voice.py generate / batch / serve / request` | Automatic short carrier/cut/Parakeet routing; serialized synthesis; review audio and receipt |
| Inventory and replace an owner-authorized existing corpus | `regenerate_voice_corpus.py` | Frozen scripts, external originals, progress journal, recoverable installation |
| Finish the frozen problematic short-phrase selection | `finish_voice_priority.py` | Audit installed takes, recover saved sources, then bounded fresh carrier/cut/Parakeet attempts |
| Cut an already generated carrier recording | `voice_carrier.py` | Target-suffix alignment and measured PCM pause; separate extracted WAV and evidence |
| Screen an installed corpus without changing it | `regenerate_voice_corpus.py review / reassess` | External automated findings and listening queue |
| Human listening, master comparison, saved scores/notes | `export_voice_review_batch.py` → shared Takeboard | Separate human judgments; no automatic runtime promotion |

**Current default:** normal VoxStage character requests with **fewer than five
words** automatically use the localized carrier → cut → final Parakeet pipeline.
This applies to CLI, JSONL, Python and warm-service requests, including Dani.
Deterministic pedagogical speech stays on its native route. `short_text_mode=off`
explicitly bypasses wrapping; word/character limits are configurable per request.
The retained Chatterbox adapter uses the ordinary route in auto mode; forcing
`on` on an unsupported provider is rejected. Separate durable generation and
verification queues remain [proposed shared work](../../docs/plans/2026-10-22_VERIFIED_VOICE_PIPELINE/README.md).

## 1. Readiness and dependencies

Read [SETUP.md](../../SETUP.md) §7 and the
[workstation guide](../../docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md)
before installing anything. Reuse the installed shared VoxStage worker:

```bash
voxstage start
# Existing Mac environment, including cached local Parakeet dependencies:
voice_python="$HOME/Library/Application Support/Greia/voice-production/venv/bin/python"
"$voice_python" tools/greia_voice.py doctor
```

Python 3.11+ and FFmpeg suffice for the default synthesis HTTP client. Parakeet
verification additionally needs the prepared Apple Silicon MLX environment and
pinned cached weights. Use the prepared interpreter above for ASR/cutting. Do not
reinstall packages or download weights during a recording run.

`doctor` does not synthesize, import voices or download weights. Exit 0 means
selected character provider + references + FFmpeg are ready; exit 2 means they
are not. Inspect `verifier.available` separately: doctor exit 0 does not promise
ASR readiness or native pedagogical availability.

## 2. Identity, language and performance

The active registry is
`assets/audio/characters/canonical/v0.3/manifest.toml`:

| Speaker | Exact Greia voice ID |
|---|---|
| dani | `greia.dani.v3` |
| momo | `greia.momo.v3` |
| tito | `greia.tito.v3` |
| lilli | `greia.lilli.v2` |
| leo | `greia.leo.v2` |
| flash | `greia.flash.v2` |

Use these semantic speaker names, including **lilli**. The adapter resolves their
exact selected VoxStage identities; it never replaces an existing conflicting
saved voice. A fresh library can import the selected repository references lazily.

Pitch/register, timbre, vocal age and permanent personality belong in master
design. Masters remain immutable. `character_delivery.json` supplies warm, calm, clear reading
with careful natural pronunciation. A request's `delivery_prompt` replaces that default for
line-specific tone/mood/pace; do not repeat identity descriptors on every line.
The VoxStage adapter adds language direction separately from spoken text. Its
effective delivery field, including that language prefix, must fit 300 characters.
Chatterbox/native reject explicit delivery prompts they cannot implement.

Released languages are `en`, `it`, `fr`, `es`. Supply exact authored words in that
language, including accents. VoxCPM2 has no hard language/phoneme selector;
pronunciation, acting and character identity require listening.

| Kind | Route |
|---|---|
| `character_dialogue` | selected cloned character, all six speakers |
| `shared_character_utterance` | same; static shared-library authoring |
| `dani_system_speech` | selected Dani clone; retained compatible kind |
| `pedagogical_speech` | independent deterministic native/system pronunciation |

Pedagogical requests use speaker `pedagogical` or `system`. Isolated educational
letters/syllables must keep that pronunciation-authoritative route.

## 3. One line, JSONL and Python

Generate into external review staging:

```bash
"$voice_python" tools/greia_voice.py generate \
  --speaker leo --kind character_dialogue --locale it \
  --text 'Guardiamo con calma.' --cue-id presenter.hint \
  --delivery-prompt 'Quiet and reassuring.' \
  --verification required --max-attempts 3 \
  --output /tmp/greia-voice-review/presenter-hint.ogg

"$voice_python" tools/greia_voice.py generate \
  --speaker pedagogical --kind pedagogical_speech --locale it \
  --text 'ma' --cue-id phonics.ma --verification off \
  --output /tmp/greia-voice-review/phonics-ma.wav
```

Create `requests.jsonl` with one JSON object per line:

```json
{"speaker":"tito","kind":"character_dialogue","locale":"es","text":"Mira lo que encontramos.","cue_id":"discovery.es","output":"/tmp/greia-voice-review/discovery-es.wav","verification":"required","max_attempts":3,"ignore_accents":true}
{"speaker":"dani","kind":"dani_system_speech","locale":"fr","text":"Motif détecté !","cue_id":"pattern.fr","output":"/tmp/greia-voice-review/pattern-fr.wav","verification":"auto"}
```

```bash
"$voice_python" tools/greia_voice.py batch --input /absolute/requests.jsonl
```

JSON/Python requests share these fields:

| Field | Default / contract |
|---|---|
| `speaker`, `kind`, `locale`, `text` | required; exact semantic speaker and approved words |
| `cue_id` | optional stable semantic identifier, recommended |
| `output` | optional WAV/OGG path; absent → authoring-state review folder; relative → repository root |
| `delivery_prompt` | empty → character default; nonempty → cue-specific performance |
| `verification` | `auto`; alternatives `required`, `off` |
| `max_attempts` | **3 total**, allowed 1–4 on ordinary routes; short pipeline caps at 3; includes the initial take |
| `ignore_accents` | **true**; false restores strict diacritic comparison |
| `short_text_mode` | **auto**; `off` bypasses wrapping; `on` forces it on a supported character provider |
| `short_text_max_words` | **4** inclusive, allowed 1–20; Unicode words with internal apostrophes |
| `short_text_max_alnum` | **null**; optional additional AND limit, 1–1000 Unicode letters/digits |

For in-process use, start Python with `PYTHONPATH=tools:src` from the repo root:

```python
from pathlib import Path
from greia_voice import build_engine
from greia_voice_core.models import SpeechKind, VerificationMode, VoiceRequest

with build_engine() as engine:
    result = engine.generate(VoiceRequest(
        speaker="momo", kind=SpeechKind.CHARACTER_DIALOGUE,
        locale="en", text="We can try again.", cue_id="encourage.retry",
        output=Path("/tmp/greia-voice-review/retry.wav"),
        verification=VerificationMode.REQUIRED, max_attempts=3,
        ignore_accents=True,
    ))
    print(result.to_dict())
```

## 4. Verification and result handling

Default ASR uses cached multilingual **Parakeet-TDT v3**,
`mlx-community/parakeet-tdt-0.6b-v3`, revision
`ed2b7e8c15f9aaa0b5772e2efb986255eaef7e15`, owned by `parakeet_asr.py`.
ASR resolution is offline; missing weights/dependencies are reported, not downloaded
or silently replaced by Whisper. Historical Whisper evidence keeps its original
verifier identity and is not reinterpreted.
Comparison ignores diacritics by default (`trovò` = `trovo`), preserving original
scripts/transcripts. Override with CLI `--strict-accents`, JSON
`"ignore_accents": false`, or Python `ignore_accents=False`.

### Ordinary route (long speech or explicit carrier bypass)

On this ordinary route, eligibility currently excludes Dani, pedagogical/other excluded kinds, one-word
utterances, and text over 500 characters. `required` does **not** remove those
exclusions. For eligible requests:

- `auto`: check if ready; unavailable verifier → `NOT_RUN`.
- `required`: unavailable verifier → `WARN`.
- `off`: no ASR; the current verifier reports `NOT_APPLICABLE`.
- Transcript score **>0.8** → `PASS`; score ≤0.8 or recognition error → `WARN`.

Known quality `WARN` triggers another synthesis, up to `max_attempts`. Each
candidate is packaged and the delivered audio is checked before publication.
Exhaustion returns no output. Indeterminate ASR/provider/I/O outcomes stop as
`NEEDS_RECOVERY` without blindly submitting another take. Explicit public
`verification=off` opts out of ASR and is unverified, not a machine PASS.

`generate`, `batch`, and `request` exit 0 when the result returns an output path, including ASR-warning
output; exit 2 indicates missing/rejected/unavailable output or request error.
Inspect each result's `disposition`, `verification` and receipt, not exit status
alone. Every successful output has a sibling `<audio>.receipt.json` with request,
provider/job/settings/seeds, master identity, attempts, output hash and
`human_review=PENDING`.

### Automatic short-phrase pipeline

Automatic short requests use extractor **v7** (`tools/voice_carrier_search.py`)
for all six actors, including Dani and one-word targets. The localized intro is
disposable: raw carrier synthesis has verification OFF, and no raw-intro ASR is
requested. PCM measurements identify quiet runs of at least 200 ms (10 ms
frames, RMS ≤−42 dBFS and peak ≤−30 dBFS). Each retained suffix starts 100 ms
before the run ends and is transcribed independently with pinned Parakeet-TDT v3,
without an expected-text prompt. More than six candidate runs rejects before
ASR; exactly one suffix must qualify. Zero or multiple matches reject. Each
candidate must retain energetic speech and have energetic speech before its cut.

The normal API uses the extractor's `warn` comparison policy: score **>0.8**,
equal canonical comparison-unit count, and identical numeric-token sequence.
This does not mean a warning is published: the final delivered target still must
pass `TargetQualityChecker` with no signal flags. `required` extraction, available
through the Python cutter API, instead requires exact canonical units.
Locale-specific spelled numbers and digits **0–100** compare equivalently in
EN/IT/FR/ES, including listed compounds such as `dix-sept`. Wrong numbers,
extra/missing units, leading-zero codes, signed/decimal notation and arbitrary
joined words are not silently treated as equivalent. Accents are ignored by
default; `ignore_accents=False` / `--strict-accents` overrides this.

Historical/general number comparison v2 remains `locale-number-tokens-v2`:
canonical units retain exact numeric identity, but similarity scores use ordinary
digit text, not internal `<num:...>` labels. This fixes artificial score
inflation (e.g. `Client to 10` for `Count to ten`). New Parakeet verification,
short-target extraction and its delivered check use the registered
`locale-number-tokens-v3-chck-orthographic` policy. It parses locale cardinals and
literal numeric identities first, then compares lexical `ch`, `c` and `k` as `k`
for this version only. Expected authored text and exact ASR transcripts remain
unchanged and are retained in receipts/evidence. Thus `Oskar`/`Oscar`, `casa`/
`kasa`, `chico`/`kiko`, and `Raconte-moi`/`Raconte moi` compare equivalently.
Existing v2, saved-replay and historical receipts retain their declared policy;
this does not make extra/missing words or different numeric values equivalent.
Ordinary requests leave the policy unset and use the current Parakeet v3 default;
registered corpus plans explicitly pin their frozen policy (currently v2) so
resuming them does not reinterpret prior evidence.
Numeric digits outside the spelling range still have exact identity guards;
leading-zero codes, signed/decimal literals are kept distinct. The supported
spelling range is bounded: this is not an arbitrary-number or phonetic parser.
V1 evidence keeps its historical 0–25 rules/scoring when explicitly interpreted
as v1; old receipts and reports are never rewritten. Review policy is now v4.

`CarrierSourcePreparation` in `carrier_source.py` is an **experimental**, explicit
native→22,050Hz mono PCM preparation collaborator, with both hashes retained.
It is not the default ShortPhrasePipeline recipe. Normalized replays and prompt
experiments live outside the repository. The owner stopped the corpus to repair
the method; new small diagnostics do not authorize bulk restart or installation.
See paired method evidence (archived; see git history).

The actual delivered rendition is checked after packaging, including decoded
lossy delivery. Parakeet token timestamps are retained only when supplied by the
model; no word alignment is fabricated. Internal pauses/trailing silence
**<1.5s** do not warn; existing signal checks (including leading silence ≥0.4s)
remain active. No gain normalization is applied by this correction. If the target
occurs inside the primary intro, a predefined alternate localized intro is used.

Exhaustion returns REJECTED with no output path, preserving raw takes/evidence
and the prior destination. An unavailable alignment verifier blocks before
synthesis. Provider/ASR/disk/infrastructure errors stop in NEEDS_RECOVERY without
spending another take. Evidence is retained under
`GREIA_VOICE_HOME/short-phrases/`; each extraction also retains bounded candidate
WAVs and `search.json` beside its cut. Archive evidence after review. There is
no blind automatic restart of an uncertain job. Machine PASS is listening-pending.

`--verification off` skips final quality scoring but still runs target-only ASR
to select a safe cut. For zero ASR, explicitly use **both**
`--short-text-mode off --verification off`. Such output is unverified, not PASS.

CLI overrides (JSON/Python use the corresponding underscore names):

```bash
# Normal generate/request arguments plus these optional routing controls:
# --short-text-mode auto|off|on
# --short-text-max-words 4
# --short-text-max-alnum 28
```

Each automatic call uses up to three total provider takes, bounded further by
`max_attempts`. No more than 240 characters may enter the composite and the
combined delivery must fit 300; oversize composites fail before submission so
VoxStage cannot split intro/target into separate recordings.

### Existing frozen corpus operations

**Diagnostic stop, 2026-10-22:** the historical priority producer still calls v6.
Do not resume it unchanged. Normal API v7 does not mutate frozen plans or
retroactively replace their extraction policy. The saved-only adapter
`tools/recover_voice_candidates.py` now reconciles v7 metadata and budgets for
FAILED source rows without synthesis. Further generation still requires a
separately evidenced continuation. See `2026-10-22_V7_SAVED_CORPUS_RECOVERY.md` (archived; see git history).

The finisher retains its original narrower selection (1–3 words or 4 words with
≤28 alphanumerics); the new automatic API default does not expand that scope.
Its explicit raw carrier requests set `short_text_mode=off` to prevent double
wrapping. Shared delivery preparation and packaged-target checking are reused;
legacy frozen corpus checks retain their original token-count policy.

An ASR/cut rejection preserves the prior runtime audio. Distinct saved sources
are tried first. New takes use the language prefix, ellipsis/blank line and a
two-second pause instruction; the tool measures the actual gap rather than
assuming the requested silence happened. Maximum **three cumulative fresh
provider generations per cue across history**, not three per restart. Deferred
recordings and deterministic isolated letters/syllables remain excluded.

Very short targets and letter names can be false-rejected by ASR. Exhaustion
means unresolved automated evidence, not proof that the recording sounds wrong;
retain the take for listening rather than silently relaxing the gate.

Corpus speaker selection and its frozen word/character rule remain separate
from the normal API routing parameters above.
See the [exact corpus commands/recovery](../../docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md)
and [cutter contract](../../docs/agents/GREIA_SPOKEN_CARRIER_EXTRACTION.md).
Standalone extraction does not synthesize, retry or install files.

## 5. Warm service, shared queue and recovery

For repeated requests, start Greia's semantic socket service at `127.0.0.1:43841`:

```bash
"$voice_python" tools/greia_voice.py serve
# Another shell, with voice_python set as above:
"$voice_python" tools/greia_voice.py request \
  --speaker lilli --kind character_dialogue --locale en \
  --text "Let's try something new!" --cue-id presenter.try-new \
  --output /tmp/greia-voice-review/try-new.ogg --timeout 3600
"$voice_python" tools/greia_voice.py shutdown
```

This socket service is separate from VoxStage's HTTP API at `127.0.0.1:8791`.
The Greia service holds the generation lock for its lifetime, including idle
time. A batch/corpus process also owns that lock: do not launch a competing
`generate`, batch or service during it. Shutdown stops the Greia service only.
No separate background verification queue is implemented; current calls are serial.

VoxStage's one inference worker is shared across projects. Inspect with
`voxstage jobs queue` / `voxstage jobs get JOB_ID`. A transport timeout does not
cancel inference. Inspect the **same** job and idempotency key and recover its
completed output before considering another synthesis; never blindly resubmit.
POSTs are not automatically repeated. Corpus GENERATING/INSTALLING states require
provider/transaction reconciliation, not deleting the lock or resetting counts.

Use `voxstage unload` to release model memory only when the shared worker is idle
and no other project needs it. `voxstage stop` finishes the current recording and
keeps remaining jobs queued for next start; it does **not** drain the queue.
Do not stop/restart the shared service to discard jobs.

| Configuration | Meaning |
|---|---|
| `GREIA_VOICE_CHARACTER_PROVIDER` | `voxstage` default; `chatterbox` explicit alternative; CLI `--character-provider` wins |
| `GREIA_VOXSTAGE_URL` | loopback HTTP origin only; default `http://127.0.0.1:8791` |
| `VOXSTAGE_API_KEY` | optional environment-only service authentication |
| `GREIA_VOXSTAGE_HTTP_TIMEOUT` | per-HTTP-response timeout:120s default, allowed1–7,200; distinct from job wait; no POST retries |
| `GREIA_VOXSTAGE_TIMEOUT` | provider job wait: 1,800s default, allowed 1–7,200 |
| `request --timeout` | semantic service response wait: 3,600s default, allowed 1–7,200 |
| `GREIA_VOICE_HOME` | review/lock state outside Git; independent of VoxStage data root |

Chatterbox remains explicitly selectable on `doctor/generate/batch/serve`; no
silent provider fallback occurs. Read its setup/field guide before loading that
alternate model, and coordinate memory use with the shared worker.

## 6. Automated review and human listening

```bash
"$voice_python" tools/regenerate_voice_corpus.py review \
  --work-dir /absolute/finished-corpus-run \
  --report-dir /absolute/new-review-report --asr auto
```

The [automated review procedure](../../docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md)
explains eligibility/coverage, findings, resumability and exit statuses. It reads
installed audio without changing receipts, files or acceptance. `reassess`
re-scores saved measurements/transcripts; it does not re-run Base or relabel
historical Tiny evidence. Use a fresh report directory for a changed policy.

Export completed review reports with Greia's `export_voice_review_batch.py`, then
use shared Takeboard for audio/master comparison and saved human judgments.
Machine PASS, corpus DONE and an accepted master do not accept new speech.
Listen for exact words/locale, pronunciation/stress, identity, delivery, clipping,
repeats and small-speaker intelligibility. The owning workflow promotes accepted
output; the explicit corpus replacement exception installs listening-pending
assets with recoverable originals.

## Documentation and source map

- [Voice-production skill](../../skills/greia-voice-production/SKILL.md): agent workflow.
- [Architecture](../../docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md): ownership/seams.
- [Canonical voice design](../../docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md): selected identity policy.
- [Workstation setup](../../docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md): environment/readiness.
- [Corpus operation](../../docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md): plans, installation, retries, restoration.
- [Carrier extraction](../../docs/agents/GREIA_SPOKEN_CARRIER_EXTRACTION.md): suffix alignment/PCM safety.
- [Automated review](../../docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md): screening and human-review export.

Source owns exact behavior: `models.py`/`service.py` request fields,
`engine.py` ordinary retries, `verification.py` eligibility/scoring,
`asr_policy.py` pinned Base/accent folding, `review.py`/`review_policy.py` signal thresholds,
`greia_voice_corpus/carrier_generation.py` strict final-target gate,
`greia_voice_corpus/runner.py` transactional installation, and
`tools/finish_voice_priority.py` scoped continuation/budgets.

### Recover saved corpus sources with v7

The normal automatic API already uses v7. For historical frozen v6 corpus takes,
use `tools/recover_voice_candidates.py` to stage failed saved sources in a new
external directory, then `--install` that completed directory. It cannot submit
synthesis, requires final verification, preserves cumulative budgets and uses
existing CorpusRunner backup/transactions. Exact flags and resume rules are in
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md` § V7 saved-provider recovery.
Historical producers remain stopped; this is not a fresh-generation command.


Historical FAILED/PRESERVED provider takes can be selected explicitly with
`recover_voice_candidates.py --source-selection <index.json>`. The corpus manual
owns the versioned index schema and provenance gates. It binds unchanged
remaining/priority/source-plan IDs and exact completed job/key/media; differing
provider/retained WAV rates require exact existing packaging reproduction.
No fresh-generation mode or approval override is introduced.


### Current short recording direction and final priority take

Owner update2026-10-22: the spoken intro ends with a **normal period**, then a
paragraph break and the exact target. No ellipsis is added. Receipt composition
policy: `period-separated-intro-v1`. Default direction for all six actors:

> Read clearly in a warm, calm tone. Pronounce every word carefully and naturally.

The short pipeline appends its separate silent-pause/final-target instruction.
Master identity/register/timbre are still supplied only by the selected master.
A request may explicitly override the default delivery. Historical recordings
and frozen carrier plans retain the actual prompts used to create them.

`continue_voice_priority_v7.py` prepares/runs only the last remaining cumulative
take of frozen priority rows with exactly two prior submissions. It calls normal
VoiceEngine with short mode ON, required verification and max_attempts=1, then
uses existing CorpusRunner transactions. Known quality failures preserve the
original as budget-exhausted; provider/ASR/IO uncertainty stops NEEDS_RECOVERY.
`GenerationResult.evidence_dir` is an optional structured path for retained short
pipeline state; automation reads it instead of parsing error prose. See the
corpus manual for the versioned plan/commands and live readiness gate.


Natural completion update2026-10-22: owner authorized a new bounded natural-
method run for247 unresolved priority cues. It injects NaturalCarrierPolicy and
MethodAttemptBudget into existing ShortPhrasePipeline, with up to3actual new
calls and historical counters retained. Existing transactions install only final
Base/count/number/signal passes, human pending. Initial real-corpus canary hit
METHOD_REVIEW_REQUIRED (2installed,3exhausted,242unstarted); do not blindly resume.
Read docs/agents/GREIA_NATURAL_VOICE_COMPLETION.md and HANDOVER for active method
repair. Alternate policy selection is explicit; normal API defaults unchanged.


Natural completion continuation2026-10-22: the original natural247run is held.
A saved-only English Oskar/Oscar policy is explicit, opt-in and retains raw ASR;
normal/historical numeric policies do not change. The ordinary-speech child197
moves only zero-use allowances through natural_continuation, never rebudgets
attempted cues.45letter cues remain separate. Read the current completion guide
and HANDOVER; do not restart a held parent or duplicate its child. Existing
quality/poor-yield guards and humanPENDING state remain binding.


Historical voice continuation correction (2026-10-22): BOTH natural producers were held
for poor yield; do not restart natural-context-v1 or natural-context-speech-v1.
Latest exact audit7installed pending,240remaining. Explicit saved-only English spoken
comparison can recover homophonic recognition errors without another provider
call; normal API defaults and historical policies remain unchanged. Read the
current natural completion guide/HANDOVER for diagnostic state and remaining
lists. A failed prompt experiment never authorizes a blind bulk continuation.


2026-10-22 context safety correction: the82-source packaged-context experiment
failed on an uncut-intro OGG false approval. Neither context version is selected.
Two additional saved diagnostic takes pass unchanged isolated checks and were
installed pending through existing transactions; no new synthesis/default change.
Current7installed/240remaining, all actual corpus/diagnostic calls retained. Follow
PACKAGED_CONTEXT_SAFETY_REVIEW and HANDOVER for optional saved-WAV scope; never
restart held producers or claim failed experimental gates passed.

## Disabled saved-WAV substitution experiment (2026-10-22)

This is a maintainer extension seam, **not an enabled generation mode**. Normal
short routing, v7 extraction, OGG checking and all default comparison policies
remain unchanged. The earlier broad packaged-context experiment failed its
registered gates; this seam does not adopt that experiment.

`contextual_target.ContextualTargetChecker(audio, transcriber, evidence_root)`
checks the exact original PCM suffix against the actual packaged/decoded WAV.
It preserves isolated screening first. Context may be consulted only for a
lexical substitution with nonempty isolated text, matching canonical count and
numbers, and no signal flags. It cannot override extra/missing words or numeric
conflicts. Reconstructed context uses the original prefix through the fixed
sample cut plus the **actual decoded payload**, without requiring intro wording
agreement. Every timestamped word after that fixed boundary is compared;
straddling, incomplete, unordered or nonfinite timings reject.

For explicitly registered saved-audio experiments only:

```python
from greia_voice_core.contextual_target import (
    ContextualTargetChecker, PackagedCandidateVerifier,
)

checker = ContextualTargetChecker(audio_pipeline, observed_offline_base, evidence_root)
# Existing voice_carrier_search.extract(...) keyword, disabled when omitted:
candidate_verifier = PackagedCandidateVerifier(checker)
# Final delivery can use TargetQualityChecker(context_checker=checker), passing
# source=<immutable raw WAV> and packaged=<actual delivered WAV> to check(...).
```

The injected transcriber must use installed pinned Base/settings without an
expected-text prompt, persist exact audio/hash/locale/settings/ASR observations
before interpretation, and serialize access. Caller owns the bounded evidence
batch and cleanup. Each checker observation uses at most two offline ASR calls;
the cutter retains its existing six-candidate cap and unique-boundary rule.
`context_timing.TimedTargetSlice` owns complete word-clock validation. Invalid
clock/provenance/IO is fail-closed uncertainty, not permission to resynthesize.

Opt-in receipts use extraction version
`greia-spoken-carrier-extractor-v7-saved-wav-context-v1` and verification policy
`saved-wav-context-hard-invariants-v1`, retain isolated/contextual evidence and
explicitly acknowledge that the recognizer may hear the prefix on fallback.
Normal production still does not enable these versions. The separately explicit
saved-only policy `target-only-v7-saved-wav-context-v1` now admits them through
`recover_voice_candidates.py` and normal CorpusRunner/RunStore transactions.
Read the following section; never bypass its source selection or use it to spend
fresh corpus takes.

### Recorded-only contextual saved recovery

This mode **cannot synthesize or run Whisper**. It reads an existing, exact
`CachedTranscriber` observation cache, indexed by audio SHA256, locale, pinned
Base model/revision and unchanged no-prompt/deterministic timestamp settings.
Missing observations stop; do not fill them by rerolling recognition. A separate
bounded saved-audio experiment may obtain new evidence under its own registration.
`context_evidence.RecordedTranscriber` owns this read-only seam. Each checker now
also retains full isolated/contextual observations with identity/hash witnesses
inside its run before interpreting them, including failing timestamp responses.

Stage a new external run with the existing recovery CLI:

```bash
python tools/recover_voice_candidates.py --work-dir /external/new-run \
  --source-work /external/original-frozen-run \
  --priority-file /external/frozen-priority.json \
  --history-root /external/original-history \
  --source-selection /external/selected-sources.json \
  --cache-root /external/exact-observation-cache \
  --policy target-only-v7-saved-wav-context-v1
python tools/recover_voice_candidates.py --work-dir /external/new-run --install
```

Use the prepared voice Python documented in the setup guide. Source selection
uses the existing version-1 schema: source plan/priority hashes, hash-pinned
current remaining list, and per-path raw/receipt/completed provider-job manifest
identities. It is mandatory in contextual mode. The frozen source must have the
same semantic request/carrier and original destination pair; original plans are
never rewritten. OGG is rejected. Normal recovery policies retain prior behavior.

`greia_voice_corpus.context_recovery` owns source and admission checks. Before
installation it replays **every** bounded candidate from retained observations,
requires one qualifying cut, rechecks the final actual packaged WAV independently,
and reproduces prefix/suffix PCM derivation. Count/number/signal vetoes and complete
word-clock rules remain mandatory. Full recorded results and strategy metadata
stay separate from human review. Installation uses existing recoverable originals,
journals and PENDING receipts. Attempt budgets are copied unchanged, never spent
or reset. See `2026-10-22_SAVED_CONTEXT_CORPUS_ADAPTER.md` (archived; see git history) for executed evidence;
this limited saved recovery does not establish live-generation reliability.


### Registered diagnostic saved-source reconciliation — 2026-10-23

`greia_voice_corpus.diagnostic_reconciliation` permits an exact registered
diagnostic result to enter saved-only recovery when its source is outside the
older source-selection layout. It pins the frozen source plan, current remaining
and priority snapshots, original destination hashes, Activity family, semantic
and actual request aliases, raw WAV and receipt, completed job/master, and
attempt ledgers. It then reuses the existing saved candidate, CorpusRunner and
RunStore transaction; saved-recovery plans still cannot synthesize.

Literal target matches use the normal explicit comparison policy. Spoken
equivalence requires a separately registered comparison policy, selected here
for exact Oscar/Oskar spelling across released locales and the existing finite
English letter-name policy. This does not broaden the default or historical
comparison behavior. The source for `C as Cat` belongs to already-resolved Leo
letter C and must not be reused for Forest `find_c` by text alone.

The 2026-10-23 saved-recovery audit recovered two pending recordings (French Tito Oskar and
English Leo W): 2 pairs changed, 665 frozen pairs unchanged, and 1,559 other
protected hashes unchanged. Combined frozen-667 status is 10 changed, 430 kept
or installed, 237 remaining (44 letters, 193 ordinary, 0 exhausted) at that
historical audit boundary. Takeboard
8814 contains ten human-listening-pending clips. Corpus parent/child saved-only
screening yield was 7/25 (28%); the producers were held at that point. The
owner's later 2026-10-23 order explicitly authorizes the separate full 237-row
replacement now running; follow the current-run instructions at the top of this
README and HANDOVER. Do not resume or alter the old plans. The earlier next step
was
read-only earliest-failed-predicate attribution over the 25 retained cases.
That investigation restriction was superseded by the new explicit production
order. See
`2026-10-22_SAVED_CONTEXT_CORPUS_ADAPTER.md` (archived; see git history) for exact evidence.
