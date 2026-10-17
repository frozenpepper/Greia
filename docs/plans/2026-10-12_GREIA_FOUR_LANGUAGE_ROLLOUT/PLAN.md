# Greia — Honest Language Selection and Four-Language Rollout

**Date:** 2026-10-12  
**Status:** ACTIVE. **Owner decision 2026-10-17: EN, IT, ES and FR are all released and selectable**; every selector offers exactly these four (registry `src/greia_platform/system_language.py`, all 45 Activity manifests). Four-way text-key parity holds across installer, Shell, Parent panel and Activities; missing voice lines approved by the owner ("I approve all lines") were recorded locally in all four languages on 2026-10-17 (see `PROGRESS.md`). Remaining: rendered 1024×600/800×480 review, installed-image and hardware evidence, human listening of the 2026-10-17 recordings, and the per-Activity wiring of requested lines that no code plays yet.  
**Intent:** one correctly integrated language experience across the installer, installed OS, Parent controls, built-in Activities and their speech.  
**Owner:** Greia product source; language setting authority remains `src/greia_platform/system_language.py`; runtime inheritance/Activity fallback remains ADR 0028.  
**Voice execution:** `LOCAL_AGENT_VOICE_PRODUCTION.md` in this directory.  
**Progress:** append to `PROGRESS.md`; integration/acceptance tasks remain in the existing `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`.

## Owner design decision — 2026-10-15: unify runtime localization and spoken-asset lookup

**New architecture/implementation slice:** [`SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md`](./SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md). Retain the existing shared `greia_platform.localization` as the single Activity-facing localization owner: child/profile-selected locale, semantic text key, semantic prerecorded audio key, and resolved string/audio path. Consolidate direct Activity file lookups and launcher speech fallback into that layer; only update Activity-creation skill to the *implemented* API. Preserve all owner-approved committed recordings unchanged. **File modification by users is permitted; do not add anti-tamper/hash approval infrastructure.** For now every speech cue, including phonemes/letters/syllables, may use **requested-locale audio file → English file → silence**, with a single key→legacy-filename mapping where needed. No new running TTS or per-language duplicate catalogues. Existing `VOICE_GENERATION.md` strict native-phoneme fallback guidance is superseded as a future design constraint **once the shared implementation is migrated**; until then current code contracts remain what callers actually use.

**Owner approval status:** All previously committed recordings are fully personally approved; old text saying audio generation/listening is entirely pending is historical and does not override this decision. The focused still-missing files are assigned to [`docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md`](../../testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md). Release status remains EN/IT selectable, ES/FR staging until technical runtime/playback and visual acceptance; fallback alone should not be treated as a failure or as a security concern.

## 2026-10-16 — Voice lines requested by the P7 Activity reworks

All 45 Activities were reworked word-free and voice-first (P7 W0–W3, `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P7_ACTIVITY_QUALITY_PROGRAM.md`). The consolidated, owner-reviewable list of every spoken line the reworks want (shared numbers 0–25, colour, position, shape and noun names for the vocabulary bank, then per-Activity lines, EN + IT) is [`VOICE_LINES_REQUESTED_2026-10-16.md`](./VOICE_LINES_REQUESTED_2026-10-16.md). **Nothing was generated.** After the owner approves rows, the zero-new-spend local Voice Studio may produce candidates under the rules of `LOCAL_AGENT_VOICE_PRODUCTION.md`; ES/FR stay staged.

## Owner decision — 2026-10-14: text approved, complete voice production authorized

The owner explicitly **approved all translations already authored in the
English, Italian, Spanish and French source text catalogues**. This is an
owner content/copy acceptance decision for those existing literal
translations, including staged curriculum *written examples*. Stop
holding available text solely for another generic translation approval.
It does **not** assert there are no remaining untranslated inline Shell,
Creations, Parent API or child-visible messages, and it does **not**
conjure absent long-form narration/phoneme scripts. Native preschool
pronunciation, syllable sound, scientifically accurate narration and
actual rendered text fit remain separate *technical* verification tasks.

The owner additionally instructed Greia's local agent to **record every
missing spoken cue across all apps in all four languages**, including
EN/IT repairs. Use the exact executable
[`LOCAL_AGENT_ALL_APP_VOICE_RECORDING_ORDER.md`](./LOCAL_AGENT_ALL_APP_VOICE_RECORDING_ORDER.md)
alongside existing
[`LOCAL_AGENT_VOICE_PRODUCTION.md`](./LOCAL_AGENT_VOICE_PRODUCTION.md).
An already configured registered no-new-spend local producer may work
without waiting for Modal; new paid/cloud expenditure still requires
explicit amount/provider consent. New recordings and existing cues
still need human listening; ES/FR remain **unselectable** until L6.

## 1. Product commitment

The shipped selector must show **only usable supported product languages**.
The prior twelve-language registry created a false product claim. Existing
English and Italian are the current baseline, but even their completeness
must be audited rather than assumed. **Spanish (es) and French (fr) are the
two languages being added**, with equivalent scope, quality and child
accessibility. German, Chinese, Portuguese, Arabic, Hindi, Indonesian,
Bengali and Swahili are not selectable until separately localized/accepted.

| Language | Now visible | Rollout target | Notes |
|---|---|---|---|
| English `en` | yes | complete text + spoken guidance | repair any gaps |
| Italian `it` | yes | complete text + spoken guidance | repair any gaps |
| Spanish `es` | no | complete text + spoken guidance | stage offline assets, then promote |
| French `fr` | no | complete text + spoken guidance | stage offline assets, then promote |
| Other eight | no | later project | no pretend support |

The registry above governs **device language choices**. It must not
conflate the language of an educational lesson, a child's creation,
an imported Activity or the Linux `LANG` process environment. An
independently authored single-language Activity may remain valid under
ADR 0028, with a visible real-language cue. A locale is not declared
fully supported solely because a JSON file or voice sample exists.

**English compatibility fallback (owner revised 2026-10-15):**
when a selected-locale spoken file is absent, Greia may play the English
version, **including for literacy/phoneme lessons for now**. This is
intentional acceptable runtime behavior, not a language-release hard
block, a voice-quality rejection or a prompt to regenerate approved
files. Continue counting fallback occurrences in coverage reporting;
ES/FR still need independent UI, installer, profile and real playback
validation before being offered as fully selectable OS languages.

## 2. Ownership and invariants

1. `SUPPORTED_SYSTEM_LANGUAGES` in
   `src/greia_platform/system_language.py` is the single **selectable**
   set. Installer `choose_language`, installed hidden Parent panel,
   `greia-languagectl` and Parent GET/PUT share it. No new browser
   hard-coded list. Accepted language additions are made atomically
   after the coverage/QA gate below.
2. Historical `/etc/greia-os/install-record.json` and old
   `/var/lib/greia-system-settings/language.json` records are never
   destructively migrated. If they contain retired unsupported tags,
   effective locale temporarily resolves to English; after a parent
   chooses a supported language, the override updates atomically.
   Restore/promotion rules must be tested.
3. `src/greia_installer/i18n.py` owns installer English base +
   reviewed translations; safety/security, destructive disk warnings,
   Wi-Fi, keyboard, pointer, status/error and formatted dynamic values
   must all be covered. Never translate SSIDs, disk IDs or passwords.
4. Platform Shell text (profiles/collections/launcher/chrome,
   permissions/rewards/time/Parent overlay/notifications/creation
   viewer/picker/OS settings) must use platform-owned semantic strings,
   **not** Activity-local copies and not process locale. Parent HTML
   client is a separate `frozenpepper/Greia-Parent-App-Html` source
   with its exact pinned build integrity handled through the existing
   release/Parent-client procedure.
5. Each built-in Activity receives effective locale through ADR 0028,
   has `locales/{en,it,es,fr}.json` (or an explicitly reviewed
   language-neutral declaration), matching manifest metadata, honest
   dialogue/instruction/text resources, correct grammar/plurals,
   captions, and semantic audio paths. Localized in-game labels,
   endings, rewards, progress, asset prompts, voice/text input and
   tutorial cues count; so do Creations, writing/painting and
   encyclopedia. Retain local educational **content** locale
   independent of UI locale.
6. Do not introduce per-language Pygame coordinate forks, duplicated
   Activity logic or new broad dependencies. Respect responsive
   typography, protected chrome, offline installation, low-memory Acer
   and ARM images, deterministic fallback and previous accepted ADRs.
7. Existing project policy prefers **Modal for voice production**.
   Modal/ASR/TTS are strictly authoring-time dependencies, never in
   child OS images or runtime. Only reviewed, bounded WAV/OGG assets
   enter release packs. Source translation/integration proceeds here;
   local agent owns recording, receipt and acoustic verification.
8. Source documentation and product scope are in English even while
   child-facing strings/recordings are translated.

## 3. Phase sequence

### L0 — Honest selector / legacy compatibility (started)

- Restrict canonical visible device language list to `en,it`.
- Confirm installer chooses from this list; Parent API and on-device
  panel use the same registry; helper rejects retired tags.
- Retain legacy historical records without modifying them;
  effective system fallback must not crash, hide menus or corrupt
  profile overrides. Test rejected writes and safe read/fallback.
- Update accepted product docs and outdated tests that claim 12
  supported languages. The release claim is still baseline/WIP
  until missing EN/IT audio and uncovered platform strings are fixed.

### L1 — Inventory, text extraction and completeness baseline

- Enumerate every OS text source, Parent HTML string, profile,
  launcher/Parent overlay/dialog, installer state/error, first-boot
  screen, system accessibility text, every built-in Activity and
  the encyclopedia. Identify inline nonlocalizable text with owner.
- Inventory `en,it` actual files; compare semantic keys, placeholders,
  direction/grammar, media path existence, catalogue title voices,
  speaker character IDs and all missing or unreviewed audio cues.
- Build a **single generated recording ledger** per locale, speaker,
  cue, exact text, output path, source, review status and test/evidence
  reference. Use the helper inventory tool, direct code review and
  audit scripts; they are complementary, not mutually exhaustive.
  Character dialogue embedded in gameplay must also be extracted.
- Repair missing EN/IT text/catalogue metadata and missing keys
  before mass translation; don't translate stale keys.

### L2 — Installer ES/FR translated and checked

- Add reviewed `es` and `fr` message maps for every installer
  source string and dynamic-safe full-message formatting;
  translate disk erasure/permission/preflight errors exactly.
- Integrate via existing `InstallerTranslator`; keep locale target
  staged and nonselectable. Test all translation keys, interpolations,
  accented glyphs, no accidental fallback and keyboard/pointer layout.
- Capture graphical installer at 1024×600 plus smaller supported size
  for en/it/es/fr; do not perform destructive installs merely to
  preview strings. Separate actual installer acceptance later.

### L3 — Platform Shell + Parent surfaces ES/FR and EN/IT repair

- Extract inline text from Shell, platform presentation, child
  navigation, Parent overlay and other system controllers to
  semantic string catalogue(s). Translate all four; keep one
  reference source and typed variable interpolation.
- Update the separate Parent HTML repo **using its own contract**
  and regenerate/re-pin integrity manifests only through the
  authorized existing procedure. Do not remove security or auth copy.
- End-to-end parent language change must affect effective device,
  profile inheritance, Shell and subsequent Activity launch without
  reinstall. Verify after reboot. Preserve per-profile overrides.

### L4 — Built-in Activity + encyclopedia text and manifest rollout

- Batch Activities in small, reviewable sets with en/it/es/fr key
  parity, visible language metadata and launch resolution. Extract
  remaining inline UI/dialogue before claiming translated.
- Include errors/tutorials/tool descriptions, endings/celebrations,
  all voice caption text, activity titles, educational labels,
  children's artwork/media view controls, and encyclopedia facts.
- Validate text fit on actual 1024×600 and 800×480, C0 RAM and
  no glyph replacement. No silent cross-language narration.
- Keep language-learning content language separate from UI; do not
  translate semantic data that is intentionally used to teach a
  language without product review.

### L5 — Local-agent speech production for all four locales

- Follow `LOCAL_AGENT_VOICE_PRODUCTION.md` exactly. Generate
  **missing en/it**, plus all required es/fr voices for the
  installer where spoken, OS/Shell/Parent surfaces, catalogue and
  every voice-using Activity/encyclopedia.
- Capture transcript/text QA, stable speaker identities, locale
  pronunciation, deterministic filenames, WAV specs, receipts,
  ASR score, loudness bounds, per-file human listening approval.
  Reuse verified existing clips; never blanket regenerate accepted
  character voices. Avoid inappropriate English fallback for
  Spanish/French speakers and bilingual mispronunciations.
- Review full catalogue plus negative cases; only accepted clips
  promoted from staging. No need to block text-only authoring on
  model/voice-generation availability.

### L6 — Atomic promotion of ES/FR and release acceptance

**Promotion requires all**, independently for each added locale:

1. Installer string catalogue complete, no English leakage outside
   named intentional product text; reviewed warnings and actual
   installation flow.
2. Platform Shell, authenticated Parent panel/API/HTML and built-in
   Activity text keys complete and displayable.
3. Audio ledger has no missing required cues for **all four
   locales**; new ES/FR voices verified by listening and receipts.
4. EN/IT existing missing text/audio defects resolved; locale-scoped
   fallback checks green, supported-language choices consistent.
5. Profile/parent locale inheritance, launcher labels and Activities
   behave correctly under real language switching and restarts.
6. Bilingual/multilingual 1024×600 and 800×480 visual acceptance,
   realistic speakers/audio, safe no-data-loss installer/upgrade
   checks, source tests, `make verify`, ARM/i386 packaging evidence.
7. Reconciliation of exact parent HTML client pin and installer
   build content; no stale prebuilt language strings.

After those gates, add `SystemLanguage("es", ...)` and/or
`SystemLanguage("fr", ...)` to the canonical registry with tests and
documentation. Do not prematurely promote unsupported languages.
No GitHub-hosted Actions, privileged installs, USB flashing,
expensive cloud work or device changes without separate authority.

## 4. Acceptance and evidence

- **Unit/static:** registry exactly matches selectable languages;
  legacy read-only fallback; strict rejection of unsupported writes;
  no unknown/duplicate semantic keys or missing required locale
  data; properly retained text placeholders/case; no unreviewed
  English strings inside promised UI; voice manifest complete;
  bounded audio format/files, shell/installer profile invariants.
- **Integrated:** select a locale as first installer screen,
  install-record preserves it, OS defaults to it on boot, Parent
  API/overlay changes persist without install-record mutation,
  child overrides inherit correctly, Activity sees its true
  support and catalogue flag, offline operation end-to-end.
- **Human:** language-aware proofread all four, human listen to
  character voices, install disk-erasure copy, ensure legibility
  at low resolution and no wrong-language speech. Take screenshots
  per major screen; missing audio must be a BLOCKED gate, not PASS.
- **Evidence boundaries:** GitHub source/commit ≠ executed unit test
  ≠ rendered Simulator ≠ installed Acer ≠ accepted recording.
  Report these separately in `PROGRESS.md`, `HANDOVER.md` and
  the existing agent queue. Preserve failures.

## 5. Immediate handoff and next slices

- Current engineering turn starts L0 source restriction and focused
  regression re-baselining, writes this plan and the exact local
  voice work order.
- Next GitHub slices: complete L0 validation and test migration;
  implement installer es/fr translations; inventory all platform
  strings and Activity audio; author the Shell/Activity locale packs.
- Local agent remains the exclusive designated producer/reviewer
  of speech audio, while this GitHub agent owns text, configuration,
  manifests, provider-agnostic integration, gap analysis and tests.
