# Acer Aspire One Activity sweep — launch, idle/interaction CPU, memory (2026-10-16)

**Evidence class:** PHYSICAL DEVICE + remote input injection (`xdotool` on `DISPLAY=:0` over SSH; not physical input).
Sixteen rows are additionally **STANDALONE DIAGNOSTIC** (see §1).
**Device:** Acer Aspire One, Intel Atom N270 (1 core / 2 HT threads), 1 GB RAM, no swap, i686, Debian 6.1.0-53-686, Python 3.11.2, pygame 2.1.2 / SDL 2.26.5, Xorg 1024×600.
**Deployed tree:** `/opt/greia-os` = `main` **0148f113** (not redeployed during this sweep). Profile: one child profile (locale `it`, age 6, `visibility_mode=recommended_only`).
**Operator:** acer-test agent. Repository not modified apart from this report.

CPU% is per logical CPU, so the ceiling is 200%. A value above 100% means both hyperthreads are busy. Idle = the 12 s window right after READY with no input. Interaction = a 10 s window of scripted taps, keys or drags. RSS = the Activity process tree (bwrap + python).

---

## 0. Headline

1. **P0: No Activity can launch on this device as shipped.** The first tap on any Activity card crashes the whole child Shell (`ProfileError`), and the session drops to `trusted_presentation`. The bug is reproducible and has a deterministic root cause in source (§3.1). The rest of the sweep needed a temporary, reversible workaround on the device (§1), which has since been undone.
2. **P0/P1: Every Activity takes 13.5–20.6 s to reach READY through the Shell, against a hard 15 s ready timeout.** In the first pass 17 of 36 Shell-launched Activities were killed with `ready_timeout`. On a retry 10 of those launched, at 15.7–18.4 s. Seven never launched through the Shell in two attempts. The kill depends on when the Shell happens to poll, so launches near 15 s pass or fail by chance.
3. **P1: The image ships with no Python bytecode at all.** That adds about 3.3 s of compile time to every Activity launch and about 2.5 s to Shell start.
4. **P1: 19 of 29 measured Activities use more than 60% CPU while idle** (up to 136%). Most redraw and flip the full frame at 20–30 fps even when nothing changes.
5. Memory: there was no OOM, and MemAvailable never fell below 384 MB. Activities hold 145–197 MB RSS each. The Shell grew from 147 MB at Home to a 202 MB peak, then 174 MB at Home after 57 sessions.

## 1. Method and deviations (read before using the numbers)

- **Launch time.** Measured as the remote tap timestamp on the device clock (`time.time()` just before `xdotool click`) to `sessions.ready_at` in the profile's `progress/history.sqlite3`. The Shell records `ready_at` when it polls the Activity's READY marker. Activities write that marker after their first `display.flip()`. The supervisor `started_at` came 0.49–0.55 s after the tap in every case.
- **CPU and RSS.** A 1 Hz `/proc` sampler on the device (`/tmp/gsweep.py`, now deleted). It costs about 1–2% CPU.
- **Home.** Tap at (38, 38), then time until `sessions.ended_at`. The first-screen-change time is listed but it is noisy: it often catches the button's press feedback, not the Shell being redrawn.
- **Shell navigation timing.** Screen-hash polling with PIL, about 60 ms per grab in a separate process. That polling competes for CPU, so these numbers are an upper bound.
- **Workaround applied for §2 (device-state change; now reverted).** Every launch crashed the Shell because of §3.1. To measure Activities at all I did the following:
  - ran `chown greiakid` on `/var/lib/greia-profiles/data/<profile>/activities`, which had been `greiapanel:pipprofiles 2770`;
  - pre-created `activities/<id>` and `storage/<id>` for all 45 Activity ids, as `greiakid:pipprofiles 0770`;
  - pre-created `storage/`, as `greiakid:pipprofiles 2770`.

  At the end, `activities/` was restored to `greiapanel:pipprofiles 2770`. **The device is therefore back in the crash-on-launch state that `main` produces.** The per-Activity directories and the sweep's saves remain: 752 files, 7.9 MB under `activities/` and 632 KB under `storage/`. `storage/` is now mode 0770 because the Shell's own code removed its setgid bit (§3.1).
- **Traceback capture.** I used the ops-manual `session.err` technique: I edited `/usr/local/lib/greia-os/greia-x-session` and added `-X faulthandler`. The file was restored byte-identical (sha256 `91d311cf…f20e`, 775 root:root). `greia-launcher` was restarted three times in total: once to load the capture, once to return from the crash fallback, and once after restoring. `NRestarts` stayed 0 throughout.
- **Hidden Activities.** `recommended_only` hides 9 Activities from every Collection: alfabeto_leo, cucciolo_mio, faccine_momo, festa_delle_rime, il_giardino_dei_numeri, mondo_contrari, nascondino_bosco, quattro_stagioni and treno_numeri. I did not change the parent policy. These 9, and the 7 that never launched through the Shell, were measured **STANDALONE**. That means running `python3 main.py` as `greiakid` with the Activity environment, outside bwrap and the supervisor, with no storage or event broker and no Home chrome. Standalone READY is about 3.5 s faster than the Shell path (writing: 10.7 s standalone against 14.2 s through the Shell).
- **Orphaned processes.** A harness bug left 8 orphaned standalone Activity processes for about 1 minute. I killed them; there was no OOM and `NRestarts` was 0.
- **Usage limit.** The sweep used the profile's 60-minute daily limit down to about 26 minutes remaining. I made no setting changes.

## 2. Per-Activity results

Shell = launched by tapping its Collection card. "Launch" is tap → READY. Where there were two attempts, the values are shown as `1st / 2nd`.

| Activity | Path | Launch s | Idle CPU % | Interact CPU % | Peak RSS MB | RSS growth MB | Home → ended s | Issues |
|---|---|---|---|---|---|---|---|---|
| acquario_magico | Shell | 15.4 | 135 | 127 | 164 | +3 | 1.02 | idle >100% |
| alfabeto_leo | standalone | (12.9) | 20 | – | 173 | – | – | hidden by policy |
| baia_delle_orche | Shell | 14.0 | 125 | 111 | 164 | +4 | 1.37 | idle >100% |
| bosco_numeri | Shell ✗✗ / sa | timeout / timeout (sa 11.7) | sa 23 | – | sa 154 | – | – | **never launched via Shell** |
| bottega_delle_misure | Shell | 17.7 | 45 | 39 | 166 | +11 | 0.90 | over 15 s, survived |
| casa_del_dieci | Shell | timeout / 16.2 | 48 | 58 | 160 | +3 | 1.35 | flaky launch |
| clinica_cuccioli | Shell | 15.2 | 53 | 36 | 157 | +1 | 1.01 | |
| colline_allegre | Shell | timeout / 18.3 | 114 | 111 | 150 | +1 | 0.94 | flaky; idle >100% |
| corsa_bacche | Shell ✗✗ / sa | timeout / timeout (sa 14.4) | sa 89 | – | sa 143 | – | – | **never launched via Shell** |
| costruiamo_ponti | Shell | timeout / 18.2 | 136 | 120 | 163 | +14 | 1.95 | flaky; highest idle CPU |
| cucciolo_mio | standalone | (14.7–14.9) | 31 | – | 149 | – | – | hidden |
| enciclopedia_greia | Shell | 20.6 | 131 | 125 | 161 | +11 | 0.81 | slowest successful launch |
| faccine_momo | standalone | (12.0–12.1) | 34 | – | 156 | – | – | hidden |
| festa_delle_rime | standalone | (11.1–11.2) | 21 | – | 158 | – | – | hidden |
| foresta_parole | Shell | 17.3 | 119 | 116 | 184 | +2 | 0.81 | |
| il_giardino_dei_numeri | standalone | (13.0–13.1) | 35 | – | 140 | – | – | hidden |
| la_discesa_della_biglia | Shell | timeout / 18.4 | 133 | 130 | 150 | 0 | 0.97 | flaky |
| labirinto_magico | Shell ✗✗ / sa | timeout / timeout (sa 15.0–17.0) | sa 72 | – | sa 138 | – | – | **never launched via Shell** |
| luci_di_momo | Shell | 16.9 | 75 | 52 | 185 | +16 | 1.02 | lowest MemAvailable (384) |
| memory_meraviglie | Shell | 15.3 | 12 | 49 | 167 | +7 | **2.37 forced_stop** | ignores graceful stop |
| mondo_contrari | standalone | (12.9) | 38 | – | 153 | – | – | hidden |
| morbidi_mostriciattoli | Shell | timeout / 16.1 / 17.5 | 51 (17 after 5 min) | 61 | 197 | +14 | 1.03 | largest RSS; flaky |
| nanna_delle_nuvolette | Shell | timeout / 17.4 | 88 | 79 | 148 | +1 | 0.96 | flaky |
| nascondino_bosco | standalone | (11.8–12.0) | 29 | – | 144 | – | – | hidden |
| officina_dei_suoni | Shell | timeout / 15.7 | 37 | 78 | 163 | +4 | 0.98 | flaky |
| orchestra_animali | Shell | timeout / 16.2 | 108 | 99 | 164 | +3 | 0.83 | flaky |
| painting | Shell | 13.6 | 114 | 106 | 169 | +13 | 0.78 | idle >100% on a blank canvas |
| pasticceria_magica | Shell ✗✗ / sa | timeout / timeout (sa 15.8) | sa 44 | – | sa 147 | – | – | **never launched via Shell** |
| piccola_serra | Shell ✗✗ / sa | timeout / timeout (sa 15.9–16.1) | sa 103 | – | sa 143 | – | – | **never launched via Shell** |
| posta_di_leo | Shell | 13.5 | 41 | 40 | 152 | +3 | 0.71 | |
| quattro_amici | Shell | 16.3 | 45 | 97 | 160 | +10 | 0.86 | |
| quattro_stagioni | standalone | (11.5–11.7) | 11 | – | 138 | – | – | hidden |
| shape_garden | Shell | 16.0 | 128 | 125 | 160 | +6 | 0.99 | idle >100% |
| sillabe_magiche | Shell | 13.7 | 79 | 84 | 146 | +1 | **4.37** | slow graceful stop |
| sottomarino_giramondo | Shell | timeout / 16.4 | 125 | 95 | 176 | +19 | 0.79 | flaky; largest RSS growth |
| specchi_magici | Shell | timeout / 16.9 | 63 | 29 | 149 | +2 | 0.90 | flaky |
| stelle_incantate | Shell | timeout / 16.3 | 50 | 104 | 148 | 0 | 0.88 | flaky |
| storie_della_mia_voce | Shell ✗✗ / sa | timeout / timeout (sa 14.7–14.9) | sa 10 | – | sa 153 | – | – | **never launched via Shell** |
| teatrino_fiabe | Shell | 19.9 | 121 | 130 | 180 | +9 | 1.28 | presents every frame |
| torre_forme | Shell | 16.5 | 68 | 30 | 150 | 0 | 1.44 | |
| treno_numeri | standalone | (13.5) | 62 | – | 138 | – | – | hidden |
| viaggio_delfino | Shell ✗✗ / sa | timeout / timeout (sa 17.7–17.9) | sa 103 | – | sa 161 | – | – | **never launched via Shell**; slowest standalone |
| volo_draghetto | Shell | 14.1 | 126 | 131 | 170 | +5 | 0.95 | idle >100% |
| workshop_settings | Shell | 14.6 | 13 | 39 | 159 | +7 | 0.87 | a settings screen takes 14.6 s |
| writing | Shell | 14.2 / 13.7 | 115 | 113 | 148 | +3 | 0.72 | idle >100%; space lost once under fast synthetic typing |

Notes:
- **Shell-launch totals.** 25 `ready_timeout`s across 57 Shell sessions. Of the 36 visible Activities, 29 eventually launched and 7 never did in two tries. A `ready_timeout` shows the sad-cloud badge on the Collection page and the child stays on the page.
- **Home.** Every launched Activity returned to its originating Collection page. Session end took 0.71–1.95 s, except memory_meraviglie (2.37 s, `forced_stop`) and sillabe_magiche (4.37 s).
- **Visual check.** I looked at 2–3 frames per Activity (`*_1`, `*_2`, `*_3`) and found no missing art, black boxes or wrong-language text. Minor: in teatrino's recording sheet, the title field renders as a blank white bar.
- **Idle-window caveat.** The idle window starts at READY, so it includes intro animation and voice. morbidi dropped from 51% to 17.5% after 5 minutes. Treat these as "first 12 s" numbers.

## 3. Problems ranked by severity

### 3.1 P0 — Every Activity launch crashes the child Shell (profile directory contract)

The traceback was captured in `session.err` (abridged):
```
greia_launcher/main.py:1013 _launch_selected -> supervisor.start
greia_launcher/supervisor.py:292 profile.activity_data_dir(manifest.activity_id)
greia_platform/profiles.py:230 _ensure_managed_directory(target, self.root, mode=0o770)
greia_platform/profiles.py:723 ProfileError: managed profile directory mode is 2770, expected 0770,
  and chmod was refused: /var/lib/greia-profiles/data/<profile>/activities
```

**Root cause (source).**
- `profiles.py:230`, and the same pattern at `:241` for `activity_storage_dir`, call `_ensure_managed_directory(target, root, mode=0o770)`.
- `_ensure_managed_directory` (`profiles.py:747-770`) applies that *leaf* mode to **every component** under the profile root. That includes the parent `activities/`, which line 228 had just required to be `0o2770`.
- On this device the Parent service created `activities/` as `greiapanel` on 2026-10-06. `ProfileStore._ensure_context_directories` (`profiles.py:641-670`) excludes only `storage` and `progress` from Parent pre-creation, not `activities`. The child therefore cannot chmod it, and every launch fails.
- If the child did own `activities/`, the same call would remove its setgid bit (observed on `storage/`: now 0770). A newly created leaf would then get gid `greiakid` (994), not `pipprofiles` (995), and fail the group check instead.
- This has been latent since commits b6b82b84/cf204c8e (2026-10-07) turned chmod refusal into a hard error. The profile's history contains only crashed sessions from before this sweep (`platform_restart`, never READY).

**Second fault.** `main.py:1013` does not catch `ProfileError` from `supervisor.start`. A failure that should affect one launch instead kills the Shell process, and xinit falls back to `trusted_presentation`.

**Suggested fix.**
- Enforce the per-component modes in `activity_data_dir` and `activity_storage_dir`: 2770 for the parent, then 0770 for the leaf only. For example, ensure the parent, then mkdir and check the leaf alone.
- Either add `activities` to `CHILD_OWNED_DIRECTORY_NAMES` or accept a parent-owned 2770 parent without trying to chmod it.
- Contain launch-preparation exceptions in `_launch_selected` as a failed launch.
- Add a regression test that runs a Parent-created profile followed by a child launch under distinct uids.

### 3.2 P0/P1 — Launch time is at or above the hard 15 s ready timeout, so launches are flaky or impossible

- **Measurements.** The ready timeout is `supervisor.py:123` (`ready_timeout_seconds=15.0`). Successful Shell launches measured 13.5–20.6 s, with a median of about 16.3 s. A launch beyond 15 s survives only if the Shell's poll arrives late. The Shell loop is starved while the Activity compiles and imports at about 100% CPU, so the outcome is effectively random. Seven Activities, with standalone READY times of 11.7–17.9 s, failed both attempts.
- **Profile of morbidi (cProfile, standalone).**
  - `MonsterAudio.__init__` synthesises 15 WAVs in pure Python: 18.8 s of 38 s under the profiler (`activities/morbidi_mostriciattoli/monster_audio.py:45,75,99-128`, `greia_platform/pygame_audio.py:26 append_mono_pcm16`).
  - Source compilation: `compile` 5.0 s across 220 modules (§3.3).
  - The `pkg_resources` import pulled in by `pygame.pkgdata`: 3.6 s.
  - `get_shared_visual_path`: 3.4 s across 9 calls (`greia_platform/activity_api.py:381-404` via `activity_controls.py:460-523`).
  - `display.set_mode`: 4.6 s.
- **Shell overhead.** About 3.5 s over standalone: bwrap, brokers, and the pre-READY overlay that redraws and flips at 10 fps (`main.py:1119-1129`) and competes with the starting Activity for CPU.
- **Suggested fixes.**
  - Make the ready timeout reflect the hardware: either scale it per device class or treat it as a *liveness* check (process alive and progressing) rather than a hard 15 s kill.
  - Remove or precompute startup work: pre-render tone assets at build time, cache or lazily synthesise audio, and memoise shared-visual lookups.
  - Avoid importing `pkg_resources`.
  - Stop the pre-READY overlay from repainting at 10 fps.
  - Target READY ≤ 5 s on the N270.

### 3.3 P1 — No bytecode in the image: every Python process recompiles

- **On device.** `/opt/greia-os/src` has 0 `.pyc` files for 219 `.py` files. The stdlib has 91 `.pyc` for 544 `.py`, and dist-packages (pygame, PIL, pkg_resources) 36 for 697. The cause is `build/lib/compose.sh:1024`, which deletes every `__pycache__` in the rootfs, combined with `PYTHONDONTWRITEBYTECODE=1` in `greia-launcher.service` and the Activity environment.
- **Measured.** The common Activity import set takes 5.26 / 5.12 s without bytecode and 1.97 / 1.94 s with a warm pyc cache (`PYTHONPYCACHEPREFIX`), about 3.2 s saved per launch. The Shell import (`greia_launcher.child_shell`) takes 7.6 s without bytecode.
- **Suggested fix.** At compose time, precompile platform, stdlib and dist-packages with `compileall --invalidation-mode unchecked-hash` (or `checked-hash`). This keeps Activity folders bytecode-free as the validation policy requires. Measure the footprint: the partial cache in this test was 7.4 MB.

### 3.4 P1 — High idle CPU from unconditional full-frame redraw

- **Scope.** 19 of 29 Shell-measured Activities exceeded 60% idle, and 12 exceeded 100%. The worst are costruiamo_ponti, acquario_magico, la_discesa_della_biglia, enciclopedia_greia, shape_garden, volo_draghetto, baia_delle_orche, sottomarino, teatrino, foresta, writing, painting and colline.
- **Per-thread check (writing).** The main Python thread accounts for about 96%; SDL audio threads are negligible.
- **Examples.**
  - `activities/writing/writing_app.py:204-215` and `activities/painting/painting_app.py:209-224` call `_draw()` and `display.flip()` every iteration at 30 fps with no dirty gating.
  - `activities/teatrino_fiabe/teatrino_app.py:419-421` gates `render()` but still calls `canvas.present()` and `flip()` every frame ("platform draws the Greia pointer here"). `PygameReferenceCanvas.present` (`greia_platform/pygame_canvas.py:226-260`) fills, blits and clips the full 1024×600 surface each time.
- **Effect.** On a 1-core Atom this drains the battery, slows input response and slows the Shell's poll loop.
- **Suggested fix.** Adopt the dirty/animating gating that morbidi, ponti and biglia already use. Present only on change or pointer motion, and use `display.update(rects)` for the pointer. Add a platform lint or performance test for "no flip without dirty".

### 3.5 P2 — Shell CPU and memory

- **CPU while an Activity is in the foreground.** The Shell uses 9–14% CPU continuously. `main.py:1131` polls at 50 Hz (`time.sleep(0.02)` with `supervisor.poll` every pass). Suggest about 5–10 Hz while RUNNING.
- **Idle CPU in the Shell UI.**

  | Screen | Idle CPU |
  |---|---|
  | Profile picker | 1.8% |
  | Home, fresh | 2.2% |
  | Home, after the sweep (time pill shows minutes) | 8.2% |
  | Collection pages | 7–9% |

  The collection pages show a constant animated sparkle or selection and a title tooltip. These pages are not fully dirty-redraw idle.
- **RSS.** The launcher grew from 141 MB (picker) and 147 MB (Home) to a 202 MB peak during the sweep. It was back at 174 MB at Home after 57 sessions; I did not determine whether it plateaus. Worth a bounded-cache audit (images or tile caches per Collection page).

### 3.6 P2 — Activity stop and lifecycle

- memory_meraviglie did not exit within the graceful-stop window. Home produced `forced_stop` after 2.37 s.
- sillabe_magiche took 4.37 s to stop gracefully.
- Both should check `activity_stop_requested()` in every loop and modal state.

### 3.7 P3 — Visual and UX glitches (Shell)

- **Clipped time pill.** The Home "1 H RIMASTE" / "26 MIN RIMAST…" pill is clipped under the star badge. `child_shell.py:454-463` anchors the pill at `width - pill_width - 14` without reserving the achievement badge's area.
- **Title tooltip overlaps neighbouring labels.** On Collection pages the hover/selection tooltip overlaps the card label below or above it. Seen with "LA CASA DEL DIECI" over "BAIA DELLE ORCHE" and "ENCICLOPEDIA DI GREIA" over "LA BOTTEGA…". The cause is `presentation.py:1333-1336`: the tooltip goes below the card whenever `py < 65`, which is every first-row card.
- **Inconsistent Back position.** "Le mie creazioni" has Back at bottom-left (56, 556) and no top-left avatar or Back button, unlike the other Collections.
- **Writing.** With 12 ms per character `xdotool type`, "ciao mamma" became "ciaomamma". The space was not lost at 200 ms per character. This needs a physical-keyboard check. A suspect is the `_swallow_text` path (`activities/writing/writing_app.py:320-332,373-376`).

### 3.8 Note — the fallback is not a busy loop

`trusted_presentation` showed 60–100% CPU in `ps` right after the crash. That was startup averaging: sampled idle it measured 1.5%.

## 4. Shell timings (remote tap → first screen change; upper bound, see §1)

| Transition | Time s |
|---|---|
| Profile picker → Home | 0.80 |
| Home → Crea (first visit) | 1.34 |
| Home → Le mie creazioni (first visit) | 2.02 |
| Home → Gioca / Impara / Esplora / Mio Greia (first visit) | 0.71 / 0.57 / 0.57 / 0.30 |
| Collection → Home (Back) | 0.22–0.44 |
| Collection next page | 0.29–1.20 (Esplora p2 first visit 1.20) |
| Folder (Mare) open | 0.41 |
| Activity Home → session ended | 0.71–1.95 typical |
| Shell process start → `launcher_interactive_ready` | 4.1–6.2 s (boot markers `launcher_python_enter`→`launcher_interactive_ready`; X `set_mode` alone 2.5–3.4 s) |

## 5. Memory picture

- **MemAvailable.**
  - Before the sweep: 646 MB, with the Shell on the picker.
  - Lowest observed: 384 MB, during luci_di_momo interaction.
  - Typical with an Activity running: 410–470 MB.
  - At Home after the sweep: 527 MB.
  - After restoring and restarting the Shell: 618 MB.
- **OOM.** No swap exists. `dmesg` shows no OOM events and `NRestarts` stayed 0.
- **Footprint.** With one Activity running, Shell (about 175–200 MB) plus Activity (145–197 MB) plus Xorg (about 35–60 MB) is roughly 400 MB of RSS. That leaves about 400 MB of headroom on 1 GB. The 768 MiB reference-floor estimate would leave about 150 MB, which is tight.

## 6. Activities that feel slow

- **Launch > 3 s.** All 45. Shell launch is 13.5–20.6 s and standalone READY is 11.1–17.9 s.
- **Slowest Shell launches.** enciclopedia_greia 20.6 s, teatrino_fiabe 19.9 s, la_discesa_della_biglia 18.4 s, colline_allegre 18.3 s, costruiamo_ponti 18.2 s, bottega_delle_misure 17.7 s, morbidi_mostriciattoli 17.5 s.
- **Never launched via the Shell.** bosco_numeri, corsa_bacche, labirinto_magico, pasticceria_magica, piccola_serra, storie_della_mia_voce, viaggio_delfino.
- **Idle CPU > 60%.**

  | Activity | Idle CPU % |
  |---|---|
  | costruiamo_ponti | 136 |
  | acquario_magico | 135 |
  | la_discesa_della_biglia | 133 |
  | enciclopedia_greia | 131 |
  | shape_garden | 128 |
  | volo_draghetto | 126 |
  | baia_delle_orche | 125 |
  | sottomarino_giramondo | 125 |
  | teatrino_fiabe | 121 |
  | foresta_parole | 119 |
  | writing | 115 |
  | colline_allegre | 114 |
  | painting | 114 |
  | orchestra_animali | 108 |
  | nanna_delle_nuvolette | 88 |
  | sillabe_magiche | 79 |
  | luci_di_momo | 75 |
  | torre_forme | 68 |
  | specchi_magici | 63 |

  Standalone only: viaggio_delfino 103, piccola_serra 103, corsa_bacche 89, labirinto_magico 72, treno_numeri 62.

## 7. Device state left behind

- Shell restarted on the original session script and left on Home; `NRestarts` 0.
- All `/tmp` files and `/run/greia-os/session.err` created for this sweep are deleted.
- Profile `activities/` ownership and mode restored, so the §3.1 crash reproduces again.
- Retained: the per-Activity data directories and saves created during the sweep, and 57 history rows (25 `ready_timeout`).
- The profile's daily usage is down to about 26 minutes remaining for today.
- First-frame contact sheet, kept locally and not in the repository: `~/.cache/greia-acer-test/sweep_firstframes.png`. Shell first frames are used where a launch succeeded, standalone frames otherwise.
