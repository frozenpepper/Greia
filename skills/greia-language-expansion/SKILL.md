---
name: greia-language-expansion
description: Use when asked to add or translate a Greia language, create a new locale, expand installer/Shell/Parent/Activity translations, or prepare voice recording and verification for another language.
---

# Add or translate a Greia language

Start at `docs/development/ADD_A_GREIA_LANGUAGE.md`. This is the single practical contributor runbook and has the current truth about the configuration-only gap.

Read only the relevant authorities for each task:
- Product: `docs/product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md`, ADR 0028, `src/greia_platform/system_language.py`.
- Activity bundles: `src/greia_platform/localization.py` and `skills/greia-activity-authoring/SKILL.md`.
- Voice Studio: `skills/greia-voice-production/SKILL.md`, `tools/greia_voice_core/README.md`, `docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md`.
- Existing four-language historical rollout: `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md`.

A request to *prepare/translate* a new locale does not authorize making it selectable. Do not rewrite approved voices, start provider/model downloads or hosted paid jobs without authorization. Do not claim code-free locale addition: current installer, Parent/Shell and audit/release gates include hardcoded Python language tables.

Completion: demonstrate translated source coverage, voice provider and Parakeet readiness (or explicitly name what's missing), review and layout, the existing four-language regressions, and owner-approved release promotion separately. External contributors work on review branches/PRs.
