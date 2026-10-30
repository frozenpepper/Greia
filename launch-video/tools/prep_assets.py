"""Prepare web-sized assets for the launch video composition (hf/assets).

Run from launch-video/: python3 tools/prep_assets.py
Inputs: repo art, website brand files, headless captures in /Volumes/Venus/GREIA_LAUNCH_VIDEO/captures.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parent
OUT = HERE / "hf" / "assets"
CAP = Path("/Volumes/Venus/GREIA_LAUNCH_VIDEO/captures")
(OUT / "img").mkdir(parents=True, exist_ok=True)
(OUT / "shots").mkdir(parents=True, exist_ok=True)
(OUT / "svg").mkdir(parents=True, exist_ok=True)


def jpg(src: Path, dst: Path, size=None, q=92):
    im = Image.open(src).convert("RGB")
    if size:
        im = im.resize(size, Image.LANCZOS)
    im.save(dst, quality=q, optimize=True)


# --- night panorama (original boot-art world) -------------------------------------------------
jpg(REPO / "website/assets/brand/greia-night-panorama-v2.png", OUT / "img/night.jpg", (2304, 1297), 90)

# --- the generated Acer photo (owner supplied) -------------------------------------------------
jpg(REPO.parent / "Art/Product Pics/a8f9ec5c-c2cd-4234-b734-e5144e8e64fb.png", OUT / "img/acer.jpg", None, 94)

# --- Shell captures (real, 1920x1080) -----------------------------------------------------------
jpg(CAP / "shell_a-01-shell-frame.png", OUT / "shots/shell_profile.jpg", None, 94)
home = CAP / "shell_b-03-post-interaction.png"
jpg(home, OUT / "shots/shell_home.jpg", None, 94)

# Clean Shell background: the profile-picker capture has the identical landscape with no Collection
# icons. Patch the owl (home has the mascot there), the rainbow and the centre profile icon.
home_img = cv2.cvtColor(cv2.imread(str(home)), cv2.COLOR_BGR2RGB)
prof = cv2.cvtColor(cv2.imread(str(CAP / "shell_a-01-shell-frame.png")), cv2.COLOR_BGR2RGB)
H, W = home_img.shape[:2]
clean = prof.copy()
clean[800:1075, 386:570] = home_img[800:1075, 386:570]          # owl area -> home pixels (bush, flowers)
hole = np.zeros((H, W), np.uint8)
cv2.rectangle(hole, (905, 20), (1015, 100), 255, -1)            # rainbow
cv2.rectangle(hole, (340, 800), (390, 1075), 255, -1)           # seam between owl and mascot
clean = cv2.inpaint(clean, hole, 6, cv2.INPAINT_TELEA)
# centre profile icon + label: interpolate each column between the rows above and below the hole
y0, y1, x0, x1 = 455, 715, 845, 1080
top = clean[y0 - 6:y0 - 1, x0:x1].astype(float).mean(axis=0)
bot = clean[y1 + 1:y1 + 6, x0:x1].astype(float).mean(axis=0)
t = np.linspace(0, 1, y1 - y0)[:, None, None]
clean[y0:y1, x0:x1] = (top[None] * (1 - t) + bot[None] * t).astype(np.uint8)
Image.fromarray(clean).save(OUT / "shots/shell_clean.jpg", quality=94)

ICONS = {  # name: (cx, cy) icon centre in the 1920x1080 capture; box = icon + label pill
    "create": (686, 350), "creations": (960, 350), "play": (1234, 350),
    "learn": (686, 650), "explore": (960, 650), "greia": (1234, 650),
}
BOXES = {k: (cx - 125, cy - 150, 250, 340) for k, (cx, cy) in ICONS.items()}
BOXES.update({"chip": (10, 5, 100, 100), "star": (1820, 0, 100, 100), "mascot": (140, 770, 330, 270)})
diff = np.abs(home_img.astype(int) - clean.astype(int)).sum(axis=2)
meta = {}
for k, (x0, y0, w, h) in BOXES.items():
    d = diff[y0:y0 + h, x0:x0 + w]
    a = (d > 24).astype(np.uint8) * 255
    if k in ICONS:  # each sprite owns only its own grid cell, so neighbours' labels never leak into it
        gx = np.arange(x0, x0 + w)[None, :]; gy = np.arange(y0, y0 + h)[:, None]
        cx, cy = ICONS[k]
        col = lambda v: np.digitize(v, [823, 1097]); row = lambda v: np.digitize(v, [535])
        a = a * ((col(gx) == col(cx)) & (row(gy) == row(cy))).astype(np.uint8)
    a = cv2.morphologyEx(a, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    a = cv2.dilate(a, np.ones((3, 3), np.uint8))
    a = cv2.GaussianBlur(a, (0, 0), 1.2)
    rgba = np.dstack([home_img[y0:y0 + h, x0:x0 + w], a])
    Image.fromarray(rgba, "RGBA").save(OUT / f"shots/icon_{k}.png", optimize=True)
    meta[k] = dict(x=x0, y=y0, w=w, h=h)
(OUT / "shots/icons.json").write_text(json.dumps(meta))

# --- Activity thumbnails for the 45-tile mosaic ------------------------------------------------
names = sorted(p.name.split("-02-post")[0] for p in CAP.glob("*-02-post.png") if not p.name.startswith(("shell", "painting-")) or p.name.startswith("painting-02"))
names = [n for n in names if not n.startswith("shell")]
(OUT / "shots/tiles").mkdir(exist_ok=True)
for n in names:
    jpg(CAP / f"{n}-02-post.png", OUT / f"shots/tiles/{n}.jpg", (320, 188), 88)
(OUT / "shots/tiles.json").write_text(json.dumps(names))
print("tiles", len(names))

# a few hero stills at full size for quick montage cuts
for n in ["acquario_magico", "treno_numeri", "pasticceria_magica", "torre_forme", "sillabe_magiche", "costruiamo_ponti",
          "baia_delle_orche", "memory_meraviglie", "teatrino_fiabe", "nanna_delle_nuvolette", "piccola_serra",
          "orchestra_animali", "enciclopedia_greia", "quattro_stagioni", "clinica_cuccioli", "sottomarino_giramondo", "volo_draghetto"]:
    src = CAP / f"{n}-02-post.png"
    if src.exists():
        jpg(src, OUT / f"shots/{n}.jpg", (1920, 1125), 92)

# --- characters (vector, canonical) and brand ----------------------------------------------------
for c in ["lilli", "leo", "flash", "tito", "momo", "dani"]:
    for pose in ["pose_cheer", "pose_wave"]:
        s = REPO / f"assets/visual/characters/canonical/v0.1/{c}/{pose}.svg"
        if s.exists():
            shutil.copy(s, OUT / f"svg/{c}_{pose}.svg")
for f in ["greia-mark-light.svg", "greia-lockup-light.svg"]:
    shutil.copy(REPO / "website/assets/brand" / f, OUT / "svg" / f)

jpg(REPO / "website/assets/parent/this-greia-1024x600.png", OUT / "shots/parent_web.jpg", (1400, 820), 92)

# --- phone assets (real Greia Parents iOS app, simulator) -------------------------------------------
for f in ["family.png", "activities.png"]:
    p = Path("/Volumes/Venus/GREIA_LAUNCH_VIDEO/phone") / f
    if p.exists():
        jpg(p, OUT / f"shots/phone_{f[:-4]}.jpg", (603, 1311), 92)
print("done")
