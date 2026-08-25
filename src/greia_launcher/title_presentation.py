from __future__ import annotations

from typing import Any, Callable
from greia_platform.typography import grapheme_spans

CARD_TITLE_DISPLAY_CAP = 48


def cap_title_for_card(title: str, max_graphemes: int = CARD_TITLE_DISPLAY_CAP) -> str:
    """Cap title to defensive grapheme limit before normal-card rendering."""
    title_clean = title.strip()
    spans = grapheme_spans(title_clean)
    if len(spans) <= max_graphemes:
        return title_clean
    end = spans[max_graphemes - 1].end
    return title_clean[:end].rstrip() + "…"


def split_title_two_lines(
    text: str,
    font: Any,
    max_width: int,
    max_graphemes: int = CARD_TITLE_DISPLAY_CAP,
) -> tuple[str, ...]:
    """Break title into at most two lines using word-aware and grapheme-safe wrapping."""
    capped = cap_title_for_card(text, max_graphemes)
    if not capped:
        return ("Activity",)

    # 1. Single line check
    if font.size(capped)[0] <= max_width:
        return (capped,)

    # 2. Word-aware split: find balanced split that fits max_width on both lines
    words = capped.split()
    if len(words) >= 2:
        candidates: list[tuple[int, tuple[str, str]]] = []
        for i in range(1, len(words)):
            l1 = " ".join(words[:i])
            l2 = " ".join(words[i:])
            w1 = font.size(l1)[0]
            w2 = font.size(l2)[0]
            if w1 <= max_width and w2 <= max_width:
                # Prefer more balanced line widths
                diff = abs(w1 - w2)
                candidates.append((diff, (l1, l2)))
        if candidates:
            candidates.sort(key=lambda item: item[0])
            return candidates[0][1]

    # 3. Grapheme-aware split (fallback for single long words or non-spaced text)
    spans = grapheme_spans(capped)
    if len(spans) >= 2:
        g_candidates: list[tuple[int, tuple[str, str]]] = []
        for i in range(1, len(spans)):
            l1 = capped[: spans[i - 1].end].rstrip()
            l2 = capped[spans[i].start :].lstrip()
            w1 = font.size(l1)[0]
            w2 = font.size(l2)[0]
            if w1 <= max_width and w2 <= max_width:
                diff = abs(w1 - w2)
                g_candidates.append((diff, (l1, l2)))
        if g_candidates:
            g_candidates.sort(key=lambda item: item[0])
            return g_candidates[0][1]

    # 4. Truncation fallback: fill line 1 as much as possible, then line 2 with ellipsis
    l1 = ""
    split_idx = 0
    if len(words) >= 2:
        for i in range(1, len(words) + 1):
            test_l1 = " ".join(words[:i])
            if font.size(test_l1)[0] <= max_width:
                l1 = test_l1
                split_idx = i
            else:
                break
        rem_words = words[split_idx:]
        rem_text = " ".join(rem_words)
    else:
        for i, sp in enumerate(spans):
            test_l1 = capped[: sp.end]
            if font.size(test_l1)[0] <= max_width:
                l1 = test_l1
                split_idx = i + 1
            else:
                break
        rem_spans = spans[split_idx:]
        rem_text = capped[spans[split_idx].start :] if rem_spans else ""

    if not l1:
        # Even 1st word/cluster is wide: truncate line 1
        l1 = capped
        while len(l1) > 1 and font.size(l1 + "…")[0] > max_width:
            l1 = l1[:-1]
        return (l1 + "…",)

    # Line 2 with ellipsis if needed
    l2 = rem_text
    if font.size(l2)[0] > max_width:
        rem_spans = grapheme_spans(rem_text)
        l2 = ""
        for sp in rem_spans:
            test_l2 = rem_text[: sp.end].rstrip() + "…"
            if font.size(test_l2)[0] <= max_width:
                l2 = test_l2
            else:
                break
        if not l2 and rem_spans:
            l2 = "…"

    return (l1, l2) if l2 else (l1,)


def render_activity_card_label(
    text: str,
    *,
    max_width: int,
    max_height: int,
    font_provider: Callable[[int], Any],
    color: tuple[int, int, int],
    preferred_size: int,
    pygame: Any,
    min_size: int = 14,
) -> Any:
    """Render a 1- or 2-line centered Activity label surface fitting bounds without geometric distortion."""
    max_width = max(24, max_width)
    max_height = max(18, max_height)

    best_lines: tuple[str, ...] = (text,)
    best_font: Any = None

    # Always try at least the preferred size: when preferred_size is below
    # min_size the naive range would be empty and no fit check would run.
    lowest_size = min(min_size, preferred_size)
    for size in range(preferred_size, lowest_size - 1, -1):
        font = font_provider(size)
        lines = split_title_two_lines(text, font, max_width)
        line_h = font.get_linesize()
        total_h = len(lines) * line_h
        if total_h <= max_height:
            best_lines = lines
            best_font = font
            break

    if best_font is None:
        best_font = font_provider(lowest_size)
        best_lines = split_title_two_lines(text, best_font, max_width)

    line_surfaces = [best_font.render(line, True, color) for line in best_lines]
    total_w = min(max_width, max(s.get_width() for s in line_surfaces) if line_surfaces else 1)
    line_h = best_font.get_linesize()

    # Hard guarantee against text crossing the card border: when even the
    # chosen font cannot stack its lines inside the band, compress leading
    # instead of letting glyphs clip past the label bounds.
    tallest_line = max((s.get_height() for s in line_surfaces), default=line_h)
    count = len(line_surfaces)
    if count > 1 and count * line_h > max_height:
        line_h = max(1, min(line_h, (max_height - tallest_line) // (count - 1)))

    needed_h = count * line_h
    total_h = min(max_height, needed_h)

    surface = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
    y_offset = (total_h - needed_h) // 2
    for i, line_s in enumerate(line_surfaces):
        x = (total_w - line_s.get_width()) // 2
        y = y_offset + i * line_h
        surface.blit(line_s, (x, y))

    return surface


def contain_fit_icon_surface(
    source_surface: Any,
    size: int,
    pygame: Any,
    *,
    safe_padding_ratio: float = 0.03,
) -> Any:
    """Contain-fit source icon in a square surface reserving safe outer padding."""
    size = max(16, size)
    target = pygame.Surface((size, size), pygame.SRCALPHA)
    src_w, src_h = source_surface.get_size()
    if src_w <= 0 or src_h <= 0:
        return target

    max_dim = max(1, int(round(size * (1.0 - 2.0 * safe_padding_ratio))))
    scale = min(max_dim / src_w, max_dim / src_h)
    new_w = max(1, int(round(src_w * scale)))
    new_h = max(1, int(round(src_h * scale)))

    scaled = pygame.transform.smoothscale(source_surface, (new_w, new_h))
    dest_x = (size - new_w) // 2
    dest_y = (size - new_h) // 2
    target.blit(scaled, (dest_x, dest_y))
    return target


_DISCLOSURE_SURFACES: dict[tuple[str, int, tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]], Any] = {}


def render_full_title_disclosure_surface(
    full_title: str,
    *,
    font: Any,
    theme: Any,
    max_width: int,
    pygame: Any,
) -> Any:
    """Render a clean Greia-native full title tooltip / callout pill."""
    full_title = full_title.strip()
    if not full_title:
        return pygame.Surface((1, 1), pygame.SRCALPHA)

    cache_key = (
        full_title,
        max_width,
        getattr(theme, "text", (30, 30, 30)),
        getattr(theme, "panel", (255, 255, 255)),
        getattr(theme, "accent", (66, 133, 244)),
    )
    if cache_key in _DISCLOSURE_SURFACES:
        return _DISCLOSURE_SURFACES[cache_key]

    # Word wrap for tooltip if title is very long
    words = full_title.split()
    lines: list[str] = []
    current_line = ""
    usable_w = max(60, max_width - 24)

    for word in words:
        test = f"{current_line} {word}".strip() if current_line else word
        if font.size(test)[0] <= usable_w:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    if not lines:
        lines = [full_title]

    line_h = font.get_linesize()
    text_surfaces = [font.render(line, True, theme.text) for line in lines]
    text_w = max(s.get_width() for s in text_surfaces)
    text_h = len(text_surfaces) * line_h

    pad_x = 12
    pad_y = 7
    pill_w = text_w + pad_x * 2
    pill_h = text_h + pad_y * 2

    pill = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
    pill.fill((0, 0, 0, 0))
    rect = pygame.Rect(0, 0, pill_w, pill_h)

    # Pill background
    bg_color = (
        min(255, getattr(theme, "panel", (255, 255, 255))[0] + 12),
        min(255, getattr(theme, "panel", (255, 255, 255))[1] + 12),
        min(255, getattr(theme, "panel", (255, 255, 255))[2] + 12),
    )
    border_color = getattr(theme, "accent", (66, 133, 244))
    pygame.draw.rect(pill, bg_color, rect, border_radius=12)
    pygame.draw.rect(pill, border_color, rect, width=2, border_radius=12)

    for i, ts in enumerate(text_surfaces):
        tx = (pill_w - ts.get_width()) // 2
        ty = pad_y + i * line_h
        pill.blit(ts, (tx, ty))

    if len(_DISCLOSURE_SURFACES) > 64:
        _DISCLOSURE_SURFACES.clear()
    _DISCLOSURE_SURFACES[cache_key] = pill
    return pill

