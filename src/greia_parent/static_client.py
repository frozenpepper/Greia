from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import unquote


MAX_STATIC_ASSET_BYTES = 512 * 1024
_ALLOWED_TOP_LEVEL = frozenset({"styles", "src", "assets"})
_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
}


@dataclass(frozen=True, slots=True)
class StaticClientAsset:
    content_type: str
    body: bytes
    cache_control: str = "no-cache"


class ParentStaticClient:
    """Bounded read-only loader for the pinned Parent App runtime (source: ``parent-app/``)."""

    def __init__(self, root: Path):
        self.root = root

    @classmethod
    def from_environment(cls) -> "ParentStaticClient":
        return cls(
            Path(
                os.environ.get(
                    "GREIA_PARENT_WEB_ROOT",
                    "/usr/share/greia-parent-app",
                )
            )
        )

    def read(self, request_path: str) -> StaticClientAsset | None:
        relative = self._relative_path(request_path)
        if relative is None:
            return None
        try:
            if self.root.is_symlink():
                return None
            root = self.root.resolve(strict=True)
            unresolved = root
            for part in relative.parts:
                unresolved = unresolved / part
                if unresolved.is_symlink():
                    return None
            candidate = unresolved.resolve(strict=True)
            candidate.relative_to(root)
            if not candidate.is_file():
                return None
            stat = candidate.stat()
            if stat.st_size < 0 or stat.st_size > MAX_STATIC_ASSET_BYTES:
                return None
            content_type = _CONTENT_TYPES.get(candidate.suffix.lower())
            if content_type is None:
                return None
            body = candidate.read_bytes()
        except (FileNotFoundError, OSError, RuntimeError, ValueError):
            return None
        if len(body) > MAX_STATIC_ASSET_BYTES:
            return None
        return StaticClientAsset(content_type=content_type, body=body)

    @staticmethod
    def _relative_path(request_path: str) -> Path | None:
        if request_path == "/":
            return Path("index.html")
        if not isinstance(request_path, str) or not request_path.startswith("/"):
            return None
        decoded = unquote(request_path)
        if "\\" in decoded or "\x00" in decoded:
            return None
        parts = PurePosixPath(decoded.lstrip("/")).parts
        if not parts or parts[0] not in _ALLOWED_TOP_LEVEL:
            return None
        if any(part in {"", ".", ".."} or part.startswith(".") for part in parts):
            return None
        if Path(parts[-1]).suffix.lower() not in _CONTENT_TYPES:
            return None
        return Path(*parts)
