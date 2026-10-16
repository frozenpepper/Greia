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

---

## Re-sweep at 0f560c2e

**Evidence class:** PHYSICAL DEVICE + remote input injection (`xdotool`, not physical input). The hidden-Activity rows and the per-phase, `set_mode` and pointer experiments are **STANDALONE DIAGNOSTIC**.
**Deployed:** `/opt/greia-os/.deployed-sha` = `0f560c2e`. This includes:
- 2af434da: the P0 launch-crash fix;
- 44aa49ed: the launch-speed work (pkg_resources blocked, read-only bytecode prefix `/usr/lib/greia/pycache` with 1,483 `.pyc` / 34 MB, C0 ready timeout 30 s, Shell at 10 Hz while an Activity runs);
- 0f560c2e: the frame governor in all 45 Activities.

**Same method as the first sweep, with these exceptions:**
- The idle window is 10 s (was 12 s) and the interaction window 8 s (was 10 s), to fit the play limit.
- **No device workaround was applied.** `activities/` was left at `greiapanel:pipprofiles 2770`. The 45 per-Activity directories left over from the first sweep already existed. This means the fix was exercised for "Parent-owned 2770 parent plus existing leaf", but **not** for creating a brand-new leaf under a foreign-owned parent. That case needs a fresh profile or a new Activity id to verify on device.
- No system files were touched, no session-script edit was made, and there was no launcher restart. `NRestarts` stayed 0 and the Shell kept the same PID throughout.
- **Play limit not raised.** The supported Parent path, `POST /api/v1/profiles/<id>/usage-limit`, requires a paired-device credential, and getting one means entering the Parent password (`/pairing/bootstrap`). I may not enter passwords. The sweep therefore ran within the remaining allowance: 2003 s → 3213 s used, about 6 minutes left today. For the same reason the `recommended_only` filter was not changed, and the 9 hidden Activities were measured standalone, through the shipped entry (`python3 -P -m greia_platform.python_activity_entry`) with `PYTHONPYCACHEPREFIX=/usr/lib/greia/pycache`.
- The first sweep's leftover saves and history rows are still in place. The history now holds 98 rows, including 38 new `graceful_stop` sessions. I found no supported Parent or platform operation that clears history for one profile, so nothing was cleared.

### R.1 Before / after

| Metric | 0148f113 | 0f560c2e |
|---|---|---|
| Activity launch from the Shell | crashed the Shell (P0) | **works; 0 crashes, `NRestarts` 0** |
| Shell launches succeeded on first try (visible 36) | 19 of 36 (17 `ready_timeout`) | **36 of 36**, all `graceful_stop` on Home |
| Tap → READY via Shell, median (range) | 16.3 s (13.5–20.6) | **10.3 s (6.9–14.9)** |
| Standalone READY, 9 hidden Activities | 11.1–14.9 s | **6.0–9.8 s** |
| Activities idling above 60% / 100% CPU | 19 / 12 of 29 | 22 / 13 of 36 (median 77%, was 88%) |
| Activity peak RSS | 145–197 MB | 137–203 MB (unchanged) |
| Shell CPU while an Activity is foreground | 9–14% | **5.7–9.1%** |
| Shell idle, Home / Collection page | 2.2–8.2% / 7–9% | 2.2–7.9% / 8.6% |
| Shell RSS | 147 MB at Home → 202 MB peak → 174 MB at Home | **141 → 222 MB peak, 217 MB at Home after 38 launches; monotonic (≈+2 MB per launch)** |
| Lowest MemAvailable | 384 MB | 443 MB (foresta_parole) |
| OOM events | none | none |
| Home → session ended | 0.71–1.95 s (memory 2.37 s forced, sillabe 4.37 s) | 0.55–1.79 s (corsa 2.88 s); **no forced stops** |
| Shell `set_mode` at start (boot markers) | 2.5–3.4 s | 2.84 s |

Per Activity (Shell; launch s / idle CPU% / interaction CPU% / peak RSS MB), old → new:

| Activity | 0148f113 | 0f560c2e |
|---|---|---|
| acquario_magico | 15.4 / 135 / 127 / 164 | 7.8 / 121 / 118 / 169 |
| baia_delle_orche | 14.0 / 125 / 111 / 164 | 7.3 / 102 / 93 / 161 |
| bosco_numeri | never launched | 11.3 / 23 / 107 / 163 |
| bottega_delle_misure | 17.7 / 45 / 39 / 166 | 12.6 / 56 / 66 / 158 |
| casa_del_dieci | timeout, then 16.2 / 48 / 58 / 160 | 12.1 / 49 / 37 / 158 |
| clinica_cuccioli | 15.2 / 53 / 36 / 157 | 8.5 / **128** / 126 / 157 |
| colline_allegre | timeout, then 18.3 / 114 / 111 / 150 | 14.3 / 115 / 110 / 161 |
| corsa_bacche | never launched | 12.0 / 137 / 119 / 158 |
| costruiamo_ponti | timeout, then 18.2 / 136 / 120 / 163 | 11.3 / 56 / 46 / 160 |
| enciclopedia_greia | 20.6 / 131 / 125 / 161 | 12.8 / 121 / 123 / 161 |
| foresta_parole | 17.3 / 119 / 116 / 184 | 10.2 / 120 / 116 / 184 |
| la_discesa_della_biglia | timeout, then 18.4 / 133 / 130 / 150 | 14.9 / 70 / 84 / 149 |
| labirinto_magico | never launched | 11.6 / 131 / 136 / 150 |
| luci_di_momo | 16.9 / 75 / 52 / 185 | 10.0 / 98 / 47 / 168 |
| memory_meraviglie | 15.3 / 12 / 49 / 167 | 10.2 / 12 / 37 / 175 |
| morbidi_mostriciattoli | timeout, then 16.1–17.5 / 51 / 61 / 197 | 11.6 / 64 / 63 / 189 |
| nanna_delle_nuvolette | timeout, then 17.4 / 88 / 79 / 148 | 12.2 / 82 / 85 / 155 |
| officina_dei_suoni | timeout, then 15.7 / 37 / 78 / 163 | 6.9 / 25 / 60 / 157 |
| orchestra_animali | timeout, then 16.2 / 108 / 99 / 164 | 10.4 / 112 / 106 / 168 |
| painting | 13.6 / 114 / 106 / 169 | 8.6 / **27** / 37 / 158 |
| pasticceria_magica | never launched | 12.8 / 45 / 71 / 166 |
| piccola_serra | never launched | 13.6 / 120 / 113 / 162 |
| posta_di_leo | 13.5 / 41 / 40 / 152 | 10.3 / 41 / 38 / 151 |
| quattro_amici | 16.3 / 45 / 97 / 160 | 10.5 / 47 / 96 / 149 |
| shape_garden | 16.0 / 128 / 125 / 160 | 9.7 / 117 / 125 / 161 |
| sillabe_magiche | 13.7 / 79 / 84 / 146 | 9.7 / 80 / 84 / 146 |
| sottomarino_giramondo | timeout, then 16.4 / 125 / 95 / 176 | 8.6 / 82 / 99 / 157 |
| specchi_magici | timeout, then 16.9 / 63 / 29 / 149 | 11.3 / 51 / 48 / 153 |
| stelle_incantate | timeout, then 16.3 / 50 / 104 / 148 | 10.2 / 62 / 86 / 148 |
| storie_della_mia_voce | never launched | 13.6 / 13 / 73 / 170 |
| teatrino_fiabe | 19.9 / 121 / 130 / 180 | 10.1 / 93 / 57 / 180 |
| torre_forme | 16.5 / 68 / 30 / 150 | 9.9 / 73 / 48 / 148 |
| viaggio_delfino | never launched | 14.8 / 125 / 117 / 203 |
| volo_draghetto | 14.1 / 126 / 131 / 170 | 7.5 / 126 / 132 / 165 |
| workshop_settings | 14.6 / 13 / 39 / 159 | 8.0 / 12 / 45 / 147 |
| writing | 14.2 / 115 / 113 / 148 | 8.8 / **45** / 55 / 138 |

Hidden by `recommended_only` (STANDALONE, shipped entry; READY s / idle CPU% / RSS MB):

| Activity | READY s | Idle CPU % | RSS MB |
|---|---|---|---|
| alfabeto_leo | 7.6 | 20 | 170 |
| cucciolo_mio | 9.8 | 34 | 141 |
| faccine_momo | 6.8 | 35 | 152 |
| festa_delle_rime | 6.0 | 20 | 156 |
| il_giardino_dei_numeri | 7.9 | 30 | 138 |
| mondo_contrari | 7.6 | 45 | 149 |
| nascondino_bosco | 6.7 | 30 | 140 |
| quattro_stagioni | 6.4 | 13 | 137 |
| treno_numeri | 8.4 | 49 | 138 |

None of the 45 first frames shows missing art, black boxes or wrong-language text (contact sheet refreshed at `~/.cache/greia-acer-test/sweep_firstframes.png`). Two items carried over from the first sweep:
- teatrino's recording sheet still shows a blank white title bar;
- Writing again turned the typed text "ciao mamma" into "ciaomamma" with `xdotool type --delay 120`. Single `xdotool key space` presses work. This is still unconfirmed on a physical keyboard.

### R.2 Per-phase launch breakdown (STANDALONE, shipped entry and env, seconds from spawn)

The wrapper timestamps the curated interpreter start-up and then patches `pygame.display.init/set_mode/flip` and `mark_activity_ready`. Spawn itself is under 3 ms. The Shell path adds roughly 3 s on top of these numbers (bwrap, brokers, Shell polling).

| Phase | writing | morbidi_mostriciattoli | viaggio_delfino |
|---|---|---|---|
| python start | 0.08 | 0.07 | 0.08 |
| curated startup + other imports → `import pygame` begins | 0.49 | 0.49 | 0.49 |
| `import pygame` done | 1.15 | 1.16 | 1.15 |
| Activity script starts (platform imports) | 1.42 | 1.45 | 1.48 |
| `display.init` | 1.85–1.96 | 1.92–2.03 | 1.96–2.08 |
| `set_mode` | 2.22 → **3.28 (1.06 s)** | 2.26 → **2.95 (0.69 s)** | 2.32 → **3.50 (1.18 s)** |
| first flip = READY | **5.45** (content 2.2 s) | **8.47** (content 5.5 s) | **12.69** (content 9.2 s) |
| same, with `SDL_FRAMEBUFFER_ACCELERATION=0` | set_mode 0.14 s, READY 4.64 | set_mode 0.03 s, READY 8.01 | set_mode 0.15 s, READY 11.80 |
| **RSS (normal → with that hint)** | **131.6 → 59.7 MB** | **166.8 → 98.7 MB** | **153.8 → 85.6 MB** |

**Why `set_mode` was about 4.6 s, and is still about 1 s.**

`set_mode` breakdown (same script, curated start-up):

| Case | `set_mode` |
|---|---|
| Plain script, no curated start-up | 2.0 s |
| With pkg_resources blocked (as shipped now) | 0.64 s windowed / 1.07 s `FULLSCREEN` |
| Plus `SDL_FRAMEBUFFER_ACCELERATION=0` | **0.03 s windowed / 0.15 s `FULLSCREEN`** |

Raw SDL through ctypes:

| Step | Default | With the hint |
|---|---|---|
| `SDL_CreateWindow` | 4 ms | 4 ms |
| `SDL_GetWindowSurface` | 413 ms | 1 ms |
| first `SDL_UpdateWindowSurface` | 237 ms | 12 ms |

The steady-state `flip` also dropped from 7 ms to 2–3 ms.

The two causes:

1. **pygame's lazy default-icon load.** `set_mode` loads `pygame_icon.bmp` through `pygame.pkgdata`, which imported `pkg_resources` and cost about 1.3 s on the Atom. 44aa49ed fixed this (pkg_resources is now blocked).
2. **SDL 2.26's X11 "texture framebuffer".** For the window surface, SDL creates an OpenGL renderer and streams the frame through a GL texture. That loads Mesa/libGL for GMA 950 into every process. It costs about 0.6–1.0 s of `set_mode`, about 70 MB of RSS per process, and double the per-flip cost.

Tested and **not** the cause: XRandR, XVidMode, XInput2, the input-method hints (`XMODIFIERS`, `SDL_IM_MODULE`), and the video driver choice (always x11). Window creation itself takes 4 ms.

**Proposed fix.** Set `SDL_FRAMEBUFFER_ACCELERATION=0` in the Activity environment (`runtime_adapter.py`, next to `SDL_VIDEODRIVER=x11`) and in `greia-launcher.service` for the Shell. The Shell's boot `set_mode` is still 2.84 s, and it would very likely see the same RSS saving: it is at 141 MB at start with the same GL path. Then confirm on device that pointer and presentation look identical.

**The remaining launch cost is Activity content construction (2–9 s), confirmed by cProfile:**
- viaggio_delfino:
  - `delfino_audio._init_sounds` synthesises audio in Python: 6.3 s profiled (`delfino_audio.py:124`).
  - `delfino_art.warm_thumbnails` / `_bake_scene` bakes four scenes eagerly: 6.0 s (`delfino_art.py:401,516,575`).
- morbidi_mostriciattoli: `MonsterAudio.__init__` still synthesises 15 WAVs through `pygame_audio.append_mono_pcm16`: 17.9 s profiled (`monster_audio.py:45,75,99-128`). **This was not addressed by 44aa49ed.**
- **Large `Surface.blit` cost**, about 3–7 ms per blit (morbidi 962 blits = 6.6 s, delfino 3,349 = 11.5 s profiled). This *suggests* source surfaces that are not `convert()`/`convert_alpha()`-ed to the display format. That is a hypothesis to check, not verified.

**Fix direction:**
- Ship pre-rendered audio assets, or synthesise lazily on first use.
- Bake thumbnails lazily or at build time.
- Audit `convert_alpha()` on loaded art.

### R.3 Pointer feel (move pointer → first repaint in an 80×80 box)

| Case | Median (range) |
|---|---|
| Minimal pygame reference app (calibrates the harness: ~38 ms per grab + XTest) | **~120 ms** |
| Shell Home | ~200 ms (103–269) |
| painting, via Shell | **380 ms** (352–423) |
| painting, standalone | 340 ms |
| painting, standalone, with the hint | 290 ms |
| writing, via Shell | **435 ms** (325–542) |
| writing, standalone | 332 ms |
| writing, standalone, with the hint | 237 ms |

So painting and writing add about 200–300 ms over the reference: pointer motion visibly trails the hand.

**Root cause (source).** Plain motion does yield `FrameKind.POINTER` (`frame_governor.py:219-232`). But painting treats every non-`SKIP` frame as a full `_draw()` + `flip()` — see its own comment at `painting_app.py:231-233`: "a pointer-only frame is a full redraw here". Writing uses the same `FrameGovernor(redraw_on_input=True, …)` loop. Every hover move therefore repaints the whole UI.

**Fix.** Keep a cached back-buffer (or the reference canvas) and on `POINTER` frames use the `present_pointer()` rect-repair path (`pygame_canvas.py:282-311`). Strokes can blit only their dirty rect. Exact per-frame draw time was not instrumented in-process.

### R.4 Remaining problems, ranked

1. **P1: Shell RSS grows monotonically, about 2 MB per Activity launch.** It went from 141 MB to a 222 MB peak, and was 217 MB at idle Home after 38 launches. It did not fall back as it did at 0148f113. On a 768 MiB reference floor this cuts headroom within a single play session. I did not localise it. Likely candidates are per-launch caches in the Shell (launch overlay or tile caches, history or session objects). It needs a bounded-cache audit and a long-run test.
2. **P1: 22 of 36 Activities still idle above 60% CPU after the governor, 13 above 100%.** The worst are corsa_bacche 137%, labirinto_magico 131%, clinica_cuccioli 128%, volo_draghetto 126%, viaggio_delfino 125%, enciclopedia_greia 121%, acquario_magico 121%, piccola_serra 120%, foresta_parole 120%, shape_garden 117%, colline_allegre 115%, orchestra_animali 112% and baia_delle_orche 102%. These are continuous scene animations, still costing about 40–100 ms per frame at the low-end ambient rate. clinica rose from 53% to 128%, which looks like a regression; confirm with a longer window. The fix is per-scene dirty-rect animation, plus a reference-floor policy that stops purely decorative motion after a timeout.
3. **P1: `SDL_FRAMEBUFFER_ACCELERATION` unset**, which costs about 70 MB RSS and up to 1 s launch time per process (R.2). This is the single largest cheap win.
4. **P1: launch is still 6.9–14.9 s via the Shell** (target ≤ 5 s). The remaining time is content construction (R.2). No Activity is near the new 30 s C0 timeout.
5. **P2: pointer latency of 380–435 ms in painting and writing** (R.3).
6. **P2: Shell boot `set_mode` 2.84 s** (`FULLSCREEN`, same framebuffer-acceleration cause).
7. **P3, unchanged from the first sweep:**
   - the "N MIN RIMAST…" pill is still clipped under the star badge (`child_shell.py:454-463`);
   - the title tooltip still overlaps neighbouring card labels (`presentation.py:1333-1336`);
   - the teatrino recording-sheet title bar is blank;
   - the Writing space loss under `xdotool type` is unconfirmed on a physical keyboard.
8. **Verification gap:** the P0 fix on a *new* per-Activity directory under a Parent-owned `activities/` (see method notes above).

### R.5 Device state left

- Shell left on Home: same PID as before the sweep, `NRestarts` 0, no OOM.
- Every `/tmp` file this sweep created is deleted. No system files, profile directories or settings were changed, and no restore was needed.
- About 6 minutes of today's play time remain.
- New history: 38 `graceful_stop` sessions, plus the first sweep's leftovers listed in §7.
