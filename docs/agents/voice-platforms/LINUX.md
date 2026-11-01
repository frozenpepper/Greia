# Greia voice production on Linux

**Scope:** Linux authoring workstation, not the running Greia child OS. [Common skill](../../../skills/greia-voice-production/SKILL.md) · [platform index](../GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md).

## Native pedagogical speech (no Mac required)

You need Python 3.11+, \`ffmpeg\` and \`espeak-ng\`. On Debian/Ubuntu, after explicit operator approval to install packages:

```sh
sudo apt-get install python3 ffmpeg espeak-ng
python3 tools/greia_voice.py doctor
mkdir -p "$HOME/greia-voice-review"
python3 tools/greia_voice.py generate --speaker pedagogical \
  --kind pedagogical_speech --locale it --text 'ma' \
  --cue-id example.phonics.ma --verification off \
  --output "$HOME/greia-voice-review/ma.wav"
```

\`espeak-ng --voices=it\` displays installed voice choices for the requested locale. Greia invokes eSpeak NG via \`--stdin\` without a shell, so text does not become command-line flags. Local system voices sound different from the canonical cloned presenter voices: evaluate their suitability by listening, especially for phonics.

\`doctor\` may exit 2 solely because the selected default character provider is unavailable. Check the native eSpeak provider row and FFmpeg instead. This does **not** block local \`pedagogical_speech\` using \`--verification off\`. \`--verification auto\` performs ASR if available, otherwise records \`NOT_RUN\`; it never blocks generation. \`--verification required\` is the explicit strict mode.

## Canonical character speech via the Mac service

The current selected VoxStage/VoxCPM2 and optional MLX Parakeet implementations run on a prepared Apple Silicon workstation; no Linux-local cloned-character worker is bundled in Greia. A separate approved Mac can expose the **Greia semantic service** through SSH loopback forwarding. On the Mac:

```sh
voxstage start
"$HOME/Library/Application Support/Greia/voice-production/venv/bin/python" tools/greia_voice.py serve
```

On Linux, in another terminal (replace with authorized SSH details):

```sh
ssh -N -L 43841:127.0.0.1:43841 user@mac-host
```

On Linux, in the Greia repo while that SSH session is running:

```sh
python3 tools/greia_voice.py request --speaker leo --kind character_dialogue \
  --locale it --text 'Guardiamo con calma.' --cue-id example.leo \
  --verification off --output /tmp/greia-voice-review/leo.wav
```

The output WAV/OGG and receipt are written on the **Mac**. Copy them to a review station explicitly when needed. Use \`--verification auto\` if advisory ASR on the Mac is desirable; do not make it a prerequisite for owner acceptance.

Every new clip goes to review staging. Never replace accepted recordings as part of platform setup. Linux backend was inspected at source level, not certified on the full range of Linux distributions.
