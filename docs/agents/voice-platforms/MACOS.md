# Greia voice production on macOS

**Scope:** authoring workstation, not the child device. [Common skill](../../../skills/greia-voice-production/SKILL.md) · [platform index](../GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md).

## Prepare and inspect

Install Python 3.11+ and FFmpeg, using your preferred package manager. For example, on a Homebrew machine:

```sh
brew install python ffmpeg
python3 tools/greia_voice.py doctor
```

From the Greia repository root, this prints separate readiness for the default character provider, native system voice, FFmpeg and optional Parakeet. A fresh Mac does **not** automatically have the separate VoxStage worker, selected voice IDs, local MLX stack or cached verifier. Do not download heavy models or incur service charges without owner approval.

For the already prepared owner Apple Silicon environment:

```sh
voice_python="$HOME/Library/Application Support/Greia/voice-production/venv/bin/python"
voxstage start
"$voice_python" tools/greia_voice.py doctor
```

The cloned Dani/Lilli/Leo/Flash/Momo/Tito voice backend currently uses the Apple Silicon VoxStage/VoxCPM2 service; the Chatterbox MLX option is also Apple Silicon. Use the existing prepared setup as in [the canonical workstation guide](../GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md).

## Produce and listen

New audio always goes to an **external staging folder**. Never replace accepted recordings merely to test setup.

```sh
mkdir -p /tmp/greia-voice-review
python3 tools/greia_voice.py generate --speaker pedagogical --kind pedagogical_speech \
  --locale it --text 'ma' --cue-id example.phonics.ma \
  --verification off --output /tmp/greia-voice-review/ma.wav

python3 tools/greia_voice.py generate --speaker leo --kind character_dialogue \
  --locale it --text 'Guardiamo con calma.' --cue-id example.leo \
  --verification auto --output /tmp/greia-voice-review/leo.wav
```

The second command needs an already configured character worker. \`off\` generates without ASR; \`auto\` uses ASR only if already available and never rejects audio just because ASR disagrees; \`required\` explicitly opts into strict ASR/retries and, for short character lines, the carrier extraction method. All outputs remain human-listening pending regardless of machine results.

The macOS native \`say\` and \`afconvert\` tools are used **inside** VoiceEngine for pedagogical speech, not directly by Activity generators. Native voice identity and pronunciation vary with OS-installed voices. An unavailable native voice is a host setup issue; install/select a suitable language voice in macOS system settings, then retry. Language names used for EN/IT/ES/FR default to Samantha/Alice/Mónica/Thomas. Optional \`GREIA_VOICE_PEDAGOGICAL_VOICE_IT\` etc selects an existing local voice.

For serialized batches use \`python3 tools/greia_voice.py batch --input requests.jsonl\`. For remote clients start \`python3 tools/greia_voice.py serve\` on the Mac and use an **explicit authorized** SSH tunnel as in the Windows/Linux guides. It listens only on loopback by default. Stop only the session you own; do not restart a shared worker because another project may have queued jobs.

Check the generated WAV/OGG and its sibling \`*.receipt.json\`. Only the human owner decides whether to accept or replace audio.
