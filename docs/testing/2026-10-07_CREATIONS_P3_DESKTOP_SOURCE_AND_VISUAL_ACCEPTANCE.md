# Creations Library P3 — Desktop Source + Real GUI Acceptance

**Scope:** non-destructive desktop **SOURCE and SIMULATOR** evidence for the 2026-10-07 Creations work, not hardware acceptance.  
**Pinned source candidate:** `60832f87e2ff432ccadb1189ba1cb726cb2e1394` (latest code/test checkpoint; later documentation-only commits may follow).  
**Authority:** `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md` and sibling `PROGRESS.md`.  
**Expected state:** P3 Gallery, authenticated request/poll/cancel transport, **trusted in-Activity modal presentation**, and P4 PNG paths across Painting, Shape Garden and Teatrino exist SOURCE-WIP. Legacy-X reuses Greia's existing Shell window with exact supervised-PID revalidation before modal presentation; Simulator uses its existing remote display bridge to divert ordinary input/frames to the same real Shell picker while mandatory Home remains platform-owned. Painting imports a selected PNG as an independent editable painting. Shape Garden imports a selected PNG as a private backdrop beneath its persistent tap-to-grow shapes and explicitly publishes a flattened composition. Teatrino imports a selected PNG as a stage backdrop and persists a private content-addressed snapshot with saved shows. **None of this latest modal/cross-app slice has been accepted in a complete checkout or real GUI yet.** WAV/text producers, all-writer capacity and hardware evidence remain open.

## Instructions for one local desktop agent

Work in the authorized existing Greia macOS checkout. This is **not** an installer/flash/rebuild/Acer task.

### 0. Safety and exact checkout identity

1. Do not modify, delete, chmod or clean unrelated project data; do not flash, repartition, run a privileged Greia release builder, reboot the Acer or touch physical media. No production child profiles or actual children's pictures/recordings in this test.
2. `cd` to the existing local clone and record `pwd`.
3. `git status --short`; if there are modifications not explicitly authorized for this test, **STOP** and report filenames/HEAD. Do not stash, reset or silently discard changes.
4. `git fetch origin main` and `git switch main && git merge --ff-only origin/main`. If ff-only fails, STOP; do not merge/rebase/reset.
5. `git rev-parse HEAD`, `git merge-base --is-ancestor 60832f87e2ff432ccadb1189ba1cb726cb2e1394 HEAD` (exit **0** required). Check `git diff --name-only 60832f87e2ff432ccadb1189ba1cb726cb2e1394 HEAD -- src activities runtime tests build`. It should be empty for this pinned code candidate; if not, STOP and report new source changed by other work.

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
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_teatrino_fiabe.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_pygame_png.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_shell_window_legacy_x.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_system_chrome.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_trusted_chrome_supervisor.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_simulator_system_chrome.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_activity_index.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_supervisor.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_profiles.py' -v
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
21. **Audio/text:** the common picker has WAV preview/text support, but genuine audio/text producers are not yet integrated. Do not inject media into a real child's profile or edit SQLite to fake the workflow. Pure source tests may cover those types; real preview-before-select remains pending until an approved producer/fixture exists.

Record frame-rate/idle CPU/RSS observations if the Simulator exposes them; no claim about Acer performance can follow from desktop observation.

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

Do not bypass the real presenter gate, inject raw shared paths, or create a dummy Activity-local picker. The implemented backend semantics are documented in
`docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P3_TRUSTED_PICKER_DISPLAY_CONTRACT.md`.

**Further deferred:** genuine WAV preview-before-select, UTF-8 producers/consumers, sibling-profile isolation in live sessions, backup/restore, disk saturation at 75% plus OS headroom, Wayland/KMSDRM modal backends, and installed Acer/Pi interaction/performance only after the independent lifecycle/first-boot route permits it. Avoid unreviewed hardware flashing now.

### 3. Report and evidence

Provide exactly:
- tested HEAD and dirty state;
- every source command, exit code, relevant summary and first failure;
- whether the Simulator ran, screenshot filenames and what was visually inspected;
- whether Paint→My Creations saved original PNG snapshots, deduplicated unchanged images, and the **Painting→trusted picker→new editable Painting** cancel/select/reopen paths behaved correctly;
- whether **Painting→Shape Garden→flattened My Creations→Painting** persisted correctly and kept independent snapshots;
- whether **Painting/Shape Garden→Teatrino** saved-show backdrop survived deletion of the shared source PNG;
- image detail/deletion/cancel state; actual observed bug(s), with steps;
- accepted screen sizes/input modes; limitations;
- any audio/TTS/microphone output not tested;
- clear evidence classification **SOURCE**, **SIMULATOR**, **PHYSICAL NOT TESTED**.

Return a ZIP of the raw screenshots + logs + concise Markdown report from the `tmp` evidence directory. No source commits unless the owner explicitly authorizes a fix tranche. **Do not** flash/install/reboot any device or call this release/Acer acceptance.

### Stop conditions

STOP on pre-existing uncommitted source state, mismatched source SHA ancestry, source changes beyond candidate not yet reviewed, first focused or full verify failure, missing unavailable dependencies not safely bootstrappable, profile selection/data isolation ambiguity, real child data exposure, unrecoverable simulator failure, or a GUI crash. Preserve files/logs exactly for root cause; no false PASS by skipping failing gates.

**Expected handoff:** this accumulated run either validates the current trusted modal + Painting/Shape Garden/Teatrino PNG round trip or stops at the first reproducible defect with raw evidence. After repairs, proceed to P5 WAV/text and all-writer capacity work rather than creating another picker implementation.
