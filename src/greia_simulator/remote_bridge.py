from __future__ import annotations

import io
import json
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Mapping
from urllib.parse import parse_qs, urlparse


DEFAULT_REMOTE_PORT = 8767

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Greia Activity Simulator — Live Canvas</title>
  <style>
    :root {
      --bg: #1c1815;
      --card: #2c2520;
      --text: #f5f0e8;
      --accent: #f1b923;
      --border: #443a32;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 100vh;
      padding: 16px;
    }
    header {
      width: 100%;
      max-width: 1024px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    h1 { font-size: 1.25rem; font-weight: 600; display: flex; align-items: center; gap: 8px; }
    .badge {
      font-size: 0.75rem;
      background: var(--accent);
      color: #3d2c1f;
      padding: 2px 8px;
      border-radius: 999px;
      font-weight: 700;
    }
    .status-bar {
      font-size: 0.85rem;
      color: #a09080;
      display: flex;
      gap: 16px;
    }
    #viewport-container {
      position: relative;
      background: #000;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
      border: 2px solid var(--border);
      cursor: crosshair;
    }
    canvas { display: block; max-width: 100vw; height: auto; }
    .controls {
      width: 100%;
      max-width: 1024px;
      margin-top: 16px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }
    .control-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
    }
    .control-card h3 { font-size: 0.85rem; text-transform: uppercase; color: #a09080; margin-bottom: 8px; }
    .btn-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
    button {
      background: #3d342d;
      border: 1px solid #5a4e44;
      color: var(--text);
      padding: 8px;
      border-radius: 6px;
      font-size: 0.85rem;
      cursor: pointer;
      font-weight: 500;
      transition: background 0.1s;
    }
    button:hover { background: #4f433a; }
    button:active { background: var(--accent); color: #3d2c1f; }
    button.primary { background: var(--accent); color: #3d2c1f; font-weight: 700; border: none; }
    button.primary:hover { background: #e0a91a; }
    input[type="text"] {
      width: 100%;
      padding: 8px;
      background: #1c1815;
      border: 1px solid var(--border);
      color: var(--text);
      border-radius: 6px;
      margin-bottom: 6px;
    }
    .hint { font-size: 0.75rem; color: #887868; margin-top: 4px; }
  </style>
</head>
<body>
  <header>
    <h1>Greia OS Simulator <span class="badge" id="mode-badge">INITIALIZING</span></h1>
    <div class="status-bar">
      <span id="res-label">Resolution: --</span>
      <span id="fps-label">FPS: --</span>
    </div>
  </header>

  <div id="viewport-container">
    <canvas id="screen" width="1024" height="600" tabindex="0"></canvas>
  </div>

  <div class="controls">
    <div class="control-card">
      <h3>Navigation Controls</h3>
      <div class="btn-grid">
        <div></div>
        <button onclick="sendKey('UP')">▲</button>
        <div></div>
        <button onclick="sendKey('LEFT')">◀</button>
        <button class="primary" onclick="sendKey('RETURN')">Enter</button>
        <button onclick="sendKey('RIGHT')">▶</button>
        <button onclick="sendKey('ESCAPE')">Esc</button>
        <button onclick="sendKey('DOWN')">▼</button>
        <button onclick="sendKey('TAB')">Tab</button>
      </div>
      <div class="hint">Or click canvas and use your keyboard directly!</div>
    </div>

    <div class="control-card">
      <h3>Parent Settings Chord</h3>
      <button class="primary" style="width: 100%; padding: 12px;" onclick="sendChord('s', 't', 5.0)">
        Hold 's' + 't' for 5 seconds
      </button>
      <div class="hint">Triggers the on-device Parent Settings Panel.</div>
    </div>

    <div class="control-card">
      <h3>Text Input</h3>
      <input type="text" id="text-input" placeholder="Type text to send..." onkeydown="if(event.key==='Enter')sendText()">
      <button style="width: 100%;" onclick="sendText()">Send Text Input</button>
    </div>
  </div>

  <script>
    const canvas = document.getElementById('screen');
    const ctx = canvas.getContext('2d');
    const modeBadge = document.getElementById('mode-badge');
    const resLabel = document.getElementById('res-label');
    const fpsLabel = document.getElementById('fps-label');
    let nativeWidth = 1024;
    let nativeHeight = 600;

    // Frame polling loop (~30 fps)
    let lastFrameTime = performance.now();
    let frameCount = 0;
    let fps = 30;

    function refreshFrame() {
      const img = new Image();
      img.onload = () => {
        if (img.width !== nativeWidth || img.height !== nativeHeight) {
          nativeWidth = img.width;
          nativeHeight = img.height;
          canvas.width = nativeWidth;
          canvas.height = nativeHeight;
          resLabel.textContent = `Resolution: ${nativeWidth}x${nativeHeight}`;
        }
        ctx.drawImage(img, 0, 0);
        frameCount++;
        const now = performance.now();
        if (now - lastFrameTime >= 1000) {
          fps = Math.round((frameCount * 1000) / (now - lastFrameTime));
          fpsLabel.textContent = `FPS: ${fps}`;
          frameCount = 0;
          lastFrameTime = now;
        }
        setTimeout(refreshFrame, 25);
      };
      img.onerror = () => {
        setTimeout(refreshFrame, 200);
      };
      img.src = '/api/frame?t=' + performance.now();
    }

    // State polling
    setInterval(() => {
      fetch('/api/state')
        .then(r => r.json())
        .then(state => {
          if (state && state.mode) {
            modeBadge.textContent = state.mode.toUpperCase();
          }
        }).catch(() => {});
    }, 1000);

    refreshFrame();

    function sendKey(keyName, action = 'press') {
      fetch('/api/input/key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: keyName, action: action })
      });
    }

    function sendText() {
      const input = document.getElementById('text-input');
      const text = input.value;
      if (!text) return;
      fetch('/api/input/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text })
      });
      input.value = '';
    }

    function sendChord(key1, key2, duration) {
      fetch('/api/input/chord', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keys: [key1, key2], duration: duration })
      });
    }

    function sendMouse(x, y, action, button = 1) {
      fetch('/api/input/mouse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ x: Math.round(x), y: Math.round(y), action: action, button: button })
      });
    }

    function getCanvasCoords(event) {
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      return {
        x: (event.clientX - rect.left) * scaleX,
        y: (event.clientY - rect.top) * scaleY
      };
    }

    canvas.addEventListener('mousedown', e => {
      const { x, y } = getCanvasCoords(e);
      sendMouse(x, y, 'down', e.button === 2 ? 3 : 1);
    });

    canvas.addEventListener('mouseup', e => {
      const { x, y } = getCanvasCoords(e);
      sendMouse(x, y, 'up', e.button === 2 ? 3 : 1);
    });

    canvas.addEventListener('mousemove', e => {
      const { x, y } = getCanvasCoords(e);
      sendMouse(x, y, 'move', 0);
    });

    canvas.addEventListener('contextmenu', e => e.preventDefault());

    // Keyboard capture on canvas
    const KEY_MAP = {
      'ArrowLeft': 'LEFT',
      'ArrowRight': 'RIGHT',
      'ArrowUp': 'UP',
      'ArrowDown': 'DOWN',
      'Enter': 'RETURN',
      'Escape': 'ESCAPE',
      'Tab': 'TAB',
      ' ': 'SPACE',
      'Backspace': 'BACKSPACE'
    };

    window.addEventListener('keydown', e => {
      if (document.activeElement === document.getElementById('text-input')) return;
      const mapped = KEY_MAP[e.key] || (e.key.length === 1 ? e.key.toLowerCase() : null);
      if (mapped) {
        sendKey(mapped, 'down');
        e.preventDefault();
      }
    });

    window.addEventListener('keyup', e => {
      if (document.activeElement === document.getElementById('text-input')) return;
      const mapped = KEY_MAP[e.key] || (e.key.length === 1 ? e.key.toLowerCase() : null);
      if (mapped) {
        sendKey(mapped, 'up');
        e.preventDefault();
      }
    });
  </script>
</body>
</html>
"""


class RemoteBridgeRequestHandler(BaseHTTPRequestHandler):
    bridge: SimulatorRemoteBridge

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"", "/"}:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(HTML_PAGE.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        if parsed.path == "/api/frame":
            png_bytes = self.bridge.get_latest_frame_png()
            if png_bytes is None:
                self.send_response(503)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(png_bytes)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(png_bytes)
            return

        if parsed.path == "/api/state":
            payload = json.dumps(self.bridge.get_state()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if parsed.path == "/api/events":
            events = self.bridge.drain_events()
            self._send_json({"events": events})
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        if parsed.path == "/api/frame":
            self.bridge.set_external_frame_png(body)
            self._send_json({"ok": True})
            return

        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            data = {}

        if parsed.path == "/api/input/key":
            key_name = str(data.get("key", "")).upper()
            action = str(data.get("action", "press")).lower()
            self.bridge.queue_key(key_name, action=action)
            self._send_json({"ok": True})
            return

        if parsed.path == "/api/input/text":
            text = str(data.get("text", ""))
            self.bridge.queue_text(text)
            self._send_json({"ok": True})
            return

        if parsed.path == "/api/input/mouse":
            x = int(data.get("x", 0))
            y = int(data.get("y", 0))
            action = str(data.get("action", "click")).lower()
            button = int(data.get("button", 1))
            self.bridge.queue_mouse(x, y, action=action, button=button)
            self._send_json({"ok": True})
            return

        if parsed.path == "/api/input/chord":
            keys = [str(k) for k in data.get("keys", ["s", "t"])]
            duration = float(data.get("duration", 5.0))
            self.bridge.trigger_chord_async(keys, duration)
            self._send_json({"ok": True, "keys": keys, "duration": duration})
            return

        self.send_response(404)
        self.end_headers()

    def _send_json(self, data: Mapping[str, Any], status: int = 200) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # Suppress noisy HTTP request logging to keep console clean
        pass


class SimulatorRemoteBridge:
    """Loopback remote bridge and interactive canvas for the Activity Simulator."""

    def __init__(self, port: int = DEFAULT_REMOTE_PORT, host: str = "127.0.0.1") -> None:
        self.host = host
        self.port = port
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._running = False

        self._frame_lock = threading.Lock()
        self._latest_png: bytes | None = None
        self._latest_time = 0.0
        self._frame_count = 0
        self._resolution = (1024, 600)
        self._mode = "profiles"

        self._input_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=128)

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> None:
        if self._running:
            return
        handler_class = type(
            "BoundRemoteBridgeHandler",
            (RemoteBridgeRequestHandler,),
            {"bridge": self},
        )
        try:
            self._server = HTTPServer((self.host, self.port), handler_class)
        except OSError:
            # Fall back to dynamically assigned port if default is occupied
            self._server = HTTPServer((self.host, 0), handler_class)

        self.port = self._server.server_address[1]
        self._running = True
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="greia-simulator-bridge",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    def capture_frame(self, surface: Any, pygame: Any, mode: str = "profiles") -> None:
        """Capture Pygame screen surface into double-buffered PNG bytes."""
        try:
            data = pygame.image.tobytes(surface, "RGBA")
            width, height = surface.get_size()
            # Convert RGBA to PNG via PIL / Pillow or direct Pygame save
            from PIL import Image

            img = Image.frombytes("RGBA", (width, height), data)
            bio = io.BytesIO()
            img.save(bio, format="PNG", compress_level=1)
            png_bytes = bio.getvalue()

            with self._frame_lock:
                self._latest_png = png_bytes
                self._latest_time = time.monotonic()
                self._frame_count += 1
                self._resolution = (width, height)
                self._mode = mode
        except Exception:
            pass

    def get_latest_frame_png(self) -> bytes | None:
        with self._frame_lock:
            return self._latest_png

    def get_state(self) -> dict[str, Any]:
        with self._frame_lock:
            return {
                "mode": self._mode,
                "resolution": list(self._resolution),
                "frame_count": self._frame_count,
                "timestamp": self._latest_time,
                "url": self.url,
            }

    def queue_key(self, key_name: str, action: str = "press") -> None:
        try:
            self._input_queue.put_nowait({
                "type": "key",
                "key": key_name,
                "action": action,
            })
        except queue.Full:
            pass

    def queue_text(self, text: str) -> None:
        try:
            self._input_queue.put_nowait({
                "type": "text",
                "text": text,
            })
        except queue.Full:
            pass

    def queue_mouse(self, x: int, y: int, action: str = "click", button: int = 1) -> None:
        try:
            self._input_queue.put_nowait({
                "type": "mouse",
                "x": x,
                "y": y,
                "action": action,
                "button": button,
            })
        except queue.Full:
            pass

    def trigger_chord_async(self, keys: list[str], duration: float = 5.0) -> None:
        def _runner() -> None:
            for k in keys:
                self.queue_key(k, action="down")
            time.sleep(duration + 0.15)
            for k in keys:
                self.queue_key(k, action="up")

        threading.Thread(target=_runner, name="greia-sim-chord", daemon=True).start()

    def poll_events(self, pygame: Any) -> list[Any]:
        """Convert queued bridge events into Pygame events."""
        events: list[Any] = []
        while True:
            try:
                item = self._input_queue.get_nowait()
            except queue.Empty:
                break

            ev_type = item.get("type")
            if ev_type == "key":
                key_code = self._resolve_pygame_key(item.get("key", ""), pygame)
                action = item.get("action", "press")
                if key_code is not None:
                    if action in {"down", "press"}:
                        events.append(pygame.event.Event(pygame.KEYDOWN, key=key_code))
                    if action in {"up", "press"}:
                        events.append(pygame.event.Event(pygame.KEYUP, key=key_code))

            elif ev_type == "text":
                text = str(item.get("text", ""))
                if text:
                    events.append(pygame.event.Event(pygame.TEXTINPUT, text=text))

            elif ev_type == "mouse":
                x = int(item.get("x", 0))
                y = int(item.get("y", 0))
                action = item.get("action", "click")
                button = int(item.get("button", 1))

                events.append(pygame.event.Event(pygame.MOUSEMOTION, pos=(x, y), rel=(0, 0), buttons=(0, 0, 0)))
                if action in {"down", "click"}:
                    events.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=button))
                if action in {"up", "click"}:
                    events.append(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(x, y), button=button))

        return events

    def drain_events(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        while not self._input_queue.empty():
            try:
                events.append(self._input_queue.get_nowait())
            except queue.Empty:
                break
        return events

    def set_external_frame_png(self, png_bytes: bytes, mode: str = "activity") -> None:
        with self._frame_lock:
            self._latest_png = png_bytes
            self._latest_time = time.monotonic()
            self._frame_count += 1
            self._mode = mode

    @staticmethod
    def _resolve_pygame_key(name: str, pygame: Any) -> int | None:
        name_upper = name.upper()
        named_map = {
            "LEFT": pygame.K_LEFT,
            "RIGHT": pygame.K_RIGHT,
            "UP": pygame.K_UP,
            "DOWN": pygame.K_DOWN,
            "RETURN": pygame.K_RETURN,
            "ENTER": pygame.K_RETURN,
            "ESCAPE": pygame.K_ESCAPE,
            "ESC": pygame.K_ESCAPE,
            "TAB": pygame.K_TAB,
            "SPACE": pygame.K_SPACE,
            "BACKSPACE": pygame.K_BACKSPACE,
        }
        if name_upper in named_map:
            return named_map[name_upper]
        if len(name) == 1:
            return ord(name.lower())
        return None
