# Handover — `.greiaactivity` distribution + profile presentation/grammar tranche

Date: 2026-08-23

Branch: `work/profile-addressing-activity-format-20260823`

Base: `1c93880c834d25ef6549d597b3eb733ad026c140`

Status: **source implementation and permanent docs authored; local execution/physical UI review still required before merge/release claims**

## Why this tranche exists

Two related product needs were requested:

1. make a Greia Activity distributable as an easily identifiable single file for Parent clients; and
2. give a child profile a small optional boy/girl presentation preference that can seed a light first theme and solve occasional grammatical agreement such as Italian `bravo` / `brava`, including prerecorded Activity voices.

The implementation deliberately avoids turning boy/girl into a gameplay/content taxonomy.

## Decisions

### Activity file

- canonical parent-facing extension: `.greiaactivity`
- container: ordinary ZIP
- media type: `application/vnd.greia.activity+zip`
- root manifest: `activity.toml`
- Activity contents live directly at ZIP root; no wrapping folder
- extension/MIME are file-picker/routing hints only, never validation/trust
- the existing hardened `ActivityPackageService` remains authoritative for bounded archive inspection, Activity validation and atomic new install
- R10 replacement/update/rollback remains open; naming the container does not close R10

Normative explanation: `docs/architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md`.

### Child presentation

Persist a customization-side `neutral | boy | girl` presentation hint, separate from the core profile record and all security/progression state.

Derive localization agreement:

- neutral -> neutral
- boy -> masculine
- girl -> feminine

This value must never alter Activity eligibility, discovery, difficulty, permissions, progression, rewards or inferred interests.

Theme seed is initial-only:

- neutral -> normal Greia defaults, no redundant theme file
- boy -> `sky / turquoise / navy`
- girl -> `lavender / raspberry / plum`

A seed is written only if no saved theme preference exists. Changing presentation later never overwrites a chosen theme.

Normative explanation: `docs/adr/0032-profile-presentation-and-grammatical-agreement.md`.

### Localized text/audio

Localization bundles remain schema v1. Optional semantic variants use suffixes:

```text
feedback.correct
feedback.correct.masculine
feedback.correct.feminine
```

Resolution is **per locale**: requested variant first, then same-locale base, then next locale. This intentionally makes an Italian neutral fallback beat an English gendered variant.

Text and prerecorded audio for one cue must use the same variant.

Neutral wording is preferred when natural. Italian example:

```text
base      = Ottimo lavoro!
masculine = Bravo!
feminine  = Brava!
```

High-quality character variants are generated at authoring/build time with the same canonical speaker voice. The child selector changes the wording addressed to the child; it never changes which character voice speaks.

## Core Greia source added/changed

Added:

- `src/greia_platform/activity_package_format.py`
- `src/greia_platform/profile_presentation.py`
- `tests/test_activity_package_format.py`
- `tests/test_profile_presentation.py`
- `tests/test_localization_variants.py`
- `tests/test_activity_profile_presentation_api.py`
- `tests/test_profile_presentation_parent_protocol.py`
- `docs/adr/0032-profile-presentation-and-grammatical-agreement.md`
- `docs/architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md`
- this handover

Changed:

- `src/greia_platform/localization.py`
  - bounded optional semantic `variant=` lookup for text and audio
- `src/greia_platform/activity_api.py`
  - `get_profile_presentation()`
  - `get_profile_grammatical_gender()`
- `src/greia_launcher/child_shell.py`
  - injects only resolved presentation/grammatical semantic values into ordinary Activity launches
- `src/greia_parent/protocol.py`
  - declares profile-presentation resource
  - adds fail-closed `profiles.presentation` capability
- `src/greia_parent/update_api.py`
  - top-level composition advertises presentation capability
  - enriches profile payloads with presentation/grammar
  - GET/PUT profile presentation route
  - optional one-time theme seed
- `src/greia_parent/package_api.py`
  - imports canonical Activity package media type
- `skills/greia-activity-authoring/SKILL.md`
- `skills/greia-activity-authoring/VOICE_GENERATION.md`
- `docs/product/ACTIVITY_ECOSYSTEM_AND_DISTRIBUTION.md`

## Parent HTML candidate

Separate repository:

```text
frozenpepper/Greia-Parent-App-Html
```

Candidate branch:

```text
work/profile-presentation-activity-picker-20260823
```

Based on external main `cdea281a1848d1372a18822a559dc15494e749b0`.

Changes there:

- Parent API client GET/PUT profile presentation methods
- child editor `Style & wording` selector with Neutral/Boy/Girl
- child cards display the selected style when capability exists
- new/edit profile flow applies presentation after the core profile mutation and requests initial theme seeding
- Activity file picker accepts only `.greiaactivity` + vendor media type
- UI rejects generic `.zip` filenames before upload
- API client also rejects a named non-`.greiaactivity` file
- source tests added for presentation route/payload and package-extension handling

**Do not repin Greia's vendored/served Parent HTML source yet.** External AGENTS requires local `npm test` before source-complete claims, followed by the Greia vendoring/integrity/source tests and physical/loopback review appropriate to the Parent client. Those have not been executed in this connector-only session.

## Important integration defect already caught

The first Parent API draft attempted to advertise `profiles.presentation` only from `UpdateParentApiApplication`. `api_index_payload()` intentionally rejects unknown capability overrides, so that would have crashed index construction.

This was corrected properly in `src/greia_parent/protocol.py`: the resource/capability is protocol-defined, defaults fail-closed, and only the concrete top-level composition enables it.

Do not remove that fail-closed pattern.

## Verification state

Authored tests cover:

- presentation defaults and corrupt-state fallback
- boy/girl -> masculine/feminine derivation
- one-time theme seeding and non-overwrite
- `.greiaactivity` naming helpers/constants
- localized text/audio variant resolution and same-locale neutral fallback
- ordinary Activity launch-context API fallback
- Parent protocol resource and fail-closed capability declaration
- external Parent client route/body/filename behavior

**These newly added tests have not been executed in this session.** No hosted GitHub Actions execution was requested or used.

The pre-existing repository baseline at the branch base was already not fully green according to root `HANDOVER.md`: 1042 discovered tests with 5 known non-passing cases (four boot-diagnostic expectation drift plus one stale `test_child_shell_visual_context.py` signature expectation). Do not attribute those existing failures to this tranche without rerunning and comparing evidence.

## Required local verification before merge/release claims

Core checkout:

1. run the focused new tests:

```bash
python -m unittest \
  tests.test_activity_package_format \
  tests.test_profile_presentation \
  tests.test_localization_variants \
  tests.test_activity_profile_presentation_api \
  tests.test_profile_presentation_parent_protocol
```

2. run repository syntax/compile/source validation using the repository's current canonical commands;
3. run the broader relevant Parent/localization/launcher/package suites;
4. classify any failures against the documented pre-existing baseline rather than hiding them;
5. manually verify that a customized theme is never overwritten by changing presentation.

External Parent HTML checkout:

```bash
npm test
```

Then use the existing Greia Parent-client pin/integrity workflow; do not hand-edit generated integrity artifacts. Exercise the actual HTML UI against a local Greia API instance before considering a runtime pin.

## Useful manual acceptance scenarios

1. Existing child with no presentation file -> neutral; existing theme unchanged.
2. New child -> select Girl -> lavender/raspberry/plum seed appears if no theme existed.
3. Customize that theme manually -> change presentation to Boy -> customized theme remains untouched.
4. Italian Activity cue with all variants -> girl hears/sees `Brava!`, boy `Bravo!`, neutral `Ottimo lavoro!`.
5. Italian bundle with only neutral base -> every presentation gets the Italian neutral base, not another-language variant.
6. Parent Activity picker shows/selects `.greiaactivity`, not generic ZIP.
7. Rename malformed ZIP to `.greiaactivity` -> server still rejects it through canonical archive/Activity validation.
8. Valid `.greiaactivity` root has `activity.toml`; same package wrapped one directory too deep is rejected.

## Future follow-ups, not blockers for this source tranche

- Activity Simulator should eventually expose presentation/grammar alongside viewport, locale and interface-size simulation so authors can switch variants without editing state manually.
- Activity Designer/voice tooling can add a small “generate agreement set” authoring affordance that takes one semantic cue plus neutral/masculine/feminine localized texts and renders each with the same canonical voice. This should wrap the documented semantic convention, not invent another manifest format.
- R10 should add the official package export/validation command if one does not already exist in the relevant tranche; it should emit `.greiaactivity` and run normal Activity/package validation.
- If future languages need plural/case/select semantics beyond this small addressing requirement, design that extension deliberately rather than proliferating Activity-specific suffixes.
