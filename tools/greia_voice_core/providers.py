from __future__ import annotations

from abc import ABC, abstractmethod
import gc
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from .models import GeneratedTake, ProviderStatus, SpeechKind, VoiceProfile, VoiceRequest
from .native import (
    MACOS_DANI_PROFILES,
    MACOS_PEDAGOGICAL_PROFILES,
    NativeSpeechProfile,
    pedagogical_synthesis_text,
)


class VoiceProviderError(RuntimeError):
    pass


class VoiceProvider(ABC):
    provider_id: str

    @abstractmethod
    def supports(self, request: VoiceRequest, profile: VoiceProfile | None) -> bool:
        raise NotImplementedError

    @abstractmethod
    def probe(self) -> ProviderStatus:
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: VoiceRequest, profile: VoiceProfile | None) -> GeneratedTake:
        raise NotImplementedError

    def close(self) -> None:
        return None


class ChatterboxMLXProvider(VoiceProvider):
    provider_id = "chatterbox-mlx-multilingual-v3"
    model_id = "mlx-community/chatterbox-multilingual-v3"

    def __init__(self) -> None:
        self._model: Any | None = None
        self._model_load_count = 0

    def supports(self, request: VoiceRequest, profile: VoiceProfile | None) -> bool:
        return (
            request.kind is SpeechKind.CHARACTER_DIALOGUE
            and profile is not None
            and profile.production == "cloned_reference"
        )

    def probe(self) -> ProviderStatus:
        try:
            import mlx.core  # noqa: F401
            from mlx_audio.tts import load  # noqa: F401
            import soundfile  # noqa: F401
        except Exception as exc:
            return ProviderStatus(self.provider_id, False, f"MLX voice stack unavailable: {exc}")
        return ProviderStatus(
            self.provider_id,
            True,
            self.model_id,
            capabilities=(SpeechKind.CHARACTER_DIALOGUE.value,),
        )

    def _load_model(self) -> Any:
        if self._model is None:
            from mlx_audio.tts import load
            self._model = load(self.model_id)
            self._model_load_count += 1
        return self._model

    @staticmethod
    def _token_budget(text: str) -> int:
        words = len(text.split())
        if words <= 2:
            return 45
        if words <= 4:
            return 65
        if words <= 12:
            return 160
        # Long factual/narrative lines need headroom; keep a bounded ceiling.
        return min(700, max(180, words * 24))

    @staticmethod
    def _trim_audio(audio: Any, sample_rate: int, short: bool) -> Any:
        import numpy as np
        samples = np.asarray(audio, dtype=np.float32)
        frame_len = max(1, int(0.010 * sample_rate))
        frame_count = len(samples) // frame_len
        if frame_count == 0:
            return samples
        frames = samples[: frame_count * frame_len].reshape(frame_count, frame_len)
        rms = np.sqrt(np.mean(frames ** 2, axis=1))
        peak = float(np.max(rms))
        if peak < 1e-4:
            return samples
        threshold = max(0.005 if not short else 0.010, peak * (10 ** ((-38 if not short else -35) / 20.0)))
        active = np.where(rms > threshold)[0]
        if not len(active):
            return samples

        start_frame = int(active[0])
        end_frame = int(active[-1])
        if short:
            end_frame = start_frame
            for idx in active[1:]:
                if int(idx) - end_frame > 12:
                    break
                end_frame = int(idx)
            lead_ms, trail_ms = 25.0, 40.0
        else:
            lead_ms, trail_ms = 40.0, 180.0

        start = max(0, int((start_frame * 0.010 - lead_ms / 1000.0) * sample_rate))
        end = min(len(samples), int(((end_frame + 1) * 0.010 + trail_ms / 1000.0) * sample_rate))
        return samples[start:end]

    def generate(self, request: VoiceRequest, profile: VoiceProfile | None) -> GeneratedTake:
        if profile is None or profile.anchor_path is None:
            raise VoiceProviderError("Chatterbox request requires a canonical cloning reference")
        status = self.probe()
        if not status.available:
            raise VoiceProviderError(status.detail)

        import mlx.core as mx
        import numpy as np
        import soundfile as sf

        max_tokens = self._token_budget(request.text)
        try:
            try:
                model = self._load_model()
                result = next(
                    model.generate(
                        text=request.text,
                        ref_audio=str(profile.anchor_path),
                        lang_code=request.language,
                        max_new_tokens=max_tokens,
                        verbose=False,
                    )
                )
                sample_rate = int(result.sample_rate)
                cleaned = self._trim_audio(
                    np.asarray(result.audio),
                    sample_rate,
                    short=len(request.text.split()) <= 4,
                )
                fd, tmp_name = tempfile.mkstemp(prefix="greia-voice-", suffix=".wav")
                os.close(fd)
                tmp_path = Path(tmp_name)
                sf.write(str(tmp_path), cleaned, sample_rate, subtype="PCM_16")
                return GeneratedTake(
                    provider_id=self.provider_id,
                    temporary_wav=tmp_path,
                    sample_rate_hz=sample_rate,
                    generation_parameters={
                        "model_id": self.model_id,
                        "max_new_tokens": max_tokens,
                        "lang_code": request.language,
                        "model_load_count": self._model_load_count,
                    },
                )
            except Exception as exc:
                raise VoiceProviderError(f"Chatterbox generation failed: {exc}") from exc
        finally:
            # MLX autoregressive generation retains Metal buffers. Clear after every
            # utterance while keeping model weights alive in this provider instance.
            mx.clear_cache()
            gc.collect()

    def close(self) -> None:
        if self._model is not None:
            try:
                import mlx.core as mx
                mx.clear_cache()
            except Exception:
                pass
        self._model = None
        gc.collect()


class MacOSNativeSpeechProvider(VoiceProvider):
    provider_id = "macos-native-say"

    def supports(self, request: VoiceRequest, profile: VoiceProfile | None) -> bool:
        return sys.platform == "darwin" and request.kind in {
            SpeechKind.PEDAGOGICAL_SPEECH,
            SpeechKind.DANI_SYSTEM_SPEECH,
        }

    def probe(self) -> ProviderStatus:
        available = sys.platform == "darwin" and shutil.which("say") and shutil.which("afconvert")
        return ProviderStatus(
            self.provider_id,
            bool(available),
            "macOS say + afconvert" if available else "requires macOS say and afconvert",
            capabilities=(
                SpeechKind.PEDAGOGICAL_SPEECH.value,
                SpeechKind.DANI_SYSTEM_SPEECH.value,
            ),
        )

    @staticmethod
    def _profile(request: VoiceRequest) -> NativeSpeechProfile:
        profiles = (
            MACOS_DANI_PROFILES
            if request.kind is SpeechKind.DANI_SYSTEM_SPEECH
            else MACOS_PEDAGOGICAL_PROFILES
        )
        try:
            profile = profiles[request.language]
        except KeyError as exc:
            raise VoiceProviderError(
                f"no macOS native speech profile for language {request.language}"
            ) from exc

        env_name = (
            f"GREIA_VOICE_DANI_VOICE_{request.language.upper()}"
            if request.kind is SpeechKind.DANI_SYSTEM_SPEECH
            else f"GREIA_VOICE_PEDAGOGICAL_VOICE_{request.language.upper()}"
        )
        override = os.environ.get(env_name, "").strip()
        return NativeSpeechProfile(voice=override or profile.voice, rate_wpm=profile.rate_wpm)

    def generate(self, request: VoiceRequest, profile: VoiceProfile | None) -> GeneratedTake:
        status = self.probe()
        if not status.available:
            raise VoiceProviderError(status.detail)
        native = self._profile(request)
        synthesis_text = (
            pedagogical_synthesis_text(request.text, request.language)
            if request.kind is SpeechKind.PEDAGOGICAL_SPEECH
            else request.text
        )
        with tempfile.TemporaryDirectory(prefix="greia-native-speech-") as temp_dir:
            temp = Path(temp_dir)
            aiff = temp / "speech.aiff"
            wav = temp / "speech.wav"
            try:
                subprocess.run(
                    [
                        "say", "-v", native.voice, "-r", str(native.rate_wpm),
                        synthesis_text, "-o", str(aiff),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                subprocess.run(
                    [
                        "afconvert", "-f", "WAVE", "-d", "LEI16@22050", "-c", "1",
                        str(aiff), str(wav),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as exc:
                detail = (exc.stderr or exc.stdout or str(exc)).strip()
                raise VoiceProviderError(f"macOS native speech generation failed: {detail}") from exc
            fd, tmp_name = tempfile.mkstemp(prefix="greia-voice-native-", suffix=".wav")
            os.close(fd)
            tmp_path = Path(tmp_name)
            shutil.copy2(wav, tmp_path)
        return GeneratedTake(
            provider_id=self.provider_id,
            temporary_wav=tmp_path,
            sample_rate_hz=22050,
            generation_parameters={
                "voice": native.voice,
                "rate_wpm": native.rate_wpm,
                "synthesis_text": synthesis_text,
            },
        )


class UnsupportedNativeSpeechProvider(VoiceProvider):
    provider_id = "native-system-unavailable"

    def supports(self, request: VoiceRequest, profile: VoiceProfile | None) -> bool:
        return request.kind in {
            SpeechKind.PEDAGOGICAL_SPEECH,
            SpeechKind.DANI_SYSTEM_SPEECH,
        }

    def probe(self) -> ProviderStatus:
        return ProviderStatus(
            self.provider_id,
            False,
            "no implemented native/system speech adapter for this host",
        )

    def generate(self, request: VoiceRequest, profile: VoiceProfile | None) -> GeneratedTake:
        raise VoiceProviderError(self.probe().detail)
