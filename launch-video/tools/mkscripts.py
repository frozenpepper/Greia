"""Build recording scripts in 1024x600 design coordinates; scaled 1.875x for the 1920x1125 recording viewport."""
import json, math
S = 1.875
def P(x, y): return round(x * S), round(y * S)
def save(name, ev, dur): json.dump(dict(duration=round(dur, 2), events=ev), open(f"scripts_in/{name}.json", "w"))
def clicks(seq, t0=0.8, dt=0.9):
    ev, t = [], t0
    for x, y in seq:
        px, py = P(x, y); ev += [dict(t=round(t, 3), type="move", x=px, y=py), dict(t=round(t + .08, 3), type="click", x=px, y=py)]; t += dt
    return ev, t
def stroke(ev, pts, t, dt=0.028):
    x, y = P(*pts[0]); ev.append(dict(t=round(t, 3), type="move", x=x, y=y)); t += .05
    ev.append(dict(t=round(t, 3), type="down", x=x, y=y))
    for p in pts[1:]:
        t += dt; x, y = P(*p); ev.append(dict(t=round(t, 3), type="move", x=x, y=y))
    ev.append(dict(t=round(t + .04, 3), type="up", x=x, y=y)); return t + .14
def arc(cx, cy, r, a0, a1, n=34):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
def spiral(cx, cy, r, turns=3.2, n=70):
    return [(cx + r * (i / n) * math.cos(turns * 2 * math.pi * i / n), cy + r * (i / n) * math.sin(turns * 2 * math.pi * i / n)) for i in range(n + 1)]

# painting: rainbow, big yellow sun, pink heart
sw = dict(red=105, orange=159, yellow=212, green=267, blue=321, purple=429, pink=483)
ev, t = [], 0.7
for i, c in enumerate(["red", "orange", "yellow", "green", "blue", "purple"]):
    x, y = P(sw[c], 540); ev.append(dict(t=round(t, 3), type="click", x=x, y=y)); t += .18
    t = stroke(ev, arc(512, 400, 300 - i * 26, 180, 360), t)
x, y = P(813, 540); ev.append(dict(t=round(t, 3), type="click", x=x, y=y)); t += .2          # large brush
x, y = P(sw["yellow"], 540); ev.append(dict(t=round(t, 3), type="click", x=x, y=y)); t += .2
t = stroke(ev, spiral(870, 150, 44), t, .022)
x, y = P(sw["pink"], 540); ev.append(dict(t=round(t, 3), type="click", x=x, y=y)); t += .2
heart = [(160 + 38 * math.sin(a) ** 3 * 1.0, 330 - 3 * (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))) for a in [i * 2 * math.pi / 44 for i in range(45)]]
t = stroke(ev, heart, t, .03)
save("painting", ev, t + 1.2)

ev, t = clicks([(530, 125), (626, 230), (530, 350), (433, 230), (686, 425)], dt=0.95)
save("stelle", ev, t + 2.5)
ev, t = clicks([(195, 380), (320, 420), (448, 440), (575, 440), (700, 440), (825, 440), (245, 535), (320, 535), (398, 535), (472, 535), (550, 535), (625, 535), (700, 535), (778, 535)], dt=0.42)
save("orchestra", ev, t + 1.2)
