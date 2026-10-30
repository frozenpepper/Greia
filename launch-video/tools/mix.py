"""Sound design + final mix for the Greia launch film (no external services).

SFX are synthesised here (bell pings, pops, whooshes, ticks, swells); VO takes come from tools/greia_voice.py;
music is the songkit cue. Every event time matches hf/src/main.js. Run from launch-video/:  python3 tools/mix.py
Outputs hf/assets/audio/mix.wav (stereo 44.1 kHz) and a timing report.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import numpy as np

SR = 44100
ROOT = Path(__file__).resolve().parents[1]
VO = ROOT / "assets/audio/vo"
MUSIC = ROOT / "assets/audio/music/export/greia_launch_master.wav"
OUT = ROOT / "hf/assets/audio/mix.wav"
DUR = 60.0
rng = np.random.default_rng(20261017)


def load(path: Path, tempo: float = 1.0) -> np.ndarray:
    """Decode any audio file to mono float32 at 44.1 kHz through ffmpeg (optional pitch-preserving tempo)."""
    af = ["-af", f"atempo={tempo}"] if tempo != 1.0 else []
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), *af, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<f4").copy()


def write_wav(path: Path, data: np.ndarray) -> None:
    """Write float32 stereo as 32-bit float WAV via ffmpeg."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-c:a", "pcm_f32le", str(path)],
                   input=np.ascontiguousarray(data, dtype="<f4").tobytes(), check=True)


def t_(n: float) -> np.ndarray:
    return np.arange(int(n * SR)) / SR


def env(n: int, a=0.004, d=0.2, curve=4.0) -> np.ndarray:
    x = np.arange(n) / SR
    e = np.exp(-x / max(d, 1e-3) * curve / 4.0)
    att = np.minimum(1.0, x / max(a, 1e-4))
    return (e * att).astype(np.float32)


def lowpass(x: np.ndarray, fc: np.ndarray | float) -> np.ndarray:
    """One-pole low-pass with a (possibly moving) cutoff."""
    fc = np.broadcast_to(fc, x.shape) if np.isscalar(fc) else fc
    a = 1 - np.exp(-2 * np.pi * np.clip(fc, 20, 20000) / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def ping(f: float, dur=1.1, bright=1.0) -> np.ndarray:
    t = t_(dur)
    x = np.sin(2 * np.pi * f * t) + 0.45 * bright * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t * 6) + 0.2 * bright * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t * 10)
    return (x * env(len(t), 0.002, dur * 0.35)).astype(np.float32) * 0.5


def pop(f0=620.0, f1=170.0, dur=0.14) -> np.ndarray:
    t = t_(dur)
    f = f1 + (f0 - f1) * np.exp(-t * 38)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * env(len(t), 0.001, dur * 0.5) * 0.8).astype(np.float32)


def tick(f=2200.0, dur=0.03) -> np.ndarray:
    t = t_(dur)
    n = rng.standard_normal(len(t)).astype(np.float32)
    return lowpass(n, f) * env(len(t), 0.0005, 0.012) * 0.4


def thump(dur=0.5, f=62.0) -> np.ndarray:
    t = t_(dur)
    fr = f * (1 + 1.2 * np.exp(-t * 18))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    return (np.sin(ph) * env(len(t), 0.002, dur * 0.4) * 0.9).astype(np.float32)


def whoosh(dur=0.7, up=True, lo=300.0, hi=6000.0, level=0.5) -> np.ndarray:
    t = t_(dur)
    n = rng.standard_normal(len(t)).astype(np.float32)
    p = t / dur
    sweep = (p ** 2) if up else (1 - p) ** 2
    fc = lo + (hi - lo) * sweep
    y = lowpass(n, fc)
    swell = np.sin(np.pi * p) ** 1.6
    return (y * swell * level).astype(np.float32)


def riser(dur=0.6, f0=300.0, f1=1800.0, level=0.3) -> np.ndarray:
    t = t_(dur)
    p = t / dur
    f = f0 * (f1 / f0) ** (p ** 1.5)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * p ** 1.8 * level).astype(np.float32)


def shimmer(fs: list[float], gap=0.05, dur=0.9) -> np.ndarray:
    out = np.zeros(int((dur + gap * len(fs)) * SR), np.float32)
    for i, f in enumerate(fs):
        p = ping(f, dur, 1.2) * 0.7
        s = int(i * gap * SR)
        out[s:s + len(p)] += p[: len(out) - s]
    return out


def swish(dur=0.16, level=0.5) -> np.ndarray:
    return whoosh(dur, True, 1500, 9000, level)


PENTA = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.7, 1318.5, 1568.0]
events: list[tuple[float, np.ndarray, float, float]] = []  # (time, wave, gain_db, pan)


SHIFT_ON = False
SHIFTS: list = []


def shift(t: float) -> float:
    return t + sum(d for b, d in SHIFTS if t >= b - 1e-9)


def add(t: float, wave: np.ndarray, db: float = 0.0, pan: float = 0.0, lead: float = 0.0) -> None:
    events.append(((shift(t) if SHIFT_ON else t) - lead, wave, db, pan))


# ------------------------------------------------------------------ SFX timeline (times come from timeline.json, same as main.js)
TL = json.loads((ROOT / "timeline.json").read_text())
SC, CUT, W, VOT = TL["scene"], TL["cut"], TL["word"], TL["vo"]
DUR = float(TL["duration"])
SHIFTS.extend(TL["shifts"])
BOOT_CHIME = ROOT.parent / "assets/audio/system/greia-boot-chime.wav"

# S1: logo
for i, t in enumerate([0.3, 0.9, 1.95, 3.0, 3.54, 4.02, 4.26]):
    add(t, ping(PENTA[(i * 2 + 3) % 7] * 2, 1.0, 1.3), -20, [0.4, -0.4, -0.6, 0.5, 0.3, -0.2, 0.0][i])
add(4.1, whoosh(0.7, True, 600, 9000, 0.35), -17)
add(4.28, riser(0.55, 280, 1900, 0.5), -17)
add(4.78, thump(0.7, 55), -9)
add(4.8, whoosh(1.0, True, 400, 7000, 0.5), -14)
# S2 (final-frame times): drawer -> bloom -> dark netbook, USB stick, boot, Shell held, hardware chips, zoom-through
add(5.75, riser(0.5, 200, 1400, 0.5), -19); add(6.0, shimmer([1046.5, 1318.5, 1568], 0.06, 1.0), -22)
for t in (7.0, 7.5):
    add(t, pop(780, 300, 0.12), -17); add(t + 0.3, tick(3000), -22)
add(8.3, whoosh(0.7, True, 300, 6000, 0.35), -20)
add(9.2, thump(0.25, 140), -13); add(9.22, tick(3200, 0.04), -15); add(9.35, ping(1568, 1.2), -20)
if BOOT_CHIME.exists():
    events.append((9.5, load(BOOT_CHIME) * 0.9, -12.0, 0.0))                       # the real Greia boot chime, on the boot splash
add(11.5, shimmer([1046.5, 1318.5, 1568], 0.05, 1.0), -24)                         # the Shell appears
for t in (12.5, 12.75, 13.0):
    add(t, pop(700, 260, 0.13), -17); add(t + 0.02, ping(PENTA[int(t * 10) % 7], 0.5, 1.0), -27)
add(12.2, whoosh(0.7, True, 300, 6000, 0.35), -21)
add(16.6, whoosh(1.0, True, 200, 7500, 0.6), -13)
SHIFT_ON = True
# S3: profile, six worlds, Create
add(13.1, tick(2600, 0.04), -14); add(13.12, pop(520, 200, 0.12), -17)
for i, t in enumerate([13.3, 13.38, 13.56, 13.68, 13.8, 13.92, 14.06, 14.12, 14.18]):
    add(t, pop(430 + 60 * i, 190, 0.13), -20, (-0.5 + i * 0.12)); add(t + 0.02, ping(PENTA[i % 9] * 2, 0.5, 1.0), -27, (-0.5 + i * 0.12))
add(15.55, tick(2600, 0.04), -14); add(15.57, pop(520, 200, 0.12), -17)
add(15.7, whoosh(0.75, True, 250, 8000, 0.55), -13); add(16.3, riser(0.5, 200, 1200, 0.4), -20)
# S4: montage
for t, n in [(W["paint"], 0), (W["count"], 2), (W["listen"], 4), (W["build"], 6), (W["discover"], 8)]:
    add(t, thump(0.38, 90 - n * 3), -12); add(t + 0.01, pop(900, 260, 0.12), -17)
for k in ("count", "listen", "build", "orca", "dolphin", "enc"):
    add(CUT[k], swish(0.12, 0.6), -22)
M0 = CUT["mosaic"]
add(M0, thump(0.9, 50), -9); add(M0 + 0.01, shimmer([1046.5, 1318.5, 1568, 2093], 0.04, 1.2), -22)
for i in range(45):
    add(M0 + 0.1 + i * 0.02, tick(1800 + (i % 7) * 260, 0.025), -27, ((i * 0.37) % 2) - 1)
for i in range(0, 45, 3):
    add(M0 + 0.1 + i * 0.02, pop(600 + (i % 9) * 40, 240, 0.1), -26, ((i * 0.21) % 2) - 1)
for i in range(40):
    add(M0 + 0.05 + i * 0.02, tick(3400, 0.012), -28)
add(M0 + 1.2, pop(900, 300, 0.14), -16); add(M0 + 1.22, ping(1318.5, 0.6), -24)
add(25.3, whoosh(0.9, False, 400, 7000, 0.5), -17)
add(25.7, whoosh(1.0, True, 300, 6500, 0.55), -13)
# S5: cast, speech rings, four languages
for i in range(6):
    t = 26.35 + i * 0.12
    add(t, pop(380 + 60 * i, 120, 0.2), -17, -0.8 + i * 0.32); add(t + 0.05, ping(PENTA[(i * 2) % 9], 0.9, 1.0), -25, -0.8 + i * 0.32)
for t, f in zip((W["lang1"], W["lang2"], W["lang3"], W["lang4"]), (1046.5, 1174.7, 1318.5, 1568)):
    add(t - 0.05, pop(900, 300, 0.14), -16); add(t, ping(f, 1.0, 1.2), -21)
# S6: Home, then what is not there
H0 = SC["s6a"]
for t, f in ((H0 + 0.15, 1046.5), (H0 + 0.55, 1174.7), (H0 + 1.1, 1318.5), (W["home"], 1568)):
    add(t, ping(f, 1.0), -22)
add(H0 + 0.55, swish(0.12, 0.6), -22); add(H0 + 1.1, swish(0.12, 0.6), -22)
add(W["home"], tick(2600, 0.04), -14); add(W["home"] + 0.02, pop(500, 190, 0.14), -16); add(W["home"] + 0.02, whoosh(0.5, False, 300, 9000, 0.5), -17)
for k in ("nodesktop", "nobrowser", "noads"):
    t = W[k]
    add(t - 0.2, pop(560, 220, 0.12), -22)
    add(t + 0.1, swish(0.18, 0.7), -17); add(t + 0.12, thump(0.25, 100), -18)
# S7: what they see and for how long
S7 = SC["s7"]
for d in (0.45, 0.7, 0.95, 1.35, 1.6, 1.85, 2.1):
    add(S7 + d, tick(2400, 0.03), -24)
add(S7 + 0.3, whoosh(0.9, True, 250, 7000, 0.5), -15)
add(W["long"] - 0.25, pop(700, 260, 0.12), -19); add(W["long"], ping(1318.5, 0.9), -23)
for wk in (W["science"], W["writing"]):
    add(wk - 0.1, swish(0.2, 0.5), -21)
    for i in range(4):
        add(wk + 0.2 + i * 0.1, tick(2800 + i * 200, 0.03), -22, -0.4 + i * 0.27)
add(W["soon"], pop(760, 240, 0.16), -14); add(W["soon"] + 0.02, shimmer([1318.5, 1568, 2093, 2637], 0.05, 1.2), -20)
# S8: agent, open tools, voices
A0 = SC["s8"]
for d in (0.45, 0.75, 1.1, 1.55, 1.85, 2.15):
    add(A0 + d, tick(2400, 0.03), -24)
for i in range(6):
    add(W["easy"] + i * 0.09, pop(520 + i * 50, 200, 0.12), -21, -0.6 + i * 0.24)
for i in range(52):
    add(W["agent"] + 0.1 + i * (1.5 / 52), tick(2000 + (i * 137) % 900, 0.02), -26, ((i * 0.13) % 1) - 0.5)
for i in range(8):
    add(W["agent"] + 0.4 + i * 0.1, ping(PENTA[(i * 3) % 9] * 2, 0.7, 1.0), -25, (i % 2) - 0.5)
add(W["agent"] + 0.55, riser(1.0, 200, 1500, 0.3), -21)
for i in range(3):
    add(W["tools"] + i * 0.28, pop(640 + i * 90, 240, 0.12), -19); add(W["tools"] + i * 0.28 + 0.02, ping(PENTA[(i * 2 + 2) % 9], 0.7, 1.0), -25)
add(W["voices"] - 0.65, whoosh(0.5, True, 500, 8000, 0.5), -16)
add(W["voices"] - 0.3, thump(0.6, 70), -11); add(W["voices"] - 0.28, shimmer([1046.5, 1318.5, 1568, 2093, 2637], 0.05, 1.3), -19)
for i in range(6):
    add(W["voices"] + i * 0.16, pop(380 + 60 * i, 120, 0.2), -18, -0.7 + i * 0.28); add(W["voices"] + i * 0.16 + 0.25, ping(PENTA[(i * 2) % 9], 0.8, 1.0), -25, -0.7 + i * 0.28)
# S9: close
Z = SC["s9"]
add(Z, whoosh(1.0, True, 300, 7000, 0.4), -19)
for i, k in enumerate([0.3, 0.9, 1.95, 3.0, 3.54, 4.02]):
    add(Z + 0.3 + k * 0.4, ping(PENTA[(i * 2 + 3) % 7] * 2, 1.2, 1.2), -21, [0.4, -0.4, -0.6, 0.5, 0.3, -0.2][i])
for d in (-0.05, 0.25, 0.5, 0.8):
    add(W["daughters"] + d, tick(2400, 0.03), -25)
for d in (-0.05, 0.4, 0.7, 1.05, 1.4):
    add(W["open"] + d, tick(2400, 0.03), -25)
for k in range(10):
    add(W["grow"] - 0.9 + k * 0.22, ping(PENTA[(k * 2 + 1) % 9] * 2, 1.0, 1.1), -26, ((k * 0.37) % 2) - 1)
for d in (-0.05, 0.3, 0.55):
    add(W["grow"] + d, tick(2400, 0.03), -25)
add(W["grow"] + 1.2, ping(1568, 2.0), -25)

# ------------------------------------------------------------------ VO placements (take chosen per line)
VO_FILES = {"vo03e": "vo03a", "vo01n": "vo01na_t", "vo02b": "vo02b", "vo03n": "vo03na", "vo05": "vo05n2a", "vo06": "vo06n2a_t",
            "vo07": "vo07xb_tt", "vo08": "vo08n2a_tt", "vo09": "vo09fb", "vo04": "vo04ma"}
VO_TEMPO = {"vo06n2a_t": 1.1}
VO_PLACE = [(VO_FILES[k], shift(VOT[k])) for k in VOT if k in VO_FILES]


def rms_db(x: np.ndarray) -> float:
    return 20 * math.log10(float(np.sqrt(np.mean(x ** 2))) + 1e-9)


def build() -> None:
    n = int((DUR + 1.0) * SR)
    L = np.zeros(n, np.float32)
    Rr = np.zeros(n, np.float32)
    # ---- voice: normalise each take, gentle high-pass, place
    vo_track = np.zeros(n, np.float32)
    vo_mask = np.zeros(n, np.float32)
    for name, t in VO_PLACE:
        x = load(VO / f"{name}.wav", VO_TEMPO.get(name, 1.0)) if (VO / f"{name}.wav").exists() else None
        if x is None:
            continue
        # resample if the voice engine wrote another rate
        x = x - np.mean(x)
        active = x[np.abs(x) > 0.01 * np.max(np.abs(x))]
        g = 10 ** ((-19.0 - rms_db(active)) / 20)
        x = x * g
        s = int(t * SR)
        vo_track[s:s + len(x)] += x[: n - s]
        vo_mask[s:s + len(x)] = np.maximum(vo_mask[s:s + len(x)], (np.abs(x) > 0.004).astype(np.float32)[: n - s])
    # smooth the "voice present" mask into a ducking envelope (fast attack, slower release)
    k = int(0.35 * SR)
    kern = np.ones(k, np.float32) / k
    duck = np.convolve(vo_mask, kern, mode="same")
    duck = np.clip(duck * 2.2, 0, 1)
    duck = np.convolve(duck, np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")
    # ---- music
    m = load(MUSIC)
    mus = np.zeros(n, np.float32)
    mus[: min(n, len(m))] = m[:n]
    mus *= 10 ** (-1.5 / 20)
    mus *= (1 - duck * (1 - 10 ** (-5.5 / 20)))
    fade = np.ones(n, np.float32)
    f0, f1 = int((DUR - 1.2) * SR), int(DUR * SR)
    fade[f0:f1] = np.linspace(1, 0, f1 - f0)
    fade[f1:] = 0
    mus *= fade
    # ---- sfx
    sl = np.zeros(n, np.float32)
    sr_ = np.zeros(n, np.float32)
    for t, w, db, pan in events:
        s = int(max(0.0, t) * SR)
        if s >= n:
            continue
        w = w[: n - s] * 10 ** (db / 20)
        a = (pan + 1) / 2
        sl[s:s + len(w)] += w * math.cos(a * math.pi / 2)
        sr_[s:s + len(w)] += w * math.sin(a * math.pi / 2)
    L = mus + vo_track * 1.0 + sl
    Rr = mus + vo_track * 1.0 + sr_
    st = np.stack([L, Rr], axis=1)[: int(DUR * SR)]
    peak = np.max(np.abs(st))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".raw.wav")
    write_wav(tmp, st / max(1.0, peak * 1.02))
    # loudness: two-pass loudnorm to -14 LUFS then a true-peak limiter
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(tmp), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
          f"measured_thresh={j['input_thresh']}:linear=true,alimiter=limit=0.84:level=disabled")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(tmp), "-af", af, "-ar", "44100", "-c:a", "pcm_s16le", str(OUT)], check=True)
    tmp.unlink()
    print("mix written", OUT, "| input", j["input_i"], "LUFS ->", "-14 target")


if __name__ == "__main__":
    build()
