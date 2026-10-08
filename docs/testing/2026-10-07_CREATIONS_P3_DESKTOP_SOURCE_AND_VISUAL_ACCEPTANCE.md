# Creations Library P1–P7 — Accumulated Desktop Source, Simulator + Draft-Curation Acceptance

**Scope:** non-destructive desktop **SOURCE and SIMULATOR** evidence for the 2026-10-07 Creations work, not hardware acceptance.  
**Pinned source candidate:** `9d8da5ba6a34c6d3efa8da84748406b82c5ace64` (P7 batch-4 source/test + 22-candidate draft roster checkpoint; later documentation-only commits may follow).  
**Authority:** `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md` and sibling `PROGRESS.md`.  
**Expected state:** P1 adaptive capacity, P3 Gallery/authenticated trusted modal, P4 PNG interoperability, and P5 WAV + UTF-8 routes exist SOURCE-WIP. One launcher-composed `VolumeBudget` now owns variable child-data growth for Activity private storage, My Creations and history; shipped private Activity namespaces scale to 25% of the actual writable data filesystem while aggregate positive growth remains bounded by the 75% used ceiling + 512 MiB free floor. Storie della Mia Voce publishes saved narration WAVs; Teatrino can puppeteer without microphone contention; Orchestra owns durable non-autoplay backing tracks; Writing and Posta exchange independent UTF-8 snapshots. **P6 source owns a draft, release-fail-closed 22-item candidate roster; P7 has source-reviewed 28/45 (six withheld). None of the accumulated P1–P7 source has been accepted in a complete checkout or real GUI/audio/text/capacity/gameplay run yet.** Hardware evidence remains separate.

## Instructions for one local desktop agent

Work in the authorized existing Greia macOS checkout. This is **not** an installer/flash/rebuild/Acer task.

### 0. Safety and exact checkout identity

1. Do not modify, delete, chmod or clean unrelated project data; do not flash, repartition, run a privileged Greia release builder, reboot the Acer or touch physical media. No production child profiles or actual children's pictures/recordings in this test.
2. `cd` to the existing local clone and record `pwd`.
3. `git status --short`; if there are modifications not explicitly authorized for this test, **STOP** and report filenames/HEAD. Do not stash, reset or silently discard changes.
4. `git fetch origin main` and `git switch main && git merge --ff-only origin/main`. If ff-only fails, STOP; do not merge/rebase/reset.
5. `git rev-parse HEAD`, `git merge-base --is-ancestor 9d8da5ba6a34c6d3efa8da84748406b82c5ace64 HEAD` (exit **0** required). Check `git diff --name-only 9d8da5ba6a34c6d3efa8da84748406b82c5ace64 HEAD -- src activities runtime tests build`. It should be empty for this pinned code candidate; if not, STOP and report new source changed by other work.

### 1. Source preflight

Use the project's existing working Python interpreter/environment. If any of Python, Pillow, pygame, Tk or the repository dependencies are missing, report the missing dependency rather than installing globally. A **new disposable local venv** is permitted for ordinary developer dependencies as per Greia setup docs; don't change locked product runtime/import policy to placate the test.

In a Bash shell, create a unique evidence directory under the repository's ignored `tmp/` area, without modifying existing evidence:

```bash
EVIDENCE="tmp/creations-p3-acceptance-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$EVIDENCE"
git rev-parse HEAD > "$EVIDENCE/HEAD.txt"
git status --short > "$EVIDENCE/git-status.txt"
```

For each test command below, redirect its entire output to a *different* descriptive `"$EVIDENCE/<test>.log"`, check its exact exit code before running the next, and retain all failure output. Do not `rm -rf`, truncate previous evidence or modify source merely to make a command green.

Run each command **sequentially** and save stdout/stderr + exit status; if any fails, STOP before proceeding to the GUI, report the **first** failure, and do not claim acceptance.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_creation_*.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_painting_creations.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_shape_garden_project.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_shape_garden_creations.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_teatrino_shared_backdrop_repository.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_teatrino_shared_backdrop.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_teatrino_audio_narration.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_teatrino_shared_narration.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_voice_creations.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_voice_creations_storage.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_teatrino_fiabe.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_pygame_png.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_shell_window_legacy_x.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_system_chrome.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_trusted_chrome_supervisor.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_simulator_system_chrome.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_index.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_supervisor.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_profiles.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_profile_volume_budget.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_writing_creations.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_posta_di_leo_creations.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_orchestra_backing_store.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_orchestra_creations.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_orchestra_manifest.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_release_selection.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_stage_release_activities.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_greia_release.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_action_pointer_boundaries.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_colline_allegre.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_corsa_bacche.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_labirinto_magico.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_quattro_amici.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_torre_forme.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_viaggio_delfino.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_volo_draghetto.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_event_idempotency.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_p7_batch3_source_regressions.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_acquario_magico.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_baia_delle_orche.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_clinica_cuccioli_refactor.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_faccine_momo.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_il_giardino_dei_numeri.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_luci_di_momo.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_alfabeto_leo.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_bosco_numeri.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_bottega_delle_misure.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_casa_del_dieci.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_festa_delle_rime.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_foresta_parole.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_morbidi_mostriciattoli.py' -v
make verify
```

If the repo's `make verify` chooses its canonical interpreter, that environment is the evidence. Never treat the isolated `33/33` mirror suite from the assistant as a substitute. Review any failure for a real source bug; report the shortest reproducible traceback/source snippet. Do not widen a sandbox policy or skip tests.

### 2. Real Pygame desktop visual acceptance (no hardware)

Only after §1 is green, start the canonical Greia Activity Simulator:

```bash
python3 tools/greia_simulator.py
```

Use a newly created **disposable simulator-only child profile**, not a real child's existing profile. Select viewport **1024×600**, Italian, normal UI size; launch the real child Shell window. Test with mouse and keyboard. Keep the real child Shell window visible, not just the developer control panel.

Capture **actual screenshots from the real running Shell** at these exact checkpoints. On macOS, activate the child Shell window and run `screencapture -x <evidence-path>/<name>.png` (keep original unmodified). If window capture requires a different method, keep the unaltered raw screenshots and document it. Never substitute a mockups/rendered illustration for an actual Simulator screenshot.

1. **Home, 1024×600.** Confirm `Le mie creazioni` is a visible dedicated platform destination in the Home portal row, without damaging Play/Create/Learn/Explore/My Greia positioning. Screenshot `01-home-1024.png`.
2. **Empty viewer.** Open My Creations. Check the friendly picture-first empty state, obvious back control, category icons, absence of technical paths/files. Screenshot `02-empty-library.png`. Return Home.
3. **Painting.** Open Painting, draw a genuinely recognizable colorful scene, and locate the *new green picture/share upward-arrow* action in its safe top toolbar. Screenshot `03-painting-before-share.png`.
4. **Publish.** Save/share once. Expect successful non-reader-friendly feedback; repeat without changing the picture and ensure no duplicate is created. Add a stroke, share again and expect a new snapshot. Screenshot `04-share-feedback.png`.
5. **Library after saving.** Return Home using Greia controls. Enter My Creations. Expect large pictures, not tiny filename icons. Two versions should be independently viewable. Screenshot `05-gallery-two-large-pictures.png`.
6. **Full preview.** Open a picture, verify uncropped original high-resolution details and Back behavior. Screenshot `06-full-picture.png`.
7. **Safe delete.** Tap trash. Verify a distinct cancel and confirm choice; screenshot `07-delete-confirmation.png`. Cancel and verify the picture remains. Repeat and confirm delete of **one** item; verify second saved snapshot remains after leaving/reopening the gallery. Screenshot `08-after-delete.png`.
8. **Painting → trusted picker → Painting, CANCEL path.** Reopen Painting and switch to Painting's **private gallery**. Confirm the new picture-arrow-down import action is visible and visually distinct from the upward publish action. Screenshot `09-painting-private-gallery-import.png`. Trigger it. On the Simulator's authoritative **remote web canvas**, the running Activity must remain alive while the **same universal Creations picker** replaces the Activity view. There must be no desktop file dialog, raw path, duplicate Painting-specific chooser, or filename dependence. Screenshot `10-trusted-picker-over-painting.png`. Press Back/Escape inside the picker. Painting must reappear automatically with the prior private painting/gallery state intact and no stale click reaching the canvas. Screenshot `11-picker-cancel-restored-painting.png`.
9. **Painting → trusted picker → Painting, SELECT path.** Trigger import again. Verify only compatible PNG items are shown. Open one published picture and confirm it. Painting must resume automatically and open a **new independent editable painting** derived from that snapshot. Add a visibly identifying stroke and save. Confirm the shared source remains visually unchanged in My Creations and the imported Painting project retains the edit. Screenshot `12-selected-import-new-editable.png`.
10. **Repeated modal lifecycle.** Exercise import → cancel → import → select → import → cancel. Check no stale request, duplicate modal, click-through, lost keyboard focus, pointer disappearance, phantom selection, or Activity restart. If a request is unavailable, it must fail back to Painting rather than leaving an invisible pending picker.
11. **Trusted Home during picker.** Open the picker from Painting, then use Greia's protected Home control. Home must remain above the modal and route through the normal Activity stop lifecycle. The picker/audio/request must be torn down; returning to Painting later must not resurrect the old request.
12. **Resolution checks.** Using documented Simulator viewport controls, repeat Home + gallery + **in-Activity picker** checks at **800×480** and **1366×768**. Screenshot `13-picker-800x480.png`, `14-picker-1366x768.png`. Ensure cards, back/title, select controls and protected Home never overlap or clip.
13. **Keyboard/controller semantics.** Tab cycles media tabs; arrows move visible focus/pages; Enter opens/chooses as intended; Esc/Backspace cancels/restores; no phantom deletion/selection. Record which input modes were physically exercised. If no controller is connected, do not claim controller accepted.
14. **Simulator display evidence boundary.** The remote web canvas is the Simulator's authoritative synthetic display for the modal path. Verify Activity frame uploads do not overwrite the picker while it is active and resume after dismissal. Do **not** reinterpret this as proof of native macOS foreground-window stacking or installed Legacy-X behavior.
15. **Shape Garden → persistent project.** From Painting, deliberately publish a recognizable picture that contains easy-to-identify details. Launch Shape Garden and use its picture-arrow-down import action. Confirm the **same trusted universal picker** appears; select that Painting PNG. The garden must resume automatically with the selected picture as the upper backdrop while its soil/shape-growing identity remains visible. Plant at least six shapes in visibly different positions. Screenshot `15-shape-garden-imported-backdrop.png`.
16. **Shape Garden persistence.** Leave Shape Garden normally, reopen it, and verify the imported backdrop plus durable shapes return. Transient sparkles/grow-in animation must not be serialized/replayed as project state. Add one more shape, close/reopen again, and verify it persists. Screenshot `16-shape-garden-reopened-project.png`.
17. **Shape Garden → My Creations → Painting.** Use Shape Garden's upward share action once. Re-share without changing anything and confirm no duplicate is added in-session; add/change a shape and share again, expecting a new flattened `composition` snapshot. Open My Creations and verify the flattened image has the Painting backdrop + garden shapes, without transient particles. Screenshot `17-shape-garden-flattened-composition.png`. Import that composition into Painting through Painting's existing picker, add a visible brush mark, save privately, and verify the My Creations source snapshot itself did not change. Screenshot `18-composition-reopened-in-painting.png`.
18. **Painting/Shape Garden → Teatrino backdrop.** Publish or reuse one recognizable PNG. Launch Teatrino and use its picture-import control. The same trusted picker must appear; choose the PNG. Verify it becomes the stage backdrop without replacing puppets, curtains, built-in scene controls or trusted Home. Screenshot `19-teatrino-custom-backdrop.png`.
19. **Teatrino durable show snapshot.** Record a short show using the custom backdrop, stop/save, reopen the saved show from Teatrino's story library, and verify the custom image returns. Then exit to My Creations and delete the **shared source PNG** used for the backdrop (after confirming you are deleting the intended library item). Reopen Teatrino and replay the saved show again: its private backdrop snapshot must still render. Screenshot `20-teatrino-show-after-source-delete.png`. This proves snapshot independence, not raw shared-path coupling.
20. **Teatrino failure/resource sanity.** Save two short shows using the same custom picture and confirm normal behavior/no visible duplicate-media bookkeeping. The source unit tests, not manual filesystem edits, own proof of content-addressed deduplication and rollback. Do not tamper with private storage during GUI acceptance.
21. **Create and publish a real narration WAV.** Launch Storie della Mia Voce using the disposable simulator profile. Record and save a short scene (speak clearly enough to recognize it), open its saved-story/library view, and use the new share action for that **saved private scene recording**. Re-sharing the same saved scene without changing it must not create a duplicate in-session. Screenshot `21-voice-scene-share.png`.
22. **Audio preview before choosing.** Open My Creations and select the Audio tab. The narration must appear as a large child-friendly audio card. Exercise **Play → Pause → Resume → Replay** and verify it is genuinely audible before any consumer selection. Leaving the detail/card or the gallery must stop playback. Screenshot `22-audio-preview-before-select.png`. Do not use a real child's recording.
23. **Voice Stories → Teatrino narration.** Launch Teatrino. Use its small saved-voice import control between Stories and REC. The universal picker must show only compatible WAV items with semantic role `narration`; image/text creations and unrelated audio roles must not appear. Preview the narration again in the picker, select it, and confirm Teatrino returns with the imported-narration control visibly active. Screenshot `23-teatrino-imported-narration.png`.
24. **Puppeteer to imported narration with NO microphone capture.** Press REC and move/jump puppets while the selected narration plays. Confirm microphone capture is not opened/used for this performance; imported narration is the timing/audio source. Let one show finish automatically at narration end, then record another and press STOP early. Save/replay both. The early-stop show must contain only the corresponding trimmed narration prefix, not the full original clip. Screenshot `24-teatrino-puppeteer-to-narration.png`.
25. **Saved-show independence from My Creations.** After saving a show that used imported narration, return to My Creations and deliberately delete the shared narration item. Reopen Teatrino and replay the saved show: its private WAV copy must still play and remain synchronized with the saved puppet frames. This proves snapshot independence, not raw shared-path coupling. Screenshot `25-teatrino-audio-after-source-delete.png`.
26. **Audio/microphone source switching.** Import another narration, then tap the microphone-source control before recording. The imported narration should be cleared and the ordinary microphone path selected; record a very short mic show and verify the legacy microphone flow still works. During an imported-narration performance, no live mic level/capture should compete with playback.
27. **Writing → Posta UTF-8 import.** In Writing create and save a document containing Italian/English text, whitespace/newlines and a multi-codepoint emoji such as 👩🏽‍🔬. Publish it deliberately. In My Creations confirm the bounded text preview identifies it. Launch Posta di Leo and use the large paper-arrow-down control. The picker must show only compatible `text/plain` roles (`document` / `postcard`). Pick the Writing document. Posta must replace the draft with a single-message compact form, preserve complete grapheme clusters and cap it to postcard length without splitting emoji.
28. **Posta save → share → Writing.** Save that postcard first. Open its saved-card modal and use the deliberate paper-arrow-up share control. Unsaved drafts must have no publish path. In Writing, import the `postcard` item through the same trusted picker. It must open as a **new independent private document**, not overwrite an existing Writing document.
29. **Text snapshot independence.** Delete the shared Writing source and shared postcard item from My Creations. The saved Posta card and imported Writing document must remain readable/editable because each consumer owns its own private copy.
30. **Text failure cases.** Cancel both text pickers once and try an overlong document. Source regressions own malformed UTF-8/control/digest/role cases; do not mutate private stores manually. Cancel/failure must preserve the pre-existing Posta draft / Writing document.
31. **Voice Stories → Orchestra backing track.** Publish/reuse a short saved Voice Stories narration. Launch Orchestra Animali and use the music-note/down-arrow control. The picker must show only `audio/wav` roles `narration`, `song` or `music`. Exercise audible Play/Pause/Resume in the picker **before selecting**. Select the narration; returning to Orchestra must **not autoplay** it. Screenshot `26-orchestra-backing-ready.png`.
32. **Play-along isolation.** Press Orchestra's large Play control, then rapidly tap several animal instruments and rainbow piano keys while the narration plays. The backing audio must continue uninterrupted on its reserved channel; live sounds layer over it rather than stealing/stopping it. Pause and resume the backing once from Orchestra. Screenshot `27-orchestra-playalong.png`.
33. **Picker owns preview audio.** While the backing track is playing, open the import picker again. Orchestra playback must stop before the trusted picker appears so its audio preview has sole ownership. Cancel the picker: the previously selected private backing track must remain loaded and ready, but must not resume/autoplay until the child presses Play.
34. **Backing snapshot independence.** Exit and relaunch Orchestra: the imported track must remain privately available but not autoplay. Delete the shared source WAV from My Creations, relaunch again, and verify Orchestra can still play its private backing copy. This proves snapshot independence rather than raw shared-path coupling.
35. **Concert semantics.** Let one backing track finish after playing at least one live note/instrument. Source tests own exact event validation, but manually confirm normal completion/no crash. Let another track finish with no live input: it must remain simple playback, not visually claim a concert/completion reward.

### 2a. P7 action/strategy child-play acceptance (source-reviewed batch 2)

Only after earlier source and Simulator steps succeed, exercise these **real Activity entrypoints** in the same disposable Simulator child profile. Keep raw Shell screenshots at **1024×600 and 800×480**, and include a wide 1366×768 example for at least two games. Do not infer responsiveness from an offscreen renderer screenshot. Check trusted Home behavior and actual child task comprehension rather than only whether a window opened.

36. **Colline Allegre** — drive D1 and D5 using on-screen throttle/brake/tilt. Actually cross a bridge/mud/hill, collect a star and experience a flip/landing. Verify wheel/terrain interaction, child-visible restart and committed best-distance score. Capture both low and high difficulty.
37. **Corsa delle Bacche** — test touchscreen-style press→drag→release with the Simulator's actual event translation, plus keyboard directions, across early and late authored levels. Verify no movement after release or after focusing trusted chrome, all berries genuinely reachable, rainbow/star/critter collision semantics and gentle recovery from zero hearts. Capture one late-tier action frame.
38. **Labirinto Magico** — launch all **six** actual difficulty sizes D1–D6. For a large-tier generated maze, verify passage widths, player marker and directional/path choices remain visually distinguishable at 800×480; collect a star, solve/finish and verify final overlay/replay without blocked input.
39. **Quattro Amici** — play an entire two-player game including win and restart, then test CPU tiers 1, 2 and 4 with a near-win/block situation. Verify a protected Home-region pointer cannot move the selector/drop a token, and assess CPU think-time latency on the desktop as a *non-hardware* observation.
40. **Torre Forme** — run free-build matching with a snap effect, slow-fall placement, and tower challenge with a line clear and celebration. It must execute `main.py` in the normal **script** context; no `attempted relative import with no known parent package` traceback may occur after normal gameplay. Verify shape shelf, rotation, replay and input at 800×480.
41. **Viaggio Delfino (withheld from draft)** — complete a chapter, listen to an animal fact, resize the running Simulator child surface, steer and continue. The same frame after resize must use the rebuilt canvas (no frozen/scaled-old viewport). Compare nature/discovery learning against Dragon rather than treating similar sea/sky movement as sufficient distinction.
42. **Volo Draghetto (withheld from draft)** — test stars, turbo/rainbow, bounce and accessory cycling, with keyboard and pointer. Verify it remains honestly **endless** and does not fabricate a terminal `flight.completed` reward. Evaluate whether there is enough choice/challenge to merit a separate release candidate rather than just another endless motor game.
43. **Draft release staging on disposable output only** — read `build/first-party-release-activities.toml` and confirm `status = "draft"`, exactly 22 sorted candidate IDs and no Delfino/Dragon/Orca/Alphabet/Bosco/Monster. Run only the safe **unprivileged test harness** from §1; do not change policy to approved, invoke privileged image build, or install anything. Inspect staged-selection test logs to confirm expected source directory and installed-index identities match.

These checks add to, not replace, the earlier Creations PNG/WAV/UTF-8 and adaptive-capacity acceptance. If the first failure happens before this section, **STOP** and preserve it; do not skip earlier failing tests to reach gameplay.

Record frame-rate/idle CPU/RSS observations if the Simulator exposes them; no claim about Acer performance can follow from desktop observation.


### 2aa. P7 early learning, nature and care child-play acceptance (source-reviewed batch 3)

Following §2a, capture **real Simulator shell windows** at **1024×600 and 800×480** for every newly drafted candidate; include **1366×768** for Momo and at least one counting game. Keep a comparison video/observation log where moving feedback cannot be judged from a still. No release approval without real sound and child-comprehension review.

44. **Acquario Magico:** launch via normal supervisor script, verify a first presentable frame, then actually click aquarium tools, fish, chest, glow toggle and feed. The event loop must drain queued mouse/key input rather than animate forever without accepting it. Actual eaten food, not food placement, triggers `aquarium.fish_fed`; day/night toggle triggers its event. Test saved fish population after restart and trusted chrome exclusion. Inspect max fish count and low-end per-frame particle/asset costs.
45. **Baia delle Orche (withheld):** discover all six spoken marine facts and play the orca cuddle/breach/food/music paths, including real food consumption. Compare its learning content, visuals, motion, audio and play difference against Aquarium and the already withheld Dolphin before deciding if three marine games are justified. Check pointer exclusion over Home and long-song audio behavior.
46. **Clinica Cuccioli:** five full patients, deliberately choose a wrong tool and recover, explicitly select the correct care tool before use; no automatic treatment on patient taps. Verify actual teaching cues before any English/Italian textual label, restart and star persistence.
47. **Cucciolo Mio:** feed, bath, dress, sleep, and play through queued mouse down/move/up; confirm ball drag works with injected events when global mouse position is stale, no click fires on ball release and no persistent drag after window focus loss. Verify `pet.played` is accepted by the manifest and a saved pet reopens intact. Inspect pointer controls at 800×480.
48. **Faccine Momo:** each of six emotions, sad comfort, mode switch, wrong quiz and successful quiz; verify only *newly discovered* emotions emit milestones, and all-explored only once, not each tap. Check spoken Italian/English, Home protected-region rejection, correct contain letterboxing at 800×480/1366×768, and 30Hz redraw footprint.
49. **Il Giardino dei Numeri:** child aged 2–4 should be able to tap a target, hear one counted number, retry a repeated target harmlessly and watch the basket celebration. Verify progression D1–D3 and reopening saved counts, including optional `audio.basic` absent.
50. **Luci di Momo:** complete each of five rounds at D1 and D4, including wrong choice, hint and Replay; verify bounded adaptive progression and once-only completion when replaying/restarting. Confirm spoken quantity and reveal timing remain intelligible with slower frame delivery.

The release roster is **22 draft-only source candidates**, and **Baia/Viaggio Delfino/Volo Draghetto/Alfabeto/Bosco/Monster are currently withheld**, not rejected or uninstalled from developer source. Keep all three comparisons open until actual child-facing evidence is available.


### 2ab. P7 literacy, measurement, numeracy and monster creator (source-reviewed batch 4)

Run **after** all prior source checks and GUI cases succeed on the same disposable Simulator child profile. Capture real **1024×600 and 800×480** Shell screenshots for all four new draft candidates and the three withheld comparison cases. Save raw video or annotated observations where a screenshot cannot prove spoken cue timing or result/interaction state.

51. **Alfabeto di Leo (withheld):** run both Explore and three-choice Guess; discover a fresh letter, revisit it, finish all 26, then exit/relaunch. Verify no duplicate `letter.discovered`, no second `alphabet.parade_completed`, no phantom event from restored progress. The manifest must not advertise nonexistent D1–D3 adaptation. Assess whether a non-reading 2–4-year-old learns anything beyond random card flipping; listen for literal Italian and English pronunciation accuracy.
52. **Bosco Numeri (withheld):** exercise counting 1–10 and a complete three-choice numeral quiz, including wrong/touch repeats and saved state. Directly compare child learning against the Giardino 1–5 and Luci Momo visual-quantity loops; do not advance to draft on surface/theme differences.
53. **Bottega delle Misure:** complete at least one actual success **and failure** at each D1–D5: compare, order, measure with non-standard units, shelf fit and mixed. Check relative size is visually honest (not misleading perspective), live spoken instructions, tap targets and 800×480 label/line visibility; verify exact milestone/completion count and saved adaptive level.
54. **Casa del Dieci:** complete 5-mode room composition, missing part, addition, subtraction and mixed across D1–D5. For wrong room combinations ensure failure feedback is gentle and restart valid; keyboard focus and real pointer toggles must agree with displayed room occupancy. Record locale audio comprehension for 5–7-year-olds.
55. **Festa delle Rime:** complete a rhyme-match, odd-one-out and alliteration round, then full progression at D1 and D4. Listen to **both locales** and confirm spoken item names rather than only caption/emoji shape make answers possible; ensure no wrong choice accidentally rhymes or alliterates correctly. Verify queued speech stops/replaces cleanly on new rounds, success and Home.
56. **Foresta delle Parole:** normal supervisor **direct-script** launch, word prompt, repeated target catches, wrong-orb wobble, genuine three-match word completion, then relaunch and check saved score. Listen to English/Italian phonics corpus; note that locale-specific `word.*` keys differ intentionally and are not a translation-parity defect. Verify voice cue and click hitbox scaling at 800×480.
57. **Morbidi Mostriciattoli (withheld):** create, name and save a monster; reopen gallery and verify persistence. Inject a benign failing storage fixture in the provider-free test only: attempted save/delete must leave existing editor/gallery unchanged, show no success and publish no event. Confirm `monster.portrait_created` reaches the real declared platform event path on committed saves with no child name in payload and no unsupported `session_id` keyword. Trusted Home-zone click must not terminate the Activity itself. **A reusable image/png creation is still missing**: keep withheld until actual export/picker→Painting/Theatre round trips are implemented and accepted.

The definitive candidate policy remains **draft-only: 22 source candidates, six withheld (Alphabet, Bosco, Monster, Orca, Dolphin, Dragon)**. Keep raw evidence; do not approve by converting the roster's status flag or running a privileged release build.

### 2b. SOURCE-WIP modal / transaction / P4 persistence cases carried over

The new code introduces **`tests/test_creation_selection.py`**, additional `tests/test_creation_broker.py` socket cases, enhanced `tests/test_creation_gallery.py` role filtering and `tests/test_painting_creations.py` independent PNG import tests. All are included in the `test_creation_*.py`/Painting commands at §1. In the report verify individually:

- the broker **rejects** `request_selection` until a trusted presenter is installed, and a test-only trusted activation enables a request;
- forbidden format/semantic role/empty consumer request/duplicate request/forged request ID are rejected;
- a real Unix socket returns a pending request, trusted selection completes it, the same Activity receives a single-use handle and imports exactly once;
- cancellation, expired/uncollected result, backend loss, Activity STOP/broker cleanup and a second Activity/sibling session cannot claim another session's choice;
- Gallery pre-reader cards are filtered by both MIME and role; wrong-media gallery items never appear;
- Painting's selected-image import creates a **new private editable** project, preserves current work on integrity/decoding failure, suppresses duplicate pending requests and polls the broker at a bounded cadence;
- Legacy-X modal tests prove exact-object lease ownership, show-time `_NET_WM_PID` revalidation and restoration of a recreated Activity window without leaking X11 IDs into the generic lease;
- trusted system chrome can restack on the same Activity lease above the picker;
- Simulator tests prove exact-session modal ownership, ordinary input diversion to Shell, protected Home priority and suppression of Activity frame overwrite;
- picker-host tests prove real trusted completion callback, cancel/restore, show/chrome failure, terminal Activity handling, abnormal shutdown cancellation + presenter revocation, and first picker-frame preparation before Shell raise;
- shared PNG tests reject payload/source-dimension abuse before expensive conversion;
- Shape Garden tests prove bounded durable shape serialization, transient-state exclusion, content-addressed backdrop integrity/rollback, bounded picker polling and explicit flattened publication deduplication;
- Teatrino tests prove PNG integrity-before-mutation, nonblocking cancel/select, content-addressed backdrop deduplication across shows, last-reference cleanup, show-cap reclamation, strict catalogue reads, failed-commit rollback and no false creation event on save failure.
- Voice Stories tests prove only durable private scene WAVs are publishable, failed story commits remain retryable, and share taps are bounded/deduplicated;
- imported-narration tests prove canonical WAV/duration bounds, early-stop trimming, `audio/wav` + `narration` picker scope, cancellation preservation, no microphone start while imported narration drives the show, and unchanged microphone behavior when no narration is selected;
- Writing tests prove saved-private-file publication, `document` + `postcard` picker scope, strict UTF-8/digest/role checks, independent private document import, unchanged-publication deduplication and rollback when a new-document index commit fails;
- Posta tests prove authoritative saved-card UTF-8 files, failed-index rollback/reclaim order, path-safe legacy IDs, grapheme-safe imported replacement, import failure preservation, saved-only `postcard` publication and deduplication;
- Orchestra tests prove content-addressed private backing storage, failed-pointer rollback, WAV/role/digest validation, picker audio isolation, reserved mixer channel 0 Play/Pause/Resume, persistence-before-active-state mutation, and `concert.performed` only after real live accompaniment; its manifest regression locks the corrected free-play pedagogy and declared `instrument.played` event.
- Activity-event default idempotency tests prove repeated equivalent facts with omitted keys receive independent unique IDs, while explicit retry keys remain unchanged; do not allow recycled Python object addresses to suppress feeding/emotion/progression facts;
- action-pointer tests prove Corsa explicitly recognizes event-queued press→drag→release/focus loss even if global mouse state changed, Quattro cannot hover/drop in protected chrome, and Delfino switches its render path to the new canvas in the same resize frame;
- Torre direct-script regression exercises snap and cleared-particle effects in the production import context, not merely a package import at boot; Dragon manifest test locks the actual endless milestone-only event set;
- release staging tests prove the **22-candidate draft** stages only the reviewed subset, remains refuse-to-release until explicitly approved, and does not install the withheld Orca/Dolphin/Dragon just because they exist in source;
- batch-4 monster save/delete tests prove that a failed durable write never mutates the visible gallery, loses the editor, or emits a creation event; an accepted portrait event must contain a private-safe payload and the correct stable idempotency key, and Activity child clicks cannot impersonate platform Home;
- batch-4 Alphabet tests prove exploration/quiz emit only genuine fresh discoveries and never re-award a full parade after restoration; the old fictional adaptive difficulty claim is absent from its manifest;
- shared-capacity tests prove the owner’s 8 GiB writable-volume example: at 2 GiB used the global policy permits at most 4 GiB additional persistent growth before 6 GiB used; the shipped 25% private-namespace fraction yields a 2 GiB per-Activity containment ceiling on that same writable volume while the 16 MiB single-file bound remains independent;
- `VolumeBudget.write_reservation()` is shared across private Activity storage, My Creations and history in launcher composition; deterministic concurrency coverage must prove the second writer observes the first writer's changed usage rather than both passing one stale capacity observation;
- at the 75% occupancy ceiling, same-size/non-growing repair writes to existing private state remain possible when physically free staging room exists, while a new private file, a new history session and a storage-migration working copy are denied;
- migration-copy and atomic-replacement tests must verify **peak temporary bytes** separately from final persistent growth; do not weaken the 512 MiB floor to make staging pass.

Do not bypass the real presenter gate, inject raw shared paths, or create a dummy Activity-local picker. The implemented backend semantics are documented in
`docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P3_TRUSTED_PICKER_DISPLAY_CONTRACT.md`.

**Further deferred:** sibling-profile isolation in live sessions, backup/restore, **real-device writable-volume calibration** (read-only measurement only in this desktop run; do not intentionally fill or stress a real disk), Wayland/KMSDRM modal backends, and installed Acer/Pi interaction/performance only after the independent lifecycle/first-boot route permits it. Avoid unreviewed hardware flashing now.

### 3. Report and evidence

Provide exactly:
- tested HEAD and dirty state;
- every source command, exit code, relevant summary and first failure;
- whether the Simulator ran, screenshot filenames and what was visually inspected;
- whether Paint→My Creations saved original PNG snapshots, deduplicated unchanged images, and the **Painting→trusted picker→new editable Painting** cancel/select/reopen paths behaved correctly;
- whether **Painting→Shape Garden→flattened My Creations→Painting** persisted correctly and kept independent snapshots;
- whether **Painting/Shape Garden→Teatrino** saved-show backdrop survived deletion of the shared source PNG;
- whether **Voice Stories→audio preview→Teatrino narration** worked without microphone contention, including early-stop trimming and saved-show replay after deletion of the shared source WAV;
- whether **Writing→Posta→Writing UTF-8** worked through the trusted picker, including grapheme-safe postcard compaction, saved-only Posta sharing and continued access after shared-source deletion;
- whether **Voice Stories→Orchestra** provided audible preview-before-select, no autoplay after import/relaunch, uninterrupted live accompaniment, explicit pause/resume, picker-preview isolation and playback after deletion of the shared source WAV;
- whether P7 action/strategy, early-learning and literacy/measurement/creation batches passed true script launch, model/events, child comprehension, authored difficulty progression, touch/keyboard controls, protected chrome, terminal/replay handling and 800×480 readability, with all three marine-game comparisons and Dragon differentiation noted rather than silently approved;
- whether exactly 22 **draft-only** Activities staged and official release still refused unapproved policy;
- whether `test_profile_volume_budget.py` and the full suite proved shared reservation serialization, 8 GiB→2 GiB adaptive Activity quota, 75% aggregate ceiling, non-growing recovery writes, history growth denial and migration working-copy denial;
- the **actual local writable filesystem facts** used for calibration (`df -B1`/platform-equivalent for the profile-data mount if available), recorded read-only; do not create giant filler files or intentionally approach the machine's capacity limit;
- image detail/deletion/cancel state; actual observed bug(s), with steps;
- accepted screen sizes/input modes; limitations;
- any audio/TTS/microphone output not tested;
- clear evidence classification **SOURCE**, **SIMULATOR**, **PHYSICAL NOT TESTED**.

Return a ZIP of the raw screenshots + logs + concise Markdown report from the `tmp` evidence directory. No source commits unless the owner explicitly authorizes a fix tranche. **Do not** flash/install/reboot any device or call this release/Acer acceptance.

### Stop conditions

STOP on pre-existing uncommitted source state, mismatched source SHA ancestry, source changes beyond candidate not yet reviewed, first focused or full verify failure, missing unavailable dependencies not safely bootstrappable, profile selection/data isolation ambiguity, real child data exposure, unrecoverable simulator failure, or a GUI crash. Preserve files/logs exactly for root cause; no false PASS by skipping failing gates.

**Expected handoff:** this accumulated run either validates the current P1–P7 source candidate (shared/adaptive capacity + trusted modal + PNG/WAV/UTF-8 round trips) or stops at the first reproducible defect with raw evidence. After repairs, proceed to P6 release curation and P7 Activity quality review rather than creating another picker or storage policy.
