# Greia launch film: build contract

Original mode of the launch-video-clone skill. Category: **ui-showcase** (the real Shell and Activities doing real things),
with an editorial beat (generated drawer + the supplied Acer photo) and the owner's **constellation logo** as the spine.

- Output: 1920x1080, **30 fps**, 60.0 s = 1800 frames, stereo AAC, -13.8 LUFS, -1.2 dBTP.
- Grid: **100 BPM**, a beat every 0.6 s (18 f), a bar every 2.4 s (72 f). Cuts and word hits are snapped to it.
- Tokens: navy #0a1427, cream #fff8e9, butter #f9d65c, coral #ff756c, mint #9cebd1, violet #6965da, ink #192641, brown #3f2a26
  (all from the project site and Shell). Star colours from the original boot art: #f7cf73 #9ee9da #c69cef #ae86e8.
- Type: **Nunito Sans** 400/600/700/900 (the project's own font, shipped in the repo). Display = 900, tracking -0.028em.
- Motion rules applied (references/motion-feel.md): one easing curve per element family (cubic-bezier library in main.js, no shared
  default ease), the camera never stops between keys (single long tween per channel, eased only at the ends), zoom-through uses a
  custom exponential-in that starts already moving, different curves for x/y/scale, stagger 0.027-0.13 s, holds >= 1.1 s for anything
  that must be read, hard cuts land on the beat, shots cut in on motion.

## Revision 2 (owner feedback, 2026-10-17): 60.0 s, 1692 -> 1800 frames

Fixed: the zooming Create icon no longer drags its own label or a neighbour's (each icon sprite owns only its grid cell; the zooming sprite
is on top with a soft bottom fade). Added emphasis on: **a whole operating system, not an app** (opening line, USB-boot beat, "no desktop,
no browser, no ads"); **almost any hardware** (old netbooks, Raspberry Pi 400/500, modern PCs); **four languages at launch** (English,
Italian, French, Spanish) with every Activity voiced for pre-readers; **parents choose what and how long** (daily limit ring, a Science
week then a Writing week, real Parents iOS app, "mobile app coming soon"); **agent + open tools + character voices** (Activity skill,
Voice engine, Validator); **built for our daughters, open to every family and school, built to grow**; new real footage: orcas
(Baia delle Orche), dolphin (Viaggio del Delfino) and an Encyclopedia page (Space).
`timeline.json` is now the single source of times for the visuals (hf/src/scenes.js) and the mixer (tools/mix.py).

## Script and VO (Lilli's canonical voice, tools/greia_voice.py; English)

| t (s) | line |
|---|---|
| 0.8 | Not an app. A whole operating system, for the very small. |
| 5.2 | Old computers deserve another childhood. |
| 8.9 | Boot from a USB stick, and Greia is the whole computer. |
| 16.85 | Paint, count, listen, build, discover. Forty-five Activities, from age two. |
| 26.5 | No reading needed. Every Activity speaks, in four languages. |
| 31.2 | Always a way home. No desktop, no browser, no ads. |
| 35.5 | Parents choose what they see, and for how long. Science this week, writing the next. Mobile app, coming soon. |
| 43.5 | New Activities are easy to make. Ask an AI agent, with Greia's open tools, to build them, even with the voices of the Greia characters. |
| 51.9 | Greia began at home, for our own daughters. Now it is open to every family and every school, and built to grow. |

Every take was checked with Whisper; pauses were tightened with tools/tighten.py and lines 6, 7, 8 got a 1.08-1.1x tempo to fit their
scenes. Every clip is **human-review PENDING** per the voice-production rules: it needs the owner's listen. Claims on screen:
"Ages 2-3 and up" comes from the manifests (recommended_age_min 2/3), "four languages" is the owner's launch plan (the repo's selectable
registry is en/it today; fr/es are staged), "mobile app coming soon" from the owner (the app is a draft, not submitted).

## Shots (final cut; scene starts from timeline.json)

| # | time | what happens |
|---|---|---|
| 1 | 0.0-4.8 | Night panorama (original boot art). The constellation G draws through its stars (celesta note per star), "Not an app. A whole operating system." fades in on the words, wordmark wipes in, the gold star swells into a sun. |
| 2 | 4.8-11.2 | Sun iris opens on a generated drawer (dtgen, klein 9B) with a forgotten netbook; warm light blooms into the supplied Acer photo; callouts (Acer Aspire One, Atom, 1 GB, 1024x600); chips "Old netbooks / Raspberry Pi 400-500 / Modern PCs"; a USB stick plugs in, the REAL Greia boot splash appears on the netbook (with the real boot chime), then the real Shell; zoom-through. |
| 3 | 11.2-17.0 | Real 1080p profile picker, cursor presses Explorer, six Collections pop in, cursor presses Create, icon opens full screen. |
| 4 | 16.8-26.4 | Montage on the voice: PAINT (real recording), COUNT (real Stelle Incantate), LISTEN (Orchestra), BUILD, DISCOVER over orcas, dolphin, Encyclopedia (Space). 45-tile mosaic, counter, "Ages 2-3 and up". |
| 5 | 25.7-31.4 | "No reading needed." Six characters, Lilli sends rings on the words; Hello / Ciao / Bonjour / Hola land with the four language words. |
| 6 | 31.2-35.6 | Home corner while three Activities cut by; flash to the Shell; Desktop, Browser, Ads each struck out. |
| 7 | 35.4-43.4 | "What they see, and for how long." Real Parents iOS app (simulator), a daily-limit ring, a Science week then a Writing week built from real Activities, badge "Mobile app . coming soon". |
| 8 | 43.4-51.4 | "New Activities are easy to make." A wish is typed, a train becomes a constellation, three tool chips (Activity skill, Voice engine, Validator), it collapses into a real Activity tile and the six characters give it a voice. |
| 9 | 51.4-60.0 | Night again: G redraws, "Built for our daughters." then "Open to every family. Every school.", ten small constellations light up (one per new Activity), "Built to grow.", source line, fade. |

## Sound

- Music: `assets/audio/music/greia_launch.py` (songkit): 25 bars at 100 BPM, celesta twinkles timed to the logo's stars, marimba/bass groove,
  full kit under the montage, shaker-only bars for Home / no-list, glockenspiel hook, resolve on C at 50.4 s (glockenspiel hook again over the agent build).
- Sound design: `tools/mix.py` synthesises every effect (pings tuned to the music's scale, pops, whooshes, ticks, risers, thumps); ~330 events
  placed from the same times as main.js. Music ducks 5.5 dB under speech.
- Master: two-pass loudnorm to -14 LUFS then a true-peak limiter: -13.7 LUFS, -1.4 dBTP.

## Directions considered (storyboard/directions_comparison.jpg)

A **Night sky + constellation** (built). B Paper and tape collage (mock). C Type-first colour blocks (mock).
Picked A: it is the only one that uses the owner's original logo animation and looks (explicit instruction), it gives the film a
night-to-day arc (stars -> sun -> the child's world -> stars again), and it lets real screens carry the product. B and C were
quick mocks only; C's type collision was left visible on purpose.

## Numbers taken from donors

No new donor video was downloaded or analysed (downloads were not approved in this session). Targets came from the donor numbers already
recorded in the skill's type files: ~30-33 f settle on entrances, quartic ease-out for big scale moves, 2-2.5 f stagger, containers a
frame ahead of content, shots cut in on motion, no ease-in at a cut. Per-shot compare.py grading does not apply (there is no reference);
motion was reviewed with contact sheets and a frame-difference scan (no 0.5 s window without motion; hard cuts only where intended).


## Revision 3 (owner notes, 2026-10-17): 68.3 s

- Netbook screen: the quad was re-measured with OpenCV on the photo (TL 301,175 / TR 939,133 / BR 997,509 / BL 359,583, pushed out 2 px); my first
  bottom-right corner was 14 px off. The machine now starts dark with a USB stick plugging in (7.2-8.2 s), the real boot splash and chime at 8.3 s,
  the Shell on the screen from 9.75 s, and the camera holds on it until the zoom-through at 15.4 s (about 6 s of Greia on the Acer, before ~1.5 s).
- Pacing: `timeline.json` now has `shifts` (breakpoint, pause) applied to picture, sound and scene durations alike: +4.5 s before the Shell, then +0.5, +0.9,
  +0.6, +0.7 s between voice lines. The line "Every child gets a world of their own" is spoken again over the Shell. Scene fades happen just before the next scene.
- Ending: "every school" removed. New line: "Greia began at home, for our own daughters. Now it is free and open source, for every family, and built to grow."
  On screen: "Built for our daughters." / "Now free and open source." / "For every family." / "Built to grow." (each text lands on its word) plus the source line.
- Music rescored to 29 bars (full band under the montage/languages and the agent build, resolve on "built to grow"). Master -13.8 LUFS, -1.5 dBTP.

## Revision 4 (owner note): USB beat and stick artwork, 68.9 s

"Old computers deserve another childhood" now finishes before the next line: VO 02 at 5.0 s, a pause, the stick plugs in at 8.4 s, VO 03 "Boot from a USB stick" at 8.9 s
with the boot splash and chime, the Shell from 10.9 s, hardware chips from 11.6 s, zoom-through at 16.0 s (Shell shift +5.1 s). The USB stick was redrawn (butter body,
brown outline, metal connector, lanyard hole, tiny LEDs).
