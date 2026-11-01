# Greia voice authoring on macOS — VoxCPM2 + Parakeet v3

Use **Python 3.12**, Git and FFmpeg. Homebrew example:
`brew install python@3.12 git ffmpeg`.
New voice authoring uses the same VoxCPM2 model and Parakeet v3 as Windows
and Linux, without requiring any alternate OS-specific speech generator.

From the Greia repo root:

```sh
voice_home="$HOME/Library/Application Support/Greia/voice-production"
mkdir -p "$voice_home"
python3.12 -m venv "$voice_home/venv"
voice_python="$voice_home/venv/bin/python"
"$voice_python" -m pip install --upgrade pip
"$voice_python" -m pip install voxcpm soundfile 'onnx-asr[cpu,hub]' huggingface-hub
"$voice_python" tools/setup_voice_models.py
"$voice_python" tools/greia_voice.py doctor
```

The model setup downloads both VoxCPM2 and Parakeet v3. On Apple Silicon,
PyTorch's MPS backend is selectable automatically; if it fails, an operator
may force `GREIA_VOXCPM_DEVICE=cpu` for a slower common baseline. On Intel
Macs the CPU route is available.

```sh
mkdir -p "$voice_home/review"
"$voice_python" tools/greia_voice.py generate --speaker leo \
  --kind character_dialogue --locale it --text 'Guardiamo con calma.' \
  --cue-id sample.leo --output "$voice_home/review/leo.wav"
```

Parakeet runs by default. An operator may set `--verification off`;
listening remains the decision point.

**Existing Mac workflow:** the original owner's already-configured shared
VoxStage process runs a quantized MLX implementation of **VoxCPM2**.
It remains selectable explicitly using
`--character-provider voxstage` when the operator chooses to reuse it.
Neither that historical backend nor its reference audio or receipts are
changed by this portable setup. Do not switch models for any platform.
