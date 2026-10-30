"""Virtual-clock recording scripts (1024x600 design coordinates -> 1920x1125 viewport, scale 1.875)."""
import json, math
S = 1.875
P = lambda x, y: (round(x * S), round(y * S))
def save(name, ev, dur, settle=1.0): json.dump(dict(duration=round(dur, 3), settle=settle, events=ev), open(f"scripts_in/{name}.json", "w"))
def click(ev, t, x, y):
    px, py = P(x, y); ev += [dict(t=round(t, 3), type="move", x=px, y=py), dict(t=round(t + .05, 3), type="click", x=px, y=py)]
def stroke(ev, pts, t, dt):
    x, y = P(*pts[0]); ev.append(dict(t=round(t, 3), type="move", x=x, y=y)); t += .03
    ev.append(dict(t=round(t, 3), type="down", x=x, y=y))
    for p in pts[1:]:
        t += dt; x, y = P(*p); ev.append(dict(t=round(t, 3), type="move", x=x, y=y))
    ev.append(dict(t=round(t + .03, 3), type="up", x=x, y=y)); return t + .08
arc = lambda cx, cy, r, a0, a1, n: [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
spiral = lambda cx, cy, r, turns, n: [(cx + r * (i / n) * math.cos(turns * 2 * math.pi * i / n), cy + r * (i / n) * math.sin(turns * 2 * math.pi * i / n)) for i in range(n + 1)]
sw = dict(red=105, orange=159, yellow=212, green=267, blue=321, purple=429, pink=483)

# PAINT (fast, for the montage): four arcs in ~1.3 s, then a sun spiral
ev, t = [], 0.12
for i, c in enumerate(["red", "orange", "yellow", "green", "blue", "purple"]):
    click(ev, t, sw[c], 540); t += .07
    t = stroke(ev, arc(512, 395, 300 - i * 27, 180, 360, 44), t, .0075)
click(ev, t, 813, 540); t += .08; click(ev, t, sw["yellow"], 540); t += .08
t = stroke(ev, spiral(865, 150, 46, 3.0, 70), t, .008)
save("v_paint", ev, t + .6)

# STELLE seed 2 (kite): tap 1..5 quickly
pos = [(988, 232), (1172, 424), (992, 664), (812, 424), (1284, 792)]
ev, t = [], 0.2
for x, y in pos:
    ev += [dict(t=round(t, 3), type="move", x=x, y=y), dict(t=round(t + .04, 3), type="click", x=x, y=y)]; t += 0.22
save("v_stelle2", ev, t + 2.6)

# ORCHESTRA: animals then keys, quick
ev, t = [], 0.1
for x, y in [(195, 380), (320, 420), (448, 440), (575, 440), (700, 440), (825, 440), (245, 535), (320, 535), (398, 535), (472, 535), (550, 535)]:
    click(ev, t, x, y); t += 0.11
save("v_orch", ev, t + 1.4)

save("v_static", [], 0.4)

# ---- new footage for the revised cut
ev = []; click(ev, 0.6, 584, 553); click(ev, 1.3, 538, 353); click(ev, 2.0, 215, 551); click(ev, 2.7, 640, 300)
save("v_orca", ev, 4.0)
ev = []; click(ev, 0.8, 189, 215)
save("v_delfino", ev, 6.0)
ev = []; click(ev, 0.8, 510, 230)
save("v_enc", ev, 5.0)
