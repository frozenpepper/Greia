from __future__ import annotations

import bisect
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import unicodedata
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .ui_core import BoundedCache

try:
    import regex as _regex
except ImportError:  # pragma: no cover - shipping Greia images install python3-regex
    _regex = None

# Greia default interface typeface: Nunito Sans (SIL OFL 1.1).
# See GREIA_VISUAL_STYLE_GUIDE.md section 3 and
# build/trust/nunito-sans-2.3.2.provenance.
#
# Normal fonts are loaded once per (role, size) and cached; consumers never
# open raw font paths. Emoji are a platform fallback, not Greia system icons:
# Noto Color Emoji is rasterized through Pillow's embedded-color path and then
# composed into ordinary Pygame surfaces. Missing/corrupt fonts degrade safely
# instead of taking down the child session.

DEFAULT_EMOJI_FONT = Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf")
# Debian 12/bookworm's Noto Color Emoji package is CBDT/CBLC with a 109-pixel
# native bitmap strike. Greia renders that strike and scales the RGBA result to
# the requested UI size. Keep this version-specific fact behind this service.
DEFAULT_EMOJI_NATIVE_STRIKE_PX = 109

if _regex is not None:
    _GRAPHEME_PATTERN = _regex.compile(r"\X")
    _EMOJI_PATTERN = _regex.compile(
        r"(?:\p{Extended_Pictographic}|\p{Regional_Indicator}|[0-9#*]\uFE0F?\u20E3)"
    )
else:  # pragma: no cover - development-host compatibility only
    _GRAPHEME_PATTERN = None
    _EMOJI_PATTERN = None


class FontRole(StrEnum):
    BODY = "body"
    SECONDARY = "secondary"
    CONTROL = "control"
    TITLE = "title"
    DISPLAY = "display"


# Semantic role -> static Nunito Sans weight file.
_WEIGHT_FILES: dict[FontRole, str] = {
    FontRole.BODY: "NunitoSans-Regular.ttf",
    FontRole.SECONDARY: "NunitoSans-Regular.ttf",
    FontRole.CONTROL: "NunitoSans-SemiBold.ttf",
    FontRole.TITLE: "NunitoSans-Bold.ttf",
    FontRole.DISPLAY: "NunitoSans-ExtraBold.ttf",
}


@dataclass(frozen=True, slots=True)
class FontSpec:
    role: FontRole
    size: int

    def __post_init__(self) -> None:
        if self.size < 8 or self.size > 160:
            raise ValueError("font size must be within [8, 160]")


@dataclass(frozen=True, slots=True)
class GraphemeSpan:
    """One user-perceived text element and its Python-string boundaries."""

    start: int
    end: int
    text: str
    emoji: bool


@dataclass(frozen=True, slots=True)
class TypographyMetrics:
    """Measured single-line dimensions using Greia's actual fallback chain."""

    width: int
    height: int
    line_height: int


class TypographyError(RuntimeError):
    pass


def grapheme_spans(text: str) -> tuple[GraphemeSpan, ...]:
    """Segment text into Unicode extended grapheme clusters.

    Installed Greia images include ``python3-regex`` and use its Unicode ``\X``
    implementation. The stdlib fallback exists so source tools can still import
    this module on a development host missing that package; it covers combining
    marks and the structural emoji sequences used by Greia but is not the
    shipping Unicode segmentation authority.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not text:
        return ()
    if _GRAPHEME_PATTERN is not None:
        return tuple(
            GraphemeSpan(
                match.start(),
                match.end(),
                match.group(0),
                is_emoji_cluster(match.group(0)),
            )
            for match in _GRAPHEME_PATTERN.finditer(text)
        )
    return _fallback_grapheme_spans(text)


def grapheme_boundaries(text: str) -> tuple[int, ...]:
    """Return valid user-cursor boundaries, including zero and len(text)."""

    spans = grapheme_spans(text)
    if not spans:
        return (0,)
    return (0, *(span.end for span in spans))


def previous_grapheme_boundary(text: str, cursor: int) -> int:
    boundaries = grapheme_boundaries(text)
    cursor = max(0, min(int(cursor), len(text)))
    return boundaries[max(0, bisect.bisect_left(boundaries, cursor) - 1)]


def next_grapheme_boundary(text: str, cursor: int) -> int:
    boundaries = grapheme_boundaries(text)
    cursor = max(0, min(int(cursor), len(text)))
    index = bisect.bisect_right(boundaries, cursor)
    return boundaries[min(index, len(boundaries) - 1)]


def snap_grapheme_boundary(text: str, cursor: int) -> int:
    """Clamp a stale codepoint cursor to the preceding safe user boundary."""

    boundaries = grapheme_boundaries(text)
    cursor = max(0, min(int(cursor), len(text)))
    return boundaries[max(0, bisect.bisect_right(boundaries, cursor) - 1)]


def truncate_grapheme_safe(text: str, maximum_codepoints: int) -> str:
    """Bound a string without retaining half of a grapheme/emoji sequence."""

    if not isinstance(text, str):
        raise TypeError("text must be a string")
    maximum = max(0, int(maximum_codepoints))
    if len(text) <= maximum:
        return text
    end = 0
    for span in grapheme_spans(text):
        if span.end > maximum:
            break
        end = span.end
    return text[:end]


def is_emoji_cluster(cluster: str) -> bool:
    """Return whether a grapheme cluster requests emoji presentation."""

    if not cluster:
        return False
    if _EMOJI_PATTERN is not None:
        return _EMOJI_PATTERN.search(cluster) is not None
    if "\ufe0f" in cluster or "\u200d" in cluster or "\u20e3" in cluster:
        return True
    if sum(_is_regional_indicator(ord(char)) for char in cluster) >= 2:
        return True
    return any(_fallback_emoji_codepoint(ord(char)) for char in cluster)


class GreiaTypography:
    """Bounded Greia font provider and mixed text/color-emoji renderer.

    Normal text uses the selected static Nunito Sans role. Emoji grapheme
    clusters use Noto Color Emoji through Pillow and are then composed with the
    normal text into a Pygame surface. Callers therefore work with one Greia
    typography contract instead of implementing font fallback themselves.
    """

    _MAX_CACHE = 64
    _MAX_EMOJI_SURFACES = 256

    def __init__(
        self,
        font_dir: Path | None = None,
        *,
        emoji_font_path: Path | str = DEFAULT_EMOJI_FONT,
        emoji_native_strike_px: int = DEFAULT_EMOJI_NATIVE_STRIKE_PX,
    ) -> None:
        self._font_dir = Path(font_dir) if font_dir is not None else None
        self._cache: dict[FontSpec, Any] = {}
        self._degraded: bool | None = None
        self._fallback: Any = None
        self._pygame_font = None
        self._emoji_font_path = Path(emoji_font_path)
        self._emoji_native_strike_px = int(emoji_native_strike_px)
        if self._emoji_native_strike_px < 1:
            raise ValueError("emoji native strike must be positive")
        self._emoji_font: ImageFont.FreeTypeFont | None = None
        self._emoji_surfaces: BoundedCache[tuple[str, int], Any] = BoundedCache(
            self._MAX_EMOJI_SURFACES
        )

    def _ensure_pygame(self) -> Any:
        import pygame

        if self._pygame_font is None:
            pygame.font.init()
            self._pygame_font = pygame.font
        return pygame

    @property
    def degraded(self) -> bool:
        return bool(self._degraded)

    @property
    def emoji_available(self) -> bool:
        return self._emoji_font_path.is_file()

    @property
    def cached_emoji_count(self) -> int:
        return len(self._emoji_surfaces)

    def clear(self) -> None:
        """Release renderer-owned caches after display/session teardown."""

        self._cache.clear()
        self._emoji_surfaces.clear()
        self._emoji_font = None

    def font(self, role: FontRole, size: int) -> Any:
        spec = FontSpec(role, size)
        cached = self._cache.get(spec)
        if cached is not None:
            return cached
        if len(self._cache) >= self._MAX_CACHE:
            self._cache.clear()
        font = self._load(spec)
        self._cache[spec] = font
        return font

    def line_height(self, role: FontRole, size: int) -> int:
        return max(self.font(role, size).get_linesize(), int(size))

    def measure(self, text: str, role: FontRole, size: int) -> TypographyMetrics:
        """Measure one line using the same fallback choices as ``render``."""

        FontSpec(role, size)
        if "\n" in text:
            raise ValueError("GreiaTypography.measure accepts one line at a time")
        width = 0
        height = self.line_height(role, size)
        for emoji, value in self._pieces(text):
            if emoji and self.emoji_available:
                surface = self._emoji_surface(value, size)
                width += surface.get_width()
                height = max(height, surface.get_height())
            else:
                measured = self.font(role, size).size(value)
                width += measured[0]
                height = max(height, measured[1])
        return TypographyMetrics(width, height, max(self.line_height(role, size), height))

    def render(
        self,
        text: str,
        role: FontRole,
        size: int,
        color: tuple[int, int, int] | tuple[int, int, int, int],
    ) -> Any:
        """Render one mixed text/emoji line into a transparent Pygame surface."""

        FontSpec(role, size)
        if "\n" in text:
            raise ValueError("GreiaTypography.render accepts one line at a time")
        pygame = self._ensure_pygame()
        rgb = tuple(max(0, min(255, int(channel))) for channel in color[:3])
        surfaces: list[Any] = []
        for emoji, value in self._pieces(text):
            if emoji and self.emoji_available:
                surfaces.append(self._emoji_surface(value, size))
            else:
                surfaces.append(self.font(role, size).render(value, True, rgb))
        line_height = self.line_height(role, size)
        if surfaces:
            line_height = max(line_height, *(surface.get_height() for surface in surfaces))
        width = sum(surface.get_width() for surface in surfaces)
        target = pygame.Surface((max(1, width), max(1, line_height)), pygame.SRCALPHA)
        x = 0
        for surface in surfaces:
            target.blit(surface, (x, max(0, (line_height - surface.get_height()) // 2)))
            x += surface.get_width()
        return target

    def prefix_width(
        self,
        text: str,
        cursor: int,
        role: FontRole,
        size: int,
    ) -> int:
        cursor = snap_grapheme_boundary(text, cursor)
        return self.measure(text[:cursor], role, size).width

    def _load(self, spec: FontSpec) -> Any:
        pygame = self._ensure_pygame()
        filename = _WEIGHT_FILES.get(spec.role)
        if filename is None:
            raise TypographyError(f"no font file for role {spec.role}")
        path = None
        if self._font_dir is not None:
            candidate = self._font_dir / filename
            if candidate.is_file():
                path = candidate
        if path is None and self._degraded is not True:
            # Lazily probe the canonical Greia install location.
            canonical = Path("/opt/greia-os/assets/fonts/nunito-sans") / filename
            if canonical.is_file():
                path = canonical
        if path is not None:
            try:
                return pygame.font.Font(str(path), spec.size)
            except (OSError, ValueError):
                pass
        self._degraded = True
        return pygame.font.Font(None, spec.size)

    def _emoji_surface(self, cluster: str, size: int) -> Any:
        key = (cluster, int(size))
        cached = self._emoji_surfaces.get(key)
        if cached is not None:
            return cached
        pygame = self._ensure_pygame()
        source = self._render_native_emoji(cluster)
        target_height = max(1, int(size))
        if source.height != target_height:
            target_width = max(1, int(round(source.width * target_height / source.height)))
            source = source.resize(
                (target_width, target_height),
                Image.Resampling.LANCZOS,
            )
        surface = pygame.image.fromstring(source.tobytes(), source.size, "RGBA")
        self._emoji_surfaces[key] = surface
        return surface

    def _render_native_emoji(self, cluster: str) -> Image.Image:
        font = self._pillow_emoji_font()
        probe = Image.new(
            "RGBA",
            (self._emoji_native_strike_px * 4, self._emoji_native_strike_px * 2),
            (0, 0, 0, 0),
        )
        draw = ImageDraw.Draw(probe)
        bbox = draw.textbbox((0, 0), cluster, font=font, embedded_color=True)
        width = max(1, bbox[2] - bbox[0])
        height = max(1, bbox[3] - bbox[1])
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ImageDraw.Draw(image).text(
            (-bbox[0], -bbox[1]),
            cluster,
            font=font,
            embedded_color=True,
        )
        visible = image.getbbox()
        return image if visible is None else image.crop(visible)

    def _pillow_emoji_font(self) -> ImageFont.FreeTypeFont:
        if self._emoji_font is None:
            self._emoji_font = ImageFont.truetype(
                str(self._emoji_font_path),
                self._emoji_native_strike_px,
            )
        return self._emoji_font

    @staticmethod
    def _pieces(text: str) -> tuple[tuple[bool, str], ...]:
        if not text:
            return ()
        pieces: list[tuple[bool, str]] = []
        for span in grapheme_spans(text):
            # Keep emoji clusters separate so the bounded surface cache is useful
            # across different strings. Coalesce ordinary text so font kerning is
            # preserved within the normal run.
            if not span.emoji and pieces and not pieces[-1][0]:
                _, previous = pieces[-1]
                pieces[-1] = (False, previous + span.text)
            else:
                pieces.append((span.emoji, span.text))
        return tuple(pieces)


def _fallback_grapheme_spans(text: str) -> tuple[GraphemeSpan, ...]:
    spans: list[GraphemeSpan] = []
    index = 0
    while index < len(text):
        start = index
        first = ord(text[index])
        index += 1
        if (
            _is_regional_indicator(first)
            and index < len(text)
            and _is_regional_indicator(ord(text[index]))
        ):
            index += 1
        while index < len(text):
            codepoint = ord(text[index])
            if _is_extend(codepoint):
                index += 1
                continue
            if codepoint == 0x200D and index + 1 < len(text):
                index += 2
                while index < len(text) and _is_extend(ord(text[index])):
                    index += 1
                continue
            break
        cluster = text[start:index]
        spans.append(GraphemeSpan(start, index, cluster, is_emoji_cluster(cluster)))
    return tuple(spans)


def _is_extend(codepoint: int) -> bool:
    if 0xFE00 <= codepoint <= 0xFE0F or 0xE0100 <= codepoint <= 0xE01EF:
        return True
    if 0x1F3FB <= codepoint <= 0x1F3FF:
        return True
    if 0xE0020 <= codepoint <= 0xE007F:
        return True
    return unicodedata.category(chr(codepoint)).startswith("M")


def _is_regional_indicator(codepoint: int) -> bool:
    return 0x1F1E6 <= codepoint <= 0x1F1FF


def _fallback_emoji_codepoint(codepoint: int) -> bool:
    return (
        0x1F000 <= codepoint <= 0x1FAFF
        or 0x2600 <= codepoint <= 0x27BF
        or codepoint
        in {0x00A9, 0x00AE, 0x2122, 0x231A, 0x231B, 0x2328, 0x23F0, 0x23F3}
    )
