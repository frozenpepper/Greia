# Greia Voice Production Engine — Quick Start

**Current default:** VoxStage/VoxCPM2 with the six owner-selected v0.2 masters
(2026-10-19). Chatterbox remains explicitly selectable. Dani now has a cloned
reference; its existing `dani_system_speech` kind still works.

One semantic authoring entry point serves Activities, OS/shared libraries and
Encyclopedia: `tools/greia_voice.py`. Callers never operate VoxStage, Chatterbox,
native TTS, Whisper, reference files or FFmpeg directly. No synthesis model,
worker or reference master is installed on child devices.

## Setup and readiness

The Greia CLI requires Python 3.11+ and FFmpeg for 22,050 Hz mono WAV/OGG packaging.
Default character production uses the shared local VoxStage service through
standard-library HTTP, so the Greia process needs no MLX environment of its own.
On a workstation where the shared tool is installed:

```bash
voxstage start
python3 tools/greia_voice.py doctor
```

The active registry is `assets/audio/characters/canonical/v0.2/manifest.toml`.
A fresh local VoxStage library is populated lazily from the repository's exact
reviewed references and transcripts. Saved IDs are never overwritten. `doctor`
is non-mutating and does not download weights, import voices or synthesize.

For initial shared-tool installation, read `SETUP.md`, the in-house tools catalog
and the VoxStage skill. Do not install/download another model stack silently.
VoxStage's synthesis host currently uses Apple Silicon/MLX. Default HTTP-client
readiness is portable; native pedagogical availability remains host-specific.
Do not configure a cloud or remote host: the adapter permits loopback only.

All four released languages (English, Italian, French and Spanish) use native
text plus language direction. There is no hard VoxCPM2 language selector, so
pronunciation and identity still need listening review.

## Speech routing

VoxStage uses editable acting defaults from `character_delivery.json` for all six
characters. Override a cue with `--delivery-prompt 'Quiet, curious and reassuring.'`
or the JSON `delivery_prompt` field in batch/service requests. The provider sends
language and acting as direction, separately from exact spoken words, and records
the actual prompt in receipt generation parameters. Explicit acting prompts are
unsupported by the retained Chatterbox/native adapters and are rejected.

For the owner-authorized existing-corpus replacement (2026-10-19), use
`tools/regenerate_voice_corpus.py` and
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`: inventory, resolve scripts,
run/resume with progress, inspect status, recover/retry and restore originals.
This operation preserves deterministic isolated letters/syllables and installs
new recordings as listening-pending; it does not grant audio acceptance.

| Kind | Current route |
|---|---|
| `character_dialogue` | selected cloned character, all six speakers |
| `shared_character_utterance` | selected cloned character, all six speakers |
| `dani_system_speech` | selected Dani cloned master; compatible existing kind |
| `pedagogical_speech` | independent deterministic native/system pronunciation |

Pedagogical requests use speaker `pedagogical` or `system`, never a character.
Existing accepted runtime recordings and receipts remain unchanged. Every new
result remains `human_review=PENDING`, even when its master is accepted.

## Retained alternative and lifecycle

```bash
# Release the default worker's model before loading another large model.
voxstage unload
python3 tools/greia_voice.py doctor --character-provider chatterbox
python3 tools/greia_voice.py serve --character-provider chatterbox
```

`GREIA_VOICE_CHARACTER_PROVIDER=chatterbox` selects the alternative for repository
producers. Explicit CLI choices win. There is no automatic backend fallback.
Chatterbox's optional tested dependencies remain in
`tools/greia_voice_requirements_mlx.txt`; its setup and field guide are linked
from `docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md`.

Default endpoint: `http://127.0.0.1:8791`; override with a loopback origin in
`GREIA_VOXSTAGE_URL`. `VOXSTAGE_API_KEY` is optional environment-only service auth.
`GREIA_VOXSTAGE_TIMEOUT` bounds job waits (default 1,800 seconds; 1–7,200). A
reported job timeout does not cancel shared inference: inspect the job ID before
submitting more work. POSTs are never automatically repeated.

Greia closes only its own temporary audio; VoxStage owns its shared warm worker.
Use `voxstage unload` when finished to release model memory, or `voxstage stop`
to drain and stop the service. Greia client shutdown never stops other projects'
worker. The warm Greia server selects its provider at startup; `request` uses that
choice and has a separate `--timeout` (default 3,600 seconds, 1–7,200).

# Usage

## Check readiness

```bash
python tools/greia_voice.py doctor
```

## Generate one character line

```bash
python tools/greia_voice.py generate \
  --speaker leo \
  --kind character_dialogue \
  --locale it \
  --text "Guardiamo con calma." \
  --cue-id presenter.hint \
  --output ./tmp/voice-review/presenter-hint.ogg
```

## Generate a syllable deterministically

```bash
python tools/greia_voice.py generate \
  --speaker pedagogical \
  --kind pedagogical_speech \
  --locale it \
  --text "ma" \
  --cue-id phonics.ma \
  --verification off \
  --output ./tmp/voice-review/phonics-ma.wav
```

Do not ask a canonical character to speak a pronunciation-authoritative teaching target merely to preserve mascot identity.

## Generate Dani with the selected cloned master

```bash
python tools/greia_voice.py generate \
  --speaker dani \
  --kind dani_system_speech \
  --locale it \
  --text "Schema completato!" \
  --cue-id dani.complete \
  --output ./tmp/voice-review/dani-complete.ogg
```

## Batch generation

Create newline-delimited JSON (`.jsonl`), one semantic request per line:

```json
{"speaker":"tito","kind":"character_dialogue","locale":"it","text":"Guarda cosa abbiamo scoperto!","cue_id":"curiosity.discovery","output":"./tmp/voice-review/discovery.ogg"}
{"speaker":"pedagogical","kind":"pedagogical_speech","locale":"it","text":"to","cue_id":"phonics.to","output":"./tmp/voice-review/to.wav","verification":"off"}
```

Run:

```bash
python tools/greia_voice.py batch --input requests.jsonl
```

The model is kept warm for the batch and generation stays single-worker.

## Warm service for agents

When an agent will request many clips over time:

```bash
python tools/greia_voice.py serve
```

Then from another shell:

```bash
python tools/greia_voice.py request \
  --speaker lilli \
  --kind character_dialogue \
  --locale en \
  --text "Let's try something new!" \
  --cue-id presenter.try-new \
  --output ./tmp/voice-review/try-new.ogg
```

Stop cleanly:

```bash
python tools/greia_voice.py shutdown
```

The service binds only to localhost. Do not expose it on the LAN.

---

# Output and review

Every successful generation produces:

```text
<requested audio file>
<requested audio file>.receipt.json
```

The receipt records the semantic request, provider, voice/reference identity, generation parameters, optional ASR result, attempts and output hash.

Machine success is not acceptance. Before integrating audio, a human must listen for:

- exact words and correct locale;
- correct character identity when applicable;
- correct pronunciation/stress;
- no repeated or invented sounds;
- no clipped start/end or unwanted tail;
- appropriate delivery and small-speaker intelligibility.

For pedagogical speech, exact educational pronunciation is the primary gate.

Existing owner-accepted audio does **not** need to be regenerated just because its historical script predates this engine.

---

# Rule for new Greia work

For new voice production:

```text
Activity / OS / Encyclopedia author
    -> semantic request
    -> tools/greia_voice.py
    -> provider chosen by VoiceEngine
    -> review asset + receipt
    -> human listening
    -> owning workflow integrates only accepted audio
```

Do not add another Activity-specific VoxStage/Chatterbox/system-TTS/Whisper implementation. Legacy `generate_*_audio.py` scripts are historical compatibility/evidence unless and until converted into thin semantic request producers.
`doctor` exits 0 when the selected character provider, all active references and
FFmpeg are ready; otherwise it exits 2. Optional verifier/retained-alternative
status is reported independently. `selected_character_provider` records the
effective choice; `default_character_provider` records the built-in `voxstage` default.
