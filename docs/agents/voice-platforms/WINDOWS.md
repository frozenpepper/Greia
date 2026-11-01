# Greia voice production on Windows

**Scope:** Windows PowerShell 5.1 or a PowerShell environment providing `System.Speech`; Python 3.11+; FFmpeg. [Common skill](../../../skills/greia-voice-production/SKILL.md) · [platform index](../GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md).

## Native pedagogical speech (no Mac required)

From the Greia repository root in **PowerShell**:

```powershell
py -3 --version
ffmpeg -version
py -3 tools/greia_voice.py doctor
New-Item -ItemType Directory -Force "$env:TEMP\greia-voice-review" | Out-Null
py -3 tools/greia_voice.py generate --speaker pedagogical --kind pedagogical_speech --locale en --text "A" --cue-id example.phonics.a --verification off --output "$env:TEMP\greia-voice-review\a.wav"
```

Install Python and FFmpeg separately through your preferred trusted packages if absent. The Windows adapter uses PowerShell's `System.Speech.Synthesis.SpeechSynthesizer` and a **locally installed SAPI voice matching the requested language**. If the language voice is absent, it reports a generation error rather than switching language silently. Install the appropriate Windows language/speech voices before retrying.

**PowerShell quoting:** use a single complete command line as above, or PowerShell's backtick for continuation; Unix backslashes are not PowerShell line continuation characters. The engine sends spoken content as encoded data to PowerShell, never interpolates it as command code. Never call PowerShell TTS directly from Activity authoring.

`doctor` may exit 2 because its default **character** engine (VoxStage) is not running locally; inspect the native provider row separately. That does not prevent `--verification off` local pedagogical generation. `--verification auto` also generates with `NOT_RUN` when MLX Parakeet is not present, leaving a clip for the user to listen to. The verifier is optional; `--verification required` is an explicit strict mode.

## Canonical Greia character voices

The current canonical cloned voices and MLX Parakeet implementation do **not** run as a bundled Windows-local backend. To request the exact canonical characters, use the **already prepared Mac** VoiceEngine service through an SSH local forward (only with that host owner's permission).

On the Mac, in the Greia repo:

```sh
voxstage start
"$HOME/Library/Application Support/Greia/voice-production/venv/bin/python" tools/greia_voice.py serve
```

On Windows, in a separate PowerShell terminal (substitute a real, authorized SSH user and Mac name):

```powershell
ssh -N -L 43841:127.0.0.1:43841 user@mac-host
```

In a second Windows PowerShell terminal, from the Greia repo:

```powershell
py -3 tools/greia_voice.py request --speaker leo --kind character_dialogue --locale en --text "We can try again." --cue-id example.leo --verification off --output /tmp/greia-voice-review/leo.wav
```

The SSH tunnel forwards only the loopback semantic service, not the raw MLX worker. The `--output` path is **on the Mac**, not Windows; copy the review result and receipt with `scp` or another authorized transfer if listening locally. Use `request` only while the Mac service is running. For character synthesis, the output still uses the selected canonical master, not SAPI. `--verification auto` offers advisory ASR when the Mac has cached weights; `off` never uses ASR.

Review output by listening. Do not promote or overwrite existing accepted files automatically. Speech on Windows has not been exercised on a real Windows workstation as part of this source-only change.
