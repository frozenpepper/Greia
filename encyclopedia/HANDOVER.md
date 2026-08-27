# Greia Encyclopedia workstream handover

**Updated:** 2026-08-27  
**Current phase:** E0 — foundation workspace and contract  
**Runtime integration:** not started; this directory is intentionally not yet a discoverable Activity.

## Accepted owner direction

- Keep the encyclopedia engine very small.
- Treat section pages and final entries as executable Python pages.
- Different pages may use very different lightweight interactions.
- Examples explicitly accepted: slowly orbiting Solar System, erupting volcano.
- Do not assume child speech recognition.
- Do not assume on-device/runtime narration TTS.
- Normal character narration is prerecorded during authoring.
- Dani/system TTS and pronunciation-critical system speech are also generated ahead of time on parent/development hardware and packaged as files.
- Initial languages: Italian and English.
- Maintain one unified, precise voice-recording request file so a separate local agent can generate audio independently while page implementation continues.

## Files that own this workstream

```text
encyclopedia/README.md
encyclopedia/PLAN.md
encyclopedia/VOICE_RECORDING_REQUESTS.md
encyclopedia/HANDOVER.md
encyclopedia/engine/
encyclopedia/pages/catalogue.py
```

## Current v0.1 scope

43 executable pages:
- 1 home;
- 6 sections;
- 36 final entries.

See `PLAN.md` for the exact ledger.

## What exists now

- detailed architecture/content/sequencing plan;
- page IDs and first-version scope;
- independent audio queue protocol;
- first 14 requested navigation/section clips (7 semantic cues × it/en);
- tiny pure-Python page lifecycle/navigation foundation;
- explicit planned-page catalogue.

## What does not exist yet

- Greia `activity.toml`;
- real Activity `main.py`;
- Pygame renderer;
- integrated Greia localization/audio adapters;
- finished Home page;
- section pages;
- researched final entries;
- packaged voice assets;
- source/simulator/physical acceptance.

Do not call the encyclopedia a working Greia Activity yet.

## Next exact step

Phase E1:

1. inspect current Greia Activity runtime/source contracts again at current `main`;
2. create the actual first-party Activity shell without weakening runtime policy;
3. integrate the minimal page navigator into the real Pygame/Greia lifecycle;
4. implement one visual Home page and one section transition;
5. add it/en localization;
6. run relevant source verification;
7. run the mandatory real Greia Simulator launch/survival/transition/Home gate;
8. record the exact result here and in the root project handover as required.

The independent local voice agent may meanwhile process only `REQUESTED` rows in `VOICE_RECORDING_REQUESTS.md`.
