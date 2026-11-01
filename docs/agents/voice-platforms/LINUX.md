# Greia voice authoring on Linux — VoxCPM2 + Parakeet v3

Install Python **3.12** and FFmpeg in your distro. On Debian/Ubuntu, install
\`git\`, \`ffmpeg\`, \`python3.12\` and its \`venv\` support using the packages
available in your release (or an operator-managed Python 3.12).
You do **not** need eSpeak or a Mac/MLX worker.

From the Greia checkout root in a Linux shell:

\`\`\`sh
voice_home="\${XDG_DATA_HOME:-$HOME/.local/share}/greia/voice-production"
mkdir -p "$voice_home"
python3.12 -m venv "$voice_home/venv"
voice_python="$voice_home/venv/bin/python"
"$voice_python" -m pip install --upgrade pip
"$voice_python" -m pip install voxcpm soundfile 'onnx-asr[cpu,hub]' huggingface-hub
"$voice_python" tools/setup_voice_models.py
"$voice_python" tools/greia_voice.py doctor
\`\`\`

Both models are downloaded by the one-time setup command, into the user-local
cache, not Git. \`doctor\` must show both the VoxCPM2 provider and
Parakeet v3 ONNX verifier available.

\`\`\`sh
mkdir -p "$voice_home/review"
"$voice_python" tools/greia_voice.py generate \
  --speaker leo --kind character_dialogue --locale it \
  --text 'Guardiamo con calma.' --cue-id sample.leo \
  --output "$voice_home/review/leo.wav"
\`\`\`

The same VoxCPM2/Parakeet models run on macOS and Windows. VoxCPM2 runs on
CPU without NVIDIA; with a compatible CUDA PyTorch environment, set
\`GREIA_VOXCPM_DEVICE=cuda\` to select the GPU. Parakeet review runs by default,
but the user can choose \`--verification off\`. Human acceptance is final.

No live Linux inference or voice-identity comparison has been certified in
this source-only commit.
