"""Cross-platform VoxCPM2 renderer; preserves Greia's canonical reference WAVs.

The same OpenBMB VoxCPM2 model runs through PyTorch (CUDA, MPS or CPU).
Legacy VoxStage/MLX remains a selectable wrapper for historical workflows.
Weights are provisioned explicitly by tools/setup_voice_models.py, never here.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import os
import tempfile

from .models import GeneratedTake, ProviderStatus, SpeechKind, VoiceProfile, VoiceRequest
from .providers import VoiceProvider, VoiceProviderError
from .registry import VoiceRegistry


class VoxCPM2TorchProvider(VoiceProvider):
    provider_id = "voxcpm2-torch"
    model_id = "openbmb/VoxCPM2"
    supports_delivery_prompt = True

    def __init__(self) -> None:
        self._model = None

    @staticmethod
    def _cached_snapshot() -> Path:
        from huggingface_hub import snapshot_download
        return Path(snapshot_download("openbmb/VoxCPM2", local_files_only=True))

    def supports(self, request: VoiceRequest, profile: VoiceProfile | None) -> bool:
        if request.kind is SpeechKind.PEDAGOGICAL_SPEECH:
            return request.speaker in {"pedagogical", "system"}
        return (
            request.kind in {
                SpeechKind.CHARACTER_DIALOGUE,
                SpeechKind.SHARED_CHARACTER_UTTERANCE,
                SpeechKind.DANI_SYSTEM_SPEECH,
            }
            and profile is not None
            and profile.production == "cloned_reference"
        )

    def probe(self) -> ProviderStatus:
        try:
            if importlib.util.find_spec("voxcpm") is None:
                raise ImportError("voxcpm is not installed")
            if importlib.util.find_spec("soundfile") is None:
                raise ImportError("soundfile is not installed")
            snapshot = self._cached_snapshot()
            if not snapshot.is_dir():
                raise FileNotFoundError("VoxCPM2 snapshot directory is missing")
            return ProviderStatus(
                self.provider_id, True,
                f"{self.model_id} cached at {snapshot}; PyTorch selects CUDA/MPS/CPU",
                capabilities=tuple(kind.value for kind in SpeechKind),
            )
        except Exception as exc:
            return ProviderStatus(
                self.provider_id, False,
                f"VoxCPM2 not prepared: {exc}; follow the platform-specific setup",
            )

    @staticmethod
    def _reference(profile: VoiceProfile | None) -> VoiceProfile:
        if profile is not None:
            return profile
        # Pedagogical lines have no character actor; use the SAME VoxCPM2 model
        # with an existing canonical reference rather than a host-native TTS.
        root = Path(__file__).resolve().parents[2]
        registry = VoiceRegistry.load(root)
        leo = registry.get("leo")
        registry.verify_anchor(leo)
        return leo

    def _load(self):
        if self._model is None:
            from voxcpm import VoxCPM
            self._model = VoxCPM.from_pretrained(
                str(self._cached_snapshot()),
                device=os.environ.get("GREIA_VOXCPM_DEVICE", "auto"),
                optimize=False,  # avoids torch.compile/Triton incompatibilities on Windows
                load_denoiser=False,
            )
        return self._model

    def generate(self, request: VoiceRequest, profile: VoiceProfile | None) -> GeneratedTake:
        if not self.supports(request, profile):
            raise VoiceProviderError("VoxCPM2 request needs a supported speech kind and speaker")
        status = self.probe()
        if not status.available:
            raise VoiceProviderError(status.detail)
        reference = self._reference(profile)
        if reference.anchor_path is None or not reference.anchor_transcript:
            raise VoiceProviderError("canonical voice reference audio/transcript missing")
        if profile is None:
            # No raw host voices: exact Leo reference is the pedagogical voice.
            VoiceRegistry.load(Path(__file__).resolve().parents[2]).verify_anchor(reference)
        try:
            model = self._load()
            if request.delivery_prompt:
                # Reference-only mode supports performance direction; hi-fi mode
                # ignores instructions, so use timbre cloning for directed lines.
                kwargs = {
                    "text": f"({request.delivery_prompt}){request.text}",
                    "reference_wav_path": str(reference.anchor_path),
                }
            else:
                # Recommended high-fidelity same-identity cloning.
                kwargs = {
                    "text": request.text,
                    "reference_wav_path": str(reference.anchor_path),
                    "prompt_wav_path": str(reference.anchor_path),
                    "prompt_text": reference.anchor_transcript,
                }
            waveform = model.generate(
                **kwargs, cfg_value=2.0, inference_timesteps=10,
                normalize=False, denoise=False,
            )
            import soundfile as sf
            fd, name = tempfile.mkstemp(prefix="greia-voxcpm2-", suffix=".wav")
            os.close(fd)
            target = Path(name)
            sample_rate = int(model.tts_model.sample_rate)
            try:
                sf.write(str(target), waveform, sample_rate, subtype="PCM_16")
            except BaseException:
                target.unlink(missing_ok=True)
                raise
            return GeneratedTake(
                provider_id=self.provider_id,
                temporary_wav=target,
                sample_rate_hz=sample_rate,
                generation_parameters={
                    "model": self.model_id,
                    "runtime": "pytorch",
                    "voice": reference.voice_id,
                    "reference_sha256": reference.anchor_sha256,
                    "synthesis_text": kwargs["text"],
                    "delivery_prompt": request.delivery_prompt,
                },
            )
        except VoiceProviderError:
            raise
        except Exception as exc:
            raise VoiceProviderError(f"VoxCPM2 generation failed: {exc}") from exc

    def close(self) -> None:
        self._model = None
