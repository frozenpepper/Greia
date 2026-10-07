# Creations Library P3 — Desktop Source + Real GUI Acceptance

**Scope:** non-destructive desktop **SOURCE and SIMULATOR** evidence for the 2026-10-07 Creations work, not hardware acceptance.  
**Pinned source candidate:** `d63b9f530e684819e80e9e5a271c13bd953cc001` (last code/test source commit before documentation-only updates).  
**Authority:** `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md` and sibling `PROGRESS.md`.  
**Expected state:** P3 Gallery + Painting publish source exists but is **not yet accepted**; in-Activity consumer picker, audio producer, cross-app import, release selection and hardware tests remain **not implemented**.

## Instructions for one local desktop agent

Work in the authorized existing Greia macOS checkout. This is **not** an installer/flash/rebuild/Acer task.

### 0. Safety and exact checkout identity

1. Do not modify, delete, chmod or clean unrelated project data; do not flash, repartition, run a privileged Greia release builder, reboot the Acer or touch physical media. No production child profiles or actual children's pictures/recordings in this test.
2. `cd` to the existing local clone and record `pwd`.
3. `git status --short`; if there are modifications not explicitly authorized for this test, **STOP** and report filenames/HEAD. Do not stash, reset or silently discard changes.
4. `git fetch origin main` and `git switch main && git merge --ff-only origin/main`. If ff-only fails, STOP; do not merge/rebase/reset.
5. `git rev-parse HEAD`, `git merge-base --is-ancestor d63b9f530e684819e80e9e5a271c13bd953cc001 HEAD` (exit **0** required). Check `git diff --name-only d63b9f530e684819e80e9e5a271c13bd953cc001 HEAD -- src activities runtime tests build`. It should be empty for this pinned code candidate; if not, STOP and report new source changed by other work.

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
8. **Resolution checks.** Using documented Simulator viewport controls, repeat Home + gallery checks at **800×480** and **1366×768**. Screenshot `09-gallery-800x480.png`, `10-gallery-1366x768.png`. Ensure gallery cards, back, title and delete confirmation never overlap protected navigation or get clipped.
9. **Keyboard/controller semantics.** Tab cycles media tabs; arrows move visible focus/pages; Enter opens item; Esc/Backspace returns; no phantom deletion on single key; size/selection follow real Greia input mapping. Record findings. If controller isn't physically present, do not claim controller accepted.
10. **Audio/text:** The gallery source includes playable WAV preview and text descriptions, but voice/text Activities do **not yet publish** into the shared library. **Do not** inject media into a production child's profile, mount shared folders or edit private SQLite files to fake this test. Audio/ordinary text gallery visual acceptance remains **PENDING** until a source-approved disposable fixture producer or a genuine integrated producer exists. Unit tests may prove pure behavior only.

Record frame-rate/idle CPU/RSS observations if the Simulator exposes them; no claim about Acer performance can follow from desktop observation.

### 3. Report and evidence

Provide exactly:
- tested HEAD and dirty state;
- every source command, exit code, relevant summary and first failure;
- whether the Simulator ran, screenshot filenames and what was visually inspected;
- whether Paint→My Creations saved original PNG snapshots, deduplicated unchanged images and survived reopening;
- image detail/deletion/cancel state; actual observed bug(s), with steps;
- accepted screen sizes/input modes; limitations;
- any audio/TTS/microphone output not tested;
- clear evidence classification **SOURCE**, **SIMULATOR**, **PHYSICAL NOT TESTED**.

Return a ZIP of the raw screenshots + logs + concise Markdown report from the `tmp` evidence directory. No source commits unless the owner explicitly authorizes a fix tranche. **Do not** flash/install/reboot any device or call this release/Acer acceptance.

### Stop conditions

STOP on pre-existing uncommitted source state, mismatched source SHA ancestry, source changes beyond candidate not yet reviewed, first focused or full verify failure, missing unavailable dependencies not safely bootstrappable, profile selection/data isolation ambiguity, real child data exposure, unrecoverable simulator failure, or a GUI crash. Preserve files/logs exactly for root cause; no false PASS by skipping failing gates.

**Expected handoff:** the first screenshot/transport run identifies concrete integration defects so the next coding session can repair the real owners, then finish the in-Activity trusted picker mediation and Painting↔Shape Garden↔Theatre import work.
