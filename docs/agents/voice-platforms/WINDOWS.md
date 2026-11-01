# Greia voice authoring on Windows — VoxCPM2 + Parakeet v3

Install **Python 3.12**, Git and FFmpeg on the Windows host, with `git`,
`ffmpeg` and `py -3.12` usable from **PowerShell**. No Mac machine,
VoxStage server, SAPI voice, MOSS, or eSpeak is required.

Open PowerShell in the Greia repo root. Install the same model packages as
Linux/macOS, in a separate Windows user-local environment:

```powershell
$homeDir = Join-Path $env:LOCALAPPDATA "Greia\voice-production"
New-Item -ItemType Directory -Path $homeDir -Force | Out-Null
py -3.12 -m venv (Join-Path $homeDir "venv")
$python = Join-Path $homeDir "venv\Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install voxcpm soundfile 'onnx-asr[cpu,hub]' huggingface-hub
& $python tools/setup_voice_models.py
& $python tools/greia_voice.py doctor
```

The setup command downloads **VoxCPM2** and **Parakeet-TDT v3** once.
Verify that `character_production_ready` and `verifier.available` are
both true. First run downloads may take several GB; do not start them
without operator approval.

Example generation, with Parakeet automatically reporting transcription:

```powershell
$review = Join-Path $homeDir "review"
New-Item -ItemType Directory -Path $review -Force | Out-Null
& $python tools/greia_voice.py generate --speaker leo --kind character_dialogue --locale en --text "We can try again." --cue-id sample.leo --output (Join-Path $review "leo.wav")
```

User can add `--verification off` to omit Parakeet without changing VoxCPM2;
listen before accepting. If Windows encounters Triton/`torch.compile`
issues, Greia's PyTorch provider explicitly uses `optimize=False`
as suggested by upstream. For CUDA, install compatible NVIDIA drivers and
a CUDA-enabled PyTorch build, then optionally set
`$env:GREIA_VOXCPM_DEVICE = "cuda"`. CPU is always a fallback.

This is a source-level workflow; live Windows model installation and audio
quality have not been certified by Greia maintainers.
