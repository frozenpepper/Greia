# Greia — Current Engineering Handover

**Updated:** 2026-09-02  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`  
**Version file:** `0.13.0-phase0-dev`  
**Primary blocking phase:** **R7 — display/session/input architecture and exact-current physical closure**  
**Public source readiness:** **IN PROGRESS — documentation cleanup started; legal/provenance/security/community gates still open**  
**Ordinary-family release:** **NOT READY**

This file is deliberately a **short continuation contract**. Historical implementation detail belongs in the append-only active plan, dated reviews and Git history.

---

## 1. Start here

Before substantive work read:

```text
AGENTS.md
README.md
docs/DOCUMENTATION.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
HANDOVER.md
skills/greia-os-work/SKILL.md   # OS/platform work
```

Before installing/configuring tools read `SETUP.md`.

For public-release work also read:

```text
docs/release/GREIA_PUBLIC_RELEASE_READINESS.md
docs/governance/LICENSING_AND_TRADEMARK.md
docs/reviews/2026-09-02_PUBLIC_REPOSITORY_DOCUMENTATION_DEEP_DIVE.md
```

Do not use GitHub-hosted Actions without explicit owner authorization.

---

## 2. Exact current source/evidence boundary

At the start of the 2026-09-02 documentation cleanup, `main` was:

```text
a893654cfc95d816dbdbdfc0f3060b8c0fc6daa8
```

That commit is documentation-only. The latest runtime-affecting commit immediately below it is:

```text
138116186b7731264aedf92a898558984432d4e9
Expose live Greia volume controls to Parent API
```

The current runtime tree also contains the preceding system-control/hardware-session changes made after the last physically tested Home candidate.

### Important evidence rule

The Home regression was physically proven on the Acer at exact runtime candidate:

```text
57626d3f65a8bf3ae074eee15b00ee32ba3277bd
```

At that candidate:

- Writing Home visible/action: PASS;
- Painting Home visible/action: PASS;
- Shape Garden Home visible/action: PASS;
- Acquario Home visible/action: PASS;
- protected Home returned through Greia lifecycle;
- Activity process was gone after return;
- Shell was immediately responsive;
- usage-limit wrapper sanity was physically observed;
- no additional Legacy-X visibility hardening was required.

Full evidence is preserved in the active plan's 2026-09-02 Home-regression entry and Git history.

**Do not silently promote that physical PASS to the later system-control/Parent-API source.** The current runtime tree has advanced beyond `57626d`; exact-current physical claims require a new frozen/deployed candidate where the applicable R7 gate demands them.

---

## 3. R7 status — still blocking

R7 remains open. Core invariants:

- Home/Back is Greia platform authority, never Activity-owned UI;
- `DisplaySessionCoordinator` owns Shell/Activity display-session transitions;
- `SystemChromeCoordinator` owns trusted navigation semantics;
- `TrustedChromeActivitySupervisor` binds Home to the authoritative Activity lifecycle;
- Activities remain display-backend neutral and retain direct safe SDL/Pygame rendering/input paths;
- ordinary Activities receive no raw `/dev/input` or `/dev/dri` authority;
- Legacy X remains migration/compatibility plumbing, not the final architectural target;
- Simulator evidence never substitutes for production backend/hardware evidence.

Current continuation procedure:

```text
docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md
```

Before executing it, freeze the **actual current runtime candidate**. Do not reuse the old `1edb22ce` wording that remains in historical evidence. Screen coordinates are navigation only; counted launches must use the procedure's semantic process/Activity identity proof.

R7.4/controller-system-input work must not bypass the remaining R7.2/R7.3 acceptance requirements.

---

## 4. Home regression — CLOSED

The September 2 regression in which Activities could run without Home was caused by a fail-open supervisor-composition path when Parent-package discovery raised `ActivityValidationError`.

Correction:

```text
918770a3d3c98baffe02e1e2388ce9b169b1c06c
```

`GreiaLauncherPresentation._configure_parent_package_source()` now rebuilds the current specialized runtime services around the already validated registry instead of retaining the plain base `ActivitySupervisor`.

This preserves the intended composition:

```text
ProfileVisualActivitySupervisor
  -> TrustedChromeActivitySupervisor
  -> UsageLimitedActivitySupervisor
  -> ActivitySupervisor
```

Physical Home verification at `57626d` is PASS as recorded in §2. Do **not** restore retired Activity-side Home helpers.

---

## 5. Activity catalogue

Current built-in Activity inventory: **34**.

The catalogue-wide modernization/decomposition pass is **COMPLETE**. Do not restart a broad refactor sweep without a concrete defect.

Latest known catalogue regressions fixed on current history include:

- `acquario_magico` script/package import fallback after decomposition;
- `treno_numeri` slotted `TrainModel.train_state` field;
- strict Activity backend-independence audit blockers: historically zero on the latest executed R7 gates;
- strict Activity system-chrome ownership blockers: historically zero on the latest executed R7 gates.

Run the current exact gates again whenever the active R7 procedure requires current-source evidence; old PASS counts are not automatically current.

---

## 6. Launcher spoken labels

Current implemented/content state:

```text
34 Activities × it/en = 68 Activity-title clips
19 Collection/sub-Collection IDs × it/en = 38 system clips
total = 106
```

All 106 launcher-label clips received owner human acceptance on 2026-09-02. Runtime uses prerecorded static assets; no child-runtime TTS is introduced.

Architecture:

- Shell-owned semantic focus/hover presentation;
- pointer dwell about 160 ms;
- immediate keyboard selection speech;
- one interrupt/replace narration channel, no FIFO backlog;
- bounded 48-entry Sound cache;
- Activity launch/profile/logout lifecycle stops launcher speech;
- Activity title uses accepted lead presenter when explicitly established, otherwise Leo; platform Collections use Leo;
- pedagogical speech is never used merely for a launcher title.

Source/audit/headless-controller work is complete. Any remaining formal GUI/Acer spoken-label acceptance should be treated as its own evidence lane and must not be confused with voice human review, which is complete.

Authority:

```text
src/greia_launcher/spoken_labels.py
skills/greia-activity-authoring/LAUNCHER_SPOKEN_LABELS.md
docs/agents/2026-09-01_LAUNCHER_SPOKEN_LABELS_LOCAL_COMPLETION.md
```

---

## 7. Shared character speech

The shared reaction/introduction production status is now:

```text
180 shared character reactions: GENERATED + OWNER-ACCEPTED
12 character introductions:     GENERATED + OWNER-ACCEPTED
accepted set: assets/audio/characters/shared/v0.2/
v0.1 predecessor: retired historical set
runtime shared-utterance resolver wiring: separate/pending where not yet completed
final introduction product placement: undecided
```

Do not describe the v0.2 assets as still awaiting generation/listening. Conversely, accepted authoring assets do not prove runtime resolver/product-UX completion.

All new prerecorded speech continues through `tools/greia_voice.py` / VoiceEngine; no authoring model stack belongs on child devices.

---

## 8. Toddler Activities (Ages 2–3): Counting and Letters

Two first-party built-in Activities targeted at toddlers (2–4yo, difficulty 1, pre-reader design) have been added and remediated:
- `activities/il_giardino_dei_numeri/` (`org.greia.il-giardino-dei-numeri`): Early counting, subitizing, and one-to-one correspondence (quantities 1–5) guided by Dani with interactive objects (apples, strawberries, flowers, butterflies, ducklings, stars), basket filling mechanics, ascending pentatonic procedural audio chimes, pleasant ripple effects on empty ground taps, and milestone/completion platform events (`garden.set_counted`, `garden.basket_filled`).
- `activities/alfabeto_leo/` (`org.greia.alfabeto-leo`): Capital letter discovery (A–Z) guided by Leo with tactile surprises, 26 bilingual object reveals (Italian/English), dual modes (Explore & Peek-a-boo Guess), physical keyboard letter key discovery (pressing A–Z triggers the letter immediately), procedural audio chimes/wobbles/fanfares, and milestone/completion platform events (`letter.discovered`, `alphabet.parade_completed`).

Both activities satisfy:
- Pre-reader UX pass: `PRE_READER_CORE_FLOW_PASS=yes`, `TEXT_REQUIRED_FOR_GAMEPLAY=no` (`PRE_READER_UX.md`)
- Capital letters default policy (`ADR 0034`)
- Spoken title audio generated via Chatterbox MLX Multilingual v3 engine for both Italian and English (`locales/it/audio/activity-title.wav`, `locales/en/audio/activity-title.wav`)
- 134 total in-game spoken educational voice clips generated via Greia VoiceEngine (`tools/generate_toddler_audio.py`):
  - 22 Dani clips in `il_giardino_dei_numeri/assets/audio/it|en/` for welcome greeting (*"Ciao! Tocca e conta con me!"*), counting numbers 1–5, prompts, and praise (*"Fantastico! Che meraviglia, il cesto è pieno!"*)
  - 112 pedagogical clips in `alfabeto_leo/assets/audio/it|en/` for welcome greeting, letter pronunciation A–Z ("A come Ape" / "A is for Apple"), spoken questions for pre-readers ("Dov'è la lettera S?"), retries, and praise
  - Storybook visuals: official 256x256 character art (Dani and Leo) grounded with animations, lush backgrounds (meadow and treehouse), rich high-contrast storybook item emojis (`🍎`, `🐝`, `🐸`, `🚂`...)
  - True Nunito Sans font loading fallback in `src/greia_platform/typography.py` for development/simulator hosts
  - Sequenced audio queue in `giardino_model.py`: 1.0s delay between final counted item and celebration prevents celebration fanfare from stomping over Dani's spoken number
  - Interactive drawn triangle buttons replacing unicode arrow glyphs (no tofu boxes)
- 256x256 RGBA icons composed with character art
- Dedicated unit tests: `test_activity_il_giardino_dei_numeri.py` (3 tests PASS), `test_activity_alfabeto_leo.py` (4 tests PASS), all 355 test_activity_* tests PASS
- `tools/audit_launcher_spoken_labels.py`: PASS (`BUILT_IN_ACTIVITIES=36 ACTIVITY_TITLE_COMPLETE=72`)
- `tools/audit_activity_backend_independence.py`: PASS (`activities=36 blockers=0`)
- `tools/audit_activity_system_chrome_ownership.py --strict`: PASS (`blockers=0`)
- `tools/headless_greia_simulator.py`: PASS on both activities (survived >= 2s, click interaction, Home return to Shell, rc=0)

---

## 9. Parent/system controls

Current source after the Home physical candidate includes a platform-owned persistent system-control domain and later Parent API exposure for live output volume controls.

Relevant current source owners include:

```text
src/greia_platform/system_controls.py
src/greia_platform/system_controls_legacy_x.py
src/greia_platform/hardware_session.py
src/greia_platform/hardware_session_legacy_x.py
src/greia_parent/protocol.py
src/greia_parent/update_api.py
```

The latest runtime-affecting commit at the start of this docs pass is `138116186...`.

Because these source changes post-date the `57626d` Home physical candidate, do not claim exact-current physical certification merely from the Home run. Review/run the focused/current gate before promoting this newer runtime tree.

Parent authority remains typed and bounded; browser/Parent API code does not directly own host mixer/backlight device mechanics.

---

## 9. Public-source/release documentation cleanup

The first public-repository documentation deep dive is recorded in:

```text
docs/reviews/2026-09-02_PUBLIC_REPOSITORY_DOCUMENTATION_DEEP_DIVE.md
```

First tranche goals:

- current entry points stay current instead of accumulating historical evidence;
- dated test protocols stop pretending to be global perpetual “START HERE” documents;
- root historical `LOCAL_AGENT_RESULT.md` is removed from the public front door;
- README/SETUP/voice status are synchronized with actual repository state.

Still pending before public source publication:

- refresh `docs/DOCUMENTATION.md` owner/ADR matrix, including ADR 0034 and newer source owners;
- repair broken/stale paths in derived routers/manuals (including the ADR 0013 filename in `skills/greia-os-work/SKILL.md`);
- repository-relative documentation link/path audit;
- full licensing/provenance/history-secret audit;
- reviewed public legal/community files and security/privacy/contribution entry points;
- public developer quick start and parent/user documentation appropriate to the release threshold.

The authoritative full checklist remains:

```text
docs/release/GREIA_PUBLIC_RELEASE_READINESS.md
```

---

## 10. Next exact work

### Blocking engineering

1. reconcile/freeze the current runtime candidate after the post-`57626d` system-control changes;
2. run the current source gates required by `docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md`;
3. execute the remaining exact-current R7.2/R7.3 physical evidence lanes;
4. only then advance the next blocking R7 work allowed by the active plan.

### Documentation/public-source cleanup

In parallel where it does not bypass R7:

1. refresh `docs/DOCUMENTATION.md` against the actual tree and ADR 0034;
2. repair task-router/manual path drift;
3. classify stale one-off agent/testing docs as historical/superseded where needed;
4. add a deterministic repository-relative documentation path/link audit;
5. begin the licensing/provenance/security/community-file Threshold-A gate without making unsupported legal claims.

---

## 11. Evidence discipline

Always preserve these distinctions:

```text
SOURCE
AUTHORING PROVIDER + HUMAN LISTENING
SIMULATOR
VM / IMAGE
PHYSICAL DEVICE
```

A later source commit does not inherit a physical PASS automatically. A valid audio receipt/Whisper result does not replace human listening. A Simulator screenshot does not prove production trusted chrome. Historical reviews remain evidence for their exact state, not current truth by default.
