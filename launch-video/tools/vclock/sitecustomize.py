"""Virtual clock for deterministic Activity capture (launch-video tooling, never shipped).

Loaded automatically in the child process when this directory is first on PYTHONPATH.
Env: VCLOCK_SCRIPT (json: {"duration": s, "settle": s, "events": [...]}), VCLOCK_OUT (frame dir), VCLOCK_FPS.
Time only advances when the main thread sleeps/waits, so the frame rate of the capture does not depend on
machine load. Scripted pointer/key events are posted into pygame's queue by virtual time; every 1/FPS of
virtual time the display surface is written as a PNG.
"""
import json
import os
import sys
import threading
import time as _time

_SCRIPT = os.environ.get("VCLOCK_SCRIPT")
if _SCRIPT:
    spec = json.load(open(_SCRIPT))
    OUT = os.environ["VCLOCK_OUT"]
    FPS = float(os.environ.get("VCLOCK_FPS", "30"))
    os.makedirs(OUT, exist_ok=True)
    MAIN = threading.main_thread()
    V = {"t": 1000.0, "origin": None, "n": 0, "next": None, "mx": 0, "my": 0, "down": False, "ev": 0}
    EVENTS = sorted(spec["events"], key=lambda e: e["t"])
    SETTLE = float(spec.get("settle", 1.0))
    DURATION = float(spec["duration"])
    _real_sleep = _time.sleep

    def _is_main():
        return threading.current_thread() is MAIN

    def vmono():
        return V["t"]

    _time.monotonic = vmono
    _time.perf_counter = vmono
    _time.monotonic_ns = lambda: int(V["t"] * 1e9)
    _time.perf_counter_ns = lambda: int(V["t"] * 1e9)
    _t0 = _time.time()
    _time.time = lambda: _t0 + (V["t"] - 1000.0)

    def vsleep(x):
        if _is_main():
            V["t"] += max(0.0, float(x))
            _drive()
        else:
            _real_sleep(min(float(x), 0.002))

    _time.sleep = vsleep

    import random as _random  # noqa: E402
    _SEED = int(os.environ.get("VCLOCK_SEED", "7"))
    _orig_init = _random.Random.__init__

    def _seeded_init(self, x=None):
        _orig_init(self, _SEED if x is None else x)

    _random.Random.__init__ = _seeded_init
    _random.seed(_SEED)

    import pygame  # noqa: E402

    class VClock:
        def __init__(self):
            self._last = V["t"]

        def tick(self, fps=0):
            if fps:
                V["t"] += 1.0 / fps
            dt = V["t"] - self._last
            self._last = V["t"]
            return int(dt * 1000)

        def tick_busy_loop(self, fps=0):
            return self.tick(fps)

        def get_fps(self):
            return FPS

        def get_time(self):
            return 33

        def get_rawtime(self):
            return 5

    pygame.time.Clock = VClock
    pygame.time.get_ticks = lambda: int((V["t"] - 1000.0) * 1000)
    pygame.time.wait = lambda ms: (vsleep(ms / 1000.0) or ms)
    pygame.time.delay = pygame.time.wait

    def _post(e):
        k = e["type"]
        if k == "move":
            rel = (e["x"] - V["mx"], e["y"] - V["my"]); V["mx"], V["my"] = e["x"], e["y"]
            pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(e["x"], e["y"]), rel=rel, buttons=(1 if V["down"] else 0, 0, 0)))
        elif k in ("down", "up", "click"):
            x, y = e.get("x", V["mx"]), e.get("y", V["my"])
            if (x, y) != (V["mx"], V["my"]):
                _post(dict(type="move", x=x, y=y))
            if k in ("down", "click"):
                V["down"] = True
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1))
            if k in ("up", "click"):
                V["down"] = False
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(x, y), button=1))
        elif k == "key":
            code = getattr(pygame, "K_" + e["key"].upper(), None) or getattr(pygame, "K_" + e["key"].lower(), None)
            if code is not None:
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=code))
                pygame.event.post(pygame.event.Event(pygame.KEYUP, key=code))

    def _due():
        if V["origin"] is None:
            return
        rel = V["t"] - V["origin"] - SETTLE
        while V["ev"] < len(EVENTS) and EVENTS[V["ev"]]["t"] <= rel:
            _post(EVENTS[V["ev"]]); V["ev"] += 1

    def _drive():
        if V["origin"] is not None and V["t"] - V["origin"] - SETTLE > DURATION:
            sys.stdout.write("VCLOCK_DONE %d\n" % V["n"]); sys.stdout.flush()
            os._exit(0)

    def _capture():
        surf = pygame.display.get_surface()
        if surf is None:
            return
        if V["origin"] is None:
            V["origin"] = V["t"]; V["next"] = V["t"] + SETTLE
        while V["t"] >= V["next"] - 1e-9:
            pygame.image.save(surf, os.path.join(OUT, "f%05d.png" % V["n"]))
            V["n"] += 1; V["next"] += 1.0 / FPS
            if V["n"] > 4000:
                os._exit(3)

    _flip, _upd = pygame.display.flip, pygame.display.update

    def vflip(*a, **k):
        r = _flip(*a, **k); _capture(); _due(); return r

    def vupdate(*a, **k):
        r = _upd(*a, **k); _capture(); _due(); return r

    pygame.display.flip, pygame.display.update = vflip, vupdate
    _eget, _epoll, _epeek, _ewait = pygame.event.get, pygame.event.poll, pygame.event.peek, pygame.event.wait

    def eget(*a, **k):
        _due()
        out = _eget(*a, **k)
        return [e for e in out if not (e.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and not hasattr(e, "pos"))]

    def epoll(*a, **k):
        _due(); return _epoll(*a, **k)

    def epeek(*a, **k):
        _due(); return _epeek(*a, **k)

    def ewait(timeout=0):
        _due()
        if timeout:
            vsleep(timeout / 1000.0)
        return _epoll()

    pygame.event.get, pygame.event.poll, pygame.event.peek, pygame.event.wait = eget, epoll, epeek, ewait
    pygame.mouse.get_pos = lambda: (V["mx"], V["my"])
    pygame.mouse.get_pressed = lambda *a, **k: (V["down"], False, False)
