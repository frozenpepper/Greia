from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SpeechKind(str, Enum):
    CHARACTER_DIALOGUE = "character_dialogue"
    SHARED_CHARACTER_UTTERANCE = "shared_character_utterance"
    PEDAGOGICAL_SPEECH = "pedagogical_speech"
    DANI_SYSTEM_SPEECH = "dani_system_speech"


class VerificationMode(str, Enum):
    AUTO = "auto"
    OFF = "off"
    REQUIRED = "required"


class VerificationDisposition(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    NOT_RUN = "NOT_RUN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class GenerationDisposition(str, Enum):
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVIEW_REQUIRED_ASR_WARNING = "REVIEW_REQUIRED_ASR_WARNING"
    UNAVAILABLE = "UNAVAILABLE"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class VoiceRequest:
    speaker: str
    kind: SpeechKind
    locale: str
    text: str
    cue_id: str | None = None
    output: Path | None = None
    verification: VerificationMode = VerificationMode.AUTO
    max_attempts: int = 3
    delivery_prompt: str = ""
    ignore_accents: bool = True
    short_text_mode: str = "auto"
    short_text_max_words: int = 4
    short_text_max_alnum: int | None = None

    def __post_init__(self) -> None:
        if self.short_text_mode not in {"auto", "off", "on"}:
            raise ValueError("short_text_mode must be auto, off or on")
        if type(self.short_text_max_words) is not int or not 1 <= self.short_text_max_words <= 20:
            raise ValueError("short_text_max_words must be an integer between 1 and 20")
        if self.short_text_max_alnum is not None and (
                type(self.short_text_max_alnum) is not int or not 1 <= self.short_text_max_alnum <= 1000):
            raise ValueError("short_text_max_alnum must be null or an integer between 1 and 1000")
        if not isinstance(self.ignore_accents, bool):
            raise ValueError("ignore_accents must be a boolean")
        speaker = self.speaker.strip().lower()
        locale = self.locale.strip().lower().replace("_", "-")
        text = self.text.strip()
        if not speaker:
            raise ValueError("speaker must not be empty")
        if not locale:
            raise ValueError("locale must not be empty")
        if not text:
            raise ValueError("text must not be empty")
        if not 1 <= self.max_attempts <= 4:
            raise ValueError("max_attempts must be between 1 and 4")
        object.__setattr__(self, "speaker", speaker)
        object.__setattr__(self, "locale", locale)
        object.__setattr__(self, "text", text)
        if not isinstance(self.delivery_prompt, str) or len(self.delivery_prompt) > 2000:
            raise ValueError("delivery_prompt must be a string of at most 2000 characters")
        object.__setattr__(self, "delivery_prompt", self.delivery_prompt.strip())

    @property
    def language(self) -> str:
        return self.locale.split("-", 1)[0]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["kind"] = self.kind.value
        payload["verification"] = self.verification.value
        payload["output"] = str(self.output) if self.output is not None else None
        return payload


@dataclass(frozen=True)
class VoiceProfile:
    """Canonical character identity and its portable authoring reference."""

    character: str
    voice_id: str
    production: str
    purpose: str
    anchor_path: Path | None = None
    anchor_sha256: str | None = None
    anchor_transcript: str = ""
    voxstage_voice_id: str = ""


@dataclass(frozen=True)
class ProviderStatus:
    provider_id: str
    available: bool
    detail: str
    capabilities: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerificationResult:
    disposition: VerificationDisposition
    verifier_id: str
    transcript: str | None = None
    score: float | None = None
    detail: str = ""
    model_id: str | None = None
    model_revision: str | None = None
    ignore_accents: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["disposition"] = self.disposition.value
        return payload


@dataclass(frozen=True)
class GeneratedTake:
    provider_id: str
    temporary_wav: Path
    sample_rate_hz: int
    generation_parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationResult:
    disposition: GenerationDisposition
    request: VoiceRequest
    provider_id: str | None
    output_path: Path | None
    receipt_path: Path | None
    verification: VerificationResult
    attempts: int
    detail: str = ""
    evidence_dir: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "disposition": self.disposition.value,
            "request": self.request.to_dict(),
            "provider_id": self.provider_id,
            "output_path": str(self.output_path) if self.output_path else None,
            "receipt_path": str(self.receipt_path) if self.receipt_path else None,
            "verification": self.verification.to_dict(),
            "attempts": self.attempts,
            "detail": self.detail,
            "evidence_dir": str(self.evidence_dir) if self.evidence_dir else None,
        }
