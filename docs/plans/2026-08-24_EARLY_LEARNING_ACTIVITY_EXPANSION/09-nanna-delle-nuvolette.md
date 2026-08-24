# Session 09 — Nanna delle Nuvolette: calm age-three play

**Provider calls:** forbidden; local reviewed art only
**Prerequisite:** Sessions 00–08 accepted and committed
**Commit:** `feat(activity): add Nanna delle Nuvolette`

## Outcome

`org.greia.nanna-delle-nuvolette` gives a three-year-old a calm, language-light bedtime scene in which three cloud friends receive a blanket and one to three stars before falling asleep. There is no score, wrong answer, timer, forced finish, or fullscreen victory.

## Preconditions

- Pull current `main`; verify Sessions 00–08 handoff packets and cumulative gate.
- Read the Activity core/engineering/achievement/discovery/visual routes and inspect `cucciolo_mio` and `acquario_magico` so this remains a distinct sensory composition loop rather than another care schedule.

## Allowed files

```text
activities/nanna_delle_nuvolette/**
tests/test_activity_nanna_delle_nuvolette.py
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

## Forbidden changes

- No score, correctness state, countdown, lives, streak, rapid flashing, mandatory audio, text instruction, profile-age lookup, or global bedtime policy.
- No duplicated pet-care schedule, profile mutation, fullscreen terminal overlay, or Activity-owned Home/Back control.

## Evidence and source decisions

The age-three lane follows the Head Start 36–48 month emphasis on small, visible actions and the repository's child-first, language-neutral navigation contract. The educational value is gentle sequencing, choice, cause/effect, and small-set placement; it is intentionally not a literacy or assessment task.

## Exact implementation

1. Manifest: `org.greia.nanna-delle-nuvolette`, title key `activity.nanna_delle_nuvolette.title`; `it,en`; collections `play,explore`; tags `care,nature`; education `sequencing,cause_and_effect,color_shape_matching`; difficulty 1, age min 3 with no max, adaptive false; pointer input; required `display,pointer`, optional `touch,audio.basic`; event `cloud.rest_completed` kind `completion`; storage schema 1.
2. Create thin `main.py` plus `cloud_model.py`, `cloud_services.py`, `cloud_audio.py`, `cloud_art.py`, `cloud_renderer.py`, and `cloud_app.py`. Model `CloudFriend(id,position,blanket_id,star_ids,asleep)`, six immutable blanket choices, nine reusable star tokens, and `NightScene` containing exactly three cloud friends.
3. A cloud becomes ready to sleep only after it has one blanket and at least one star. Dragging any blanket onto an awake cloud is accepted and replaces its prior blanket; dragging a star attaches it up to a maximum of three. Tap/Space on a ready cloud starts a 0.8-second yawn-to-sleep transition. An early tap makes the cloud point to the missing blanket or star for 1.2 seconds; it never marks an error.
4. Provide pointer drag plus semantic focus navigation. Focus order is the three clouds, six blanket cards, star basket, moon chime, and `new_night`. Space picks/drops the focused object; Escape cancels a held object. Touch follows the pointer semantic path.
5. When all three clouds sleep, emit `cloud.rest_completed` once with `{night_id, cloud_count: 3, star_count}` and keep the scene alive with a bounded six-sprite twinkle cycle. A large moon control starts a new night only after explicit activation. Leaving with Home before all sleep is a valid outcome and emits nothing.
6. Persist only `nanna_delle_nuvolette.preferences.v1 = {blanket_ids: [three known IDs]}` after a completed night. Unknown IDs and malformed state fall back to the six-choice default. Do not persist timing or partial play.
7. Optional audio consists of one soft nonverbal chime, one yawn, and one rustle with at most two simultaneous channels. Missing output keeps every cue visible through motion and expression.
8. Reuse `character.momo` as a small sleepy guide and adapt the reviewed moonbeam/contact-shadow references. Create original cloud faces, blanket patterns, star, moon, basket, background, and distinct launcher icon. Bake opaque background layers; cache every scaled sprite; keep twinkle state to six reusable sprites.
9. Render at 1024×600 logical coordinates. Cloud and tray targets are at least 88×88; the star basket dispenses semantic tokens without allocating a new image. Static settled scenes redraw only on invalidation; transition animation runs near 30 fps and stops after 0.8 seconds.

## Tests

- Exactly three clouds, six blanket IDs, nine star placements, one-blanket replacement, three-star cap, and readiness invariant.
- Early tap is neutral; all-sleep completion emits once; early Home emits nothing; new-night reset is explicit.
- Storage writes only after completion, accepts only known IDs, and recovers from malformed data.
- Pointer/focus/Space equivalence, Escape cancellation, optional-audio fail-soft, protected-region rejection, cache bounds, and static-idle invalidation.
- Manifest audience/input/event parity, localization completeness, icon uniqueness, READY-once and STOP handling.

## Local gate

```bash
find activities/nanna_delle_nuvolette -type d -name __pycache__ -prune -exec rm -rf {} +
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_nanna_delle_nuvolette -v
PYTHONPATH=src:tools python3 tools/validate_activity.py activities/nanna_delle_nuvolette
```

Expected: tests and validation exit 0; no bytecode remains.

## Cumulative gate

```bash
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_luci_di_momo tests.test_activity_casa_del_dieci tests.test_activity_bottega_delle_misure tests.test_activity_specchi_magici tests.test_activity_festa_delle_rime tests.test_activity_officina_dei_suoni tests.test_activity_posta_di_leo tests.test_activity_tre_carte_una_storia tests.test_activity_nanna_delle_nuvolette tests.test_activity_contract tests.test_activity_audience_manifest tests.test_first_party_activity_audience_metadata tests.test_first_party_activity_readiness tests.test_core_activity_system_safe_ui tests.test_activity_ui tests.test_activity_viewport tests.test_localization tests.test_typography_emoji -v
```

Expected: exit 0 with nine portfolio suites and named contracts green.

## Stop conditions

- The visible loop requires reading, treats a free choice as wrong, or cannot be completed with one-pointer/one-button semantics.
- The implementation introduces persistent animation, unbounded particles, or more than three simultaneous audio channels.

## Handoff

Return the standard packet plus a state-transition table, neutral-feedback proof, all-sleep idempotency fixture, palette/art hashes, cache/channel bounds, accessibility matrix, and SOURCE label.
