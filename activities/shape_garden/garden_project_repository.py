"""Profile-private persistence for Shape Garden creative projects."""
from __future__ import annotations

import hashlib

if __package__:
    from .garden_content import (
        BACKGROUND_PREFIX,
        MAX_BACKGROUND_BYTES,
        MAX_SHAPES,
        STORAGE_KEY,
    )
    from .garden_project_model import GardenProject, GardenStamp
else:  # pragma: no cover - direct script fallback
    from garden_content import (
        BACKGROUND_PREFIX,
        MAX_BACKGROUND_BYTES,
        MAX_SHAPES,
        STORAGE_KEY,
    )
    from garden_project_model import GardenProject, GardenStamp


class GardenProjectError(RuntimeError):
    pass


class GardenProjectRepository:
    """Persist one bounded editable garden with immutable backdrop snapshots."""

    def __init__(self, storage) -> None:
        self.storage = storage

    @staticmethod
    def _background_name(digest: str) -> str:
        return f"{BACKGROUND_PREFIX}/{digest}.png"

    def load(self) -> GardenProject:
        raw = self.storage.kv_get(STORAGE_KEY, None)
        if raw is None:
            return GardenProject()
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            raise GardenProjectError("unsupported garden project")
        items = raw.get("stamps", [])
        if not isinstance(items, list) or len(items) > MAX_SHAPES:
            raise GardenProjectError("invalid garden stamp collection")
        try:
            digest = raw.get("background_sha256")
            if digest is not None and not isinstance(digest, str):
                raise ValueError("invalid background digest")
            return GardenProject(
                tuple(GardenStamp.from_raw(item) for item in items),
                digest,
            )
        except ValueError as exc:
            raise GardenProjectError("invalid garden project data") from exc

    def load_background(self, project: GardenProject) -> bytes | None:
        digest = project.background_sha256
        if digest is None:
            return None
        try:
            payload = self.storage.file_read(self._background_name(digest))
        except RuntimeError as exc:
            raise GardenProjectError("garden background missing") from exc
        if (
            not isinstance(payload, bytes)
            or not payload
            or len(payload) > MAX_BACKGROUND_BYTES
            or hashlib.sha256(payload).hexdigest() != digest
        ):
            raise GardenProjectError("garden background failed integrity check")
        return payload

    def save(
        self,
        project: GardenProject,
        *,
        replacement_background_png: bytes | None = None,
    ) -> GardenProject:
        previous = self.load()
        digest = project.background_sha256
        if replacement_background_png is not None:
            payload = replacement_background_png
            if (
                not isinstance(payload, bytes)
                or not payload
                or len(payload) > MAX_BACKGROUND_BYTES
            ):
                raise GardenProjectError("garden background exceeds bounds")
            digest = hashlib.sha256(payload).hexdigest()
            try:
                self.storage.file_write_atomic(
                    self._background_name(digest), payload
                )
            except RuntimeError as exc:
                raise GardenProjectError("garden background write failed") from exc

        committed = GardenProject(project.stamps, digest)
        try:
            self.storage.kv_set(
                STORAGE_KEY,
                {
                    "schema_version": 1,
                    "stamps": [stamp.as_raw() for stamp in committed.stamps],
                    "background_sha256": committed.background_sha256,
                },
            )
        except RuntimeError as exc:
            self._cleanup(previous.background_sha256)
            raise GardenProjectError("garden project write failed") from exc

        self._cleanup(committed.background_sha256)
        return committed

    def save_export(self, payload: bytes) -> str:
        """Write one replace-in-place PNG source for trusted publication."""
        if (
            not isinstance(payload, bytes)
            or not payload
            or len(payload) > MAX_BACKGROUND_BYTES
        ):
            raise GardenProjectError("garden export exceeds bounds")
        name = "garden/shared.png"
        try:
            self.storage.file_write_atomic(name, payload)
        except RuntimeError as exc:
            raise GardenProjectError("garden export write failed") from exc
        return name

    def _cleanup(self, keep_digest: str | None) -> None:
        keep = self._background_name(keep_digest) if keep_digest else None
        try:
            names = self.storage.file_list(prefix=BACKGROUND_PREFIX)
        except RuntimeError:
            return
        # Project creation itself is bounded; a small cleanup cap also bounds
        # repair work if old/crashed versions left unreachable files.
        for name in names[:16]:
            if name != keep:
                try:
                    self.storage.file_delete(name)
                except RuntimeError:
                    pass


__all__ = ["GardenProjectError", "GardenProjectRepository"]
