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
# See GREIA_VISUAL_STYLE_GUIDE.md and build/trust/nunito-sans-2.3.2.provenance.
#
# Normal fonts are loaded once per (role, size) and cached; consumers never
# open raw font paths. Emoji are a platform fallback, not Greia system icons:
# Noto Color Emoji is rasterized through Pillow's embedded-color path and then
# composed into ordinary Pygame surfaces. Missing/corrupt fallback resources
# degrade safely instead of taking down the child session.

DEFAULT_EMOJI_FONT = Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf")
_HOST_FALLBACK_EMOJI_FONTS: tuple[Path, ...] = (
    Path("/System/Library/Fonts/Apple Color Emoji.ttc"),
    Path("/System/Library/Fonts/CoreAddition/AppleColorEmoji.ttc"),
    Path("/Library/Fonts/NotoColorEmoji.ttf"),
)
# Debian 12/bookworm's Noto Color Emoji package is CBDT/CBLC with a 109-pixel
# native bitmap strike. Greia renders that strike and scales the RGBA result to
# the requested UI size. Keep this version-specific fact behind this service.
DEFAULT_EMOJI_NATIVE_STRIKE_PX = 109

if _regex is not None:
    _GRAPHEME_PATTERN = _regex.compile(r"\X")
    _EMOJI_PRESENTATION_PATTERN = _regex.compile(r"\p{Emoji_Presentation}")
else:  # pragma: no cover - development-host compatibility only
    _GRAPHEME_PATTERN = None
    _EMOJI_PRESENTATION_PATTERN = None


class FontRole(StrEnum):
    BODY = "body"
    SECONDARY = "secondary"
    CONTROL = "control"
    TITLE = "title"
    DISPLAY = "display"


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
        if self.size < 8 or self.size > 144:
            raise ValueError(f"font size must be between 8 and 144, got {self.size}")


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
    r"""Segment text into Unicode extended grapheme clusters.

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
                match.group(),
                is_emoji_cluster(match.group()),
            )
            for match in _GRAPHEME_PATTERN.finditer(text)
        )
    return _fallback_grapheme_spans(text)


def grapheme_boundaries(text: str) -> tuple[int, ...]:
    """Return all valid cursor indices (0, end, and cluster boundaries)."""

    if not text:
        return (0,)
    boundaries = [0]
    for span in grapheme_spans(text):
        boundaries.append(span.end)
    return tuple(boundaries)


def previous_grapheme_boundary(text: str, cursor: int) -> int:
    """Step back by one user-perceived character."""

    boundaries = grapheme_boundaries(text)
    pos = bisect.bisect_left(boundaries, cursor) - 1
    return boundaries[max(0, pos)]


def next_grapheme_boundary(text: str, cursor: int) -> int:
    """Advance by one user-perceived character."""

    boundaries = grapheme_boundaries(text)
    pos = bisect.bisect_right(boundaries, cursor)
    return boundaries[min(pos, len(boundaries) - 1)]


def snap_grapheme_boundary(text: str, cursor: int) -> int:
    """Clamp a raw codepoint index to the nearest valid grapheme boundary."""

    boundaries = grapheme_boundaries(text)
    if cursor <= 0:
        return 0
    if cursor >= len(text):
        return len(text)
    pos = bisect.bisect_right(boundaries, cursor) - 1
    return boundaries[pos]


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
    """Return whether a grapheme cluster requests emoji presentation.

    Emoji-capable symbols such as © are not automatically colored: explicit
    text presentation (VS15) stays text, explicit emoji presentation (VS16),
    ZWJ/keycap sequences, flags and default Emoji_Presentation characters use
    the emoji fallback.
    """

    if not cluster or "\ufe0e" in cluster:
        return False
    if "\ufe0f" in cluster or "\u200d" in cluster or "\u20e3" in cluster:
        return True
    if sum(_is_regional_indicator(ord(char)) for char in cluster) >= 2:
        return True
    if _EMOJI_PRESENTATION_PATTERN is not None:
        return _EMOJI_PRESENTATION_PATTERN.search(cluster) is not None
    return any(_fallback_emoji_codepoint(ord(char)) for char in cluster)


class GreiaTypography:
    """Bounded Greia font provider and mixed text/color-emoji renderer.

    Normal text uses the selected static Nunito Sans role. Emoji grapheme
    clusters use Noto Color Emoji through Pillow and are then composed with the
    normal text into a Pygame surface. Callers therefore work with one Greia
    typography contract instead of implementing font fallback themselves.
    """

    _MAX_CACHE = 64
    # Bounded text-surface cache for per-frame copy. Kept well inside the
    # C0 memory floor; cleared wholesale rather than evicted per entry so the
    # structure cannot grow without bound.
    _MAX_SURFACE_CACHE = 512
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
        self._pygame_font = None
        resolved_emoji_path = Path(emoji_font_path)
        if not resolved_emoji_path.is_file() and emoji_font_path == DEFAULT_EMOJI_FONT:
            for candidate in _HOST_FALLBACK_EMOJI_FONTS:
                if candidate.is_file():
                    resolved_emoji_path = candidate
                    break
        self._emoji_font_path = resolved_emoji_path
        self._emoji_native_strike_px = int(emoji_native_strike_px)
        if self._emoji_native_strike_px < 1:
            raise ValueError("emoji native strike must be positive")
        self._emoji_font: ImageFont.FreeTypeFont | None = None
        self._emoji_degraded = False
        self._emoji_surfaces: BoundedCache[tuple[str, int], Any] = BoundedCache(
            self._MAX_EMOJI_SURFACES
        )
        self._surface_cache: dict[tuple[int, str, tuple[int, ...]], tuple[Any, Any]] = {}

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
        return self._emoji_font_path.is_file() and not self._emoji_degraded

    @property
    def emoji_degraded(self) -> bool:
        return self._emoji_degraded

    @property
    def cached_emoji_count(self) -> int:
        return len(self._emoji_surfaces)

    def clear(self) -> None:
        """Release renderer-owned caches after display/session teardown."""

        self._cache.clear()
        self._emoji_surfaces.clear()
        self._emoji_font = None
        self._emoji_degraded = False
        self._surface_cache.clear()

    def surface(self, font: Any, text: str, color: Any) -> Any:
        """Return a bounded, cached antialiased surface for one text line.

        Callers that draw the same copy every frame must not re-rasterize it
        every frame. On the reference Acer (Intel GMA 500, software rendering,
        no GPU) the graphical installer's unconditional 30 fps full repaint
        re-rendered every label 30 times a second and pinned one core, which
        the child experiences as a brutally unresponsive screen.

        The cache is keyed by the live font object, so it can never serve a
        surface belonging to a different typeface or size. The font is held in
        the value so its ``id`` cannot be recycled onto a different object
        while an entry is live.
        """

        if not isinstance(text, str) or not text:
            return font.render(text, True, color)
        key = (id(font), text, tuple(color))
        cached = self._surface_cache.get(key)
        if cached is not None:
            return cached[1]
        if len(self._surface_cache) >= self._MAX_SURFACE_CACHE:
            self._surface_cache.clear()
        surface = font.render(text, True, color)
        self._surface_cache[key] = (font, surface)
        return surface

    def surface_width(self, font: Any, text: str) -> int:
        """Width of ``text`` in ``font``, without building a surface."""

        return font.size(text)[0]

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
        normal_font = self.font(role, size)
        for emoji, value in self._pieces(text):
            surface = self._safe_emoji_surface(value, size) if emoji else None
            if surface is not None:
                width += surface.get_width()
                height = max(height, surface.get_height())
            else:
                measured = normal_font.size(value)
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
        normal_font = self.font(role, size)
        pieces = tuple(self._pieces(text))
        if not pieces:
            return normal_font.render("", True, rgb)
        if len(pieces) == 1 and not pieces[0][0]:
            return normal_font.render(pieces[0][1], True, rgb)
        surfaces: list[Any] = []
        for emoji, value in pieces:
            surface = self._safe_emoji_surface(value, size) if emoji else None
            if surface is None:
                surface = normal_font.render(value, True, rgb)
            surfaces.append(surface)
        line_height = self.line_height(role, size)
        if surfaces:
            line_height = max(line_height, *(surface.get_height() for surface in surfaces))
        width = sum(surface.get_width() for surface in surfaces)
        target = pygame.Surface((max(1, width), max(1, line_height)), pygame.SRCALPHA)
        x = 0
        for surface in surfaces:
            target.blit(
                surface,
                (x, max(0, (line_height - surface.get_height()) // 2)),
            )
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
            else:
                self._degraded = True
        elif self._degraded is not True:
            canonical = Path("/opt/greia-os/assets/fonts/nunito-sans") / filename
            if canonical.is_file():
                path = canonical
            else:
                repo_fallback = (
                    Path(__file__).resolve().parents[2]
                    / "assets"
                    / "fonts"
                    / "nunito-sans"
                    / filename
                )
                if repo_fallback.is_file():
                    path = repo_fallback
        if path is not None:
            try:
                return pygame.font.Font(str(path), spec.size)
            except (OSError, ValueError):
                pass
        self._degraded = True
        return pygame.font.Font(None, spec.size)

    def _safe_emoji_surface(self, cluster: str, size: int) -> Any | None:
        if not self.emoji_available:
            return None
        try:
            return self._emoji_surface(cluster, size)
        except (OSError, ValueError):
            # A release image should have a verified compatible fallback font,
            # but a damaged/mismatched local resource must not crash the child
            # session. Degrade for the remainder of this typography lifetime.
            self._emoji_degraded = True
            self._emoji_font = None
            self._emoji_surfaces.clear()
            return None

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
        draw = ImageDraw.Draw(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
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
            strikes = (self._emoji_native_strike_px, 96, 64, 160, 48, 32, 20, 109)
            last_err: Exception | None = None
            for strike in strikes:
                try:
                    self._emoji_font = ImageFont.truetype(
                        str(self._emoji_font_path),
                        strike,
                    )
                    break
                except OSError as err:
                    last_err = err
            if self._emoji_font is None:
                raise last_err or OSError(f"cannot load emoji font {self._emoji_font_path}")
        return self._emoji_font

    @staticmethod
    def _pieces(text: str) -> tuple[tuple[bool, str], ...]:
        if not text:
            return ()
        pieces: list[tuple[bool, str]] = []
        for span in grapheme_spans(text):
            # Keep emoji clusters separate so the bounded surface cache is useful
            # across strings. Coalesce ordinary text so normal-font kerning is
            # preserved within each run.
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
    # Development-host fallback only; shipping classification uses Unicode
    # Emoji_Presentation through python3-regex.
    return 0x1F000 <= codepoint <= 0x1FAFF or codepoint in {
        0x231A,
        0x231B,
        0x23F0,
        0x23F3,
    }
