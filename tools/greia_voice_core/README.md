# Greia Voice Production Engine

**Usage reference, reviewed 2026-10-22.** Run commands from the Greia repository
root. This is authoring software; models, masters, services and authoring Python
dependencies do not ship on child devices.

All new Greia speech enters through `tools/greia_voice.py` / `VoiceEngine`.
“Voice Studio” refers to this workflow. Activities and content producers supply
semantic requests; they do not invoke TTS, Whisper or trimming tools themselves.

## Choose the right workflow

| Need | Entry point | Implemented behavior |
|---|---|---|
| One new line, JSONL batch, or requests over time | `greia_voice.py generate / batch / serve / request` | Serialized synthesis; optional eligible-line Base verification; review audio and receipt |
| Inventory and replace an owner-authorized existing corpus | `regenerate_voice_corpus.py` | Frozen scripts, external originals, progress journal, recoverable installation |
| Finish the frozen problematic short-phrase selection | `finish_voice_priority.py` | Audit installed takes, recover saved sources, then bounded fresh carrier/cut/Base attempts |
| Cut an already generated carrier recording | `voice_carrier.py` | Target-suffix alignment and measured PCM pause; separate extracted WAV and evidence |
| Screen an installed corpus without changing it | `regenerate_voice_corpus.py review / reassess` | External automated findings and listening queue |
| Human listening, master comparison, saved scores/notes | `export_voice_review_batch.py` → shared Takeboard | Separate human judgments; no automatic runtime promotion |

**Current boundary:** ordinary `generate`, `batch` and `request` do not
automatically prepend/cut short text. The strict carrier workflow is implemented
in corpus tooling. The general asynchronous generation/verification queues,
automatic short-request routing and configurable word-limit API are still
[proposed work](../../docs/plans/2026-10-22_VERIFIED_VOICE_PIPELINE/README.md).

## 1. Readiness and dependencies

Read [SETUP.md](../../SETUP.md) §7 and the
[workstation guide](../../docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md)
before installing anything. Reuse the installed shared VoxStage worker:

```bash
voxstage start
# Existing Mac environment, including working Whisper Base dependencies:
voice_python="$HOME/Library/Application Support/Greia/voice-production/venv/bin/python"
"$voice_python" tools/greia_voice.py doctor
```

Python 3.11+ and FFmpeg suffice for the default synthesis HTTP client. Base
verification additionally needs the prepared Apple Silicon MLX/Whisper environment
and cached weights. The global Anaconda interpreter on this workstation has an
incompatible Whisper import; use the prepared interpreter above for ASR/cutting.
Do not reinstall packages or download weights during a recording run.

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
design. Masters remain immutable. `character_delivery.json` supplies neutral
performance defaults. A request's `delivery_prompt` replaces that default for
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
| `max_attempts` | **2 total**, allowed 1–4; includes the initial take |
| `ignore_accents` | **true**; false restores strict diacritic comparison |

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

Default ASR uses cached multilingual **Whisper Base**,
`mlx-community/whisper-base-mlx`, revision
`1e3e249fb8d01c655324bd6841b1deadffd6d04c`, owned by `asr_policy.py`.
ASR resolution is offline; missing weights/dependencies are reported, not downloaded.
Comparison ignores diacritics by default (`trovò` = `trovo`), preserving original
scripts/transcripts. Override with CLI `--strict-accents`, JSON
`"ignore_accents": false`, or Python `ignore_accents=False`.

### Ordinary VoiceEngine requests

Eligibility currently excludes Dani, pedagogical/other excluded kinds, one-word
utterances, and text over 500 characters. `required` does **not** remove those
exclusions. For eligible requests:

- `auto`: check if ready; unavailable verifier → `NOT_RUN`.
- `required`: unavailable verifier → `WARN`.
- `off`: no ASR; the current verifier reports `NOT_APPLICABLE`.
- Transcript score **>0.8** → `PASS`; score ≤0.8 or recognition error → `WARN`.

Only `WARN` triggers another synthesis, up to `max_attempts`. The ordinary engine
checks the provider's temporary WAV before final packaging. After exhausted
warnings it still writes the **last** take and receipt, returning
`REVIEW_REQUIRED_ASR_WARNING`. It does not choose the highest-scoring take or
fail closed on ASR. Ordinary verification does not apply the corpus signal gate.

`generate`, `batch`, and `request` exit 0 when output exists, including ASR-warning
output; exit 2 indicates missing/rejected/unavailable output or request error.
Inspect each result's `disposition`, `verification` and receipt, not exit status
alone. Every successful output has a sibling `<audio>.receipt.json` with request,
provider/job/settings/seeds, master identity, attempts, output hash and
`human_review=PENDING`.

### Strict short-phrase corpus workflow

The priority finisher uses a stronger gate for **all six actors**, including
Dani and short targets. Raw carrier synthesis has verification OFF: introductory
mistakes are disposable. The cutter locates the final target and a unique quiet
PCM run; it does not require correctly spoken intro words or a literal ASR word
count. The delivered target is then checked with Base, including the actual
decoded delivery after lossy packaging. Installation requires score **>0.8** and
no signal flags. Internal pauses/trailing silence **<1.5s** do not warn; other
signal checks (including leading silence ≥0.4s) remain active.

An ASR/cut rejection preserves the prior runtime audio. Distinct saved sources
are tried first. New takes use the language prefix, ellipsis/blank line and a
two-second pause instruction; the tool measures the actual gap rather than
assuming the requested silence happened. Maximum **three cumulative fresh
provider generations per cue across history**, not three per restart. Deferred
recordings and deterministic isolated letters/syllables remain excluded.

Current short selection is 1–3 words, or 4 words with ≤28 Unicode letters/digits.
Very short targets and letter names can be false-rejected by ASR. Exhaustion
means unresolved automated evidence, not proof that the recording sounds wrong;
retain the take for listening rather than silently relaxing the gate.

Speaker selection is configurable; word/character limits currently live in
`greia_voice_corpus/carriers.py`, with no public word-limit CLI flag.
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
