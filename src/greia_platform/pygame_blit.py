"""Fast-blit preparation for Pygame Activities on the Atom reference floor.

Measured on the developer Acer (Atom N270, Debian pygame 2.1.2 / SDL 2.26.5,
X11, 32-bit XRGB display, 2026-10-16), blitting onto a 1024x600 canvas:

* opaque display-format surface (``convert()``), full frame: ~2 ms;
* per-pixel-alpha surface (``convert_alpha()``), full frame: **~134 ms**,
  whatever the pixels' alpha (SDL's generic alpha path, ~0.22 us/pixel);
* the same surface with SDL RLE acceleration: ~1.5 ms when its pixels are
  mostly opaque/transparent, ~16 ns/pixel when every pixel is translucent;
  the result is identical within 1/255 per channel.

So a scrolling scene built from alpha layers (parallax bands, ground strips,
sprites) costs 150-250 ms per frame un-encoded and a few ms RLE-encoded.
Every *static* alpha surface an Activity blits per frame should come from
:func:`prepare_static`.

RLE caveats (SDL semantics, not Greia policy):

* drawing on, ``get_at``, ``smoothscale``/``rotozoom`` from or ``subsurface``
  of an RLE surface locks it, which decodes and re-encodes it: prepare the
  *final* surface once, never something you still draw on;
* SDL encodes lazily, at the first blit (``copy()`` keeps the request);
  ``set_alpha(x)`` without ``RLEACCEL`` drops the request, and SDL cannot
  RLE a per-pixel-alpha surface while a per-surface alpha is set. For fades use :class:`FadeSteps` (alpha baked
  into a few RLE copies) instead of ``set_alpha`` per frame;
* blit RLE surfaces onto *opaque* targets only (the canvas, the display, a
  ``convert()``-ed cache).  Onto a per-pixel-alpha surface SDL's RLE alpha
  blit writes opaque destination alpha, so translucent edges turn into dark
  fringes there (measured on SDL 2.26.5 and 2.28.4);
  :meth:`PreparedSurfaces.for_target` picks the right surface for a target.

:class:`HudOverlay` covers the other common cost: a HUD/control layer drawn
every frame over a moving scene. It composes the HUD once into a transparent
RLE overlay and re-composes it only when its key changes or it is invalidated.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Hashable

import pygame

__all__ = ["FadeSteps", "HudOverlay", "PreparedSurfaces", "is_rle", "prepare_static"]


def is_rle(surface: pygame.Surface) -> bool:
    """True when SDL RLE acceleration is requested (or active) for ``surface``."""

    return bool(surface.get_flags() & (pygame.RLEACCELOK | pygame.RLEACCEL))


def prepare_static(surface: pygame.Surface) -> pygame.Surface:
    """Return a new display-format copy of ``surface`` that blits fast.

    Per-pixel-alpha surfaces become ``convert_alpha()`` + RLE, others
    ``convert()``; a colorkey survives and is RLE-encoded too. Without a
    display (headless tests) the copy keeps its format but still requests
    RLE, so behaviour is the same. The input surface is never modified, so
    surfaces shared through a loader cache stay untouched.
    """

    alpha = bool(surface.get_flags() & pygame.SRCALPHA)
    if pygame.display.get_init() and pygame.display.get_surface() is not None:
        prepared = surface.convert_alpha() if alpha else surface.convert()
    else:
        prepared = surface.copy()
    if alpha:
        prepared.set_alpha(255, pygame.RLEACCEL)
    else:
        key = surface.get_colorkey()
        if key is not None:
            prepared.set_colorkey(key, pygame.RLEACCEL)
    return prepared


class PreparedSurfaces:
    """Bounded identity-keyed cache of :func:`prepare_static` copies.

    For renderers that blit surfaces owned by someone else's cache (the
    shared ``ControlArt`` loader, a cast, a kit painter):
    ``target.blit(fast(image), pos)`` blits an RLE copy made the first time
    that exact surface object is seen. The cache keeps a reference to each
    source, so an id is never reused while cached; it is bounded by entries
    and by total pixels (LRU). Only pass surfaces that are *not drawn on*
    after they were first blitted (a mutated source would show stale pixels),
    and never one carrying a per-surface ``set_alpha`` fade: use
    ``fast.faded(image, fraction)`` instead of ``set_alpha`` + ``blit``.
    """

    def __init__(self, *, max_entries: int = 64, max_pixels: int = 1024 * 600 * 3) -> None:
        if max_entries < 1 or max_pixels < 1:
            raise ValueError("bounds must be positive")
        self.max_entries = int(max_entries)
        self.max_pixels = int(max_pixels)
        self._items: OrderedDict[int, tuple[pygame.Surface, pygame.Surface]] = OrderedDict()
        self._pixels = 0
        self._fades: OrderedDict[int, tuple[pygame.Surface, FadeSteps]] = OrderedDict()

    def __len__(self) -> int:
        return len(self._items)

    @property
    def cached_pixels(self) -> int:
        return self._pixels

    def __call__(self, surface: pygame.Surface | None) -> pygame.Surface | None:
        if surface is None:
            return None
        key = id(surface)
        entry = self._items.get(key)
        if entry is not None and entry[0] is surface:
            self._items.move_to_end(key)
            return entry[1]
        if entry is not None:
            self._forget(key)
        if is_rle(surface) or not (surface.get_flags() & pygame.SRCALPHA or surface.get_colorkey() is not None):
            return surface  # already fast (RLE or opaque): no copy needed
        prepared = prepare_static(surface)
        self._items[key] = (surface, prepared)
        self._pixels += surface.get_width() * surface.get_height()
        while len(self._items) > self.max_entries or (self._pixels > self.max_pixels and len(self._items) > 1):
            self._forget(next(iter(self._items)))
        return prepared

    def for_target(self, surface: pygame.Surface, target: pygame.Surface) -> pygame.Surface:
        """``surface`` ready to blit onto ``target``.

        The cached RLE copy for an opaque target; ``surface`` itself for a
        per-pixel-alpha target (see the module notes) or for objects that are
        not Pygame surfaces (provider-free test doubles).
        """

        if not isinstance(surface, pygame.Surface) or not isinstance(target, pygame.Surface):
            return surface
        if target.get_flags() & pygame.SRCALPHA:
            return surface
        prepared = self(surface)
        return surface if prepared is None else prepared

    def faded(self, surface: pygame.Surface | None, fraction: float, *, steps: int = 8) -> pygame.Surface | None:
        """``surface`` at opacity ``fraction`` (0..1) from baked :class:`FadeSteps`.

        Replaces ``image.set_alpha(a); target.blit(image, ...)``; returns None
        when nothing is visible. Bounded by ``max_entries`` sources.
        """

        if surface is None:
            return None
        if fraction >= 1.0:
            return self(surface)
        key = id(surface)
        entry = self._fades.get(key)
        if entry is None or entry[0] is not surface:
            entry = (surface, FadeSteps(surface, steps=steps))
            self._fades[key] = entry
            while len(self._fades) > self.max_entries:
                self._fades.popitem(last=False)
        else:
            self._fades.move_to_end(key)
        return entry[1].at(fraction)

    def _forget(self, key: int) -> None:
        source, _ = self._items.pop(key)
        self._pixels -= source.get_width() * source.get_height()

    def clear(self) -> None:
        self._items.clear()
        self._fades.clear()
        self._pixels = 0


class FadeSteps:
    """A few pre-faded RLE copies of one sprite, instead of per-frame ``set_alpha``.

    ``set_alpha(x)`` on a per-pixel-alpha sprite forces SDL's slow blend
    path every frame. ``FadeSteps(surface, steps=8).at(0.4)`` returns the
    nearest pre-baked level (``0`` -> None, nothing to draw). Bounded: at
    most ``steps`` surfaces, built lazily.
    """

    def __init__(self, surface: pygame.Surface, *, steps: int = 8) -> None:
        if steps < 1:
            raise ValueError("steps must be positive")
        self._source = surface.copy()
        if not self._source.get_flags() & pygame.SRCALPHA:
            self._source = self._source.convert_alpha() if pygame.display.get_surface() is not None else _with_alpha(self._source)
        self.steps = int(steps)
        self._levels: dict[int, pygame.Surface] = {}

    def level(self, fraction: float) -> int:
        """The level (0..steps) used for opacity ``fraction`` (0..1)."""

        return int(round(max(0.0, min(1.0, float(fraction))) * self.steps))

    def at(self, fraction: float) -> pygame.Surface | None:
        level = self.level(fraction)
        if level == 0:
            return None
        cached = self._levels.get(level)
        if cached is not None:
            return cached
        faded = self._source.copy()
        if level < self.steps:
            alpha = int(round(255 * level / self.steps))
            faded.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        prepared = prepare_static(faded)
        self._levels[level] = prepared
        return prepared


class HudOverlay:
    """A HUD layer composed once into a transparent RLE overlay.

    For Activities whose scene moves every frame while the controls on top
    stay still: ``draw(target, key, render)`` calls ``render(overlay)`` only
    when ``key`` (any hashable summary of what the HUD shows: pressed
    states, counters, ...) differs from the last composition, the target
    size changed or ``invalidate()`` was called, then blits the cached
    overlay. ``render`` draws exactly what it would draw on the scene (for
    example ``layer.draw``); compositing on a transparent surface first gives
    the same pixels for non-overlapping controls (translucent pixels of
    overlapping controls may differ by rounding only).
    """

    def __init__(self) -> None:
        self._overlay: pygame.Surface | None = None
        self._work: pygame.Surface | None = None
        self._key: Hashable | None = None
        self._stale = True
        self.compositions = 0

    def invalidate(self) -> None:
        self._stale = True

    def clear(self) -> None:
        """Drop both surfaces (call when the Activity leaves the screen)."""

        self._overlay = None
        self._work = None
        self._stale = True

    def draw(
        self,
        target: pygame.Surface,
        key: Hashable,
        render: Callable[[pygame.Surface], object],
        *,
        stale: bool = False,
    ) -> bool:
        """Blit the overlay onto ``target``; returns True when it was re-composed."""

        size = target.get_size()
        recomposed = False
        if (
            stale
            or self._stale
            or self._overlay is None
            or self._overlay.get_size() != size
            or key != self._key
        ):
            work = self._work
            if work is None or work.get_size() != size:
                work = pygame.Surface(size, pygame.SRCALPHA)
                self._work = work
            work.fill((0, 0, 0, 0))
            render(work)
            # Encode a copy: drawing on an RLE surface would re-encode it on
            # every primitive, so the work surface itself never gets RLE.
            self._overlay = prepare_static(work)
            self._key = key
            self._stale = False
            self.compositions += 1
            recomposed = True
        target.blit(self._overlay, (0, 0))
        return recomposed


def _with_alpha(surface: pygame.Surface) -> pygame.Surface:
    converted = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    converted.blit(surface, (0, 0))
    return converted
