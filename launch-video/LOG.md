# Round log

| round | what changed | check |
|---|---|---|
| plan | Category ui-showcase + editorial; script written from README, website (checked against the repo), docs, real captures | SCRIPT.md |
| assets | 45 Activity captures, Shell at 1920x1080, iOS Parents app in the simulator, drawer image via dtgen, Acer photo, brand SVG, 6 vector characters | contact sheets |
| footage | wall-clock recorder gave ~3 distinct frames/s under load 60-300; replaced by a virtual-clock recorder (tools/vclock) -> 30 fps deterministic | 118/82/120 smooth frames |
| v1 draft | first full build, 3:00 render | yellow tint (fromTo leaked a flash opacity at t=0); text hidden under a still |
| v2 | drawer scene, S6/S7/S8 layouts, audio mix | scene 3 background covered scene 2 (smear at 12.0), scene 2 background covered the night |
| v3 | Home scene rebuilt as a continuous push over three Activities; cast, mosaic, grid enlarged | transition strips at 10 fps |
| v4 | transition timing, mosaic sheen/drift, sunrise gap closed | motion scan: no still window, cuts on the beat |
| final | caret/overlap timing, chips, subject line; delivery encode | check: 0 errors, contrast 11/11; ffprobe 1920x1080 30 fps 56.4 s; -13.7 LUFS / -1.4 dBTP |

Not done: a human listen (the only real sound check), ElevenLabs music/SFX (no key on this machine; songkit + the project voice engine + a
numpy synth were used instead), Gemini/audiobox soundcheck, per-donor burst analysis.
| rev 2 | Owner feedback: icon sprites own only their cell; zooming icon on top with soft fade. New beats (OS not an app, hardware range + USB boot, four languages, parents limits/weeks, agent tools + voices, daughters/open/grow), orca/dolphin/Encyclopedia footage, new VO (7 lines, 14 takes), music retimed to 25 bars, timeline.json shared by visuals and mixer | check 0 errors, contrast 35/35; 60.0 s, -13.8 LUFS / -1.2 dBTP; an overlay shared by two moments tinted a frame -> separate overlays |
| rev 3 | Screen quad re-measured; Greia held ~6 s on the Acer; USB/boot/Shell beats; spaced scenes and voices (timeline shifts); new closing (free, open source, for every family); music 29 bars | check 0 errors, 41/41 contrast; 68.3 s, -13.8 LUFS / -1.5 dBTP |
| rev 4 | Pause between the "old computers" and "USB stick" lines, boot splash 2 s, Shell held longer, USB artwork redrawn | check passed; 68.9 s |
| rev 5 | Opening: VO 01 tightened and started at 0.7 s, VO 02 moved to 5.6 s (1.1 s gap), rest of the netbook scene +0.6 s; 69.5 s | check passed |
