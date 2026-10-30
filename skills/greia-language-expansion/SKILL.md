---
name: greia-language-expansion
description: Use when asked to translate, stage, record, promote or add an OS, Activity, installer or Parent language to Greia (manifest-based language registry, scaffold/check tools, voice and acceptance steps).
---

# Add or translate a Greia language

## When to use / Read first

Use for any request to translate, stage, record, promote or retire an installer/OS/Parent/Activity language. Read `docs/development/ADD_A_GREIA_LANGUAGE.md` first; this skill is the short agent checklist on top of it.

**Start:** `docs/development/ADD_A_GREIA_LANGUAGE.md`. The one offered-language registry is now the set of `src/greia_platform/languages/<locale>/manifest.json` files, consumed by installer, Shell, Parent Settings and the Parent API. Do not add a second hardcoded language list.

**Scaffold:** `PYTHONPATH=src python3 tools/scaffold_greia_language.py <locale>`. The tool creates editable UI and Activity JSON from English reference strings, **without** adding an offered manifest or replacing existing audio. Translate and review those files; add locale to Activity TOML declarations as required. Run `PYTHONPATH=src python3 tools/check_greia_language.py <locale> --staged` before publishing the manifest: it checks UI catalog schema, ordinary and nested format placeholders, and Activity key parity. It cannot judge translation quality. Keep spoken scripts separate from UI copy and literacy curriculum.

**Voice:** read `skills/greia-voice-production/SKILL.md`, `tools/greia_voice_core/README.md` and `docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md`. Use the selected VoxCPM2/VoxStage master registry and current pinned Parakeet-TDT v3 verifier through VoiceEngine. No direct model calls or silent model downloads. Voice assets need actual human review.

**Promotion:** adding `<locale>/manifest.json` offers the language on the next process start. Do this only after translated installer/OS/Parent and Activity resources, audio, font/layout and installed-device acceptance, and owner approval. Run `PYTHONPATH=src python3 tools/check_greia_language.py <locale>`, manifest tests and the normal release source checks; a source PASS does not certify speech or an image. Existing EN/IT/ES/FR baseline remains unchanged.

**Limits:** new ordinary left-to-right languages can be added through manifest + JSON/TOML + audio rather than core Python edits. New script shaping, right-to-left layouts, native phonics, language-model capabilities and the separately sourced Parents HTML UI may require engineering and testing. External contributors submit review PRs.
