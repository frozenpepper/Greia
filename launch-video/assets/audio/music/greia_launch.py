#!/usr/bin/env python3
"""greia_launch: score for the Greia launch video. 100 BPM, 24 bars (57.6 s), one-shot.

Night-sky celesta twinkles (the constellation G) -> warm marimba/bass groove -> full montage -> soft "home" bars ->
building agent section -> resolve on C. Bar numbers below are 1-based; a bar is 2.4 s.
"""
import json
from pathlib import Path

TEMPO, BPB, BARS = 100, 4, 29
CH = {  # chord per bar: (bass root, pad voicing, arp tones)
    "C": ("C2", ["E3", "G3", "B3", "E4"], ["C5", "E5", "G5", "B5"]),
    "Am": ("A1", ["C3", "E3", "G3", "C4"], ["A4", "C5", "E5", "G5"]),
    "F": ("F1", ["A3", "C4", "E4", "A4"], ["F4", "A4", "C5", "E5"]),
    "G": ("G1", ["B3", "D4", "F#4", "B4"], ["G4", "B4", "D5", "F#5"]),
    "Em": ("E1", ["G3", "B3", "D4", "G4"], ["E4", "G4", "B4", "D5"]),
}
PROG = ["C", "Am", "F", "G", "C", "Em", "F", "G", "C", "Am", "F", "G", "Am", "F", "C", "G",
        "Am", "F", "G", "Am", "F", "C", "G", "Am", "F", "F", "G", "C", "C"]
# 0-based bars of 2.4 s, in FINAL film time (the film has pauses between scenes; see timeline.json shifts)
GROOVE = set(range(4, 9)) | set(range(17, 21)) | {25, 26}   # Shell wakes 9.6 s; Parents scene; the close
FULL = set(range(9, 15)) | set(range(21, 25))               # montage + languages 21.6-36.0; the agent build 50.4-60.0
GROOVE |= FULL                                              # the full band also plays the groove parts
SOFT = {15, 16}                                             # Home / no desktop-browser-ads (36-40.8): shaker only
END = 27                                                    # resolve on "built to grow" (64.8 s)


def ev(beat, note, dur, vel):
    return {"note": note, "startBeat": round(beat, 4), "durationBeats": dur, "velocity": vel}


def up(n, k=1):
    return n[:-1] + str(int(n[-1]) + k)


def celesta():  # twinkles: one note per star as the logo's line reaches it, then arps, then a bell chord
    out = []
    tw = [(0.5, "G6", 70), (1.5, "E6", 62), (3.25, "C6", 62), (5.0, "A6", 66), (5.9, "D6", 62), (6.7, "G6", 70),
          (7.1, "B6", 58)]
    out += [ev(b, n, 1.5, v) for b, n, v in tw]
    out.append({"notes": ["C6", "E6", "G6"], "startBeat": 8, "durationBeats": 4, "velocity": 66})  # wordmark lands
    for bar in sorted(GROOVE):
        _, _, arp = CH[PROG[bar]]
        for i, k in enumerate([0, 2, 1, 3, 2, 1, 3, 2]):
            if bar not in FULL and i % 2 == 0:
                continue
            out.append(ev(bar * BPB + i * .5, arp[k], .45, 52 if i % 2 else 62))
    for bar in SOFT:  # sparse sparkle while Home / no-list play
        out.append(ev(bar * BPB + 1, CH[PROG[bar]][2][3], 2, 46))
        out.append(ev(bar * BPB + 2.5, CH[PROG[bar]][2][1], 2, 42))
    out.append({"notes": ["C5", "E5", "G5", "C6", "E6"], "startBeat": END * BPB, "durationBeats": 14, "velocity": 72})
    return out


def pad():
    out = []
    for bar in range(1, 29):
        _, v, _ = CH[PROG[bar]]
        soft = bar in SOFT or bar < 3 or bar >= END
        out.append({"notes": v, "startBeat": bar * BPB, "durationBeats": BPB - .05 if bar < END else 14,
                    "velocity": 36 if soft else 50})
    return out


def bass():
    out = []
    for bar in sorted(GROOVE | SOFT):
        root = CH[PROG[bar]][0]
        b0 = bar * BPB
        if bar in SOFT:
            out.append(ev(b0, root, 3.8, 70))
            continue
        for beat, dur in ((0, 1.5), (2, .9), (3, .4)):
            out.append(ev(b0 + beat, root, dur, 86 if beat == 0 else 66))
        if bar % 2:
            out.append(ev(b0 + 3.5, up(root), .4, 60))
    out.append(ev(21 * BPB, "C2", 8, 80))
    return out


def marimba():  # syncopated bounce under the picture
    out = []
    for bar in sorted(GROOVE):
        _, v, _ = CH[PROG[bar]]
        b0 = bar * BPB
        n = [up(x) for x in v]
        for beat, k, vel in ((0.5, 0, 66), (1.5, 2, 58), (2.5, 1, 62), (3.25, 3, 54), (3.75, 2, 50)):
            out.append(ev(b0 + beat, n[k], .35, vel))
    return out


def lead():  # glockenspiel hook over the mosaic, the agent build and the close
    H = {9: [(0, "E5", 1), (1, "G5", 1), (2, "A5", 1.5), (3.5, "G5", .5)],
         10: [(0, "E5", 1.5), (1.5, "C5", .5), (2, "D5", 2)],
         22: [(0, "A5", 1), (1, "C6", 1), (2, "B5", 1.5), (3.5, "A5", .5)],
         23: [(0, "G5", 1.5), (1.5, "D5", .5), (2, "G5", 2)],
         24: [(0, "E6", 1), (1, "C6", 1), (2, "G5", 2)],
         26: [(0, "A5", 1), (1, "C6", 1), (2, "D6", 1), (3, "E6", 1)],
         27: [(0, "C6", 3), (3, "E6", 1)],
         28: [(0, "G5", 4)]}
    return [ev(bar * BPB + b, n, d * .95, 84 if b == 0 else 74) for bar, ns in H.items() for b, n, d in ns]


def harp():  # gliss up into the wordmark and the finale
    out = []
    for start, base in ((6.0, 0), (END * BPB - 2, 0), (END * BPB + 3, 0)):
        notes = ["C4", "E4", "G4", "C5", "E5", "G5", "C6", "E6"]
        out += [ev(start + i * .22, n, 1.2, 50 + i * 3) for i, n in enumerate(notes)]
    return out


def drums():
    out = []
    for bar in sorted(GROOVE | SOFT):
        b0 = bar * BPB
        if bar in SOFT:
            out += [ev(b0 + i, "shaker", .25, 34) for i in range(4)]
            continue
        if bar < 9 or bar in (17, 18, 19, 20, 25, 26):  # light groove: no kit, just claves + shaker
            out += [ev(b0 + 1, "claves", .25, 58), ev(b0 + 3, "claves", .25, 62)]
            out += [ev(b0 + i, "shaker", .25, 40) for i in range(4)]
            continue
        out += [ev(b0, "kick", .5, 78), ev(b0 + 2, "kick", .5, 70), ev(b0 + 2.5, "kick", .5, 62)]
        out += [ev(b0 + 1, "rimshot", .25, 72), ev(b0 + 3, "rimshot", .25, 76)]
        out += [ev(b0 + i * .5, "shaker", .25, 52 if i % 2 else 64) for i in range(8)]
        out += [ev(b0 + 1.5, "tambourine", .25, 56), ev(b0 + 3.5, "tambourine", .25, 56)]
    out += [ev(9 * BPB, "crash", 2, 70), ev(21 * BPB, "crash", 2, 70), ev(END * BPB, "crash2", 6, 72)]
    return out


spec = {
    "id": "greia_launch", "tempo": TEMPO, "beatsPerBar": BPB, "bars": BARS, "loop": False, "tailSec": 5,
    "tracks": [
        {"name": "Celesta", "sound": "gm:8", "gainDb": -1, "pan": 18, "reverb": 38, "channel": 1, "events": celesta()},
        {"name": "Harp", "sound": "gm:46", "gainDb": -6, "pan": -22, "reverb": 35, "channel": 7, "events": harp()},
        {"name": "Pad", "sound": "gm:48", "gainDb": -3, "pan": 0, "reverb": 40, "channel": 3, "events": pad()},
        {"name": "Bass", "sound": "gm:33", "gainDb": -9, "pan": 0, "reverb": 0, "channel": 2, "events": bass()},
        {"name": "Marimba", "sound": "gm:12", "gainDb": 3, "pan": -15, "reverb": 22, "channel": 4, "events": marimba()},
        {"name": "Glock", "sound": "gm:9", "gainDb": 3, "pan": 20, "reverb": 30, "channel": 5, "events": lead()},
        {"name": "Drums", "sound": "gmdrums:standard", "gainDb": -8, "pan": 0, "reverb": 10, "channel": 10, "events": drums()},
    ],
}
Path(__file__).with_name("greia_launch.song.json").write_text(json.dumps(spec, indent=1))
print("wrote spec;", sum(len(t["events"]) for t in spec["tracks"]), "events")
