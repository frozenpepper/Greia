# Greia launch film

`../final.mp4` (1920x1080, 30 fps, 60.0 s, sound) is rendered from the HyperFrames project in `hf/`.

```
hf/                 the HyperFrames project (index.html is generated from hf/src/*; assets/ holds everything it needs)
timeline.json      scene starts, VO and word times shared by visuals and mixer
storyboard/         stills for every shot, contact sheet, three-direction comparison
assets/audio/       VO takes (tools/greia_voice.py), music cue (songkit), requests
tools/              prep_assets.py, build_hf.py, make_clips.sh, mix.py, record_virtual.py (+vclock), mkscripts_v.py
BREAKDOWN.md        the build contract: grid, script, shots, sound, directions
SCRIPT.md           the first script draft; LOG.md rounds; LESSONS.md what the skill should learn
```

Rebuild: `python3 tools/prep_assets.py && python3 tools/build_hf.py && python3 tools/mix.py`, then in `hf/`:
`node /Applications/HyperFrames.app/Contents/Resources/app.asar.unpacked/node_modules/hyperframes/bin/hyperframes.mjs render --quality delivery -o out.mp4`
(or open `hf/` in the HyperFrames desktop app). Large intermediates (captures, recordings, renders) live on `/Volumes/Venus/GREIA_LAUNCH_VIDEO/`.
Footage is regenerated with `tools/record_virtual.py` (needs the Greia repo; the clips used are already in `hf/assets/video`).
