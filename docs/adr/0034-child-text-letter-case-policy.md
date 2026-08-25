# ADR 0034 — Child text letter-case policy (default CAPITAL presentation)

Status: **Accepted and implemented**

Date: 2026-08-25

Extends: ADR 0012 (platform architecture constitution), ADR 0018 (lightweight UI), ADR 0028 (localization language context), ADR 0032 (profile presentation preferences)

## Context

Greia's target children are pre-readers, and children learn CAPITAL letters before lowercase letterforms. Child-facing UI text (Activity names, Collection/Category labels, instructions, buttons, feedback) has historically mixed natural-case localized strings with hand-capitalized literals. That inconsistency also meant no single place governed the presentation of text for the youngest children.

The product direction is:

- present child-facing UI words in CAPITAL letters by default, because those are the letterforms children learn and recognize first;
- let a parent choose normal text per child in the Parent App, for example for older children;
- keep the policy purely presentational so it can never become gameplay, difficulty, permission, progression or storage semantics;
- preserve child-authored content (for example what a child writes in the Writing Activity) exactly as authored.

## Decision

### 1. One platform-owned presentation policy

`greia_platform/child_text.py` owns the bounded letter-case policy:

- `ChildTextCase.UPPERCASE` (platform default) and `ChildTextCase.NORMAL`;
- `display_text()` applies the resolved policy to one display string;
- the policy is resolved once per child process from the launch environment and can be explicitly pinned in tests.

Uppercasing is Unicode-aware (`str.upper`), so accented locales such as Italian render correctly.

### 2. Profile preference and launch plumbing

`ChildProfile.uppercase_text` (default `true`) persists in the profile registry. Legacy registries without the field parse as `true`, so no migration is required and the platform default applies until a parent chooses otherwise.

The Shell writes the resolved value into the Activity launch environment as `GREIA_PROFILE_UPPERCASE=uppercase|normal`, mirroring the other profile presentation hints. Activities read it through `get_profile_uppercase_text()`; ordinary Activities normally do not need to call it because the localization layer already applies the policy.

### 3. Localization resolves display text under the policy

`LocalizedResources.text()` applies the policy to its resolved display string. Semantic keys, variant IDs and audio cue lookup are never case-transformed. This makes every localized Activity string compliant without per-Activity edits.

Activities that render package-local literal strings must route them through `display_text(...)` (or `get_profile_uppercase_text()`) instead of hand-capitalizing or leaving mixed case.

### 4. Shell chrome applies the same policy

The Shell applies the active profile's policy at its child-facing render chokepoints: Activity card titles, the full-title disclosure, Collection/Category/discovery-group labels, profile picker names, the launch badge, and achievement library/badge copy. Parent-facing surfaces (Parent App, launcher parent panel) are adult surfaces and deliberately bypass the policy.

### 5. Child-authored content is exempt

Text the child creates (Writing documents, saved names the child typed, free drawing content) is never routed through the policy and is preserved exactly as authored. `GreiaTypography.render()` deliberately stays case-neutral for this reason.

### 6. Launcher card scale

Launcher Activity cards, Collection portals, sub-Collection cards and profile tiles use a +4% larger reference cap (Activity tiles 218 px, Collection portals 141 px, sub-Collection portals 177 px, profile tiles 213 px at the reference layout) while label font sizes stay unchanged. Two-line Activity titles must fit inside the card label band; the shared label renderer compresses leading rather than letting glyphs cross the card border.

## Consequences

- Young children see one consistent, recognizable letterform world by default.
- Parents keep an explicit, per-child off switch through the Parent App and Parent API (`uppercase_text` on create/update, exposed in `public_dict`).
- The policy is descriptive only: Activities must not derive eligibility, difficulty, rewards, permissions or stored data from it.
- New child-facing literals in Activities must go through `display_text`; reviewers should reject hand-capitalized or mixed-case child-facing strings that bypass the policy.
- Child-authored text keeps its authored case; spell-check-like or literacy Activities must not "correct" the policy into content rewriting.

## Evidence

- Source: unit suites `tests/test_child_text_case.py`, `tests/test_localization*.py`, `tests/test_launcher_title_and_icon_contract.py`; full `make verify`.
- Simulator (1024×600, isolated state): launcher Collection Home and Activity grid present CAPITAL labels and titles with two-line titles inside card borders; L'Acquario Magico toolbar copy uppercase; Painting status copy uppercase; a parent-disabled profile (`uppercase_text=false`) presents the same Shell in normal case; launch/survival/interaction/Home-return gate passed for both profiles.
