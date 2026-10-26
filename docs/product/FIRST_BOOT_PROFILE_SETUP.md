# First-boot profile setup (voiced "What's your name?" wizard)

**Status:** accepted owner request (2026-10-17); SOURCE implemented, voice lines
requested (not recorded), UNPROVEN on VM/physical hardware.
**Owner request:** "introduce at first launch some kind of new user creation
wizard (very basic: 'What is your name' etc.) with voices guiding the
kids/parents through first user creation at first boot."
**Architecture:** ADR 0012 §15.1 amendment (2026-10-17), ADR 0018 Screen
vocabulary, ADR 0037 shared control kit, ADR 0020 input profiles.
**Voice script:** [`VOICE_LINES_FIRST_BOOT_WIZARD.md`](../plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/VOICE_LINES_FIRST_BOOT_WIZARD.md).

## 1. When it appears

- Only on a device that has **no real child profile yet**. Technically: the
  profile registry contains exactly the placeholder that the platform creates
  on an empty registry (`ProfileStore.ensure_initialized`), still carrying the
  `first_profile_setup` marker. The Shell and the Parent service both create
  that placeholder at boot, so "zero profiles" is represented by it.
- It appears once. Every later boot shows the ordinary profile picker
  (AGENTS.md contract 16 / ADR 0012 §15.1).
- If a Parent creates, renames or deletes a child (Parent panel or Parent
  API) before setup finishes, setup ends and the picker appears.
- Existing devices that already have profiles never see it (no marker).
- It is **not** reachable from the profile picker. Adding more children stays
  Parent-gated (Parent panel "Add child" / Parent API), unchanged.

## 2. Steps (very basic, word-light, voiced by Leo)

| Step | What the child/parent sees | Voice cue |
|---|---|---|
| Welcome | Leo waving, "HELLO!", one big Go button, a small grown-up hint (more children can be added later in Parent settings) | `first_boot.welcome` |
| Name | "WHAT'S YOUR NAME?", the name shown large, an A–Z on-screen letter grid (+ the language's accented letters: IT À È É Ì Ò Ù, ES Á É Í Ñ Ó Ú, FR É È Ë Ï Ç Ô), Space and Delete; the physical keyboard types too | `first_boot.ask_name`; Next with no name: `first_boot.name_empty` |
| Picture | the profile avatars from `runtime/profile-defaults.toml` as big tiles | `first_boot.ask_avatar` |
| Age (optional) | big numbers 3–10 and Skip; Next without a number also skips | `first_boot.ask_age` |
| Check | Leo pointing at the chosen picture and name (age badge if set); Back or the big tick | `first_boot.check` |
| Celebrate | Leo cheering, twinkling stars, then Home with the new profile active | `first_boot.celebrate` |

A rare save failure keeps the Check step and plays `first_boot.try_again`.
An ear/speaker button (top right, every step) replays Leo's line.

## 3. Rules

- **Language:** the device language (installer choice until a parent changes
  it); explicit launch context (`GREIA_PROFILE_LOCALE`/`GREIA_DEVICE_LOCALE`)
  wins. The existing reviewed copy covers EN/IT/ES/FR. New offered languages
  provide wizard strings and optional on-screen extra letters in their
  per-language `src/greia_platform/languages/<locale>/ui.json`
  `first_profile` section (see the add-language guide). Missing optional
  entries fall back through the resolver to the baseline/English; such
  fallback is **not** evidence that a new wizard translation is complete.
- **Speech:** prerecorded Leo clips at
  `assets/audio/system/first-boot/<locale>/<cue>.wav`, played on the Shell's
  single spoken-label channel. Missing clip: locale → base → English → silence,
  never an error. No TTS on the device.
- **Text:** headings follow the child capital-letter policy; IT/ES/FR lines do
  not gender the child (ADR 0032 neutral baseline).
- **Name:** letters (any script letter), single spaces, hyphen and apostrophe;
  no leading separator; at most `max_name_characters` (24); stored NFC; a name
  typed all in one case is stored in title case ("ANNA" → "Anna"), mixed case
  is kept. Validation is the platform `ProfilePolicy`.
- **Input:** mouse/touch first (tap a tile/key); arrows/D-pad/left stick move a
  focus ring, Enter/Space/south button activate; with no focus ring Enter means
  Next; Escape/Back goes back; Backspace deletes a letter.
- **Storage:** the profile is written only by
  `ProfileStore.complete_first_profile` (same placeholder identity and
  directories; marker cleared in the same atomic write). No parallel store, no
  Parent credential required (nothing exists yet to protect).
- **Landing:** Home with the new profile active, through the normal profile
  activation path. This is explicit creation, not a silent resume.
- **Fail-soft:** any wizard error falls back to the ordinary picker with the
  placeholder profile.
- **Performance:** one opaque static layer per step/size, cached kit controls,
  RLE art blits; redraw on input only; the celebration animates at 12 fps for
  at most ~6.5 s.

## 4. Evidence and open items

- SOURCE: `src/greia_launcher/first_profile_{copy,wizard,screen,presentation}.py`,
  `src/greia_platform/profiles.py` (`first_profile_setup`,
  `complete_first_profile`), `tests/test_first_profile_wizard.py` (store marker,
  model, keyboard/pointer/controller, voice fallback, 1024×600 and 800×480 ×
  EN/IT/ES/FR, real headless Shell).
- DESKTOP VISUAL REVIEW: contact sheet of every step (local review cache only).
- Open: owner text approval and recording of the 32 clips; VM and physical
  (Acer) run of a fresh install; the production Shell loop does not yet route
  SDL controller events (pre-existing, Shell-wide), so controller support is
  proven through the Shell's semantic-action path only.
