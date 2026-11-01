---
name: greia-voice-production
description: Author, generate, listen to, review and integrate Greia prerecorded speech on macOS, Windows or Linux using VoxCPM2 and Parakeet-TDT v3.
---

# Greia Voice Production (Windows / macOS / Linux)

**Canonical authoring workflow, 2026-11-01.** This is an authoring-time skill,
not child-device runtime TTS. It applies to new and replacement Activity,
launcher, shared-library, canonical-character, Dani and pedagogical lines.

## Start here

1. [Common workstation setup](../../docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md).
2. Pick the host: [Windows](../../docs/agents/voice-platforms/WINDOWS.md),
   [macOS](../../docs/agents/voice-platforms/MACOS.md), or
   [Linux](../../docs/agents/voice-platforms/LINUX.md).
3. Install **both models** during setup, then run
   `python tools/greia_voice.py doctor` with the prepared Python.
4. Generate review candidates through **only**
   `tools/greia_voice.py generate` / `batch` / `serve` / `request`.
5. Let the owner listen and decide acceptance. Never promote or replace accepted
   recordings just because generation or ASR succeeded.

## Same models on all three platforms

| Task | Canonical model | Execution |
|---|---|---|
| Speech generation, including six canonical character references | **OpenBMB VoxCPM2** (`openbmb/VoxCPM2`) | Portable PyTorch on CPU, CUDA or MPS; host-specific *runtime*, same model family |
| Automatic speech review | **NVIDIA Parakeet-TDT 0.6B v3** | Portable ONNX export via `onnx-asr` on Windows, macOS and Linux |

VoxStage on the owner's existing Mac is a *separately selectable* wrapper around
VoxCPM2, using the existing MLX/8-bit model build. Use
`--character-provider voxstage` only when deliberately reusing that installed
Mac service. Other historical Chatterbox and macOS system-voice routes are not
cross-platform defaults and **must never be silently substituted**.

Same model **family** does not promise bit-identical samples across different
quantizations or PyTorch/MLX execution, so listen to an example on each host.
The canonical Greia source voice masters and exact transcripts in
`assets/audio/characters/canonical/v0.3/manifest.toml` remain unchanged. Do
not regenerate them when preparing a different operating system.

## Verification is available by default, not an acceptance gate

Both VoxCPM2 and Parakeet are installed by the normal setup. Request behavior:

- `--verification auto` (**default**): run Parakeet on the generated audio.
  If missing or uncertain, save the recording anyway with an honest
  `NOT_RUN` / `WARN` result for listening. No automatic retry for ASR warnings.
- `--verification off`: explicitly skip Parakeet for that request; generate
  speech and create a receipt normally.
- `--verification required`: user-chosen strict automated verification;
  an unavailable verifier or a negative verification may prevent publishing
  a take; legacy short-carrier extraction can run on this path.

Only a human accepts speech: meaning, exact words, accent, character identity,
acting, intelligibility, pronunciation and tails. Parakeet is a useful second
opinion, **not a licensing, installation, or audio acceptance authority**.
Record actual verifier identity; don't relabel historical MLX-Parakeet/Whisper
receipts or claim they were ONNX observations.

## Generate

Run commands from the Greia repo root with the prepared platform Python.
Use an external review directory (Windows PowerShell examples use Windows
paths; these are POSIX examples).

```sh
python tools/greia_voice.py doctor
python tools/greia_voice.py generate \
  --speaker leo --kind character_dialogue --locale it \
  --text "Guardiamo con calma." --cue-id presenter.hint \
  --output "$HOME/greia-voice-review/hint-it.wav"

python tools/greia_voice.py generate \
  --speaker pedagogical --kind pedagogical_speech --locale it \
  --text "ma" --cue-id phonics.ma \
  --output "$HOME/greia-voice-review/ma-it.wav"
```

Requests need a semantic speaker, kind, locale, exact reviewed speech, and
ideally stable cue ID. Kinds: `character_dialogue`,
`shared_character_utterance`, `pedagogical_speech`,
`dani_system_speech`. Six canonical speakers: Dani, Lilli, Leo, Flash, Tito,
Momo. Pedagogical speech uses the same VoxCPM2 TTS model and an existing Leo
reference, not host-native TTS. Human review is especially important for
isolated phonemes and syllables; ASR is not pronunciation authority.

Dani uses canonical cloned identity, not the host's system voice. Normal
speaker reference cloning is hi-fi (registered reference+transcript). If
`--delivery-prompt` specifies acting, VoxCPM2 uses reference-only controllable
cloning; the effective direction and model identity belong in the receipt.

A process exit, WAV/OGG decode, valid hash or model-generated transcript
does not authorize publishing new audio. Never overwrite owner-approved
committed production WAV/OGG files or receipts outside an explicit authorized
content replacement. Keep model caches, venvs, rejected takes and review output
outside the Git checkout. Do not download models implicitly in `doctor` or
during a recording.

## Dedicated operations

- [VoiceEngine reference](../../tools/greia_voice_core/README.md) — CLI and
  request/receipt behavior
- [Automated review](../../docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md) —
  historical corpus reports and new audio screening
- [Shared utterance catalog](../../docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md)
- [Language expansion skill](../greia-language-expansion/SKILL.md)
- [Activity voice authoring](../greia-activity-authoring/VOICE_GENERATION.md)
- [Corpus operations](../../docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md) —
  versioned owner-authorized replacement only
- [Voice architecture](../../docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md)

Existing frozen corpus producers/receipts may pin historical verifiers or
special extraction/comparison policies. Do not rewrite a registered plan,
reset generation budgets, assume a historical run was ONNX-based, or restart
held experimental producers merely because workstation setup has changed.
