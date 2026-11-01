# Greia voice workstation setup — all operating systems

**One TTS model:** `openbmb/VoxCPM2` (same VoxCPM2 family used by the
original Mac VoxStage service).

**One ASR/review model:** NVIDIA `parakeet-tdt-0.6b-v3` (cross-platform
ONNX export loaded via `onnx-asr`; MLX receipts from previous work remain
historical evidence).

Choose the [Windows](voice-platforms/WINDOWS.md),
[macOS](voice-platforms/MACOS.md), or
[Linux](voice-platforms/LINUX.md) guide for interpreter, FFmpeg and shell
commands. These are **authoring-machine requirements**, not packages installed
on Greia devices or inside Activities.

## Install both together

On each host, install Python 3.12, FFmpeg and Git using the native installer/
package manager, then create a voice-only virtual environment **outside Git**.
Install `voxcpm`, `soundfile`, `onnx-asr[cpu,hub]` and `huggingface-hub`.
From the Greia repo root (with the prepared environment Python):

```text
python tools/setup_voice_models.py
python tools/greia_voice.py doctor
```

The first command is an **explicit** model download that may use several GB.
The owner must authorize installing packages/weights on their workstation.
It caches VoxCPM2 in Hugging Face's model cache, and Parakeet ONNX under
`GREIA_VOICE_HOME/models/parakeet-tdt-v3`. Nothing is committed to the repo.
The second command is non-generative and does **not** download any model. It
reports the selected VoxCPM2 provider, installed canonical Greia references,
FFmpeg and Parakeet readiness separately.

The default VoxCPM2 PyTorch execution picks `CUDA → MPS → CPU`.
`GREIA_VOXCPM_DEVICE` can force `cpu`, `cuda`, or `mps` when an operator
needs that. The provider disables optional `torch.compile` for a conservative
cross-platform baseline; this does not change the model. NVIDIA GPU acceleration
requires a compatible PyTorch/CUDA installation. CPU can be slow, but does not
require another model.

## Generate / review

```text
python tools/greia_voice.py generate --speaker leo --kind character_dialogue --locale it --text "Guardiamo con calma." --output <review-folder>/leo.wav
```

Both models are installed by default, and `--verification auto` runs
Parakeet on generated audio. User can add `--verification off` to skip ASR or
`--verification required` to request strict checking. Whether ASR says PASS,
WARN, or NOT_RUN, the user accepts a take after listening; `auto` and
`off` do not block its delivery due to ASR.

Voice identity comes from Greia's existing immutable canonical reference WAVs
and scripts. **Do not regenerate, rewrite, remove or overwrite** the hundreds
of owner-reviewed recordings or their receipts while setting up a machine.
New candidates go to external staging with listening-pending receipts.

The original Mac workstation used VoxStage + MLX's quantized VoxCPM2; this
cross-platform workflow uses the same VoxCPM2 model family through PyTorch.
Different inference implementations may not be sample-identical. The
historical `voxstage` provider remains explicitly available but is not
required for Windows or Linux. No host-native SAPI/eSpeak/macOS say substitution.

Upstream references: [VoxCPM installation](https://voxcpm.readthedocs.io/en/latest/installation.html),
[VoxCPM cloning API](https://voxcpm.readthedocs.io/en/latest/usage_guide.html),
[onnx-asr installation](https://istupakov.github.io/onnx-asr/installation/),
[onnx-asr model usage](https://istupakov.github.io/onnx-asr/usage/).
