# Greia launcher: product, performance and Activity creation review

**Date:** 2026-09-08  
**Reviewed source:** `225102f022147261cee209529ff442ca7a3070c5`, `main`  
**Scope:** Python child Shell/launcher, navigation, resource behavior, characters, prerecorded voice, and the parent-to-Activity creation journey.  
**Status:** advisory review; recommendations are **PROPOSED**, not accepted architecture or a competing implementation plan. No runtime changes or device deployment were made.

## 1. Overall opinion

**Yes: the project makes sense, and Python/Pygame is a defensible foundation for it.** Greia has a coherent reason to exist: give a child a computer they can confidently own and explore, give a parent control without requiring Linux administration, and make useful older hardware worth keeping.

The strongest idea is the combination of a consistent appliance surface with an open Activity model. Drawing, writing, games, music and exploration can share the same profile, save ownership, controls and reliable route Home. That consistency is more valuable than another collection of educational games. The offline requirement and absence of dependency installation on the child machine support the product rather than merely restricting it.

The characters and voices also make sense. They can turn a technically constrained machine into a recognizable, welcoming place. Prerecording speech and producing artwork on a capable authoring workstation is exactly the right division of work. An ancient netbook can play a short recording and blit a beautiful prepared image; it does not need to generate either.

**The greatest risk is the amount of product and engineering scope being carried at once.** Greia is simultaneously an OS appliance, runtime/sandbox, installer/updater, parent-management system, educational content library, character universe and authoring platform. Each is reasonable separately. Together they can make a simple family experience expensive to maintain and difficult to finish.

I would continue the project, retain its core architecture, and prioritize dependable daily use and one genuinely easy creation path. I would resist adding more platform concepts or Activities merely to demonstrate versatility. Forty-one Activities already provide enough breadth to test whether the experience works.

A useful product test is: **Can a parent make one personally meaningful Activity, watch their child use it without repeated help, and trust that the child's creations will still be there next week?** That is a stronger milestone than a larger catalogue or more elaborate animation.

## 2. Evidence and limits

This is a source-grounded product/architecture review, with a small amount of executed verification and inspection of three current character PNGs. It is not a full line-by-line audit of every launcher module or every Activity.

Reviewed paths include the launcher composition, main and rich presentation loops, child Shell, policy projection, catalogue refresh, spoken-label controller, shared UI rendering, navigation geometry and relevant architecture/product/authoring documents. Sources below are repository-relative links so the report remains useful on GitHub.

No new Acer/Pi session, current launcher screenshot, parent-browser usability session, child observation or listening review was performed. The available `python3` was Homebrew Python 3.14 and lacked Pygame and pytest. No dependencies were installed for this review.

### Fresh checks

| Check | Result and interpretation |
|---|---|
| Git state and `git fetch origin main` | Clean `main`, aligned with `origin/main` at the reviewed SHA before report writing. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/audit_launcher_spoken_labels.py` | **FAIL:** 41 Activities, 82 title/locale combinations, 80 complete; `bosco_numeri/it` and `/en` missing. Collection labels **38/38**. |
| Navigation geometry unittest module | **14 passed, 2 dependency errors** out of 16. Both errors are missing Pygame; the entire module did not pass. |
| Spoken-label controller through unittest discovery | Zero tests discovered; these are pytest functions. This provides no passing evidence. |
| Attempted pytest controller/geometry run | Could not start: pytest absent. |
| Isolated title-resolution cache probe | Reproduced stale negative result: resolve absent label → add a valid localized mapping → resolver still returns `None` → clear its cache → resolver returns `title.wav`. Temporary fixture only; this was not an installed-package update test. |
| Character pixels | Inspected `leo_neutral.png`, `momo_happy.png`, `dani_neutral.png` from the runtime library. This establishes only an asset-level visual sample. |

The cache fixture used a temporary root and a manifest-shaped object, wrote a schema-v1 locale JSON with `strings.activity.title` and an `audio.activity.title` path/caption mapping, and compared resolution before/after `_TITLE_AUDIO_CACHE.clear()`. Dummy file bytes were sufficient because this checks path resolution, not audio decoding or playback.

`make verify` was not run. There is no claim of a fresh full-suite PASS or fresh frame-time/RSS measurement.

### Current versus historical state

The active implementation plan explicitly records **R7 COMPLETE on 2026-09-05** and advances the primary blocking phase to **R8**. This report respects that recorded disposition. It does not independently recertify the physical tests or assume subsequent source changes inherit their evidence.

The September 7 handover also describes ongoing boot/composition work and a deployment boundary. That work should be reconciled through its existing authority, not displaced by this report. Earlier notes saying R7 remained open are historical for phase status.

Historical performance evidence is useful context: the [performance manual](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md) records the August 23 Acer hover improvement from approximately 190 ms full-scene work to 26.6 ms hover frames, steady cached frames around 3.34 ms, and launcher RSS around 153 MB. **These are dated measurements, not measurements of the reviewed September 7 source.**

## 3. What is already good and should be preserved

| Existing decision or mechanism | Why it fits Greia |
|---|---|
| Activity as the universal abstraction | Children and parents do not need to care which runtime implements an experience. |
| Platform-owned Home and optional Back | A learned escape route is particularly important when an Activity freezes or confuses a child. |
| Separate profile-scoped data | A shared family machine can still feel personally owned. |
| Writing and painting as core experiences | Greia offers creation and expression, not only correct-answer exercises. |
| One curated Python environment | Avoids dependency drift, duplicated runtimes and installation work on weak hardware. |
| Runtime-neutral input profiles | Extends versatility without requiring each author to understand controller hardware. |
| Prepared visual assets and prerecorded speech | Rich output can be inexpensive at runtime. |
| Collection-first navigation and bounded pages | The child is not confronted with a wall of 41 icons. |
| Parent visibility/age policy before presentation | Adaptive presentation does not become a route around parent authority. |
| Real-service Simulator | Provides a useful integration boundary for authors while keeping physical evidence distinct. |

The normal rich launcher already coalesces pointer motion, caches scene/card work, redraws on invalidation, and uses adaptive idle sleeps. Those are strengths, not missing features to propose again. The lower-level base launcher has a separate continuous redraw loop; it should not be confused with the normal production Shell path.

The architecture also recognizes that an Activity should report facts while the platform owns rewards, saves and permission decisions. This substantially improves the chances of an open ecosystem remaining coherent.

## 4. Concrete findings in the current source

### F1 — Two missing spoken launcher titles

**Priority: high for catalogue completeness. Evidence: executed audit and locale source.**

The title audit reports missing Italian and English mappings for `bosco_numeri`. Its Italian locale has the visible title “Il Bosco dei Numeri di Tito” but an empty `audio` object. This means the Shell's spoken-title discovery feature is inconsistent for this Activity; it does not establish that all of its internal audio is absent.

**Suggestion:** produce/review the two title clips through the existing voice engine, map the existing semantic cue, and repeat the catalogue audit and spoken-label interaction checks. Do not change the audit to tolerate a missing first-party title. A pre-reader should not encounter an inexplicably silent tile among speaking peers.

Owners: [spoken-label audit](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/tools/audit_launcher_spoken_labels.py), [Italian bundle](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/activities/bosco_numeri/locales/it.json), [English bundle](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/activities/bosco_numeri/locales/en.json), [voice authoring router](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/skills/greia-voice-production/SKILL.md).

### F2 — Spoken-title resolution can retain stale content

**Priority: medium. Evidence: reproduced resolver behavior; playback impact inferred from source.**

In [spoken_labels.py](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/src/greia_launcher/spoken_labels.py), `_TITLE_AUDIO_CACHE` is keyed by resolved Activity root and locale and caches missing results too. The player caches decoded sounds by resolved file path. The catalogue rescan clears pointer state and visual caches but does not visibly invalidate these audio caches.

The isolated probe confirms that adding a missing mapping under an already-cached root does not repair resolution until eviction, process restart or explicit clearing. Similarly, if an update replaces audio bytes at the same resolved path, the player's key alone cannot distinguish the revision. That second scenario was not exercised with a real mixer or package installation. Versioned roots may naturally avoid it; the update layout must be checked before deciding its production reach.

**Suggestion:** make the existing controller own an explicit catalogue-revision invalidation path. Clear affected resolution and decoded-sound entries after an accepted catalogue replacement; include locale/package revision in identity where needed. Prefer this to filesystem hashing on every pointer movement. Preserve fail-silent optional playback and stop old speech when changing contexts.

Acceptance examples: missing→available label at a reused root, same-path changed clip, Italian→English focus, removal while focused, and unchanged catalogue without repeated decoding. Include at least one real accepted-package update path rather than relying entirely on fake manifests.

### F3 — The Shell's extension structure is becoming difficult to reason about

**Priority: medium-high for maintainability. Evidence: source structure, not a claim of a present crash.**

The launcher contains approximately **18,000 lines across 46 Python files**. `main.py` has 2,010 lines, `presentation.py` 2,185 and `parent_panel.py` 1,579 at this snapshot. Size alone does not prove poor design, but the central `GreiaChildShell` inherits nine mixins plus `GreiaLauncherPresentation`. Rendering, navigation, policy, achievements and profile behavior rely on inherited state and cooperative overrides.

There are also separate base/rich event loops. This increases the chance that resize, input cleanup, narration, pacing or failure handling is repaired in one path and missed in another. The [engineering foundations](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/docs/engineering/ENGINEERING_FOUNDATIONS.md) explicitly prefer composition and discourage mixin webs; this is a real tension with that goal.

**Suggestion:** extract collaborators only when touching a responsibility: navigation state, catalogue snapshot application, speech policy and screen rendering are useful candidates. Retain the existing service owners and trusted supervisor. Move one responsibility at a time behind a narrow typed seam and test both normal and emergency compositions. Do not introduce a universal UI framework or rewrite the launcher wholesale.

A successful refactor should make “who owns selected Activity, page, focus and launch origin?” answerable from one small object, and reduce the number of classes requiring simultaneous changes for a new screen behavior.

Owners: [child_shell.py](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/src/greia_launcher/child_shell.py), [presentation.py](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/src/greia_launcher/presentation.py), [main.py](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/src/greia_launcher/main.py), [trusted_presentation.py](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/src/greia_launcher/trusted_presentation.py).

### F4 — Catalogue changes can perform substantial work on the interactive thread

**Priority: measure before optimization. Evidence: execution-path inspection.**

The Shell invokes rescanning from the UI loop, at a base two-second cadence. `ActivityRegistry.discovery_token()` scans manifest paths and metadata; it is not a recursive content hash every frame. When the token changes, rich presentation performs discovery/validation and rebuilds runtime services before publishing the new catalogue. Tree validation includes recursive file inspection.

This correctly preserves authority before exposing new tiles, but a large package update or slow storage can make the changed-catalogue path noticeable. This review did not measure a current stall.

**Suggestion:** instrument unchanged-token cost and changed-catalogue latency separately on Acer. If the changed path is expensive, reuse the existing preparation/snapshot approach to prepare a bounded candidate away from drawing and apply it atomically. Revalidate the relevant identity/version before publication. An old visible snapshot must not make a newly forbidden Activity launchable; launch-time authority and policy updates remain mandatory.

Avoid a new persistent daemon or recursive polling watcher by default. Parent/package transaction notifications plus a bounded reconciliation path may be enough. Do not “speed up” discovery by trusting arbitrary mutable package bytes.

Owners: [registry](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/src/greia_platform/activities.py), [bootstrap](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/src/greia_launcher/bootstrap.py), [presentation rescan](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/src/greia_launcher/presentation.py), [policy projection](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/src/greia_launcher/activity_policy_presentation.py).

### F5 — Bounded entry counts should become an aggregate memory budget

**Priority: medium; proposed measurement work.**

The rich presentation has bounded tile, backdrop and disclosure caches; other caches use dictionaries and clear at selected lifecycle boundaries. Entry bounds are useful, but an entry can be a small glyph or a screen-sized surface. Sixteen 1024×600 surfaces at four bytes per pixel represent about **37.5 MiB of pixel storage** before object overhead. This is an illustrative bound, not measured current cache occupancy.

**Suggestion:** extend existing cache instrumentation with retained bytes/pixels, high-water marks and hit/miss/eviction counts. Audit aggregate residency across Shell, Activity, trusted chrome, audio and parent services. Review resize/profile/theme transitions as well as steady state. Use a single deliberate budget for large backdrops and ensure old profile decoration is reclaimable.

Do not reduce cache capacity blindly: the existing performance history shows undersized caches can thrash. Measure the actual working set before choosing limits.

### F6 — Living documentation has materially stale status statements

**Priority: high for contributor/agent efficiency. Evidence: conflicting current documents.**

The [launcher interaction guide](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md) still lists adaptive sub-Collections, age fields and Parent visibility policy as unimplemented, while current source and `HANDOVER.md` describe their implementation. The [local testing router](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/docs/testing/LOCAL_AGENT_START_HERE.md) still names R7 as the primary blocking phase, while the active plan and handover advance to R8. The canonical cast document's older pending runtime statements also need reconciliation with later visual progress and existing renditions.

**Suggestion:** correct derived current-status sections from their owning source/plan evidence, preserve dated history, and keep the handover genuinely short. Do not erase unresolved per-feature acceptance gates merely because the overall phase advanced. The report records these inconsistencies; it does not silently edit other workstreams' authority.

This directly affects simplicity for creators: a strong API surrounded by contradictory instructions is still difficult to use.

## 5. Improving the child's experience

### Keep spatial memory stable

The primary Create/Play/Learn/Explore/My Greia vocabulary is sensible, but those concepts overlap. An Activity appearing in several Collections is helpful; it should still have one identity and one save state.

Adaptive grouping should help a growing catalogue without moving familiar destinations unexpectedly. Keep top-level positions stable and avoid rearranging a visible page during interaction. Parent policy removal must take effect even when that changes a page; preserve the nearest safe focus rather than targeting an unrelated replacement tile.

A proposed small “my familiar Activities” area could hold three or four parent/child-approved favorites. Do not let automatic recency reorder the main grid. If a Continue shortcut is added, distinguish genuine resumable work from simply reopening the last Activity, and apply the effective per-child visibility policy to it.

### Make the first action obvious and recovery ordinary

The next quality improvement should be an observation pass over representative Activities: drawing, writing, one pointer puzzle, one directional game and one spoken-instruction task. Check whether a child can find the first meaningful action, recover from a mistake, repeat an instruction and return Home.

Prefer a tiny demonstration followed by immediate play. Spoken guidance should reinforce an understandable scene. Timed instructions, tiny hit targets or a long tutorial should not be the price of a more sophisticated Activity.

Keep Home and Back behavior distinct: Home returns to root; Back returns to the launch origin after ending the Activity. Preserve category/page/selection for Back where safe. Avoid adding a third ambiguous global exit icon.

### Quiet is a feature

Offer a small parent-controlled presentation choice such as reduced motion and quieter optional narration, composed from existing preferences/services where possible. A quiet setting must not indiscriminately remove the required spoken task in a pre-reader language Activity. Treat navigation labels, essential instructions, optional praise, music and sound effects as different purposes.

The current pointer label dwell is **160 ms** and keyboard/controller announcements are immediate on real changes. Those are implementation values, not evidence of optimal child behavior. Compare the current behavior with a somewhat longer pointer dwell, for example 250–350 ms, during actual exploration. Measure speech cutoffs, successful identification and annoyance; do not expose a millisecond settings slider to families.

Provide a deliberate repeat action where speech carries an instruction. Touch interaction cannot depend on hover. Meaningful cues should also have visual reinforcement, and color should not be the sole carrier of a distinction.

### Let creations carry the value

Make reopening a drawing or piece of writing reliable and prominent. A bounded gallery can present “my things” without exposing files. Future parent export/backup should make preserving those creations easy. Do not add automatic scores or medals to every creative action; intrinsic satisfaction and a recognizable saved result often provide enough feedback.

These are design recommendations, not claims that the current children prefer them. NAEYC's guidance supports intentional, active and creative technology use and adult/child engagement; it does not validate Greia or a particular interface. See [NAEYC's position statement](https://www.naeyc.org/resources/topics/technology-and-media-0/technology-and-interactive-media-position-statement) and [preschool/kindergarten guidance](https://www.naeyc.org/resources/topics/technology-and-media/preschoolers-and-kindergartners).

## 6. Characters, artwork and voice

### Keep the cast, use it deliberately

The six-character affinities are coherent: Lilli for creativity, Leo for language/knowledge, Flash for action, Dani for logic, Tito for exploration and Momo for emotion/music/playfulness. They should remain flexible affinities rather than six separate navigation systems children must memorize.

The three inspected runtime assets have strong simple silhouettes, restrained facial detail and readable expressions. Leo's glasses, Dani's robot body and Momo's purple round shape give useful identity cues. I would retain this compact visual grammar. This sample does not establish consistency of all expressions, legibility at every rendered size, or the quality of the current Shell composition.

Give a character a job: point, demonstrate, explain briefly, react meaningfully or offer optional curiosity. Usually one lead character is enough. Avoid a permanently animated audience of mascots around the playfield. A drawing Activity can be quiet for long stretches; the character does not need to justify its presence continuously.

Introduce the cast gradually and optionally. The accepted introductions do not need to become a boot sequence. A small optional “meet the characters” destination is more compatible with fast daily use than six mandatory introductions.

### Prerecorded speech is the correct runtime choice

The shared library documents **180 reactions plus 12 introductions**, accepted as v0.2. Accepted recording bytes and a working shared runtime resolver are separate milestones. A source search did not locate a shared-utterance runtime consumer under the corresponding semantic terms in `src/greia_platform`; do not assume Activity authors can already call a complete shared reaction API because the clips exist.

Finish one narrow semantic runtime consumption path when the owning workstream permits it, then migrate a small number of real consumers. This can reduce repeated generic recordings and authoring effort. Do not duplicate shared WAVs into every package or invent an unrestricted dialogue engine.

Keep exact phonemes, letter sounds and pronunciation targets separate from expressive character speech. A charming delivery is not evidence of educational phonetic correctness. I did not listen to the audio in this review and cannot judge the actual voices, pronunciation or small-speaker intelligibility.

### Resolve feedback before playing audio

The authoring guidance already recognizes the final-item collision: collection sound, spoken answer, victory music and praise can fire together. Apply that rule consistently. Resolve the state transition first, then choose one bounded sequence. Required instruction/phonetic content should not be cut off by optional congratulations.

Use specificity sparingly: “You found three” may be useful when it describes the actual learning action; generic applause on every click becomes noise. Never make continued play depend on watching a celebration. A quiet, static terminal state also costs less CPU.

Owners: [presenter guidance](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md), [feedback orchestration](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/skills/greia-activity-authoring/FEEDBACK_ORCHESTRATION.md), [shared utterances](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md), [cast](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/docs/design/GREIA_CANONICAL_CAST_SYSTEM.md).

## 7. Making Activity creation simple for parents

### The current contract is contributor-friendly more than ordinary-parent-friendly

The skill, manifest, localization, validators, Simulator, storage/lifecycle interfaces and voice engine form a strong engineering toolkit. They do not by themselves make creating an Activity simple for a parent who does not program. Such a parent should not need to understand trust classes, semantic event schemas, renderer caches or a model provider.

The reviewed authoring route is documentation → author/agent writes code → validate → simulate → package. I did not find an obvious integrated parent-facing Activity creation wizard in the inspected tool/Simulator entry points. The separately maintained Parent browser source was not audited here, so this is a scoped authoring-gap assessment, not proof that no external prototype exists.

### Start with three guided creation recipes

I would prioritize a small authoring experience on the parent's capable machine, leaving the child appliance lightweight:

| Recipe | Parent provides | Greia supplies |
|---|---|---|
| Picture matching | A small set of pictures and optional spoken names | Layout, interaction, retries, localization slots, saved settings and bounded feedback. |
| Personal picture story | A few pictures, short captions and recordings | Page navigation, narration/repeat, safe image sizing and resume state. |
| Sorting/counting toy | Objects, a few groups or number targets, simple difficulty choice | The mechanic, large targets, instruction timing and controlled progression facts. |

Choose recipes from existing Activities and shared controls after checking their suitability for reuse. These are proposed content editors over vetted mechanics, not another arbitrary-code runtime or a universal visual programming language.

The parent journey should be short:

1. Choose what the child will do and the intended age/language.
2. Supply a few personal pictures, words or recordings.
3. Try the exact Activity preview with one clear “try again” path.
4. Review permissions and send/install it through the normal package service.

Validation should explain the repair in family language: “This instruction needs a recording” or “This picture is too large; resize it.” Technical detail can remain available to an advanced author.

Parents' own prerecorded voices can be valuable for personal content. Keep them distinct from canonical cast voices, normalize/validate the assets at authoring time, and preserve privacy through normal package/data rules. Do not imply that a parent needs a voice model to create anything.

### Keep an advanced route

Python authors and agents should retain access to the full Activity contract. Provide one maintained minimal example and a few tested recipe examples with reusable collaborators, rather than encouraging copying a large first-party Activity.

An agent-assisted “describe an Activity” path should produce an ordinary inspectable package, required checks, and a parent preview. Generated code must not gain weaker trust or bypass acceptance. A parent's one-sentence request is not evidence that the resulting teaching mechanic or audio is correct.

Before expanding the editor, observe several parents trying one recipe with no developer help. Proposed practical measures: completion without assistance, time to first playable preview, number of unexplained validation failures and ability to edit it again a week later. These are usability measures, not learning-outcome claims.

## 8. Performance strategy for the ancient hardware floor

### Retain Python/Pygame and optimize the actual costs

A rewrite in another language is not justified by this review. Existing measurements point to large alpha blends, repeated composition and work scheduling, not proof that Python dispatch is the main constraint. Pygame delegates important pixel/audio operations to native implementations.

Keep prepared opaque backdrops, converted image surfaces, bounded transforms and direct Activity rendering. Do not add full-frame transport/copies merely to make an abstraction look uniform. The official [Pygame surface documentation](https://www.pygame.org/docs/ref/surface.html) explains format conversion; [display documentation](https://www.pygame.org/docs/ref/display.html) distinguishes whole-display presentation and partial software updates. Partial updates are an experiment to profile on the selected backend, not an automatic improvement over Greia's existing cached full-screen blit.

### Measure the family-visible phases

| Phase | Measure | Decision it informs |
|---|---|---|
| Power-on to first useful screen | First visible frame and first accepted interaction separately | Whether intro/validation scheduling hides or adds waiting. |
| Quiet profile picker / Home / settings | CPU, wake frequency, memory, unexpected redraws | Whether static UI really settles. |
| Pointer sweep and controller navigation | Input-to-visible feedback, speech start, p50/p95/p99 frame times | Whether discovery feels responsive under real input. |
| First/cached Activity launch | First useful Activity frame, process/memory peak | Whether loading and assets fit the floor. |
| Catalogue update while navigating | Longest UI stall, policy visibility/launch correctness | Whether background preparation is warranted. |
| Repeated Activity/Home cycles | Total memory trend, leaked processes/handles, return latency | Whether daily use remains stable. |
| Profile/theme/locale changes | Retained cache bytes, stale pixels and speech | Whether bounds and invalidation work together. |

Use the existing [draw profiler](https://github.com/frozenpepper/Greia/blob/225102f022147261cee209529ff442ca7a3070c5/tools/profile_launcher_draw.py) for diagnostic phases and the current physical procedure for acceptance. Add counters to existing owners instead of a new monitoring service. Record device facts and exact deployed source identity; include enough repetitions to distinguish noise from a regression.

The existing approximate 30 fps animation and ≤50 ms added input-latency guidance are useful goals. Near-zero static redraw is a desirable property. Do not declare a newly invented universal boot/launch/RSS target without baseline measurement. Establish separate budgets for Shell residency, Activity peak and whole-system pressure, including compositor/chrome, services, filesystem cache and swap behavior.

### Storage: distinguish source trees from installed cost

A fresh inventory of Git-tracked working-copy file sizes found:

| Tree | Files | MiB |
|---|---:|---:|
| `activities/` | 2,710 | 102.18 |
| `assets/audio/` | 394 | 17.57 |
| `assets/visual/runtime/` | 62 | 1.05 |
| `assets/visual/` including runtime | 661 | 3.68 |
| `src/greia_launcher/` | 46 | 0.67 |

These are overlapping categories where indicated and **not installed-image measurements**. They exclude system dependencies and untracked evidence, and may include authoring-only package material. They should not be summed into a claimed C0 image size.

Audio is a manageable existing asset category, but multilingual catalogue growth should be budgeted. Keep short cues cheap to decode; consider compression for longer narration only after measuring decoder cost and compatibility on the floor. Verify the installed composition excludes unused masters, review bundles, tools, recordings that are not selected runtime assets, and unnecessary locale content where the accepted language-pack design permits it.

For versatility, capability-gate genuinely expensive future runtimes or effects. More powerful hardware can improve optional presentation while preserving the same controls and content semantics. Do not make the Pi version a different product or force the Acer to load a browser engine for the Shell.

## 9. Parent confidence and operational simplicity

Parents need understandable outcomes more than architectural options: create a child profile, select suitable Activities, preserve creations, install something, and recover when it fails. Age suitability and difficulty should stay separate internally, while presets cover ordinary choices and explicit overrides remain available.

The existing on-device S+T hold is a reasonable guarded maintenance entry, but an ordinary parent should discover it through a short setup/recovery card or help flow. Routine use should not depend on remembering a secret chord or enabling SSH.

Prefer “This Activity needs attention; your creations are safe” plus an actionable parent detail over exposing Linux errors. Do not promise data safety when a failure actually prevents that conclusion. A bounded diagnostic export can help support without uploading child recordings or content by default.

Make backup/export and recovery trustworthy before treating the system as an ordinary-family release. The repository already distinguishes public-source readiness from family-release readiness; preserve that distinction. This is not a new security audit or an assessment of the external Parent app's current usability.

## 10. Suggested priority order

This is a recommendation order for the owner to consider within the active plan and existing boot/R8 work. It authorizes no implementation and does not reopen accepted phase gates.

| Order | Work | Expected benefit | Completion evidence |
|---|---|---|---|
| 1 | Complete Bosco launcher speech and repair audio-cache revision handling | Removes concrete inconsistency and stale presentation | Fresh coverage audit, accepted clips, cache transition checks, real update scenario. |
| 2 | Reconcile current guides with source/plan status | Reduces wasted work and incorrect creator guidance | Named current-status sections agree; historical evidence retained. |
| 3 | Measure current installed Shell phases and aggregate memory | Finds the largest actual performance cost | Exact-SHA/device measurements for the table above. |
| 4 | Observe child discovery, first action, repeat and Home/Back | Reveals confusion that unit tests cannot show | Recorded observation notes; no educational-efficacy overclaim. |
| 5 | Deliver one guided parent creation recipe | Tests the project's most distinctive promise | Parent creates, previews, installs, edits and reopens a real Activity. |
| 6 | Narrow incremental Shell composition refactor | Makes future changes safer and easier | Normal/fallback contract checks, pixel comparison and unchanged hardware behavior where affected. |
| 7 | Finish useful shared character runtime consumption | Reduces duplicated author work and inconsistent feedback | Accepted semantic library used by a few real Activities with bounded scheduling. |
| Later | Additional templates, approved Continue/favorites and optional richer runtimes | Broader use without enlarging everyday complexity | Evidence that simpler options do not already meet the need. |

## 11. What I would avoid

- Replacing the Shell with a web/Electron-style stack without a measured problem that justifies the cost.
- Rewriting Python infrastructure to chase performance before profiling.
- Expanding the cast or adding compulsory voice/animation to every screen.
- Live generative dialogue, ordinary runtime TTS, or network dependencies in the child's core path.
- A general-purpose drag-and-drop programming environment before one small parent recipe succeeds.
- Constant rewards, automatic difficulty engines or adaptive navigation changes without observable benefit.
- Weakening sandbox, package validation or Home authority to make creation feel easier.
- Treating attractive assets, a passed validator or a large test count as proof of enjoyable child use.

## 12. Final assessment

Greia's constraints are productive: they encourage a coherent appliance, reusable services, prepared content, offline ownership and interfaces children can learn. The limitations become damaging only if every new idea must immediately become a platform subsystem.

The project already has more architectural thought and useful implementation than a simple themed launcher. Its strongest next step is to make that foundation disappear from the family's experience. Preserve the cast, keep speech purposeful, make the machine settle when nothing changes, make creation genuinely approachable, and make return/save/recovery boringly reliable.

**My opinion: keep building Greia, but judge progress increasingly by a small number of excellent family journeys rather than the amount of infrastructure or content accumulated.**
