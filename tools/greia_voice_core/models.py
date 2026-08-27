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
    max_attempts: int = 2

    def __post_init__(self) -> None:
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
    character: str
    voice_id: str
    production: str
    purpose: str
    anchor_path: Path | None = None
    anchor_sha256: str | None = None


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
        }
