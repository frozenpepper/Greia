"""Assemble hf/index.html from hf/src/{style.css,body.html,main.js}. Run from launch-video/."""
import json, re
from pathlib import Path
H = Path(__file__).resolve().parents[1] / "hf"
svg = (H / "assets/svg/greia-mark-light.svg").read_text()
wm = re.findall(r'<path d="([^"]+)" fill="currentColor"', svg)[-1]
js = (H / "src/head.js").read_text() + "\n" + (H / "src/scenes.js").read_text()
TL = (H.parent / "timeline.json").read_text()
js = js.replace("{{TIMELINE_JSON}}", TL)
js = js.replace('"{{WORDMARK_D}}"', json.dumps(wm))
js = js.replace("{{ICONS_JSON}}", (H / "assets/shots/icons.json").read_text())
js = js.replace("{{TILES_JSON}}", (H / "assets/shots/tiles.json").read_text())
DUR = json.loads(TL)["duration"]
import re as _re
_T = json.loads(TL)
def _shift(t): return t + sum(d for b, dl in [tuple(x) for x in _T["shifts"]] for d in [dl] if t >= b - 1e-9)
def _retime(m):
    st, du = float(m.group(1)), float(m.group(2))
    ns, ne = _shift(st), _shift(st + du)
    return f'data-start="{ns:.2f}" data-duration="{ne - ns:.2f}"'
_body = _re.sub(r'data-start="([\d.]+)" data-duration="([\d.]+)"', _retime, (H / "src/body.html").read_text())
html = f"""<!doctype html>
<html lang="en" data-resolution="landscape">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1920, height=1080" />
<title>Greia launch film</title>
<script src="assets/vendor/gsap.min.js"></script>
<style>
{(H / 'src/style.css').read_text()}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="{DUR}">
{_body}
<audio id="mix" src="assets/audio/mix.wav" data-start="0" data-duration="{DUR}" data-track-index="30" data-volume="1"></audio>
</div>
<script>
{js}
</script>
</body>
</html>
"""
(H / "index.html").write_text(html)
print("built index.html", len(html))
