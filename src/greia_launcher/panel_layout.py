"""Measured, translation-tolerant layout for the on-device Parent panel.

The panel used to blit single-line text at hard-coded offsets and trust that
arithmetic sizing would fit. That assumption is already broken: the audio tab
carries half-hardcoded Italian next to English ("Guadagno Microfono",
"Preset rapidi consigliati"), and its level label is centred inside a fixed
300 px badge with no measurement, so it spills over the adjacent buttons. The
tab bar computes ``tab_w`` arithmetically and centres labels in it, so a longer
translation overlaps its neighbours.

Nothing here assumes a label fits. Text is measured with the same fallback
chain the panel renders with (including colour-emoji fallback), wrapped to a
maximum width, and allowed to grow a container downwards. Where growth is not
possible — a tab strip, a button face — text is clipped with an ellipsis rather
than allowed to escape its box, and the caller can shrink the size before
clipping.

``GreiaTypography.render`` deliberately accepts one line at a time, so wrapping
composes several measured single-line renders into one surface. That keeps the
shared emoji fallback and surface cache authoritative instead of bypassing them
with raw font rendering, which previously produced tofu boxes for every emoji on
device.

The helpers are deliberately free of Greia domain knowledge so they can be
tested headlessly and reused by every panel tab.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

#: Appended when a single-line label has to be clipped. ASCII rather than U+2026
#: because the bundled Latin fonts are known to carry it, whereas a missing
#: glyph would render as a tofu box and look like a rendering fault.
ELLIPSIS = "..."

#: Padding kept clear between a label and the edge of the box that owns it.
DEFAULT_PADDING = 12

#: Longest word that may be broken mid-word when a single token is wider than
#: the whole box. Without this, one long German compound would force the label to
#: be clipped even though there is room on the next line.
_MIN_BREAK_CHUNK = 2


@dataclass(frozen=True, slots=True)
class TextBlock:
    """A measured, possibly multi-line label and the box it was fitted into."""

    surface: Any
    width: int
    height: int
    line_count: int
    clipped: bool
    font_size: int

    @property
    def fits(self) -> bool:
        """True when nothing had to be clipped away."""

        return not self.clipped


def measure(typography: Any, text: str, role: Any, size: int) -> tuple[int, int]:
    """Return ``(width, line_height)`` for one line, via the shared metrics."""

    metrics = typography.measure(text, role, size)
    return int(metrics.width), int(metrics.line_height)


def _break_long_token(
    typography: Any, token: str, role: Any, size: int, max_width: int
) -> list[str]:
    """Split a token that cannot fit on any line, rather than clipping it.

    German and Finnish compounds routinely exceed a narrow button. Breaking the
    token keeps the whole label visible instead of silently hiding part of a
    word, which is what a child- or parent-facing control must not do.
    """

    pieces: list[str] = []
    current = ""
    for character in token:
        candidate = current + character
        width, _ = measure(typography, candidate, role, size)
        if width > max_width and len(current) >= _MIN_BREAK_CHUNK:
            pieces.append(current)
            current = character
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces or [token]


def wrap_text(
    typography: Any,
    text: str,
    role: Any,
    size: int,
    max_width: int,
    *,
    max_lines: int | None = None,
) -> list[str]:
    """Break ``text`` into lines no wider than ``max_width``.

    Existing newlines are honoured so callers can force a break. Words longer
    than the box are split rather than overflowing. When ``max_lines`` is given
    the final line is ellipsised, so the result is never silently longer than the
    caller allowed.
    """

    if max_width <= 0:
        raise ValueError("max_width must be positive")
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            width, _ = measure(typography, candidate, role, size)
            if width <= max_width or not current:
                if width <= max_width:
                    current = candidate
                    continue
                # A single word wider than the box.
                parts = _break_long_token(typography, word, role, size, max_width)
                if current:
                    lines.append(current)
                lines.extend(parts[:-1])
                current = parts[-1]
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and measure(typography, f"{last}{ELLIPSIS}", role, size)[0] > max_width:
            last = last[:-1]
        lines[-1] = f"{last.rstrip()}{ELLIPSIS}" if last else ELLIPSIS
    return lines


def fit_text_block(
    typography: Any,
    text: str,
    role: Any,
    size: int,
    color: tuple[int, int, int],
    max_width: int,
    *,
    max_lines: int | None = None,
    line_spacing: int = 2,
) -> TextBlock:
    """Render ``text`` wrapped to ``max_width`` and report what it needed.

    The returned surface is as tall as the text actually occupies, so a caller
    can grow a card downwards instead of guessing a height. ``clipped`` is true
    when content was dropped, which a test can assert on.
    """

    lines = wrap_text(typography, text, role, size, max_width, max_lines=max_lines)
    clipped = bool(max_lines is not None and len(lines) > 0 and lines[-1].endswith(ELLIPSIS))
    if not lines:
        lines = [""]
    pygame = typography._ensure_pygame()  # noqa: SLF001 - shared, authoritative surface
    rendered = [typography.render(line, role, size, color) for line in lines]
    line_height = max(surface.get_height() for surface in rendered)
    width = max((surface.get_width() for surface in rendered), default=0)
    height = line_height * len(rendered) + line_spacing * (len(rendered) - 1)
    surface = pygame.Surface((max(width, 1), max(height, 1)), pygame.SRCALPHA)
    for index, piece in enumerate(rendered):
        surface.blit(piece, (0, index * (line_height + line_spacing)))
    return TextBlock(
        surface=surface,
        width=width,
        height=height,
        line_count=len(rendered),
        clipped=clipped,
        font_size=size,
    )


def fit_single_line(
    typography: Any,
    text: str,
    role: Any,
    size: int,
    color: tuple[int, int, int],
    max_width: int,
    *,
    min_size: int = 10,
) -> TextBlock:
    """Fit a label that must stay on one line, shrinking before clipping.

    Used for tab strips and button faces, where growing downwards is not an
    option. The size is reduced while the text still overflows, down to
    ``min_size``, and only then is it ellipsised. The reported ``font_size`` is
    the one actually used, so a caller or a test can see the squeeze.
    """

    chosen = size
    block = fit_text_block(typography, text, role, chosen, color, max_width, max_lines=1)
    while block.clipped and chosen > min_size:
        chosen -= 1
        block = fit_text_block(
            typography, text, role, chosen, color, max_width, max_lines=1
        )
    return TextBlock(
        surface=block.surface,
        width=block.width,
        height=block.height,
        line_count=1,
        clipped=block.clipped,
        font_size=chosen,
    )


def blit_block(
    surface: Any,
    block: TextBlock,
    pygame: Any,
    x: int,
    y: int,
    *,
    align: str = "left",
    bounds: Any | None = None,
) -> Any:
    """Blit a block at ``x``/``y``, optionally centred, never leaving ``bounds``.

    Returns the rectangle actually used so a caller can assert containment.
    """

    rect = block.surface.get_rect()
    if align == "center":
        rect.centerx = x
    else:
        rect.x = x
    rect.y = y
    if bounds is not None:
        rect.clip_ip(bounds)
    surface.blit(block.surface, rect)
    return rect


def total_gap_width(available: int, count: int, gap: int) -> int:
    """Width left for ``count`` items once ``gap`` between them is removed."""

    if count <= 0:
        raise ValueError("count must be positive")
    if available <= 0:
        raise ValueError("available must be positive")
    return available - gap * (count - 1)


def even_columns(available: int, count: int, gap: int, *, padding: int = 0) -> list[int]:
    """Column widths that exactly fill ``available`` with no rounding drift.

    The last column absorbs the remainder, so a row of columns always ends flush
    with the right edge instead of leaving a ragged gap that later reads as a
    layout bug.
    """

    usable = total_gap_width(available - padding * 2, count, gap)
    if usable < count:
        raise ValueError("not enough width for the requested columns")
    base = usable // count
    widths = [base] * count
    widths[-1] += usable - base * count
    return widths


def overlaps(first: Any, second: Any) -> bool:
    """True when two rectangles intersect. Zero-area rectangles never overlap."""

    if first.width <= 0 or first.height <= 0 or second.width <= 0 or second.height <= 0:
        return False
    return bool(first.colliderect(second))


def find_overlaps(rects: Sequence[tuple[str, Any]]) -> list[tuple[str, str]]:
    """Return every overlapping pair, for use as a layout assertion."""

    clashes: list[tuple[str, str]] = []
    for i, (name_a, rect_a) in enumerate(rects):
        for name_b, rect_b in rects[i + 1 :]:
            if overlaps(rect_a, rect_b):
                clashes.append((name_a, name_b))
    return clashes


__all__ = [
    "DEFAULT_PADDING",
    "ELLIPSIS",
    "TextBlock",
    "blit_block",
    "even_columns",
    "find_overlaps",
    "fit_single_line",
    "fit_text_block",
    "measure",
    "overlaps",
    "total_gap_width",
    "wrap_text",
]
