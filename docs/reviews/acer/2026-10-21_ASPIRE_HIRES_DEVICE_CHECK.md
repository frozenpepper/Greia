# Aspire 5720 hi-res and boot-logo device check (2026-10-21)

Evidence label: remote input (xdotool, DISPLAY=:0) and screen capture (PIL ImageGrab) on a physical device. NOT hands-on physical acceptance. Screenshots stay out of the repo.

Source: deployed SHA `b03cac977dc0e270e73571b701be054acc6976e1` (`/opt/greia-os/.deployed-sha`, via `tools/dev_source_deploy.py deploy`; parse gate 741 files; launcher and parent active, 0 restarts after swap). Device: Acer Aspire 5720, 1280x800, ~2 GB RAM, installed Greia RC.

## Boot logo (greia-devctl restart-launcher, 0.1 s capture loop)
- Pygame intro frames: 222x600 (native asset size), centred on pure white. PASS, not upscaled.
- Before them, for about 1 s, a 277x750 frame (1.25x upscale, same centring, white background) is shown. This is the early framebuffer splash (`greia-fb-splash.c`), which `GREIA_BOOT_EXPERIENCE.md` already lists as not yet native-size. Not a regression of the native-size change.

## Activities (Shell navigation by clicks; capture, pointer sweep over bands and scene, capture again)
| Activity | Result |
|---|---|
| alfabeto_leo | PASS. Fills the panel, 25 px bands top and bottom, Home top-left, no stripes or swapped colours, no pointer trail. |
| enciclopedia_greia | PASS. Same layout. Tiny white specks flicker with the pointer still, so they are animated sparkles, not trails. |
| sottomarino_giramondo | PASS. Fills the panel, no ghosting. Arrow-key hint row hidden once the mouse is used (expected). |
| teatrino_fiabe | PASS. Black 25 px bands, no artefacts. The "AVVIO..." loading screen was still showing 7 s after the click (slow start, see issues). |
| memory_meraviglie | PASS. Bands, Home and pointer correct. |
| writing (Scrittura e lettere) | PASS. Full-screen layout without bands. Typed "ciao ABC" renders at the first ruled line, caret placed correctly after the text. Home icon is low-contrast on the cream background (visible). |

Home returned to the Shell each time; the device was left on the Shell home screen (profile picker passed via GRETA).

## CPU (top, 3rd sample, 1 s interval, Activity python3 plus Xorg)
- alfabeto_leo: 12% + Xorg 13%.
- enciclopedia_greia: 52% + Xorg 46% (right after the pointer sweep).
- sottomarino_giramondo: 45% + Xorg 50% (animated scene).
- teatrino_fiabe: 2% (static scene). memory_meraviglie: 2% (static). writing: not sampled.
- Activity start time: no per-Activity READY line in the launcher log (`logs --service launcher`, 200 lines max). Only `launcher_interactive_ready` events were present.

## Wi-Fi
- `wlan0`: routable (configured), online. `firmware-iwlwifi` 20230210-5 installed.
- `/usr/lib/systemd/system-sleep/greia-wifi-resume` is the OLD version: no "b43legacy" (0 matches), reloads iwl3945 only, dated Oct 21 15:35. Source deploy only ships `/opt/greia-os`, so the overlay script needs a reimage or a separate install. Not suspended, not tested.

## Issues
1. Resume script on the device is old (above).
2. Every `greia-launcher` stop (deploy swap, restart-launcher) logs "Main process exited, code=exited, status=1/FAILURE" and "Failed with result 'exit-code'" (17:40:44, 17:46:28, 17:47:17, 17:47:35). No traceback. Stop path exits 1 instead of 0.
3. teatrino_fiabe still loading at 7 s.
4. Early framebuffer splash upscales 1.25x (known, documented).
5. No Python tracebacks in the last 5000 journal lines (`grep -iE "traceback|exception"` empty).
