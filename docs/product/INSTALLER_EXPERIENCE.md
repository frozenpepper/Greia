# Greia Installer Experience

**Status:** SOURCE (2026-10-17 redesign). Desktop/headless visual review only; no physical Acer evidence yet.
**Scope:** what the parent sees and does in the graphical live installer. Disk eligibility, payload checks and the fail-closed transaction are owned by `src/greia_installer/` (`disk.py`, `transaction_client.py`, `transaction_service.py`) and AGENTS.md contract 14; nothing here relaxes them. Wi-Fi behaviour and carry-over: `INSTALLER_WIFI_SETUP.md`. Start-up animation: `docs/design/GREIA_BOOT_EXPERIENCE.md` § Stage D (installer).

## Journey

```text
Greia logo animation (skippable) → Language (EN / IT / ES / FR)
→ Welcome → 1 Keyboard → 2 Disk → 3 Pointer → 4 Screen → 5 Wi-Fi (optional)
→ 6 Ready to install (hold to erase) → Installing → All done | Installation stopped
```

Steps 1–6 show numbered step dots above the card (done steps show a check). The language screen and Welcome have no dots.

## Look

Same product as the child Shell: the Shell meadow backdrop (`bg.meadow_day.home`), Leo (`character.leo` poses) beside a cream card, kit controls from the shared painter (ADR 0037) and `GREIA_SVG_AUTHORING_RULES.md` palette tokens. Destructive elements use a coral-shaded fill / burgundy ink. Owner: `src/greia_installer/presentation.py` (`InstallerLook`); page logic and hit-target keys stay in `main.py`.

Without the shared catalogue in the live root the meadow is painted procedurally and the owl core icon stands in for Leo; pages remain fully usable.

## Page requirements

- **Language:** 2-column grid of big tiles with drawn flags (the fonts have no flag glyphs); Continue is labelled in the highlighted language.
- **Welcome:** says Greia goes on the internal disk, lists the steps, says nothing is erased before the last step, asks to keep power connected.
- **Disk:** explains that only safe internal disks are offered; each disk shows model, size and device path; a "disk changed" rejection is shown on this page.
- **Ready to install:** the disk to erase is the largest element (model, size, path) in a warning card, followed by "Everything currently on this disk will be erased. This cannot be undone.", the keyboard and Wi-Fi summary, and the 2-second hold button with its hint. Keyboard-only users cannot start the erase (unchanged behaviour).
- **Installing:** progress track with a moving activity dot, current step text, elapsed time, and "Do not remove the USB key / Do not turn off the computer". The production service does not stream progress during the copy, so the bar stays at its last reported value while the dot keeps moving.
- **All done:** Parent login in its own card, how to change it, and "remove the USB key after the computer turns off".
- **Installation stopped:** the reason (translated when known, sentence case) and the existing "may be incomplete if installation had already begun" note.

## Text and layout rules

- All copy goes through the installer translator (`i18n.py`, `i18n_es_fr.py`); measurement uses the translated text, and paragraphs are translated before wrapping. Machine data (SSIDs, disk models, paths, credentials) is drawn verbatim.
- Every label fits by measurement (shrink or ellipsis), never by a fixed width.
- Reviewed at 1024x600 and 800x480 in EN/IT/ES/FR with `tools/installer_screenshots.py`, which also reports overlapping or off-screen hit targets.

## Performance

Static chrome is composed once per page and viewport into an opaque prepared layer (bounded cache); controls are cached kit bodies, text uses the bounded typography cache. The installer repaints only when its state signature changes; the few states that move without input (held erase button, installing, Wi-Fi scan/connect, password caret) add a coarse time bucket to the signature.
