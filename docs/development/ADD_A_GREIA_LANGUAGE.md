# Add a Greia Language — Contributor and Agent Guide

**Status:** executable source/voice workflow, **NOT YET configuration-only** (audited 2026-10-26).
**Audience:** a volunteer with the full private repository, or an agent asked “Let's add a new language”.
**Authority:** `docs/product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md` and ADR 0028; exact behavior belongs to source. This guide must not be used to silently enable incomplete languages.

## Start here

1. Read `AGENTS.md`, `SETUP.md`, this guide, `skills/greia-voice-production/SKILL.md`, and `docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md`.
2. Ask for the *language tag* (for example `de` or `pt-BR`), native display name, target script, and whether this is **translation staging** or **release/selection approval**. If the owner has already supplied these, do not ask again.
3. Work in your own branch and submit a pull request; do not push directly to `main` as an external contributor. Never publish a private checkout or its fork without permission.
4. Keep system/instructional source documentation in English. Translate only actual child/parent-facing content and approved spoken scripts. Keep exact IDs, variables, markup and dynamic placeholders intact.
5. Stage the language without making it selectable. A locale only becomes a supported product language after all text, font, audio, render, runtime and installed-device checks pass and the owner authorizes promotion.

## What already works

Greia has a shared locale parser/resolver and per-Activity `activities/<activity>/locales/<locale>.json` files, with semantic text/audio IDs and English fallback. An Activity declares supported languages in its `activity.toml`. The device, profile, installer and Parent API use the one **selectable-language registry**, currently `SUPPORTED_SYSTEM_LANGUAGES` in `src/greia_platform/system_language.py`. This currently lists **en, it, es, fr**.

For an example, compare `activities/painting/locales/en.json` and `es.json`. Do not translate IDs such as `btn.undo` or audio paths. Some literacy Activities have language-specific lesson **content** separate from UI language, so translating the interface does not translate their curriculum, examples, phonemes or spoken targets.

## Reality check: not a data-only language extension today

The current repository **cannot** add a fully functional fifth selectable language by editing only config and translation files. In addition to per-Activity locale JSON and TOML manifests:

- `src/greia_platform/system_language.py` contains a Python tuple of supported languages.
- Installer text is coded in `src/greia_installer/i18n.py` and `i18n_es_fr.py`, including formatted status messages and a hardcoded accepted-language check.
- On-device Parent text has Python locale tables in `src/greia_launcher/panel_localization.py`; launcher feedback and other Shell presentation modules also contain translated Python literals.
- `tools/audit_greia_language_coverage.py` has a hardcoded four-language inventory list.
- `tests/test_four_language_release_contract.py` and other current release tests deliberately require **exactly** four languages. They must remain a truthful release contract until a new language is ready.
- The external Parents HTML app has its own source repository, `frozenpepper/Greia-Parent-App-Html` (pinned in `runtime/parent-app-client.*`). It must be checked, tested and repinned through its existing release procedure.
- Audio vocabulary, system messages, character banks, literacy lessons, images containing words, available glyphs and layout fit need actual per-language coverage; the language registry alone cannot create them.

**Engineering target (not yet implemented):** a single reviewed language catalog/config for supported/selectable locales; installer, on-device Parent/Shell and runtime locale strings in editable resource bundles; language inventory/tests derived from that catalog, with separate released-language acceptance expectations. Moving current literals into those resources is **a one-time code migration**. Afterwards new left-to-right languages with existing font and speech-model coverage should be primarily config, translation, audio and validation work. Complex scripts/RTL, grammatical/curriculum logic or unsupported speech languages can still require implementation changes. Do not claim “config-only” before this refactor and an actual fifth-language dry run.

## Stage one new language

1. Inventory every current English text owner (installer, Shell, on-device Parent, external Parents HTML, Creations, built-in Activities and encyclopedia), including dynamic messages. The source inventory is `tools/audit_greia_language_coverage.py`, **but its locale list currently needs engineering updates for new locales** and it explicitly excludes some code-owned speech/UI.
2. Add untranslated working bundles for the requested tag alongside the existing Activity locale JSON. Preserve all English keys, placeholders, audio cue IDs and ownership. Translate and review each surface; don't relabel English fallback as a translated string.
3. For locale-specific literacy, syllables, plural/agreement rules and educational vocabulary, review the *curriculum* independently from the ordinary UI.
4. Verify script, glyph coverage, text shaping, keyboard/input, directionality and layout at 1024×600 and 800×480. A non-Latin or right-to-left language is **not** enabled merely by adding a font.
5. Prepare a list of exact missing spoken cues (speaker, kind, locale, reviewed text, cue ID, destination) without overwriting accepted existing files. Voice generation and review are the separate authoring workflow below.
6. Use the simulator and Activity tests to inspect the staged texts. Test the actual installer and Parent panels, then an installed OS image/device, before the owner promotes the language.
7. Do not change the system selector, product claims or the exact-four-language acceptance tests merely to make staging appear complete.

## Voice Studio: new language

The canonical entry point is `tools/greia_voice.py` / `VoiceEngine`, not a direct VoxStage, Chatterbox, Parakeet or FFmpeg invocation. Details: `skills/greia-voice-production/SKILL.md`, `tools/greia_voice_core/README.md`, `docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md`.

- **Selected character model:** VoxCPM2 (VoxStage shared local Apple-Silicon worker, no cloud fallback); Chatterbox is an explicit alternative, not automatic.
- **Selected masters:** `assets/audio/characters/canonical/v0.3/manifest.toml`. Dani, Tito, Momo use the owner-selected v0.3 voices; Lilli, Leo, Flash retain the selected v0.2 identities and bytes. The exact reference WAV files ship in this authoring repository. Never redesign/rewrite them when extending a language.
- **Default new-generation ASR:** locally cached, pinned multilingual Parakeet-TDT v3 (`mlx-community/parakeet-tdt-0.6b-v3`; revision `ed2b7e8c15f9aaa0b5772e2efb986255eaef7e15`). Whisper Base is retained for **historical** comparison/review. Parakeet can only check languages it recognizes accurately; investigate/test its coverage for the proposed language before relying on PASS/WARN.
- **New machine caveat:** this repository does **not** include a standalone VoxStage installer/model weights, nor the local human-review Takeboard utility. Existing guides reference an external shared-tool catalog and a preprepared Mac environment. Therefore a new volunteer **cannot assume** a fresh clone is sufficient to set up this entire Studio. Obtain legitimate access to the shared tooling or build/document a supported independently reproducible install before claiming workstation setup PASS. Get explicit consent for significant model downloads/cloud spend.
- On a machine where tools and cached models are already provisioned, use the *prepared Greia voice Python* rather than a random Python environment:

```bash
voxstage start
voice_python="$HOME/Library/Application Support/Greia/voice-production/venv/bin/python"
"$voice_python" tools/greia_voice.py doctor
```

Read `doctor`'s **verifier readiness separately**; success for character synthesis does not mean Parakeet is present. An unavailable verifier is not a PASS. Use `tools/greia_voice.py generate` or `batch` with semantic `--speaker`, `--kind`, `--locale`, `--text`, `--cue-id`, staging `--output`. New output stays pending listening; machine PASS is not human acceptance. Pedagogical pronunciation uses the separate native/system route and currently requires macOS; verify that a suitable voice exists for the *new* language or treat it as blocked. Do not direct-generate into shipping asset directories.

## Source checks before proposing release

Run from the repository root, with the project's development dependencies available:

```bash
for pattern in test_system_language.py test_localization.py test_installer_localization.py test_four_language_release_contract.py test_four_language_inventory.py test_voice_parakeet_pipeline.py; do
  PYTHONPATH=src python3 -m unittest discover -s tests -p "$pattern" -v || exit 1
done
python3 tools/greia_voice.py doctor
```

These tests cover the **existing four-language baseline**, not proof of a fifth language. For the proposed locale also check every intended key, placeholder, manifest, semantic audio resolver, speech receipt, script/fonts, rendered UI, speaker identity and physical playback. Run `make verify` per `CONTRIBUTING.md` before proposing promotion; core OS image acceptance is separate.

**Report:** target tag, staging/release status, translated vs fallback count, missing/blocked text and audio, actual model/master/verifier readiness, test results and environment, human listening review, screenshot/device evidence, and exact required code changes. If any part is missing, report **not ready** instead of silently editing the registry.
