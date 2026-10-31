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
| Nunito Sans typeface (static instances of the upstream variable font) | `assets/fonts/nunito-sans/` | SIL Open Font License 1.1 | License text is beside each copy (`OFL.txt`); derivation is recorded in `build/trust/nunito-sans-2.3.2.provenance`. |
| Debian archive signing keyring | `build/trust/debian-archive-keyring-2025.1.gpg` | Debian's terms | Used to verify packages during image builds; provenance in the matching `.provenance` file. |

Built Greia OS images also contain Linux and many Debian packages under their
own licenses. The Greia license does not relicense them; image releases must
carry the corresponding notices and source offers.

## Media provenance still under review

These items need an explicit decision before they can be redistributed under
an open license:

- **Historical macOS System Voice recordings — removed from current tree, history unresolved.** An inventory dated 2026-10-28 identified 627 WAV files generated via the macOS `say` command and 627 associated receipts, including 60 shared files. On 2026-10-31 these 1,254 tracked files were removed from the current `main` tree. The full [inventory](docs/release/2026-10-28_MACOS_SYSTEM_VOICE_AUDIO_INVENTORY.md) remains for provenance and remediation. **This does not retract public Git-history copies or previously published installer images.** Do not distribute old Git revisions or images containing these files without an applicable separate rights grant or legal review. Missing speech must be replaced using redistributable sources and newly accepted recordings; audio-quality acceptance is not a redistribution license. See [Apple's macOS software license](https://www.apple.com/legal/sla/docs/macOSTahoe.pdf), §2.F, for the reported restriction. No conclusion is made here about every generating-system license version.

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
  **Generation-stack rights:** OpenBMB VoxCPM2 code and weights are released
  under Apache-2.0; Resemble AI Chatterbox is released under MIT. Neither
  imposes Apple's System Voices restriction. The project-owned v0.3 design
  masters are recorded as owner-selected synthetic output; the v0.1 masters
  remain a project-owner-supplied asset whose CC BY 4.0 publication still
  needs the owner's explicit asset-licence confirmation.
- **Generated artwork.** Vector art in `assets/` and `activities/` was authored
  for the project, much of it with AI assistance, and is intended for CC BY 4.0.
  Provenance is recorded per pack in the asset READMEs and catalogues.
