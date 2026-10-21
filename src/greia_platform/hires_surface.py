"""Transparent high-resolution rendering for reference-canvas Activities.

Reference-canvas Activities lay out and draw in 1024x600 logical coordinates.
On a clearly larger display (owner threshold: at least 1.2x the reference)
upscaling that finished frame softens every outline.  This adapter lets the
*same* Activity code render at the display's real resolution instead:

* :class:`ScaledSurface` holds physical pixels but answers every Python-level
  geometry question (``get_size``, ``get_rect``, ``blit`` destinations,
  ``fill`` rectangles, clips) in logical units;
* while the layer is active, ``pygame.Surface`` creates scaled surfaces and
  ``pygame.draw``, the geometry-changing ``pygame.transform`` functions,
  ``pygame.image.load``/``fromstring``/``frombytes`` and ``pygame.font.Font``
  map logical arguments onto those physical pixels;
* a plain (logical-resolution) surface blitted onto a scaled one is resampled
  on the way, so anything the layer did not create still lands in the right
  place and size; it is merely as soft as before.

Activities opt in through ``PygameReferenceCanvas(..., hires=True)``; nothing
changes below the threshold, without a Greia display, or with
``GREIA_ACTIVITY_HIRES=0``.  The layer only patches the pygame module inside
the Activity's own process, like the display-request policy in
:mod:`greia_platform.activity_display`; it grants nothing.

Known limits (documented, not hidden): ``subsurface`` of a scaled surface is a
copy rather than a pixel-sharing view; ``surfarray`` sees physical pixels
(``pygame.mask.from_surface`` is mapped back to logical units);
code that captured ``pygame.Surface``/``pygame.draw`` functions before
activation keeps creating logical surfaces.
"""

from __future__ import annotations

import math
import os
from types import SimpleNamespace
from typing import Any, Iterable

import pygame

#: Owner rule (2026-10-21): close to the reference keep the cheap path.
HIRES_MIN_SCALE = 1.2
#: Process-local opt-out for diagnosis (``0`` disables the layer).
HIRES_ENVIRONMENT = "GREIA_ACTIVITY_HIRES"

RAW = SimpleNamespace(
    Surface=pygame.Surface,
    blit=pygame.Surface.blit,
    fill=pygame.Surface.fill,
    get_size=pygame.Surface.get_size,
    copy=pygame.Surface.copy,
    convert=pygame.Surface.convert,
    convert_alpha=pygame.Surface.convert_alpha,
    set_clip=pygame.Surface.set_clip,
    get_clip=pygame.Surface.get_clip,
    get_at=pygame.Surface.get_at,
    set_at=pygame.Surface.set_at,
    subsurface=pygame.Surface.subsurface,
    get_bounding_rect=pygame.Surface.get_bounding_rect,
    scroll=pygame.Surface.scroll,
    draw=SimpleNamespace(**{
        name: getattr(pygame.draw, name)
        for name in ("rect", "circle", "ellipse", "arc", "line", "lines", "aaline", "aalines", "polygon")
    }),
    transform=SimpleNamespace(**{
        name: getattr(pygame.transform, name)
        for name in (
            "scale", "smoothscale", "scale_by", "smoothscale_by", "rotate",
            "rotozoom", "flip", "average_color", "grayscale", "chop",
        )
        if hasattr(pygame.transform, name)
    }),
    image_load=pygame.image.load,
    image_fromstring=getattr(pygame.image, "fromstring", None),
    image_frombytes=getattr(pygame.image, "frombytes", None),
    Font=pygame.font.Font,
    mask_from_surface=pygame.mask.from_surface,
)

_state = SimpleNamespace(active=False, scale=1.0)


def hires_scale_for(contain_scale: float, environ: dict[str, str] | None = None) -> float | None:
    """Return the render scale for a CONTAIN scale, or None for the cheap path."""

    environment = os.environ if environ is None else environ
    if environment.get(HIRES_ENVIRONMENT, "1").strip() == "0":
        return None
    if not math.isfinite(contain_scale) or contain_scale < HIRES_MIN_SCALE:
        return None
    return float(contain_scale)


def is_active() -> bool:
    return bool(_state.active)


def scale_of(surface: Any) -> float:
    """Logical-to-physical scale of ``surface`` (1.0 for a plain surface)."""

    if type(surface) is ScaledSurface:
        return surface._scale()
    return 1.0


# -- geometry helpers ----------------------------------------------------------
def _p(value: float, scale: float) -> int:
    return int(round(float(value) * scale))


def _point(point: Any, scale: float) -> tuple[int, int]:
    return (_p(point[0], scale), _p(point[1], scale))


def _fpoint(point: Any, scale: float) -> tuple[float, float]:
    return (float(point[0]) * scale, float(point[1]) * scale)


def _rect(rect: Any, scale: float) -> pygame.Rect:
    r = pygame.Rect(rect)
    left, top = _p(r.x, scale), _p(r.y, scale)
    return pygame.Rect(left, top, _p(r.right, scale) - left, _p(r.bottom, scale) - top)


def _logical_rect(rect: Any, scale: float) -> pygame.Rect:
    r = pygame.Rect(rect)
    left, top = math.floor(r.x / scale), math.floor(r.y / scale)
    return pygame.Rect(left, top, math.ceil(r.right / scale) - left, math.ceil(r.bottom / scale) - top)


def physical_rect(rect: Any, scale: float) -> pygame.Rect:
    """Physical pixels covered by a logical rectangle at ``scale``."""

    return _rect(rect, scale)


def _width(width: int, scale: float) -> int:
    # Round up: a 1 px line drawn per logical row (gradients, stripes) must
    # still cover every physical row at 1.25x instead of leaving gaps.
    width = int(width)
    return max(1, math.ceil(width * scale - 1e-6)) if width > 0 else width


class _SurfaceMeta(type(pygame.Surface)):
    """Keep ``isinstance(plain_surface, pygame.Surface)`` true after patching."""

    def __instancecheck__(cls, instance: Any) -> bool:
        return isinstance(instance, RAW.Surface)

    def __subclasscheck__(cls, subclass: type) -> bool:
        return issubclass(subclass, RAW.Surface)


class ScaledSurface(pygame.Surface, metaclass=_SurfaceMeta):
    """A surface with physical pixels and a logical-unit Python API."""

    # Class-level defaults: pygame's C methods can return instances of this
    # class without running ``__init__``.
    _greia_scale: float | None = None
    _greia_logical: tuple[int, int] | None = None

    def __init__(self, size: Any, *args: Any, scale: float | None = None,
                 physical: tuple[int, int] | None = None, **kwargs: Any) -> None:
        factor = float(scale if scale is not None else _state.scale)
        width, height = int(size[0]), int(size[1])
        if physical is None:
            physical = (max(1, _p(width, factor)) if width > 0 else 0,
                        max(1, _p(height, factor)) if height > 0 else 0)
        super().__init__(physical, *args, **kwargs)
        self._greia_scale = factor
        self._greia_logical = (width, height)

    # -- identity -----------------------------------------------------------
    def _scale(self) -> float:
        if self._greia_scale is None:
            self._greia_scale = _state.scale
        return self._greia_scale

    def _logical(self) -> tuple[int, int]:
        if self._greia_logical is None:
            w, h = RAW.get_size(self)
            s = self._scale()
            self._greia_logical = (max(1, round(w / s)), max(1, round(h / s)))
        return self._greia_logical

    @property
    def physical_size(self) -> tuple[int, int]:
        return RAW.get_size(self)

    @classmethod
    def adopt(cls, raw: pygame.Surface, logical: tuple[int, int], scale: float | None = None) -> "ScaledSurface":
        """Wrap physical pixels that already represent ``logical`` units."""

        factor = float(scale if scale is not None else _state.scale)
        physical = RAW.get_size(raw)
        flags = raw.get_flags() & pygame.SRCALPHA
        new = cls(logical, flags, raw, scale=factor, physical=physical) if raw.get_bitsize() >= 8 else cls(logical, flags, scale=factor, physical=physical)
        _copy_pixels(new, raw)
        return new

    @classmethod
    def upscale(cls, raw: pygame.Surface, scale: float | None = None) -> "ScaledSurface":
        """Resample a logical-resolution surface into a scaled one."""

        factor = float(scale if scale is not None else _state.scale)
        logical = RAW.get_size(raw)
        source = raw if raw.get_bitsize() in (24, 32) else RAW.convert_alpha(raw) if raw.get_flags() & pygame.SRCALPHA else RAW.convert(raw)
        flags = raw.get_flags() & pygame.SRCALPHA
        flags = source.get_flags() & pygame.SRCALPHA
        # Template on the converted source: smoothscale into a destination of
        # another channel order would swap red and blue.
        new = cls(logical, flags, source, scale=factor)
        if RAW.get_size(new) == logical:
            _copy_pixels(new, source)
        else:
            RAW.transform.smoothscale(_matching(source, new), RAW.get_size(new), new)
            if new.get_flags() & pygame.SRCALPHA:
                _snap_opaque_alpha(new)
        _copy_format_state(new, raw)
        return new

    @classmethod
    def downscale(cls, raw: pygame.Surface, source_scale: float, scale: float | None = None) -> "ScaledSurface":
        """Wrap a rendition drawn at ``source_scale`` x its logical size."""

        factor = float(scale if scale is not None else _state.scale)
        w, h = RAW.get_size(raw)
        logical = (max(1, round(w / source_scale)), max(1, round(h / source_scale)))
        source = raw if raw.get_bitsize() in (24, 32) else RAW.convert_alpha(raw) if raw.get_flags() & pygame.SRCALPHA else RAW.convert(raw)
        new = cls(logical, source.get_flags() & pygame.SRCALPHA, source, scale=factor)
        if RAW.get_size(new) == (w, h):
            _copy_pixels(new, source)
        else:
            RAW.transform.smoothscale(_matching(source, new), RAW.get_size(new), new)
            if new.get_flags() & pygame.SRCALPHA:
                _snap_opaque_alpha(new)
        _copy_format_state(new, raw)
        return new

    # -- logical geometry ---------------------------------------------------
    def get_size(self) -> tuple[int, int]:
        return self._logical()

    def get_width(self) -> int:
        return self._logical()[0]

    def get_height(self) -> int:
        return self._logical()[1]

    def get_rect(self, **kwargs: Any) -> pygame.Rect:
        rect = pygame.Rect((0, 0), self._logical())
        for key, value in kwargs.items():
            setattr(rect, key, value)
        return rect

    def get_clip(self) -> pygame.Rect:
        return _logical_rect(RAW.get_clip(self), self._scale())

    def set_clip(self, rect: Any = None) -> None:
        RAW.set_clip(self, None if rect is None else _rect(rect, self._scale()))

    def fill(self, color: Any, rect: Any = None, special_flags: int = 0) -> pygame.Rect:
        physical = None if rect is None else _rect(rect, self._scale())
        result = RAW.fill(self, color, physical, special_flags)
        return _logical_rect(result, self._scale())

    def blit(self, source: Any, dest: Any, area: Any = None, special_flags: int = 0) -> pygame.Rect:
        scale = self._scale()
        raw, source_scale = _physical_source(source, scale)
        if isinstance(dest, pygame.Rect) or (hasattr(dest, "__len__") and len(dest) == 4):
            dest = pygame.Rect(dest).topleft
        physical_dest = _point(dest, scale)
        physical_area = None if area is None else _rect(area, source_scale)
        result = RAW.blit(self, raw, physical_dest, physical_area, special_flags)
        return _logical_rect(result, scale)

    def blits(self, blit_sequence: Iterable[Any], doreturn: Any = 1) -> list[pygame.Rect] | None:
        rects = [self.blit(*item) for item in blit_sequence]
        return rects if doreturn else None

    def fblits(self, blit_sequence: Iterable[Any], special_flags: int = 0) -> None:
        for source, dest in blit_sequence:
            self.blit(source, dest, None, special_flags)

    def get_at(self, position: Any) -> pygame.Color:
        return RAW.get_at(self, _point(position, self._scale()))

    def set_at(self, position: Any, color: Any) -> None:
        scale = self._scale()
        RAW.fill(self, color, _rect((int(position[0]), int(position[1]), 1, 1), scale))

    def get_bounding_rect(self, min_alpha: int = 1) -> pygame.Rect:
        return _logical_rect(RAW.get_bounding_rect(self, min_alpha), self._scale())

    def scroll(self, dx: int = 0, dy: int = 0) -> None:
        RAW.scroll(self, _p(dx, self._scale()), _p(dy, self._scale()))

    # -- derived surfaces ---------------------------------------------------
    def copy(self) -> "ScaledSurface":
        return ScaledSurface.adopt(RAW.copy(self), self._logical(), self._scale())

    __copy__ = copy

    def convert(self, *args: Any) -> "ScaledSurface":
        return ScaledSurface.adopt(RAW.convert(self, *args), self._logical(), self._scale())

    def convert_alpha(self, *args: Any) -> "ScaledSurface":
        return ScaledSurface.adopt(RAW.convert_alpha(self, *args), self._logical(), self._scale())

    def subsurface(self, *rect: Any) -> "ScaledSurface":
        """A *copy* of the region (pixel sharing is not supported when scaled)."""

        area = pygame.Rect(*rect) if len(rect) != 1 else pygame.Rect(rect[0])
        raw = RAW.subsurface(self, _rect(area, self._scale()))
        return ScaledSurface.adopt(raw, area.size, self._scale())


def _copy_format_state(target: pygame.Surface, source: pygame.Surface) -> None:
    key = source.get_colorkey()
    if key is not None:
        target.set_colorkey(key)
    alpha = source.get_alpha()
    if alpha is not None and not source.get_flags() & pygame.SRCALPHA:
        target.set_alpha(alpha)


def _matching(source: pygame.Surface, target: pygame.Surface) -> pygame.Surface:
    """``source`` in ``target``'s pixel format (smoothscale copies bytes as-is)."""

    if source.get_bitsize() == target.get_bitsize() and source.get_masks() == target.get_masks():
        return source
    return RAW.convert(source, target)


def _snap_opaque_alpha(surface: pygame.Surface) -> None:
    """Undo smoothscale's alpha rounding (255 becomes 250-254) on solid areas.

    Left alone, a solid panel lets the layer behind it show through by a few
    levels, visible as faint ghost shapes.  Nearly-opaque pixels are restored to
    full opacity without touching their colour.
    """

    mask = RAW.mask_from_surface(surface, 245)
    solid = mask.to_surface(setcolor=(0, 0, 0, 255), unsetcolor=(0, 0, 0, 0))
    RAW.blit(surface, solid, (0, 0), None, pygame.BLEND_RGBA_MAX)


def _copy_pixels(target: pygame.Surface, source: pygame.Surface) -> None:
    """Exact pixel copy, alpha included (a normal blit would blend it)."""

    # A colour key or per-surface alpha on the source would make the blit skip
    # or fade the very pixels being copied (a keyed hole would come out black).
    key = source.get_colorkey()
    alpha = source.get_alpha()
    if key is not None:
        source.set_colorkey(None)
    if alpha is not None and alpha != 255:
        source.set_alpha(255)
    try:
        if target.get_flags() & pygame.SRCALPHA:
            RAW.fill(target, (0, 0, 0, 0))
            RAW.blit(target, source, (0, 0), None, pygame.BLEND_RGBA_MAX)
        else:
            RAW.blit(target, source, (0, 0))
    finally:
        if key is not None:
            source.set_colorkey(key)
        if alpha is not None and alpha != 255:
            source.set_alpha(alpha)
    _copy_format_state(target, source)


def _physical_source(source: Any, target_scale: float) -> tuple[pygame.Surface, float]:
    """Physical pixels of ``source`` at ``target_scale`` and the scale they use."""

    source_scale = scale_of(source)
    if abs(source_scale - target_scale) < 1e-9:
        return source, target_scale
    logical = source.get_size()
    size = (max(1, _p(logical[0], target_scale)), max(1, _p(logical[1], target_scale)))
    raw = source
    if raw.get_bitsize() not in (24, 32):
        raw = RAW.convert_alpha(raw) if raw.get_flags() & pygame.SRCALPHA else RAW.convert(raw)
    resized = RAW.transform.smoothscale(raw, size)
    _copy_format_state(resized, source)
    return resized, target_scale


# -- patched module functions -------------------------------------------------
def _draw_rect(surface, color, rect, width=0, border_radius=0, border_top_left_radius=-1,
               border_top_right_radius=-1, border_bottom_left_radius=-1, border_bottom_right_radius=-1):
    s = scale_of(surface)
    if s == 1.0:
        return RAW.draw.rect(surface, color, rect, width, border_radius, border_top_left_radius,
                             border_top_right_radius, border_bottom_left_radius, border_bottom_right_radius)
    radii = [r if r <= 0 else max(1, _p(r, s)) for r in (border_radius, border_top_left_radius,
             border_top_right_radius, border_bottom_left_radius, border_bottom_right_radius)]
    result = RAW.draw.rect(surface, color, _rect(rect, s), _width(width, s), *radii)
    return _logical_rect(result, s)


def _draw_circle(surface, color, center, radius, width=0, draw_top_right=None, draw_top_left=None,
                 draw_bottom_left=None, draw_bottom_right=None):
    s = scale_of(surface)
    quadrants = {k: v for k, v in (("draw_top_right", draw_top_right), ("draw_top_left", draw_top_left),
                 ("draw_bottom_left", draw_bottom_left), ("draw_bottom_right", draw_bottom_right)) if v is not None}
    if s == 1.0:
        return RAW.draw.circle(surface, color, center, radius, width, **quadrants)
    result = RAW.draw.circle(surface, color, _fpoint(center, s), float(radius) * s, _width(width, s), **quadrants)
    return _logical_rect(result, s)


def _draw_ellipse(surface, color, rect, width=0):
    s = scale_of(surface)
    if s == 1.0:
        return RAW.draw.ellipse(surface, color, rect, width)
    return _logical_rect(RAW.draw.ellipse(surface, color, _rect(rect, s), _width(width, s)), s)


def _draw_arc(surface, color, rect, start_angle, stop_angle, width=1):
    s = scale_of(surface)
    if s == 1.0:
        return RAW.draw.arc(surface, color, rect, start_angle, stop_angle, width)
    return _logical_rect(RAW.draw.arc(surface, color, _rect(rect, s), start_angle, stop_angle, _width(width, s)), s)


def _draw_line(surface, color, start_pos, end_pos, width=1):
    s = scale_of(surface)
    if s == 1.0:
        return RAW.draw.line(surface, color, start_pos, end_pos, width)
    return _logical_rect(RAW.draw.line(surface, color, _fpoint(start_pos, s), _fpoint(end_pos, s), _width(width, s)), s)


def _draw_lines(surface, color, closed, points, width=1):
    s = scale_of(surface)
    if s == 1.0:
        return RAW.draw.lines(surface, color, closed, points, width)
    return _logical_rect(RAW.draw.lines(surface, color, closed, [_fpoint(p, s) for p in points], _width(width, s)), s)


def _draw_aaline(surface, color, start_pos, end_pos, *args, **kwargs):
    s = scale_of(surface)
    if s == 1.0:
        return RAW.draw.aaline(surface, color, start_pos, end_pos, *args, **kwargs)
    return _logical_rect(RAW.draw.aaline(surface, color, _fpoint(start_pos, s), _fpoint(end_pos, s), *args, **kwargs), s)


def _draw_aalines(surface, color, closed, points, *args, **kwargs):
    s = scale_of(surface)
    if s == 1.0:
        return RAW.draw.aalines(surface, color, closed, points, *args, **kwargs)
    return _logical_rect(RAW.draw.aalines(surface, color, closed, [_fpoint(p, s) for p in points], *args, **kwargs), s)


def _draw_polygon(surface, color, points, width=0):
    s = scale_of(surface)
    if s == 1.0:
        return RAW.draw.polygon(surface, color, points, width)
    return _logical_rect(RAW.draw.polygon(surface, color, [_fpoint(p, s) for p in points], _width(width, s)), s)


def _resized(name: str):
    raw_function = getattr(RAW.transform, name)

    def resize(surface, size, dest_surface=None):
        s = scale_of(surface)
        if s == 1.0 and scale_of(dest_surface) == 1.0:
            if dest_surface is None:
                return raw_function(surface, size)
            return raw_function(surface, size, dest_surface)
        logical = (int(size[0]), int(size[1]))
        target = dest_surface if dest_surface is not None else ScaledSurface(
            logical, surface.get_flags() & pygame.SRCALPHA, surface, scale=s
        )
        source = surface if s == scale_of(target) else _physical_source(surface, scale_of(target))[0]
        raw_function(_matching(source, target), RAW.get_size(target), target)
        return target

    return resize


def _resized_by(name: str, base: str):
    def resize_by(surface, factor, dest_surface=None):
        fx, fy = (factor, factor) if not hasattr(factor, "__len__") else factor
        width, height = surface.get_size()
        return getattr(pygame.transform, base)(surface, (round(width * fx), round(height * fy)), dest_surface)

    return resize_by


def _geometric(name: str):
    raw_function = getattr(RAW.transform, name)

    def transform(surface, *args):
        s = scale_of(surface)
        if s == 1.0:
            return raw_function(surface, *args)
        raw = raw_function(surface, *args)
        w, h = RAW.get_size(raw)
        return ScaledSurface.adopt(raw, (max(1, round(w / s)), max(1, round(h / s))), s)

    return transform


def _average_color(surface, rect=None, consider_alpha=False):
    s = scale_of(surface)
    if s == 1.0:
        return RAW.transform.average_color(surface, rect, consider_alpha)
    return RAW.transform.average_color(surface, None if rect is None else _rect(rect, s), consider_alpha)


def _chop(surface, rect):
    s = scale_of(surface)
    if s == 1.0:
        return RAW.transform.chop(surface, rect)
    raw = RAW.transform.chop(surface, _rect(rect, s))
    w, h = RAW.get_size(raw)
    return ScaledSurface.adopt(raw, (max(1, round(w / s)), max(1, round(h / s))), s)


#: Sibling rendition rendered from the same SVG at twice the 1x pixel size.
HIRES_SUFFIX = "@2x"


def _hires_sibling(source: Any) -> str | None:
    if not isinstance(source, (str, os.PathLike)):
        return None
    path = os.fspath(source)
    stem, extension = os.path.splitext(path)
    if not extension or stem.endswith(HIRES_SUFFIX):
        return None
    sibling = f"{stem}{HIRES_SUFFIX}{extension}"
    return sibling if os.path.isfile(sibling) else None


def _image_load(*args, **kwargs):
    sibling = _hires_sibling(args[0]) if args and _state.scale > 1.0 else None
    if sibling is not None:
        try:
            return ScaledSurface.downscale(RAW.image_load(sibling), 2.0)
        except (pygame.error, OSError, ValueError):
            pass  # a damaged rendition falls back to the 1x file
    return ScaledSurface.upscale(RAW.image_load(*args, **kwargs))


def _image_from(raw_function):
    def load(*args, **kwargs):
        return ScaledSurface.upscale(raw_function(*args, **kwargs))

    return load


class ScaledFont(RAW.Font):
    """A font rasterised at physical size whose metrics are logical."""

    def __init__(self, file: Any = None, size: int = 20, *args: Any) -> None:
        self._greia_scale = _state.scale
        super().__init__(file, max(1, _p(size, self._greia_scale)), *args)

    def render(self, text: Any, antialias: Any, color: Any, background: Any = None, *args: Any) -> ScaledSurface:
        raw = super().render(text, antialias, color, background, *args)
        w, h = RAW.get_size(raw)
        s = self._greia_scale
        return ScaledSurface.adopt(raw, (max(1, math.ceil(w / s)), max(1, math.ceil(h / s))), s)

    def size(self, text: Any) -> tuple[int, int]:
        w, h = super().size(text)
        return (math.ceil(w / self._greia_scale), math.ceil(h / self._greia_scale))

    def get_height(self) -> int:
        return max(1, round(super().get_height() / self._greia_scale))

    def get_linesize(self) -> int:
        return max(1, round(super().get_linesize() / self._greia_scale))

    def get_ascent(self) -> int:
        return round(super().get_ascent() / self._greia_scale)

    def get_descent(self) -> int:
        return round(super().get_descent() / self._greia_scale)

    def metrics(self, text: Any) -> list[Any]:
        s = self._greia_scale
        return [None if m is None else tuple(round(v / s) for v in m) for m in super().metrics(text)]


def _mask_from_surface(surface: Any, threshold: int = 127) -> pygame.mask.Mask:
    """``pygame.mask.from_surface`` in logical units for a scaled surface.

    Activities use masks for opaque bounds and hit tests in the coordinates
    they lay out in; a physical-resolution mask would silently change every
    derived size.
    """

    scale = scale_of(surface)
    if scale == 1.0:
        return RAW.mask_from_surface(surface, threshold)
    source = surface if surface.get_bitsize() in (24, 32) else RAW.convert_alpha(surface)
    logical = surface.get_size()
    reduced = RAW.transform.smoothscale(source, logical)
    return RAW.mask_from_surface(reduced, threshold)


def activate(scale: float) -> None:
    """Install the layer for this process (idempotent; updates the scale)."""

    _state.scale = float(scale)
    if _state.active:
        return
    _state.active = True
    pygame.Surface = ScaledSurface  # type: ignore[misc]
    pygame.surface.Surface = ScaledSurface  # type: ignore[misc]
    for name, function in (
        ("rect", _draw_rect), ("circle", _draw_circle), ("ellipse", _draw_ellipse), ("arc", _draw_arc),
        ("line", _draw_line), ("lines", _draw_lines), ("aaline", _draw_aaline),
        ("aalines", _draw_aalines), ("polygon", _draw_polygon),
    ):
        setattr(pygame.draw, name, function)
    pygame.transform.scale = _resized("scale")
    pygame.transform.smoothscale = _resized("smoothscale")
    if hasattr(RAW.transform, "scale_by"):
        pygame.transform.scale_by = _resized_by("scale_by", "scale")
    if hasattr(RAW.transform, "smoothscale_by"):
        pygame.transform.smoothscale_by = _resized_by("smoothscale_by", "smoothscale")
    for name in ("rotate", "rotozoom", "flip", "grayscale"):
        if hasattr(RAW.transform, name):
            setattr(pygame.transform, name, _geometric(name))
    pygame.transform.average_color = _average_color
    if hasattr(RAW.transform, "chop"):
        pygame.transform.chop = _chop
    pygame.image.load = _image_load
    if RAW.image_fromstring is not None:
        pygame.image.fromstring = _image_from(RAW.image_fromstring)
    if RAW.image_frombytes is not None:
        pygame.image.frombytes = _image_from(RAW.image_frombytes)
    pygame.font.Font = ScaledFont  # type: ignore[misc]
    pygame.mask.from_surface = _mask_from_surface


def deactivate() -> None:
    """Restore the original pygame callables (tests and diagnostics)."""

    if not _state.active:
        return
    _state.active = False
    _state.scale = 1.0
    pygame.Surface = RAW.Surface  # type: ignore[misc]
    pygame.surface.Surface = RAW.Surface  # type: ignore[misc]
    for name in vars(RAW.draw):
        setattr(pygame.draw, name, getattr(RAW.draw, name))
    for name in vars(RAW.transform):
        setattr(pygame.transform, name, getattr(RAW.transform, name))
    pygame.image.load = RAW.image_load
    if RAW.image_fromstring is not None:
        pygame.image.fromstring = RAW.image_fromstring
    if RAW.image_frombytes is not None:
        pygame.image.frombytes = RAW.image_frombytes
    pygame.font.Font = RAW.Font  # type: ignore[misc]
    pygame.mask.from_surface = RAW.mask_from_surface


__all__ = [
    "HIRES_ENVIRONMENT",
    "HIRES_MIN_SCALE",
    "HIRES_SUFFIX",
    "RAW",
    "ScaledFont",
    "ScaledSurface",
    "activate",
    "deactivate",
    "hires_scale_for",
    "is_active",
    "physical_rect",
    "scale_of",
]
