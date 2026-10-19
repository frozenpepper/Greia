"""VoxCPM2 character synthesis through the shared local VoxStage service."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import secrets
import tempfile
from urllib.parse import quote
import uuid

from .models import GeneratedTake, ProviderStatus, SpeechKind, VoiceProfile, VoiceRequest
from .providers import VoiceProvider, VoiceProviderError
from .voxstage_client import VoxStageClient, VoxStageServiceError


class VoxStageProvider(VoiceProvider):
    """Adapt semantic Greia requests to one serialized VoxStage worker.

    The repository reference and transcript establish identity on fresh machines.
    Existing saved IDs are reused only when they name that same reference. Import
    is lazy and never replaces a saved voice. Provider close leaves the shared
    service/model alone; its operator owns warm-model unloading.
    """

    provider_id = "voxstage-voxcpm2"
    character_kinds = frozenset({
        SpeechKind.CHARACTER_DIALOGUE,
        SpeechKind.SHARED_CHARACTER_UTTERANCE,
        SpeechKind.DANI_SYSTEM_SPEECH,
    })

    def __init__(self, client: VoxStageClient | None = None) -> None:
        self.client = client or VoxStageClient()

    def supports(self, request: VoiceRequest, profile: VoiceProfile | None) -> bool:
        return request.kind in self.character_kinds and profile is not None and profile.production == "cloned_reference"

    def probe(self) -> ProviderStatus:
        try:
            health = self.client.json("/health")
            capabilities = self.client.json("/v1/capabilities")
            backend = health.get("backend", {})
            if not isinstance(backend, dict):
                raise VoiceProviderError("service returned malformed backend information")
            if health.get("status") != "ok" or "reference" not in capabilities.get("modes", []):
                raise VoiceProviderError("service does not advertise healthy reference cloning")
            if "voxcpm2" not in str(backend.get("model", "")).lower():
                raise VoiceProviderError("service is not running the selected VoxCPM2 model family")
            return ProviderStatus(self.provider_id, True, f"{self.client.base_url}; {backend.get('model')}; shared serialized worker", tuple(sorted(k.value for k in self.character_kinds)))
        except VoiceProviderError as exc:
            return ProviderStatus(self.provider_id, False, str(exc))

    def _ensure_voice(self, profile: VoiceProfile) -> str:
        voice_id = profile.voxstage_voice_id
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", voice_id) or not profile.anchor_path or not profile.anchor_transcript:
            raise VoiceProviderError("VoxStage requires a registered voice ID, reference WAV and exact transcript")
        if hashlib.sha256(profile.anchor_path.read_bytes()).hexdigest() != profile.anchor_sha256:
            raise VoiceProviderError(f"Canonical reference differs for {profile.character}")
        try:
            saved = self.client.json(f"/v1/voices/{quote(voice_id, safe='')}")
        except VoxStageServiceError as exc:
            if exc.status not in {400, 404} or "Unknown voice:" not in str(exc):
                raise
            saved = self.client.json("/v1/voices/import", {
                "id": voice_id,
                "path": str(profile.anchor_path.resolve()),
                "transcript": profile.anchor_transcript,
                "description": profile.purpose,
            })
        if saved.get("reference_sha256") != profile.anchor_sha256 or saved.get("transcript") != profile.anchor_transcript:
            raise VoiceProviderError(f"VoxStage saved voice {voice_id} does not match the selected Greia master/transcript; no reference was replaced")
        return voice_id

    def generate(self, request: VoiceRequest, profile: VoiceProfile | None) -> GeneratedTake:
        if profile is None or not self.supports(request, profile):
            raise VoiceProviderError("VoxStage character speech requires a cloned canonical profile")
        # The language is performance direction, not a dedicated backend selector.
        language = {"en": "English", "it": "Italian", "fr": "French", "es": "Spanish"}.get(request.language)
        if language is None:
            raise VoiceProviderError(f"VoxStage language direction is not configured for {request.language}")
        voice_id = self._ensure_voice(profile)
        payload = {
            "title": f"Greia {profile.character} {request.language}",
            "voice": voice_id,
            "seed": secrets.randbits(32),
            "takes": 1,
            "max_chars": 240,
            "settings": {"steps": 10, "cfg": 2.0, "max_tokens": 300},
            "segments": [{"id": "speech", "text": request.text, "delivery": f"Speak naturally in {language}", "pause_after_ms": 0}],
        }
        key = f"greia-{uuid.uuid4().hex}"
        try:
            submitted = self.client.json("/v1/jobs", payload, key=key)
        except VoxStageServiceError as exc:
            raise VoiceProviderError(f"{exc}; uncertain submission key {key}. Inspect VoxStage jobs before resubmitting") from exc
        job_id = str(submitted.get("id", ""))
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", job_id):
            raise VoiceProviderError(f"VoxStage returned no usable job identity; submission key {key}; inspect existing jobs before resubmitting")
        job = self.client.wait_job(job_id)
        recordings = job.get("results", [])
        if job.get("status") != "completed" or not recordings or any(
            r.get("spec", {}).get("voice") != voice_id
            or r.get("spec", {}).get("reference_sha256") != profile.anchor_sha256
            or r.get("spec", {}).get("mode") != "reference"
            for r in recordings
        ):
            raise VoiceProviderError(f"VoxStage job {job_id} has no matching completed reference recordings")
        # Length splitting may change whitespace at chunk edges, but must never
        # drop a sentence or return another cue with the same speaker identity.
        returned_text = "".join(str(r["spec"].get("text", "")) for r in recordings)
        if "".join(returned_text.split()) != "".join(request.text.split()):
            raise VoiceProviderError(f"VoxStage job {job_id} does not contain the complete requested text")
        mixes = job.get("mixes", [])
        if len(mixes) != 1 or mixes[0].get("file") != "mix-take-01.wav":
            raise VoiceProviderError(f"VoxStage job {job_id} did not return its complete speech mix")
        descriptor, name = tempfile.mkstemp(prefix="greia-voxstage-", suffix=".wav")
        os.close(descriptor)
        path = Path(name)
        try:
            self.client.download(job_id, mixes[0]["file"], path)
            if hashlib.sha256(path.read_bytes()).hexdigest() != mixes[0].get("sha256"):
                raise VoiceProviderError(f"Incomplete audio transfer for VoxStage job {job_id}")
            return GeneratedTake(self.provider_id, path, 48000, {
                "job_id": job_id,
                "idempotency_key": key,
                "backend": job.get("backend", {}),
                "voxstage_voice_id": voice_id,
                "reference_sha256": profile.anchor_sha256,
                "settings": payload["settings"],
                "script_seed": payload["seed"],
                "language_direction": language,
                "mode": "reference",
                "recordings": [{"file": r["file"], "seed": r["spec"]["seed"], "sha256": r["sha256"], "generation": r.get("generation", {})} for r in recordings],
            })
        except BaseException:
            path.unlink(missing_ok=True)
            raise
