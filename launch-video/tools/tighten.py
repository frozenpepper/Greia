"""Shorten internal pauses of a voice clip (pauses longer than MAXGAP become MAXGAP). usage: tighten.py in.wav out.wav [maxgap=0.45]"""
import subprocess, sys
import numpy as np
SR = 24000
inp, out = sys.argv[1], sys.argv[2]; maxgap = float(sys.argv[3]) if len(sys.argv) > 3 else 0.45
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", inp, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(raw, "<f4").copy()
win = int(0.02 * SR); n = len(x) // win
e = np.sqrt(np.mean(x[: n * win].reshape(n, win) ** 2, axis=1)); thr = max(0.004, 0.06 * e.max())
quiet = e < thr
y = []; i = 0; keep_gap = int(maxgap / 0.02)
while i < n:
    if not quiet[i]:
        y.append(x[i * win:(i + 1) * win]); i += 1
    else:
        j = i
        while j < n and quiet[j]: j += 1
        run = j - i
        if i == 0 or j == n: keep = min(run, 5)
        else: keep = min(run, keep_gap)
        y.append(x[i * win:(i + keep) * win]); i = j
y = np.concatenate(y)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_s16le", out], input=y.astype("<f4").tobytes(), check=True)
print(inp, len(x) / SR, "->", len(y) / SR)
