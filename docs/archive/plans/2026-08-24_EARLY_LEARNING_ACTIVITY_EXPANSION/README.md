# Greia Early Learning Activity Expansion

**Date:** 2026-08-24
**Status:** proposed future Activity workstream; sole executable implementation authority for the ten packages named here; subordinate to the active architecture-remediation plan and accepted ADRs
**Source baseline:** `5850061c2f26ef7a3c9009b941f878b8095e73c3` on `main`
**Research/evidence:** [current handover](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/HANDOVER.md), [Activity authoring contract](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/skills/greia-activity-authoring/SKILL.md), [visual authoring contract](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/skills/greia-visual-authoring/SKILL.md)

## Authority

This folder is the sole executable implementation authority for the ten new Activity packages listed below. It does not supersede [the blocking architecture-remediation plan](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md), accepted ADRs, exact source/runtime declarations, or the visual-foundation workstream. R7 remains the first blocking platform phase. These Activities may advance only through established Python Activity, storage, event, localization, input, viewport, typography, visual, and Simulator seams; they must not select a display backend, deepen X11 coupling, widen Activity authority, or create a parallel platform service.

No earlier document was found that specifies this portfolio. Existing product, design, and Activity documents remain authoritative for their owned facts. If this plan conflicts with current source or an accepted authority, stop, record the conflict, and amend this plan before implementation.

## Requested outcome

Add a coherent portfolio of ten playful first-party Activities:

- four primarily mathematical Activities for children around five;
- four reading, language, and writing Activities for children around five;
- two gentle, cute, open-ended Activities designed for children around three.

The portfolio must extend the current catalogue rather than reskin existing loops. Each Activity must be understandable without reading instructions, work offline, honor Italian and English content separately, use protected Greia navigation/input/storage/progression boundaries, and remain viable on the Acer-class resource floor.

## Current catalogue inventory

The baseline contains 19 first-party Activities. `workshop_settings` is a Greia customization surface rather than an ordinary learning game.

| Activity directory | Primary learning/play role | Audience | Gap this plan must not duplicate |
|---|---|---:|---|
| `acquario_magico` | calm marine observation and feeding | 3+ | sensory aquarium |
| `clinica_cuccioli` | care sequencing and empathy | 3–7 | patient/tool sequence |
| `costruiamo_ponti` | construction, spatial reasoning, physics intuition | 5–10 | bridge building |
| `cucciolo_mio` | pet care and daily routines | 3–7 | feed/groom/sleep pet loop |
| `foresta_parole` | letter recognition and phonological awareness | 5–8 | pick an initial letter for a pictured word |
| `labirinto_magico` | spatial navigation and planning | 4–10 | maze traversal |
| `memory_meraviglie` | pair matching and visual memory | 3–8 | concealed-card matching |
| `nascondino_bosco` | visual search and nature vocabulary | 3–7 | find hidden animals |
| `orchestra_animali` | rhythm and auditory memory | 3+ | repeat musical patterns |
| `painting` | free drawing and painting | 3+ | general canvas editor |
| `pasticceria_magica` | counting to ten and simple patterns | 4–8 | recipe ingredient counting |
| `piccola_serra` | plant cycles and care | 4–9 | seed/water/bloom/harvest |
| `shape_garden` | shape recognition and free composition | 3+ | place shapes on a canvas |
| `sillabe_magiche` | syllable exploration and matching | 5–8 | syllable-catching/word completion |
| `teatrino_fiabe` | visual storytelling and recording | 3+ | stage composition/performance |
| `treno_numeri` | counting, cardinality, quantity matching | 4–7 | fill numbered train stations |
| `volo_draghetto` | reaction and hand–eye play | 4–9 | endless flight |
| `writing` | general profile-scoped text creation | 5+ | full text editor and emoji picker |
| `workshop_settings` | self-expression and Greia settings | 3+ | platform customization |

### Portfolio gaps found

The catalogue already teaches basic counting, syllables, initial-letter matching, free writing, and general visual storytelling. The highest-value missing experiences are:

1. instant recognition of small quantities and resistance to misleading object size/spacing;
2. composing/decomposing numbers and concrete add/take-away stories;
3. measurement and comparison using one repeated non-standard unit;
4. composing shapes, spatial language, and bilateral symmetry;
5. rhyme/alliteration as listening skills before print;
6. phoneme segmentation explicitly linked to graphemes and word building;
7. authentic short-message writing with drawing, letter supports, and invented spelling;
8. sequencing two or three connected events and explaining cause/effect;
9. low-demand, soothing play for three-year-olds without scores or correctness pressure;
10. open-ended cute character creation that is distinct from profile/avatar authority.

## Research basis and design consequences

This plan uses primary public guidance as design input, not as a claim that a software Activity replaces an educator, caregiver, books, conversation, manipulatives, or physical mark-making.

- The US Institute of Education Sciences recommends developmental progressions for number/operations and for geometry, patterns, measurement, and data; monitoring current knowledge; mathematical language; and embedding math in games and daily contexts: [Teaching Math to Young Children](https://ies.ed.gov/ncee/wwc/practiceguide/18).
- Head Start's preschool mathematics progression distinguishes 36–48 and 48–60 month development. By roughly 60 months it includes subitizing up to five, one-to-one counting to ten, comparing sets up to five, concrete joining/separating, simple pattern cores, repeated-unit measurement, shape composition, and spatial vocabulary: [Math Preschool](https://headstart.gov/school-readiness/article/math-preschool).
- Head Start treats preschool literacy as phonological awareness, print/alphabet knowledge, comprehension/text structure, and writing. Its progression includes rhyme/alliteration, initial sounds, letter–sound knowledge, retelling two or three events, and intentional drawing/scribbling/letters/invented spelling: [Literacy Preschool](https://headstart.gov/school-readiness/article/literacy-preschool).
- IES gives strong-evidence recommendations to build awareness of speech sounds and link those sounds to letters, then use word-building to connect phonemic awareness and letter–sound knowledge: [Foundational Skills to Support Reading](https://ies.ed.gov/ncee/wwc/PracticeGuide/21).
- IES's preschool guide also recommends intentional, engaging mathematical instruction, mathematical conversation, letter/sound work, vocabulary, and shared-book reading: [Preparing Young Children for School](https://ies.ed.gov/ncee/wwc/PracticeGuide/30/i).

Those sources produce these implementation rules:

1. Use concrete visible objects before bare equations or isolated symbols.
2. Keep the age-three Activities at recognition, matching, cause/effect, drawing, and small-set play; never require reading.
3. Build five-year-old challenge along explicit progressions, not random difficulty spikes.
4. Use spoken prompts and pictures for phonological tasks; print must not reveal an answer before the child listens.
5. Treat Italian and English as separate content corpora. Do not mechanically translate rhymes, phonemes, decodable words, or letter examples.
6. Make writing purposeful: a postcard, caption, name, label, or story artifact. Accept invented spelling and marks; never auto-correct child authorship.
7. Record only bounded Activity-owned progress needed to resume or choose the next challenge. Do not diagnose, rank, compare children, or expose an age-derived private visibility system.
8. Give descriptive hints after errors. No countdowns, lives, loss streaks, public scores, forced speed, or shame expressions.

## New portfolio

| Order | ID / directory | Child-facing concept | Primary target | Core learning | Input | Terminal model |
|---:|---|---|---:|---|---|---|
| 1 | `org.greia.luci-di-momo` / `luci_di_momo` | Wake tiny fireflies around Momo's lantern | 4–6 | subitizing 1–5; numeral/quantity; compare small sets | pointer | five-round garden celebration |
| 2 | `org.greia.casa-del-dieci` / `casa_del_dieci` | Help Dani's ten little room-lights make a target number | 5–7 | part–whole; number bonds; add/take away within 10 | hybrid | six repaired rooms |
| 3 | `org.greia.bottega-delle-misure` / `bottega_delle_misure` | Measure parcels with equal wooden blocks | 5–7 | length/height/weight comparison; repeated units | pointer | five delivered parcels |
| 4 | `org.greia.specchi-magici` / `specchi_magici` | Complete Lilli's mirrored mosaics | 5–7 | shape composition; orientation; symmetry; spatial words | pointer | six mosaics restored |
| 5 | `org.greia.festa-delle-rime` / `festa_delle_rime` | Match picture lanterns that sound alike | 4–6 | rhyme recognition; alliteration; listening | pointer | eight listening matches |
| 6 | `org.greia.officina-dei-suoni` / `officina_dei_suoni` | Fit sound beads and letter tiles into Leo's word machine | 5–7 | initial/final phonemes; segmentation; grapheme links; word building | hybrid | six words built |
| 7 | `org.greia.posta-di-leo` / `posta_di_leo` | Draw and write a short postcard to a Greia friend | 5+ | print purpose; name/familiar words; invented spelling; expression | text | open-ended creation, no victory |
| 8 | `org.greia.tre-carte-una-storia` / `tre_carte_una_storia` | Put three picture cards in order, then add a caption | 5+ | sequence; narrative; prediction; cause/effect; emergent writing | hybrid | one saved story at a time |
| 9 | `org.greia.nanna-delle-nuvolette` / `nanna_delle_nuvolette` | Tuck sleepy cloud friends into the night sky | 3+ | gentle sequencing; color/shape matching; cause/effect | pointer | open-ended calm loop |
| 10 | `org.greia.morbidi-mostriciattoli` / `morbidi_mostriciattoli` | Make and save silly soft monster portraits | 3+ | choice-making; visual composition; fine-motor selection | pointer | open-ended creation, no victory |

### Explicit differentiation from existing Activities

- `Luci di Momo` never asks the child to count a train or recipe; flashes are brief and spatially varied so the central skill is seeing a small quantity.
- `Casa del Dieci` uses a fixed ten-frame/room model and part–whole transformations; it is not another count-to-N selection game.
- `Bottega delle Misure` requires a single repeated unit with no gaps/overlaps and comparisons that cannot be solved from decorative object scale.
- `Specchi Magici` uses rotated pieces, composition, and reflection; it is not a free shape-placement canvas.
- `Festa delle Rime` is audio-first; it never tests reading printed endings.
- `Officina dei Suoni` works at phoneme/grapheme level with sound boxes; it does not duplicate whole-syllable catching or single initial-letter choice.
- `Posta di Leo` is a bounded postcard composer, not a second full text editor. It must not copy Writing's gallery/editor implementation.
- `Tre Carte, Una Storia` owns explicit three-event sequencing and a small caption; it is not a stage/recording sandbox.
- `Nanna delle Nuvolette` has no score, failure, rapid stimulus, or mandatory finish.
- `Morbidi Mostriciattoli` saves Activity-owned portraits; it cannot change the child's Greia profile avatar.

## Shared implementation architecture

Each package uses the same responsibility shape but keeps its own domain semantics:

```text
main.py             thin composition root, locale/context construction, dependency injection
<slug>_model.py     immutable definitions + mutable session/document invariants
<slug>_content.py   bounded language/content corpus; no rendering or IO
<slug>_services.py  Greia Storage and declared-event adapters behind narrow Protocols
<slug>_audio.py     bounded non-overlapping playback owner where speech exists
<slug>_art.py       load/bake/cache Activity-local and shared visuals
<slug>_renderer.py  1024x600 logical presentation and hit geometry
<slug>_app.py       lifecycle, semantic input routing, transition timing, READY/STOP
locales/it.json
locales/en.json
assets/source/icon.svg
assets/icon.png
assets/source/...   reviewed Activity-local masters
assets/runtime/...  flattened PNGs used at runtime
```

`main.py` must stay below 150 lines. No implementation module may exceed 500 lines without a plan amendment that names the coherent ownership reason. Domain methods stay below 80 lines. Use composition; introduce a Protocol only for storage/events/audio/clock/random seams used by both production and tests.

### Rendering and interaction

- Design once in 1024×600 logical coordinates with `PygameReferenceCanvas` or use fluid `ChildUiMetrics` geometry where the Activity is document/grid driven.
- The same transform owns drawing and pointer hit testing. Reject pointer input in platform-protected regions.
- Activity code does not draw, imitate, or own Home/Back. It observes `activity_stop_requested()` and publishes READY once after the first usable presented frame.
- Every interactive target is at least 64×64 logical pixels; primary objects are at least 80×80; numerals use 36–64 px typography.
- Predecode and prescale images, prepare fonts/text, and bake static opaque scenery outside the hot loop. Static screens repaint on invalidation. Active motion targets about 30 fps and ≤50 ms added input latency.
- Completion Activities use `PygameCompletionScreen`, stop active simulation in terminal state, emit/save completion once, and repaint only on invalidation.

### Localization and pedagogical audio

- `LocalizedResources` resolves every child-facing string/audio cue from `locales/it.json` or `locales/en.json`.
- A literacy or number-word recording is `pedagogical_speech`, never a mascot imitation. Generate it from an approved deterministic/native path, keep a WAV review master outside the package, and package only reviewed OGG/WAV assets.
- The content review gate is per locale. Italian and English word/rhyme sets are independently authored and reviewed.
- `SpeechQueue` in each speech-bearing Activity is a bounded FIFO of at most four semantic cues. Starting a new round cancels stale cues. Spoken target → 0.45 s quiet gap → optional nonverbal praise → 0.90 s quiet gap → next target. No SFX begins with a phoneme/word clip.
- A replay-audio button is always available in the Activity-safe top bar, at least 64×64. Gameplay still fails soft to visual demonstration if output is unavailable.

### Storage, progress, and events

- Storage uses only `get_storage()` and one schema-versioned dictionary key per package. Invalid/missing data returns safe defaults; writes are bounded and occur only on semantic transitions.
- Adaptive challenge is driven by bounded Activity-owned recent evidence, never profile age. When a package declares adaptive difficulty, store `level` plus a maximum of eight recent attempt summaries. Raise one level after at least 6 of the last 8 first-attempt successes with at most one hint; lower one level after 3 consecutive scaffolded completions or abandoned rounds; otherwise hold. Never lower during the same visible round.
- Activities emit only exact manifest-declared factual events with stable per-occurrence idempotency keys. They do not award Stars or badges.
- Creation Activities emit one `creation` event only after an artifact is durably saved. Completion Activities emit one `completion` event per finished session set. Do not emit click/action telemetry.

### Visual asset decisions

Use the repository discovery helper before art work. Current relevant reviewed resources include:

| Need | Decision | Existing source |
|---|---|---|
| canonical guide | `REUSE` via current semantic shared-visual API | `character.momo`, `character.dani`, `character.leo`, `character.lilli` |
| number/shape blocks | `COMPOSE/ADAPT` into Activity-local flattened art | `play.toy.blocks.house_set` |
| parcel/book/basket props | `REUSE` or `COMPOSE/ADAPT` | `prop.storage.basket.woven_empty`, `prop.book.open.picture_book`, `prop.stationery.paper_stack.linen` |
| firefly accents | `COMPOSE/ADAPT`; flatten into Activity-local sprites unless promoted runtime semantics already exist | `fx.particles.fireflies` |
| grounding | `REUSE`/flatten | `shadow.contact.ellipse_small`, `shadow.contact.ellipse_wide` |
| calm water/night FX | `COMPOSE/ADAPT` from candidate references only after visual review | `fx.water.ripple_rings`, `fx.water.bubbles_rising`, `light.moonbeam.cool_blue_rays` |
| letter tiles, ten-house, balance, mirrored mosaics, postcards, cloud friends, monster parts | `CREATE ORIGINAL` Activity-local SVG masters | no direct fit; do not force unrelated assets |

Every launcher icon is a distinct 256×256 RGBA PNG baked from `assets/source/icon.svg`, with 10–12% safe padding and no text/flag. Candidate-reference art cannot be shipped by direct copy without adaptation and pixel review.

## Content lock supplied to Session 00

Session 00 must preserve these draft corpora exactly while obtaining a fluent-speaker/early-years review. A rejection stops the plan and produces a plan amendment; the implementation agent does not substitute words.

### Italian rhyme pairs

```text
cane—pane     gatto—piatto     rana—lana      mela—vela
fiore—cuore   palla—farfalla   torta—porta    naso—vaso
```

### English rhyme pairs

```text
cat—hat       moon—spoon       cake—snake     log—frog
bear—chair    boat—goat        star—car       mouse—house
```

### Initial-sound families for Officina dei Suoni

```text
Italian:
/m/ mare mela mano
/p/ pane pera palla
/l/ luna lana luce
/f/ fiore fata foglia
/t/ topo torta tenda
/s/ sole sasso sedia

English:
/m/ moon map mouse
/p/ pig pan pear
/l/ leaf lamp log
/f/ fish fan fox
/t/ top tent turtle
/s/ sun sock star
```

The shipped first version uses only these initial-sound families. Final-phoneme and multi-phoneme word-building levels remain locked until the per-locale review in Session 00 supplies an accepted exact corpus; if either locale cannot pass, `difficulty_max` is reduced to 3 and the feature is omitted rather than improvised.

### Three-card story seeds

```text
paper + crayons -> make a picture -> give the picture to a friend
rain begins -> open an umbrella -> jump in a puddle
loose kite string -> tie the knot -> kite flies
pack a basket -> walk to the meadow -> share a picnic
write a card -> put it in an envelope -> friend opens it
stack blocks -> finish a tower -> place the flag
find a cold cloud -> wrap it softly -> cloud glows warmly
spill water -> fetch a cloth -> floor is dry
```

Every story receives independently authored Italian and English captions and semantic picture IDs. Art contains no words.

## How to use this plan

Give one numbered session file to one implementation agent. The agent receives this README plus that session file, implements only its allowlist, runs its local and cumulative gate, commits the coherent result on current `main`, returns the handoff packet, and stops. A reviewer resolves the handoff before the next session begins. Do not combine sessions. Do not perform provider-backed art/audio work in an implementation session. Do not start Simulator or hardware acceptance before its numbered boundary.

## Execution order

| Session | Result |
|---:|---|
| [00](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/00-baseline-content-lock.md) | revalidated source baseline plus accepted bilingual pedagogical corpus |
| [01](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/01-luci-di-momo.md) | `Luci di Momo` source package and focused tests |
| [02](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/02-casa-del-dieci.md) | `Casa del Dieci` source package and focused tests |
| [03](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/03-bottega-delle-misure.md) | `Bottega delle Misure` source package and focused tests |
| [04](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/04-specchi-magici.md) | `Specchi Magici` source package and focused tests |
| [05](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/05-festa-delle-rime.md) | `Festa delle Rime` source package, reviewed audio, and focused tests |
| [06](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/06-officina-dei-suoni.md) | `Officina dei Suoni` source package, reviewed audio, and focused tests |
| [07](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/07-posta-di-leo.md) | `Posta di Leo` source package and focused tests |
| [08](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/08-tre-carte-una-storia.md) | `Tre Carte, Una Storia` source package and focused tests |
| [09](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/09-nanna-delle-nuvolette.md) | `Nanna delle Nuvolette` source package and focused tests |
| [10](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/10-morbidi-mostriciattoli.md) | `Morbidi Mostriciattoli` source package and focused tests |
| [11](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/11-catalogue-cumulative-gate.md) | all ten packages validated together at source level |
| [12](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/12-simulator-acceptance.md) | real-runtime Simulator interaction and visual evidence |
| [13](https://github.com/frozenpepper/Greia/blob/0f560c2e5139b713ba550b6f04cf6861b1dd11fb/docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/13-physical-acceptance.md) | Acer resource/input acceptance and honest closure status |

## Global rules

- Work directly on current `main`; pull with `git pull --ff-only origin main` before each substantive write and preserve unrelated changes.
- Read the current Activity, engineering, terminal, achievement, discovery, voice, and visual-authoring skill routes named by the session.
- Edit only the session allowlist. An unlisted required file is a stop condition and plan-amendment request.
- Keep all ten packages Python/API `0.1`; do not claim or create a Web runtime.
- Make no network, hosted Action, image-provider, or custom-voice call. Session 00 may use already available deterministic/local audio tooling only after its human review boundary is explicit.
- Run focused tests and every previously completed Activity test after each session. Session 11 owns the full provider-free repository gate.
- Update the active architecture plan and `HANDOVER.md` after every substantive implementation session exactly as repository rules require. Do not rewrite prior ledger entries.
- Label evidence as SOURCE, SIMULATOR VISUAL REVIEW, or PHYSICAL VISUAL REVIEW. No source or Simulator result proves Acer/Pi performance.
- Commit one coherent change per session using its exact commit subject.

## Cumulative regression policy

Each Activity session adds `tests/test_activity_<slug>.py`. Its cumulative gate runs all numbered-portfolio tests completed so far plus:

```text
tests.test_activity_contract
tests.test_activity_audience_manifest
tests.test_first_party_activity_audience_metadata
tests.test_first_party_activity_readiness
tests.test_core_activity_system_safe_ui
tests.test_activity_ui
tests.test_activity_viewport
tests.test_localization
tests.test_typography_emoji
```

Session 11 runs `make verify`. A missing/skipped test, invalid Activity, stale source SHA, or provider call makes the gate fail.

## Handoff contract

```text
session id:
base SHA and resulting commit SHA:
files changed:
tests added or changed:
commands with exit codes and test counts:
provider/network calls observed:
art/audio sources and review labels:
artifacts and SHA-256 values:
scoped git diff --stat:
known residuals:
stop-condition audit:
cumulative gate result:
evidence label and explicit unproven boundaries:
```

## Global stop conditions

- Current source contradicts a prescribed manifest/API/symbol and the conflict cannot be resolved without changing this plan.
- Any package requires a platform API, permission, runtime, input action, font loader, storage owner, achievement API, or shared-asset API that current source does not provide.
- Italian or English pedagogical content/audio lacks fluent-speaker review.
- A later protection is required to make the current commit safe.
- An Activity duplicates an existing package's primary loop instead of the differentiator stated above.
- An implementation needs an unlisted file or unresolved design choice.
- A required test, visual artifact, content hash, audio review, or proof field is absent or stale.
- Provider/live work would begin before Sessions 12–13 or without the explicit owner-controlled environment required there.
- R7 or another blocking architecture change makes the Activity runtime/Simulator boundary materially different; rebase the plan before continuing.

## Final acceptance boundary

Session 11 can establish provider-free SOURCE closure only. Session 12 can establish SIMULATOR VISUAL REVIEW and real-runtime developer interaction only. Session 13 can establish named Acer PHYSICAL evidence for the exact tested SHA. Pi, production direct-display/session, installed-image footprint, touch hardware, controller hardware, human learning efficacy, and Phase-0 closure remain separate evidence obligations unless they are explicitly executed and recorded under their owning procedures.
