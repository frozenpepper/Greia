# Greia — Current Engineering Handover

**Updated:** 2026-09-02  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`  
**Version file:** `0.13.0-phase0-dev`  
**Primary blocking phase:** **R7 — display/session/input architecture and exact-current physical closure**  
**Public source readiness:** **IN PROGRESS**  
**Ordinary-family release:** **NOT READY**

This is the short continuation contract. Historical implementation detail belongs in the append-only active plan, dated reviews and Git history.

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

For public-source/release preparation also read:

```text
docs/release/GREIA_PUBLIC_RELEASE_READINESS.md
docs/governance/LICENSING_AND_TRADEMARK.md
docs/reviews/2026-09-02_PUBLIC_REPOSITORY_DOCUMENTATION_DEEP_DIVE.md
```

Do not use GitHub-hosted Actions without explicit owner authorization.

---

## 2. Exact current source/evidence boundary

Current `main` at this handover update is descended from:

```text
1e851eef53e68e13f17053bc464c130b14bc3687
Enforce Greia voice contract: Chatterbox for Leo character dialogue, deterministic TTS for pedagogical targets
```

That latest runtime-affecting commit changes Activity audio/assets and receipts. It does not provide new R7 physical evidence.

The trusted-Home regression itself was physically proven on the Acer at exact runtime candidate:

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

**Do not promote that PASS to later platform/system-control source.** Exact-current R7.2/R7.3 claims require a newly frozen candidate and the current named gate.

---

## 3. R7 — still blocking

Core invariants remain:

- Home/Back is Greia platform authority, never Activity-owned UI;
- `DisplaySessionCoordinator` owns Shell/Activity display-session transitions;
- `SystemChromeCoordinator` owns trusted navigation semantics;
- `TrustedChromeActivitySupervisor` binds Home to authoritative Activity lifecycle;
- Activities remain display-backend neutral and retain direct safe SDL/Pygame rendering/input paths;
- ordinary Activities receive no raw `/dev/input` or `/dev/dri` authority;
- Legacy X is migration/compatibility plumbing, not the final architecture;
- Simulator evidence never substitutes for production backend/hardware evidence.

Current exact-candidate procedure:

```text
docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md
```

The obsolete version of that document hard-coded `1edb22ce`, a fixed Activity count and old catalogue geometry. The current version resolves the candidate dynamically from `origin/main` and requires semantic Shell launch identity rather than coordinate-only launch assumptions.

### Post-physical system-control corrections awaiting execution

```text
adec85c4fdf005ac473124dbf973405c37f3ddfa
  relative volume/brightness/mute key changes compute inside one locked desired-state mutation

e89e2e52d88f31b42c4faf6894bc25893435d362
  Legacy-X media-key listener drains Xlib-buffered events before waiting on the X socket

8610efc7dfb19ef9b82ace7b823a348f728a6f98
  focused behavioral regressions for those two contracts

b7a3d0ddc671898286c00dea0ca1aeb6f022723a
  exact-candidate-safe final R7 evidence procedure

a2123bae269dad4fbc48c7346f914ee011a932f7
  dated review of the two system-control defects/corrections
```

These are **SOURCE corrections, not PASS evidence**. The next R7 acceptance must include normal media keys, rapid key bursts, Parent-setting→physical-relative-key composition and media-key isolation while an Activity is active.

**Do not begin R7.4 implementation before the required R7.2/R7.3 exact-current physical closure is accepted.**

---

## 4. Home regression — closed at its exact candidate

The September 2 missing-Home regression was caused by a fail-open supervisor-composition path when Parent-package discovery raised `ActivityValidationError`.

Correction:

```text
918770a3d3c98baffe02e1e2388ce9b169b1c06c
```

`GreiaLauncherPresentation._configure_parent_package_source()` rebuilds the current specialized runtime services around the already validated registry instead of retaining the plain base `ActivitySupervisor`.

The intended composition remains:

```text
ProfileVisualActivitySupervisor
  -> TrustedChromeActivitySupervisor
  -> UsageLimitedActivitySupervisor
  -> ActivitySupervisor
```

Do not restore retired Activity-side Home helpers.

---

## 5. Activity catalogue

Current built-in Activity inventory: **37**.

The catalogue-wide modernization/decomposition pass is **COMPLETE**. Do not restart a broad refactor sweep without a concrete defect.

Current catalogue includes the toddler Activities:

```text
org.greia.il-giardino-dei-numeri
org.greia.alfabeto-leo
org.greia.bosco-numeri
```

Recent source evidence recorded in current history includes:

- launcher spoken-label audit: `BUILT_IN_ACTIVITIES=36`, `ACTIVITY_TITLE_COMPLETE=72`;
- backend-independence audit: `activities=36 blockers=0`;
- strict system-chrome audit: `blockers=0`;
- headless Simulator smoke PASS for toddler Activities (il-giardino-dei-numeri, alfabeto-leo, and bosco-numeri auto-advance, cardinality and guess mode).

Those recorded results do not replace the current exact R7 gate where that gate requires a freshly frozen candidate.

---

## 6. Launcher spoken labels and voice assets

Launcher spoken-label architecture/content is complete for the accepted catalogue set and remains Shell-owned prerecorded audio; no child-runtime TTS is introduced.

Shared accepted character speech remains:

```text
180 shared reactions: OWNER-ACCEPTED
12 character introductions: OWNER-ACCEPTED
accepted set: assets/audio/characters/shared/v0.2/
```

Runtime shared-utterance resolver/product placement remains a separate concern.

The latest `1e851eef` toddler-audio correction enforces the voice-production contract for `alfabeto_leo`: Leo character dialogue uses the Leo Chatterbox voice while deterministic pedagogical targets remain on the deterministic path. Newly regenerated receipts remain subject to the normal human-listening acceptance rule; generation/provider success is not human acceptance.

All new prerecorded speech continues through `tools/greia_voice.py` / VoiceEngine; no authoring model stack belongs on child devices.

---

## 7. Parent/system controls

Current exact owners include:

```text
src/greia_platform/system_controls.py
src/greia_platform/system_controls_legacy_x.py
src/greia_platform/hardware_session.py
src/greia_platform/hardware_session_legacy_x.py
src/greia_parent/protocol.py
src/greia_parent/update_api.py
```

Persistent desired state is platform-owned. Parent/browser code may mutate only typed bounded settings; it does not own host mixer/backlight mechanics or expose arbitrary commands.

Because this subsystem changed after the `57626d` physical Home candidate, the current exact-candidate physical system-control lane is mandatory before claiming current runtime acceptance.

---

## 8. Public-source documentation cleanup

The first public-repository deep dive is:

```text
docs/reviews/2026-09-02_PUBLIC_REPOSITORY_DOCUMENTATION_DEEP_DIVE.md
```

Completed/high-confidence cleanup already present in current history:

- `HANDOVER.md` converted back into a short current continuation contract;
- `docs/testing/LOCAL_AGENT_START_HERE.md` converted into a living router rather than an old fixed test session;
- historical root `LOCAL_AGENT_RESULT.md` removed from the public front door;
- README/SETUP/voice status refreshed;
- `docs/DOCUMENTATION.md` now includes ADR 0034 and newer exact owners such as child text, launcher spoken labels and system controls;
- `skills/greia-os-work/SKILL.md` references the correct ADR 0013 filename and current R7/system-control routes;
- `docs/agents/GREIA_AGENT_OPERATIONS.md` was compacted into a living operating router with current `main` branch policy, current handover-selected R7 routing, evidence separation and local-agent failure-preservation rules (`17ab93218c24029a911c64a566a7fcf912eb4bbb`).

Still pending for Threshold A public-source readiness:

1. add a deterministic provider-free repository-relative documentation path/link audit for living navigation contracts;
2. classify materially ambiguous stale one-off runbooks/reviews as historical/superseded without rewriting their evidence;
3. complete licensing/provenance/history-secret/security/privacy/community-file review;
4. add reviewed public legal/community entry points rather than generic placeholders;
5. produce a public developer quick start and later ordinary-parent/user documentation appropriate to the release threshold.

Authoritative release checklist:

```text
docs/release/GREIA_PUBLIC_RELEASE_READINESS.md
```

---

## 9. Next exact work

### Blocking engineering

1. freeze the actual current candidate using `docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md`;
2. run the focused source gate, both architecture audits and `make verify`;
3. run the real-Shell Simulator matrix;
4. only if green, deploy that exact frozen SHA to the Acer;
5. execute system-control, Writing, Painting, hostile 10/10, crash-recovery, 20/20 durability and performance/log lanes;
6. classify the exact candidate `ACCEPTED`, `REJECTED` or `INCOMPLETE`;
7. only after accepted R7.2/R7.3 closure advance the next R7 subphase permitted by the active plan.

### Public-source cleanup that may proceed in parallel

1. implement the deterministic living-document path/link audit;
2. begin the licensing/provenance/security/community-file Threshold-A audit without unsupported legal claims.

---

## 10. Evidence discipline

Always preserve these distinctions:

```text
SOURCE
AUTHORING PROVIDER + HUMAN LISTENING
SIMULATOR
VM / IMAGE
PHYSICAL DEVICE
```

A later source commit does not inherit a physical PASS automatically. A valid audio receipt/Whisper result does not replace human listening. A Simulator screenshot does not prove production trusted chrome. Historical reviews remain evidence for their exact state, not current truth by default.
