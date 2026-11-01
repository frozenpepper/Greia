# Greia licensing notice

Greia does not use one license for everything. Software, documentation,
reusable media and project marks have different terms. The full policy, and
the reasoning behind it, is in
[docs/governance/LICENSING_AND_TRADEMARK.md](docs/governance/LICENSING_AND_TRADEMARK.md)
(ADR 0024).

A file or directory with its own license or provenance notice follows that notice.
Where a media asset does not specify a reuse license, do not assume it is covered
by the platform's source-code license.

## Default terms

| Material | License |
|---|---|
| Greia-owned platform, application and tooling source code | [Mozilla Public License 2.0](LICENSE) |
| Greia-owned documentation and contributor/agent guides | [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/) |
| Greia-owned reusable artwork, icons and audio | CC BY 4.0 only where expressly indicated in the applicable asset notice |
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
