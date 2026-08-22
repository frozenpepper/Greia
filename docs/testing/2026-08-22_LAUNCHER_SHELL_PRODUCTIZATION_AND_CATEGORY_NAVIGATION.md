# 2026-08-22 — Launcher Shell Productization and Category Navigation

## Goal

Now that launcher titles and icon identity are in much better shape, the next tranche is to productize the **launcher shell itself** so it feels less like a sparse technical grid and more like a polished child-facing front page.

This is a **launcher-level UX and presentation pass**, not a rework of Activity internals.

---

## Deliverable

Implement, verify, and owner-package a complete launcher-shell refinement pass covering:

1. **category navigation clarity**;
2. **page / overflow / scrolling affordance clarity**;
3. **card-grid density and spatial efficiency**;
4. **selection / hover / launch-state clarity**;
5. **visual hierarchy of header, categories, and card field**;
6. **responsive behavior across supported launcher viewports**.

Then provide a tightly curated review bundle and push the work to `origin/main`.

---

## Product intent

The launcher should now communicate, at a glance:

- where the child is (`Crea`, `Scopri`, `Gioca`, etc.);
- what category/filter is active;
- whether more Activities exist off-screen or on another page;
- which tile is selected/focused/hovered;
- when an Activity is actually launching;
- how to go back from a category-filtered view to the broader catalogue.

The shell should feel gentle, clear, and toy-like, not sparse or ambiguous.

---

## Required implementation scope

### A. Category navigation productization

Refine category navigation so it is unmistakably readable and child-safe.

Requirements:

- Present category controls as a coherent first-class launcher navigation system, not as an afterthought.
- The active category must be visually obvious.
- There must be a clear and discoverable path back to the unfiltered/all-Activities view.
- Category controls must remain clear under keyboard navigation as well as pointer interaction.
- Category labels must remain readable at supported launcher sizes.
- Category controls must not intrude into protected platform chrome/safe areas.

If useful, improve category chips/tabs/pills/icons/counts, but keep the implementation within Greia's current visual language.

### B. Overflow / pagination / scroll affordance clarity

The user must be able to tell when more Activities exist beyond the visible page.

Requirements:

- Provide clear overflow affordances when the presented category contains more Activities than the current page/window shows.
- If scrolling/paging already exists internally, the child-facing UI must now communicate it clearly.
- The current page/window position should be perceptible.
- The launcher must remain usable via keyboard and pointer.
- Any new affordances must remain compatible with 1024x600 and larger responsive cases.

Examples of acceptable approaches include page dots, soft edge indicators, clearer arrows, page counters, or another equally clean child-facing treatment.

### C. Grid density and spatial efficiency

The launcher still wastes meaningful space.

Requirements:

- Improve the balance between whitespace, card size, and information density.
- Keep cards roomy and child-friendly, but reduce needless dead space.
- Preserve the newly improved two-line title readability and unique-icon presentation.
- Do **not** regress icon contain-fit safety, title wrapping, or disclosure behavior.
- Do **not** create overcrowding or tiny text.

You may modestly rebalance card dimensions, margins, spacing, and the content field so the launcher uses its available area more intelligently.

### D. Selection / hover / launch-state clarity

Launcher interactions should feel more alive and less ambiguous.

Requirements:

- Hover state must be visually distinct but restrained.
- Keyboard-selected/focused state must be unmistakable.
- Launching state must be evident and feel intentional, not like a frozen tile.
- If the launcher already has motion for launch/hover, refine and evidence it rather than replacing it gratuitously.
- Do not create distracting or excessive animation.

### E. Preserve previous accepted contracts

The following are now baseline contracts and must remain intact:

- two-line Activity titles;
- 48-grapheme defensive display cap;
- full-title disclosure on hover/selection;
- bounded caches;
- contain-fit icon rendering with safe padding;
- fail-soft icon fallback;
- unique package-owned first-party icons.

Regression against any of these is unacceptable.

---

## Documentation / skill updates

Update the living docs that should reflect launcher-shell behavior and expectations, as appropriate.

At minimum review and update whichever of these are relevant:

- `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`
- `HANDOVER.md`
- launcher/UI design docs if they now describe stale shell behavior

Only update what truly needs updating; keep docs coherent rather than noisy.

---

## Verification requirements

Run and report the exact outcomes of all relevant verification steps.

At minimum include:

- launcher/UI tests relevant to the new work;
- `make validate`;
- `make visual-assets-check` if still relevant to the affected assets;
- any focused new test module(s) you add for launcher shell contracts.

If you add tests, they should check actual behavior/contracts, not superficial implementation trivia.

---

## Required owner review bundle

Create a curated review directory under:

`docs/reviews/visual/2026-08-22_launcher-shell-productization/`

Include a compact, high-signal evidence set. Capture through the real simulator/launcher path, not mockups.

Required curated PNGs:

1. `01-before-baseline.png`
   - representative before state showing the weaker shell presentation.
2. `02-after-main-shell-1024x600.png`
   - main improved launcher shell at 1024x600.
3. `03-category-navigation.png`
   - clearly proving active category treatment and return-to-all behavior.
4. `04-overflow-or-pagination-proof.png`
   - clearly proving that the child can perceive additional off-screen/off-page Activities.
5. `05-selection-and-hover-proof.png`
   - clearly showing hover and selected/focused state.
6. `06-launching-state-proof.png`
   - proving the launching-state treatment.
7. `07-responsive-large-1024x600.png`
8. `08-responsive-compact-1366x768.png`
9. `09-responsive-normal-1280x800.png`
10. `10-title-and-icon-regression-proof.png`
    - proving the previously accepted title/icon contract remains intact.
11. `11-keyboard-navigation-proof.png`
    - proving the shell remains clear without pointer interaction.
12. `12-fail-soft-or-edge-case-proof.png`
    - one meaningful edge-case/fail-soft capture relevant to the shell work.

Also include:

- `OWNER_RECHECK.md`
- `runtime-audit.json`
- `simulator-trace.json`

If additional artifacts are genuinely useful, keep them few and high-signal.

---

## Transfer ZIP

Package the review material into a single root-level ZIP named exactly:

`GREIA_VISUAL_REVIEW_LAUNCHER_SHELL_PRODUCTIZATION_2026-08-22.zip`

Keep it clean and owner-facing.

---

## Return format

When done, report back with:

1. concise completed-work summary;
2. exact verification results;
3. exact review directory path;
4. exact ZIP filename/path;
5. exact commit SHA pushed to `origin/main`.

Do **not** paste huge implementation dumps.
