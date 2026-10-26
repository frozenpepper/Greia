# Greia Installer Experience

**Status:** SOURCE (2026-10-17 redesign; later manifest-based language chooser extension). The recorded 2026-10-17 desktop/headless visual review covered EN/IT/ES/FR only; the later paginated five-language path and physical Acer installer remain visually unaccepted.
**Scope:** what the parent sees and does in the graphical live installer. Disk eligibility, payload checks and the fail-closed transaction are owned by `src/greia_installer/` (`disk.py`, `transaction_client.py`, `transaction_service.py`) and AGENTS.md contract 14; nothing here relaxes them. Wi-Fi behaviour and carry-over: `INSTALLER_WIFI_SETUP.md`. Start-up animation: `docs/design/GREIA_BOOT_EXPERIENCE.md` § Stage D (installer).

## Journey

```text
Greia logo animation (skippable) → Language (manifest-offered locales; currently EN / IT / ES / FR)
→ Welcome → 1 Keyboard → 2 Disk → 3 Pointer → 4 Screen → 5 Wi-Fi (optional)
→ 6 Ready to install (hold to erase) → Installing → All done | Installation stopped
```

Steps 1–6 show numbered step dots above the card (done steps show a check). The language screen and Welcome have no dots.

## Look

Same product as the child Shell: the Shell meadow backdrop (`bg.meadow_day.home`), Leo (`character.leo` poses) beside a cream card, kit controls from the shared painter (ADR 0037) and `GREIA_SVG_AUTHORING_RULES.md` palette tokens. Destructive elements use a coral-shaded fill / burgundy ink. Owner: `src/greia_installer/presentation.py` (`InstallerLook`); page logic and hit-target keys stay in `main.py`.

Without the shared catalogue in the live root the meadow is painted procedurally and the owl core icon stands in for Leo; pages remain fully usable.

## Page requirements

- **Language:** 2-column grid of big tiles with drawn flags (the fonts have no flag glyphs); Continue is labelled in the highlighted language. The choices are loaded from packaged `src/greia_platform/languages/<locale>/manifest.json` files through `system_language.py`, not a fixed four-language list. More than four choices use paginated tiles; the page controls must remain reachable by pointer and keyboard at 800×480 as well as 1024×600. A translation-only folder without `manifest.json` never appears.
- **Welcome:** says Greia goes on the internal disk, lists the steps, says nothing is erased before the last step, asks to keep power connected.
- **Disk:** explains that only safe internal disks are offered; each disk shows model, size and device path; a "disk changed" rejection is shown on this page.
- **Ready to install:** the disk to erase is the largest element (model, size, path) in a warning card, followed by "Everything currently on this disk will be erased. This cannot be undone.", the keyboard and Wi-Fi summary, and the 2-second hold button with its hint.
  - **Keyboard equivalent (2026-10-17):** holding Enter or Space for the same 2 s fills the same button. Focus starts on Back and is shown only after the parent uses the keyboard on this page (the first Enter/Space just reveals it); Tab or an arrow moves it to the erase button, whose hint then reads "Hold Enter or Space for 2 seconds.". The press must be fresh on this page: a key already down (auto-repeat, or still held from the Wi-Fi page) never starts the hold. Releasing the key, pressing any other key, moving focus or leaving the page cancels; a lost key-up is caught by SDL's live keyboard state. Completing either hold only calls the same start path, which re-checks power, display and the selected disk exactly as before.
- **Installing:** progress track, the current phase name with its measured percentage when the service can measure it (bytes copied, bytes read back), total elapsed time, and "Do not remove the USB key / Do not turn off the computer". A phase that sends nothing for 20 s adds "Still working on this step m:ss" (that phase's own elapsed time), so a long silent step (e.g. checking the release files) never looks frozen. The bar never moves backwards.

## Install progress (2026-10-17)

The root transaction service streams display-only `PROGRESS` frames on the same EXECUTE connection, before its final `INSTALLED`/`ERROR` answer (owner: `src/greia_installer/install_progress.py`). A frame carries a phase id from the shared vocabulary (`check`, `partition`, `format`, `copy`, `verify`, `setup`, `bootloader`, `complete`; the UI adds `prepare`), an overall fraction, and when measurable the phase fraction and done/total bytes. The A/B path measures `copy` and `verify` by counting bytes through the `SYSTEM_A` slot store against the manifest's uncompressed size; the legacy engine reports its stage milestones. Frames are rate-limited to at most 2 Hz within a phase (phase changes pass at once), the overall fraction is monotonic, and a writer failure (UI gone or not reading) disables reporting without touching the install. The UI validates each frame (known phase, finite 0..1 fractions, bounded byte counts, at most 8,192 frames) and drops bad ones; the request still carries nonce + digest only, and no new privilege, socket or file is involved.
- **All done:** Parent login in its own card, how to change it, and "remove the USB key after the computer turns off". When hardware detection was incomplete (2026-10-21 owner decision: this never stops an install; common network firmware is installed as a fallback) a short, non-alarming localized note is added: "Some hardware could not be identified automatically. If Wi-Fi or sound do not work, check them in Greia Parents after first boot." The flag travels as display-only `hardware_detection: "incomplete"` on the `INSTALLED` answer (`ExecuteReceipt.hardware_detection_incomplete` -> `InstallResult`).
- **Installation stopped:** the reason (translated when known, sentence case) and the existing "may be incomplete if installation had already begun" note.

## Text and layout rules

- All copy goes through the installer translator (`i18n.py`, `i18n_es_fr.py` for the four existing baseline dictionaries, plus `<locale>/ui.json` for newly offered languages). Measurement uses the translated text, and paragraphs are translated before wrapping. Machine data (SSIDs, disk models, paths, credentials) is drawn verbatim. Contributors use `docs/development/ADD_A_GREIA_LANGUAGE.md` and check staged translations before publishing a manifest.
- Every label fits by measurement (shrink or ellipsis), never by a fixed width.
- Readability floors (`presentation.text_floors`): body/paragraph text at least 20 px and helper text at least 16 px at 1024x600, 17 px and 15 px at 800x480. Sizes come from `presentation.text_scale` (about 22/25 px body/control at 600 px high), and kit labels never shrink below the helper size.
- **Historical evidence:** the 2026-10-17 screenshot audit covered the then-four languages (EN/IT/ES/FR) at 1024×600 and 800×480 via `tools/installer_screenshots.py` (248 states). That does **not** establish any future locale's legibility or the new paginated chooser's rendered behavior. Each added manifest requires fresh page-navigation/text-fitting review (no overlaps, floor violations or unexpected truncation) at both sizes and ultimately release-image/device evidence.

## Performance

Static chrome is composed once per page and viewport into an opaque prepared layer (bounded cache); controls are cached kit bodies, text uses the bounded typography cache. The installer repaints only when its state signature changes; the few states that move without input (held erase button, installing, Wi-Fi scan/connect, password caret) add a coarse time bucket to the signature.
