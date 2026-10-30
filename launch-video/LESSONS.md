## Lessons
- RULE: To film a real app deterministically, give the child process a virtual clock (patch time.monotonic/sleep, pygame Clock/event.wait;
  post scripted events by virtual time; write the display surface every 1/fps of virtual time) instead of recording wall-clock frames.
  EVIDENCE: wall-clock capture at 1920x1125 under load 60-300 gave 7-30 changed frames per 8 s; the virtual clock gave 118 smooth frames in
  25 s wall, independent of load (tools/vclock/sitecustomize.py, tools/record_virtual.py). Seed random.Random() there too, or layouts change per run.
  GOES IN: SKILL.md section 3 (raster) / types/ui-showcase.md
- RULE: Never give a scene container an opaque background if the previous scene must stay visible during an iris or zoom transition.
  EVIDENCE: scene 2 (cream) hid the night before its iris opened; scene 3 covered the zoom-through with a smeared plate (two frames at 4.8 s and 12.0 s).
  GOES IN: references/motion-feel.md
- RULE: In a GSAP timeline, every fromTo() applies its FROM values at t=0 (immediateRender). A flash overlay authored with fromTo(0.55 -> 0)
  tinted the whole film yellow. Use tl.set + tl.to for transient overlays. GOES IN: SKILL.md section 4
- RULE: HyperFrames forbids a <video data-start> inside a timed ancestor: put footage at root level and stack with DOM order/z-index.
  EVIDENCE: lint video_nested_in_timed_element. GOES IN: SKILL.md section 4
- RULE: ffmpeg alimiter needs level=disabled; with the default it re-normalised the peak to 0 dBFS (-1.5 dB limit ignored). GOES IN: SKILL.md section 6 item 7
- RULE: Word timings from a tiny Whisper are unreliable for the first word of a sentence; take sentence starts from silencedetect (d=0.18 s).
  EVIDENCE: "Forty-five" read as 4.8 s vs 4.08 s from silence. GOES IN: SKILL.md section 6
- RULE: Do not inpaint a clean background under UI sprites; use the same app's capture of a neighbouring state, or crossfade real captures.
  EVIDENCE: Telea inpaint left a smeared column in the Shell sky/hills. GOES IN: references/living-stills.md

- RULE: Keep one timeline.json (scene starts, VO starts, word times) and have both the composition and the mixer read it; a script revision
  then moves picture and sound together. EVIDENCE: the 56 -> 60 s rewrite changed ~40 cue times with no drift. GOES IN: SKILL.md section 6
- RULE: Sprites cut from a screenshot must be masked to their own grid cell; a padded box drags the neighbour's label and shadow along when
  the sprite is scaled. EVIDENCE: owner saw Create growing with LEARN and its own label clipped (2026-10-17 review). GOES IN: types/ui-showcase.md
- RULE: Do not share one overlay element between two moments in a seekable timeline; give each moment its own overlay. EVIDENCE: a butter flash
  tinted 49.0 s although it was meant for 49.2 s. GOES IN: references/motion-feel.md

- RULE: When a plate/photo hosts a screen, derive the screen quad from the image (threshold the lit area, convex hull, approxPolyDP) and overlay a debug
  polygon before animating; a hand-read corner was 14 px off and produced a visible sliver. GOES IN: references/living-stills.md (platefit)
- RULE: Never leave a hosted screen black for more than ~2 s of a beat meant to show the product on it; schedule the boot so the product is on screen for the
  majority of the shot. GOES IN: types/ui-showcase.md

## Skill feedback
- GOT IN THE WAY: section 6 assumes ELEVENLABS_API_KEY, GEMINI_API_KEY, a donor to analyse and yt-dlp; none were available or approved.
  FIX: add an "offline sound path" (local synth + a local music tool + local TTS) and a "no donor available" path for Original mode.
- GOT IN THE WAY: Original mode asks for 3 storyboard variants but has no cheap way to render one still per variant.
  FIX: ship a tiny hyperframes variant-board template (3 static scenes + snapshot).
- Tools written: tools/vclock + record_virtual.py (virtual-clock recorder), mix.py (synth SFX + ducked mix + loudnorm), prep_assets.py,
  build_hf.py (inlines hf/src into index.html), make_clips.sh (retimed clips).

## Reviewer notes
- "The mask for the computer screen isn't precise... many seconds on a black screen and a super rapid boot... Greia on for a tiny fraction of the time": fixed in revision 3.
- "Every: the voice says school but no text; not liking every school; make free / open source clearer": text now follows the voice; closing says free and open source, for every family.
- "Way too short / fast transitions, voices almost one over the other; slightly longer than 60 s isn't a drama": pauses added via timeline shifts; film is 68.3 s.
- Create icon clips with its label and another app from 0:14 (wrong layers): sprites now own their grid cell, the zooming icon is on top with a soft fade, label removed during the zoom.
- Wanted more on: agent/skill/tools incl. character voices, four languages, voiced for pre-readers, parent control by week, built for daughters then open, orca/dolphin/Encyclopedia, designed to grow, almost any hardware, a whole OS not an app: all added in revision 2.
