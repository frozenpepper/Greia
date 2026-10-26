# Greia language support tiers — proposal for owner decision

**Date:** 2026-09-27
**Status:** HISTORICAL / SUPERSEDED on 2026-10-12. This document records the
2026-09-27 proposal, not current implemented behavior. Owner has now
approved the separate **four-language rollout**:
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md`.
As of 2026-10-12 the selectable registry has been reduced to EN/IT
and ES/FR are staged for translation and voice before future promotion.
All historical twelve-language figures below are source snapshots,
not current support claims.
**Requested by:** repository owner, during the Acer physical installer investigation.
**Audience:** lead agent / repository owner.

## 1. What was asked

Define which languages Greia actually supports, tie that declaration to the installer's
language selection, and express two support tiers — full (including spoken guidance) and
text-only — with English as the fallback where automated voiceovers are not possible.

## 2. Why this is a real gap, not a tidiness request

The repository currently contains **two contradictory declarations** of "supported
language", and neither is honest about the difference between a language being
*selectable* and a language being *implemented*.

### 2.1 What the platform declares

`src/greia_platform/system_language.py:51-64` declares twelve supported system languages:

| locale | endonym | locale | endonym |
|---|---|---|---|
| `en` | English | `pt` | Português |
| `it` | Italiano | `ar` | العربية |
| `es` | Español | `hi` | हिन्दी |
| `de` | Deutsch | `id` | Bahasa Indonesia |
| `fr` | Français | `bn` | বাংল |
| `zh-CN` | 简体中文 | `sw` | Kiswahili |

### 2.2 What is actually implemented

| Surface | Reality | Evidence |
|---|---|---|
| Installer reviewed copy | English (source) + **Italian only** | `src/greia_installer/i18n.py:14` (`_ITALIAN` is the only translation table) |
| Activity locale bundles | all **41** Activities ship exactly `en.json` + `it.json` | `activities/*/locales/` |
| Spoken catalogue labels | `en/` and `it/` only, **19 wavs each** | `assets/audio/system/launcher-labels/` |

So: **two locales are implemented; twelve are declared.** Ten languages have neither
translated interface copy nor spoken labels.

The installer already acknowledges the gap in a source comment
(`src/greia_installer/i18n.py:9-12`): a locale "is only advertised here when this surface
actually has reviewed copy", and selecting another valid device locale "remains safe and
falls back to English rather than pretending the installer is translated."

That fallback is safe, but it is **silent**. A parent can select a language whose
installer is entirely English, with no indication that they did so.

### 2.3 The fallback mechanism the owner intuited already exists

`src/greia_launcher/spoken_labels.py:28-45` implements exactly the rule proposed here,
under ADR 0028:

> Catalogue speech follows the requested Greia UI locale first. English is a final
> compatibility fallback when supplied.

Resolution order is `requested locale -> locale fallback chain -> en`. That is the
"English by default where voiceovers are not possible" behaviour — but it is **implicit**,
resolved per asset at runtime, and never declared as a language capability. Nothing in the
product states which languages have voices and which do not.

## 3. Proposed model

One authoritative declaration, consumed by both the installer chooser and the audio
resolver. Per locale:

| Field | Meaning |
|---|---|
| `locale` | BCP-47 tag, canonical |
| `endonym` | name written in the language itself |
| `text` | `complete` / `partial` / `none` — installer + launcher + Activity copy |
| `voices` | `complete` / `none` — spoken catalogue labels exist for this locale |
| `text_fallback` | locale to read copy from when this locale's `text` is not `complete` |
| `voice_fallback` | locale to speak from when this locale has no voices |

### 3.1 Tier definitions

**Tier 1 — full.** `text: complete` **and** `voices: complete`. The installer, the shell
and the Activities are in this language, and spoken navigation guidance is in this
language. Nothing falls back.

**Tier 2 — text-only.** `text: complete`, `voices: none`. Interface is fully in the
language; spoken guidance falls back to `voice_fallback` (English). The parent must be
told that voice guidance will be English, because otherwise "full support" is implied.

**Tier 3 — declared, not implemented.** `text: none`. The locale may remain a *device
language preference* (the installed system records it, and `greia-languagectl` accepts
it), but it must **not** be offered in the installer chooser, because the installer would
present English while claiming another language.

### 3.2 Honest state today

Under this model the current tree evaluates to:

| locale | tier | text | voices |
|---|---|---|---|
| `en` | 1 full | complete | complete (19 labels) |
| `it` | 1 full | complete | complete (19 labels) |
| `es` `de` `fr` `zh-CN` `pt` `ar` `hi` `id` `bn` `sw` | 3 declared only | none | none |

So the proposal does not add a language. It **stops the product claiming ten it cannot
deliver**, and it creates the explicit place where the next language is added.

## 4. Consequences the owner should decide on

1. **Should the chooser shrink or the claim grow?** Today a parent can pick any of twelve.
   Options: (a) offer only Tier 1/2 locales in the installer chooser, and keep the twelve
   available as a post-install device preference; (b) offer all twelve but label the
   unimplemented ones explicitly; (c) keep current behaviour and only fix the audio tier.
   **Recommendation: (a)** — a first-boot chooser that silently shows English is the exact
   failure the owner is trying to prevent.
2. **Is English-voice fallback acceptable for a child who cannot read the fallback
   language?** For Tier 2, a pre-reader relies entirely on speech. If the interface is
   Italian but the guidance is English, that child is materially underserved.
   **This is a product judgement, not an engineering one, and it is the strongest argument
   for treating voice coverage as a hard requirement for any Tier 1 language.**
3. **What is the cost of a new Tier 1 language?** It needs: installer copy, launcher copy,
   41 Activity locale bundles, and 19 spoken labels, plus review. It should be an explicit,
   budgeted decision rather than an accident of which strings got translated.
4. **Who owns the declaration?** Proposal: the platform module that already owns
   `system_language`, consumed by the installer chooser and by `spoken_labels`. This
   replaces the 12-language constant with an honest capability record and keeps one owner.
   It touches the localization ADR, so it is an ADR-level change, not a patch.

## 5. Explicitly not proposed

- No machine translation as a strategy. Tier 3 stays Tier 3 until a human reviews the copy.
- No removal of the twelve declared device languages. A parent may still set a device
  language preference; only the *installer chooser* and the *tier claims* change.
- No change to ADR 0028's existing per-asset fallback chain. This proposal makes the
  capability visible; it does not replace the resolver.

## 6. Evidence basis

All figures in this document were read from the tree at
`1b366e67`+ and are reproducible:

```bash
grep -n 'SUPPORTED_SYSTEM_LANGUAGES' -A 14 src/greia_platform/system_language.py
ls activities/*/locales/*.json | sed 's#.*/##' | sort | uniq -c
ls assets/audio/system/launcher-labels/
grep -c '' src/greia_installer/i18n.py
```

No hardware evidence is claimed. The Acer test that prompted this proposal concerned boot
and installer UI behaviour, not language coverage.
