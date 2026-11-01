#!/usr/bin/env python3
"""Explicit one-time download of VoxCPM2 and Parakeet-TDT v3 for authoring.

No models are downloaded during doctor, generate, batch, or review.
This installs only models; pip dependencies are installed separately per OS.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from greia_voice_core.paths import voice_home


def main() -> int:
    parser = argparse.ArgumentParser(description="Install both VoxCPM2 TTS and Parakeet v3 ASR")
    parser.add_argument("--parakeet-dir", type=Path,
                        default=voice_home() / "models" / "parakeet-tdt-v3")
    args = parser.parse_args()

    from huggingface_hub import snapshot_download
    import onnx_asr

    print("Downloading the shared VoxCPM2 model to the Hugging Face cache...", flush=True)
    vox_path = snapshot_download("openbmb/VoxCPM2")
    print(f"VoxCPM2: {vox_path}", flush=True)

    target = args.parakeet_dir.expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    print(f"Downloading/loading Parakeet-TDT 0.6B v3 ONNX to {target}...", flush=True)
    onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3", str(target))
    print("Both VoxCPM2 and Parakeet v3 are installed. Run greia_voice.py doctor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
