from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import tomllib

from .models import VoiceProfile


class VoiceRegistryError(RuntimeError):
    pass


@dataclass(frozen=True)
class VoiceRegistry:
    project_root: Path
    registry_version: str
    profiles: dict[str, VoiceProfile]

    @classmethod
    def load(cls, project_root: Path) -> "VoiceRegistry":
        manifest_path = (
            project_root
            / "assets"
            / "audio"
            / "characters"
            / "canonical"
            / "v0.1"
            / "manifest.toml"
        )
        if not manifest_path.is_file():
            raise VoiceRegistryError(f"canonical voice manifest missing: {manifest_path}")
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)

        profiles: dict[str, VoiceProfile] = {}
        anchor_root = manifest_path.parent
        for row in data.get("voice", []):
            character = str(row.get("character", "")).strip().lower()
            if not character:
                raise VoiceRegistryError("voice manifest contains a row without character")
            if character in profiles:
                raise VoiceRegistryError(f"duplicate voice profile for {character}")
            production_anchor = str(row.get("production_anchor", "")).strip()
            profiles[character] = VoiceProfile(
                character=character,
                voice_id=str(row.get("voice_id", "")).strip(),
                production=str(row.get("production", "")).strip(),
                purpose=str(row.get("purpose", "")).strip(),
                anchor_path=(anchor_root / production_anchor) if production_anchor else None,
                anchor_sha256=str(row.get("anchor_sha256", "")).strip() or None,
            )
        return cls(
            project_root=project_root,
            registry_version=str(data.get("registry_version", "unknown")),
            profiles=profiles,
        )

    def get(self, speaker: str) -> VoiceProfile:
        key = speaker.strip().lower()
        try:
            return self.profiles[key]
        except KeyError as exc:
            raise VoiceRegistryError(f"unknown canonical speaker: {speaker}") from exc

    def verify_anchor(self, profile: VoiceProfile) -> None:
        if profile.anchor_path is None:
            return
        if not profile.anchor_path.is_file():
            raise VoiceRegistryError(
                f"canonical reference missing for {profile.character}: {profile.anchor_path}"
            )
        if not profile.anchor_sha256:
            raise VoiceRegistryError(f"reference hash missing for {profile.character}")
        digest = hashlib.sha256(profile.anchor_path.read_bytes()).hexdigest()
        if digest != profile.anchor_sha256:
            raise VoiceRegistryError(
                f"canonical reference hash mismatch for {profile.character}: "
                f"expected {profile.anchor_sha256}, got {digest}"
            )
