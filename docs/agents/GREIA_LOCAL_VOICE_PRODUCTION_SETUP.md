# Greia Local Voice Production Setup for Agents

**Status:** canonical authoring-workstation setup / Voice Studio
**Reviewed:** 2026-10-22
**Not shipped to:** child devices or Activity packages

## 1. Readiness and canonical boundary

Read `SETUP.md`, `skills/greia-voice-production/SKILL.md`,
`tools/greia_voice_core/README.md`, the voice architecture and voice design docs.
All content production enters through `tools/greia_voice.py` / `VoiceEngine`.
VoxStage, Chatterbox, native TTS, Whisper and FFmpeg are provider details.

The active v0.3 registry uses owner-selected Dani, Momo and Tito masters and
retains Lilli, Leo and Flash's exact v0.2 identities and bytes. The default
provider is **VoxCPM2 through the existing shared local VoxStage worker**.
Chatterbox is retained explicitly. Pedagogical pronunciation remains the
independent native/system route.

**Corpus replacement follow-up:** the owner subsequently requested regeneration
of existing Activity/system speech except deterministic isolated letters and
syllables. The tool/agent work order is
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`; it uses the installed worker,
external backups and the same VoiceEngine. Acting defaults live in
`tools/greia_voice_core/character_delivery.json`; `--delivery-prompt` or the
batch/service `delivery_prompt` field overrides one recording. Exact direction
is retained in receipts. Fresh corpus output remains pending human listening.

Start the installed shared service, then probe Greia:

```bash
voxstage start
voice_python="$HOME/Library/Application Support/Greia/voice-production/venv/bin/python"
"$voice_python" tools/greia_voice.py doctor
```

`doctor` checks active reference bytes, packaging and provider/verifier readiness;
it never imports saved voices, generates, loads weights or downloads a model.
Read every provider status: the intentionally unavailable native adapter and an
optional unavailable verifier are not the same as an unavailable selected
character provider. A successful process exit is not audio acceptance.

### Fresh-clone limitation (especially for outside language contributors)

The commands below assume the **shared VoxStage command and VoxCPM2 model** already exist. VoxStage lives in the separate **private** repository `frozenpepper/voxstage` (see its `README.md`, `skills/voxstage/SKILL.md` and `scripts/install.py`). Its installer reuses an already prepared Apple-Silicon Python environment, so it is not a tested generic clean-Mac dependency bootstrap. Access to private Greia does not imply VoxStage repository access. VoxStage and the optional Takeboard listening tool are external shared utilities, not installed by the Greia repository. Parakeet-TDT v3 verification additionally requires a prepared compatible MLX Python environment and the **exact cached pinned model snapshot**; a different clean Mac does not inherit the owner's cached models. `doctor` must be read for both provider and verifier readiness. This document currently **does not supply a verified fresh-host VoxStage/Takeboard installer**, so do not promise new volunteers a complete ready-to-run studio from a clean clone. Arrange approved tool access and a reproducible install procedure separately before calling that setup ready.

For new-language planning and the release boundary, start with `docs/development/ADD_A_GREIA_LANGUAGE.md`.

## 2. Default workstation dependencies

The Greia HTTP client needs Python 3.11+ and the repository's canonical v0.3
assets. FFmpeg packages the generated WAV into Greia's 22,050 Hz mono WAV/OGG.
The shared VoxStage tool owns its Apple-Silicon MLX runtime/model installation,
saved library and serialized worker. Greia does not install/import a second
VoxCPM2 stack. Use the in-house tools catalog and VoxStage skill for shared-tool
setup. Do not download a multi-GB stack merely because optional speech might be
useful. Installation/first weight download still requires owner authorization.

Models, venvs, caches, rejected takes and service state stay outside Git.
`GREIA_VOICE_HOME` selects Greia's review/lock state; it is independent of
VoxStage's data root. A fresh local VoxStage library is initialized lazily from
the reviewed repository references and exact transcripts. Conflicting existing
voice IDs are reported, never overwritten or silently replaced.

The transport defaults to `http://127.0.0.1:8791`. `GREIA_VOXSTAGE_URL` accepts
another loopback HTTP origin only. `VOXSTAGE_API_KEY`, if configured by the
operator, stays environment-only. There is no cloud fallback.

## 3. Model and request lifecycle

VoxStage owns one warm serialized worker for every client/project. Closing a
Greia client must not shut down another project's model. When production is
finished, the operator frees its memory with:

```bash
voxstage unload
```

`voxstage stop` finishes the current recording and stops, preserving the other
queued jobs for next start; it does not drain them. Do not run another raw model worker
beside it. `GREIA_VOXSTAGE_TIMEOUT` bounds a Greia wait for a shared job (default
1,800 seconds; 1–7,200). A timeout/uncertain response does not cancel the external
job. Inspect the reported VoxStage job ID before resubmitting; Greia does not
repeat POSTs automatically. Receipts retain job IDs, seeds, reference and model
identity for recovery.

For repeated semantic work:

```bash
python3 tools/greia_voice.py serve
# Another shell: send a normal semantic request to that server.
python3 tools/greia_voice.py request --speaker leo --kind character_dialogue \
  --locale it --text "Guardiamo con calma." --cue-id smoke.leo \
  --output /tmp/greia-voice-review/leo.ogg --timeout 3600
python3 tools/greia_voice.py shutdown
```

The server selects its provider at startup. The client has a ten-second
connection deadline and separate response timeout (`--timeout`, default 3,600
seconds, 1–7,200). That client timeout also does not cancel server work.
Known queues use `batch --input requests.jsonl` with one warm shared worker.

## 4. Retained Chatterbox alternative

Select deliberately; unavailable VoxStage never silently chooses this path:

```bash
voxstage unload
python3 tools/greia_voice.py doctor --character-provider chatterbox
python3 tools/greia_voice.py generate --character-provider chatterbox \
  --speaker leo --kind character_dialogue --locale it \
  --text "Guardiamo con calma." --cue-id legacy.smoke \
  --output /tmp/greia-voice-review/chatterbox-leo.ogg
```

`GREIA_VOICE_CHARACTER_PROVIDER=chatterbox` selects it for repository producers;
an explicit CLI option wins. Chatterbox uses the active v0.3 references, including
Dani, and keeps the existing in-process warm-model/cleanup mechanisms. It requires
its optional Apple-Silicon environment and `tools/greia_voice_requirements_mlx.txt`.
Read its provider-specific field guide only when diagnosing that alternative.

Optional, owner-authorized installation, with state outside Git:

```bash
export GREIA_VOICE_HOME="${HOME}/Library/Application Support/Greia/voice-production"
export GREIA_VOICE_CACHE="${HOME}/Library/Caches/Greia/voice-production"
export HF_HOME="${GREIA_VOICE_CACHE}/huggingface"
export HF_HUB_DISABLE_TELEMETRY=1
mkdir -p "${GREIA_VOICE_HOME}" "${GREIA_VOICE_CACHE}" "${HF_HOME}"
```

### Preferred install with `uv`

```bash
uv venv "${GREIA_VOICE_HOME}/venv" --python 3.12
uv pip install --python "${GREIA_VOICE_HOME}/venv/bin/python" \
  -r tools/greia_voice_requirements_mlx.txt
```

### Standard venv/pip alternative

```bash
python3.12 -m venv "${GREIA_VOICE_HOME}/venv"
"${GREIA_VOICE_HOME}/venv/bin/python" -m pip install -U pip
"${GREIA_VOICE_HOME}/venv/bin/python" -m pip install \
  -r tools/greia_voice_requirements_mlx.txt
```

Install FFmpeg if missing and owner-authorized:

```bash
brew install ffmpeg
```

Activate and probe:

```bash
source "${GREIA_VOICE_HOME}/venv/bin/activate"
python3 tools/greia_voice.py doctor
```

For default cloned-character production, require the selected VoxStage provider,
active references and FFmpeg. Chatterbox is an explicit alternative; native macOS
is needed for pedagogical pronunciation. Current new-generation **Parakeet-TDT v3** ASR needs the prepared verifier
environment and cached pinned model, independently of synthesis readiness.

Whisper generation/review/cutting resolves cached weights offline and cannot
bootstrap a missing model. Configure any missing verifier or alternate-provider
model separately with owner authorization; normal production is not an install
step. `doctor` is not permission to trigger downloads.

### Existing Whisper review environment (verified 2026-10-21)

The prepared interpreter is
`~/Library/Application Support/Greia/voice-production/venv/bin/python`.
Use it explicitly for `regenerate_voice_corpus.py review`; do not use the global
Anaconda Python, whose installed NumPy/Numba combination fails Whisper import.
The prepared environment has working mlx-whisper and cached Base weights for
**historical corpus review** (that lane's default as of 2026-10-22);
Tiny remains cached for historical comparisons. New VoiceEngine synthesis
verification instead uses the pinned Parakeet-TDT v3 stack.
No packages or weights need installing. Follow the exact pilot/full commands in
`docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md`. Availability in one interpreter
does not describe other environments on the machine.

## 5. Host and semantic boundaries

The default HTTP client is portable, but the shared synthesis host currently
requires Apple Silicon/MLX. No remote/cloud configuration is implied. Native
pedagogical production currently requires macOS; Linux/Windows report that
independent provider gap truthfully. Never bypass the engine with host TTS.

Dani now clones `greia.dani.v3`; `dani_system_speech` remains a compatible kind,
and ordinary Dani `character_dialogue` is also supported. Native Dani profiles
are retained for historical compatibility, not default character production.
Pedagogical requests still use `pedagogical`/`system` and native pronunciation.
Native host profiles and rates are implementation details in `native.py`.

Optional Whisper is advisory and may be unavailable independently of default
synthesis. Its first use must not silently install/download a missing model.
Use `--verification off` for a synthesis-only smoke; report that ASR did not run.
No ASR result establishes pronunciation or human acceptance.

## 6. Smoke and review

Generate into review staging, never over shipping audio:

```bash
python3 tools/greia_voice.py generate --speaker dani --kind dani_system_speech \
  --locale fr --text "Motif détecté !" --cue-id smoke.dani \
  --verification off --output /tmp/greia-voice-review/dani-fr.wav
python3 tools/greia_voice.py generate --speaker pedagogical --kind pedagogical_speech \
  --locale it --text "ma" --cue-id smoke.phonics.ma \
  --verification off --output /tmp/greia-voice-review/ma.wav
```

New output remains `human_review=PENDING`. Listen for words, locale, character,
pronunciation, clipping/tails, delivery and small-speaker intelligibility. The
selected reference's acceptance never accepts a future recording.

The original v0.2 baseline contained 180 accepted reactions and 12 introductions.
The owner-authorized v3 corpus and priority retakes subsequently replaced selected
rows with listening-pending audio in the same catalogue. Consult current per-cue
receipts/manifest; do not infer acceptance from the v0.2 directory name. A registry
change alone does not authorize replacing other accepted recordings. Runtime
resolver/product integration and new missing cues remain separate work.

Report source SHA, doctor statuses, exact input, review paths, provider/job/voice
receipts, result counts, ASR scope, human acceptance and remaining blockers.
Provider-free tests, live authoring synthesis, listening and Greia runtime or
physical playback are distinct evidence lanes.

`doctor` exits 0 when the selected character provider, all active references and
FFmpeg are ready; otherwise it exits 2. Optional verifier/retained-alternative
status is reported independently. `selected_character_provider` records the
effective choice; `default_character_provider` records the built-in `voxstage` default.
