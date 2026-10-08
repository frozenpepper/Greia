# P6 — Child Navigation and Visual Curation (32 Draft Candidates)

**Status:** DESIGN BASELINE + SOURCE-EDITED / UNVERIFIED (2026-10-08)  
**Owner:** [Creations + Activity Release Plan](./PLAN.md), P6/P7.  
**Current exact state:** [PROGRESS.md](./PROGRESS.md); local execution queue:
[`GREIA_LOCAL_AGENT_TASK_QUEUE.md`](../../testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md).  
**Not:** a new architecture, separate implementation programme, alternative Parent
policy, approved roster, art sign-off, or authorization to create voices/use Modal.

## 1. What a child is supposed to understand

A prereader needs to distinguish **the things they can do** from **the
things they have already made**, at a glance. The Home answers six plain
questions:

| Home portal | Meaning to the child | Canonical visual cue |
|---|---|---|
| **Create / Crea** | I want to make something of my own | Existing **palette** |
| **My Creations / Le mie creazioni** | I want to see or use the things I saved | Existing **backpack** (provisional visual, requires child review) |
| **Play / Gioca** | I want an active challenge or pretend game | Existing puzzle pieces |
| **Learn / Impara** | I want to discover or practice a skill | Existing book |
| **Explore / Esplora** | I want to investigate the world | Existing magnifier |
| **My Greia / Mio Greia** | This is my own Greia space | Existing unicorn |

This is one **flat platform-owned** Home, not an extra chooser, app,
filesystem or parallel catalogue. My Creations is a *trusted Shell viewer*
with its own safe delete/preview controls, never an ordinary Activity with
arbitrary file permissions. The display/selection broker remains unchanged.

The order now authored in `GreiaChildShell._home_collections` is
**Create → My Creations → Play → Learn → Explore → My Greia**;
My Creations stays available even when Parent policy filters out all
Create Activities. The source replaces the former visually duplicated
palette icon for My Creations with an existing, different core-icon
silhouette. No new SVG or renderer dependency was added.

**Responsive information layout**, not an unbounded list: the existing
Collection-Home renderer aims for three columns × two rows on 1024×600,
two columns × three rows on 800×480, and three compact columns × two
rows on 480×320. Its small-landscape column count and lower portal-size
floor were corrected in source. **These geometry intents are NOT
accepted screenshots.** The local agent must inspect clipping, character
placement, title legibility, hit areas and actual 3–5-year-old readability.
The 480×320 physical touch target needs particular attention.

### Speech is part of the Home, not optional decoration

The existing `SpokenLabelController` looks for platform-owned
prerecorded `my_creations.wav` under
`assets/audio/system/launcher-labels/{it,en}/`.
As audited on 2026-10-08, both directories have other primary Collection
labels but **no `my_creations.wav`**. Moving the portal beside Create
does NOT silently solve that omission. This is a P6 source-content
gap. The existing `tools/greia_voice.py` authoring workflow owns
production (Modal if configured and explicitly authorized); no runtime
TTS, generic rerecording, wrong-word fallback, or automatic paid calls.
Child-facing acceptance requires a natural recorded Italian **“Le mie
creazioni”** and English **“My Creations”**, actual playback and human
listening, before proclaiming complete prereader Home navigation.

## 2. The Create collection now means making something durable

Previously four draft candidates appeared in **Create** despite being
care/exploration/goal-oriented puzzle activities without a reusable
child-authored work product:

| Existing Activity | Previous Home membership | Now | Why |
|---|---|---|---|
| `acquario_magico` | Explore + Create | **Explore** | Feeding/observing aquatic creatures and day/night ecology; persisted aquarium state is not an exported creative artifact |
| `cucciolo_mio` | Play + Create | **Play** | Feed, groom, nurture and put a pet to sleep; care is not saved art/media |
| `specchi_magici` | Learn + Create | **Learn** | Five authored symmetry challenge tiers; completion/progression is not an editable shared creation |
| `torre_forme` | Play + Create | **Play** | Spatial tower/line-clearing mastery rather than creating a saved work |

All four remain installed **draft** candidates, launchable via their
honest collection; no Activity package IDs, saved data, difficulty,
age, achievement events, trusted capability, release roster or Parent
policy changed. These are changes to `[presentation].categories`
only, not `[education].categories` (curriculum) or private
`[storage]` definitions. They are not quality approvals.

The resulting **six** current Create candidates are the sources of
actual reusable or saved work:

| Create Activity | The thing the child makes | Expected durable handoff |
|---|---|---|
| `painting` | Picture | Editable private painting; deliberate PNG share/import |
| `shape_garden` | Shape composition | Private editable project; flattened PNG share |
| `storie_della_mia_voce` | Spoken story | Saved narration; chosen WAV for Theatre/Orchestra |
| `teatrino_fiabe` | Puppet show | Saved show with private image/audio source snapshots |
| `writing` | Written page | Saved document; bounded UTF-8 share/import |
| `posta_di_leo` | Postcard/message | Saved card; compatible bounded UTF-8 share/import |

**No per-Activity Create submenu** is added: six carefully selected
large cards fit the existing grid/scroll model and keep the creative
journey visibly related to the adjacent saved-work portal.
Age/profile policy remains fully authoritative (for example Writing
and Posta may be hidden from younger children by Parent policy).

## 3. Keep navigation and curriculum as different taxonomies

The 32 *draft* child-content candidates are not 32 confirmed-good
Activities. Their **primary portfolio** for curation, independent of
their overlapping child-facing Home memberships, is:

| Portfolio family | Draft candidates | Count | Design/quality concern |
|---|---|---:|---|
| Math and quantities | `bottega_delle_misure`, `casa_del_dieci`, `il_giardino_dei_numeri`, `luci_di_momo`, `stelle_incantate`, `treno_numeri` | 6 | Show counting vs comparison vs composition as genuinely different learning loops |
| Words and literacy | `festa_delle_rime`, `foresta_parole`, `officina_dei_suoni`, `mondo_contrari`, `posta_di_leo`, `writing` | 6 | Meaning, phonemic listening, creative authorship and age-5 tools must not blur |
| Nature and observation | `acquario_magico`, `enciclopedia_greia`, `nascondino_bosco`, `quattro_stagioni` | 4 | Actual facts/observation instead of four ambient galleries |
| Logic, spatial and strategy | `la_discesa_della_biglia`, `labirinto_magico`, `memory_meraviglie`, `quattro_amici`, `specchi_magici`, `torre_forme` | 6 | Correct physical/logic feedback, solvable challenges, no fake high difficulties |
| Creative making and performance | `painting`, `shape_garden`, `storie_della_mia_voce`, `teatrino_fiabe` | 4 | Large authoring affordances, persistent work, real cross-Activity interoperability |
| Care and emotions | `clinica_cuccioli`, `cucciolo_mio`, `faccine_momo` | 3 | Distinguish health routines, pet care and expression/empathy |
| Music and rhythm | `orchestra_animali` | 1 | Important coverage gap; do not falsely relabel a word game to fill it |
| Motor/action and timing | `colline_allegre`, `corsa_bacche` | 2 | Playable challenge with recovery; prove input and performance on target screens |
| **TOTAL** | **Exactly the 32 candidate packages in the draft release roster** | **32** | **Zero approved** |

This portfolio is an **editorial lens**, not an extra runtime group ID
or a replacement for Parent educational categories. A creative
writing Activity may correctly be in both Create and Learn while
having one principal portfolio function.

The remaining **12 withheld** child-content Activities and **1
system-owned My Greia** are unchanged; consult PROGRESS P7 for
their exact dispositions. The official `[release].status` remains
`draft` and thus fail-closed.

## 4. Play and Learn: complete draft activity-to-intent audit (2026-10-08)

**Real source counts for the 32 draft candidates, after this tranche:**
**Play 21**, **Learn 22**, and **Create 6**. These are overlapping
**Home memberships**, not exclusive curriculum counts; 32 is the total
of unique child draft candidates. Source data comes from each existing
`activities/*/activity.toml`, not guessed game genres or a new runtime
classification.

Two further mismatches were corrected **only in
`[presentation].categories`**:

- `storie_della_mia_voce`: **Create**, rather than Create + Play.
  Its actual interaction is recording/replaying/saving stories, not
  a challenge or pretend-play game; a child still finds every saved
  narration in My Creations.
- `quattro_stagioni`: **Explore + Learn**, rather than Explore +
  Play + Learn. Its interactions explore seasonal/weather/day-night
  relationships; source-reviewed milestones are discoveries, not
  game wins/losses.

Neither loses launchability, saves, educational metadata, language,
events or Parent permission. Both remain draft candidates. The
`Play 23 / Learn 22` numbers before these two changes are historical.

### Play (21) — primary child-intent map for human curation

| Editorial child intent | Exactly which draft Activities | Count |
|---|---|---:|
| Move, race and react | `colline_allegre`, `corsa_bacche` | 2 |
| Care and express feelings | `clinica_cuccioli`, `cucciolo_mio`, `faccine_momo` | 3 |
| Play with numbers | `casa_del_dieci`, `il_giardino_dei_numeri`, `luci_di_momo`, `treno_numeri` | 4 |
| Play with sounds and words | `festa_delle_rime`, `foresta_parole`, `officina_dei_suoni` | 3 |
| Puzzles, observation and building | `la_discesa_della_biglia`, `labirinto_magico`, `memory_meraviglie`, `mondo_contrari`, `nascondino_bosco`, `quattro_amici`, `torre_forme` | 7 |
| Make music | `orchestra_animali` | 1 |
| Put on a story performance | `teatrino_fiabe` | 1 |
| **Total** | **Every current Play draft candidate, once** | **21** |

### Learn (22) — primary educational intent map for human curation

| Editorial child intent | Exactly which draft Activities | Count |
|---|---|---:|
| Numbers and quantities | `bottega_delle_misure`, `casa_del_dieci`, `il_giardino_dei_numeri`, `luci_di_momo`, `stelle_incantate`, `treno_numeri` | 6 |
| Words, language and writing | `festa_delle_rime`, `foresta_parole`, `officina_dei_suoni`, `posta_di_leo`, `writing` | 5 |
| Nature and seasonal knowledge | `enciclopedia_greia`, `quattro_stagioni` | 2 |
| Care and social understanding | `clinica_cuccioli`, `faccine_momo` | 2 |
| Thinking, spatial reasoning and symmetry | `la_discesa_della_biglia`, `memory_meraviglie`, `mondo_contrari`, `quattro_amici`, `shape_garden`, `specchi_magici` | 6 |
| Music and rhythm | `orchestra_animali` | 1 |
| **Total** | **Every current Learn draft candidate, once** | **22** |

These tables are **editorial review lenses only**. They do **not**
create root categories, alter approved teaching skills, or assign
new `discovery_tags`. The “musical” singleton and the Story
performance singleton are **real**: do not pretend there are enough
independent Activities to give each a two-card submenu.

The existing `AdaptiveCollectionPlanner` currently offers at most
five semantic groups of at least two Activities and requires full,
honest coverage. On the verified original 23/22 metadata the
frequency-first five tags left three Play Activities and four
Learn Activities without a truthful destination. After the two
membership corrections, at least the music singleton in each
collection prevents a complete useful split. **Therefore keep
direct Activity browsing**. This is intentional—not a
failure to finish wiring a grouping feature. A six/seven-option
chooser plus more navigation steps would be *worse* for a
3–5-year-old than carefully legible Activity cards.

The test `tests/test_launcher_collection_visual_curation.py`
asserts that the real release-roster memberships remain
represented, and checks every age-filtered projection for no
missing/duplicated Activity IDs. Future authentic content changes
may justify groups, but require real screenshots, bilingual
spoken names, complete mapping *after* Parent filtering and
child trial before introducing any submenu.

### Discovery art is a language: stop duplicating symbols

The 13 already-platform-owned subcollection themes previously
reused the **palette** for Drawing, Music and Making; **book** for
Writing, Words and Stories; and **puzzle pieces** for Building,
Numbers, Puzzles and Action. That is not meaningfully legible
to a prereader.

The source mapping in `src/greia_launcher/catalogue_view.py`
now selects 13 **different existing canonical Greia core
illustrations**: palette, notebook, music star, train blocks,
coins, alphabet board, block puzzle, garden, book, rainbow,
heart, lightning and unicorn. No new assets, font family,
rendering system or per-frame image conversions were added.
Their artwork consistency still needs GLA-008 actual
64/48px screenshot inspection. These are illustrations
for subcollection groups *when those groups legitimately exist*;
the current Play/Learn screens still browse directly.

The launch status also now uses `Avvio...` in Italian and
`Starting...` in English for **both** ordinary and shared-art
Activity cards. This repairs a real language inconsistency
without touching voice generation or changing any child
navigation level.

## 5. Concrete visual decisions to review, not declare passed

1. **Home at 1024×600, 800×480, 480×320:** screenshot all six portals
   at once. Check their order, responsive rows, no overlap with
   profile/Back chrome, finger-sized targets, distinct Create/My
   Creations silhouette, legibility and correct IT/EN labels without clipping.
   Inspect the whole frame, not unit-test-only hit boxes.
2. **The six Create cards:** compare icons/real screenshots together
   with the art-family contact sheet. Check a prereader can distinguish
   drawing, shape building, puppet theatre, voice story, writing and
   postcard without relying on similar text labels. Reuse accepted
   Greia storybook/soft-depth system, not arbitrary Activity gradients.
3. **My Creations:** first-run empty screen, image thumbnails, audio
   Play/Pause/Replay, text previews and the cancellation/delete
   confirmation must look like one family of Greia controls, with a
   clear Return-to-Home outcome.
4. **Dense Play/Learn screens:** visually inspect number of page turns
   and whether the child can independently recover their position.
   Only approve subdivision based on the complete activity-to-group
   map and the actual filtered views at ages 3/4/5.
5. **114-art-family inventory:** compare canonical 39 core icons,
   45 Activity icons and 30 character expression assets at 128/64/48
   source sizes, plus real UI screenshots; severity-rank mixed style,
   illegible silhouettes, duplicated icon metaphors and poor color
   contrast. Assets are source material, not proof of accepted UI.
6. **Low-resource floor:** large previews and soft shadows are
   appropriate only when cached, bounded and measured. No new
   per-frame rasterization, runtime SVG authoring, full-frame
   conversion, or unbounded artwork memory.

Visual direction remains warm, expressive Greia toy/storybook art,
legible silhouettes, rounded physical affordances, carefully
controlled depth and obvious feedback. This is neither a generic
desktop icon grid nor a decorative art slideshow. Parent policy
and protected OS navigation remain untouched.

## 6. Acceptance and next real work

The source-only changes to existing Activity metadata, Home ordering,
a distinct existing core icon, compact-landscape Home columns and
focused tests are **committed but not yet run locally**. Source checks
live in `tests/test_child_home_creation_organization.py`; the
existing tests for catalogue, Parent policy, spoken labels and
launcher layout remain required.

The **single** local-agent task queue assigns the current exact
commands and visual/voice check to GLA-008/GLA-010; do not create
another acceptance harness here. A local operator must record
current HEAD, clean tree, actual test outputs, screenshot sizes,
test scene/profile and failed commands. A human must separately
review pictures and IT/EN audio. No official roster change,
release status approval or installed/hardware acceptance was made
through this document.

After those checks, continue the **existing** P6/P7 programme:
correct actual misleading memberships/tags across the withheld
catalogue if justified by gameplay, resolve Play/Learn density
only with complete semantic groups, prioritize visual art defects
from contact sheets, and retest the 32 draft games before
any release approval.
