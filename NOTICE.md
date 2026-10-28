# Greia licensing notice

Greia does not use one license for everything. Software, documentation,
reusable media and project marks have different terms. The full policy, and
the reasoning behind it, is in
[docs/governance/LICENSING_AND_TRADEMARK.md](docs/governance/LICENSING_AND_TRADEMARK.md)
(ADR 0024).

**Status: license policy selected; public-release licensing and provenance
audit pending.** Until that audit is finished, do not read this notice as a
claim that every file in the repository has already been cleared under the
default below. A file or directory with its own license or provenance notice
follows that notice.

## Default terms

| Material | License |
|---|---|
| Greia-owned platform, application and tooling source code | [Mozilla Public License 2.0](LICENSE) |
| Greia-owned documentation and contributor/agent guides | [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/) |
| Greia-owned reusable artwork, icons and audio | intended CC BY 4.0 once provenance is confirmed (see below) |
| Copyable Activity templates explicitly marked as such | Apache License 2.0, when so marked |
| Third-party code, fonts and media | their original licenses, listed below |

Independent Activities may use any license their authors choose. Using the
Greia Activity API does not by itself put an Activity under the MPL.

The Greia name and distinctive wordmarks/logos, plus any future official
approval marks, are governed by the separate [trademark guide](TRADEMARK.md)
and [full policy](docs/governance/LICENSING_AND_TRADEMARK.md). Anyone may
commercially redistribute Greia code under its applicable open-source
licenses without paying the project. Truthful identification such as
“Runs Greia OS” on a product box is allowed; official partner/certification
claims and prominent official product branding are different and may
require authorization. No registration or certification is claimed.
Distinctive identity/logo assets are excluded from the proposed CC BY 4.0
default for reusable non-brand media.

## Third-party material in this repository

| Material | Location | License | Notes |
|---|---|---|---|
| Nunito Sans typeface (static instances of the upstream variable font) | `assets/fonts/nunito-sans/`, `website/assets/fonts/` | SIL Open Font License 1.1 | License text is beside each copy (`OFL.txt`); derivation is recorded in `build/trust/nunito-sans-2.3.2.provenance`. |
| Debian archive signing keyring | `build/trust/debian-archive-keyring-2025.1.gpg` | Debian's terms | Used to verify packages during image builds; provenance in the matching `.provenance` file. |

Built Greia OS images also contain Linux and many Debian packages under their
own licenses. The Greia license does not relicense them; image releases must
carry the corresponding notices and source offers.

## Media provenance still under review

These items need an explicit decision before they can be redistributed under
an open license:

- **Recorded speech made with macOS system voices — likely public-release
  blocker.** About 1,350 committed recordings (pedagogical and system speech
  in English, Italian, Spanish and French) were produced with the macOS
  `say` command. Each recording's `.receipt.json` names the provider and
  voice. Apple's published [macOS Tahoe 26 software license, §2.F](https://www.apple.com/legal/sla/docs/macOSTahoe.pdf) permits System Voices
  for personal/non-commercial creation but expressly restricts recording,
  publishing or redistribution in public, nonprofit or commercial contexts.
  Earlier Apple macOS licenses contain substantially similar restrictions.
  **Do not publish this content as open-licensed media without an applicable
  separate authorization or competent license review of the exact generating
  system and assets.** Inventory the impacted files and their use in the
  release image; seek permission or replace them with legally redistributable
  alternatives. Owner approval of the audio's quality is distinct from
  distribution rights. Removing files from HEAD does not remove Git-history
  copies from a repository whose full history is made public.
- **Character voice references.** The cloning references under
  `assets/audio/characters/canonical/v0.1/` and the source masters under
  `assets/source/audio/character-voice-masters/v0.1/` are synthetic
  voice-design recordings. Their redistribution status is recorded as pending
  in `assets/audio/characters/canonical/v0.1/manifest.toml`. Character speech
  rendered from them with Chatterbox carries the same question. Active v0.3
  masters and references were designed locally using VoxStage/VoxCPM2; Dani,
  Momo and Tito were owner-selected on 2026-10-21, while Lilli, Leo and Flash
  retain their exact v0.2 bytes. Selection and job provenance are in
  `assets/source/audio/character-voice-masters/v0.3/provenance.json`. Owner voice
  acceptance does not by itself settle the separate public-redistribution audit.
- **Generated artwork.** Vector art in `assets/` and `activities/` was authored
  for the project, much of it with AI assistance, and is intended for CC BY 4.0.
  Provenance is recorded per pack in the asset READMEs and catalogues.
